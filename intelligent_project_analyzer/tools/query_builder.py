"""
Deliverable Query Builder (v7.64)

从交付物规格（name + description）构建精准搜索查询，避免泛泛而谈的通用搜索
"""

import re
from typing import Any, Dict, List, Optional

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

    # 🔑 交付物格式 → 搜索术语映射表 (v7.65扩展: 30种→50+种)
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
        "trend_analysis": "trend analysis forecasting",  # 🔥 require_search=true
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
        # === 案例与资料库 ===  # 🔥 require_search=true
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

    # 🌍 项目类型 → 上下文术语
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
            logger.info("✅ DeliverableQueryBuilder: jieba initialized")
        else:
            logger.warning("⚠️ DeliverableQueryBuilder: jieba disabled")

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
                logger.debug(f"📌 Name keywords: {name_keywords}")

        # 2. 提取交付物描述关键词（权重中，取top5）
        description = deliverable.get("description", "")
        if description:
            desc_keywords = self._extract_keywords(description, topK=5)
            if desc_keywords:
                query_parts.extend(desc_keywords)
                logger.debug(f"📌 Description keywords: {desc_keywords}")

        # 3. 添加格式对应的搜索术语（英文，提高国际搜索准确性）
        fmt = deliverable.get("format", "")
        if fmt and fmt in self.FORMAT_SEARCH_TERMS:
            format_term = self.FORMAT_SEARCH_TERMS[fmt]
            query_parts.append(format_term)
            logger.debug(f"📌 Format term: {format_term}")

        # 4. 添加项目类型上下文
        if project_type and project_type in self.PROJECT_TYPE_CONTEXT:
            context_term = self.PROJECT_TYPE_CONTEXT[project_type]
            query_parts.append(context_term)
            logger.debug(f"📌 Project context: {context_term}")

        # 5. 组合查询（去重）
        unique_parts = []
        seen = set()
        for part in query_parts:
            part_lower = part.lower()
            if part_lower not in seen:
                unique_parts.append(part)
                seen.add(part_lower)

        final_query = " ".join(unique_parts)
        logger.info(f"🔍 Built query for '{name}': {final_query}")

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
                logger.error(f"❌ Jieba extraction failed: {e}")
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
        - RAGFlow: 内部知识库，中文为主
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
            "ragflow": self._build_ragflow_query(deliverable, base_query),
            "bocha": self._build_bocha_query(deliverable, base_query),
        }

        return queries

    def _build_arxiv_query(self, deliverable: Dict[str, Any], base_query: str) -> str:
        """为Arxiv构建学术化查询"""
        # 添加方法论关键词
        methodology_terms = ["methodology", "framework", "approach", "model"]
        return f"{base_query} {methodology_terms[0]}"

    def _build_ragflow_query(self, deliverable: Dict[str, Any], base_query: str) -> str:
        """为RAGFlow（内部知识库）构建查询"""
        # 保留中文关键词为主
        name = deliverable.get("name", "")
        description = deliverable.get("description", "")
        chinese_text = name if self._is_chinese_text(name) else description
        if chinese_text:
            return chinese_text[:50]  # 保留原文前50字
        return base_query

    def _build_bocha_query(self, deliverable: Dict[str, Any], base_query: str) -> str:
        """为Bocha（中文搜索）构建查询"""
        # 同RAGFlow，优先使用中文
        return self._build_ragflow_query(deliverable, base_query)


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
