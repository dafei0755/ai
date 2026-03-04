"""
Deliverable Query Builder (v7.170)

从交付物规格（name + description）构建精准搜索查询，避免泛泛而谈的通用搜索

v7.170 新增：
- 多模式搜索词生成（概念+领域+关系词+时间+类型）
- 渐进式搜索词生成（用于5轮搜索编排）
- 内容类型词和时间限定词
"""

import re
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

try:
    import jieba
    import jieba.analyse
except ImportError:
    logger.warning("jieba not installed. Please install with: pip install jieba")
    jieba = None


class DeliverableQueryBuilder:
    """
    交付物查询构建器

    核心功能：
    1. 从交付物的name和description中提取关键词
    2. 将交付物格式映射到搜索术语（如"persona" → "user persona methodology"）
    3. 结合项目类型添加上下文
    4. 生成针对性强的搜索查询
    """

    #  交付物格式 → 搜索术语映射表 (v7.65扩展: 30种→50+种)
    FORMAT_SEARCH_TERMS = {
        # === 设计类 ===
        "design": "design methodology",
        "concept": "concept design approach",
        "blueprint": "design blueprint standards",
        "diagram": "design diagram techniques",
        "spatial_design": "spatial planning methods",
        "moodboard": "mood board design inspiration techniques",
        "stylescape": "style scape visual direction",
        "colorpalette": "color palette theory application",
        "material_board": "material selection board methods",
        "floorplan": "floor plan design standards",
        "elevation": "elevation drawing techniques",
        "section": "section drawing methods",
        # === 分析类 ===
        "analysis": "analysis framework",
        "evaluation": "evaluation criteria",
        "assessment": "assessment methodology",
        "audit": "audit checklist",
        "benchmark": "benchmarking best practices",
        "research": "research methodology",
        "insight": "insight discovery methods",
        "swot": "SWOT analysis framework",
        "gap_analysis": "gap analysis techniques",
        "competitor_analysis": "competitive analysis methods",
        "market_research": "market research methodology",
        "trend_analysis": "trend analysis forecasting",  #  require_search=true
        # === 策略类 ===
        "strategy": "strategic planning",
        "plan": "planning framework",
        "roadmap": "implementation roadmap",
        "framework": "framework design",
        "model": "modeling approach",
        "positioning": "brand positioning strategy",
        "value_proposition": "value proposition design",
        # === 用户体验类 ===
        "persona": "user persona design methodology",
        "journey_map": "customer journey mapping techniques",
        "experience_map": "experience mapping methods",
        "scenario": "scenario design framework",
        "wireframe": "wireframe design best practices",
        "prototype": "prototyping methods",
        "storyboard": "storyboard visualization techniques",
        "empathy_map": "empathy mapping methods",
        "service_blueprint": "service blueprint design",
        "touchpoint_map": "touchpoint mapping methods",
        # === 文档类 ===
        "report": "report structure",
        "proposal": "proposal writing",
        "presentation": "presentation design",
        "guideline": "guideline development",
        "manual": "manual documentation",
        "checklist": "checklist design",
        "specification": "specification writing standards",
        "whitepaper": "white paper methodology",
        # === 案例与资料库 ===  #  require_search=true
        "case_study": "case study analysis methodology",
        "case_library": "design case studies best practices",
        "best_practices": "industry best practices examples",
        "reference_library": "design reference library",
        "precedent_study": "precedent analysis methods",
        # === 其他 ===
        "recommendation": "recommendation framework",
        "summary": "summary techniques",
        "narrative": "narrative design",
        "materials_list": "materials specification",
        "budget": "budget planning methods",
        "timeline": "project timeline planning",
        "kpi": "KPI definition measurement",
    }

    #  项目类型 → 上下文术语
    PROJECT_TYPE_CONTEXT = {
        "interior_design": "interior design",
        "commercial_space": "commercial space design",
        "residential": "residential design",
        "hospitality": "hospitality design",
        "retail": "retail space design",
        "office": "office design",
        "restaurant": "restaurant design",
        "branding": "branding design",
        "product_design": "product design",
        "urban_planning": "urban planning",
    }

    def __init__(self, enable_jieba: bool = True):
        """
        初始化查询构建器

        Args:
            enable_jieba: 是否启用jieba分词（中文关键词提取）
        """
        self.enable_jieba = enable_jieba and jieba is not None

        if self.enable_jieba:
            # 加载jieba词典（可选：添加自定义词汇）
            jieba.initialize()
            logger.info(" DeliverableQueryBuilder: jieba initialized")
        else:
            logger.warning("️ DeliverableQueryBuilder: jieba disabled")

    def build_query(self, deliverable: Dict[str, Any], project_type: str = "", agent_context: str = "") -> str:
        """
        从交付物构建精准搜索查询

        Args:
            deliverable: 交付物字典，包含name, description, format
            project_type: 项目类型（如"commercial_space"）
            agent_context: 智能体上下文（如"V4设计研究员"）

        Returns:
            精准的搜索查询字符串

        Example:
            Before: "用户画像"
            After: "user persona design methodology commercial space"
        """
        query_parts = []

        # 1. 提取交付物名称关键词（权重高，取top2）
        name = deliverable.get("name", "")
        if name:
            name_keywords = self._extract_keywords(name, topK=2)
            if name_keywords:
                query_parts.extend(name_keywords)
                logger.debug(f" Name keywords: {name_keywords}")

        # 2. 提取交付物描述关键词（权重中，取top5）
        description = deliverable.get("description", "")
        if description:
            desc_keywords = self._extract_keywords(description, topK=5)
            if desc_keywords:
                query_parts.extend(desc_keywords)
                logger.debug(f" Description keywords: {desc_keywords}")

        # 3. 添加格式对应的搜索术语（英文，提高国际搜索准确性）
        fmt = deliverable.get("format", "")
        if fmt and fmt in self.FORMAT_SEARCH_TERMS:
            format_term = self.FORMAT_SEARCH_TERMS[fmt]
            query_parts.append(format_term)
            logger.debug(f" Format term: {format_term}")

        # 4. 添加项目类型上下文
        if project_type and project_type in self.PROJECT_TYPE_CONTEXT:
            context_term = self.PROJECT_TYPE_CONTEXT[project_type]
            query_parts.append(context_term)
            logger.debug(f" Project context: {context_term}")

        # 5. 组合查询（去重）
        unique_parts = []
        seen = set()
        for part in query_parts:
            part_lower = part.lower()
            if part_lower not in seen:
                unique_parts.append(part)
                seen.add(part_lower)

        final_query = " ".join(unique_parts)
        logger.info(f" Built query for '{name}': {final_query}")

        return final_query

    def _extract_keywords(self, text: str, topK: int = 5) -> List[str]:
        """
        从文本中提取关键词

        Args:
            text: 输入文本
            topK: 返回前K个关键词

        Returns:
            关键词列表
        """
        if not text or not text.strip():
            return []

        # 中文文本使用jieba
        if self.enable_jieba and self._is_chinese_text(text):
            try:
                # 使用TF-IDF提取关键词
                keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=False)
                return keywords
            except Exception as e:
                logger.error(f" Jieba extraction failed: {e}")
                return self._simple_keyword_extraction(text, topK)
        else:
            # 英文或jieba不可用时使用简单分词
            return self._simple_keyword_extraction(text, topK)

    def _is_chinese_text(self, text: str) -> bool:
        """
        判断文本是否包含中文

        Args:
            text: 输入文本

        Returns:
            是否包含中文字符
        """
        chinese_pattern = re.compile(r"[\u4e00-\u9fff]+")
        return bool(chinese_pattern.search(text))

    def _simple_keyword_extraction(self, text: str, topK: int = 5) -> List[str]:
        """
        简单关键词提取（备用方法）

        策略：
        1. 分词（按空格和标点）
        2. 过滤停用词
        3. 按词频排序

        Args:
            text: 输入文本
            topK: 返回前K个关键词

        Returns:
            关键词列表
        """
        # 停用词列表（简化版）
        stopwords = {
            # 中文停用词
            "的",
            "了",
            "和",
            "是",
            "就",
            "都",
            "而",
            "及",
            "与",
            "或",
            "等",
            "对",
            "在",
            "有",
            "为",
            "以",
            "将",
            "并",
            "从",
            "按",
            "该",
            "此",
            # 英文停用词
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
        }

        # 分词：按空格和常见标点符号切分
        words = re.split(r"[\s,;，；、。！？]+", text.lower())

        # 过滤：去除停用词、空字符串、过短的词
        filtered = [w for w in words if w and len(w) >= 2 and w not in stopwords]

        # 统计词频
        word_freq = {}
        for word in filtered:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 排序并取topK
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        return [word for word, freq in sorted_words[:topK]]

    def build_multi_tool_queries(self, deliverable: Dict[str, Any], project_type: str = "") -> Dict[str, str]:
        """
        为不同搜索工具构建优化的查询

        不同工具的特点：
        - Tavily: 适合国际案例，使用英文关键词
        - Arxiv: 学术论文，强调方法论术语
        - Milvus: 内部知识库（v7.154 替代 RAGFlow），中文为主
        - Bocha: 中文搜索，本土案例

        Args:
            deliverable: 交付物字典
            project_type: 项目类型

        Returns:
            工具名称 → 查询字符串的映射
        """
        base_query = self.build_query(deliverable, project_type)

        # 为不同工具优化查询
        queries = {
            "tavily": base_query,  # 默认查询适用于Tavily
            "arxiv": self._build_arxiv_query(deliverable, base_query),
            "milvus": self._build_milvus_query(deliverable, base_query),  # v7.154: ragflow → milvus
            "bocha": self._build_bocha_query(deliverable, base_query),
        }

        return queries

    def _build_arxiv_query(self, deliverable: Dict[str, Any], base_query: str) -> str:
        """为Arxiv构建学术化查询"""
        # 添加方法论关键词
        methodology_terms = ["methodology", "framework", "approach", "model"]
        return f"{base_query} {methodology_terms[0]}"

    def _build_milvus_query(self, deliverable: Dict[str, Any], base_query: str) -> str:
        """v7.154: 为Milvus（内部知识库，替代RAGFlow）构建查询"""
        # 保留中文关键词为主
        name = deliverable.get("name", "")
        description = deliverable.get("description", "")
        chinese_text = name if self._is_chinese_text(name) else description
        if chinese_text:
            return chinese_text[:50]  # 保留原文前50字
        return base_query

    def _build_bocha_query(self, deliverable: Dict[str, Any], base_query: str) -> str:
        """为Bocha（中文搜索）构建查询"""
        # 同Milvus，优先使用中文
        return self._build_milvus_query(deliverable, base_query)


