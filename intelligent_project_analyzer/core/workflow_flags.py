"""
工作流标志管理器

统一管理工作流中需要跨节点传递的控制标志，避免手动传递导致的遗漏和重复代码。
"""

from typing import Dict, Any, Set
from loguru import logger


class WorkflowFlagManager:
    """
    工作流标志管理器

    自动保留需要在节点间传递的持久化标志，消除手动传递的重复代码。

    使用场景：
    - 在节点的 Command.update 中自动保留标志
    - 避免标志丢失导致的流程错误
    - 集中管理标志定义

    示例：
        >>> state = {"skip_unified_review": True, "user_input": "test"}
        >>> update = {"calibration_processed": True}
        >>> update = WorkflowFlagManager.preserve_flags(state, update)
        >>> assert update["skip_unified_review"] == True
    """

    # 定义需要自动传递的持久化标志
    # 🔧 v7.24: 添加问卷相关的关键状态，确保 resume 后不丢失
    PERSISTENT_FLAGS: Set[str] = {
        "skip_unified_review",      # 跳过统一任务审核
        "skip_calibration",          # 跳过校准问卷
        "is_followup",               # 追问模式
        "is_rerun",                  # 重新运行标志
        "calibration_skipped",       # 问卷已跳过
        "calibration_processed",     # 问卷已处理（在某些路径需要保留）
        "calibration_answers",       # 🆕 v7.24: 问卷答案（防止 resume 后丢失）
        "questionnaire_summary",     # 🆕 v7.24: 问卷摘要（防止 resume 后丢失）
        "questionnaire_responses",   # 🆕 v7.24: 问卷响应（防止 resume 后丢失）
    }

    @staticmethod
    def preserve_flags(
        state: Dict[str, Any],
        update: Dict[str, Any],
        exclude: Set[str] = None
    ) -> Dict[str, Any]:
        """
        自动保留持久化标志

        从 state 中提取所有持久化标志，并添加到 update 中（如果 update 中未显式设置）。

        Args:
            state: 当前状态字典
            update: 待更新的状态字典
            exclude: 需要排除的标志集合（可选）

        Returns:
            更新后的 update 字典（包含保留的标志）

        示例：
            >>> state = {"skip_unified_review": True, "user_input": "test"}
            >>> update = {"calibration_processed": True}
            >>> result = WorkflowFlagManager.preserve_flags(state, update)
            >>> assert result["skip_unified_review"] == True
            >>> assert result["calibration_processed"] == True
        """
        exclude = exclude or set()
        preserved_count = 0

        for flag in WorkflowFlagManager.PERSISTENT_FLAGS:
            # 跳过排除的标志
            if flag in exclude:
                continue

            # 如果 state 中有该标志且 update 中未显式设置，则保留
            if state.get(flag) and flag not in update:
                update[flag] = state[flag]
                preserved_count += 1

        if preserved_count > 0:
            logger.debug(f"🔍 [FlagManager] 自动保留 {preserved_count} 个标志")

        return update

    @staticmethod
    def add_flag(flag_name: str) -> None:
        """
        动态添加新的持久化标志

        Args:
            flag_name: 标志名称

        示例：
            >>> WorkflowFlagManager.add_flag("custom_flag")
            >>> assert "custom_flag" in WorkflowFlagManager.PERSISTENT_FLAGS
        """
        WorkflowFlagManager.PERSISTENT_FLAGS.add(flag_name)
        logger.info(f"✅ [FlagManager] 添加持久化标志: {flag_name}")

    @staticmethod
    def remove_flag(flag_name: str) -> None:
        """
        移除持久化标志

        Args:
            flag_name: 标志名称

        示例:
            >>> WorkflowFlagManager.remove_flag("custom_flag")
            >>> assert "custom_flag" not in WorkflowFlagManager.PERSISTENT_FLAGS
        """
        if flag_name in WorkflowFlagManager.PERSISTENT_FLAGS:
            WorkflowFlagManager.PERSISTENT_FLAGS.remove(flag_name)
            logger.info(f"✅ [FlagManager] 移除持久化标志: {flag_name}")

    @staticmethod
    def get_flags(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取 state 中的所有持久化标志

        Args:
            state: 当前状态字典

        Returns:
            包含所有持久化标志的字典

        示例:
            >>> state = {"skip_unified_review": True, "user_input": "test", "is_followup": False}
            >>> flags = WorkflowFlagManager.get_flags(state)
            >>> assert flags == {"skip_unified_review": True, "is_followup": False}
        """
        return {
            flag: state[flag]
            for flag in WorkflowFlagManager.PERSISTENT_FLAGS
            if flag in state and state[flag]
        }

    @staticmethod
    def clear_flags(update: Dict[str, Any], flags: Set[str] = None) -> Dict[str, Any]:
        """
        清除指定的标志（设置为 False 或 None）

        Args:
            update: 待更新的状态字典
            flags: 需要清除的标志集合（默认清除所有持久化标志）

        Returns:
            更新后的 update 字典

        示例:
            >>> update = {"calibration_processed": True}
            >>> result = WorkflowFlagManager.clear_flags(update, {"skip_unified_review"})
            >>> assert result["skip_unified_review"] == False
        """
        flags_to_clear = flags or WorkflowFlagManager.PERSISTENT_FLAGS

        for flag in flags_to_clear:
            update[flag] = False

        logger.debug(f"🔍 [FlagManager] 清除 {len(flags_to_clear)} 个标志")
        return update
