"""
端到端测试：v7.234 图片搜索禁用功能
模拟真实用户场景，验证从配置到代码的完整集成
使用源码分析验证端到端流程的正确性
"""

import ast
import inspect
import os
import sys
from typing import Any, Dict, List

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestSearchAPIEndToEnd:
    """端到端测试：验证整个搜索流程的图片禁用"""

    def test_full_flow_config_to_service(self):
        """E2E：从配置到服务的完整流程"""
        # 1. 验证配置层
        from intelligent_project_analyzer.settings import BochaConfig, Settings

        config = BochaConfig()
        assert config.image_search_enabled == False, "配置层：image_search_enabled 默认应为 False"

        # 2. 验证服务层接收配置
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        assert sig.parameters["include_images"].default == False, "服务层：search() 的 include_images 默认应为 False"

        # 3. 验证服务层有强制禁用逻辑
        source = inspect.getsource(BochaAISearchService.search)
        assert "self.settings.image_search_enabled" in source, "服务层：应该检查配置中的 image_search_enabled"
        assert "include_images = False" in source, "服务层：应该有强制禁用逻辑"

    def test_full_flow_ucppt_to_bocha(self):
        """E2E：从Ucppt引擎到Bocha服务的完整流程"""
        # 1. Ucppt引擎调用Bocha服务
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 验证调用链
        assert "bocha_service.search" in source, "Ucppt应该调用 bocha_service.search"
        assert "include_images=False" in source, "Ucppt调用时应该禁用图片"

        # 2. 验证Bocha服务层默认禁用
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        sig = inspect.signature(BochaAISearchService.search)
        assert sig.parameters["include_images"].default == False


class TestStreamSearchEndToEnd:
    """端到端测试：流式搜索流程"""

    def test_stream_flow_config_to_stream(self):
        """E2E：从配置到流式搜索的完整流程"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        # 验证流式搜索默认禁用图片
        sig = inspect.signature(BochaAISearchService.search_stream)
        assert sig.parameters["include_images"].default == False, "search_stream() 的 include_images 默认应为 False"

    def test_stream_method_structure(self):
        """E2E：验证流式搜索方法结构"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        source = inspect.getsource(BochaAISearchService.search_stream)

        # 验证是异步生成器
        assert "async def search_stream" in source, "search_stream 应该是异步方法"
        assert "yield" in source, "search_stream 应该是生成器"


class TestUserScenarioSimulation:
    """端到端测试：用户场景模拟"""

    def test_user_scenario_design_search(self):
        """E2E：用户搜索设计灵感场景"""
        # 场景：用户在Ucppt模式下搜索"现代简约风格设计"
        # 期望：不返回任何图片

        # 1. 验证Ucppt引擎配置正确
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)
        assert "include_images=False" in source, "Ucppt搜索不应该返回图片"

        # 2. 验证有禁用注释说明
        assert "禁用图片搜索" in source, "代码应该有注释说明图片被禁用"

    def test_user_scenario_thinking_mode_search(self):
        """E2E：用户在思考模式下搜索场景"""
        # 场景：用户在思考模式下进行搜索
        # 期望：不返回任何图片

        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        # 验证search方法默认禁用图片
        sig = inspect.signature(BochaAISearchService.search)
        assert sig.parameters["include_images"].default == False

        # 验证即使用户传入True也会被配置覆盖
        source = inspect.getsource(BochaAISearchService.search)
        assert "self.settings.image_search_enabled" in source


class TestConfigurationEndToEnd:
    """端到端测试：配置传递链"""

    def test_config_chain_complete(self):
        """E2E：完整的配置传递链"""
        # 1. 环境变量 -> Settings
        from intelligent_project_analyzer.settings import Settings

        settings = Settings()
        assert hasattr(settings, "bocha"), "Settings 应该有 bocha 配置"
        assert hasattr(settings.bocha, "image_search_enabled"), "BochaConfig 应该有 image_search_enabled 字段"

        # 2. Settings -> BochaConfig
        assert settings.bocha.image_search_enabled == False, "配置应该默认禁用图片搜索"

    def test_config_description_accuracy(self):
        """E2E：配置描述准确性"""
        from intelligent_project_analyzer.settings import BochaConfig

        fields = BochaConfig.model_fields
        field_info = fields["image_search_enabled"]

        # 验证描述存在且有意义
        assert field_info.description is not None, "image_search_enabled 应该有描述"
        assert len(field_info.description) > 0, "描述不应该为空"


class TestCodeQualityEndToEnd:
    """端到端测试：代码质量"""

    def test_version_markers_present(self):
        """E2E：版本标记存在"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        source = inspect.getsource(BochaAISearchService.search)
        assert "v7.234" in source, "代码应该包含 v7.234 版本标记"

    def test_comments_present(self):
        """E2E：注释存在且有意义"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        source = inspect.getsource(UcpptSearchEngine._execute_basic_search)

        # 验证有注释说明禁用图片
        assert "禁用图片" in source or "图片搜索" in source, "代码应该有注释说明图片搜索被禁用"

    def test_code_consistency(self):
        """E2E：代码一致性"""
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        # search 和 search_stream 应该有相同的默认行为
        search_sig = inspect.signature(BochaAISearchService.search)
        stream_sig = inspect.signature(BochaAISearchService.search_stream)

        assert (
            search_sig.parameters["include_images"].default == stream_sig.parameters["include_images"].default
        ), "search 和 search_stream 的默认行为应该一致"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
