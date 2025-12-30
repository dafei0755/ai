# -*- coding: utf-8 -*-
"""
LLM API 限流模块

提供多种限流策略，防止 API 调用超限：
1. 令牌桶限流 - 控制请求速率
2. 信号量限流 - 控制并发数量
3. 滑动窗口限流 - 控制时间窗口内的请求数
4. 用户级别限流 - 按用户隔离配额

支持多提供商不同的限流配置
"""

import asyncio
import time
import threading
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import deque
from functools import wraps
from loguru import logger


@dataclass
class RateLimitConfig:
    """限流配置"""
    # 令牌桶配置
    tokens_per_second: float = 1.0      # 每秒生成的令牌数
    bucket_size: int = 10               # 令牌桶最大容量
    
    # 并发控制
    max_concurrent: int = 5             # 最大并发请求数
    
    # 滑动窗口配置
    window_size: int = 60               # 窗口大小（秒）
    max_requests_per_window: int = 60   # 窗口内最大请求数
    
    # 超时配置
    acquire_timeout: float = 30.0       # 获取令牌的超时时间
    
    # 重试配置
    retry_after: float = 1.0            # 限流后的重试间隔


# 各 LLM 提供商的默认限流配置
PROVIDER_RATE_LIMITS: Dict[str, RateLimitConfig] = {
    "openai": RateLimitConfig(
        tokens_per_second=3.0,      # GPT-4: ~200 RPM → 3.3 RPS
        bucket_size=10,
        max_concurrent=5,
        window_size=60,
        max_requests_per_window=200,
    ),
    "deepseek": RateLimitConfig(
        tokens_per_second=5.0,      # DeepSeek 限制较宽松
        bucket_size=20,
        max_concurrent=10,
        window_size=60,
        max_requests_per_window=300,
    ),
    "qwen": RateLimitConfig(
        tokens_per_second=2.0,      # 通义千问
        bucket_size=10,
        max_concurrent=5,
        window_size=60,
        max_requests_per_window=100,
    ),
    "openrouter": RateLimitConfig(
        tokens_per_second=1.0,      # OpenRouter 免费层较严格
        bucket_size=5,
        max_concurrent=3,
        window_size=60,
        max_requests_per_window=50,
    ),
    "gemini": RateLimitConfig(
        tokens_per_second=1.0,      # Gemini 免费层
        bucket_size=5,
        max_concurrent=3,
        window_size=60,
        max_requests_per_window=60,
    ),
}


class TokenBucket:
    """
    令牌桶限流器
    
    以固定速率生成令牌，请求需要获取令牌才能执行
    """
    
    def __init__(self, tokens_per_second: float, bucket_size: int):
        self.tokens_per_second = tokens_per_second
        self.bucket_size = bucket_size
        self.tokens = bucket_size  # 初始满桶
        self.last_update = time.monotonic()
        self._lock = threading.Lock()
    
    def _refill(self):
        """补充令牌"""
        now = time.monotonic()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.tokens_per_second
        self.tokens = min(self.bucket_size, self.tokens + new_tokens)
        self.last_update = now
    
    def acquire(self, timeout: float = 30.0) -> bool:
        """
        获取一个令牌
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否成功获取令牌
        """
        deadline = time.monotonic() + timeout
        
        while True:
            with self._lock:
                self._refill()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
            
            # 检查超时
            if time.monotonic() >= deadline:
                return False
            
            # 等待一小段时间再重试
            time.sleep(0.1)
    
    async def acquire_async(self, timeout: float = 30.0) -> bool:
        """异步获取令牌"""
        deadline = time.monotonic() + timeout
        
        while True:
            with self._lock:
                self._refill()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
            
            if time.monotonic() >= deadline:
                return False
            
            await asyncio.sleep(0.1)
    
    @property
    def available_tokens(self) -> float:
        """当前可用令牌数"""
        with self._lock:
            self._refill()
            return self.tokens


class SlidingWindowCounter:
    """
    滑动窗口计数器
    
    统计时间窗口内的请求数量
    """
    
    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: deque = deque()
        self._lock = threading.Lock()
    
    def _cleanup(self):
        """清理过期请求"""
        now = time.monotonic()
        cutoff = now - self.window_size
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
    
    def allow(self) -> bool:
        """
        检查是否允许请求
        
        Returns:
            True 如果允许，False 如果超限
        """
        with self._lock:
            self._cleanup()
            if len(self.requests) < self.max_requests:
                self.requests.append(time.monotonic())
                return True
            return False
    
    @property
    def current_count(self) -> int:
        """当前窗口内的请求数"""
        with self._lock:
            self._cleanup()
            return len(self.requests)
    
    @property
    def remaining(self) -> int:
        """剩余可用请求数"""
        return max(0, self.max_requests - self.current_count)


