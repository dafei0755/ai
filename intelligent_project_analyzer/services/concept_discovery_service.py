"""
LLM概念发现服务

ℹ️ NOTE (v9.1): 该组件是独立的 taxonomy 子系统服务，
非 P1 需求分析子组件。由 taxonomy 管理端独立调用。

自动从用户输入中提取、聚类和命名新的设计概念。
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from openai import AsyncOpenAI
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from ..models.taxonomy_models import (
    TaxonomyConceptDiscovery,
    TaxonomyEmergingType,
)
from ..settings import settings


class ConceptDiscoveryService:
    """概念发现服务 - 使用LLM自动发现新兴设计概念"""

    def __init__(self, database_url: str = None):
        """初始化服务"""
        if database_url is None:
            import os

            database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/project_analyzer")

        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # v9.2 fix: 自动创建缺失的 taxonomy 表（避免 'no such table' 错误）
        try:
            from ..models.taxonomy_models import Base as TaxonomyBase

            TaxonomyBase.metadata.create_all(self.engine, checkfirst=True)
        except Exception as e:
            logger.warning(f"⚠️ 自动创建 taxonomy 表失败（可忽略）: {e}")

        # 初始化OpenAI兼容客户端（支持DeepSeek/OpenRouter等）
        client_kwargs = {"api_key": settings.llm.api_key}
        if settings.llm.api_base:
            client_kwargs["base_url"] = settings.llm.api_base
        self.client = AsyncOpenAI(**client_kwargs)

        # Track 1: 用户需求维度（9个维度）
        self.user_demand_dimensions = [
            "motivation",  # 设计动机
            "space",  # 空间类型
            "target_user",  # 目标用户
            "style",  # 风格偏好
            "emotion",  # 情感诉求
            "method",  # 设计方法
            "constraint",  # 约束条件
            "reference",  # 参考灵感
            "locality",  # 地域性
        ]

        # Track 2: 研究任务维度（6个维度）- v7.501新增
        self.research_dimensions = [
            "case_study",  # 案例研究
            "contextual_research",  # 在地调研
            "style_analysis",  # 风格分析
            "business_model",  # 商业模式
            "concept_design",  # 概念设计
            "positioning",  # 定位策略
        ]

        # 向后兼容：保留 self.dimensions 指向用户需求维度
        self.dimensions = self.user_demand_dimensions

        logger.info(" 概念发现服务已初始化（双轨分类系统 v7.501）")

    def _identify_task_type(self, user_input: str) -> str:
        """
        识别任务类型（用户需求 vs 研究任务）

        Args:
            user_input: 用户输入文本

        Returns:
            "research" 或 "user_demand"
        """
        # 研究类关键词
        research_keywords = ["搜索", "调研", "分析", "研究", "查找", "梳理", "验证", "对比", "探索", "收集", "考察", "了解", "学习"]

        # 用户需求类关键词
        demand_keywords = ["我想要", "我需要", "设计一个", "希望", "打造", "营造", "氛围", "感觉", "风格", "空间", "家"]

        research_score = sum(1 for kw in research_keywords if kw in user_input)
        demand_score = sum(1 for kw in demand_keywords if kw in user_input)

        task_type = "research" if research_score > demand_score else "user_demand"
        logger.debug(f" 任务类型识别: {task_type} (研究={research_score}, 需求={demand_score})")

        return task_type

    def _build_extraction_prompt(self, user_input: str, task_type: str, dimensions: List[str]) -> str:
        """
        构建概念提取prompt（根据任务类型）

        Args:
            user_input: 用户输入
            task_type: 任务类型
            dimensions: 维度列表

        Returns:
            prompt文本
        """
        if task_type == "research":
            dimension_descriptions = """1. **case_study**: 案例研究（设计大师作品、行业标杆、成功项目）
2. **contextual_research**: 在地调研（当地文化、自然资源、场地特征）
3. **style_analysis**: 风格分析（风格对比、融合策略、美学特征）
4. **business_model**: 商业模式（经济可行性、运营逻辑、收入模式）
5. **concept_design**: 概念设计（设计框架、空间策略、方案构建）
6. **positioning**: 定位策略（文化定位、品牌策略、价值主张）"""

            task_label = "研究任务"
        else:
            dimension_descriptions = """1. **motivation**: 设计动机（为什么要设计？功能需求、生活方式改变等）
