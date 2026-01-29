"""
集成测试：v7.234 图片搜索禁用功能
测试各组件之间的集成，确保图片搜索在整个搜索流程中被正确禁用
使用源码分析验证配置正确性
"""

import inspect
import os
import sys
from typing import Any, Dict, List

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestBochaServiceIntegration:
    """测试 BochaAISearchService 与设置的集成"""

    def test_search_method_default_disables_images(self):
        """集成测试：search方法默认禁用图片"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        params = sig.parameters

        # 验证默认值
        assert params["include_images"].default == False, "search() 的 include_images 默认应为 False"

    def test_search_method_has_settings_check(self):
        """集成测试：search方法包含设置检查逻辑"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        source = inspect.getsource(BochaAISearchService.search)

        # 验证包含设置检查
        assert "self.settings.image_search_enabled" in source, "search() 应该检查 settings.image_search_enabled"

        # 验证强制禁用逻辑
        assert "include_images = False" in source, "search() 应该在设置禁用时强制 include_images = False"

    def test_search_stream_method_default_disables_images(self):
        """集成测试：search_stream方法默认禁用图片"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search_stream)
        params = sig.parameters

        assert params["include_images"].default == False, "search_stream() 的 include_images 默认应为 False"


class TestUcpptEngineIntegration:
    """测试 UcpptSearchEngine 与 BochaAISearchService 的集成"""

    def test_ucppt_basic_search_disables_images(self):
        """集成测试：UcpptSearchEngine基础搜索禁用图片"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 验证调用链正确
        assert "bocha_service.search" in source, "_execute_basic_search 应该调用 bocha_service.search"
        assert "include_images=False" in source, "_execute_basic_search 调用时应该设置 include_images=False"

    def test_ucppt_has_image_disable_comment(self):
        """集成测试：UcpptSearchEngine包含图片禁用注释"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 验证有说明注释
        assert "禁用图片搜索" in source, "代码应该包含禁用图片搜索的说明注释"


class TestConfigurationFlow:
    """测试配置流程的正确性"""

    def test_settings_bocha_image_disabled_by_default(self):
        """测试设置加载时图片搜索默认禁用"""
        from intelligent_project_analyzer.settings import Settings

        settings = Settings()

        assert settings.bocha.image_search_enabled == False, "Settings 实例的 bocha.image_search_enabled 应该默认为 False"

    def test_bocha_config_default_value(self):
        """测试BochaConfig默认值正确"""
        from intelligent_project_analyzer.settings import BochaConfig

        config = BochaConfig()

        assert config.image_search_enabled == False, "BochaConfig.image_search_enabled 默认应为 False"

    def test_bocha_config_can_enable_images(self):
        """测试BochaConfig可以启用图片"""
        from intelligent_project_analyzer.settings import BochaConfig

        config = BochaConfig(image_search_enabled=True)

        assert config.image_search_enabled == True, "BochaConfig 应该允许显式启用图片搜索"

    def test_bocha_config_field_description_mentions_disable(self):
        """测试配置字段描述正确"""
        from intelligent_project_analyzer.settings import BochaConfig

        fields = BochaConfig.model_fields

        assert "image_search_enabled" in fields
        field_info = fields["image_search_enabled"]

        # 验证默认值
        assert field_info.default == False

        # 验证描述
        description = field_info.description or ""
        assert "禁用" in description or "Ucppt" in description, "image_search_enabled 描述应该说明默认禁用"


class TestCodeConsistency:
    """测试代码一致性"""

    def test_all_search_methods_have_include_images_parameter(self):
        """测试所有搜索方法都有include_images参数"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        # 检查search
        search_sig = inspect.signature(BochaAISearchService.search)
        assert "include_images" in search_sig.parameters

        # 检查search_stream
        stream_sig = inspect.signature(BochaAISearchService.search_stream)
        assert "include_images" in stream_sig.parameters

    def test_all_defaults_are_false(self):
        """测试所有默认值都是False"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        search_sig = inspect.signature(BochaAISearchService.search)
        stream_sig = inspect.signature(BochaAISearchService.search_stream)

        assert search_sig.parameters["include_images"].default == False
        assert stream_sig.parameters["include_images"].default == False

    def test_ucppt_uses_correct_parameter(self):
        """测试Ucppt使用正确的参数"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 确保使用的是关键字参数形式
        assert "include_images=False" in source, "Ucppt应该使用关键字参数形式 include_images=False"


class TestVersionMarkers:
    """测试版本标记"""

    def test_bocha_search_has_v7234_marker(self):
        """测试bocha_ai_search包含v7.234版本标记"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        source = inspect.getsource(BochaAISearchService.search)

        assert "v7.234" in source, "search() 方法应该包含 v7.234 版本标记"

    def test_ucppt_has_version_marker(self):
        """测试ucppt_search_engine包含版本标记"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 可能是v7.233或其他版本
        assert "v7.23" in source, "_execute_basic_search 应该包含版本标记"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
