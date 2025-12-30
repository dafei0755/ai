"""
最小化测试 - 验证pytest配置
"""
import pytest


def test_pytest_works():
    """验证pytest基础功能"""
    assert 1 + 1 == 2


def test_import_project():
    """验证项目模块可以导入"""
    from intelligent_project_analyzer.core.state import ProjectAnalysisState
    assert ProjectAnalysisState is not None


@pytest.mark.asyncio
async def test_async_works():
    """验证异步测试支持"""
    import asyncio
    await asyncio.sleep(0.001)
    assert True