# ============================================================================
# 辅助函数：快速使用
# ============================================================================


def build_deliverable_query(deliverable: Dict[str, Any], project_type: str = "") -> str:
    """
    快速构建交付物搜索查询（单例模式）

    Args:
        deliverable: 交付物字典
        project_type: 项目类型

    Returns:
        搜索查询字符串
    """
    builder = DeliverableQueryBuilder()
    return builder.build_query(deliverable, project_type)


# ============================================================================
# v7.170 新增：多模式搜索词生成器
# ============================================================================


class AdvancedQueryBuilder:
    """
    多模式搜索词生成器 (v7.170)

    支持5种搜索词构建模式：
    1. 核心概念 + 领域 + 关系词：如 "农耕文化 对 室内设计 影响"
    2. 概念 + 概念 + 深化词：如 "天人合一 室内设计 农耕文化"
    3. 领域 + 时间限定：如 "智慧城市 室内设计 2025"
    4. 领域 + 内容类型：如 "城市化 对 室内设计 研究 论文"
    5. 融合视角：如 "城市农耕 室内设计 案例"
    """

    # 关系词
    RELATION_WORDS = ["对", "与", "影响", "关系", "作用", "应用"]

    # 深化词
    DEEPENING_WORDS = ["概念", "框架", "理论", "方法", "原则", "特点"]

    # 内容类型词
    CONTENT_TYPE_WORDS = {
        "academic": ["论文", "研究", "方法论", "理论", "综述", "学术"],
        "case": ["案例", "项目", "作品", "实践", "设计", "实例"],
        "data": ["数据", "统计", "报告", "趋势", "市场", "规模"],
        "news": ["新闻", "动态", "最新", "发布", "资讯"],
    }

    # 时间限定词
    TIME_WORDS = {
        "recent": ["2024", "2025", "最新", "近期", "当前"],
        "historical": ["历史", "传统", "演变", "发展", "起源"],
    }

    # 领域映射（中文）
    DOMAIN_MAPPING_CN = {
        "interior_design": "室内设计",
        "commercial_space": "商业空间设计",
        "residential": "住宅设计",
        "hospitality": "酒店民宿设计",
        "retail": "零售空间设计",
        "office": "办公空间设计",
        "restaurant": "餐饮空间设计",
        "urban_planning": "城市规划",
        "architecture": "建筑设计",
    }

    def __init__(self, enable_jieba: bool = True):
        """
        初始化多模式查询构建器

        Args:
            enable_jieba: 是否启用jieba分词
        """
        self.enable_jieba = enable_jieba and jieba is not None
        self.base_builder = DeliverableQueryBuilder(enable_jieba=enable_jieba)

        if self.enable_jieba:
            jieba.initialize()
            logger.info(" AdvancedQueryBuilder: jieba initialized")

    def extract_concepts(self, query: str, topK: int = 5) -> List[str]:
        """
        从查询中提取核心概念

        Args:
            query: 用户查询
            topK: 返回前K个概念

        Returns:
            核心概念列表
        """
        if not query:
            return []

        # 使用 jieba 提取关键词
        if self.enable_jieba and self._is_chinese_text(query):
            try:
                keywords = jieba.analyse.extract_tags(query, topK=topK, withWeight=False)
                return keywords
            except Exception as e:
                logger.warning(f"️ Jieba extraction failed: {e}")

        # 简单分词
        words = re.split(r"[，,。.、\s]+", query)
        return [w for w in words if len(w) >= 2][:topK]

    def _is_chinese_text(self, text: str) -> bool:
        """判断是否包含中文"""
        chinese_pattern = re.compile(r"[\u4e00-\u9fff]+")
        return bool(chinese_pattern.search(text))

    def build_multi_mode_queries(
        self, query: str, domain: str = "", modes: List[str] | None = None
    ) -> Dict[str, List[str]]:
        """
        生成多模式搜索词

        Args:
            query: 用户原始查询
            domain: 领域（如 "室内设计"）
            modes: 要使用的模式列表，默认全部

        Returns:
            模式名称 → 搜索词列表的映射
        """
        concepts = self.extract_concepts(query)
        domain_cn = self.DOMAIN_MAPPING_CN.get(domain, domain) or "设计"

        all_modes = modes or ["concept_domain", "concept_deepening", "time_limited", "content_type", "fusion"]
        results = {}

        for mode in all_modes:
            if mode == "concept_domain":
                results[mode] = self._build_concept_domain_queries(concepts, domain_cn)
            elif mode == "concept_deepening":
                results[mode] = self._build_concept_deepening_queries(concepts, domain_cn)
            elif mode == "time_limited":
                results[mode] = self._build_time_limited_queries(concepts, domain_cn)
            elif mode == "content_type":
                results[mode] = self._build_content_type_queries(concepts, domain_cn)
            elif mode == "fusion":
                results[mode] = self._build_fusion_queries(concepts, domain_cn)

        return results

    def _build_concept_domain_queries(self, concepts: List[str], domain: str) -> List[str]:
        """
        模式1：核心概念 + 领域 + 关系词

        示例：
        - "农耕文化 对 室内设计 影响"
        - "城市化 与 室内设计 关系"
        """
        queries = []
        for concept in concepts[:3]:
            for relation in self.RELATION_WORDS[:2]:
                query = f"{concept} {relation} {domain}"
                queries.append(query)
        return queries

    def _build_concept_deepening_queries(self, concepts: List[str], domain: str) -> List[str]:
        """
        模式2：概念 + 概念 + 深化词

        示例：
        - "天人合一 室内设计 概念"
        - "农耕文化 空间布局 框架"
        """
        queries = []
        for concept in concepts[:2]:
            for deepening in self.DEEPENING_WORDS[:2]:
                query = f"{concept} {domain} {deepening}"
                queries.append(query)
        return queries

    def _build_time_limited_queries(self, concepts: List[str], domain: str) -> List[str]:
        """
        模式3：领域 + 时间限定

        示例：
        - "智慧城市 室内设计 2025"
        - "室内设计 趋势 最新"
        """
        queries = []
        current_year = datetime.now().year

        for concept in concepts[:2]:
            # 添加年份
            queries.append(f"{concept} {domain} {current_year}")
            # 添加时间词
            for time_word in self.TIME_WORDS["recent"][:2]:
                queries.append(f"{concept} {domain} {time_word}")

        return queries

    def _build_content_type_queries(self, concepts: List[str], domain: str) -> List[str]:
        """
        模式4：领域 + 内容类型

        示例：
        - "城市化 对 室内设计 研究 论文"
        - "农耕文化 室内设计 案例"
        """
        queries = []
        for concept in concepts[:2]:
            for content_type, keywords in self.CONTENT_TYPE_WORDS.items():
                for keyword in keywords[:1]:  # 每种类型取1个关键词
                    query = f"{concept} {domain} {keyword}"
                    queries.append(query)
        return queries

    def _build_fusion_queries(self, concepts: List[str], domain: str) -> List[str]:
        """
        模式5：融合视角

        示例：
        - "城市农耕 室内设计 案例"
        - "传统与现代 室内设计 融合"
        """
        queries = []

        # 概念组合
        if len(concepts) >= 2:
            combined = f"{concepts[0]}与{concepts[1]}"
            queries.append(f"{combined} {domain}")
            queries.append(f"{combined} {domain} 融合")

        # 添加融合关键词
        fusion_keywords = ["融合", "结合", "创新", "转化"]
        for concept in concepts[:2]:
            for keyword in fusion_keywords[:2]:
                queries.append(f"{concept} {domain} {keyword}")

        return queries

    def build_progressive_queries(self, query: str, domain: str = "", round_type: str = "concepts") -> List[str]:
        """
        为渐进式搜索生成特定轮次的搜索词

        Args:
            query: 用户原始查询
            domain: 领域
            round_type: 轮次类型 (concepts, dimensions, academic, cases, data)

        Returns:
            搜索词列表
        """
        concepts = self.extract_concepts(query)
        domain_cn = self.DOMAIN_MAPPING_CN.get(domain, domain) or "设计"

        if round_type == "concepts":
            # 第1轮：基础概念探索
            return self._build_concept_domain_queries(concepts, domain_cn)

        elif round_type == "dimensions":
            # 第2轮：维度深化
            return self._build_concept_deepening_queries(concepts, domain_cn)

        elif round_type == "academic":
            # 第3轮：学术深度
            queries = []
            for concept in concepts[:2]:
                for keyword in self.CONTENT_TYPE_WORDS["academic"][:3]:
                    queries.append(f"{concept} {keyword}")
            return queries

        elif round_type == "cases":
            # 第4轮：实践案例
            queries = []
            for concept in concepts[:2]:
                for keyword in self.CONTENT_TYPE_WORDS["case"][:3]:
                    queries.append(f"{concept} {keyword}")
            return queries

        elif round_type == "data":
            # 第5轮：数据支撑
            queries = []
            current_year = datetime.now().year
            for concept in concepts[:2]:
                for keyword in self.CONTENT_TYPE_WORDS["data"][:2]:
                    queries.append(f"{concept} {keyword} {current_year}")
            return queries

        return []

    def build_all_queries(self, query: str, domain: str = "") -> List[str]:
        """
        生成所有模式的搜索词（去重）

        Args:
            query: 用户原始查询
            domain: 领域

        Returns:
            去重后的搜索词列表
        """
        all_queries = self.build_multi_mode_queries(query, domain)

        # 合并所有模式的查询
        combined = []
        for mode_queries in all_queries.values():
            combined.extend(mode_queries)

        # 去重
        seen = set()
        unique = []
        for q in combined:
            q_normalized = q.lower().strip()
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique.append(q)

        return unique


