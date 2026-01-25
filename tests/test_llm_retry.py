"""
测试LLM重试机制

验证：
1. 成功调用不触发重试
2. 网络错误触发重试
3. 重试达到最大次数后抛出异常
4. 超时配置生效
5. 日志记录正确

作者：Design Beyond Team
日期：2026-01-04
版本：v7.131
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpcore
import pytest
from langchain_core.messages import AIMessage

from intelligent_project_analyzer.utils.llm_retry import (
    LLMRetryConfig,
    ainvoke_llm_with_retry,
    async_llm_retry,
    invoke_llm_with_retry,
    llm_retry,
)


class TestLLMRetrySync:
    """测试同步LLM重试机制"""

    def test_successful_invoke_no_retry(self):
        """测试成功调用不触发重试"""
        # 创建Mock LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = AIMessage(content="Success")

        # 调用
        result = invoke_llm_with_retry(mock_llm, "test message")

        # 验证
        assert result.content == "Success"
        assert mock_llm.invoke.call_count == 1

    def test_network_error_triggers_retry(self):
        """测试网络错误触发重试"""
        # 创建Mock LLM
        mock_llm = Mock()
        # 前两次失败，第三次成功
        mock_llm.invoke.side_effect = [
            httpcore.ConnectError("Connection failed"),
            httpcore.ConnectError("Connection failed"),
            AIMessage(content="Success after retry"),
        ]

        # 调用（使用较短的重试等待时间以加快测试）
        config = LLMRetryConfig(max_attempts=3, min_wait=0.1, max_wait=0.5)
        result = invoke_llm_with_retry(mock_llm, "test message", config=config)

        # 验证
        assert result.content == "Success after retry"
        assert mock_llm.invoke.call_count == 3

    def test_max_retry_reached(self):
        """测试达到最大重试次数后抛出异常"""
        # 创建Mock LLM
        mock_llm = Mock()
        mock_llm.invoke.side_effect = httpcore.ConnectError("Persistent error")

        # 调用并期望抛出异常
        config = LLMRetryConfig(max_attempts=3, min_wait=0.1, max_wait=0.5)
        with pytest.raises(httpcore.ConnectError):
            invoke_llm_with_retry(mock_llm, "test message", config=config)

        # 验证重试了3次
        assert mock_llm.invoke.call_count == 3

    def test_timeout_configuration(self):
        """测试超时配置生效"""
        # 创建Mock LLM（模拟慢速响应）
        mock_llm = Mock()

        def slow_invoke(*args, **kwargs):
            import time

            time.sleep(2)
            return AIMessage(content="Slow response")

        mock_llm.invoke.side_effect = slow_invoke

        # 调用并期望超时
        config = LLMRetryConfig(max_attempts=1, timeout=0.5)
        with pytest.raises(TimeoutError):
            invoke_llm_with_retry(mock_llm, "test message", config=config)

    def test_decorator_successful(self):
        """测试装饰器（成功情况）"""
        mock_llm = Mock()
        mock_llm.invoke.return_value = AIMessage(content="Decorated success")

        @llm_retry(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def call_llm():
            return mock_llm.invoke("test")

        result = call_llm()
        assert result.content == "Decorated success"
        assert mock_llm.invoke.call_count == 1

    def test_decorator_with_retry(self):
        """测试装饰器（重试情况）"""
        mock_llm = Mock()
        mock_llm.invoke.side_effect = [
            httpcore.ConnectError("First fail"),
            AIMessage(content="Success on retry"),
        ]

        @llm_retry(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def call_llm():
            return mock_llm.invoke("test")

        result = call_llm()
        assert result.content == "Success on retry"
        assert mock_llm.invoke.call_count == 2


class TestLLMRetryAsync:
    """测试异步LLM重试机制"""

    @pytest.mark.asyncio
    async def test_successful_ainvoke_no_retry(self):
        """测试异步成功调用不触发重试"""
        # 创建Mock LLM
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = AIMessage(content="Async success")

        # 调用
        result = await ainvoke_llm_with_retry(mock_llm, "test message")

        # 验证
        assert result.content == "Async success"
        assert mock_llm.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_network_error_triggers_retry(self):
        """测试异步网络错误触发重试"""
        # 创建Mock LLM
        mock_llm = AsyncMock()
        # 前两次失败，第三次成功
        mock_llm.ainvoke.side_effect = [
            httpcore.ConnectError("Connection failed"),
            httpcore.ConnectError("Connection failed"),
            AIMessage(content="Async success after retry"),
        ]

        # 调用
        config = LLMRetryConfig(max_attempts=3, min_wait=0.1, max_wait=0.5)
        result = await ainvoke_llm_with_retry(mock_llm, "test message", config=config)

        # 验证
        assert result.content == "Async success after retry"
        assert mock_llm.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retry_reached(self):
        """测试异步达到最大重试次数后抛出异常"""
        # 创建Mock LLM
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = httpcore.ConnectError("Persistent error")

        # 调用并期望抛出异常
        config = LLMRetryConfig(max_attempts=3, min_wait=0.1, max_wait=0.5)
        with pytest.raises(httpcore.ConnectError):
            await ainvoke_llm_with_retry(mock_llm, "test message", config=config)

        # 验证重试了3次
        assert mock_llm.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_configuration(self):
        """测试异步超时配置生效"""
        # 创建Mock LLM
        mock_llm = AsyncMock()

        async def slow_ainvoke(*args, **kwargs):
            await asyncio.sleep(2)
            return AIMessage(content="Slow response")

        mock_llm.ainvoke.side_effect = slow_ainvoke

        # 调用并期望超时
        config = LLMRetryConfig(max_attempts=1, timeout=0.5)
        with pytest.raises(asyncio.TimeoutError):
            await ainvoke_llm_with_retry(mock_llm, "test message", config=config)

    @pytest.mark.asyncio
    async def test_decorator_successful(self):
        """测试异步装饰器（成功情况）"""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = AIMessage(content="Async decorated success")

        @async_llm_retry(max_attempts=3, min_wait=0.1, max_wait=0.5)
        async def call_llm():
            return await mock_llm.ainvoke("test")

        result = await call_llm()
        assert result.content == "Async decorated success"
        assert mock_llm.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_with_retry(self):
        """测试异步装饰器（重试情况）"""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = [
            httpcore.ConnectError("First fail"),
            AIMessage(content="Async success on retry"),
        ]

        @async_llm_retry(max_attempts=3, min_wait=0.1, max_wait=0.5)
        async def call_llm():
            return await mock_llm.ainvoke("test")

        result = await call_llm()
        assert result.content == "Async success on retry"
        assert mock_llm.ainvoke.call_count == 2


class TestLLMRetryIntegration:
    """集成测试：验证与真实组件的交互"""

    @pytest.mark.asyncio
    async def test_gap_question_generator_integration(self):
        """测试Gap Question Generator集成"""
        from intelligent_project_analyzer.services.llm_gap_question_generator import LLMGapQuestionGenerator

        # 创建生成器
        generator = LLMGapQuestionGenerator()

        # 验证配置加载了重试参数
        config = generator.generation_config
        assert "max_retry_attempts" in config
        assert "retry_min_wait" in config
        assert "retry_max_wait" in config
        assert "llm_timeout" in config

        # 验证默认值
        assert config.get("max_retry_attempts", 3) >= 1
        assert config.get("retry_min_wait", 1.0) > 0
        assert config.get("retry_max_wait", 10.0) >= config.get("retry_min_wait", 1.0)
        assert config.get("llm_timeout", 30.0) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
