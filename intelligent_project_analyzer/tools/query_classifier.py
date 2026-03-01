"""
查询分类器 (v7.197)

识别查询类型，用于动态调整搜索策略和质量控制参数。

分类类型：
- news: 新闻/时事类 - 高时效性权重
- academic: 学术/研究类 - 低时效性，高可信度权重
- case: 案例/项目类 - 优先专业站点
- concept: 概念/定义类 - 优先权威来源
- trend: 趋势/流行类 - 中等时效性
- howto: 教程/方法类 - 优先社区内容
- comparison: 对比/评测类 - 多源验证
- general: 通用查询

作者: AI Assistant
日期: 2026-01-10
"""

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

from loguru import logger

# 配置
QUERY_CLASSIFIER_ENABLED = os.getenv("QUERY_CLASSIFIER_ENABLED", "true").lower() == "true"


class QueryType(Enum):
    """查询类型枚举"""

    NEWS = "news"  # 新闻/时事
    ACADEMIC = "academic"  # 学术/研究
    CASE = "case"  # 案例/项目
    CONCEPT = "concept"  # 概念/定义
    TREND = "trend"  # 趋势/流行
    HOWTO = "howto"  # 教程/方法
    COMPARISON = "comparison"  # 对比/评测
    GENERAL = "general"  # 通用


@dataclass
class QueryClassification:
    """查询分类结果"""

    query_type: QueryType
    confidence: float  # 0-1
    keywords_matched: List[str]

    # 动态权重调整
    timeliness_weight: float  # 时效性权重
    credibility_weight: float  # 可信度权重

    # 搜索策略建议
    preferred_sources: List[str]  # 优先来源


# 关键词规则库
QUERY_PATTERNS: Dict[QueryType, Dict] = {
    QueryType.NEWS: {
        "keywords": [
            "最新",
            "今日",
            "今天",
            "昨天",
            "本周",
            "本月",
            "近期",
            "刚刚",
            "新闻",
            "报道",
            "发布",
            "宣布",
            "曝光",
            "热点",
            "突发",
            "快讯",
            "2025",
            "2026",
            "年度",
            "季度",
        ],
        "patterns": [
            r"\d{4}年\d{1,2}月",
            r"最近.*消息",
            r".*发布会",
        ],
        "timeliness_weight": 0.30,
        "credibility_weight": 0.25,
        "preferred_sources": ["新闻媒体", "官方公告"],
    },
    QueryType.ACADEMIC: {
        "keywords": [
            "论文",
            "研究",
            "学术",
            "文献",
            "期刊",
            "学者",
            "理论",
            "实验",
            "分析",
            "综述",
            "引用",
            "摘要",
            "方法论",
            "假设",
            "验证",
            "paper",
            "research",
            "study",
            "journal",
            "thesis",
            "dissertation",
            "arxiv",
            "知网",
            "万方",
        ],
        "patterns": [
            r".*的研究",
            r".*理论",
            r".*模型",
            r".*算法",
        ],
        "timeliness_weight": 0.05,
        "credibility_weight": 0.45,
        "preferred_sources": ["arxiv", "cnki", "scholar"],
    },
    QueryType.CASE: {
        "keywords": [
            "案例",
            "项目",
            "作品",
            "设计",
            "方案",
            "实例",
            "样例",
            "范例",
            "成功案例",
            "经典案例",
            "优秀作品",
            "获奖",
            "入围",
            "archdaily",
            "gooood",
            "dezeen",
            "designboom",
        ],
        "patterns": [
            r".*设计案例",
            r".*项目分析",
            r".*作品集",
        ],
        "timeliness_weight": 0.15,
        "credibility_weight": 0.35,
        "preferred_sources": ["archdaily", "gooood", "dezeen", "designboom"],
    },
    QueryType.CONCEPT: {
        "keywords": [
            "什么是",
            "定义",
            "概念",
            "含义",
            "是什么",
            "意思",
            "区别",
            "原理",
            "本质",
            "特征",
            "特点",
            "分类",
            "类型",
            "what is",
            "definition",
            "meaning",
            "concept",
        ],
        "patterns": [
            r"什么是.*",
            r".*是什么",
            r".*的定义",
            r".*的概念",
        ],
        "timeliness_weight": 0.05,
        "credibility_weight": 0.40,
        "preferred_sources": ["百科", "学术", "权威"],
    },
    QueryType.TREND: {
        "keywords": [
            "趋势",
            "流行",
            "潮流",
            "热门",
            "火爆",
            "爆款",
            "风格",
            "未来",
            "预测",
            "展望",
            "发展方向",
            "新兴",
            "trend",
            "popular",
            "emerging",
            "future",
        ],
        "patterns": [
            r"\d{4}年.*趋势",
            r".*流行趋势",
            r"未来.*发展",
        ],
        "timeliness_weight": 0.25,
        "credibility_weight": 0.30,
        "preferred_sources": ["行业报告", "设计媒体"],
    },
    QueryType.HOWTO: {
        "keywords": [
            "如何",
            "怎么",
            "怎样",
            "方法",
            "步骤",
            "教程",
            "指南",
            "攻略",
            "技巧",
            "诀窍",
            "入门",
            "实践",
            "操作",
            "使用",
            "how to",
            "tutorial",
            "guide",
            "tips",
            "step by step",
        ],
        "patterns": [
            r"如何.*",
            r"怎么.*",
            r".*教程",
            r".*指南",
        ],
        "timeliness_weight": 0.15,
        "credibility_weight": 0.30,
        "preferred_sources": ["社区", "博客", "教程站"],
    },
    QueryType.COMPARISON: {
        "keywords": [
            "对比",
            "比较",
            "区别",
            "差异",
            "优缺点",
            "哪个好",
            "选择",
            "VS",
            "versus",
            "和",
            "与",
            "还是",
            "comparison",
            "compare",
            "difference",
            "vs",
        ],
        "patterns": [
            r".*和.*对比",
            r".*还是.*",
            r".*哪个好",
            r".*vs.*",
        ],
        "timeliness_weight": 0.15,
        "credibility_weight": 0.35,
        "preferred_sources": ["评测", "专业论坛"],
    },
}

