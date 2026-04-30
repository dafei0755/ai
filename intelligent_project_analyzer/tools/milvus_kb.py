"""
Milvus 向量数据库知识库工具 (v7.141+)

提供基于 Milvus 的 6 阶段深度定制 RAG Pipeline:
  Stage 1: 查询理解与改写 (Query Understanding)
  Stage 2: 混合检索 (Hybrid Retrieval)
  Stage 3: 粗排 (Coarse Ranking)
  Stage 4: 重排序 (Reranking)
  Stage 5: 后处理与质量控制 (Post-processing)
  Stage 6: 结果组装与监控 (Output Formatting)
"""

import json
import time
from typing import Any, Dict, List, Optional

import jieba
from loguru import logger

from ..core.types import ToolConfig

# Milvus imports
try:
    from pymilvus import Collection, connections, utility
    from sentence_transformers import CrossEncoder, SentenceTransformer

    MILVUS_AVAILABLE = True
except ImportError:
    logger.warning("️ Milvus/sentence-transformers not available. Run: pip install pymilvus sentence-transformers")
    MILVUS_AVAILABLE = False

# LangChain integration
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field

    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, tool wrapping disabled")
    LANGCHAIN_AVAILABLE = False

# 复用现有模块
try:
    from .quality_control import SearchQualityControl
    from .query_builder import DeliverableQueryBuilder
except ImportError:
    logger.warning("️ quality_control/query_builder not available. Will use fallback mode.")
    DeliverableQueryBuilder = None
    SearchQualityControl = None

#  v7.164: 导入搜索结果ID生成器
try:
    from ..utils.search_id_generator import add_ids_to_search_results
except ImportError:
    logger.warning("️ v7.164 search_id_generator not available")
    add_ids_to_search_results = None


# ==================== Stage 1: 查询理解与改写 ====================
class QueryProcessor:
    """
    查询处理器 - Pipeline 第一阶段

    功能:
    - 关键词提取 (jieba 中文分词)
    - 意图识别 (规范查询/案例查询/技术查询)
    - 查询扩展 (同义词、相关术语)
    - 构建过滤条件
    """

    def __init__(self, llm=None):
        self.llm = llm
        # 停用词列表 (中文)
        self.stopwords = set(
            [
                "的",
                "了",
                "在",
                "是",
                "我",
                "有",
                "和",
                "就",
                "不",
                "人",
                "都",
                "一",
                "一个",
                "上",
                "也",
                "很",
                "到",
                "说",
                "要",
                "去",
                "你",
                "会",
                "着",
                "没有",
                "看",
                "好",
                "自己",
                "这",
            ]
        )

    def process(self, query: str, context: Dict = None) -> Dict[str, Any]:
        """
        处理查询,生成增强版查询

        Args:
            query: 原始查询字符串
            context: 上下文信息 (deliverable, project_type等)

        Returns:
            {
                "original_query": "原始查询",
                "keywords": ["关键词1", "关键词2"],
                "intent": "规范查询|案例查询|技术查询",
                "expanded_query": "扩展后的查询",
                "filters": {"document_type": "规范", ...}
            }
        """
        # 1. 关键词提取
        keywords = self._extract_keywords(query)

        # 2. 意图识别
        intent = self._classify_intent(query, keywords, context)

        # 3. 查询扩展 (当前版本使用规则,未来可集成LLM)
        expanded_query = self._expand_query(query, keywords, intent)

        # 4. 构建标量过滤条件
        filters = self._build_filters(intent, context)

        return {
            "original_query": query,
            "keywords": keywords,
            "intent": intent,
            "expanded_query": expanded_query,
            "filters": filters,
        }

    def _extract_keywords(self, query: str) -> List[str]:
        """使用 jieba 分词提取关键词"""
        words = jieba.cut(query)
        # 过滤停用词和单字符
        keywords = [w for w in words if w not in self.stopwords and len(w) > 1]
        return keywords[:10]  # 限制最多10个关键词

    def _classify_intent(self, query: str, keywords: List[str], context: Optional[Dict]) -> str:
        """意图分类 - 基于规则"""
        # 规则: "标准"/"规范"/"国标"/"要求" → 规范查询
        if any(k in query for k in ["标准", "规范", "国标", "要求", "规定"]):
            return "规范查询"
        # 规则: "案例"/"项目"/"参考"/"示例" → 案例查询
        elif any(k in query for k in ["案例", "项目", "参考", "实例", "示例"]):
            return "案例查询"
        # 规则: "材料"/"工艺"/"技术"/"施工" → 技术查询
        elif any(k in query for k in ["材料", "工艺", "技术", "施工", "方法"]):
            return "技术查询"
        # 从上下文推断
        elif context and context.get("deliverable"):
            deliverable_name = context["deliverable"].get("name", "")
            if "规范" in deliverable_name or "标准" in deliverable_name:
                return "规范查询"
            elif "方案" in deliverable_name or "设计" in deliverable_name:
                return "案例查询"
        return "通用查询"

    def _expand_query(self, query: str, keywords: List[str], intent: str) -> str:
        """
        查询扩展 - 添加同义词和相关术语

        当前版本: 基于规则的扩展
        未来版本: 可集成LLM生成同义词
        """
        # 同义词映射 (示例)
        synonym_map = {
            "客厅": ["起居室", "会客厅"],
            "卧室": ["睡房", "卧房"],
            "现代": ["现代风格", "现代简约"],
            "照明": ["灯光", "照明设计", "光照"],
            "标准": ["规范", "要求", "国标"],
        }

        expanded_terms = []
        for keyword in keywords:
            if keyword in synonym_map:
                expanded_terms.extend(synonym_map[keyword])

        if expanded_terms:
            return f"{query} {' '.join(expanded_terms[:3])}"  # 最多添加3个同义词
        return query

    def _build_filters(self, intent: str, context: Optional[Dict]) -> Dict:
        """
        根据意图和上下文构建 Milvus 标量过滤条件

         v7.141: 添加用户隔离过滤支持
         v7.141.2: 添加团队知识库支持
        """
        filters = {}

        # 根据意图映射到 document_type
        intent_to_type = {"规范查询": "设计规范", "案例查询": "案例库", "技术查询": "技术知识"}

        if intent in intent_to_type:
            filters["document_type"] = intent_to_type[intent]

        # 从上下文提取 project_type
        if context and context.get("project_type"):
            filters["project_type"] = context["project_type"]

        #  v7.141: 添加用户隔离过滤
        #  v7.141.2: 添加团队知识库支持
        if context:
            if context.get("user_id"):
                filters["user_id"] = context["user_id"]
            if context.get("team_id"):  #  v7.141.2
                filters["team_id"] = context["team_id"]
            if context.get("search_scope"):
                filters["search_scope"] = context["search_scope"]

        return filters


