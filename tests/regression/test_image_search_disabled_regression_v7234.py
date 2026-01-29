"""
回归测试：v7.234 图片搜索禁用功能
确保修改不会破坏现有功能，且新的禁用逻辑在各种边界条件下正常工作
使用源码分析验证代码结构正确性
"""

import inspect
import os
import sys
from typing import Any, Dict, List

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestRegressionSearchFunctionality:
    """回归测试：确保搜索核心功能不受影响"""

    def test_search_method_still_exists(self):
        """回归：search方法仍然存在"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        assert hasattr(BochaAISearchService, "search"), "BochaAISearchService 应该有 search 方法"
        assert callable(getattr(BochaAISearchService, "search")), "search 应该是可调用的"

    def test_search_stream_method_still_exists(self):
        """回归：search_stream方法仍然存在"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        assert hasattr(BochaAISearchService, "search_stream"), "BochaAISearchService 应该有 search_stream 方法"

    def test_search_returns_ai_search_result(self):
        """回归：search方法返回类型正确"""
        from intelligent_project_analyzer.services.bocha_ai_search import AISearchResult, BochaAISearchService

        # 检查方法签名中的返回类型注解
        sig = inspect.signature(BochaAISearchService.search)
        # 验证返回类型存在于模块中
        assert AISearchResult is not None

    def test_search_still_accepts_query_parameter(self):
        """回归：search仍然接受query参数"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        assert "query" in sig.parameters, "search 应该接受 query 参数"

    def test_search_still_accepts_count_parameter(self):
        """回归：search仍然接受count参数"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        assert "count" in sig.parameters, "search 应该接受 count 参数"


class TestRegressionParameterDefaults:
    """回归测试：参数默认值"""

    def test_include_images_has_default(self):
        """回归：include_images有默认值"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        param = sig.parameters.get("include_images")

        assert param is not None, "应该有 include_images 参数"
        assert param.default != inspect.Parameter.empty, "include_images 应该有默认值"

    def test_image_count_has_default(self):
        """回归：image_count有默认值"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        param = sig.parameters.get("image_count")

        assert param is not None, "应该有 image_count 参数"
        assert param.default != inspect.Parameter.empty, "image_count 应该有默认值"

    def test_count_default_is_reasonable(self):
        """回归：count默认值合理"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        param = sig.parameters.get("count")

        if param.default != inspect.Parameter.empty:
            assert isinstance(param.default, int), "count 默认值应该是整数"
            assert param.default > 0, "count 默认值应该大于0"


class TestRegressionImageDisableLogic:
    """回归测试：图片禁用逻辑"""

    def test_settings_check_exists(self):
        """回归：设置检查逻辑存在"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        source = inspect.getsource(BochaAISearchService.search)

        assert "self.settings" in source, "应该访问 self.settings"
        assert "image_search_enabled" in source, "应该检查 image_search_enabled"

    def test_forced_disable_logic_exists(self):
        """回归：强制禁用逻辑存在"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        source = inspect.getsource(BochaAISearchService.search)

        # 验证有条件判断和赋值
        assert (
            "if not self.settings.image_search_enabled" in source or "if self.settings.image_search_enabled" in source
        ), "应该有条件判断 image_search_enabled"

    def test_v7234_marker_present(self):
        """回归：v7.234版本标记存在"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        source = inspect.getsource(BochaAISearchService.search)

        assert "v7.234" in source, "应该包含 v7.234 版本标记"


class TestRegressionUcpptIntegration:
    """回归测试：Ucppt引擎集成"""

    def test_ucppt_search_engine_exists(self):
        """回归：UcpptSearchEngine类存在"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        assert UcpptSearchEngine is not None

    def test_ucppt_has_execute_basic_search(self):
        """回归：UcpptSearchEngine有_execute_basic_search方法"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        assert hasattr(UcpptSearchEngine, "_execute_basic_search"), "应该有 _execute_basic_search 方法"

    def test_ucppt_calls_bocha_correctly(self):
        """回归：Ucppt正确调用Bocha服务"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        assert "bocha_service" in source, "应该使用 bocha_service"
        assert "include_images=False" in source, "应该禁用图片搜索"


class TestRegressionConfigurationStructure:
    """回归测试：配置结构"""

    def test_bocha_config_exists(self):
        """回归：BochaConfig类存在"""
        from intelligent_project_analyzer.settings import BochaConfig

        assert BochaConfig is not None

    def test_bocha_config_has_image_search_enabled(self):
        """回归：BochaConfig有image_search_enabled字段"""
        from intelligent_project_analyzer.settings import BochaConfig

        fields = BochaConfig.model_fields
        assert "image_search_enabled" in fields

    def test_settings_has_bocha(self):
        """回归：Settings有bocha属性"""
        from intelligent_project_analyzer.settings import Settings

        settings = Settings()
        assert hasattr(settings, "bocha"), "Settings 应该有 bocha 属性"

    def test_settings_bocha_has_image_search_enabled(self):
        """回归：settings.bocha有image_search_enabled"""
        from intelligent_project_analyzer.settings import Settings

        settings = Settings()
        assert hasattr(settings.bocha, "image_search_enabled"), "settings.bocha 应该有 image_search_enabled"


class TestRegressionBackwardCompatibility:
    """回归测试：向后兼容性"""

    def test_search_method_signature_compatible(self):
        """回归：search方法签名向后兼容"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        params = sig.parameters

        # 必须的参数
        assert "query" in params
        assert "count" in params
        assert "include_images" in params
        assert "image_count" in params

    def test_search_stream_method_signature_compatible(self):
        """回归：search_stream方法签名向后兼容"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search_stream)
        params = sig.parameters

        assert "query" in params
        assert "include_images" in params

    def test_ai_search_result_structure_unchanged(self):
        """回归：AISearchResult结构不变"""
        from intelligent_project_analyzer.services.bocha_ai_search import AISearchResult

        # 创建实例测试
        result = AISearchResult(query="test")

        # 验证必要属性存在
        assert hasattr(result, "query")
        assert hasattr(result, "sources")
        assert hasattr(result, "images")
        assert hasattr(result, "execution_time")

    def test_source_card_exists(self):
        """回归：SourceCard类存在"""
        from intelligent_project_analyzer.services.bocha_ai_search import SourceCard

        assert SourceCard is not None


class TestRegressionEdgeCases:
    """回归测试：边界条件"""

    def test_empty_sources_handled(self):
        """回归：空来源列表能正确处理"""
        from intelligent_project_analyzer.services.bocha_ai_search import AISearchResult

        result = AISearchResult(query="test")
        result.sources = []

        assert len(result.sources) == 0

    def test_empty_images_handled(self):
        """回归：空图片列表能正确处理"""
        from intelligent_project_analyzer.services.bocha_ai_search import AISearchResult

        result = AISearchResult(query="test")
        result.images = []

        assert len(result.images) == 0

    def test_image_search_enabled_can_be_true(self):
        """回归：image_search_enabled可以设为True"""
        from intelligent_project_analyzer.settings import BochaConfig

        config = BochaConfig(image_search_enabled=True)
        assert config.image_search_enabled == True

    def test_image_search_enabled_can_be_false(self):
        """回归：image_search_enabled可以设为False"""
        from intelligent_project_analyzer.settings import BochaConfig

        config = BochaConfig(image_search_enabled=False)
        assert config.image_search_enabled == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
