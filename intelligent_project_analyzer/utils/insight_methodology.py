"""
洞察方法论公共模块 (v7.180)

提取自 requirements_analyst.py 的核心方法论，
供需求分析和搜索模块共同使用。

核心功能：
1. JTBD (Jobs-To-Be-Done) 解析
2. 核心矛盾 (Core Tension) 解析
3. 人性维度 (Human Dimensions) 提取与评估
4. 用户模型相关性计算

使用示例：
    from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

    # 解析JTBD
    jtbd = InsightMethodology.parse_jtbd("为一位事业转型期的前金融律师，打造私人空间，雇佣空间完成'专业形象重塑'与'内在自我整合'两项任务")
    # 返回: {"identity": "事业转型期的前金融律师", "space": "私人空间", "tasks": ["专业形象重塑", "内在自我整合"]}

    # 解析核心矛盾
    tension = InsightMethodology.parse_core_tension("作为[内容创作者]的[展示需求]与其对[精神庇护]的根本对立")
    # 返回: ("展示需求", "精神庇护")

    # 提取人性维度
    dimensions = InsightMethodology.extract_human_dimensions("用户追求温馨的家庭氛围，重视传统仪式感")
    # 返回: {"emotional": ["温馨", "氛围"], "ritual": ["仪式"], ...}
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class InsightMethodology:
    """
    洞察方法论工具类

    提供需求分析和搜索模块共用的方法论工具
    """

    # ============================================================================
    # L3 核心矛盾模式
    # ============================================================================
    TENSION_PATTERNS = [
        ("展示", "私密"),
        ("效率", "体验"),
        ("功能", "情感"),
        ("现代", "传统"),
        ("开放", "封闭"),
        ("简约", "丰富"),
        ("理性", "感性"),
        ("公共", "私人"),
        ("工作", "生活"),
        ("社交", "独处"),
    ]

    # ============================================================================
    # 人性维度关键词（5大维度）
    # ============================================================================
    HUMAN_DIMENSIONS = {
        "emotional": [
            "情感",
            "感受",
            "体验",
            "氛围",
            "温度",
            "情绪",
            "心情",
            "温馨",
            "舒适",
            "安心",
            "愉悦",
            "放松",
            "宁静",
            "平和",
            "焦虑",
            "压力",
            "紧张",
            "兴奋",
            "期待",
            "满足",
            "幸福",
        ],
        "spiritual": [
            "精神",
            "追求",
            "价值",
            "意义",
            "信仰",
            "理想",
            "信念",
            "自我",
            "成长",
            "蜕变",
            "升华",
            "超越",
            "内在",
            "灵魂",
            "哲学",
            "美学",
            "艺术",
            "文化",
            "品味",
            "格调",
        ],
        "safety": [
            "安全",
            "庇护",
            "私密",
            "边界",
            "保护",
            "归属",
            "依恋",
            "领地",
            "控制",
            "稳定",
            "可靠",
            "信任",
            "安心",
            "踏实",
            "避风港",
            "港湾",
            "家",
            "根",
            "基地",
        ],
        "ritual": [
            "仪式",
            "习惯",
            "日常",
            "节奏",
            "规律",
            "传统",
            "惯例",
            "晨间",
            "睡前",
            "周末",
            "节日",
            "纪念",
            "庆祝",
            "聚会",
            "咖啡",
            "茶",
            "阅读",
            "冥想",
            "运动",
            "烹饪",
        ],
        "memory": [
            "记忆",
            "回忆",
            "故事",
            "传承",
            "历史",
            "纪念",
            "怀旧",
            "童年",
            "家族",
            "祖辈",
            "老物件",
            "收藏",
            "纪念品",
            "照片",
            "时光",
            "岁月",
            "痕迹",
            "印记",
            "足迹",
        ],
    }

    # ============================================================================
    # JTBD 解析
    # ============================================================================
    @classmethod
    def parse_jtbd(cls, jtbd_statement: str) -> Dict[str, Any]:
        """
        解析JTBD语句，提取身份、空间、任务

        JTBD公式: "为[身份]打造[空间]，雇佣空间完成[任务1]与[任务2]"

        Args:
            jtbd_statement: JTBD语句

        Returns:
            {
                "identity": "身份描述",
                "space": "空间类型",
                "tasks": ["任务1", "任务2"],
                "raw": "原始语句"
            }
        """
        result = {
            "identity": "",
            "space": "",
            "tasks": [],
            "raw": jtbd_statement,
        }

        if not jtbd_statement:
            return result

        try:
            # 模式1: "为[身份]打造[空间]，雇佣空间完成[任务1]与[任务2]"
            pattern1 = r"为(.+?)(?:，|,)?打造(.+?)(?:，|,)?雇佣空间完成['\"]?(.+?)['\"]?(?:与|和|、)['\"]?(.+?)['\"]?(?:两项)?任务"
            match1 = re.search(pattern1, jtbd_statement)
            if match1:
                result["identity"] = match1.group(1).strip()
                result["space"] = match1.group(2).strip()
                result["tasks"] = [
                    match1.group(3).strip().strip("'\""),
                    match1.group(4).strip().strip("'\""),
                ]
                return result

            # 模式2: 简化版 "为[身份]打造[空间]"
            pattern2 = r"为(.+?)(?:，|,)?打造(.+?)(?:，|,|$)"
            match2 = re.search(pattern2, jtbd_statement)
            if match2:
                result["identity"] = match2.group(1).strip()
                result["space"] = match2.group(2).strip()

            # 提取任务（查找引号内的内容）
            task_pattern = r"['\"]([^'\"]+)['\"]"
            tasks = re.findall(task_pattern, jtbd_statement)
            if tasks:
                result["tasks"] = [t.strip() for t in tasks[:4]]  # 最多4个任务

            # 如果没有找到引号内的任务，尝试提取"完成X与Y"模式
            if not result["tasks"]:
                task_pattern2 = r"完成(.+?)(?:与|和|、)(.+?)(?:任务|$)"
                match_tasks = re.search(task_pattern2, jtbd_statement)
                if match_tasks:
                    result["tasks"] = [
                        match_tasks.group(1).strip(),
                        match_tasks.group(2).strip(),
                    ]

        except Exception as e:
            logger.warning(f"JTBD解析失败: {e}, 原文: {jtbd_statement[:100]}")

        return result

    # ============================================================================
    # 核心矛盾解析
    # ============================================================================
    @classmethod
    def parse_core_tension(cls, tension: str) -> Tuple[str, str]:
        """
        解析核心矛盾，提取对立双方

        核心矛盾公式: "作为[A]的[需求1]与其对[需求2]的根本对立"

        Args:
            tension: 核心矛盾描述

        Returns:
            (pole_a, pole_b) 对立的两极
        """
        if not tension:
            return ("", "")

        try:
            # 模式1: "作为[A]的[需求1]与其对[需求2]的根本对立"
            pattern1 = r"作为.+?的\[?(.+?)\]?与其对\[?(.+?)\]?的"
            match1 = re.search(pattern1, tension)
            if match1:
                return (match1.group(1).strip(), match1.group(2).strip())

            # 模式2: "[需求1]与[需求2]的对立"
            pattern2 = r"\[?(.+?)\]?\s*(?:与|和|vs|VS)\s*\[?(.+?)\]?\s*(?:的)?(?:对立|矛盾|冲突)"
            match2 = re.search(pattern2, tension)
            if match2:
                return (match2.group(1).strip(), match2.group(2).strip())

            # 模式3: 查找已知的对立模式
            for pole_a, pole_b in cls.TENSION_PATTERNS:
                if pole_a in tension and pole_b in tension:
                    return (pole_a, pole_b)

            # 模式4: 简单的"X vs Y"或"X与Y"
            pattern4 = r"(.+?)\s*(?:vs|VS|与|和|对)\s*(.+)"
            match4 = re.search(pattern4, tension)
            if match4:
                pole_a = match4.group(1).strip()
                pole_b = match4.group(2).strip()
                # 清理常见后缀
                for suffix in ["的对立", "的矛盾", "的冲突", "的张力"]:
                    pole_b = pole_b.replace(suffix, "").strip()
                return (pole_a, pole_b)

        except Exception as e:
            logger.warning(f"核心矛盾解析失败: {e}, 原文: {tension[:100]}")

        return ("", "")

    # ============================================================================
    # 人性维度提取
    # ============================================================================
    @classmethod
    def extract_human_dimensions(cls, text: str) -> Dict[str, List[str]]:
        """
        从文本中提取人性维度关键词

        Args:
            text: 输入文本

        Returns:
            {
                "emotional": ["温馨", "舒适", ...],
                "spiritual": ["追求", ...],
                "safety": ["安全", ...],
                "ritual": ["仪式", ...],
                "memory": ["记忆", ...],
            }
        """
        result = {dim: [] for dim in cls.HUMAN_DIMENSIONS.keys()}

        if not text:
            return result

        text_lower = text.lower()

        for dimension, keywords in cls.HUMAN_DIMENSIONS.items():
            matched = []
            for keyword in keywords:
                if keyword in text or keyword.lower() in text_lower:
                    matched.append(keyword)
            result[dimension] = list(set(matched))  # 去重

        return result

    @classmethod
    def get_dimension_coverage(cls, text: str) -> Dict[str, Any]:
        """
        计算文本的人性维度覆盖度

        Args:
            text: 输入文本

        Returns:
            {
                "dimensions": {...},  # 各维度匹配的关键词
                "coverage_score": 0-100,  # 覆盖度分数
                "covered_dimensions": ["emotional", "ritual"],  # 覆盖的维度
                "missing_dimensions": ["spiritual", ...],  # 缺失的维度
            }
        """
        dimensions = cls.extract_human_dimensions(text)

        covered = [dim for dim, keywords in dimensions.items() if keywords]
        missing = [dim for dim, keywords in dimensions.items() if not keywords]

        # 计算覆盖度分数（每个维度20分）
        coverage_score = len(covered) * 20

        return {
            "dimensions": dimensions,
            "coverage_score": coverage_score,
            "covered_dimensions": covered,
            "missing_dimensions": missing,
        }

    # ============================================================================
    # 用户模型相关性计算
    # ============================================================================
    @classmethod
    def calculate_human_relevance(cls, content: str, user_model: Optional[Dict[str, Any]] = None) -> float:
        """
        计算内容与用户人性维度的相关性分数

        基于用户模型中的情感地图、精神追求等维度

        Args:
            content: 待评估的内容
            user_model: 用户模型（来自L2分析）
                {
                    "psychological": "...",
                    "sociological": "...",
                    "aesthetic": "...",
                    "emotional": "...",
                    "ritual": "..."
                }

        Returns:
            相关性分数 (0-100)
        """
        if not content:
            return 0.0

        # 基础分数：内容本身的人性维度覆盖
        coverage = cls.get_dimension_coverage(content)
        base_score = coverage["coverage_score"]

        # 如果没有用户模型，返回基础分数
        if not user_model:
            return min(100.0, base_score)

        # 提取用户模型中的关键词
        user_keywords = set()
        for field in ["psychological", "sociological", "aesthetic", "emotional", "ritual"]:
            field_value = user_model.get(field, "")
            if field_value:
                # 提取用户模型中的人性维度关键词
                field_dims = cls.extract_human_dimensions(field_value)
                for keywords in field_dims.values():
                    user_keywords.update(keywords)

        # 计算内容与用户关键词的匹配度
        content_keywords = set()
        content_dims = cls.extract_human_dimensions(content)
        for keywords in content_dims.values():
            content_keywords.update(keywords)

        # 计算交集
        if user_keywords:
            intersection = content_keywords & user_keywords
            match_ratio = len(intersection) / len(user_keywords) if user_keywords else 0
            user_match_score = match_ratio * 50  # 用户匹配最多50分
        else:
            user_match_score = 0

        # 综合分数
        total_score = base_score * 0.5 + user_match_score

        return min(100.0, total_score)

    # ============================================================================
    # 辅助方法
    # ============================================================================
    @classmethod
    def extract_keywords_from_jtbd(cls, jtbd_statement: str) -> List[str]:
        """
        从JTBD语句中提取搜索关键词

        Args:
            jtbd_statement: JTBD语句

        Returns:
            关键词列表
        """
        parsed = cls.parse_jtbd(jtbd_statement)
        keywords = []

        # 从身份提取
        if parsed["identity"]:
            # 提取名词短语
            identity_keywords = re.findall(r"[\u4e00-\u9fff]+", parsed["identity"])
            keywords.extend([k for k in identity_keywords if len(k) >= 2])

        # 从任务提取
        for task in parsed["tasks"]:
            task_keywords = re.findall(r"[\u4e00-\u9fff]+", task)
            keywords.extend([k for k in task_keywords if len(k) >= 2])

        # 去重并保持顺序
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique_keywords.append(k)

        return unique_keywords[:10]  # 最多10个关键词

    @classmethod
    def extract_keywords_from_tension(cls, tension: str) -> List[str]:
        """
        从核心矛盾中提取搜索关键词

        Args:
            tension: 核心矛盾描述

        Returns:
            关键词列表
        """
        pole_a, pole_b = cls.parse_core_tension(tension)
        keywords = []

        if pole_a:
            keywords.append(pole_a)
        if pole_b:
            keywords.append(pole_b)

        # 添加组合关键词
        if pole_a and pole_b:
            keywords.append(f"{pole_a}{pole_b}平衡")

        return keywords

    @classmethod
    def get_dimension_keywords(cls, dimension: str) -> List[str]:
        """
        获取指定维度的关键词列表

        Args:
            dimension: 维度名称 (emotional/spiritual/safety/ritual/memory)

        Returns:
            关键词列表
        """
        return cls.HUMAN_DIMENSIONS.get(dimension, [])

    @classmethod
    def identify_dominant_dimension(cls, text: str) -> Optional[str]:
        """
        识别文本中最主导的人性维度

        Args:
            text: 输入文本

        Returns:
            主导维度名称，如果没有明显主导则返回None
        """
        dimensions = cls.extract_human_dimensions(text)

        # 找出匹配关键词最多的维度
        max_count = 0
        dominant = None

        for dim, keywords in dimensions.items():
            if len(keywords) > max_count:
                max_count = len(keywords)
                dominant = dim

        # 至少要有2个关键词才算主导
        return dominant if max_count >= 2 else None


# ============================================================================
# 便捷函数
# ============================================================================


def parse_jtbd(jtbd_statement: str) -> Dict[str, Any]:
    """解析JTBD语句（便捷函数）"""
    return InsightMethodology.parse_jtbd(jtbd_statement)


def parse_core_tension(tension: str) -> Tuple[str, str]:
    """解析核心矛盾（便捷函数）"""
    return InsightMethodology.parse_core_tension(tension)


def extract_human_dimensions(text: str) -> Dict[str, List[str]]:
    """提取人性维度（便捷函数）"""
    return InsightMethodology.extract_human_dimensions(text)


def calculate_human_relevance(content: str, user_model: Optional[Dict[str, Any]] = None) -> float:
    """计算人性维度相关性（便捷函数）"""
    return InsightMethodology.calculate_human_relevance(content, user_model)
