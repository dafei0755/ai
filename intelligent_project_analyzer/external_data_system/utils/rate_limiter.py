"""
爬虫频率控制工具

实现智能延迟、请求限流、反爬虫检测等功能。
提供 4 种预设模板，可按目标网站的反爬强度快速套用。
"""

import random
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from loguru import logger

# ==================== 延迟策略模板 ====================


class CrawlProfile(str, Enum):
    """爬虫速率预设模板

    GENTLE   - 温和：反爬弱的站点（开放 API、静态站）
    MODERATE - 适中：有基础反爬的站点（频率检测、简单 WAF）
    STEALTH  - 隐蔽：反爬较强的站点（Cloudflare、行为分析）
    PARANOID - 极慢：曾被封/高价值目标（宁可一天只爬100条也不被封）
    """

    GENTLE = "gentle"
    MODERATE = "moderate"
    STEALTH = "stealth"
    PARANOID = "paranoid"


@dataclass(frozen=True)
class CrawlProfileConfig:
    """单个模板的完整参数"""

    # RateLimiter 参数
    requests_per_minute: int
    min_delay: float
    max_delay: float
    burst_size: int = 3
    # 非均匀抖动控制
    jitter_sigma: float = 0.8  # 对数正态 sigma（越大越分散）
    micro_pause_prob: float = 0.05  # 微停顿概率
    micro_pause_min: float = 3.0  # 微停顿最短（秒）
    micro_pause_max: float = 12.0  # 微停顿最长（秒）
    # BatchConfig 参数
    batch_size: int = 30
    batch_rest: float = 90.0
    error_retry_delay: float = 60.0
    batch_jitter_sigma: float = 0.4  # 批次休息的对数正态 sigma
    long_rest_prob: float = 0.12  # 长休息概率
    long_rest_min: float = 180.0  # 长休息最短（秒）
    long_rest_max: float = 600.0  # 长休息最长（秒）
    max_requests_per_hour: int = 300
    max_requests_per_day: int = 3000


# 四套预设模板
CRAWL_PROFILES: Dict[CrawlProfile, CrawlProfileConfig] = {
    CrawlProfile.GENTLE: CrawlProfileConfig(
        requests_per_minute=20,
        min_delay=1.5,
        max_delay=3.0,
        jitter_sigma=0.5,
        micro_pause_prob=0.02,
        micro_pause_min=1.0,
        micro_pause_max=5.0,
        batch_size=100,
        batch_rest=30.0,
        error_retry_delay=15.0,
        batch_jitter_sigma=0.3,
        long_rest_prob=0.05,
        long_rest_min=60.0,
        long_rest_max=180.0,
        max_requests_per_hour=1000,
        max_requests_per_day=10000,
    ),
    CrawlProfile.MODERATE: CrawlProfileConfig(
        requests_per_minute=12,
        min_delay=3.0,
        max_delay=6.0,
        jitter_sigma=0.6,
        micro_pause_prob=0.03,
        micro_pause_min=2.0,
        micro_pause_max=8.0,
        batch_size=50,
        batch_rest=60.0,
        error_retry_delay=30.0,
        batch_jitter_sigma=0.4,
        long_rest_prob=0.08,
        long_rest_min=120.0,
        long_rest_max=360.0,
        max_requests_per_hour=500,
        max_requests_per_day=5000,
    ),
    CrawlProfile.STEALTH: CrawlProfileConfig(
        requests_per_minute=8,
        min_delay=5.0,
        max_delay=10.0,
        jitter_sigma=0.8,
        micro_pause_prob=0.05,
        micro_pause_min=3.0,
        micro_pause_max=15.0,
        batch_size=30,
        batch_rest=90.0,
        error_retry_delay=60.0,
        batch_jitter_sigma=0.4,
        long_rest_prob=0.12,
        long_rest_min=180.0,
        long_rest_max=600.0,
        max_requests_per_hour=300,
        max_requests_per_day=3000,
    ),
    CrawlProfile.PARANOID: CrawlProfileConfig(
        requests_per_minute=4,
        min_delay=10.0,
        max_delay=20.0,
        jitter_sigma=1.0,
        micro_pause_prob=0.10,
        micro_pause_min=5.0,
        micro_pause_max=30.0,
        batch_size=15,
        batch_rest=180.0,
        error_retry_delay=120.0,
        batch_jitter_sigma=0.5,
        long_rest_prob=0.20,
        long_rest_min=300.0,
        long_rest_max=900.0,
        max_requests_per_hour=100,
        max_requests_per_day=800,
    ),
}

