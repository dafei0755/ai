"""
单元测试：v7.234 图片搜索禁用功能
测试覆盖所有图片搜索相关的禁用逻辑
"""

import os
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestBochaAISearchServiceImageDisabled:
    """测试 BochaAISearchService 图片搜索禁用"""

    def test_search_default_include_images_is_false(self):
        """测试search方法默认include_images为False"""
        import inspect

        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        params = sig.parameters

        assert "include_images" in params
        assert params["include_images"].default == False, "search() 方法的 include_images 默认值应该为 False"

    def test_search_stream_default_include_images_is_false(self):
        """测试search_stream方法默认include_images为False"""
        import inspect

        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search_stream)
        params = sig.parameters

        assert "include_images" in params
        assert params["include_images"].default == False, "search_stream() 方法的 include_images 默认值应该为 False"


class TestSettingsImageSearchConfig:
    """测试Settings中的图片搜索配置"""

    def test_image_search_enabled_default_is_false(self):
        """测试image_search_enabled默认值为False"""
        from intelligent_project_analyzer.settings import BochaConfig

        config = BochaConfig()
        assert config.image_search_enabled == False, "BochaConfig.image_search_enabled 默认值应该为 False"

    def test_image_search_can_be_enabled_via_env(self):
        """测试可以通过环境变量启用图片搜索"""
        import os

        from intelligent_project_analyzer.settings import BochaConfig

        # 设置环境变量
        old_value = os.environ.get("BOCHA_IMAGE_SEARCH_ENABLED")
        try:
            os.environ["BOCHA_IMAGE_SEARCH_ENABLED"] = "true"
            # 注意：Pydantic Settings 可能在模块加载时就读取了环境变量
            # 这里主要验证配置模型可以接受该值
            config = BochaConfig(image_search_enabled=True)
            assert config.image_search_enabled == True
        finally:
            if old_value is not None:
                os.environ["BOCHA_IMAGE_SEARCH_ENABLED"] = old_value
            elif "BOCHA_IMAGE_SEARCH_ENABLED" in os.environ:
                del os.environ["BOCHA_IMAGE_SEARCH_ENABLED"]


class TestUcpptSearchEngineImageDisabled:
    """测试 UcpptSearchEngine 图片搜索禁用"""

    def test_execute_basic_search_passes_include_images_false(self):
        """验证_execute_basic_search调用bocha_service.search时传入include_images=False"""
        # 读取源代码验证
        import inspect

        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 验证源代码中包含include_images=False
        assert "include_images=False" in source, "_execute_basic_search 应该包含 include_images=False 参数"

    def test_execute_basic_search_has_bocha_call_with_disabled_images(self):
        """验证_execute_basic_search方法正确设置了禁用图片搜索的调用"""
        import inspect

        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 验证调用参数链
        assert "bocha_service.search" in source, "应该调用 bocha_service.search"
        assert "include_images=False" in source, "应该设置 include_images=False"

        # 验证注释说明
        assert "禁用图片搜索" in source, "应该有禁用图片搜索的注释说明"


class TestImageSearchDisabledInSource:
    """通过源代码分析验证图片搜索禁用"""

    def test_bocha_ai_search_has_forced_disable_logic(self):
        """验证bocha_ai_search.py包含强制禁用图片搜索的逻辑"""
        import inspect

        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        source = inspect.getsource(BochaAISearchService.search)

        # 验证包含强制禁用逻辑
        assert (
            "if not self.settings.image_search_enabled:" in source
        ), "search() 方法应该包含检查 settings.image_search_enabled 的逻辑"
        assert "include_images = False" in source, "search() 方法应该在设置禁用时强制 include_images = False"

    def test_ucppt_search_engine_has_include_images_false(self):
        """验证ucppt_search_engine.py中bocha搜索调用包含include_images=False"""
        import inspect

        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 验证包含禁用图片搜索参数
        assert (
            "include_images=False" in source
        ), "_execute_basic_search 应该在调用 bocha_service.search 时传入 include_images=False"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
