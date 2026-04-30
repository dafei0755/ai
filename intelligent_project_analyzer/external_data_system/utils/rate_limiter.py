"""
爬虫频率控制工具

实现智能延迟、请求限流、反爬虫检测等功能
"""

import time
import random
from typing import Optional, Dict, List
from collections import deque
from loguru import logger


class RateLimiter:
    """请求频率限制器"""
    
    def __init__(
        self,
        requests_per_minute: int = 12,  # 每分钟允许12个请求（即5秒/个）
        burst_size: int = 3,  # 突发请求数
        min_delay: float = 3.0,  # 最小延迟（秒）
        max_delay: float = 5.0,  # 最大延迟（秒）
    ):
        """
        初始化频率限制器
        
        Args:
            requests_per_minute: 每分钟允许的请求数
            burst_size: 允许的突发请求数
            min_delay: 最小延迟时间（秒）
            max_delay: 最大延迟时间（秒）
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.min_delay = min_delay
        self.max_delay = max_delay
        
        # 请求时间戳队列（用于滑动窗口计数）
        self.request_times: deque = deque(maxlen=requests_per_minute)
        
        # 上次请求时间
        self.last_request_time: Optional[float] = None
        
        # 被封次数
        self.block_count = 0
        
        # 当前延迟倍数
        self.delay_multiplier = 1.0
    
    def wait(self):
        """等待直到允许发送请求"""
        now = time.time()
        
        # 1. 检查是否在滑动窗口内超过限制
        self._clean_old_requests(now)
        
        if len(self.request_times) >= self.requests_per_minute:
            # 计算需要等待的时间
            oldest_request = self.request_times[0]
            wait_time = 60.0 - (now - oldest_request)
            
            if wait_time > 0:
                logger.debug(f"⏳ 请求频率限制，等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)
                now = time.time()
        
        # 2. 计算基于最小延迟的等待时间
        if self.last_request_time is not None:
            elapsed = now - self.last_request_time
            base_delay = self.min_delay * self.delay_multiplier
            
            if elapsed < base_delay:
                wait_time = base_delay - elapsed
                time.sleep(wait_time)
                now = time.time()
        
        # 3. 添加随机抖动（避免规律性）
        jitter = random.uniform(0, self.max_delay - self.min_delay)
        time.sleep(jitter)
        
        # 4. 记录请求时间
        self.last_request_time = time.time()
        self.request_times.append(self.last_request_time)
        
        logger.debug(f"✅ 请求发送 (队列: {len(self.request_times)}/{self.requests_per_minute})")
    
    def _clean_old_requests(self, now: float):
        """清理60秒之前的请求记录"""
        while self.request_times and now - self.request_times[0] > 60:
            self.request_times.popleft()
    
    def report_block(self):
        """报告被封，自动增加延迟"""
        self.block_count += 1
        
        if self.block_count == 1:
            # 第一次被封：延迟翻倍
            self.delay_multiplier = 2.0
            logger.warning(f"⚠️ 检测到封禁，延迟增加至 {self.min_delay * self.delay_multiplier:.1f} 秒")
        
        elif self.block_count == 2:
            # 第二次被封：延迟三倍
            self.delay_multiplier = 3.0
            logger.warning(f"⚠️ 再次被封，延迟增加至 {self.min_delay * self.delay_multiplier:.1f} 秒")
        
        else:
            # 第三次及以上：暂停1小时
            logger.error("❌ 频繁被封，暂停爬取 1 小时...")
            time.sleep(3600)
            self.delay_multiplier = 1.0
            self.block_count = 0
    
    def report_success(self):
        """报告请求成功，逐步恢复正常延迟"""
        if self.delay_multiplier > 1.0:
            self.delay_multiplier = max(1.0, self.delay_multiplier * 0.9)
            logger.debug(f"✅ 延迟恢复至 {self.min_delay * self.delay_multiplier:.1f} 秒")
    
    def reset(self):
        """重置限流器状态"""
        self.request_times.clear()
        self.last_request_time = None
        self.block_count = 0
        self.delay_multiplier = 1.0
        logger.info("🔄 频率限制器已重置")


class UserAgentRotator:
    """User-Agent 轮换器"""
    
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        
        # Firefox on Linux
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    def __init__(self):
        self.current_index = 0
    
    def get_next(self) -> str:
        """获取下一个 User-Agent"""
        ua = self.USER_AGENTS[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.USER_AGENTS)
        return ua
    
    def get_random(self) -> str:
        """获取随机 User-Agent"""
        return random.choice(self.USER_AGENTS)


class ProxyPool:
    """代理IP池（可选功能）"""
    
    def __init__(self, proxies: Optional[List[str]] = None):
        """
        初始化代理池
        
        Args:
            proxies: 代理列表，格式如 ["http://proxy1:8080", "http://proxy2:8080"]
        """
        self.proxies = proxies or []
        self.current_index = 0
        self.failed_proxies: Dict[str, int] = {}  # 记录失败次数
    
    def get_next(self) -> Optional[str]:
        """获取下一个可用代理"""
        if not self.proxies:
            return None
        
        # 跳过失败次数过多的代理
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            
            if self.failed_proxies.get(proxy, 0) < 3:
                return proxy
            
            attempts += 1
        
        return None
    
    def report_failure(self, proxy: str):
        """报告代理失败"""
        self.failed_proxies[proxy] = self.failed_proxies.get(proxy, 0) + 1
        logger.warning(f"⚠️ 代理失败: {proxy} (失败次数: {self.failed_proxies[proxy]})")
    
    def report_success(self, proxy: str):
        """报告代理成功，重置失败计数"""
        if proxy in self.failed_proxies:
            self.failed_proxies[proxy] = 0


class AntiBlocker:
    """反封禁综合工具"""
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        use_proxy: bool = False,
        proxies: Optional[List[str]] = None
    ):
        """
        初始化反封禁工具
        
        Args:
            rate_limiter: 频率限制器
            use_proxy: 是否使用代理
            proxies: 代理列表
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self.ua_rotator = UserAgentRotator()
        self.proxy_pool = ProxyPool(proxies) if use_proxy else None
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头（包含随机UA）"""
        return {
            "User-Agent": self.ua_rotator.get_random(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    def get_proxy(self) -> Optional[str]:
        """获取代理（如果启用）"""
        if self.proxy_pool:
            return self.proxy_pool.get_next()
        return None
    
    def before_request(self):
        """请求前处理（频率限制）"""
        self.rate_limiter.wait()
    
    def after_request(self, success: bool, status_code: Optional[int] = None):
        """
        请求后处理
        
        Args:
            success: 请求是否成功
            status_code: HTTP状态码
        """
        if success:
            self.rate_limiter.report_success()
        else:
            if status_code in [403, 429]:
                self.rate_limiter.report_block()
            logger.warning(f"⚠️ 请求失败: status_code={status_code}")


# 全局单例
_rate_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(source: str) -> RateLimiter:
    """
    获取指定数据源的频率限制器（单例模式）
    
    Args:
        source: 数据源名称（如 'archdaily', 'gooood'）
    
    Returns:
        RateLimiter实例
    """
    if source not in _rate_limiters:
        # 根据不同网站设置不同的频率
        if source == 'archdaily':
            _rate_limiters[source] = RateLimiter(
                requests_per_minute=12,  # 5秒/请求
                min_delay=3.0,
                max_delay=5.0
            )
        elif source == 'gooood':
            _rate_limiters[source] = RateLimiter(
                requests_per_minute=10,  # 6秒/请求（更保守）
                min_delay=4.0,
                max_delay=6.0
            )
        elif source == 'dezeen':
            _rate_limiters[source] = RateLimiter(
                requests_per_minute=12,
                min_delay=4.0,
                max_delay=6.0
            )
        else:
            # 默认配置
            _rate_limiters[source] = RateLimiter()
    
    return _rate_limiters[source]


__all__ = [
    'RateLimiter',
    'UserAgentRotator',
    'ProxyPool',
    'AntiBlocker',
    'get_rate_limiter',
]
