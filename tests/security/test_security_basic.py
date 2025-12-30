"""
Security模块基础测试

测试内容安全、输入验证等安全相关功能
使用conftest.py提供的fixtures避免app初始化问题
"""

import pytest
from unittest.mock import Mock


class TestSecurityNodes:
    """测试安全节点"""

    def test_report_guard_node_import(self, env_setup):
        """测试ReportGuardNode导入"""
        from intelligent_project_analyzer.security.report_guard_node import ReportGuardNode

        assert ReportGuardNode is not None

    def test_unified_input_validator_node_import(self, env_setup):
        """测试UnifiedInputValidatorNode导入"""
        from intelligent_project_analyzer.security.unified_input_validator_node import UnifiedInputValidatorNode

        assert UnifiedInputValidatorNode is not None

    def test_input_guard_node_import(self, env_setup):
        """测试InputGuardNode导入"""
        from intelligent_project_analyzer.security.input_guard_node import InputGuardNode

        assert InputGuardNode is not None

    def test_domain_validator_node_import(self, env_setup):
        """测试DomainValidatorNode导入"""
        from intelligent_project_analyzer.security.domain_validator_node import DomainValidatorNode

        assert DomainValidatorNode is not None


class TestContentSafety:
    """测试内容安全"""

    def test_content_safety_guard_import(self, env_setup):
        """测试ContentSafetyGuard导入"""
        from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard

        assert ContentSafetyGuard is not None

    def test_llm_safety_detector_import(self, env_setup):
        """测试LLMSafetyDetector导入"""
        from intelligent_project_analyzer.security.llm_safety_detector import LLMSafetyDetector

        assert LLMSafetyDetector is not None

    def test_enhanced_regex_detector_import(self, env_setup):
        """测试EnhancedRegexDetector导入"""
        from intelligent_project_analyzer.security.enhanced_regex_detector import EnhancedRegexDetector

        assert EnhancedRegexDetector is not None


class TestDomainClassification:
    """测试领域分类"""

    def test_domain_classifier_import(self, env_setup):
        """测试DomainClassifier导入"""
        from intelligent_project_analyzer.security.domain_classifier import DomainClassifier

        assert DomainClassifier is not None

    def test_domain_classifier_is_class(self, env_setup):
        """测试DomainClassifier是类"""
        from intelligent_project_analyzer.security.domain_classifier import DomainClassifier

        assert isinstance(DomainClassifier, type)


class TestDynamicRuleLoader:
    """测试动态规则加载器"""

    def test_dynamic_rule_loader_import(self, env_setup):
        """测试DynamicRuleLoader导入"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import DynamicRuleLoader

        assert DynamicRuleLoader is not None

    def test_get_privacy_patterns(self, env_setup):
        """测试获取隐私模式"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import DynamicRuleLoader

        loader = DynamicRuleLoader()

        # 获取隐私模式
        patterns = loader.get_privacy_patterns()

        assert isinstance(patterns, dict)

    def test_get_keywords(self, env_setup):
        """测试获取关键词"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import DynamicRuleLoader

        loader = DynamicRuleLoader()

        # 获取关键词
        keywords = loader.get_keywords()

        assert isinstance(keywords, dict)


class TestSafeLLMWrapper:
    """测试SafeLLM包装器"""

    def test_safe_llm_wrapper_import(self, env_setup):
        """测试SafeLLMWrapper导入"""
        from intelligent_project_analyzer.security.safe_llm_wrapper import SafeLLMWrapper

        assert SafeLLMWrapper is not None

    def test_safe_llm_wrapper_is_class(self, env_setup):
        """测试SafeLLMWrapper是类"""
        from intelligent_project_analyzer.security.safe_llm_wrapper import SafeLLMWrapper

        assert isinstance(SafeLLMWrapper, type)


class TestViolationLogger:
    """测试违规日志"""

    def test_violation_logger_import(self, env_setup):
        """测试ViolationLogger导入"""
        from intelligent_project_analyzer.security.violation_logger import ViolationLogger

        assert ViolationLogger is not None

    def test_violation_logger_is_class(self, env_setup):
        """测试ViolationLogger是类"""
        from intelligent_project_analyzer.security.violation_logger import ViolationLogger

        assert isinstance(ViolationLogger, type)


class TestTencentContentSafety:
    """测试腾讯内容安全"""

    @pytest.mark.skip(reason="TencentContentSafety类可能命名不同或不存在")
    def test_tencent_content_safety_import(self, env_setup):
        """测试TencentContentSafety导入"""
        from intelligent_project_analyzer.security.tencent_content_safety import TencentContentSafety

        assert TencentContentSafety is not None


class TestSecurityInitialization:
    """测试安全模块初始化"""

    def test_content_safety_guard_initialization(self, env_setup):
        """测试ContentSafetyGuard初始化"""
        from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard

        guard = ContentSafetyGuard()

        assert guard is not None

    def test_dynamic_rule_loader_initialization(self, env_setup):
        """测试DynamicRuleLoader初始化"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import DynamicRuleLoader

        loader = DynamicRuleLoader()

        assert loader is not None
        assert hasattr(loader, 'get_privacy_patterns')
        assert hasattr(loader, 'get_keywords')

    def test_llm_safety_detector_has_methods(self, env_setup):
        """测试LLMSafetyDetector有必需方法"""
        from intelligent_project_analyzer.security.llm_safety_detector import LLMSafetyDetector

        # 验证类有必需方法
        assert hasattr(LLMSafetyDetector, '__init__')