# ==================== Stage 2: 混合检索 ====================
class HybridRetriever:
    """
    混合检索器 - Pipeline 第二阶段

    功能:
    - 向量检索 (语义相似度)
    - 标量过滤 (metadata filtering)
    """

    def __init__(self, collection: "Collection", embedding_model: "SentenceTransformer"):
        self.collection = collection
        self.embedding_model = embedding_model

    def retrieve(self, processed_query: Dict, top_k: int = 50) -> List[Dict]:
        """
        混合检索

        Args:
            processed_query: Stage 1 的输出
            top_k: 候选结果数量 (为后续 rerank 准备，通常是最终结果的 5-10 倍)

        Returns:
            候选文档列表
        """
        # 1. 生成查询向量
        query_text = processed_query["expanded_query"]
        query_vector = self.embedding_model.encode(query_text, normalize_embeddings=True).tolist()

        # 2. 构建标量过滤表达式
        filter_expr = self._build_milvus_expr(processed_query["filters"])

        # 3. 向量检索 + 标量过滤
        search_params = {"metric_type": "COSINE", "params": {"ef": 128}}  # HNSW 参数

        try:
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=filter_expr,  # 标量过滤
                output_fields=[
                    "title",
                    "content",
                    "document_type",
                    "tags",
                    "source_file",
                    "project_type",
                    "owner_type",
                    "owner_id",
                    "visibility",
                ],  #  v7.141: 包含用户隔离字段
            )
        except Exception as e:
            logger.error(f"Milvus 检索失败: {e}")
            return []

        # 4. 格式化结果
        candidates = []
        for hit in results[0]:
            candidates.append(
                {
                    "id": str(hit.id),
                    "title": hit.entity.get("title", "无标题"),
                    "content": hit.entity.get("content", ""),
                    "vector_score": float(hit.score),  # Cosine 相似度
                    "metadata": {
                        "document_type": hit.entity.get("document_type", ""),
                        "tags": hit.entity.get("tags", []),
                        "project_type": hit.entity.get("project_type", ""),
                        "source_file": hit.entity.get("source_file", ""),
                        #  v7.141: 添加用户隔离字段
                        "owner_type": hit.entity.get("owner_type", "system"),
                        "owner_id": hit.entity.get("owner_id", "public"),
                        "visibility": hit.entity.get("visibility", "public"),
                    },
                }
            )

        logger.debug(f"Stage 2: 检索到 {len(candidates)} 个候选文档")
        return candidates

    def _build_milvus_expr(self, filters: Dict) -> Optional[str]:
        """
        构建 Milvus 标量过滤表达式

         v7.141: 支持用户隔离过滤 + 文档共享
        - owner_type: "system" | "user" | "team"
        - owner_id: "public" | user_id | team_id
        - visibility: "public" | "private"
        - search_scope: "all" | "system" | "user" | "team"

        共享逻辑：
        - owner_type="system" 的文档对所有人可见（公共知识库）
        - owner_type="user" + visibility="public" 的文档对所有人可见（用户共享）
        - owner_type="user" + visibility="private" 的文档仅所有者可见
        - owner_type="team" 的文档对团队成员可见（需要传递 team_id）
        """
        if not filters:
            return None

        exprs = []

        #  v7.141.2: 用户隔离过滤 + 文档共享
        user_id = filters.get("user_id")
        team_id = filters.get("team_id")  #  团队ID
        search_scope = filters.get("search_scope", "all")

        if search_scope == "all":
            # 查询：公共知识库 + 用户共享文档 + 当前用户的私有库 + 所属团队的文档
            visibility_conditions = []

            # 1. 公共知识库（所有人可见）
            visibility_conditions.append('owner_type == "system"')

            # 2. 用户共享文档（visibility=public）
            visibility_conditions.append('(owner_type == "user" AND visibility == "public")')

            # 3. 当前用户的私有文档
            if user_id:
                visibility_conditions.append(f'(owner_type == "user" AND owner_id == "{user_id}")')

            # 4. 所属团队的文档
            if team_id:
                visibility_conditions.append(f'(owner_type == "team" AND owner_id == "{team_id}")')

            if visibility_conditions:
                exprs.append(f'({" OR ".join(visibility_conditions)})')

        elif search_scope == "system":
            # 仅查询公共知识库
            exprs.append('owner_type == "system"')

        elif search_scope == "user" and user_id:
            # 仅查询当前用户的私有库（包括 private 和 public）
            exprs.append(f'(owner_type == "user" AND owner_id == "{user_id}")')

        elif search_scope == "team" and team_id:
            #  v7.141.2: 仅查询团队知识库
            exprs.append(f'(owner_type == "team" AND owner_id == "{team_id}")')

        # 原有过滤逻辑
        if "document_type" in filters:
            exprs.append(f'document_type == "{filters["document_type"]}"')

        if "project_type" in filters:
            exprs.append(f'project_type == "{filters["project_type"]}"')

        if "tags" in filters and filters["tags"]:
            # Array 包含查询 (如果 tags 是数组字段)
            tag_exprs = [f'array_contains(tags, "{tag}")' for tag in filters["tags"]]
            exprs.append(f'({" or ".join(tag_exprs)})')

        return " and ".join(exprs) if exprs else None


