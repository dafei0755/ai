"""
人机交互节点集合

导出所有交互节点类
"""

from .calibration_questionnaire import CalibrationQuestionnaireNode

# from .analysis_review import AnalysisReviewNode  # 🗑️ v2.2: 已废弃，被role_selection_quality_review替代
from .final_review import FinalReviewNode
from .quality_preflight import QualityPreflightNode  # 🆕
from .role_selection_quality_review import RoleSelectionQualityReviewNode, role_selection_quality_review_node  # 🆕 v2.2
from .user_question import UserQuestionNode

__all__ = [
    "CalibrationQuestionnaireNode",
    # "AnalysisReviewNode",  # 🗑️ v2.2: 已废弃
    "FinalReviewNode",
    "UserQuestionNode",
    "QualityPreflightNode",  # 🆕
    "RoleSelectionQualityReviewNode",  # 🆕 v2.2
    "role_selection_quality_review_node",  # 🆕 v2.2
]
