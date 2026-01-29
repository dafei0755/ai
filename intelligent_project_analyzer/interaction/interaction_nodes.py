"""
人机交互节点 - 兼容性导入模块

⚠️ 此文件已重构：所有节点类已拆分到 nodes/ 子目录
为保持向后兼容，此文件继续提供导入接口

新结构：
- nodes/calibration_questionnaire.py - 战略校准问卷节点
- nodes/analysis_review.py - 🗑️ v2.2: 已废弃，被role_selection_quality_review替代
- nodes/final_review.py - 最终审核节点
- nodes/user_question.py - 用户追问节点
- nodes/role_selection_quality_review.py - 🆕 v2.2: 角色选择质量审核节点

注: requirements_confirmation 已在 v7.151 中合并到 questionnaire_summary（需求洞察）
"""

# 从 nodes 子包导入所有节点类
from .nodes import (  # AnalysisReviewNode,  # 🗑️ v2.2: 已废弃
    CalibrationQuestionnaireNode,
    FinalReviewNode,
    UserQuestionNode,
)

# 🆕 v2.2: 角色选择质量审核节点
from .nodes.role_selection_quality_review import RoleSelectionQualityReviewNode, role_selection_quality_review_node

# 导出所有类（向后兼容）
__all__ = [
    "CalibrationQuestionnaireNode",
    # "AnalysisReviewNode",  # 🗑️ v2.2: 已废弃
    "FinalReviewNode",
    "UserQuestionNode",
    "RoleSelectionQualityReviewNode",  # 🆕 v2.2
    "role_selection_quality_review_node",  # 🆕 v2.2
]
