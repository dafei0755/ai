"""
项目类型自动检测器
v7.152: 基于关键词+LLM的项目类型自动识别

功能：
1. 根据用户输入自动识别项目类型
2. 支持关键词规则层（快速匹配）
3. 支持复杂/混合类型项目的智能识别
"""

from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

# 项目类型关键词映射
PROJECT_TYPE_KEYWORDS = {
    # 城市更新/公共市场（优先级最高）
    "urban_renewal_market": {
        "name": "城市更新/公共市场",
        "keywords": ["城市更新", "菜市场", "农贸市场", "市场改造", "活化", "再生", "旧改", "老旧改造"],
        "secondary_keywords": ["标杆", "示范", "渔村", "老街", "历史街区", "公共市场", "集市"],
        "priority": 10,
    },
    # 城市更新/历史街区
    "urban_renewal_heritage": {
        "name": "城市更新/历史街区",
        "keywords": ["历史街区", "老建筑", "文物保护", "历史保护", "古建筑", "老城区"],
        "secondary_keywords": ["修缮", "修复", "保护", "传承", "非遗"],
        "priority": 10,
    },
    # 酒店民宿
    "commercial_hospitality": {
        "name": "酒店民宿",
        "keywords": ["酒店", "民宿", "度假", "客房", "住宿", "度假村"],
        "secondary_keywords": ["精品酒店", "boutique", "resort", "客栈", "旅馆"],
        "priority": 8,
    },
    # 餐饮空间
    "commercial_dining": {
        "name": "餐饮空间",
        "keywords": ["餐厅", "餐饮", "咖啡", "茶室", "酒吧", "咖啡馆"],
        "secondary_keywords": ["美食", "厨房", "用餐", "茶馆", "酒楼", "食堂"],
        "priority": 8,
    },
    # 文化教育
    "public_cultural": {
        "name": "文化教育",
        "keywords": ["博物馆", "展览", "图书馆", "文化中心", "艺术馆", "美术馆"],
        "secondary_keywords": ["展示", "教育", "文化", "画廊", "剧院", "音乐厅"],
        "priority": 8,
    },
    # 商业零售
    "commercial_retail": {
        "name": "商业零售",
        "keywords": ["商场", "店铺", "零售", "购物", "专卖店", "商业综合体"],
        "secondary_keywords": ["品牌", "门店", "旗舰店", "购物中心", "百货"],
        "priority": 7,
    },
    # 办公空间
    "commercial_office": {
        "name": "办公空间",
        "keywords": ["办公", "写字楼", "工作室", "联合办公", "办公室"],
        "secondary_keywords": ["会议室", "工位", "共享办公", "孵化器"],
        "priority": 7,
    },
    # 企业空间
    "commercial_enterprise": {
        "name": "企业空间",
        "keywords": ["企业", "总部", "展厅", "接待中心", "体验中心"],
        "secondary_keywords": ["品牌展厅", "企业文化", "员工空间"],
        "priority": 7,
    },
    # 个人住宅（默认类型，优先级最低）
    "personal_residential": {
        "name": "个人住宅",
        "keywords": ["住宅", "家", "公寓", "别墅", "房子", "新房"],
        "secondary_keywords": ["卧室", "客厅", "厨房", "卫生间", "装修", "家装"],
        "priority": 5,
    },
}