# 默认权重（通用查询）
DEFAULT_WEIGHTS = {
    "timeliness_weight": 0.10,
    "credibility_weight": 0.35,
    "preferred_sources": [],
}


def classify_query(query: str) -> QueryClassification:
    """
    分类查询

    使用规则匹配识别查询类型。

    Args:
        query: 用户查询

    Returns:
        QueryClassification 分类结果
    """
    if not query or not QUERY_CLASSIFIER_ENABLED:
        return QueryClassification(
            query_type=QueryType.GENERAL,
            confidence=1.0,
            keywords_matched=[],
            timeliness_weight=DEFAULT_WEIGHTS["timeliness_weight"],
            credibility_weight=DEFAULT_WEIGHTS["credibility_weight"],
            preferred_sources=DEFAULT_WEIGHTS["preferred_sources"],
        )

    query_lower = query.lower()

    # 统计每种类型的匹配分数
    scores: Dict[QueryType, Tuple[float, List[str]]] = {}

    for query_type, config in QUERY_PATTERNS.items():
        matched_keywords = []
        score = 0.0

        # 关键词匹配
        for keyword in config["keywords"]:
            if keyword.lower() in query_lower:
                matched_keywords.append(keyword)
                score += 1.0

        # 正则匹配（权重更高）
        for pattern in config["patterns"]:
            if re.search(pattern, query, re.IGNORECASE):
                score += 2.0
                matched_keywords.append(f"[pattern:{pattern[:20]}]")

        if score > 0:
            scores[query_type] = (score, matched_keywords)

    # 找出最高分的类型
    if scores:
        best_type = max(scores.keys(), key=lambda t: scores[t][0])
        best_score, matched = scores[best_type]

        # 计算置信度（基于匹配数量）
        confidence = min(1.0, best_score / 5.0)

        config = QUERY_PATTERNS[best_type]

        result = QueryClassification(
            query_type=best_type,
            confidence=confidence,
            keywords_matched=matched,
            timeliness_weight=config["timeliness_weight"],
            credibility_weight=config["credibility_weight"],
            preferred_sources=config["preferred_sources"],
        )

        logger.info(f" [QueryClassifier] 查询分类 | " f"类型={best_type.value} | 置信度={confidence:.2f} | " f"匹配={matched[:3]}")

        return result

    # 无匹配，返回通用类型
    return QueryClassification(
        query_type=QueryType.GENERAL,
        confidence=0.5,
        keywords_matched=[],
        timeliness_weight=DEFAULT_WEIGHTS["timeliness_weight"],
        credibility_weight=DEFAULT_WEIGHTS["credibility_weight"],
        preferred_sources=DEFAULT_WEIGHTS["preferred_sources"],
    )


def get_dynamic_weights(query: str) -> Dict[str, float]:
    """
    获取动态权重（便捷接口）

    Args:
        query: 用户查询

    Returns:
        权重字典
    """
    classification = classify_query(query)

    return {
        "relevance": 0.35,  # 固定
        "timeliness": classification.timeliness_weight,
        "credibility": classification.credibility_weight,
        "completeness": 1.0 - 0.35 - classification.timeliness_weight - classification.credibility_weight,
    }


def get_preferred_sources(query: str) -> List[str]:
    """
    获取优先来源（便捷接口）

    Args:
        query: 用户查询

    Returns:
        优先来源列表
    """
    classification = classify_query(query)
    return classification.preferred_sources