class ConcurrencyLimiter:
    """
    并发限制器
    
    使用信号量控制同时执行的请求数
    """
    
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._sync_semaphore = threading.Semaphore(max_concurrent)
        self._active = 0
        self._lock = threading.Lock()
    
    async def acquire_async(self):
        """异步获取信号量"""
        await self._semaphore.acquire()
        with self._lock:
            self._active += 1
    
    def release_async(self):
        """异步释放信号量"""
        self._semaphore.release()
        with self._lock:
            self._active -= 1
    
    def acquire_sync(self, timeout: float = 30.0) -> bool:
        """同步获取信号量"""
        acquired = self._sync_semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._active += 1
        return acquired
    
    def release_sync(self):
        """同步释放信号量"""
        self._sync_semaphore.release()
        with self._lock:
            self._active -= 1
    
    @property
    def active_count(self) -> int:
        """当前活跃请求数"""
        with self._lock:
            return self._active
    
    @property
    def available(self) -> int:
        """可用并发数"""
        return self.max_concurrent - self.active_count


class LLMRateLimiter:
    """
    LLM API 综合限流器
    
    整合令牌桶、滑动窗口和并发控制
    """
    
    def __init__(self, provider: str = "openai", config: Optional[RateLimitConfig] = None):
        """
        初始化限流器
        
        Args:
            provider: LLM 提供商名称
            config: 自定义限流配置，如果为 None 则使用默认配置
        """
        self.provider = provider
        self.config = config or PROVIDER_RATE_LIMITS.get(provider, RateLimitConfig())
        
        # 初始化各限流组件
        self.token_bucket = TokenBucket(
            tokens_per_second=self.config.tokens_per_second,
            bucket_size=self.config.bucket_size
        )
        
        self.sliding_window = SlidingWindowCounter(
            window_size=self.config.window_size,
            max_requests=self.config.max_requests_per_window
        )
        
        self.concurrency_limiter = ConcurrencyLimiter(
            max_concurrent=self.config.max_concurrent
        )
        
        # 统计
        self._total_requests = 0
        self._rejected_requests = 0
        self._lock = threading.Lock()
        
        logger.info(
            f"🚦 LLM 限流器初始化: provider={provider}, "
            f"rate={self.config.tokens_per_second}/s, "
            f"concurrent={self.config.max_concurrent}, "
            f"window={self.config.max_requests_per_window}/{self.config.window_size}s"
        )
    
    async def acquire_async(self) -> bool:
        """
        异步获取执行许可
        
        Returns:
            True 如果获取成功，False 如果被限流
        """
        # 1. 检查滑动窗口
        if not self.sliding_window.allow():
            logger.warning(f"⚠️ [{self.provider}] 滑动窗口限流: {self.sliding_window.current_count}/{self.config.max_requests_per_window}")
            self._record_rejection()
            return False
        
        # 2. 获取令牌
        if not await self.token_bucket.acquire_async(timeout=self.config.acquire_timeout):
            logger.warning(f"⚠️ [{self.provider}] 令牌桶限流")
            self._record_rejection()
            return False
        
        # 3. 获取并发许可
        await self.concurrency_limiter.acquire_async()
        
        self._record_request()
        return True
    
    def release_async(self):
        """异步释放并发许可"""
        self.concurrency_limiter.release_async()
    
    def acquire_sync(self) -> bool:
        """
        同步获取执行许可
        
        Returns:
            True 如果获取成功，False 如果被限流
        """
        # 1. 检查滑动窗口
        if not self.sliding_window.allow():
            logger.warning(f"⚠️ [{self.provider}] 滑动窗口限流")
            self._record_rejection()
            return False
        
        # 2. 获取令牌
        if not self.token_bucket.acquire(timeout=self.config.acquire_timeout):
            logger.warning(f"⚠️ [{self.provider}] 令牌桶限流")
            self._record_rejection()
            return False
        
        # 3. 获取并发许可
        if not self.concurrency_limiter.acquire_sync(timeout=self.config.acquire_timeout):
            logger.warning(f"⚠️ [{self.provider}] 并发限流")
            self._record_rejection()
            return False
        
        self._record_request()
        return True
    
    def release_sync(self):
        """同步释放并发许可"""
        self.concurrency_limiter.release_sync()
    
    def _record_request(self):
        """记录请求"""
        with self._lock:
            self._total_requests += 1
    
    def _record_rejection(self):
        """记录拒绝"""
        with self._lock:
            self._rejected_requests += 1
    
    @property
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "provider": self.provider,
            "total_requests": self._total_requests,
            "rejected_requests": self._rejected_requests,
            "rejection_rate": self._rejected_requests / max(1, self._total_requests + self._rejected_requests),
            "available_tokens": self.token_bucket.available_tokens,
            "window_remaining": self.sliding_window.remaining,
            "concurrent_active": self.concurrency_limiter.active_count,
            "concurrent_available": self.concurrency_limiter.available,
        }