# ==================== Stage 3: 粗排 ====================
class CoarseRanker:
    """
    粗排器 - Pipeline 第三阶段

    功能:
    - 快速过滤明显不相关的结果 (基于向量相似度阈值)
    """

    def __init__(self, similarity_threshold: float = 0.6):
        self.threshold = similarity_threshold

    def rank(self, candidates: List[Dict]) -> List[Dict]:
        """
        粗排: 基于向量相似度快速过滤

        Args:
            candidates: Stage 2 的候选结果

        Returns:
            过滤后的候选列表
        """
        # 1. 过滤低分结果
        filtered = [doc for doc in candidates if doc.get("vector_score", 0) >= self.threshold]

        # 2. 按相似度排序
        ranked = sorted(filtered, key=lambda x: x["vector_score"], reverse=True)

        logger.debug(f"Stage 3: 粗排 {len(candidates)} → {len(ranked)} (过滤掉 {len(candidates) - len(ranked)} 个)")

        return ranked


# ==================== Stage 4: 重排序 ====================
class CrossEncoderReranker:
    """
    重排序器 - Pipeline 第四阶段

    功能:
    - 使用 Cross-Encoder 模型 (BGE-Reranker-v2-M3) 重新排序
    - 提升 Top-10 质量
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        try:
            self.model = CrossEncoder(model_name, max_length=512)
            logger.info(f"Reranker 模型加载成功: {model_name}")
        except Exception as e:
            logger.warning(f"Reranker 模型加载失败: {e}. 将跳过重排序阶段")
            self.model = None

    def rerank(self, query: str, candidates: List[Dict], top_k: int = 10, rerank_weight: float = 0.7) -> List[Dict]:
        """
        重排序

        Args:
            query: 原始查询
            candidates: Stage 3 的粗排结果
            top_k: 最终返回数量
            rerank_weight: 重排序分数权重 (0-1)

        Returns:
            重排序后的文档列表
        """
        if not self.model or not candidates:
            logger.debug("跳过重排序阶段")
            return candidates[:top_k]

        # 1. 构建 query-document pairs
        pairs = [[query, doc["content"][:500]] for doc in candidates]  # 截断到 500 字符

        # 2. Cross-Encoder 打分
        try:
            rerank_scores = self.model.predict(pairs)
        except Exception as e:
            logger.error(f"Rerank 失败: {e}")
            return candidates[:top_k]

        # 3. 更新分数
        for doc, score in zip(candidates, rerank_scores):
            doc["rerank_score"] = float(score)
            # 融合分数: rerank_weight * rerank + (1-rerank_weight) * vector
            doc["final_score"] = rerank_weight * score + (1 - rerank_weight) * doc["vector_score"]

        # 4. 重新排序并截取 top-k
        reranked = sorted(candidates, key=lambda x: x["final_score"], reverse=True)

        logger.debug(f"Stage 4: 重排序完成, Top-1: {reranked[0]['title']}")

        return reranked[:top_k]


# ==================== Stage 5: 后处理与质量控制 ====================
class PostProcessor:
    """
    后处理器 - Pipeline 第五阶段

    功能:
    - 去重 (合并高度相似的 chunks)
    - 质量控制 (复用 SearchQualityControl)
    - 可信度评分
    """

    def __init__(self, qc_module=None, dedup_threshold: float = 0.95):
        self.qc = qc_module  # SearchQualityControl 实例
        self.dedup_threshold = dedup_threshold

    def process(self, reranked_docs: List[Dict], deliverable_context: Dict = None) -> List[Dict]:
        """
        后处理流程:
        1. 去重
        2. 质量控制 (复用 SearchQualityControl)
        3. 可信度评分
        """
        # 1. 去重 (合并高度相似的 chunks)
        deduplicated = self._deduplicate(reranked_docs)

        # 2. 质量控制 (复用现有模块)
        if self.qc and deliverable_context:
            try:
                qc_processed = self.qc.process_results(deduplicated, deliverable_context=deliverable_context)
            except Exception as e:
                logger.warning(f"质量控制失败: {e}, 使用原始结果")
                qc_processed = deduplicated
        else:
            qc_processed = deduplicated

        # 3. 可信度评分
        final_docs = self._add_credibility_scores(qc_processed)

        logger.debug(f"Stage 5: 后处理完成, 最终文档数: {len(final_docs)}")

        return final_docs

    def _deduplicate(self, docs: List[Dict]) -> List[Dict]:
        """去重: 合并高度相似的文档块 (基于简单的 Jaccard 相似度)"""
        if len(docs) <= 1:
            return docs

        unique_docs = []
        seen_indices = set()

        for i, doc in enumerate(docs):
            if i in seen_indices:
                continue

            # 检查与后续文档的相似度
            for j in range(i + 1, len(docs)):
                if j in seen_indices:
                    continue

                similarity = self._text_similarity(doc["content"], docs[j]["content"])

                if similarity > self.dedup_threshold:
                    # 合并: 保留分数更高的
                    if docs[j].get("final_score", 0) > doc.get("final_score", 0):
                        doc = docs[j]
                    seen_indices.add(j)

            unique_docs.append(doc)

        logger.debug(f"去重: {len(docs)} → {len(unique_docs)} (合并 {len(docs) - len(unique_docs)} 个重复)")

        return unique_docs

    def _text_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算 (Jaccard)"""
        words1 = set(jieba.cut(text1))
        words2 = set(jieba.cut(text2))
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0

    def _add_credibility_scores(self, docs: List[Dict]) -> List[Dict]:
        """添加可信度评分"""
        for doc in docs:
            credibility = 0.0

            # 因素 1: 来源类型 (规范 > 案例 > 通用)
            type_scores = {"设计规范": 1.0, "案例库": 0.8, "技术知识": 0.7}
            credibility += type_scores.get(doc["metadata"].get("document_type"), 0.5) * 0.3

            # 因素 2: 检索分数
            credibility += min(doc.get("final_score", 0) / 10, 1.0) * 0.5

            # 因素 3: 文档完整性 (长度)
            content_length = len(doc.get("content", ""))
            credibility += min(content_length / 1000, 1.0) * 0.2

            doc["credibility_score"] = round(credibility, 2)

        return docs


