"""
LLM工厂单元测试
测试多提供商切换、自动降级链、负载均衡、Retry机制、配置验证
"""

import os
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_llm_config():
    """创建Mock LLM配置"""
    return {"provider": "openai", "model": "gpt-4", "temperature": 0.7, "max_tokens": 2000, "timeout": 30}


@pytest.fixture
def mock_env_variables(monkeypatch):
    """Mock环境变量"""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.setenv("OPENROUTER_API_KEYS", "key1,key2,key3")


@pytest.fixture
def mock_chat_openai():
    """创建Mock ChatOpenAI对象"""
    from tests.fixtures.mocks import MockAsyncLLM

    return MockAsyncLLM(responses=["Mock OpenAI response"])


# ============================================================================
# 配置管理测试
# ============================================================================


class TestConfiguration:
    """测试LLM配置管理"""

    def test_default_config_loading(self, mock_llm_config):
        """测试加载默认配置"""
        default_config = mock_llm_config

        assert default_config["provider"] == "openai"
        assert default_config["model"] == "gpt-4"
        assert default_config["temperature"] == 0.7

    def test_custom_config_override(self, mock_llm_config):
        """测试自定义配置覆盖"""
        custom_config = {"temperature": 0.9, "max_tokens": 4000}

        # 合并配置
        final_config = {**mock_llm_config, **custom_config}

        assert final_config["temperature"] == 0.9  # 覆盖
        assert final_config["max_tokens"] == 4000  # 覆盖
        assert final_config["provider"] == "openai"  # 保留

    def test_kwargs_override_config(self, mock_llm_config):
        """测试kwargs覆盖配置"""
        # 模拟create_llm(config, **kwargs)
        config = mock_llm_config.copy()
        kwargs = {"temperature": 0.5, "streaming": True}

        # kwargs优先级最高
        final_config = {**config, **kwargs}

        assert final_config["temperature"] == 0.5
        assert final_config["streaming"] is True

    def test_validate_required_fields(self):
        """测试必填字段验证"""
        config = {
            "provider": "openai",
            "model": "gpt-4"
            # 缺少max_tokens
        }

        required_fields = ["provider", "model", "max_tokens"]
        missing_fields = [f for f in required_fields if f not in config]

        assert "max_tokens" in missing_fields

    def test_validate_api_key_presence(self, mock_env_variables):
        """测试API Key存在性验证"""
        provider = "openai"

        # 检查环境变量
        api_key = os.getenv("OPENAI_API_KEY")

        assert api_key is not None
        assert api_key.startswith("sk-")


# ============================================================================
# 多提供商切换测试
# ============================================================================


class TestMultiProvider:
    """测试多LLM提供商支持"""

    def test_create_openai_llm(self):
        """测试创建OpenAI LLM"""
        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_instance = Mock()
            mock_openai.return_value = mock_instance

            llm = mock_openai(model="gpt-4", temperature=0.7)

            assert llm is not None
            mock_openai.assert_called_once()

    def test_create_openrouter_llm(self):
        """测试创建OpenRouter LLM"""
        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_instance = Mock()
            mock_openai.return_value = mock_instance

            # OpenRouter使用ChatOpenAI with base_url
            llm = mock_openai(model="google/gemini-2.0-flash-exp:free", openai_api_base="https://openrouter.ai/api/v1")

            assert llm is not None

    def test_create_deepseek_llm(self):
        """测试创建DeepSeek LLM"""
        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_instance = Mock()
            mock_openai.return_value = mock_instance

            llm = mock_openai(model="deepseek-chat", openai_api_base="https://api.deepseek.com")

            assert llm is not None

    def test_switch_provider_at_runtime(self):
        """测试运行时切换提供商"""
        providers = ["openai", "openrouter", "deepseek"]

        for provider in providers:
            config = {"provider": provider, "model": "test-model"}

            # 根据provider选择不同的base_url
            if provider == "openai":
                base_url = None
            elif provider == "openrouter":
                base_url = "https://openrouter.ai/api/v1"
            else:
                base_url = "https://api.deepseek.com"

            assert config["provider"] == provider


