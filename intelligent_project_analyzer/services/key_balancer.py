# -*- coding: utf-8 -*-
"""
多 API Key 负载均衡器

支持：
1. 多 Key 轮询 - 突破单 Key 限制
2. 多提供商负载均衡 - 分散风险
3. 自动故障转移 - Key 失效自动切换
4. 智能权重分配 - 根据成功率调整
"""

import os
import time
import random
import threading
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
from loguru import logger


class KeyStatus(Enum):
    """API Key 状态"""
    ACTIVE = "active"           # 正常
    RATE_LIMITED = "rate_limited"  # 被限流（临时）
    EXHAUSTED = "exhausted"     # 配额用尽（当天）
    INVALID = "invalid"         # 无效（永久）


@dataclass
class APIKeyInfo:
    """API Key 信息"""
    key: str
    provider: str
    status: KeyStatus = KeyStatus.ACTIVE
    
    # 统计
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    rate_limit_count: int = 0
    
    # 限流恢复时间
    rate_limit_until: float = 0.0
    
    # 权重（用于加权轮询）
    weight: float = 1.0
    
    # 最后使用时间
    last_used: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.success_count / self.total_requests
    
    @property
    def is_available(self) -> bool:
        """是否可用"""
        if self.status == KeyStatus.INVALID:
            return False
        if self.status == KeyStatus.EXHAUSTED:
            return False
        if self.status == KeyStatus.RATE_LIMITED:
            return time.time() > self.rate_limit_until
        return True
    
    def record_success(self):
        """记录成功"""
        self.total_requests += 1
        self.success_count += 1
        self.last_used = time.time()
        self.status = KeyStatus.ACTIVE
        # 成功后提升权重
        self.weight = min(2.0, self.weight * 1.1)
    
    def record_failure(self, is_rate_limit: bool = False, retry_after: float = 60.0):
        """记录失败"""
        self.total_requests += 1
        self.failure_count += 1
        self.last_used = time.time()
        
        if is_rate_limit:
            self.rate_limit_count += 1
            self.status = KeyStatus.RATE_LIMITED
            self.rate_limit_until = time.time() + retry_after
            logger.warning(f"🔒 Key {self.key[:8]}... 被限流，{retry_after}秒后恢复")
        
        # 失败后降低权重
        self.weight = max(0.1, self.weight * 0.8)
    
    def mark_exhausted(self):
        """标记配额用尽"""
        self.status = KeyStatus.EXHAUSTED
        logger.error(f"❌ Key {self.key[:8]}... 配额用尽")
    
    def mark_invalid(self):
        """标记无效"""
        self.status = KeyStatus.INVALID
        logger.error(f"❌ Key {self.key[:8]}... 无效")


class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"       # 轮询
    WEIGHTED = "weighted"             # 加权轮询
    LEAST_USED = "least_used"         # 最少使用
    RANDOM = "random"                 # 随机
    FASTEST = "fastest"               # 最快响应


class APIKeyPool:
    """
    API Key 池
    
    管理单个提供商的多个 Key
    """
    
    def __init__(
        self,
        provider: str,
        keys: List[str],
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.WEIGHTED
    ):
        self.provider = provider
        self.strategy = strategy
        self.keys: List[APIKeyInfo] = [
            APIKeyInfo(key=key, provider=provider) for key in keys if key
        ]
        self._index = 0
        self._lock = threading.Lock()
        
        logger.info(f"🔑 {provider} Key 池初始化: {len(self.keys)} 个 Key")
    
    def get_key(self) -> Optional[APIKeyInfo]:
        """
        获取一个可用的 Key
        
        Returns:
            可用的 Key 信息，如果没有则返回 None
        """
        with self._lock:
            available_keys = [k for k in self.keys if k.is_available]
            
            if not available_keys:
                logger.warning(f"⚠️ {self.provider} 没有可用的 Key")
                return None
            
            if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
                key = self._round_robin(available_keys)
            elif self.strategy == LoadBalanceStrategy.WEIGHTED:
                key = self._weighted_random(available_keys)
            elif self.strategy == LoadBalanceStrategy.LEAST_USED:
                key = self._least_used(available_keys)
            elif self.strategy == LoadBalanceStrategy.RANDOM:
                key = random.choice(available_keys)
            else:
                key = available_keys[0]
            
            return key
    
    def _round_robin(self, keys: List[APIKeyInfo]) -> APIKeyInfo:
        """轮询"""
        key = keys[self._index % len(keys)]
        self._index += 1
        return key
    
    def _weighted_random(self, keys: List[APIKeyInfo]) -> APIKeyInfo:
        """加权随机"""
        total_weight = sum(k.weight for k in keys)
        r = random.uniform(0, total_weight)
        cumulative = 0
        for key in keys:
            cumulative += key.weight
            if r <= cumulative:
                return key
        return keys[-1]
    
    def _least_used(self, keys: List[APIKeyInfo]) -> APIKeyInfo:
        """最少使用"""
        return min(keys, key=lambda k: k.total_requests)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        return {
            "provider": self.provider,
            "total_keys": len(self.keys),
            "available_keys": len([k for k in self.keys if k.is_available]),
            "keys": [
                {
                    "key": k.key[:8] + "...",
                    "status": k.status.value,
                    "requests": k.total_requests,
                    "success_rate": f"{k.success_rate:.1%}",
                    "weight": f"{k.weight:.2f}"
                }
                for k in self.keys
            ]
        }