# ==================== Stage 6: 结果组装与监控 ====================
class OutputFormatter:
    """
    输出格式化器 - Pipeline 第六阶段

    功能:
    - 格式化为 LangChain 兼容的输出
    - 添加引用编号
    - 记录监控指标
    """

    def format(self, processed_docs: List[Dict], query_info: Dict, metrics: Dict) -> Dict[str, Any]:
        """
        格式化最终输出

        Returns:
            完全兼容 ragflow_kb.py 的输出格式
        """
        # 1. 添加引用编号
        for idx, doc in enumerate(processed_docs, start=1):
            doc["reference_number"] = idx

        # 2. 组装输出 (兼容现有接口)
        output = {
            "success": True,
            "query": query_info["original_query"],
            "results": [
                {
                    "title": doc["title"],
                    "content": doc["content"],
                    "snippet": doc["content"][:300],
                    "url": None,  # 内部知识库无 URL
                    "relevance_score": doc.get("final_score", doc.get("vector_score", 0)),
                    "similarity_score": doc.get("final_score", doc.get("vector_score", 0)),  # 兼容旧字段
                    "reference_number": doc["reference_number"],
                    "credibility_score": doc.get("credibility_score", 0.8),
                    "source": "milvus",
                    "metadata": doc["metadata"],
                }
                for doc in processed_docs
            ],
            "total_results": len(processed_docs),
            "execution_time": metrics.get("total_time", 0),
            "quality_controlled": True,
            # Pipeline 特有字段
            "pipeline_metrics": {
                "query_processing_time": metrics.get("stage1_time", 0),
                "retrieval_time": metrics.get("stage2_time", 0),
                "reranking_time": metrics.get("stage4_time", 0),
                "candidates_count": metrics.get("candidates_count", 0),
                "filtered_count": metrics.get("filtered_count", 0),
            },
        }

        #  v7.164: 为搜索结果添加唯一ID
        if add_ids_to_search_results and output["results"]:
            output["results"] = add_ids_to_search_results(output["results"], source_tool="milvus")

        # 3. 记录监控指标
        self._log_metrics(output, metrics)

        return output

    def _log_metrics(self, output: Dict, metrics: Dict):
        """记录监控指标"""
        logger.info(
            f"Pipeline完成: 查询='{output['query']}', "
            f"结果数={output['total_results']}, "
            f"总耗时={output['execution_time']:.3f}s"
        )
        logger.debug(f"Pipeline 详细指标: {json.dumps(metrics, indent=2, ensure_ascii=False)}")