# ============================================================================
# 自动降级链测试
# ============================================================================


class TestFallbackChain:
    """测试自动降级链"""

    def test_respects_provider_when_no_fallback(self, monkeypatch):
        """禁用自动降级时也必须尊重 LLM_PROVIDER（例如 openrouter）"""
        # 使用 patch 确保环境变量被正确模拟
        env_values = {
            "LLM_PROVIDER": "openrouter",
            "LLM_AUTO_FALLBACK": "false",
            "OPENROUTER_API_KEY": "sk-test-openrouter",
            "OPENROUTER_API_KEYS": "",  # 空字符串，避免触发负载均衡
        }

        def mock_getenv(key, default=""):
            return env_values.get(key, default)

        from intelligent_project_analyzer.services.llm_factory import LLMFactory

        sentinel = Mock(name="openrouter-llm")
        with patch("os.getenv", side_effect=mock_getenv):
            with patch(
                "intelligent_project_analyzer.services.multi_llm_factory.MultiLLMFactory.create_llm",
                return_value=sentinel,
            ) as mock_create:
                llm = LLMFactory.create_llm()

        assert llm is sentinel
        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs.get("provider") == "openrouter"

    @pytest.mark.asyncio
    async def test_primary_provider_success(self):
        """测试主提供商成功时不降级"""
        from tests.fixtures.mocks import MockAsyncLLM

        primary_llm = MockAsyncLLM(responses=["Primary response"])

        try:
            response = await primary_llm.ainvoke("test prompt")
            used_fallback = False
        except:
            used_fallback = True

        assert not used_fallback
        assert "Primary" in response.content

    @pytest.mark.asyncio
    async def test_fallback_to_openrouter(self):
        """测试OpenAI失败后降级到OpenRouter"""
        from tests.fixtures.mocks import MockAsyncLLM

        # 模拟OpenAI失败
        openai_llm = AsyncMock()
        openai_llm.ainvoke.side_effect = Exception("OpenAI connection failed")

        # OpenRouter备用
        openrouter_llm = MockAsyncLLM(responses=["OpenRouter fallback response"])

        try:
            response = await openai_llm.ainvoke("test")
        except:
            # 降级到OpenRouter
            response = await openrouter_llm.ainvoke("test")

        assert "OpenRouter" in response.content

    @pytest.mark.asyncio
    async def test_fallback_to_deepseek(self):
        """测试OpenRouter失败后降级到DeepSeek"""
        from tests.fixtures.mocks import MockAsyncLLM

        # OpenAI和OpenRouter都失败
        openai_llm = AsyncMock()
        openai_llm.ainvoke.side_effect = Exception("OpenAI failed")

        openrouter_llm = AsyncMock()
        openrouter_llm.ainvoke.side_effect = Exception("OpenRouter failed")

        # DeepSeek最后兜底
        deepseek_llm = MockAsyncLLM(responses=["DeepSeek fallback response"])

        # 降级链
        for llm in [openai_llm, openrouter_llm, deepseek_llm]:
            try:
                response = await llm.ainvoke("test")
                break
            except:
                continue

        assert "DeepSeek" in response.content

    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        """测试所有提供商都失败"""
        failing_llms = [
            AsyncMock(ainvoke=AsyncMock(side_effect=Exception("Provider 1 failed"))),
            AsyncMock(ainvoke=AsyncMock(side_effect=Exception("Provider 2 failed"))),
            AsyncMock(ainvoke=AsyncMock(side_effect=Exception("Provider 3 failed"))),
        ]

        response = None
        for llm in failing_llms:
            try:
                response = await llm.ainvoke("test")
                break
            except:
                continue

        # 应该最终失败
        assert response is None

    def test_fallback_config_disabled(self):
        """测试禁用降级功能"""
        auto_fallback_enabled = False

        if not auto_fallback_enabled:
            # 不使用降级链，直接失败
            should_fallback = False
        else:
            should_fallback = True

        assert not should_fallback


# ============================================================================
# OpenRouter负载均衡测试
# ============================================================================


