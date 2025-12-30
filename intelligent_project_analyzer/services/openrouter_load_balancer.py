"""
OpenRouter 多 Key 负载均衡器

实现多个 API Key 的轮询、健康检查和故障转移，提高 API 调用的稳定性。

特性:
- 多 Key 轮询负载均衡
- 自动健康检查和故障转移
- Key 使用统计和监控
- 速率限制保护
- 自动重试机制
"""

import os
import time
import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from loguru import logger
from langchain_openai import ChatOpenAI


@dataclass
class APIKeyStats:
    """API Key 统计信息"""
    key_id: str  # Key 的唯一标识（前8位）
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    is_healthy: bool = True
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def error_rate(self) -> float:
        """错误率"""
        return 1.0 - self.success_rate


@dataclass
class LoadBalancerConfig:
    """负载均衡器配置"""
    # 健康检查配置
    health_check_interval: int = 300  # 健康检查间隔（秒）
    max_consecutive_failures: int = 3  # 最大连续失败次数
    failure_cooldown: int = 600  # 失败后冷却时间（秒）

    # 负载均衡策略
    strategy: str = "round_robin"  # round_robin | random | least_used

    # 重试配置
    max_retries: int = 3
    retry_delay: int = 2

    # 速率限制
    rate_limit_per_key: int = 100  # 每个 Key 每分钟最大请求数
    rate_limit_window: int = 60  # 速率限制窗口（秒）