# 网站 → 模板映射（可快速调整）
SOURCE_PROFILE_MAP: Dict[str, CrawlProfile] = {
    "gooood": CrawlProfile.STEALTH,
    "archdaily": CrawlProfile.STEALTH,
    "archdaily_cn": CrawlProfile.STEALTH,
    "dezeen": CrawlProfile.MODERATE,
}


def get_profile(source: str) -> CrawlProfileConfig:
    """获取指定数据源的模板配置"""
    profile = SOURCE_PROFILE_MAP.get(source, CrawlProfile.MODERATE)
    return CRAWL_PROFILES[profile]


def get_profile_by_name(name: str) -> CrawlProfileConfig:
    """按模板名称获取配置（gentle/moderate/stealth/paranoid）"""
    try:
        profile = CrawlProfile(name.lower())
    except ValueError:
        logger.warning(f"未知模板 '{name}'，使用 MODERATE")
        profile = CrawlProfile.MODERATE
    return CRAWL_PROFILES[profile]


class RateLimiter:
    """请求频率限制器（保守策略：宁可慢，不要被封）

    可通过 profile 参数一键套用预设模板，也可逐项自定义。
    """

    def __init__(
        self,
        requests_per_minute: int = 12,
        burst_size: int = 3,
        min_delay: float = 3.0,
        max_delay: float = 5.0,
        *,
        profile: CrawlProfileConfig | None = None,
    ):
        """
        初始化频率限制器

        Args:
            requests_per_minute: 每分钟允许的请求数
            burst_size: 允许的突发请求数
            min_delay: 最小延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            profile: 预设模板（传入后会覆盖上面的参数）
        """
        if profile is not None:
            requests_per_minute = profile.requests_per_minute
            burst_size = profile.burst_size
            min_delay = profile.min_delay
            max_delay = profile.max_delay

        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._base_min_delay = min_delay

        # 抖动参数（从 profile 读取，否则用默认值）
        self._jitter_sigma = profile.jitter_sigma if profile else 0.8
        self._micro_pause_prob = profile.micro_pause_prob if profile else 0.05
        self._micro_pause_min = profile.micro_pause_min if profile else 3.0
        self._micro_pause_max = profile.micro_pause_max if profile else 12.0

        # 请求时间戳队列（用于滑动窗口计数）
        self.request_times: deque = deque(maxlen=requests_per_minute)

        # 上次请求时间
        self.last_request_time: float | None = None

        # 连续被封次数（暂停后重置）
        self.block_count = 0

        # 累计被封次数（整个会话期间不重置，用于长期记忆）
        self.total_blocks = 0

        # 连续成功次数（用于判断何时开始恢复）
        self.consecutive_successes = 0

        # 当前延迟倍数
        self.delay_multiplier = 1.0

        # 暂停次数（每次长暂停后 +1，用于升级暂停时长）
        self.pause_count = 0

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

        # 3. 添加非均匀随机抖动（模拟真人浏览的不规则节奏）
        # 使用对数正态分布：大部分抖动集中在中低区间，偶尔出现较长停顿
        jitter_range = self.max_delay - self.min_delay
        raw = random.lognormvariate(mu=0, sigma=self._jitter_sigma)
        jitter = min(raw * jitter_range * 0.5, jitter_range * 2.0)  # 软上限
        time.sleep(jitter)

        # 按概率额外微停顿（模拟人类犹豫/切tab/读内容）
        if random.random() < self._micro_pause_prob:
            micro_pause = random.uniform(self._micro_pause_min, self._micro_pause_max)
            logger.debug(f"💤 模拟人类微停顿 {micro_pause:.1f}s")
            time.sleep(micro_pause)

        # 4. 记录请求时间
        self.last_request_time = time.time()
        self.request_times.append(self.last_request_time)

        logger.debug(
            f"✅ 请求发送 (队列: {len(self.request_times)}/{self.requests_per_minute}, 倍率: {self.delay_multiplier:.1f}x)"
        )

    def _clean_old_requests(self, now: float):
        """清理60秒之前的请求记录"""
        while self.request_times and now - self.request_times[0] > 60:
            self.request_times.popleft()

    def report_block(self):
        """
        报告被封，大幅度增加延迟。

        策略：宁可慢，不要被封。封禁升级采用大跨度倍率，
        暂停后不重置到原速，保持高倍率缓慢恢复。
        """
        self.block_count += 1
        self.total_blocks += 1
        self.consecutive_successes = 0

        if self.block_count == 1:
            # 第一次被封：立即跳到 3x（不是 2x）
            self.delay_multiplier = 3.0
            logger.warning(f"⚠️ 检测到封禁(累计{self.total_blocks}次)，" f"延迟增加至 {self.min_delay * self.delay_multiplier:.1f}s")

        elif self.block_count == 2:
            # 第二次被封：跳到 8x
            self.delay_multiplier = 8.0
            logger.warning(f"⚠️ 再次被封(累计{self.total_blocks}次)，" f"延迟增加至 {self.min_delay * self.delay_multiplier:.1f}s")

        elif self.block_count == 3:
            # 第三次被封：跳到 15x，同时短暂冷却
            self.delay_multiplier = 15.0
            cooldown = 120  # 2 分钟冷却
            logger.error(
                f"🚨 连续第3次被封(累计{self.total_blocks}次)，"
                f"延迟={self.min_delay * self.delay_multiplier:.1f}s，冷却 {cooldown}s..."
            )
            time.sleep(cooldown)

        else:
            # 第 4 次及以上：长暂停，暂停时长逐次翻倍
            self.pause_count += 1
            # 30min → 60min → 120min → 240min (上限)
            pause_minutes = min(30 * (2 ** (self.pause_count - 1)), 240)
            logger.error(f"❌ 频繁被封(连续{self.block_count}次, 累计{self.total_blocks}次)，" f"暂停爬取 {pause_minutes} 分钟...")
            time.sleep(pause_minutes * 60)

            # 暂停后：不重置到 1.0！保持高倍率
            self.delay_multiplier = 8.0
            self.block_count = 0  # 重置连续计数，但 total_blocks 不重置

            # 永久提升基线延迟（每经历 2 次长暂停，基线翻倍，上限 4 倍原始值）
            if self.pause_count >= 2 and self.min_delay < self._base_min_delay * 4:
                self.min_delay = min(self.min_delay * 2, self._base_min_delay * 4)
                logger.warning(f"📈 永久提升基线延迟至 {self.min_delay:.1f}s (原始: {self._base_min_delay:.1f}s)")

    def report_success(self):
        """
        报告请求成功，非常缓慢地恢复延迟。

        策略：需要连续 5 次成功才开始恢复，每次恢复仅 ×0.95，
        且有基于累计封禁次数的地板值，防止恢复过快再次被封。
        """
        self.consecutive_successes += 1

        if self.delay_multiplier > 1.0:
            # 必须连续成功 5 次才开始恢复（防止刚解封就加速）
            if self.consecutive_successes >= 5:
                # 缓慢恢复：×0.95（比原来的 ×0.9 慢一倍）
                new_mult = self.delay_multiplier * 0.95

                # 地板值：基于累计封禁次数，防止完全恢复到 1.0
                # 每次累计封禁 +0.3 倍率地板，上限 3.0
                floor = 1.0 + min(self.total_blocks * 0.3, 2.0)
                self.delay_multiplier = max(floor, new_mult)

                logger.debug(
                    f"✅ 延迟恢复至 {self.min_delay * self.delay_multiplier:.1f}s "
                    f"(倍率: {self.delay_multiplier:.2f}x, 地板: {floor:.1f}x, "
                    f"连续成功: {self.consecutive_successes})"
                )
            else:
                logger.debug(f"✅ 成功 ({self.consecutive_successes}/5 次后开始恢复延迟)")

    def reset(self):
        """重置限流器状态（完全重置，仅用于新会话）"""
        self.request_times.clear()
        self.last_request_time = None
        self.block_count = 0
        self.total_blocks = 0
        self.consecutive_successes = 0
        self.delay_multiplier = 1.0
        self.pause_count = 0
        self.min_delay = self._base_min_delay
        logger.info("🔄 频率限制器已重置")


