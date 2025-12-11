"""
工作流标志管理器测试

测试 WorkflowFlagManager 的标志保留和管理功能。
"""

import pytest
from intelligent_project_analyzer.core.workflow_flags import WorkflowFlagManager


class TestWorkflowFlagManager:
    """测试工作流标志管理器"""

    def test_preserve_single_flag(self):
        """测试保留单个标志"""
        state = {"skip_unified_review": True, "user_input": "test"}
        update = {"calibration_processed": True}

        result = WorkflowFlagManager.preserve_flags(state, update)

        assert result["skip_unified_review"] == True
        assert result["calibration_processed"] == True

    def test_preserve_multiple_flags(self):
        """测试保留多个标志"""
        state = {
            "skip_unified_review": True,
            "is_followup": True,
            "skip_calibration": True,
            "user_input": "test"
        }
        update = {"calibration_processed": True}

        result = WorkflowFlagManager.preserve_flags(state, update)

        assert result["skip_unified_review"] == True
        assert result["is_followup"] == True
        assert result["skip_calibration"] == True
        assert result["calibration_processed"] == True

    def test_no_overwrite_explicit_flags(self):
        """测试不覆盖显式设置的标志"""
        state = {"skip_unified_review": True}
        update = {"skip_unified_review": False, "calibration_processed": True}

        result = WorkflowFlagManager.preserve_flags(state, update)

        # 显式设置的值不应被覆盖
        assert result["skip_unified_review"] == False
        assert result["calibration_processed"] == True

    def test_ignore_false_flags(self):
        """测试忽略 False 值的标志"""
        state = {"skip_unified_review": False, "is_followup": True}
        update = {"calibration_processed": True}

        result = WorkflowFlagManager.preserve_flags(state, update)

        # False 值的标志不应被保留
        assert "skip_unified_review" not in result or result["skip_unified_review"] == False
        assert result["is_followup"] == True

    def test_exclude_flags(self):
        """测试排除特定标志"""
        state = {
            "skip_unified_review": True,
            "is_followup": True,
            "skip_calibration": True
        }
        update = {"calibration_processed": True}

        result = WorkflowFlagManager.preserve_flags(
            state, update, exclude={"skip_calibration"}
        )

        assert result["skip_unified_review"] == True
        assert result["is_followup"] == True
        assert "skip_calibration" not in result

    def test_get_flags(self):
        """测试提取所有持久化标志"""
        state = {
            "skip_unified_review": True,
            "is_followup": False,
            "skip_calibration": True,
            "user_input": "test",
            "calibration_processed": True
        }

        flags = WorkflowFlagManager.get_flags(state)

        # 只返回值为 True 的持久化标志
        assert flags["skip_unified_review"] == True
        assert flags["skip_calibration"] == True
        assert flags["calibration_processed"] == True
        assert "is_followup" not in flags  # False 值不返回
        assert "user_input" not in flags  # 非持久化标志不返回

    def test_clear_flags(self):
        """测试清除标志"""
        update = {"calibration_processed": True}

        result = WorkflowFlagManager.clear_flags(
            update, flags={"skip_unified_review", "is_followup"}
        )

        assert result["skip_unified_review"] == False
        assert result["is_followup"] == False
        assert result["calibration_processed"] == True

    def test_add_flag(self):
        """测试动态添加标志"""
        original_flags = WorkflowFlagManager.PERSISTENT_FLAGS.copy()

        try:
            WorkflowFlagManager.add_flag("custom_flag")
            assert "custom_flag" in WorkflowFlagManager.PERSISTENT_FLAGS

            # 验证新标志可以被保留
            state = {"custom_flag": True}
            update = {}
            result = WorkflowFlagManager.preserve_flags(state, update)
            assert result["custom_flag"] == True

        finally:
            # 恢复原始标志集合
            WorkflowFlagManager.PERSISTENT_FLAGS = original_flags

    def test_remove_flag(self):
        """测试移除标志"""
        original_flags = WorkflowFlagManager.PERSISTENT_FLAGS.copy()

        try:
            # 添加一个临时标志
            WorkflowFlagManager.add_flag("temp_flag")
            assert "temp_flag" in WorkflowFlagManager.PERSISTENT_FLAGS

            # 移除标志
            WorkflowFlagManager.remove_flag("temp_flag")
            assert "temp_flag" not in WorkflowFlagManager.PERSISTENT_FLAGS

        finally:
            # 恢复原始标志集合
            WorkflowFlagManager.PERSISTENT_FLAGS = original_flags

    def test_empty_state(self):
        """测试空状态"""
        state = {}
        update = {"calibration_processed": True}

        result = WorkflowFlagManager.preserve_flags(state, update)

        # 空状态不应添加任何标志
        assert result == {"calibration_processed": True}

    def test_empty_update(self):
        """测试空更新"""
        state = {"skip_unified_review": True, "is_followup": True}
        update = {}

        result = WorkflowFlagManager.preserve_flags(state, update)

        # 应该保留所有持久化标志
        assert result["skip_unified_review"] == True
        assert result["is_followup"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
