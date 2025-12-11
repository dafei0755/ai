"""
统一输入验证节点单元测试

测试 UnifiedInputValidatorNode 的初始验证和二次验证功能
"""

import pytest
from unittest.mock import Mock, patch
from intelligent_project_analyzer.security.unified_input_validator_node import (
    UnifiedInputValidatorNode,
    InputRejectedNode
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState


class TestUnifiedInputValidatorInitialValidation:
    """测试初始验证功能"""

    def test_safe_design_input_high_confidence(self):
        """测试安全的设计类输入（高置信度）"""
        state = {
            "session_id": "test-session",
            "user_input": "我需要设计一个200平米的现代风格咖啡厅，位于商业街，目标客群是年轻白领"
        }

        # Mock LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"is_design": true, "confidence": 0.95, "categories": ["餐饮空间"], "reasoning": "明确的咖啡厅设计需求"}'
        )

        result = UnifiedInputValidatorNode.execute_initial_validation(
            state,
            store=None,
            llm_model=mock_llm
        )

        # 验证结果
        assert result.goto == "requirements_analyst"
        assert result.update["initial_validation_passed"] == True
        assert result.update["safety_check_passed"] == True
        assert result.update["domain_confidence"] >= 0.85
        assert result.update["needs_secondary_validation"] == False  # 高置信度跳过二次验证
        assert result.update["task_complexity"] in ["simple", "medium", "complex"]

    def test_safe_design_input_low_confidence(self):
        """测试安全的设计类输入（低置信度）- 用户确认为设计类"""
        state = {
            "session_id": "test-session",
            "user_input": "帮我做个东西"  # 更模糊的输入，不包含设计关键词
        }

        # Mock LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"is_design": "unclear", "confidence": 0.5, "categories": [], "reasoning": "需求不明确"}'
        )

        # Mock interrupt - 用户确认为设计类
        with patch("intelligent_project_analyzer.security.unified_input_validator_node.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "yes"  # 用户确认是设计类

            result = UnifiedInputValidatorNode.execute_initial_validation(
                state,
                store=None,
                llm_model=mock_llm
            )

            # 验证结果
            assert result.goto == "requirements_analyst"
            assert result.update["initial_validation_passed"] == True

    def test_non_design_input_high_confidence(self):
        """测试非设计类输入（高置信度）"""
        state = {
            "session_id": "test-session",
            "user_input": "帮我写一个Python爬虫程序"
        }

        # Mock LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"is_design": false, "confidence": 0.95, "categories": [], "reasoning": "编程开发需求"}'
        )

        result = UnifiedInputValidatorNode.execute_initial_validation(
            state,
            store=None,
            llm_model=mock_llm
        )

        # 验证结果
        assert result.goto == "input_rejected"
        assert result.update["rejection_reason"] == "not_design_related"

    def test_unsafe_content(self):
        """测试不安全内容"""
        state = {
            "session_id": "test-session",
            "user_input": "设计一个包含暴力血腥元素的空间"
        }

        # Mock LLM
        mock_llm = Mock()

        # Mock ContentSafetyGuard
        with patch("intelligent_project_analyzer.security.unified_input_validator_node.ContentSafetyGuard") as mock_guard:
            mock_guard_instance = Mock()
            mock_guard_instance.check.return_value = {
                "is_safe": False,
                "violations": [{"category": "暴力血腥", "severity": "high"}]
            }
            mock_guard.return_value = mock_guard_instance

            result = UnifiedInputValidatorNode.execute_initial_validation(
                state,
                store=None,
                llm_model=mock_llm
            )

            # 验证结果
            assert result.goto == "input_rejected"
            assert result.update["rejection_reason"] == "content_safety_violation"


