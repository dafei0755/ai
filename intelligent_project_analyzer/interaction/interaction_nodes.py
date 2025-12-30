"""
人机交互节点 - 兼容性导入模块

⚠️ 此文件已重构：所有节点类已拆分到 nodes/ 子目录
为保持向后兼容，此文件继续提供导入接口

新结构：
- nodes/calibration_questionnaire.py - 战略校准问卷节点
- nodes/requirements_confirmation.py - 需求确认节点
- nodes/analysis_review.py - 分析审核节点
- nodes/final_review.py - 最终审核节点
- nodes/user_question.py - 用户追问节点
"""

# 从 nodes 子包导入所有节点类
from .nodes import (
    CalibrationQuestionnaireNode,
    RequirementsConfirmationNode,
    AnalysisReviewNode,
    FinalReviewNode,
    UserQuestionNode,
)

# 导出所有类（向后兼容）
__all__ = [
    "CalibrationQuestionnaireNode",
    "RequirementsConfirmationNode",
    "AnalysisReviewNode",
    "FinalReviewNode",
    "UserQuestionNode",
]
