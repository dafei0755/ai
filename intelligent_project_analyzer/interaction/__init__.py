"""
人机交互模块

实现用户确认、审核、追问等交互功能
"""

from .interaction_nodes import (  # AnalysisReviewNode,  # 🗑️ v2.2: 已废弃，被role_selection_quality_review替代
    FinalReviewNode,
    UserQuestionNode,
)

# 🆕 v2.2: 角色选择质量审核节点
from .nodes.role_selection_quality_review import RoleSelectionQualityReviewNode, role_selection_quality_review_node

__all__ = [
    # "AnalysisReviewNode",  # 🗑️ v2.2: 已废弃
    "FinalReviewNode",
    "UserQuestionNode",
    "RoleSelectionQualityReviewNode",  # 🆕 v2.2
    "role_selection_quality_review_node",  # 🆕 v2.2
]