2. **space**: 空间类型（什么空间？住宅、办公、商业等）
3. **target_user**: 目标用户（为谁设计？年龄、职业、生活方式等）
4. **style**: 风格偏好（什么风格？现代、传统、混搭等，包括新兴小众风格）
5. **emotion**: 情感诉求（想要什么感觉？温馨、冷静、活力、松弛感等）
6. **method**: 设计方法（用什么手法？极简、装饰、模块化等）
7. **constraint**: 约束条件（有什么限制？预算、空间、时间等）
8. **reference**: 参考灵感（参考什么？自然、城市、艺术作品等）
9. **locality**: 地域性（什么地域特征？文化、气候、习俗等）"""

            task_label = "用户需求"

        return f"""你是一个室内设计{task_type}分析专家。请从以下{task_label}中提取所有相关的关键维度。

{task_label}：
```
{user_input}
```

请提取以下类型的维度：
{dimension_descriptions}

请以JSON格式输出，每个概念包含：
- dimension: 所属维度（使用上述维度的英文名，如 case_study, motivation 等）
- concept: 概念名称（简短、准确的中文描述）
- keywords: 关键词列表（3-5个中文关键词）
- confidence: 置信度（0.0-1.0，表示该维度与输入的匹配程度）
- description: 简短描述（10-20字）