# 便捷函数
def build_advanced_queries(query: str, domain: str = "") -> List[str]:
    """
    快速生成多模式搜索词

    Args:
        query: 用户查询
        domain: 领域

    Returns:
        搜索词列表
    """
    builder = AdvancedQueryBuilder()
    return builder.build_all_queries(query, domain)


def build_progressive_queries(query: str, domain: str = "", round_type: str = "concepts") -> List[str]:
    """
    快速生成渐进式搜索词

    Args:
        query: 用户查询
        domain: 领域
        round_type: 轮次类型

    Returns:
        搜索词列表
    """
    builder = AdvancedQueryBuilder()
    return builder.build_progressive_queries(query, domain, round_type)


# ============================================================================
# v7.180 新增：JTBD导向查询构建器
# ============================================================================


class JTBDQueryBuilder:
    """
    基于JTBD（Jobs-To-Be-Done）构建搜索查询 (v7.180)

    从需求分析结果中提取：
    - L4 JTBD任务定义
    - L3 核心矛盾
    - 人性维度关键词

    生成针对性搜索词，提升搜索精准度和洞察力

    使用示例：
        builder = JTBDQueryBuilder()
        queries = builder.build_from_requirements(
            structured_requirements={
                "project_task": "为一位事业转型期的前金融律师，打造私人空间，雇佣空间完成'专业形象重塑'与'内在自我整合'两项任务",
                "core_tension": "作为[内容创作者]的[展示需求]与其对[精神庇护]的根本对立",
                "emotional_landscape": "从进门时的都市压力 → 玄关放下包袱的仪式感 → 客厅的社交安全感",
            },
            domain="室内设计"
        )
    """

    def __init__(self):
        """初始化JTBD查询构建器"""
        # 延迟导入以避免循环依赖
        try:
            from ..utils.insight_methodology import InsightMethodology

            self.methodology = InsightMethodology
        except ImportError:
            logger.warning("️ InsightMethodology not available, using fallback")
            self.methodology = None

        self.base_builder = DeliverableQueryBuilder()
        logger.info(" JTBDQueryBuilder initialized")

    def build_from_requirements(
        self, structured_requirements: Dict[str, Any], domain: str = ""
    ) -> Dict[str, List[str]]:
        """
        从需求分析结果构建多维度搜索词

        Args:
            structured_requirements: 结构化需求（来自需求分析师Phase2输出）
            domain: 领域（如 "室内设计"）

        Returns:
            {
                "jtbd_queries": [...],      # 基于JTBD的搜索词
                "tension_queries": [...],   # 基于核心矛盾的搜索词
                "human_queries": [...],     # 基于人性维度的搜索词
                "all_queries": [...],       # 所有搜索词（去重）
            }
        """
        queries = {
            "jtbd_queries": [],
            "tension_queries": [],
            "human_queries": [],
            "all_queries": [],
        }

        if not structured_requirements:
            logger.warning("️ No structured_requirements provided")
            return queries

        # 1. 从JTBD构建查询
        project_task = structured_requirements.get("project_task", "")
        if project_task:
            queries["jtbd_queries"] = self._build_jtbd_queries(project_task, domain)
            logger.debug(f" JTBD queries: {queries['jtbd_queries']}")

        # 2. 从核心矛盾构建查询
        core_tension = structured_requirements.get("core_tension", "")
        if not core_tension:
            # 尝试从 analysis_layers 中获取
            analysis_layers = structured_requirements.get("analysis_layers", {})
            core_tension = analysis_layers.get("L3_core_tension", "")

        if core_tension:
            queries["tension_queries"] = self._build_tension_queries(core_tension, domain)
            logger.debug(f" Tension queries: {queries['tension_queries']}")

        # 3. 从人性维度构建查询
        human_fields = [
            "emotional_landscape",
            "spiritual_aspirations",
            "psychological_safety_needs",
            "ritual_behaviors",
            "memory_anchors",
        ]
        human_text = " ".join(str(structured_requirements.get(field, "")) for field in human_fields)
        if human_text.strip():
            queries["human_queries"] = self._build_human_queries(human_text, domain)
            logger.debug(f" Human queries: {queries['human_queries']}")

        # 4. 合并所有查询（去重）
        all_queries = queries["jtbd_queries"] + queries["tension_queries"] + queries["human_queries"]
        seen = set()
        unique_queries = []
        for q in all_queries:
            q_normalized = q.lower().strip()
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique_queries.append(q)
        queries["all_queries"] = unique_queries

        logger.info(f" JTBDQueryBuilder: Generated {len(unique_queries)} unique queries")
        return queries

    def _build_jtbd_queries(self, project_task: str, domain: str) -> List[str]:
        """
        从JTBD任务定义构建搜索词

        Args:
            project_task: JTBD任务定义语句
            domain: 领域

        Returns:
            搜索词列表
        """
        queries = []

        if self.methodology:
            # 使用方法论模块解析JTBD
            jtbd_parts = self.methodology.parse_jtbd(project_task)
            identity = jtbd_parts.get("identity", "")
            tasks = jtbd_parts.get("tasks", [])

            # 基于身份构建查询
            if identity:
                queries.append(f"{identity} {domain}")
                queries.append(f"{identity} 空间需求")

            # 基于任务构建查询
            for task in tasks[:2]:  # 最多2个任务
                if task:
                    queries.append(f"{task} {domain}")
                    queries.append(f"{task} 设计案例")
                    queries.append(f"{task} 空间设计")

            # 组合查询
            if identity and tasks:
                queries.append(f"{identity} {tasks[0]} 设计")
        else:
            # 备用方案：简单关键词提取
            keywords = self._extract_keywords_simple(project_task)
            for kw in keywords[:3]:
                queries.append(f"{kw} {domain}")

        return queries[:8]  # 最多8个JTBD查询

    def _build_tension_queries(self, core_tension: str, domain: str) -> List[str]:
        """
        从核心矛盾构建对比搜索词

        Args:
            core_tension: 核心矛盾描述
            domain: 领域

        Returns:
            搜索词列表
        """
        queries = []

        if self.methodology:
            # 使用方法论模块解析核心矛盾
            pole_a, pole_b = self.methodology.parse_core_tension(core_tension)

            if pole_a and pole_b:
                # 单极查询
                queries.append(f"{pole_a} {domain}")
                queries.append(f"{pole_b} {domain}")

                # 对比查询
                queries.append(f"{pole_a} {pole_b} 平衡 {domain}")
                queries.append(f"{pole_a} vs {pole_b} 空间设计")
                queries.append(f"{pole_a} 与 {pole_b} 融合 设计")

                # 解决方案查询
                queries.append(f"{pole_a} {pole_b} 设计解决方案")
            elif pole_a:
                queries.append(f"{pole_a} {domain}")
            elif pole_b:
                queries.append(f"{pole_b} {domain}")
        else:
            # 备用方案
            keywords = self._extract_keywords_simple(core_tension)
            for kw in keywords[:2]:
                queries.append(f"{kw} {domain}")

        return queries[:6]  # 最多6个矛盾查询

    def _build_human_queries(self, human_text: str, domain: str) -> List[str]:
        """
        从人性维度文本构建搜索词

        Args:
            human_text: 人性维度描述文本
            domain: 领域

        Returns:
            搜索词列表
        """
        queries = []

        if self.methodology:
            # 使用方法论模块提取人性维度
            dimensions = self.methodology.extract_human_dimensions(human_text)

            for dim_name, keywords in dimensions.items():
                if keywords:
                    # 取前2个关键词
                    for kw in keywords[:2]:
                        queries.append(f"{kw} {domain}")

                    # 维度组合查询
                    if len(keywords) >= 2:
                        queries.append(f"{keywords[0]} {keywords[1]} 空间设计")
        else:
            # 备用方案
            keywords = self._extract_keywords_simple(human_text)
            for kw in keywords[:4]:
                queries.append(f"{kw} {domain}")

        return queries[:8]  # 最多8个人性维度查询

    def _extract_keywords_simple(self, text: str, topK: int = 5) -> List[str]:
        """
        简单关键词提取（备用方法）

        Args:
            text: 输入文本
            topK: 返回前K个关键词

        Returns:
            关键词列表
        """
        if not text:
            return []

        # 使用jieba（如果可用）
        if jieba:
            try:
                keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=False)
                return keywords
            except Exception:
                pass

        # 简单分词
        words = re.split(r"[，,。.、\s\[\]【】]+", text)
        return [w for w in words if len(w) >= 2][:topK]

    def build_enhanced_queries(
        self, query: str, structured_requirements: Dict[str, Any] | None = None, domain: str = ""
    ) -> List[str]:
        """
        构建增强查询（结合原始查询和需求分析结果）

        Args:
            query: 原始用户查询
            structured_requirements: 结构化需求（可选）
            domain: 领域

        Returns:
            增强后的搜索词列表
        """
        all_queries = []

        # 1. 原始查询
        if query:
            all_queries.append(query)

        # 2. 基于需求分析的查询
        if structured_requirements:
            req_queries = self.build_from_requirements(structured_requirements, domain)
            all_queries.extend(req_queries.get("all_queries", []))

        # 3. 去重
        seen = set()
        unique = []
        for q in all_queries:
            q_normalized = q.lower().strip()
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique.append(q)

        return unique


# 便捷函数
def build_jtbd_queries(structured_requirements: Dict[str, Any], domain: str = "") -> Dict[str, List[str]]:
    """
    快速构建JTBD导向搜索词

    Args:
        structured_requirements: 结构化需求
        domain: 领域

    Returns:
        搜索词字典
    """
    builder = JTBDQueryBuilder()
    return builder.build_from_requirements(structured_requirements, domain)