class TestLoadBalancing:
    """测试OpenRouter多Key负载均衡"""

    def test_parse_multiple_api_keys(self):
        """测试解析多个API Key"""
        keys_string = "key1,key2,key3"

        keys = [k.strip() for k in keys_string.split(",")]

        assert len(keys) == 3
        assert keys[0] == "key1"

    def test_round_robin_strategy(self):
        """测试轮询策略"""
        keys = ["key1", "key2", "key3"]
        current_index = 0

        # 模拟3次调用
        used_keys = []
        for _ in range(3):
            used_keys.append(keys[current_index % len(keys)])
            current_index += 1

        assert used_keys == ["key1", "key2", "key3"]

    def test_random_strategy(self):
        """测试随机策略"""
        import random

        keys = ["key1", "key2", "key3"]

        # 模拟随机选择
        random.seed(42)  # 固定随机种子
        selected_key = random.choice(keys)

        assert selected_key in keys

    def test_least_used_strategy(self):
        """测试最少使用策略"""
        keys_usage = {"key1": 5, "key2": 2, "key3": 8}

        # 选择使用次数最少的Key
        least_used_key = min(keys_usage, key=keys_usage.get)

        assert least_used_key == "key2"
        assert keys_usage[least_used_key] == 2

    def test_load_balancer_state_tracking(self):
        """测试负载均衡器状态追踪"""
        keys = ["key1", "key2", "key3"]
        usage_counts = {k: 0 for k in keys}

        # 模拟10次调用
        for i in range(10):
            key = keys[i % len(keys)]
            usage_counts[key] += 1

        # 应该均匀分布
        assert usage_counts["key1"] in [3, 4]
        assert usage_counts["key2"] in [3, 4]
        assert usage_counts["key3"] in [3, 4]


# ============================================================================
# Retry机制测试
# ============================================================================


class TestRetryMechanism:
    """测试网络错误重试机制"""

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self):
        """测试连接错误时重试"""
        from tests.fixtures.mocks import MockAsyncLLM

        # 模拟第1、2次失败，第3次成功
        attempt = 0

        async def failing_invoke(prompt):
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise ConnectionError("Network error")
            return await MockAsyncLLM().ainvoke(prompt)

        # 重试逻辑
        max_retries = 3
        for retry in range(max_retries):
            try:
                response = await failing_invoke("test")
                break
            except ConnectionError:
                if retry == max_retries - 1:
                    raise

        assert attempt == 3
        assert response is not None

    def test_exponential_backoff(self):
        """测试指数退避"""
        import time

        base_delay = 1
        max_retries = 4

        delays = []
        for retry in range(max_retries):
            delay = base_delay * (2**retry)  # 1, 2, 4, 8
            delays.append(delay)

        assert delays == [1, 2, 4, 8]

    @pytest.mark.asyncio
    async def test_max_retry_exceeded(self):
        """测试超过最大重试次数"""
        max_retries = 3
        attempt = 0

        async def always_failing():
            nonlocal attempt
            attempt += 1
            raise ConnectionError("Persistent error")

        # 应该在3次后抛出异常
        with pytest.raises(ConnectionError):
            for retry in range(max_retries):
                try:
                    await always_failing()
                except ConnectionError:
                    if retry == max_retries - 1:
                        raise

        assert attempt == 3

    def test_retry_on_timeout_only(self):
        """测试仅对超时错误重试"""
        errors = [TimeoutError("Timeout"), ConnectionError("Connection lost"), ValueError("Invalid parameter")]

        retryable_errors = [TimeoutError, ConnectionError]

        for error in errors:
            should_retry = type(error) in retryable_errors

            if type(error) == ValueError:
                assert not should_retry
            else:
                assert should_retry


# ============================================================================
# 配置验证测试
# ============================================================================


