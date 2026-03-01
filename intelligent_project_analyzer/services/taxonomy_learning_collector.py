"""
维度学习数据收集器

在用户完成问卷时自动收集学习数据，无需用户手动反馈。
"""

from typing import Dict, Any, Optional
from loguru import logger

from .concept_discovery_service import ConceptDiscoveryService
from .taxonomy_promotion_service import TaxonomyPromotionService


class TaxonomyLearningCollector:
    """维度学习数据收集器"""

    def __init__(self):
        """初始化收集器"""
        self.discovery_service = ConceptDiscoveryService()
        self.promotion_service = TaxonomyPromotionService()
        logger.info(" 维度学习收集器已初始化")

    async def collect_from_questionnaire(
        self, session_id: str, user_input: str, questionnaire_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从问卷数据中收集学习信息

        Args:
            session_id: 会话ID
            user_input: 原始用户输入
            questionnaire_data: 问卷数据（包含Step 1-3的回答）

        Returns:
            收集结果
        """
        logger.info(f" 开始收集学习数据: session={session_id}")

        try:
            # 1. 提取用户输入中的概念
            discovery_result = await self.discovery_service.analyze_session(session_id, user_input)

            # 2. 检查是否有标签可以晋升
            promotion_result = self.promotion_service.run_promotion_check(auto_promote=True)

            result = {
                "status": "success",
                "session_id": session_id,
                "discovery": {
                    "concepts_extracted": discovery_result.get("concepts_extracted", 0),
                    "clusters_created": discovery_result.get("clusters_created", 0),
                    "discoveries_saved": discovery_result.get("discoveries_saved", 0),
                },
                "promotion": {
                    "qualified": promotion_result.get("qualified", 0),
                    "promoted": promotion_result.get("promoted", 0),
                },
            }

            logger.info(
                f" 学习数据收集完成: "
                f"发现{result['discovery']['discoveries_saved']}个新概念, "
                f"晋升{result['promotion']['promoted']}个标签"
            )

            return result

        except Exception as e:
            logger.error(f" 学习数据收集失败: {e}")
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
            }

    def record_type_correction(
        self,
        detected_type: Optional[str],
        confirmed_type: str,
        user_text: str,
    ) -> None:
        """
        Step 7: 记录用户纠正的项目类型，反向学习别名。

        当检测结果与用户确认结果不一致时调用，将用户原文中可能导致误判的
        词汇注册为 ``confirmed_type`` 的动态别名，供后续检测优先命中。

        Args:
            detected_type:  系统原先检测到的类型 ID（可能为 None）
            confirmed_type: 用户手动确认/修正后的类型 ID
            user_text:      触发误判的原始用户输入文本
        """
        if detected_type == confirmed_type:
            return  # 无需学习

        try:
            from .type_alias_normalizer import add_dynamic_alias
            from .project_type_detector import PROJECT_TYPE_REGISTRY

            # 找到 confirmed_type 对应的规范中文名
            canonical_name: Optional[str] = None
            for entry in PROJECT_TYPE_REGISTRY:
                if entry.get("type_id") == confirmed_type:
                    canonical_name = entry.get("name_zh") or entry.get("name")
                    break

            if canonical_name is None:
                logger.warning(f"[TaxonomyLearning] record_type_correction: 未知 confirmed_type={confirmed_type}")
                return

            # 提取用户文本中不超过 10 字的有效片段作为别名候选
            # 简单策略：直接将截断后的 user_text 作为别名（不超过 10 字）
            alias_candidate = user_text.strip()[:10]
            if alias_candidate:
                add_dynamic_alias(alias_candidate, canonical_name)
                logger.info(
                    f"[TaxonomyLearning] 别名学习: '{alias_candidate}' → '{canonical_name}' "
                    f"(detected={detected_type}, confirmed={confirmed_type})"
                )

        except Exception as e:
            logger.error(f"[TaxonomyLearning] record_type_correction 失败: {e}")

    def get_learning_summary(self) -> Dict[str, Any]:
        """
        获取学习系统摘要

        Returns:
            学习系统状态摘要
        """
        try:
            discovery_stats = self.discovery_service.get_discovery_statistics()
            promotion_stats = self.promotion_service.get_promotion_statistics()

            return {
                "status": "active",
                "discoveries": discovery_stats,
                "promotions": promotion_stats,
                "system_health": "healthy",
            }

        except Exception as e:
            logger.error(f" 获取学习摘要失败: {e}")
            return {"status": "error", "error": str(e)}


# 全局单例
_learning_collector: Optional[TaxonomyLearningCollector] = None


def get_learning_collector() -> TaxonomyLearningCollector:
    """获取全局学习收集器实例"""
    global _learning_collector
    if _learning_collector is None:
        _learning_collector = TaxonomyLearningCollector()
    return _learning_collector
