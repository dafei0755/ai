"""
pytest配置文件：v7.214 深度搜索优化单元测试
"""

import asyncio
import os
import sys
from unittest.mock import patch

import pytest

# 添加项目路径到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# 配置异步测试
@pytest.fixture(scope="session")
def event_loop():
    """创建一个事件循环用于整个测试会话"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# 配置测试环境变量
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    test_env = {
        "DEEPSEEK_API_KEY": "test_deepseek_key_123456",
        "OPENROUTER_API_KEYS": "test_openrouter_key_123456",
        "OPENAI_API_KEY": "test_openai_key_123456",
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "WARNING",  # 减少测试时的日志输出
    }

    with patch.dict(os.environ, test_env):
        yield


# Mock外部依赖
@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """自动Mock外部依赖"""
    with patch("intelligent_project_analyzer.services.bocha_ai_search.get_ai_search_service"):
        with patch("intelligent_project_analyzer.tools.openalex_search.OpenAlexSearchTool"):
            with patch("intelligent_project_analyzer.tools.quality_control.SearchQualityControl"):
                yield


# 测试标记配置
pytest_plugins = []


# 自定义测试标记
def pytest_configure(config):
    """配置自定义测试标记"""
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "performance: 性能测试标记")
    config.addinivalue_line("markers", "slow: 慢速测试标记")


# 测试收集配置
def pytest_collection_modifyitems(config, items):
    """修改测试收集行为"""
    for item in items:
        # 为异步测试添加asyncio标记
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)

        # 根据测试名称自动添加标记
        if "test_performance" in item.name:
            item.add_marker(pytest.mark.performance)
        elif "test_integration" in item.name or "test_full_" in item.name:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
