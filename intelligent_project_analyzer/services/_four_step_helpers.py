"""
4步骤搜索流程编排服务 (v1.0)

实现智能、开放、不硬编码的4步骤搜索流程：
- Step 1: 深度分析 - 动态生成输出框架
- Step 2: 搜索任务分解 - 将框架转化为具体查询
- Step 3: 智能搜索执行 - 动态增补查询
- Step 4: 总结生成 - 灵活的内容驱动输出

核心原则：
1. 智能、开放、不硬编码
2. 职责分离
3. 自适应搜索
4. 用户控制

Author: AI Assistant
Created: 2026-02-01
Version: 1.0
"""

import json
import os
import re
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Tuple

import yaml
from loguru import logger

# 导入数据结构
from intelligent_project_analyzer.core.four_step_flow_types import (
    DeepAnalysisResult,
    Discovery,
    ExecutionAdvice,
    ExecutionStrategy,
    FourStepFlowState,
    FrameworkAddition,
    HumanDimensions,
    L1ProblemDeconstruction,
    L2MotivationDimension,
    L3CoreTension,
    L4JTBDDefinition,
    L5SharpnessTest,
    OutputBlock,
    OutputBlockSubItem,
    OutputFramework,
    Priority,
    QualityAssessment,
    SearchDirection,  # Step 1.5 新增
    SearchExecutionConfig,
    SearchQuery,
    SearchResultAnalysis,
    SearchTaskList,
    SupplementaryQuery,
    TriggerType,
    Understanding,
    ValidationCheck,
    ValidationReport,
)

# 导入LLM工厂
from intelligent_project_analyzer.services.llm_factory import LLMFactory

# 导入搜索方向生成器 (Step 1.5)
from intelligent_project_analyzer.services.search_direction_generator import (
    SearchDirectionGenerator,
)

# 导入搜索服务
try:
    from intelligent_project_analyzer.services.bocha_ai_search import (
        get_ai_search_service,
    )

    SEARCH_SERVICE_AVAILABLE = True
except ImportError:
    SEARCH_SERVICE_AVAILABLE = False
    logger.warning("️ 搜索服务未可用")


# ============================================================================
# 配置加载
# ============================================================================


class PromptLoader:
    """Prompt配置加载器"""

    @staticmethod
    def load_prompt_config(prompt_file: str) -> Dict[str, Any]:
        """
        加载prompt配置文件

        Args:
            prompt_file: prompt文件名（如 "step1_deep_analysis.yaml"）

        Returns:
            配置字典
        """
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "prompts", prompt_file)

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.debug(f" 加载prompt配置: {prompt_file}")
            return config
        except Exception as e:
            logger.error(f" 加载prompt配置失败 {prompt_file}: {e}")
            raise


# ============================================================================
# 重复内容后处理清理
# ============================================================================


def clean_repetitive_content(content: str) -> str:
    """
    清理 LLM 输出中的重复内容（后处理）

    策略：保守处理，只清理明确的重复模式
    - 检测 "方案高参来帮您" 是否出现多次
    - 如果出现多次，截取到第二次出现之前的内容

    Args:
        content: LLM 生成的完整内容

    Returns:
        清理后的内容
    """
    # 优先：如果存在明确的结束标记，直接截断
    end_marker = "【输出到此结束】"
    end_idx = content.find(end_marker)
    if end_idx != -1:
        trimmed = content[: end_idx + len(end_marker)].strip()
        return trimmed

    # 关键段落标记，用于检测重复
    markers = [
        "方案高参来帮您",
        "【您将获得什么】",
        "**【您将获得什么】",
        "【我们如何理解您的需求】",
        "**【我们如何理解您的需求】**",
        "您面临的挑战：",
        "我们发现的深层需求：",
        "我们的分析维度：",
        "我们的设计重点：",
    ]

    def find_second_occurrence(text: str, marker: str) -> Tuple[int, int]:
        first = text.find(marker)
        if first == -1:
            return -1, -1
        second = text.find(marker, first + len(marker))
        return first, second

    candidates: List[Tuple[str, int, int]] = []
    for marker in markers:
        first_idx, second_idx = find_second_occurrence(content, marker)
        if first_idx != -1 and second_idx != -1:
            # 避免同一段内的误判：重复距离太近则忽略
            if second_idx - first_idx >= 100:
                candidates.append((marker, first_idx, second_idx))

    if not candidates:
        return content

    # 选择最早出现的"重复起点"
    marker, first_idx, second_idx = min(candidates, key=lambda x: x[2])

    logger.warning(f"️ 检测到重复内容: marker='{marker}' 第一次位置={first_idx}，第二次位置={second_idx}")
    logger.info(f"️ 截取内容长度: {len(content)} → {second_idx}")

    cleaned = content[:second_idx].strip()

    # 确保结尾是合理的（不是在句子中间截断）
    # 如果截断后没有以标点或换行结尾，往前找到最后一个完整段落
    if cleaned and not cleaned.endswith(("\n", "。", "！", "？", "）", "」", "】")):
        last_newline = cleaned.rfind("\n\n")
        if last_newline > len(cleaned) * 0.8:  # 只有在最后 20% 内找到换行才截断
            cleaned = cleaned[:last_newline].strip()

    return cleaned


__all__ = ["PromptLoader", "clean_repetitive_content"]
