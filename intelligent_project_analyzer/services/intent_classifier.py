"""
意图分类服务

功能：识别用户问题的意图类型
"""

from typing import List, Optional, Literal
from loguru import logger


class IntentClassifier:
    """意图分类器"""
    
    # 意图识别规则
    INTENT_PATTERNS = {
        "clarification": [
            "什么意思", "解释", "说明", "澄清", "如何理解",
            "为什么", "怎么", "是什么", "含义", "定义"
        ],
        "deep_dive": [
            "详细", "深入", "展开", "补充", "更多",
            "具体", "案例", "实例", "举例", "细节"
        ],
        "regenerate": [
            "重新生成", "修改", "优化", "改进", "调整",
            "重新", "再", "重做"
        ],
        "new_analysis": [
            "新的分析", "另一个项目", "重新开始", "新项目",
            "开始新", "换一个"
        ]
    }
    
    def classify(
        self,
        question: str,
        history: Optional[List] = None
    ) -> Literal["clarification", "deep_dive", "regenerate", "new_analysis", "general"]:
        """
        分类用户意图
        
        Args:
            question: 用户问题
            history: 对话历史（暂未使用）
        
        Returns:
            意图类型
        """
        question_lower = question.lower()
        
        # 规则匹配
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in question_lower:
                    logger.info(f"Intent matched: {intent} (pattern: {pattern})")
                    return intent
        
        # 默认为一般性问答
        logger.info("Intent classified as: general (no pattern matched)")
        return "general"