# ==================== 主工具类 ====================
class MilvusKBTool:
    """
    Milvus 知识库工具 - 带完整 6 阶段 Pipeline

    提供:
    - search_knowledge() - 通用知识搜索
    - search_for_deliverable() - 交付物精准搜索
    - to_langchain_tool() - LangChain 工具包装
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        collection_name: str = "design_knowledge_base",
        embedding_model_name: str = "BAAI/bge-m3",
        reranker_model_name: str = "BAAI/bge-reranker-v2-m3",
        config: Optional[ToolConfig] = None,
    ):
        """
        初始化 Milvus 知识库工具

        Args:
            host: Milvus 服务器地址
            port: Milvus 端口
            collection_name: Collection 名称
            embedding_model_name: Embedding 模型名称
            reranker_model_name: Reranker 模型名称
            config: 工具配置
        """
        self.config = config or ToolConfig(name="milvus_kb")
        self.name = self.config.name

        # 连接状态
        self.is_connected = False
        self.is_placeholder = False

        if not MILVUS_AVAILABLE:
            logger.error("Milvus 未安装, 工具将以占位符模式运行")
            self.is_placeholder = True
            return

        # 连接 Milvus
        try:
            connections.connect(host=host, port=port, timeout=10)
            logger.info(f"Milvus 连接成功: {host}:{port}")

            # 检查 collection 是否存在
            if utility.has_collection(collection_name):
                self.collection = Collection(collection_name)
                self.collection.load()
                logger.info(f"Collection '{collection_name}' 加载成功")
                self.is_connected = True
            else:
                logger.warning(f"Collection '{collection_name}' 不存在, 将以占位符模式运行")
                self.is_placeholder = True
                self.collection = None

        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}, 将以占位符模式运行")
            self.is_placeholder = True
            self.collection = None

        # 加载模型
        if not self.is_placeholder:
            try:
                logger.info(f"加载 Embedding 模型: {embedding_model_name}")
                self.embedding_model = SentenceTransformer(embedding_model_name)
                logger.info("Embedding 模型加载成功")
            except Exception as e:
                logger.error(f"Embedding 模型加载失败: {e}")
                self.is_placeholder = True
                return

        # 初始化 Pipeline 组件
        if not self.is_placeholder:
            self.query_processor = QueryProcessor()
            self.hybrid_retriever = HybridRetriever(self.collection, self.embedding_model)
            self.coarse_ranker = CoarseRanker(similarity_threshold=0.6)
            self.reranker = CrossEncoderReranker(model_name=reranker_model_name)
            self.post_processor = PostProcessor(
                qc_module=SearchQualityControl() if SearchQualityControl else None, dedup_threshold=0.95
            )
            self.output_formatter = OutputFormatter()

            # 复用现有模块
            self.query_builder = DeliverableQueryBuilder() if DeliverableQueryBuilder else None

            logger.info("Milvus KB Tool 初始化完成 (6-Stage Pipeline)")

    def search_knowledge(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        max_results: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        user_id: Optional[str] = None,  #  v7.141: 用户ID（用于过滤私有知识库）
        search_scope: str = "all",  #  v7.141: 搜索范围 ("all" | "system" | "user" | "team")
        team_id: Optional[str] = None,  #  v7.141.2: 团队ID（用于团队知识库）
        **kwargs,
    ) -> Dict[str, Any]:
        """
        在知识库中搜索相关内容

        Args:
            query: 搜索查询字符串
            knowledge_base_id: 知识库 ID (Milvus 中为 collection_name, 通常不需要)
            max_results: 最大结果数量
            similarity_threshold: 相似度阈值
            user_id: 用户ID（用于过滤私有知识库） v7.141
            search_scope: 搜索范围 ("all"=公共+私有+共享+团队 | "system"=仅公共 | "user"=仅私有 | "team"=仅团队)  v7.141/v7.141.2
            team_id: 团队ID（用于团队知识库） v7.141.2
            **kwargs: 其他参数

        Returns:
            搜索结果字典
        """
        if self.is_placeholder:
            return self._placeholder_response(query)

        max_results = max_results or 10
        metrics = {}
        total_start = time.time()

        try:
            #  v7.141: 添加用户隔离参数到 context
            #  v7.141.2: 添加团队知识库参数
            context = kwargs.get("context", {})
            context["user_id"] = user_id
            context["team_id"] = team_id  #  v7.141.2
            context["search_scope"] = search_scope

            # Stage 1: 查询理解
            t1 = time.time()
            processed_query = self.query_processor.process(query, context=context)
            metrics["stage1_time"] = time.time() - t1

            # Stage 2: 混合检索
            t2 = time.time()
            candidates = self.hybrid_retriever.retrieve(processed_query, top_k=max_results * 5)
            metrics["stage2_time"] = time.time() - t2
            metrics["candidates_count"] = len(candidates)

            # Stage 3: 粗排
            t3 = time.time()
            coarse_ranked = self.coarse_ranker.rank(candidates)
            metrics["stage3_time"] = time.time() - t3

            # Stage 4: 重排序
            t4 = time.time()
            reranked = self.reranker.rerank(processed_query["expanded_query"], coarse_ranked, top_k=max_results * 2)
            metrics["stage4_time"] = time.time() - t4

            # Stage 5: 后处理
            t5 = time.time()
            final_docs = self.post_processor.process(reranked, deliverable_context=kwargs.get("deliverable_context"))[
                :max_results
            ]
            metrics["stage5_time"] = time.time() - t5
            metrics["filtered_count"] = len(final_docs)

            # Stage 6: 格式化输出
            metrics["total_time"] = time.time() - total_start
            output = self.output_formatter.format(final_docs, query_info=processed_query, metrics=metrics)

            return output

        except Exception as e:
            logger.error(f"Milvus 搜索失败: {e}")
            return {"success": False, "error": str(e), "query": query, "results": []}

    def search_for_deliverable(
        self, deliverable: Dict, project_type: str = "", max_results: int = 10, **kwargs
    ) -> Dict[str, Any]:
        """
        交付物精准搜索 - 完整 Pipeline 执行

        Args:
            deliverable: 交付物信息 (包含 name, description 等)
            project_type: 项目类型
            max_results: 最大结果数

        Returns:
            搜索结果
        """
        if self.is_placeholder:
            return self._placeholder_response(deliverable.get("name", ""))

        # 使用 DeliverableQueryBuilder 构建精准查询
        if self.query_builder:
            queries = self.query_builder.build_multi_tool_queries(deliverable, project_type)
            base_query = queries.get("milvus", deliverable.get("name", ""))
        else:
            base_query = deliverable.get("name", "")

        # 执行搜索, 传入 deliverable 上下文
        return self.search_knowledge(
            query=base_query,
            max_results=max_results,
            context={"deliverable": deliverable, "project_type": project_type},
            deliverable_context=deliverable,
        )

    def _placeholder_response(self, query: str) -> Dict[str, Any]:
        """占位符响应 (Milvus 未连接时)"""
        logger.warning(f"️ [Milvus] Placeholder mode - 返回模拟结果: {query}")
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "title": "示例文档 1 (Placeholder)",
                    "content": f"这是关于 '{query}' 的示例内容。Milvus 知识库当前未连接。",
                    "snippet": f"关于 '{query}' 的示例内容...",
                    "url": None,
                    "relevance_score": 0.85,
                    "similarity_score": 0.85,
                    "reference_number": 1,
                    "credibility_score": 0.7,
                    "source": "milvus_placeholder",
                    "metadata": {"document_type": "示例", "tags": [], "project_type": "", "source_file": "placeholder"},
                }
            ],
            "total_results": 1,
            "execution_time": 0.01,
            "quality_controlled": False,
        }

    def to_langchain_tool(self):
        """
        将 MilvusKBTool 转换为 LangChain StructuredTool

        Returns:
            StructuredTool instance compatible with bind_tools()
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, returning self")
            return self

        # 定义输入 schema
        class MilvusSearchInput(BaseModel):
            query: str = Field(description="知识库搜索查询字符串")

        def milvus_search_func(query: str) -> str:
            """在 Milvus 知识库中搜索相关内容 (6-Stage Deep Pipeline)"""
            result = self.search_knowledge(query)
            if not result.get("success", False):
                return f"搜索失败: {result.get('error', 'Unknown error')}"

            results = result.get("results", [])
            if not results:
                return "未找到相关结果"

            # 格式化输出
            output = f"Milvus 知识库搜索结果 (关键词: {query}):\n\n"
            for i, item in enumerate(results, 1):
                output += f"{i}. {item.get('title', '无标题')}\n"
                output += f"   内容: {item.get('content', '无内容')[:200]}...\n"
                output += f"   相似度: {item.get('relevance_score', 0):.2f}\n"
                output += f"   可信度: {item.get('credibility_score', 0):.2f}\n\n"

            return output

        # 创建 LangChain StructuredTool
        tool = StructuredTool(
            name="milvus_kb_search",
            description="在 Milvus 向量数据库知识库中搜索相关设计规范、案例和技术知识。"
            "使用深度定制的 6 阶段 RAG Pipeline (查询理解→混合检索→粗排→重排序→质量控制→输出)，"
            "提供高质量的知识检索结果。适用于设计咨询、规范查询、案例参考等场景。",
            func=milvus_search_func,
            args_schema=MilvusSearchInput,
        )

        logger.debug("MilvusKBTool 已包装为 LangChain StructuredTool")
        return tool

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if self.is_placeholder:
            return {"status": "placeholder", "message": "Milvus 未连接"}

        try:
            # 检查连接
            connections.list_connections()
            # 检查 collection
            if self.collection:
                num_entities = self.collection.num_entities
                return {"status": "healthy", "collection": self.collection.name, "num_entities": num_entities}
            else:
                return {"status": "degraded", "message": "Collection 未加载"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
