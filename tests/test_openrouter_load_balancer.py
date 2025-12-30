"""
OpenRouter 负载均衡器测试

测试多 Key 负载均衡、健康检查、故障转移等功能。
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from intelligent_project_analyzer.services.openrouter_load_balancer import (
    OpenRouterLoadBalancer,
    LoadBalancerConfig,
    APIKeyStats,
    get_global_balancer,
    reset_global_balancer
)


class TestAPIKeyStats:
    """测试 API Key 统计"""

    def test_success_rate_calculation(self):
        """测试成功率计算"""
        stats = APIKeyStats(key_id="test_key")
        stats.total_requests = 100
        stats.successful_requests = 80

        assert stats.success_rate == 0.8
        assert abs(stats.error_rate - 0.2) < 0.001  # 使用近似比较避免浮点精度问题

    def test_success_rate_no_requests(self):
        """测试无请求时的成功率"""
        stats = APIKeyStats(key_id="test_key")

        assert stats.success_rate == 1.0
        assert stats.error_rate == 0.0


class TestLoadBalancerConfig:
    """测试负载均衡器配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = LoadBalancerConfig()

        assert config.health_check_interval == 300
        assert config.max_consecutive_failures == 3
        assert config.failure_cooldown == 600
        assert config.strategy == "round_robin"
        assert config.max_retries == 3

    def test_custom_config(self):
        """测试自定义配置"""
        config = LoadBalancerConfig(
            strategy="random",
            max_retries=5,
            rate_limit_per_key=200
        )

        assert config.strategy == "random"
        assert config.max_retries == 5
        assert config.rate_limit_per_key == 200


class TestOpenRouterLoadBalancer:
    """测试 OpenRouter 负载均衡器"""

    @pytest.fixture
    def mock_keys(self):
        """模拟 API Keys"""
        return ["key1_12345678", "key2_87654321", "key3_abcdefgh"]

    @pytest.fixture
    def balancer(self, mock_keys):
        """创建负载均衡器实例"""
        return OpenRouterLoadBalancer(
            api_keys=mock_keys,
            model="openai/gpt-4o-2024-11-20"
        )

    def test_initialization(self, balancer, mock_keys):
        """测试初始化"""
        assert len(balancer.api_keys) == 3
        assert len(balancer.stats) == 3
        assert balancer.model == "openai/gpt-4o-2024-11-20"

        # 验证所有 Keys 初始状态为健康
        for key in mock_keys:
            key_id = balancer._get_key_id(key)
            assert balancer.stats[key_id].is_healthy
            assert balancer.stats[key_id].total_requests == 0

    def test_load_keys_from_env(self):
        """测试从环境变量加载 Keys"""
        with patch.dict('os.environ', {
            'OPENROUTER_API_KEYS': 'key1,key2,key3'
        }):
            balancer = OpenRouterLoadBalancer()
            assert len(balancer.api_keys) == 3

    def test_round_robin_strategy(self, balancer):
        """测试轮询策略"""
        keys = []
        for _ in range(6):
            key = balancer._select_key()
            keys.append(balancer._get_key_id(key))

        # 验证轮询顺序
        assert keys[0] == keys[3]
        assert keys[1] == keys[4]
        assert keys[2] == keys[5]

    def test_random_strategy(self, mock_keys):
        """测试随机策略"""
        config = LoadBalancerConfig(strategy="random")
        balancer = OpenRouterLoadBalancer(
            api_keys=mock_keys,
            config=config
        )

        keys = set()
        for _ in range(20):
            key = balancer._select_key()
            keys.add(balancer._get_key_id(key))

        # 随机策略应该使用多个不同的 Keys
        assert len(keys) >= 2

    def test_least_used_strategy(self, mock_keys):
        """测试最少使用策略"""
        config = LoadBalancerConfig(strategy="least_used")
        balancer = OpenRouterLoadBalancer(
            api_keys=mock_keys,
            config=config
        )

        # 模拟不同的使用次数
        balancer.stats["key1_123"].total_requests = 10
        balancer.stats["key2_876"].total_requests = 5
        balancer.stats["key3_abc"].total_requests = 15

        # 应该选择使用次数最少的 Key
        key = balancer._select_key()
        assert balancer._get_key_id(key) == "key2_876"

    def test_update_stats_success(self, balancer):
        """测试成功更新统计"""
        key_id = "key1_123"

        balancer._update_stats(key_id, success=True)

        stats = balancer.stats[key_id]
        assert stats.total_requests == 1
        assert stats.successful_requests == 1
        assert stats.failed_requests == 0
        assert stats.consecutive_failures == 0
        assert stats.is_healthy

    def test_update_stats_failure(self, balancer):
        """测试失败更新统计"""
        key_id = "key1_123"

        balancer._update_stats(key_id, success=False, error="Test error")

        stats = balancer.stats[key_id]
        assert stats.total_requests == 1
        assert stats.successful_requests == 0
        assert stats.failed_requests == 1
        assert stats.consecutive_failures == 1
        assert stats.last_error == "Test error"

    def test_mark_unhealthy_after_failures(self, balancer):
        """测试连续失败后标记为不健康"""
        key_id = "key1_123"

        # 连续失败 3 次
        for _ in range(3):
            balancer._update_stats(key_id, success=False)

        # 应该被标记为不健康
        assert not balancer.stats[key_id].is_healthy

    def test_health_check_recovery(self, balancer):
        """测试健康检查恢复"""
        key_id = "key1_123"

        # 标记为不健康
        balancer.stats[key_id].is_healthy = False
        balancer.stats[key_id].last_error_time = datetime.now() - timedelta(seconds=700)

        # 重置上次健康检查时间，确保会执行检查
        balancer._last_health_check = datetime.now() - timedelta(seconds=400)

        # 执行健康检查（冷却期 600 秒）
        balancer._perform_health_check()

        # 应该恢复健康
        assert balancer.stats[key_id].is_healthy

    def test_rate_limit_check(self, balancer):
        """测试速率限制"""
        key_id = "key1_123"

        # 模拟达到速率限制
        for _ in range(balancer.config.rate_limit_per_key):
            assert balancer._check_rate_limit(key_id)

        # 下一个请求应该被限制
        assert not balancer._check_rate_limit(key_id)

    def test_get_llm(self, balancer):
        """测试获取 LLM 实例"""
        llm = balancer.get_llm()

        assert llm is not None
        assert llm.model_name == "openai/gpt-4o-2024-11-20"
        assert "openrouter.ai" in llm.openai_api_base

    def test_get_stats_summary(self, balancer):
        """测试获取统计摘要"""
        # 模拟一些请求
        balancer._update_stats("key1_123", success=True)
        balancer._update_stats("key1_123", success=True)
        balancer._update_stats("key2_876", success=False)

        summary = balancer.get_stats_summary()

        assert summary["total_keys"] == 3
        assert summary["healthy_keys"] == 3
        assert summary["total_requests"] == 3
        assert summary["successful_requests"] == 2
        assert summary["failed_requests"] == 1
        assert summary["overall_success_rate"] == 2/3

    def test_skip_unhealthy_keys(self, balancer):
        """测试跳过不健康的 Keys"""
        # 标记第一个 Key 为不健康
        first_key_id = balancer._get_key_id(balancer.api_keys[0])
        balancer.stats[first_key_id].is_healthy = False

        # 选择 10 次，不应该选到不健康的 Key
        for _ in range(10):
            key = balancer._select_key()
            assert balancer._get_key_id(key) != first_key_id