class OpenRouterLoadBalancer:
    """
    OpenRouter 多 Key 负载均衡器

    使用方法:
        # 1. 在 .env 中配置多个 Key
        OPENROUTER_API_KEYS=key1,key2,key3

        # 2. 创建负载均衡器
        balancer = OpenRouterLoadBalancer()

        # 3. 获取 LLM 实例
        llm = balancer.get_llm()

        # 4. 使用 LLM
        response = llm.invoke("Hello")
    """

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        config: Optional[LoadBalancerConfig] = None,
        model: str = "openai/gpt-4o-2024-11-20",
        **llm_kwargs
    ):
        """
        初始化负载均衡器

        Args:
            api_keys: API Key 列表，如果为 None 则从环境变量读取
            config: 负载均衡器配置
            model: OpenRouter 模型名称
            **llm_kwargs: 传递给 ChatOpenAI 的其他参数
        """
        self.config = config or LoadBalancerConfig()
        self.model = model
        self.llm_kwargs = llm_kwargs

        # 加载 API Keys
        self.api_keys = self._load_api_keys(api_keys)
        if not self.api_keys:
            raise ValueError("未找到可用的 OpenRouter API Keys")

        # 初始化统计信息
        self.stats: Dict[str, APIKeyStats] = {
            self._get_key_id(key): APIKeyStats(key_id=self._get_key_id(key))
            for key in self.api_keys
        }

        # 负载均衡状态
        self._current_index = 0
        self._lock = Lock()
        self._last_health_check = datetime.now()

        # 速率限制追踪
        self._rate_limit_tracker: Dict[str, List[datetime]] = {
            self._get_key_id(key): []
            for key in self.api_keys
        }

        logger.info(f"✅ OpenRouter 负载均衡器初始化完成: {len(self.api_keys)} 个 API Keys")
        logger.info(f"📊 负载均衡策略: {self.config.strategy}")
        logger.info(f"🔄 最大重试次数: {self.config.max_retries}")

    def _load_api_keys(self, api_keys: Optional[List[str]]) -> List[str]:
        """
        加载 API Keys

        优先级:
        1. 传入的 api_keys 参数
        2. 环境变量 OPENROUTER_API_KEYS (逗号分隔)
        3. 环境变量 OPENROUTER_API_KEY (单个)
        """
        if api_keys:
            return [key.strip() for key in api_keys if key.strip()]

        # 从环境变量加载多个 Keys
        keys_env = os.getenv("OPENROUTER_API_KEYS", "")
        if keys_env:
            keys = [key.strip() for key in keys_env.split(",") if key.strip()]
            if keys:
                logger.info(f"📥 从 OPENROUTER_API_KEYS 加载了 {len(keys)} 个 API Keys")
                return keys

        # 从环境变量加载单个 Key
        single_key = os.getenv("OPENROUTER_API_KEY", "")
        if single_key and single_key != "your_openrouter_api_key_here":
            logger.info("📥 从 OPENROUTER_API_KEY 加载了 1 个 API Key")
            return [single_key]

        return []

    def _get_key_id(self, api_key: str) -> str:
        """获取 Key 的唯一标识（前8位）"""
        return api_key[:8] if len(api_key) >= 8 else api_key

    def _select_key(self) -> str:
        """
        根据负载均衡策略选择一个 API Key

        Returns:
            选中的 API Key
        """
        with self._lock:
            # 过滤出健康的 Keys
            healthy_keys = [
                key for key in self.api_keys
                if self.stats[self._get_key_id(key)].is_healthy
            ]

            if not healthy_keys:
                logger.warning("⚠️ 所有 API Keys 都不健康，尝试使用所有 Keys")
                healthy_keys = self.api_keys

            # 根据策略选择
            if self.config.strategy == "round_robin":
                # 轮询策略
                key = healthy_keys[self._current_index % len(healthy_keys)]
                self._current_index += 1
            elif self.config.strategy == "random":
                # 随机策略
                key = random.choice(healthy_keys)
            elif self.config.strategy == "least_used":
                # 最少使用策略
                key = min(
                    healthy_keys,
                    key=lambda k: self.stats[self._get_key_id(k)].total_requests
                )
            else:
                # 默认轮询
                key = healthy_keys[self._current_index % len(healthy_keys)]
                self._current_index += 1

            return key

    def _check_rate_limit(self, key_id: str) -> bool:
        """
        检查 Key 是否超过速率限制

        Args:
            key_id: Key 标识

        Returns:
            是否在速率限制内
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.config.rate_limit_window)

        # 清理过期的请求记录
        self._rate_limit_tracker[key_id] = [
            ts for ts in self._rate_limit_tracker[key_id]
            if ts > window_start
        ]

        # 检查是否超限
        if len(self._rate_limit_tracker[key_id]) >= self.config.rate_limit_per_key:
            return False

        # 记录本次请求
        self._rate_limit_tracker[key_id].append(now)
        return True

    def _update_stats(self, key_id: str, success: bool, error: Optional[str] = None):
        """
        更新 Key 的统计信息

        Args:
            key_id: Key 标识
            success: 是否成功
            error: 错误信息
        """
        stats = self.stats[key_id]
        stats.total_requests += 1
        stats.last_used = datetime.now()

        if success:
            stats.successful_requests += 1
            stats.consecutive_failures = 0
            stats.is_healthy = True
        else:
            stats.failed_requests += 1
            stats.consecutive_failures += 1
            stats.last_error = error
            stats.last_error_time = datetime.now()

            # 检查是否需要标记为不健康
            if stats.consecutive_failures >= self.config.max_consecutive_failures:
                stats.is_healthy = False
                logger.warning(
                    f"⚠️ API Key {key_id} 标记为不健康 "
                    f"(连续失败 {stats.consecutive_failures} 次)"
                )

    def _perform_health_check(self):
        """执行健康检查，恢复冷却期已过的 Keys"""
        now = datetime.now()

        # 检查是否需要执行健康检查
        if (now - self._last_health_check).total_seconds() < self.config.health_check_interval:
            return

        self._last_health_check = now
        cooldown_threshold = now - timedelta(seconds=self.config.failure_cooldown)

        for key_id, stats in self.stats.items():
            if not stats.is_healthy and stats.last_error_time:
                # 如果冷却期已过，恢复健康状态
                if stats.last_error_time < cooldown_threshold:
                    stats.is_healthy = True
                    stats.consecutive_failures = 0
                    logger.info(f"✅ API Key {key_id} 已恢复健康状态")

    def get_llm(self, **override_kwargs) -> ChatOpenAI:
        """
        获取一个 LLM 实例（使用负载均衡选择的 Key）

        Args:
            **override_kwargs: 覆盖默认的 LLM 参数

        Returns:
            ChatOpenAI 实例
        """
        # 执行健康检查
        self._perform_health_check()

        # 选择一个 Key
        api_key = self._select_key()
        key_id = self._get_key_id(api_key)

        # 检查速率限制
        if not self._check_rate_limit(key_id):
            logger.warning(f"⚠️ API Key {key_id} 达到速率限制，切换到其他 Key")
            # 尝试选择另一个 Key
            api_key = self._select_key()
            key_id = self._get_key_id(api_key)

        # 构建 LLM 参数
        llm_params = {
            "model": self.model,
            "api_key": api_key,
            "base_url": "https://openrouter.ai/api/v1",
            "max_retries": self.config.max_retries,
            **self.llm_kwargs,
            **override_kwargs
        }

        logger.debug(f"🔑 使用 API Key: {key_id} (成功率: {self.stats[key_id].success_rate:.2%})")

        return ChatOpenAI(**llm_params)

    def invoke_with_retry(self, prompt: str, **kwargs) -> Any:
        """
        使用重试机制调用 LLM

        Args:
            prompt: 提示词
            **kwargs: 传递给 LLM 的参数

        Returns:
            LLM 响应
        """
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                llm = self.get_llm(**kwargs)
                key_id = self._get_key_id(llm.openai_api_key)

                # 调用 LLM
                response = llm.invoke(prompt)

                # 更新统计
                self._update_stats(key_id, success=True)

                return response

            except Exception as e:
                last_error = str(e)
                key_id = self._get_key_id(llm.openai_api_key) if 'llm' in locals() else "unknown"

                # 更新统计
                self._update_stats(key_id, success=False, error=last_error)

                logger.warning(
                    f"⚠️ API Key {key_id} 调用失败 (尝试 {attempt + 1}/{self.config.max_retries}): {last_error}"
                )

                # 如果不是最后一次尝试，等待后重试
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))

        # 所有重试都失败
        raise Exception(f"所有 API Keys 调用失败: {last_error}")

    def get_stats_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要

        Returns:
            统计信息字典
        """
        total_requests = sum(s.total_requests for s in self.stats.values())
        total_successful = sum(s.successful_requests for s in self.stats.values())
        total_failed = sum(s.failed_requests for s in self.stats.values())

        healthy_keys = sum(1 for s in self.stats.values() if s.is_healthy)

        return {
            "total_keys": len(self.api_keys),
            "healthy_keys": healthy_keys,
            "unhealthy_keys": len(self.api_keys) - healthy_keys,
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "overall_success_rate": total_successful / total_requests if total_requests > 0 else 1.0,
            "keys": {
                key_id: {
                    "total_requests": stats.total_requests,
                    "success_rate": stats.success_rate,
                    "is_healthy": stats.is_healthy,
                    "consecutive_failures": stats.consecutive_failures,
                    "last_used": stats.last_used.isoformat() if stats.last_used else None,
                    "last_error": stats.last_error
                }
                for key_id, stats in self.stats.items()
            }
        }

    def print_stats(self):
        """打印统计信息"""
        summary = self.get_stats_summary()

        logger.info("=" * 60)
        logger.info("📊 OpenRouter 负载均衡器统计")
        logger.info("=" * 60)
        logger.info(f"总 Keys: {summary['total_keys']}")
        logger.info(f"健康 Keys: {summary['healthy_keys']}")
        logger.info(f"不健康 Keys: {summary['unhealthy_keys']}")
        logger.info(f"总请求数: {summary['total_requests']}")
        logger.info(f"成功请求: {summary['successful_requests']}")
        logger.info(f"失败请求: {summary['failed_requests']}")
        logger.info(f"总成功率: {summary['overall_success_rate']:.2%}")
        logger.info("-" * 60)

        for key_id, stats in summary['keys'].items():
            status = "✅" if stats['is_healthy'] else "❌"
            logger.info(
                f"{status} Key {key_id}: "
                f"{stats['total_requests']} 请求, "
                f"{stats['success_rate']:.2%} 成功率"
            )
            if stats['last_error']:
                logger.info(f"   最后错误: {stats['last_error']}")

        logger.info("=" * 60)


# 全局单例
_global_balancer: Optional[OpenRouterLoadBalancer] = None


def get_global_balancer(**kwargs) -> OpenRouterLoadBalancer:
    """
    获取全局负载均衡器单例

    Args:
        **kwargs: 传递给 OpenRouterLoadBalancer 的参数

    Returns:
        OpenRouterLoadBalancer 实例
    """
    global _global_balancer

    if _global_balancer is None:
        _global_balancer = OpenRouterLoadBalancer(**kwargs)

    return _global_balancer


def reset_global_balancer():
    """重置全局负载均衡器"""
    global _global_balancer
    _global_balancer = None