class MultiKeyLoadBalancer:
    """
    多 Key 多提供商负载均衡器
    
    Usage:
        balancer = MultiKeyLoadBalancer()
        
        # 自动从环境变量加载
        balancer.load_from_env()
        
        # 或手动添加
        balancer.add_keys("openai", ["key1", "key2", "key3"])
        
        # 获取 Key
        key_info = balancer.get_key("openai")
        
        # 使用后报告结果
        balancer.report_success(key_info)
        # 或
        balancer.report_failure(key_info, is_rate_limit=True)
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
        
        self._pools: Dict[str, APIKeyPool] = {}
        self._provider_priority: List[str] = []  # 提供商优先级
        self._initialized = True
        
        # 自动从环境变量加载
        self.load_from_env()
    
    def load_from_env(self):
        """
        从环境变量加载 API Keys
        
        支持的格式：
        - OPENAI_API_KEY=key1  (单个)
        - OPENAI_API_KEYS=key1,key2,key3  (多个，逗号分隔)
        """
        providers_config = {
            "openai": ["OPENAI_API_KEY", "OPENAI_API_KEYS"],
            "deepseek": ["DEEPSEEK_API_KEY", "DEEPSEEK_API_KEYS"],
            "qwen": ["QWEN_API_KEY", "QWEN_API_KEYS", "DASHSCOPE_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEY", "OPENROUTER_API_KEYS"],
            "gemini": ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GEMINI_API_KEYS"],
            "anthropic": ["ANTHROPIC_API_KEY", "ANTHROPIC_API_KEYS"],
        }
        
        for provider, env_vars in providers_config.items():
            keys = []
            for env_var in env_vars:
                value = os.getenv(env_var, "")
                if value and value not in ["your_key_here", f"your_{provider}_api_key_here"]:
                    # 支持逗号分隔的多个 Key
                    if "," in value:
                        keys.extend([k.strip() for k in value.split(",") if k.strip()])
                    else:
                        keys.append(value)
            
            # 去重
            keys = list(dict.fromkeys(keys))
            
            if keys:
                self.add_keys(provider, keys)
                self._provider_priority.append(provider)
        
        logger.info(f"🔑 加载完成: {[f'{p}({len(self._pools[p].keys)})' for p in self._provider_priority]}")
    
    def add_keys(
        self,
        provider: str,
        keys: List[str],
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.WEIGHTED
    ):
        """添加 Key 池"""
        if provider in self._pools:
            # 追加到现有池
            for key in keys:
                if key and not any(k.key == key for k in self._pools[provider].keys):
                    self._pools[provider].keys.append(APIKeyInfo(key=key, provider=provider))
        else:
            self._pools[provider] = APIKeyPool(provider, keys, strategy)
    
    def get_key(self, provider: Optional[str] = None) -> Optional[APIKeyInfo]:
        """
        获取一个可用的 Key
        
        Args:
            provider: 指定提供商，如果为 None 则按优先级选择
            
        Returns:
            可用的 Key 信息
        """
        if provider:
            if provider in self._pools:
                return self._pools[provider].get_key()
            return None
        
        # 按优先级尝试
        for p in self._provider_priority:
            key = self._pools[p].get_key()
            if key:
                return key
        
        return None
    
    def get_key_with_fallback(self, preferred_provider: str) -> Tuple[Optional[APIKeyInfo], str]:
        """
        获取 Key，如果首选提供商不可用则回退
        
        Returns:
            (key_info, actual_provider)
        """
        # 尝试首选
        key = self.get_key(preferred_provider)
        if key:
            return key, preferred_provider
        
        # 回退到其他提供商
        for provider in self._provider_priority:
            if provider != preferred_provider:
                key = self.get_key(provider)
                if key:
                    logger.info(f"🔄 {preferred_provider} 不可用，回退到 {provider}")
                    return key, provider
        
        return None, ""
    
    def report_success(self, key_info: APIKeyInfo):
        """报告调用成功"""
        key_info.record_success()
    
    def report_failure(
        self,
        key_info: APIKeyInfo,
        is_rate_limit: bool = False,
        retry_after: float = 60.0,
        is_quota_exceeded: bool = False,
        is_invalid: bool = False
    ):
        """报告调用失败"""
        if is_invalid:
            key_info.mark_invalid()
        elif is_quota_exceeded:
            key_info.mark_exhausted()
        else:
            key_info.record_failure(is_rate_limit, retry_after)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计"""
        return {
            provider: pool.stats
            for provider, pool in self._pools.items()
        }
    
    @property
    def available_providers(self) -> List[str]:
        """可用的提供商列表"""
        return [
            p for p in self._provider_priority
            if any(k.is_available for k in self._pools[p].keys)
        ]


# 全局实例
key_balancer = MultiKeyLoadBalancer()


# ==================== 便捷函数 ====================

def get_api_key(provider: str = "openai") -> Optional[str]:
    """
    获取一个可用的 API Key
    
    Usage:
        key = get_api_key("openai")
        llm = ChatOpenAI(api_key=key)
    """
    key_info = key_balancer.get_key(provider)
    return key_info.key if key_info else None


def get_api_key_with_callback(provider: str = "openai"):
    """
    获取 Key 并返回回调函数
    
    Usage:
        key, on_success, on_failure = get_api_key_with_callback("openai")
        try:
            result = call_llm(key)
            on_success()
        except RateLimitError:
            on_failure(is_rate_limit=True)
    """
    key_info = key_balancer.get_key(provider)
    if not key_info:
        return None, None, None
    
    def on_success():
        key_balancer.report_success(key_info)
    
    def on_failure(is_rate_limit=False, retry_after=60.0, is_quota_exceeded=False, is_invalid=False):
        key_balancer.report_failure(key_info, is_rate_limit, retry_after, is_quota_exceeded, is_invalid)
    
    return key_info.key, on_success, on_failure