class TestGlobalBalancer:
    """测试全局负载均衡器单例"""

    def teardown_method(self):
        """每个测试后重置全局单例"""
        reset_global_balancer()

    def test_get_global_balancer(self):
        """测试获取全局负载均衡器"""
        with patch.dict('os.environ', {
            'OPENROUTER_API_KEYS': 'key1,key2'
        }):
            balancer1 = get_global_balancer()
            balancer2 = get_global_balancer()

            # 应该返回同一个实例
            assert balancer1 is balancer2

    def test_reset_global_balancer(self):
        """测试重置全局负载均衡器"""
        with patch.dict('os.environ', {
            'OPENROUTER_API_KEYS': 'key1,key2'
        }):
            balancer1 = get_global_balancer()
            reset_global_balancer()
            balancer2 = get_global_balancer()

            # 应该是不同的实例
            assert balancer1 is not balancer2


class TestIntegration:
    """集成测试"""

    @pytest.mark.skip(reason="需要真实的 API Keys，手动运行")
    def test_real_api_call(self):
        """测试真实 API 调用（需要真实的 API Keys）"""
        import os

        # 检查是否有真实的 API Keys
        if not os.getenv("OPENROUTER_API_KEYS"):
            pytest.skip("需要设置 OPENROUTER_API_KEYS 环境变量")

        balancer = OpenRouterLoadBalancer()
        llm = balancer.get_llm()

        # 调用 API
        response = llm.invoke("Say hello in one word")

        assert response is not None
        assert len(response.content) > 0

        # 检查统计
        summary = balancer.get_stats_summary()
        assert summary["total_requests"] > 0
        assert summary["successful_requests"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