class TestUnifiedInputValidatorSecondaryValidation:
    """测试二次验证功能"""

    def test_skip_secondary_validation_high_confidence(self):
        """测试跳过二次验证（高置信度）"""
        state = {
            "session_id": "test-session",
            "user_input": "设计咖啡厅",
            "domain_confidence": 0.90,
            "needs_secondary_validation": False,
            "agent_results": {
                "requirements_analyst": {
                    "structured_data": {
                        "project_task": "设计一个现代风格咖啡厅",
                        "project_overview": "200平米商业街咖啡厅"
                    }
                }
            }
        }

        result = UnifiedInputValidatorNode.execute_secondary_validation(
            state,
            store=None,
            llm_model=None
        )

        # 验证结果
        assert isinstance(result, dict)
        assert result["secondary_validation_skipped"] == True
        assert result["secondary_validation_reason"] == "high_initial_confidence"

    def test_secondary_validation_pass(self):
        """测试二次验证通过"""
        state = {
            "session_id": "test-session",
            "user_input": "设计空间",
            "domain_confidence": 0.70,
            "needs_secondary_validation": True,
            "agent_results": {
                "requirements_analyst": {
                    "structured_data": {
                        "project_task": "设计一个办公空间",
                        "project_overview": "500平米科技公司办公室"
                    }
                }
            }
        }

        # Mock LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"is_design": true, "confidence": 0.88, "categories": ["办公空间"], "reasoning": "明确的办公空间设计需求"}'
        )

        result = UnifiedInputValidatorNode.execute_secondary_validation(
            state,
            store=None,
            llm_model=mock_llm
        )

        # 验证结果
        assert isinstance(result, dict)
        assert result["secondary_validation_passed"] == True
        assert result["secondary_domain_confidence"] >= 0.85
        assert "confidence_delta" in result

    def test_domain_drift_detection(self):
        """测试领域漂移检测"""
        state = {
            "session_id": "test-session",
            "user_input": "设计空间",
            "domain_confidence": 0.70,
            "needs_secondary_validation": True,
            "agent_results": {
                "requirements_analyst": {
                    "structured_data": {
                        "project_task": "开发一个网站",
                        "project_overview": "电商平台前端开发"
                    }
                }
            }
        }

        # Mock LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"is_design": false, "confidence": 0.90, "categories": [], "reasoning": "编程开发需求"}'
        )

        # Mock interrupt
        with patch("intelligent_project_analyzer.security.unified_input_validator_node.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "reject"}

            result = UnifiedInputValidatorNode.execute_secondary_validation(
                state,
                store=None,
                llm_model=mock_llm
            )

            # 验证结果
            assert result.goto == "input_rejected"
            assert result.update["rejection_reason"] == "domain_drift_confirmed"


class TestInputRejectedNode:
    """测试输入拒绝节点"""

    def test_input_rejected(self):
        """测试输入拒绝"""
        state = {
            "session_id": "test-session",
            "rejection_reason": "content_safety_violation",
            "rejection_message": "输入包含不适当内容"
        }

        result = InputRejectedNode.execute(state, store=None)

        # 验证结果
        assert result["current_stage"] == "REJECTED"
        assert result["rejection_reason"] == "content_safety_violation"
        assert result["rejection_message"] == "输入包含不适当内容"
        assert result["final_status"] == "rejected"
        assert "completed_at" in result


class TestHelperMethods:
    """测试辅助方法"""

    def test_extract_project_summary_v35_format(self):
        """测试提取项目摘要（V3.5格式）"""
        requirements_result = {
            "project_task": "设计咖啡厅",
            "project_overview": "200平米现代风格咖啡厅",
            "core_objectives": ["营造舒适氛围", "提升品牌形象"],
            "design_challenge": "空间狭小，需要优化布局"
        }

        summary = UnifiedInputValidatorNode._extract_project_summary(requirements_result)

        assert "设计咖啡厅" in summary
        assert "200平米" in summary
        assert "营造舒适氛围" in summary

    def test_extract_project_summary_old_format(self):
        """测试提取项目摘要（旧格式）"""
        requirements_result = {
            "project_info": {
                "name": "咖啡厅设计",
                "type": "餐饮空间",
                "description": "现代风格咖啡厅"
            },
            "core_requirements": ["舒适氛围", "品牌形象"]
        }

        summary = UnifiedInputValidatorNode._extract_project_summary(requirements_result)

        assert "咖啡厅设计" in summary
        assert "餐饮空间" in summary

    def test_build_safety_rejection_message(self):
        """测试构造安全拒绝消息"""
        safety_result = {
            "violations": [{"category": "暴力血腥", "severity": "high"}]
        }

        message = UnifiedInputValidatorNode._build_safety_rejection_message(safety_result)

        assert "不适当的内容" in message
        assert "空间设计" in message

    def test_build_domain_guidance_message(self):
        """测试构造领域引导消息"""
        domain_result = {
            "detected_domain": "编程开发"
        }

        message = UnifiedInputValidatorNode._build_domain_guidance_message(domain_result)

        assert "专业领域" in message
        assert "空间设计" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
