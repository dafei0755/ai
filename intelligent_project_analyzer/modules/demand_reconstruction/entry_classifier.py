"""Entry classification for demand reconstruction.

This module owns the lightweight routing predicates used by the compatibility
service: whether a message should enter demand reconstruction, whether it asks
for formal brief output, and whether a pending card message is a follow-up.
"""

from __future__ import annotations

from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
    should_enter_demand_reconstruction,
)


class DemandReconstructionEntryClassifier:
    """Classify user messages at the demand reconstruction entry boundary."""

    FORMAL_TERMS = (
        "设计任务书",
        "任务书",
        "完整设计",
        "完整室内设计",
        "完整室内设计概念框架",
        "完整概念框架",
        "完整框架",
        "可执行版本",
        "按这个做",
        "定稿",
        "输出方案",
    )

    @staticmethod
    def should_handle(message: str) -> bool:
        return should_enter_demand_reconstruction(message)

    @classmethod
    def is_formal_brief_request(cls, message: str) -> bool:
        text = str(message or "")
        if any(term in text for term in cls.FORMAL_TERMS):
            return True
        has_complete = "完整" in text
        has_framework = any(term in text for term in ("框架", "概念", "方案"))
        has_multi_topic = (
            sum(
                1
                for term in ("光", "材料", "动线", "自然", "空间", "界面", "精神性")
                if term in text
            )
            >= 3
        )
        return has_complete and has_framework and has_multi_topic

    @staticmethod
    def is_demand_reconstruction_followup(message: str) -> bool:
        return bool(str(message or "").strip())