class ProjectTypeDetector:
    """
    项目类型自动检测器

    v7.152: 基于关键词规则的项目类型自动识别
    """

    def __init__(self):
        self.keywords_config = PROJECT_TYPE_KEYWORDS
        logger.info("🔍 [v7.152] 项目类型检测器初始化")

    def detect(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, float, str]:
        """
        检测项目类型

        Args:
            user_input: 用户原始输入
            confirmed_tasks: 确认的任务列表（可选）

        Returns:
            (project_type, confidence, reason)
            - project_type: 项目类型ID
            - confidence: 置信度 (0.0-1.0)
            - reason: 检测原因
        """
        # 合并文本（用户输入 + 任务标题/描述）
        combined_text = user_input.lower()
        if confirmed_tasks:
            for task in confirmed_tasks:
                combined_text += " " + task.get("title", "").lower()
                combined_text += " " + task.get("description", "").lower()

        # 关键词匹配
        scores: Dict[str, Dict[str, Any]] = {}
        for type_id, config in self.keywords_config.items():
            score = 0
            matched_keywords = []

            # 主关键词匹配（权重2）
            for kw in config["keywords"]:
                if kw in combined_text:
                    score += 2
                    matched_keywords.append(kw)

            # 次要关键词匹配（权重1）
            for kw in config.get("secondary_keywords", []):
                if kw in combined_text:
                    score += 1
                    matched_keywords.append(kw)

            if score > 0:
                scores[type_id] = {
                    "score": score,
                    "priority": config["priority"],
                    "matched": matched_keywords,
                    "name": config["name"],
                }

        if not scores:
            # 默认返回住宅类型
            logger.info("🔍 [v7.152] 未匹配到特定类型，使用默认类型: personal_residential")
            return "personal_residential", 0.3, "未匹配到特定类型，使用默认类型"

        # 按 score * priority 排序
        sorted_types = sorted(
            scores.items(),
            key=lambda x: x[1]["score"] * x[1]["priority"],
            reverse=True,
        )

        best_type = sorted_types[0]
        type_id = best_type[0]
        info = best_type[1]

        # 计算置信度
        confidence = min(0.95, 0.5 + info["score"] * 0.1)
        reason = f"匹配关键词: {', '.join(info['matched'][:3])}"

        logger.info(f"🎯 [v7.152] 检测到项目类型: {info['name']} ({type_id}), 置信度: {confidence:.0%}")
        logger.info(f"   {reason}")

        return type_id, confidence, reason

    def detect_with_details(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        检测项目类型（返回详细信息）

        Args:
            user_input: 用户原始输入
            confirmed_tasks: 确认的任务列表（可选）

        Returns:
            {
                "project_type": "urban_renewal_market",
                "project_type_name": "城市更新/公共市场",
                "confidence": 0.85,
                "reason": "匹配关键词: 菜市场, 城市更新, 标杆",
                "all_matches": [
                    {"type_id": "urban_renewal_market", "score": 8, "matched": [...]},
                    ...
                ]
            }
        """
        # 合并文本
        combined_text = user_input.lower()
        if confirmed_tasks:
            for task in confirmed_tasks:
                combined_text += " " + task.get("title", "").lower()
                combined_text += " " + task.get("description", "").lower()

        # 关键词匹配
        all_matches = []
        for type_id, config in self.keywords_config.items():
            score = 0
            matched_keywords = []

            for kw in config["keywords"]:
                if kw in combined_text:
                    score += 2
                    matched_keywords.append(kw)

            for kw in config.get("secondary_keywords", []):
                if kw in combined_text:
                    score += 1
                    matched_keywords.append(kw)

            if score > 0:
                all_matches.append(
                    {
                        "type_id": type_id,
                        "type_name": config["name"],
                        "score": score,
                        "priority": config["priority"],
                        "weighted_score": score * config["priority"],
                        "matched": matched_keywords,
                    }
                )

        # 排序
        all_matches.sort(key=lambda x: x["weighted_score"], reverse=True)

        if not all_matches:
            return {
                "project_type": "personal_residential",
                "project_type_name": "个人住宅",
                "confidence": 0.3,
                "reason": "未匹配到特定类型，使用默认类型",
                "all_matches": [],
            }

        best = all_matches[0]
        confidence = min(0.95, 0.5 + best["score"] * 0.1)

        return {
            "project_type": best["type_id"],
            "project_type_name": best["type_name"],
            "confidence": confidence,
            "reason": f"匹配关键词: {', '.join(best['matched'][:3])}",
            "all_matches": all_matches[:5],  # 返回前5个匹配结果
        }


# 便捷函数
def detect_project_type(
    user_input: str,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    便捷函数：检测项目类型

    Args:
        user_input: 用户原始输入
        confirmed_tasks: 确认的任务列表（可选）

    Returns:
        项目类型ID
    """
    detector = ProjectTypeDetector()
    project_type, _, _ = detector.detect(user_input, confirmed_tasks)
    return project_type


def detect_project_type_with_confidence(
    user_input: str,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, float]:
    """
    便捷函数：检测项目类型（带置信度）

    Args:
        user_input: 用户原始输入
        confirmed_tasks: 确认的任务列表（可选）

    Returns:
        (项目类型ID, 置信度)
    """
    detector = ProjectTypeDetector()
    project_type, confidence, _ = detector.detect(user_input, confirmed_tasks)
    return project_type, confidence