只返回JSON数组，不要其他文字。示例格式：
[
  {{
    "dimension": "case_study",
    "concept": "设计大师案例",
    "keywords": ["安藤忠雄", "隈研吾", "民宿设计"],
    "confidence": 0.9,
    "description": "研究国际设计大师的民宿作品"
  }}
]"""

    async def extract_concepts_from_text(self, user_input: str, session_id: str) -> List[Dict[str, Any]]:
        """
        从用户输入中提取设计概念（双轨分类系统 v7.501）

        Args:
            user_input: 用户输入文本
            session_id: 会话ID（用于追踪）

        Returns:
            提取的概念列表
        """
        logger.info(f" 开始从文本中提取概念: session={session_id}")

        # Step 1: 识别任务类型
        task_type = self._identify_task_type(user_input)
        logger.info(f" 任务类型: {task_type}")

        # Step 2: 选择维度体系
        dimensions = self.research_dimensions if task_type == "research" else self.user_demand_dimensions
        logger.info(f" 使用维度数: {len(dimensions)}")

        # Step 3: 构建prompt
        prompt = self._build_extraction_prompt(user_input, task_type, dimensions)

        # Step 4: 调用LLM
        try:
            response = await self.client.chat.completions.create(
                model=settings.llm.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content.strip()

            # 尝试解析JSON
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            concepts = json.loads(content.strip())

            logger.info(f" 提取到 {len(concepts)} 个概念 (任务类型: {task_type})")
            return concepts

        except Exception as e:
            logger.error(f" 概念提取失败: {e}")
            return []

    def cluster_similar_concepts(self, concepts: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        聚类相似概念（基于关键词重叠）

        Args:
            concepts: 概念列表
            threshold: 相似度阈值

        Returns:
            聚类后的概念簇
        """
        logger.info(f" 开始聚类 {len(concepts)} 个概念")

        # 按维度分组
        by_dimension = defaultdict(list)
        for concept in concepts:
            by_dimension[concept["dimension"]].append(concept)

        clusters = []

        for dimension, dim_concepts in by_dimension.items():
            # 简单的关键词重叠聚类
            used = set()

            for i, concept in enumerate(dim_concepts):
                if i in used:
                    continue

                # 创建新簇
                cluster = {
                    "dimension": dimension,
                    "cluster_name": concept["concept"],
                    "keywords": set(concept.get("keywords", [])),
                    "concepts": [concept],
                    "confidence": concept.get("confidence", 0.5),
                }

                # 查找相似概念
                for j, other in enumerate(dim_concepts):
                    if j <= i or j in used:
                        continue

                    other_keywords = set(other.get("keywords", []))
                    overlap = len(cluster["keywords"] & other_keywords)
                    min_size = min(len(cluster["keywords"]), len(other_keywords))

                    if min_size > 0 and overlap / min_size >= threshold:
                        cluster["concepts"].append(other)
                        cluster["keywords"].update(other_keywords)
                        cluster["confidence"] = max(cluster["confidence"], other.get("confidence", 0.5))
                        used.add(j)

                # 转换keywords为列表
                cluster["keywords"] = list(cluster["keywords"])
                clusters.append(cluster)
                used.add(i)

        logger.info(f" 聚类完成，生成 {len(clusters)} 个概念簇")
        return clusters

    async def generate_type_id(self, label_zh: str) -> str:
        """
        为中文标签生成英文type_id（snake_case）

        Args:
            label_zh: 中文标签

        Returns:
            英文type_id
        """
        prompt = f"""请将以下中文设计概念翻译为简洁的英文短语（2-4个单词），并转换为snake_case格式。

中文概念：{label_zh}

只输出snake_case格式的英文，不要有其他文字。例如：
- 松弛感 → relaxed_living
- 后工业风 → post_industrial
- 极简主义 → minimalism"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.llm.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=50,
            )

            type_id = response.choices[0].message.content.strip().lower()
            # 清理可能的多余字符
            type_id = "".join(c if c.isalnum() or c == "_" else "" for c in type_id)

            return type_id

        except Exception as e:
            logger.error(f" type_id生成失败: {e}")
            # 备用方案：使用拼音或简单转换
            return label_zh.replace(" ", "_").lower()[:50]

    async def save_discoveries(
        self, clusters: List[Dict[str, Any]], session_id: str, task_type: str = "user_demand"
    ) -> int:
        """
        保存发现的概念到数据库

        Args:
            clusters: 概念簇列表
            session_id: 会话ID
            task_type: 任务类型（user_demand | research）- v7.501新增

        Returns:
            保存的记录数
        """
        logger.info(f" 开始保存 {len(clusters)} 个概念发现 (任务类型: {task_type})")

        db = self.SessionLocal()
        saved_count = 0

        try:
            for cluster in clusters:
                cluster_name = cluster["cluster_name"]
                dimension = cluster["dimension"]

                # 检查是否已存在
                existing = db.query(TaxonomyConceptDiscovery).filter_by(concept_cluster=cluster_name).first()

                if existing:
                    # 更新出现次数
                    existing.occurrence_count += 1
                    existing.last_seen_at = datetime.now()
                    existing.confidence = max(existing.confidence, cluster["confidence"])
                    logger.info(f"   更新已有概念: {cluster_name}")
                else:
                    # 创建新记录（v7.501: 添加task_type）
                    discovery = TaxonomyConceptDiscovery(
                        concept_cluster=cluster_name,
                        keywords=json.dumps(cluster["keywords"], ensure_ascii=False),
                        sample_inputs=json.dumps(
                            [c["description"] for c in cluster["concepts"]],
                            ensure_ascii=False,
                        ),
                        occurrence_count=1,
                        confidence=cluster["confidence"],
                        suggested_dimension=dimension,
                        suggested_type_id=await self.generate_type_id(cluster_name),
                        task_type=task_type,  # v7.501新增
                        discovered_at=datetime.now(),
                        last_seen_at=datetime.now(),
                    )
                    db.add(discovery)
                    saved_count += 1
                    logger.info(f"   新增概念发现: {cluster_name}")

            db.commit()
            logger.info(f" 保存完成: 新增{saved_count}个, 更新{len(clusters)-saved_count}个")

            return saved_count

        except Exception as e:
            db.rollback()
            logger.error(f" 保存失败: {e}")
            return 0

        finally:
            db.close()

    async def promote_to_emerging(self, min_occurrence: int = 3, min_confidence: float = 0.6) -> int:
        """
        将高频概念晋升为新兴标签

        Args:
            min_occurrence: 最小出现次数
            min_confidence: 最小置信度

        Returns:
            晋升的标签数
        """
        logger.info(f"⬆️ 检查概念晋升: 出现>={min_occurrence}, 置信度>={min_confidence}")

        db = self.SessionLocal()
        promoted_count = 0

        try:
            # 查找符合条件的概念
            candidates = (
                db.query(TaxonomyConceptDiscovery)
                .filter(
                    TaxonomyConceptDiscovery.occurrence_count >= min_occurrence,
                    TaxonomyConceptDiscovery.confidence >= min_confidence,
                    TaxonomyConceptDiscovery.suggested_dimension.isnot(None),
                )
                .all()
            )

            for discovery in candidates:
                # 检查是否已经晋升
                existing = (
                    db.query(TaxonomyEmergingType)
                    .filter_by(
                        dimension=discovery.suggested_dimension,
                        type_id=discovery.suggested_type_id,
                    )
                    .first()
                )

                if existing:
                    continue

                # 创建新兴标签（v7.501: 添加task_type）
                emerging = TaxonomyEmergingType(
                    dimension=discovery.suggested_dimension,
                    type_id=discovery.suggested_type_id,
                    label_zh=discovery.concept_cluster,
                    label_en=discovery.suggested_type_id.replace("_", " ").title(),
                    keywords=discovery.keywords,
                    case_count=discovery.occurrence_count,
                    success_count=int(discovery.occurrence_count * 0.8),  # 假设80%成功率
                    source="llm_discover",
                    confidence_score=discovery.confidence,
                    task_type=discovery.task_type,  # v7.501新增: 继承task_type
                    created_at=datetime.now(),
                    last_used_at=discovery.last_seen_at,
                )
                db.add(emerging)
                promoted_count += 1

                logger.info(f"  ⬆️ 晋升为新兴标签: {discovery.concept_cluster}")

            db.commit()
            logger.info(f" 晋升完成: {promoted_count} 个新兴标签")

            return promoted_count

        except Exception as e:
            db.rollback()
            logger.error(f" 晋升失败: {e}")
            return 0

        finally:
            db.close()

    async def analyze_session(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """
        分析单个会话的概念（双轨分类系统 v7.501）

        Args:
            session_id: 会话ID
            user_input: 用户输入

        Returns:
            分析结果
        """
        logger.info(f" 开始分析会话: {session_id}")

        # 0. 识别任务类型（v7.501新增）
        task_type = self._identify_task_type(user_input)
        logger.info(f" 任务类型: {task_type}")

        # 1. 提取概念
        concepts = await self.extract_concepts_from_text(user_input, session_id)

        if not concepts:
            return {"status": "no_concepts", "task_type": task_type, "concepts": [], "clusters": []}  # v7.501新增

        # 2. 聚类
        clusters = self.cluster_similar_concepts(concepts)

        # 3. 保存发现（v7.501: 传递task_type）
        saved_count = await self.save_discoveries(clusters, session_id, task_type)

        # 4. 检查晋升
        promoted_count = await self.promote_to_emerging()

        return {
            "status": "success",
            "session_id": session_id,
            "task_type": task_type,  # v7.501新增
            "concepts_extracted": len(concepts),
            "clusters_created": len(clusters),
            "discoveries_saved": saved_count,
            "promoted_to_emerging": promoted_count,
            "clusters": clusters,
        }

    def get_discovery_statistics(self) -> Dict[str, Any]:
        """获取概念发现统计信息"""
        db = self.SessionLocal()

        try:
            total_discoveries = db.query(TaxonomyConceptDiscovery).count()
            high_confidence = (
                db.query(TaxonomyConceptDiscovery).filter(TaxonomyConceptDiscovery.confidence >= 0.7).count()
            )

            # 最近7天的发现
            week_ago = datetime.now() - timedelta(days=7)
            recent_discoveries = (
                db.query(TaxonomyConceptDiscovery).filter(TaxonomyConceptDiscovery.discovered_at >= week_ago).count()
            )

            # 按维度统计
            by_dimension = (
                db.query(
                    TaxonomyConceptDiscovery.suggested_dimension,
                    func.count(TaxonomyConceptDiscovery.id),
                )
                .group_by(TaxonomyConceptDiscovery.suggested_dimension)
                .all()
            )

            return {
                "total_discoveries": total_discoveries,
                "high_confidence_count": high_confidence,
                "recent_7d": recent_discoveries,
                "by_dimension": {dim: count for dim, count in by_dimension if dim},
            }

        finally:
            db.close()