class UserAgentRotator:
    """User-Agent 轮换器"""

    # 更新于 2026-02 — 保持与浏览器市场份额近似的比例
    USER_AGENTS = [
        # Chrome 131 on Windows 10
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # Chrome 131 on Windows 11
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # Chrome 132 on Windows 10
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        # Edge 131 on Windows 10
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        # Chrome 130 on macOS Sonoma
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        # Chrome 131 on macOS Sequoia
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # Firefox 133 on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        # Firefox 134 on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
        # Firefox 133 on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:133.0) Gecko/20100101 Firefox/133.0",
        # Safari 18 on macOS Sequoia
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
        # Chrome 131 on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # Firefox 134 on Linux
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    ]

    def __init__(self):
        self.current_index = 0

    def get_next(self) -> str:
        """获取随机 User-Agent（避免顺序规律被检测）"""
        return random.choice(self.USER_AGENTS)

    def get_random(self) -> str:
        """获取随机 User-Agent"""
        return random.choice(self.USER_AGENTS)


class ProxyPool:
    """代理IP池（可选功能）"""

    def __init__(self, proxies: List[str] | None = None):
        """
        初始化代理池

        Args:
            proxies: 代理列表，格式如 ["http://proxy1:8080", "http://proxy2:8080"]
        """
        self.proxies = proxies or []
        self.current_index = 0
        self.failed_proxies: Dict[str, int] = {}  # 记录失败次数

    def get_next(self) -> str | None:
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
        self, rate_limiter: RateLimiter | None = None, use_proxy: bool = False, proxies: List[str] | None = None
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

    def get_proxy(self) -> str | None:
        """获取代理（如果启用）"""
        if self.proxy_pool:
            return self.proxy_pool.get_next()
        return None

    def before_request(self):
        """请求前处理（频率限制）"""
        self.rate_limiter.wait()

    def after_request(self, success: bool, status_code: int | None = None):
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

    自动从 SOURCE_PROFILE_MAP 查找对应模板。
    要切换某个网站的策略，只需修改 SOURCE_PROFILE_MAP 即可。

    Args:
        source: 数据源名称（如 'archdaily', 'gooood', 'dezeen'）

    Returns:
        RateLimiter实例
    """
    if source not in _rate_limiters:
        profile_cfg = get_profile(source)
        _rate_limiters[source] = RateLimiter(profile=profile_cfg)
        profile_name = SOURCE_PROFILE_MAP.get(source, CrawlProfile.MODERATE).value
        logger.info(
            f"🔧 [{source}] 使用 {profile_name.upper()} 模板 "
            f"(delay={profile_cfg.min_delay}-{profile_cfg.max_delay}s, "
            f"rpm={profile_cfg.requests_per_minute}, "
            f"batch={profile_cfg.batch_size})"
        )

    return _rate_limiters[source]


__all__ = [
    "RateLimiter",
    "UserAgentRotator",
    "ProxyPool",
    "AntiBlocker",
    "CrawlProfile",
    "CrawlProfileConfig",
    "CRAWL_PROFILES",
    "SOURCE_PROFILE_MAP",
    "get_rate_limiter",
    "get_profile",
    "get_profile_by_name",
]
