"""
简单测试验证conftest.py的fixtures是否工作
"""
import pytest


def test_basic_fixture_works():
    """测试基础pytest功能"""
    assert True


@pytest.mark.asyncio
async def test_async_works():
    """测试async功能"""
    import asyncio
    await asyncio.sleep(0.001)
    assert True


def test_app_fixture(app):
    """测试app fixture"""
    assert app is not None
    assert hasattr(app, 'routes')


@pytest.mark.asyncio
async def test_client_fixture(client):
    """测试client fixture - 简单GET请求"""
    response = await client.get("/")
    # 不管返回什么状态码，只要能发送请求就说明fixture工作
    assert response is not None
    assert response.status_code in [200, 404, 405, 500]  # 任何有效HTTP状态码
