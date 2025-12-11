"""
问卷组件模块

提供问卷生成、调整和答案解析功能，支持战略校准问卷的模块化管理。

v7.4 更新：
- 新增 KeywordExtractor：智能关键词提取，支持领域识别和核心概念提取
- 新增 DomainSpecificQuestionGenerator：基于领域生成专业问题
- 优化 FallbackQuestionGenerator：使用提取的关键词生成定制问题
- 优化 ConflictQuestionGenerator：冲突问题需由用户约束激活
"""

from .context import QuestionContext, KeywordExtractor
from .generators import (
    FallbackQuestionGenerator,
    PhilosophyQuestionGenerator,
    BiddingStrategyGenerator,
    ConflictQuestionGenerator,
    DomainSpecificQuestionGenerator
)
from .adjusters import QuestionAdjuster
from .parsers import AnswerParser

__all__ = [
    "QuestionContext",
    "KeywordExtractor",
    "FallbackQuestionGenerator",
    "PhilosophyQuestionGenerator",
    "BiddingStrategyGenerator",
    "ConflictQuestionGenerator",
    "DomainSpecificQuestionGenerator",
    "QuestionAdjuster",
    "AnswerParser",
]