class GlobalRateLimitManager:
    """
    全局限流管理器
    
    管理所有 LLM 提供商的限流器，支持用户级别隔离
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._limiters: Dict[str, LLMRateLimiter] = {}
        self._user_limiters: Dict[str, Dict[str, LLMRateLimiter]] = {}
        self._initialized = True
        
        logger.info("🚦 全局限流管理器已初始化")
    
    def get_limiter(self, provider: str = "openai", user_id: Optional[str] = None) -> LLMRateLimiter:
        """
        获取限流器
        
        Args:
            provider: LLM 提供商
            user_id: 用户ID（可选，用于用户级别限流）
            
        Returns:
            限流器实例
        """
        if user_id:
            # 用户级别限流
            if user_id not in self._user_limiters:
                self._user_limiters[user_id] = {}
            
            if provider not in self._user_limiters[user_id]:
                # 用户级别配置（更严格）
                base_config = PROVIDER_RATE_LIMITS.get(provider, RateLimitConfig())
                user_config = RateLimitConfig(
                    tokens_per_second=base_config.tokens_per_second / 2,
                    bucket_size=max(1, base_config.bucket_size // 2),
                    max_concurrent=max(1, base_config.max_concurrent // 2),
                    window_size=base_config.window_size,
                    max_requests_per_window=base_config.max_requests_per_window // 2,
                )
                self._user_limiters[user_id][provider] = LLMRateLimiter(provider, user_config)
            
            return self._user_limiters[user_id][provider]
        
        # 全局限流
        if provider not in self._limiters:
            self._limiters[provider] = LLMRateLimiter(provider)
        
        return self._limiters[provider]
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有限流器的统计信息"""
        stats = {
            "global": {provider: limiter.stats for provider, limiter in self._limiters.items()},
            "users": {
                user_id: {provider: limiter.stats for provider, limiter in user_limiters.items()}
                for user_id, user_limiters in self._user_limiters.items()
            }
        }
        return stats


# 全局实例
rate_limit_manager = GlobalRateLimitManager()


# ==================== 装饰器 ====================

def rate_limited(provider: str = "openai", user_id: Optional[str] = None):
    """
    同步函数限流装饰器
    
    Usage:
        @rate_limited("openai")
        def call_openai(prompt):
            return llm.invoke(prompt)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = rate_limit_manager.get_limiter(provider, user_id)
            
            if not limiter.acquire_sync():
                raise RateLimitExceeded(f"LLM API 限流: {provider}")
            
            try:
                return func(*args, **kwargs)
            finally:
                limiter.release_sync()
        
        return wrapper
    return decorator


def rate_limited_async(provider: str = "openai", user_id: Optional[str] = None):
    """
    异步函数限流装饰器
    
    Usage:
        @rate_limited_async("openai")
        async def call_openai(prompt):
            return await llm.ainvoke(prompt)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            limiter = rate_limit_manager.get_limiter(provider, user_id)
            
            if not await limiter.acquire_async():
                raise RateLimitExceeded(f"LLM API 限流: {provider}")
            
            try:
                return await func(*args, **kwargs)
            finally:
                limiter.release_async()
        
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """限流异常"""
    pass


# ==================== 便捷函数 ====================

async def with_rate_limit_async(
    provider: str,
    func: Callable,
    *args,
    user_id: Optional[str] = None,
    **kwargs
) -> Any:
    """
    使用限流执行异步函数
    
    Usage:
        result = await with_rate_limit_async("openai", llm.ainvoke, prompt)
    """
    limiter = rate_limit_manager.get_limiter(provider, user_id)
    
    if not await limiter.acquire_async():
        raise RateLimitExceeded(f"LLM API 限流: {provider}")
    
    try:
        return await func(*args, **kwargs)
    finally:
        limiter.release_async()


def with_rate_limit_sync(
    provider: str,
    func: Callable,
    *args,
    user_id: Optional[str] = None,
    **kwargs
) -> Any:
    """
    使用限流执行同步函数
    
    Usage:
        result = with_rate_limit_sync("openai", llm.invoke, prompt)
    """
    limiter = rate_limit_manager.get_limiter(provider, user_id)
    
    if not limiter.acquire_sync():
        raise RateLimitExceeded(f"LLM API 限流: {provider}")
    
    try:
        return func(*args, **kwargs)
    finally:
        limiter.release_sync()