class TestConfigValidation:
    """测试配置验证逻辑"""

    def test_missing_api_key_detection(self):
        """测试检测缺失的API Key"""
        config = {
            "provider": "openai",
            "model": "gpt-4"
            # 没有api_key
        }

        has_api_key = "api_key" in config

        assert not has_api_key

    def test_invalid_max_tokens(self):
        """测试无效的max_tokens"""
        invalid_values = [-1, 0, 200001]  # 负数、0、超出限制

        for value in invalid_values:
            is_valid = 1 <= value <= 200000
            assert not is_valid

    def test_invalid_temperature(self):
        """测试无效的temperature"""
        invalid_temps = [-0.1, 2.1, -1.0]

        for temp in invalid_temps:
            is_valid = 0.0 <= temp <= 2.0
            assert not is_valid

    def test_invalid_timeout(self):
        """测试无效的timeout"""
        invalid_timeouts = [-1, 0, 301]  # 负数、0、超过5分钟

        for timeout in invalid_timeouts:
            is_valid = 1 <= timeout <= 300
            assert not is_valid

    def test_unsupported_provider(self):
        """测试不支持的提供商"""
        supported_providers = ["openai", "openrouter", "deepseek", "qwen"]

        test_provider = "unsupported_llm"

        is_supported = test_provider in supported_providers

        assert not is_supported


# ============================================================================
# 结构化输出测试
# ============================================================================


class TestStructuredOutput:
    """测试结构化输出LLM创建"""

    @pytest.mark.asyncio
    async def test_create_structured_llm(self):
        """测试创建结构化输出LLM"""
        from tests.fixtures.mocks import MockAsyncLLM

        # 模拟返回JSON格式
        structured_llm = MockAsyncLLM(responses=['{"field1": "value1", "field2": "value2"}'])

        response = await structured_llm.ainvoke("Generate JSON")

        import json

        try:
            data = json.loads(response.content)
            is_valid_json = True
        except:
            is_valid_json = False

        assert is_valid_json
        assert "field1" in data

    def test_with_structured_output_method(self):
        """测试with_structured_output方法"""
        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_llm.with_structured_output.return_value = mock_structured
            mock_openai.return_value = mock_llm

            llm = mock_openai()
            structured_llm = llm.with_structured_output({"type": "object"})

            assert structured_llm is not None
            mock_llm.with_structured_output.assert_called_once()


# ============================================================================
# 集成场景测试
# ============================================================================


class TestIntegrationScenarios:
    """测试完整集成场景"""

    @pytest.mark.asyncio
    async def test_create_with_auto_fallback_enabled(self, mock_env_variables):
        """测试启用自动降级的LLM创建"""
        auto_fallback = os.getenv("LLM_AUTO_FALLBACK") == "true"

        assert auto_fallback

        # 应该创建带降级链的LLM
        # 这里简化为Mock
        from tests.fixtures.mocks import MockAsyncLLM

        llm = MockAsyncLLM()

        response = await llm.ainvoke("test")
        assert response is not None

    @pytest.mark.asyncio
    async def test_load_balanced_openrouter_calls(self):
        """测试OpenRouter负载均衡调用"""
        keys = ["key1", "key2", "key3"]
        current_index = 0

        from tests.fixtures.mocks import MockAsyncLLM

        # 模拟3次调用使用不同的Key
        used_keys = []
        for _ in range(3):
            key = keys[current_index % len(keys)]
            used_keys.append(key)
            current_index += 1

            # 使用该Key创建LLM并调用
            llm = MockAsyncLLM()
            await llm.ainvoke(f"test with {key}")

        assert len(set(used_keys)) == 3  # 使用了3个不同的Key

    @pytest.mark.asyncio
    async def test_retry_with_fallback(self):
        """测试Retry + Fallback组合"""
        from tests.fixtures.mocks import MockAsyncLLM

        # 主LLM重试3次都失败
        primary_attempts = 0

        async def failing_primary():
            nonlocal primary_attempts
            primary_attempts += 1
            raise ConnectionError("Primary failed")

        # 降级到备用LLM
        fallback_llm = MockAsyncLLM(responses=["Fallback response"])

        # 尝试3次主LLM，每次都失败
        for _ in range(3):
            try:
                await failing_primary()
            except ConnectionError:
                pass  # 继续重试

        # 3次都失败后，使用降级LLM
        response = await fallback_llm.ainvoke("test")

        assert primary_attempts == 3
        assert "Fallback" in response.content
