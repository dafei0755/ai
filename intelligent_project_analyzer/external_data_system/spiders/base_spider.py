"""
统一爬虫基类

所有外部数据源爬虫的基类，提供：
- 请求管理（重试、限速、User-Agent轮换）
- Cookie持久化
- 数据标准化接口
- 错误处理
- 专用Playwright线程（避免asyncio冲突）
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, TypeVar, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import os
import time
import re
import random
import concurrent.futures
from pathlib import Path
import json
from loguru import logger
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from ..utils.rate_limiter import RateLimiter, get_rate_limiter
from ..utils.network_rotate import IPRotator

T = TypeVar("T")


@dataclass
class ProjectData:
    """标准化项目数据结构

    语言字段规则
    ─────────────────────────────────────────────────────────────────
    lang          | 页面语言: "zh" / "en" / "bilingual"
    title_zh      | 中文标题
    title_en      | 英文标题
    description_zh| 中文描述（中文源页面或双语页面的中文段落）
    description_en| 英文描述（英文源页面或双语页面的英文段落）
    ─────────────────────────────────────────────────────────────────
    title / description 保持原样（兼容旧代码）：
      - 英文网站：原始英文内容
      - 中文网站：原始中文内容
      - 双语网站：中英混合原始内容
    """

    # 必需字段
    source: str  # archdaily/archdaily_cn/gooood/dezeen
    source_id: str
    url: str
    title: str

    # 可选字段
    description: Optional[str] = None
    architects: List[Dict[str, str]] = field(default_factory=list)
    location: Optional[Dict[str, Any]] = None
    area_sqm: Optional[float] = None
    year: Optional[int] = None
    primary_category: Optional[str] = None
    sub_categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    views: Optional[int] = None
    publish_date: Optional[datetime] = None

    # ── 双语内容字段 ──────────────────────────────────────────────
    # 页面语言标识
    lang: str = "unknown"  # "zh" | "en" | "bilingual" | "unknown"
    # 中文内容
    title_zh: Optional[str] = None
    description_zh: Optional[str] = None
    # 英文内容
    title_en: Optional[str] = None
    description_en: Optional[str] = None

    # 原始数据（调试用）
    raw_html: Optional[str] = None

    # ── 扩展字段 ──────────────────────────────────────────────────
    # 站点特有字段 catch-all（业主、方案类型等）
    # key 用英文小写_下划线，value 为 str / list[str] / dict
    extra_fields: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "architects": self.architects,
            "location": self.location,
            "area_sqm": self.area_sqm,
            "year": self.year,
            "primary_category": self.primary_category,
            "sub_categories": self.sub_categories,
            "tags": self.tags,
            "images": self.images,
            "views": self.views,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            # 双语字段
            "lang": self.lang,
            "title_zh": self.title_zh,
            "title_en": self.title_en,
            "description_zh": self.description_zh,
            "description_en": self.description_en,
        }

    def validate(self) -> bool:
        """验证数据完整性"""
        if not all([self.source, self.source_id, self.url, self.title]):
            return False
        # 取三个候选中最长的描述字段（Python or 只返回第一个truthy值，
        # 若 description_zh 非空但极短，会误导致 description_en/description 被忽略）
        candidates = [
            self.description_zh or "",
            self.description_en or "",
            self.description or "",
        ]
        primary_desc = max(candidates, key=len)
        if not primary_desc or len(primary_desc) < 50:
            logger.warning(
                f"描述过短: {self.url} | "
                f"description={len(self.description or '')}字符, "
                f"description_zh={len(self.description_zh or '')}字符, "
                f"description_en={len(self.description_en or '')}字符"
            )
            return False
        return True


class BaseSpider(ABC):
    """
    爬虫基类

    核心设计：所有Playwright操作在专用线程中执行，避免与FastAPI的asyncio事件循环冲突。
    使用 run_in_browser_thread() 将任何函数调度到Playwright线程。
    """

    # ── 指纹一致性档案 ──────────────────────────────────────────────────────
    # 每个 UA 对应一组一致的指纹参数（platform, languages, timezone, locale, screen）
    # 确保同一 context 内各维度不矛盾，避免被指纹关联检测
    _FINGERPRINT_PROFILES: List[Dict[str, Any]] = [
        # --- Windows / Chrome ---
        {
            "ua_keyword": "Windows NT 10.0",
            "browser": "Chrome/131",
            "platform": "Win32",
            "languages": ["zh-CN", "zh", "en-US", "en"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1040, "colorDepth": 24},
        },
        {
            "ua_keyword": "Windows NT 11.0",
            "browser": "Chrome/131",
            "platform": "Win32",
            "languages": ["zh-CN", "zh", "en"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 2560, "height": 1440, "availWidth": 2560, "availHeight": 1400, "colorDepth": 24},
        },
        {
            "ua_keyword": "Windows NT 10.0",
            "browser": "Chrome/132",
            "platform": "Win32",
            "languages": ["zh-CN", "zh", "en-US", "en"],
            "timezone": "Asia/Chongqing",
            "locale": "zh-CN",
            "screen": {"width": 1536, "height": 864, "availWidth": 1536, "availHeight": 824, "colorDepth": 24},
        },
        {
            "ua_keyword": "Windows",
            "browser": "Edg/131",
            "platform": "Win32",
            "languages": ["zh-CN", "zh", "en-US"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1040, "colorDepth": 24},
        },
        # --- macOS / Chrome ---
        {
            "ua_keyword": "Macintosh",
            "browser": "Chrome/130",
            "platform": "MacIntel",
            "languages": ["zh-CN", "zh-Hans", "en-US", "en"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1440, "height": 900, "availWidth": 1440, "availHeight": 875, "colorDepth": 30},
        },
        {
            "ua_keyword": "Macintosh",
            "browser": "Chrome/131",
            "platform": "MacIntel",
            "languages": ["zh-CN", "zh", "en"],
            "timezone": "Asia/Hong_Kong",
            "locale": "zh-CN",
            "screen": {"width": 2560, "height": 1440, "availWidth": 2560, "availHeight": 1415, "colorDepth": 30},
        },
        # --- Windows / Firefox ---
        {
            "ua_keyword": "Windows",
            "browser": "Firefox/133",
            "platform": "Win32",
            "languages": ["zh-CN", "zh", "en-US", "en"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1040, "colorDepth": 24},
        },
        {
            "ua_keyword": "Windows",
            "browser": "Firefox/134",
            "platform": "Win32",
            "languages": ["zh-CN", "zh", "en-US"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1366, "height": 768, "availWidth": 1366, "availHeight": 728, "colorDepth": 24},
        },
        # --- macOS / Firefox ---
        {
            "ua_keyword": "Macintosh",
            "browser": "Firefox/133",
            "platform": "MacIntel",
            "languages": ["zh-CN", "zh", "en-US"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1440, "height": 900, "availWidth": 1440, "availHeight": 875, "colorDepth": 30},
        },
        # --- macOS / Safari ---
        {
            "ua_keyword": "Macintosh",
            "browser": "Safari/605",
            "platform": "MacIntel",
            "languages": ["zh-Hans-CN", "zh-Hans", "en"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1440, "height": 900, "availWidth": 1440, "availHeight": 875, "colorDepth": 30},
        },
        # --- Linux / Chrome ---
        {
            "ua_keyword": "X11; Linux",
            "browser": "Chrome/131",
            "platform": "Linux x86_64",
            "languages": ["zh-CN", "zh", "en-US", "en"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1053, "colorDepth": 24},
        },
        # --- Linux / Firefox ---
        {
            "ua_keyword": "X11; Ubuntu",
            "browser": "Firefox/134",
            "platform": "Linux x86_64",
            "languages": ["zh-CN", "zh", "en-US"],
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1053, "colorDepth": 24},
        },
    ]

    # 反自动化检测脚本（全面指纹防护）
    # 注意：navigator.languages / platform / screen 等需要与 UA 联动，
    # 在 _build_anti_detection_script() 中动态注入。此处仅保留 UA 无关的通用补丁。
    ANTI_DETECTION_SCRIPT = """
    // 1. 隐藏 webdriver 标记
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // 2. 随机化 plugins（2~4 个真实插件）
    (function() {
        const _pluginData = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
            {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''},
            {name: 'Widevine Content Decryption Module', filename: 'widevinecdm', description: 'Widevine'},
        ];
        const cnt = Math.floor(Math.random() * 3) + 2;
        const selected = _pluginData.slice(0, cnt);
        const pl = Object.create(PluginArray.prototype);
        selected.forEach((p, i) => {
            const plugin = Object.create(Plugin.prototype);
            Object.defineProperty(plugin, 'name',        { get: () => p.name });
            Object.defineProperty(plugin, 'filename',    { get: () => p.filename });
            Object.defineProperty(plugin, 'description', { get: () => p.description });
            Object.defineProperty(pl, i, { get: () => plugin });
        });
        Object.defineProperty(pl, 'length', { get: () => selected.length });
        Object.defineProperty(navigator, 'plugins', { get: () => pl });
    })();

    // 3. 随机化 hardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency',
        { get: () => [4, 6, 8, 12][Math.floor(Math.random() * 4)] });

    // 4. 随机化 deviceMemory
    Object.defineProperty(navigator, 'deviceMemory',
        { get: () => [4, 8, 16][Math.floor(Math.random() * 3)] });

    // 5. Canvas 指纹噪声（微小像素偏移，不影响视觉）
    (function() {
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {
                try {
                    const px = ctx.getImageData(0, 0, 1, 1);
                    px.data[0] = px.data[0] ^ (Math.random() > 0.5 ? 1 : 0);
                    ctx.putImageData(px, 0, 0);
                } catch(e) {}
            }
            return origToDataURL.apply(this, args);
        };
    })();

    // 6. WebGL 指纹遮蔽（WebGL1 + WebGL2）
    (function() {
        const _renderers = [
            ['Intel Inc.', 'Intel Iris OpenGL Engine'],
            ['Intel Inc.', 'Intel(R) UHD Graphics 630'],
            ['Google Inc. (NVIDIA)', 'ANGLE (NVIDIA GeForce GTX 1650)'],
        ];
        const _chosen = _renderers[Math.floor(Math.random() * _renderers.length)];
        function patchGL(proto) {
            if (!proto) return;
            const origGetParam = proto.getParameter;
            proto.getParameter = function(param) {
                if (param === 37445) return _chosen[0];
                if (param === 37446) return _chosen[1];
                return origGetParam.apply(this, arguments);
            };
        }
        patchGL(WebGLRenderingContext.prototype);
        if (typeof WebGL2RenderingContext !== 'undefined') {
            patchGL(WebGL2RenderingContext.prototype);
        }
    })();

    // 7. AudioContext 指纹噪声
    (function() {
        if (typeof AudioContext === 'undefined' && typeof webkitAudioContext === 'undefined') return;
        const AC = typeof AudioContext !== 'undefined' ? AudioContext : webkitAudioContext;
        const origCreateOsc = AC.prototype.createOscillator;
        AC.prototype.createOscillator = function() {
            const osc = origCreateOsc.apply(this, arguments);
            const origConnect = osc.connect;
            osc.connect = function(dest) {
                if (dest && dest.frequencyBinCount) {
                    // AnalyserNode — 注入微小噪声
                    const origGetFloat = dest.getFloatFrequencyData;
                    dest.getFloatFrequencyData = function(array) {
                        origGetFloat.apply(this, arguments);
                        for (let i = 0; i < array.length; i++) {
                            array[i] += (Math.random() - 0.5) * 0.0001;
                        }
                    };
                }
                return origConnect.apply(this, arguments);
            };
            return osc;
        };
    })();

    // 8. 隐藏 Playwright/Chromium 特征
    delete window.__playwright;
    delete window.__pw_manual;
    if (window.chrome) {
        window.chrome.runtime = window.chrome.runtime || {
            connect: function() {},
            sendMessage: function() {},
        };
    }

    // 9. Permission API 真实化
    (function() {
        const origQuery = navigator.permissions && navigator.permissions.query;
        if (!origQuery) return;
        navigator.permissions.query = function(desc) {
            if (desc && desc.name === 'notifications') {
                return Promise.resolve({ state: 'prompt', onchange: null });
            }
            return origQuery.apply(this, arguments);
        };
    })();
    """

    @classmethod
    def _build_anti_detection_script(cls, profile: Dict[str, Any]) -> str:
        """
        生成与 UA 联动的完整反检测脚本。

        在通用 ANTI_DETECTION_SCRIPT 基础上，追加 navigator.languages / platform /
        screen 等需要与 UA 对应的动态补丁。
        """
        screen = profile["screen"]
        langs_js = json.dumps(profile["languages"])

        dynamic_patch = f"""
    // ── 动态指纹补丁（与 UA 一致） ──────────────────────────
    // navigator.platform
    Object.defineProperty(navigator, 'platform', {{ get: () => '{profile["platform"]}' }});

    // navigator.languages
    Object.defineProperty(navigator, 'languages', {{ get: () => {langs_js} }});
    Object.defineProperty(navigator, 'language',  {{ get: () => {langs_js}[0] }});

    // screen 尺寸（与 viewport 脱钩，真实浏览器 screen > viewport）
    Object.defineProperty(screen, 'width',       {{ get: () => {screen['width']} }});
    Object.defineProperty(screen, 'height',      {{ get: () => {screen['height']} }});
    Object.defineProperty(screen, 'availWidth',   {{ get: () => {screen['availWidth']} }});
    Object.defineProperty(screen, 'availHeight',  {{ get: () => {screen['availHeight']} }});
    Object.defineProperty(screen, 'colorDepth',   {{ get: () => {screen['colorDepth']} }});
    Object.defineProperty(screen, 'pixelDepth',   {{ get: () => {screen['colorDepth']} }});
    """
        return cls.ANTI_DETECTION_SCRIPT + dynamic_patch

    def __init__(
        self,
        max_retries: int = 3,
        request_delay: float = 2.0,
        timeout: int = 30000,
        headless: bool = True,
        save_cookies: bool = True,
    ):
        self.max_retries = max_retries
        self.request_delay = request_delay
        self.timeout = timeout
        self.headless = headless
        self.save_cookies = save_cookies

        # Playwright实例（在专用线程中管理）
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self._started = False

        # 专用线程池（单线程，所有Playwright操作在此执行）
        self._pw_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None

        # Cookie存储路径
        self.cookie_dir = Path("data/cookies")
        self.cookie_dir.mkdir(parents=True, exist_ok=True)

        # ── 智能限速器（从预设模板自动创建，与 rate_limiter.py 联动）───────
        # 延迟初始化：get_name() 是抽象方法，子类 __init__ 完成后才可用
        self._rate_limiter: Optional[RateLimiter] = None

        # ── IP 轮换器（Windows 免费方案，连续失败后自动触发） ────────────────
        # 通过环境变量 CRAWLER_IP_ROTATE=1 开启
        ip_rotate_enabled = os.getenv("CRAWLER_IP_ROTATE", "0") == "1"
        ip_rotate_adapter = os.getenv("CRAWLER_NETWORK_ADAPTER")  # 如 "以太网" / "WLAN"
        self._ip_rotator = IPRotator(
            failure_threshold=int(os.getenv("CRAWLER_IP_ROTATE_THRESHOLD", "5")),
            adapter_name=ip_rotate_adapter,
            enabled=ip_rotate_enabled,
        )

        # ── 代理支持（通过环境变量 CRAWLER_PROXY 配置） ───────────────────────
        # 格式: http://user:pass@host:port 或 socks5://host:port
        self._proxy_server: Optional[str] = os.getenv("CRAWLER_PROXY")

        # User-Agent池
        # 更新于 2026-02（与 UserAgentRotator 保持同步）
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
        ]

        # 统计信息
        self.stats = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "retries": 0,
            "blocks_detected": 0,
            "ip_rotations": 0,
        }

    # ========================================================================
    # 生命周期管理
    # ========================================================================

    @property
    def rate_limiter(self) -> RateLimiter:
        """懒加载限速器（依赖 get_name()，不能在 __init__ 中调用）"""
        if self._rate_limiter is None:
            self._rate_limiter = get_rate_limiter(self.get_name())
        return self._rate_limiter

    @staticmethod
    def _is_block_status(status: int) -> bool:
        """判断 HTTP 状态码是否表示被封禁/限流"""
        return status in (403, 429, 503, 520, 521, 522, 523, 524)

    def start(self):
        """启动浏览器（在专用线程中）"""
        if self._started:
            return
        self._pw_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=f"pw-{self.get_name()}",
        )
        future = self._pw_executor.submit(self._start_browser)
        future.result(timeout=60)
        self._started = True
        logger.info(f"{self.get_name()} 浏览器已启动 (专用线程)")

    def _start_browser(self):
        """在专用线程中启动Playwright和浏览器"""
        self.playwright = sync_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]

        # 代理支持：通过环境变量或 __init__ 参数传入
        launch_kwargs: Dict[str, Any] = {
            "headless": self.headless,
            "args": launch_args,
        }
        if self._proxy_server:
            launch_kwargs["proxy"] = {"server": self._proxy_server}
            logger.info(
                f"使用代理: {self._proxy_server.split('@')[-1] if '@' in self._proxy_server else self._proxy_server}"
            )

        self.browser = self.playwright.chromium.launch(**launch_kwargs)

    def stop(self):
        """关闭浏览器和专用线程"""
        if not self._started:
            return
        try:
            if self._pw_executor:
                future = self._pw_executor.submit(self._stop_browser)
                future.result(timeout=15)
                self._pw_executor.shutdown(wait=True)
                self._pw_executor = None
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
        self._started = False
        logger.info(f"{self.get_name()} 浏览器已关闭 | 统计: {self.stats}")

    def _stop_browser(self):
        """在专用线程中关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None

    def close(self):
        """stop的别名"""
        self.stop()

    def restart_browser(self):
        """
        重启浏览器会话（消除会话级指纹关联）。

        强制关闭当前浏览器实例，清除所有上下文/Cookie/缓存，然后重新启动。
        这会改变 TLS fingerprint、connection ID 等会话级标识符。
        建议每 3~5 批次调用一次。
        """
        logger.info(f"{self.get_name()} 重启浏览器会话（消除指纹关联）")
        self.stop()
        time.sleep(random.uniform(2, 5))  # 模拟人类重新打开浏览器的自然间隔
        self.start()
        logger.info(f"{self.get_name()} 浏览器会话已重启")

    # ========================================================================
    # 线程调度
    # ========================================================================

    def run_in_browser_thread(self, fn: Callable[..., T], *args, **kwargs) -> T:
        """
        在Playwright专用线程中执行函数。

        所有涉及Playwright的操作都必须通过此方法调用，
        以避免与FastAPI asyncio事件循环冲突。
        """
        if not self._started:
            self.start()
        timeout_sec = self.timeout / 1000 + 60  # 页面超时 + 额外缓冲
        future = self._pw_executor.submit(fn, *args, **kwargs)
        return future.result(timeout=timeout_sec)

    # ========================================================================
    # 页面管理（在浏览器线程中调用）
    # ========================================================================

    def _match_fingerprint_profile(self, ua: str) -> Dict[str, Any]:
        """
        根据选定的 User-Agent 匹配最佳指纹档案。

        遍历 _FINGERPRINT_PROFILES 找到 ua_keyword + browser 同时匹配的项；
        找不到则按 ua_keyword 宽松匹配；都不命中则随机选一个。
        """
        # 精确匹配（keyword + browser 都命中）
        for p in self._FINGERPRINT_PROFILES:
            if p["ua_keyword"] in ua and p["browser"] in ua:
                return p
        # 宽松匹配（仅 keyword）
        for p in self._FINGERPRINT_PROFILES:
            if p["ua_keyword"] in ua:
                return p
        # 兜底
        return random.choice(self._FINGERPRINT_PROFILES)

    def get_page(self) -> Page:
        """
        创建新页面（含独立上下文 + 完整指纹一致性）。

        指纹维度：UA / viewport / timezone / locale / languages / platform /
        screen / plugins / Canvas / WebGL / AudioContext / Permissions
        注意：此方法应在浏览器线程中调用（通过 run_in_browser_thread）。
        """
        if not self.browser:
            raise RuntimeError("浏览器未启动，请先调用 start()")

        # 1. 选择 UA 并匹配指纹档案
        ua = random.choice(self.user_agents)
        fp = self._match_fingerprint_profile(ua)

        # 2. 随机 viewport（从 screen 尺寸下采样，真实浏览器 viewport <= screen）
        screen_w, screen_h = fp["screen"]["width"], fp["screen"]["height"]
        viewport_choices = [
            {"width": screen_w, "height": screen_h},  # 全屏
            {"width": screen_w, "height": screen_h - random.randint(30, 100)},  # 工具栏
            {"width": int(screen_w * 0.8), "height": int(screen_h * 0.85)},  # 窗口化
        ]
        viewport = random.choice(viewport_choices)

        # 3. 创建上下文（含 timezone + locale）
        context = self.browser.new_context(
            user_agent=ua,
            viewport=viewport,
            timezone_id=fp["timezone"],
            locale=fp["locale"],
            color_scheme=random.choice(["light", "light", "light", "dark"]),  # 75%浅色
        )

        # 4. 注入完整反检测脚本（通用 + 动态联动部分）
        full_script = self._build_anti_detection_script(fp)
        context.add_init_script(full_script)

        # 5. 加载Cookie
        if self.save_cookies:
            cookie_path = self.cookie_dir / f"{self.get_name()}_cookies.json"
            if cookie_path.exists():
                try:
                    with open(cookie_path, "r") as f:
                        cookies = json.load(f)
                        context.add_cookies(cookies)
                except Exception:
                    pass

        page = context.new_page()
        page.set_default_timeout(self.timeout)
        return page

    def close_page(self, page: Page):
        """关闭页面及其浏览器上下文（防止内存泄漏）"""
        if page:
            context = page.context
            try:
                self.save_page_cookies(page)
            except Exception:
                pass
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass

    def save_page_cookies(self, page: Page):
        """保存页面Cookie"""
        if self.save_cookies:
            cookie_path = self.cookie_dir / f"{self.get_name()}_cookies.json"
            try:
                cookies = page.context.cookies()
                with open(cookie_path, "w") as f:
                    json.dump(cookies, f)
            except Exception:
                pass

    # ========================================================================
    # 请求工具（在浏览器线程中调用）
    # ========================================================================

    # Referrer 来源池（模拟搜索引擎/社交媒体自然跳转）
    _REFERRER_POOL: List[str] = [
        "https://www.google.com/",
        "https://www.google.com/search?q=architecture+design",
        "https://www.baidu.com/s?wd=建筑设计",
        "https://www.baidu.com/",
        "https://www.bing.com/search?q=architecture",
        "https://cn.bing.com/",
        "",  # 直接访问（10% 概率）
    ]

    def _get_referrer(self, url: str) -> str:
        """
        根据目标 URL 选择合理的 Referrer。

        规则：
        - 中文站点 (gooood.cn) → 偏向百度/Google
        - 英文站点 → 偏向 Google/Bing
        - 10% 概率直接访问（无 referer）
        """
        if random.random() < 0.1:
            return ""  # 直接访问
        if "gooood.cn" in url:
            return random.choice(
                [
                    "https://www.baidu.com/s?wd=建筑设计",
                    "https://www.baidu.com/",
                    "https://www.google.com/",
                    "https://www.google.com/search?q=gooood+architecture",
                ]
            )
        return random.choice(self._REFERRER_POOL[:6])  # 排除空字符串

    def fetch_with_retry(self, url: str, page: Optional[Page] = None) -> Optional[Page]:
        """
        带重试的页面加载（含 Referrer 伪装 + 智能限速 + IP 轮换）。

        改进 v10.0:
        - 使用 RateLimiter 替代简单 sleep（自适应退避 + 非均匀抖动）
        - 检测 403/429/503 等封禁状态码，触发 report_block()
        - 连续失败时自动触发 IP 轮换（需 CRAWLER_IP_ROTATE=1）
        - 成功时报告 report_success()，缓慢恢复延迟

        Args:
            url: 目标URL
            page: 已有页面（可选，不传则新建）

        Returns:
            Page对象（成功）或None（失败）
        """
        should_close_page = page is None
        if page is None:
            page = self.get_page()

        referrer = self._get_referrer(url)

        for attempt in range(self.max_retries):
            try:
                # 智能限速等待（替代简单 time.sleep）
                self.rate_limiter.wait()

                self.stats["requests"] += 1
                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout,
                    referer=referrer or None,
                )

                if response and response.ok:
                    self.stats["successes"] += 1
                    self.rate_limiter.report_success()
                    self._ip_rotator.on_success()
                    self.save_page_cookies(page)
                    return page

                # HTTP 错误 — 区分封禁 vs 普通错误
                status = response.status if response else 0
                if self._is_block_status(status):
                    self.stats["blocks_detected"] += 1
                    self.rate_limiter.report_block()
                    # IP 轮换检查
                    if self._ip_rotator.on_failure():
                        self.stats["ip_rotations"] += 1
                        # IP 已变更，重启浏览器以使用新 IP
                        logger.info("IP 已轮换，重启浏览器会话")
                        self.restart_browser()
                        page = self.get_page()
                        should_close_page = True
                    raise Exception(f"HTTP {status} (blocked)")
                else:
                    raise Exception(f"HTTP {status}")

            except Exception as e:
                self.stats["retries"] += 1
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")

                if attempt < self.max_retries - 1:
                    # 指数退避（在 RateLimiter 的自适应退避之上）
                    time.sleep(2**attempt)
                else:
                    self.stats["failures"] += 1
                    self._ip_rotator.on_failure()
                    logger.error(f"请求失败（已重试{self.max_retries}次）: {url}")
                    if should_close_page:
                        self.close_page(page)
                    return None

    # ========================================================================
    # 抽象方法（子类必须实现）
    # ========================================================================

    @abstractmethod
    def get_name(self) -> str:
        """获取爬虫名称"""
        pass

    @abstractmethod
    def get_base_url(self) -> str:
        """获取网站基础URL"""
        pass

    @abstractmethod
    def parse_project_page(self, url: str) -> Optional[ProjectData]:
        """解析项目页面"""
        pass

    @abstractmethod
    def crawl_category(
        self,
        category_url: str,
        max_pages: int = 20,
        stop_url: Optional[str] = None,
    ) -> List[str]:
        """爬取分类页面，获取项目URL列表

        Args:
            category_url: 分类页入口 URL
            max_pages: 最大翻页数（安全上限）
            stop_url: checkpoint —— 上次爬取第1页第1条文章的 URL。
                      遇到此 URL 时停止翻页，只返回更新的文章。
                      None 表示首次运行，爬取全部历史数据。
                      返回列表最后一项可能是 "__checkpoint__:<url>" 格式的哨兵，
                      由 SpiderManager 统一剥离并写入 data/crawl_checkpoints.json。
        """
        pass

    # ========================================================================
    # 可选方法（子类可覆盖）
    # ========================================================================

    def get_categories(self) -> Dict[str, str]:
        """获取网站分类列表 {分类名称: 分类URL}"""
        return {}

    def normalize_url(self, url: str) -> str:
        """标准化URL"""
        if url.startswith("//"):
            return "https:" + url
        elif url.startswith("/"):
            return self.get_base_url().rstrip("/") + url
        return url

    def extract_source_id(self, url: str) -> str:
        """从URL提取项目ID（默认实现，子类可覆盖）"""
        return url.split("/")[-1].split("?")[0]

    # ========================================================================
    # robots.txt 合规检查（缓存 24h）
    # ========================================================================

    def _is_allowed_by_robots(self, url: str) -> bool:
        """
        检查 URL 是否被 robots.txt 允许。

        - 首次调用时自动 fetch ``{base_url}/robots.txt``
        - 解析结果缓存 24h，过期后重新加载
        - 任何网络异常均返回 True（宁可爬也不因 robots 错误漏爬）
        """
        import urllib.robotparser as _urobot

        now = time.time()
        cached_at: float = getattr(self, "_robots_cached_at", 0.0)

        if cached_at == 0.0 or (now - cached_at) > 86400:
            try:
                import urllib.request

                base = self.get_base_url().rstrip("/")
                robots_url = f"{base}/robots.txt"
                rp = _urobot.RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                self._robots_parser = rp  # type: ignore[attr-defined]
            except Exception as exc:
                logger.debug(f"[robots.txt] 获取失败 ({self.get_name()}): {exc}")
                self._robots_parser = None  # type: ignore[attr-defined]
            self._robots_cached_at = now  # type: ignore[attr-defined]

        parser = getattr(self, "_robots_parser", None)
        if parser is None:
            return True
        allowed: bool = parser.can_fetch("*", url)
        if not allowed:
            logger.warning(f"[robots.txt] 禁止爬取: {url}")
        return allowed

    # ========================================================================
    # sitemap.xml 发现通道（补充翻页发现）
    # ========================================================================

    def discover_from_sitemap(
        self,
        category_filter: Optional[str] = None,
    ) -> List[str]:
        """
        从 sitemap.xml 发现项目 URL 列表。

        尝试路径顺序：
          /sitemap_index.xml → /sitemap.xml → /post-sitemap.xml → /article-sitemap.xml

        Args:
            category_filter: 若提供，则仅返回路径中含该字符串的 URL（如 ``"projects"``）

        Returns:
            项目 URL 列表（已去重，不含 checkpoint 哨兵）
        """
        import requests as _req
        from xml.etree import ElementTree as ET

        NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        base = self.get_base_url().rstrip("/")
        ua = random.choice(self.user_agents)
        headers = {"User-Agent": ua}
        found: List[str] = []

        def _fetch_xml(url: str) -> Optional[ET.Element]:
            try:
                resp = _req.get(url, timeout=15, headers=headers)
                if resp.status_code == 200:
                    return ET.fromstring(resp.content)
            except Exception:
                pass
            return None

        def _collect_from_element(root: ET.Element) -> None:
            # sitemap index：递归子 sitemap
            for sitemap_loc in root.findall(".//sm:sitemap/sm:loc", NS):
                href = (sitemap_loc.text or "").strip()
                if not href:
                    continue
                # 仅递归与项目相关的子 sitemap
                if any(kw in href for kw in ("post", "article", "project", "news")):
                    sub = _fetch_xml(href)
                    if sub is not None:
                        _collect_from_element(sub)
            # URL 集合
            for url_loc in root.findall(".//sm:url/sm:loc", NS):
                url = (url_loc.text or "").strip()
                if not url:
                    continue
                if category_filter and category_filter not in url:
                    continue
                if self._is_project_url(url) and url not in found:
                    found.append(url)

        sitemap_paths = [
            "/sitemap_index.xml",
            "/sitemap.xml",
            "/post-sitemap.xml",
            "/article-sitemap.xml",
        ]
        for path in sitemap_paths:
            root = _fetch_xml(f"{base}{path}")
            if root is not None:
                _collect_from_element(root)
                if found:
                    break  # 成功找到后不再尝试备选路径

        logger.info(
            f"[sitemap] {self.get_name()} 发现 {len(found)} 个项目 URL"
            + (f"（过滤: {category_filter}）" if category_filter else "")
        )
        return found

    # ========================================================================
    # 通用提取器（核心：所有网站共用，无需逐站编写）
    # ========================================================================

    def universal_extract(
        self,
        html: str,
        url: str,
        source: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Optional["ProjectData"]:
        """
        通用页面数据提取器。

        提取优先级（高→低）：
          1. og: / twitter: meta 标签        （标题、描述、封面图、发布时间）
          2. JSON-LD / Schema.org 结构化数据  （架构师、地点、年份、面积等）
          3. 通用 "标签：值" 段落扫描         （识别已知字段 → 标准字段，
                                               未知字段 → extra_fields）
          4. 基础 HTML 回退                   （h1 / time / article 等）

        新网站接入只需：
            class MySiteSpider(BaseSpider):
                SOURCE_NAME = "mysite"
                def get_name(self): return self.SOURCE_NAME
                def get_base_url(self): return "https://mysite.com"
                def parse_project_page(self, url):
                    html = self.run_in_browser_thread(self._fetch_html_impl, url)
                    return self.universal_extract(html, url)
                # crawl_category() 视站点分页结构实现
        """
        from bs4 import BeautifulSoup
        import json as _json

        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        _src = source or self.get_name()
        _sid = source_id or self.extract_source_id(url)

        # ── 辅助：从 soup 读 meta ─────────────────────────────────────────
        def _meta(*attrs: Dict) -> Optional[str]:
            for attr in attrs:
                tag = soup.find("meta", attr)
                if tag:
                    v = tag.get("content") or tag.get("value")
                    if v and v.strip():
                        return v.strip()
            return None

        # ════════════════════════════════════════════════════════════════════
        # 阶段 1：og: / twitter: meta 标签
        # ════════════════════════════════════════════════════════════════════
        title: Optional[str] = _meta({"property": "og:title"}) or _meta({"name": "twitter:title"})
        description: Optional[str] = (
            _meta({"property": "og:description"})
            or _meta({"name": "description"})
            or _meta({"name": "twitter:description"})
        )
        publish_date_str = (
            _meta({"property": "article:published_time"})
            or _meta({"name": "publish-date"})
            or _meta({"itemprop": "datePublished"})
        )
        lang_meta = _meta({"property": "og:locale"}) or soup.get("lang") or ""

        # ────── 发布时间解析 ──────────────────────────────────────────────
        publish_date: Optional[datetime] = None
        if publish_date_str:
            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                try:
                    publish_date = datetime.strptime(publish_date_str[:19].replace("Z", ""), fmt.rstrip("%z"))
                    break
                except ValueError:
                    pass
        if not publish_date:
            time_tag = soup.find("time", {"datetime": True})
            if time_tag:
                raw_dt = time_tag["datetime"]
                try:
                    publish_date = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                except Exception:
                    pass

        # ════════════════════════════════════════════════════════════════════
        # 阶段 2：JSON-LD 结构化数据
        # ════════════════════════════════════════════════════════════════════
        architects: List[Dict] = []
        location: Dict = {}
        area_sqm: Optional[float] = None
        year: Optional[int] = None
        ld_extra: Dict = {}  # JSON-LD 中识别到的额外字段

        VALID_TYPES = {
            "VisualArtwork",
            "CreativeWork",
            "Article",
            "NewsArticle",
            "BlogPosting",
            "WebPage",
            "ArchitecturalWork",
        }
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                ld = _json.loads(script.get_text())
                if not isinstance(ld, dict):
                    continue
                ld_type = ld.get("@type", "")
                if ld_type not in VALID_TYPES and not any(t in ld_type for t in VALID_TYPES):
                    continue

                # 标题 / 描述（若 og 未取到）
                if not title:
                    title = ld.get("headline") or ld.get("name")
                if not description:
                    description = ld.get("description") or ld.get("abstract")

                # 建筑师 / 作者 / 设计师
                for key in ("architect", "creator", "author", "contributor", "designer"):
                    val = ld.get(key)
                    if not val:
                        continue
                    if isinstance(val, dict):
                        val = [val]
                    if isinstance(val, list):
                        for item in val:
                            name = item.get("name") if isinstance(item, dict) else str(item)
                            if name and name not in [a.get("name") for a in architects]:
                                architects.append({"name": name})

                # 地点
                for loc_key in ("contentLocation", "locationCreated", "location", "spatialCoverage"):
                    loc = ld.get(loc_key)
                    if not loc:
                        continue
                    if isinstance(loc, str):
                        location = {"city": loc}
                        break
                    if isinstance(loc, dict):
                        addr = loc.get("address", {})
                        if isinstance(addr, str):
                            location = {"city": addr}
                        else:
                            location = {
                                k: v
                                for k, v in {
                                    "city": addr.get("addressLocality") or loc.get("name"),
                                    "country": addr.get("addressCountry"),
                                    "region": addr.get("addressRegion"),
                                }.items()
                                if v
                            }
                        break

                # 年份
                if not year:
                    for date_key in ("dateCreated", "datePublished", "startDate"):
                        dv = ld.get(date_key, "")
                        m_yr = re.search(r"(20\d{2}|19[5-9]\d)", str(dv))
                        if m_yr:
                            year = int(m_yr.group(1))
                            break

                # 作者
                if ld.get("publisher"):
                    pub = ld["publisher"]
                    ld_extra["publisher"] = pub.get("name") if isinstance(pub, dict) else str(pub)

            except Exception:
                pass

        # ════════════════════════════════════════════════════════════════════
        # 阶段 3：通用 "标签：值" 段落扫描
        #   · 匹配到已知字段 → 写入对应标准字段
        #   · 未匹配 → extra_fields（snake_case key）
        # ════════════════════════════════════════════════════════════════════
        KNOWN_LABEL_MAP: List[tuple] = [
            # (正则, 标准字段名 或 None表示extra, 提取函数)
            # ── 建筑师 ─────────────────────────────────────────────────
            (
                re.compile(
                    r"^(主创建筑师|主持建筑师|主创设计师|建筑师|设计师|设计单位|设计事务所|"
                    r"设计方|设计团队|Architects?|Designer?|Design\s*Team|"
                    r"Lead\s*Architect|Principal\s*Architect)",
                    re.I,
                ),
                "_architects",
                None,
            ),
            # ── 面积 ───────────────────────────────────────────────────
            (re.compile(r"^(面积|建筑面积|项目面积|Floor\s*Area|Area|GFA|GBA|Site\s*Area)", re.I), "_area", None),
            # ── 年份 ─────────────────────────────────────────────────
            (re.compile(r"^(竣工时间|竣工年份?|建成时间|建成年份?|完工|" r"Year|Completion|Built|Completed)", re.I), "_year", None),
            # ── 地点 ─────────────────────────────────────────────────
            (
                re.compile(r"^(项目地点|地点|位置|项目位置|所在地|地址|城市|" r"Location|Address|City|Country|Place)", re.I),
                "_location",
                None,
            ),
            # ── 常见 extra 字段（已知但不是标准字段）──────────────────
            (re.compile(r"^(业主|建设方|客户|甲方|委托方|Client|Owner)", re.I), "owner", None),
            (re.compile(r"^(景观设计|景观|Landscape)", re.I), "landscape_architect", None),
            (re.compile(r"^(室内设计师?|室内|Interior)", re.I), "interior_designer", None),
            (re.compile(r"^(结构设计|结构工程师?|Structural)", re.I), "structural_engineer", None),
            (re.compile(r"^(照明设计|灯光设计|Lighting)", re.I), "lighting_designer", None),
            (re.compile(r"^(材料|主要材料|Materials?)", re.I), "materials", None),
            (re.compile(r"^(造价|工程造价|预算|Budget|Cost)", re.I), "budget", None),
            (re.compile(r"^(方案类型|项目类型|Programme|Program|Type|用途|功能)", re.I), "programme", None),
        ]
        SPLIT_RE = re.compile(r"[/／;；、,，\n]+")
        NOISE_KW = {"http", "www", ".com", ".cn", "copyright", "©", "版权"}

        extra_fields: Dict = {**ld_extra}

        # 主内容区候选选择器（按优先级）
        _content_candidates = [
            soup.find("article"),
            soup.find(
                "div", class_=re.compile(r"entry[-_]content|post[-_]content|article[-_]body|project[-_]detail", re.I)
            ),
            soup.find("main"),
            soup.find("body"),
        ]
        content_root = next((c for c in _content_candidates if c), soup)

        # 大 label:value 正则（支持中英文冒号及空格）
        LINE_KV_RE = re.compile(r"^(.{1,30}?)\s*[:：]\s*(.{1,300})$")

        for p_tag in content_root.find_all(["p", "li", "div", "span", "td"]):
            # 避免嵌套重复处理
            if p_tag.find(["p", "article"]):
                continue
            raw_text = p_tag.get_text(separator="\n", strip=True)
            for line in raw_text.splitlines():
                line = line.strip()
                if not line or len(line) > 300:
                    continue
                m = LINE_KV_RE.match(line)
                if not m:
                    continue
                raw_key, raw_val = m.group(1).strip(), m.group(2).strip()
                if not raw_val or any(kw in raw_val.lower() for kw in NOISE_KW):
                    continue

                matched = False
                for pattern, field_name, _ in KNOWN_LABEL_MAP:
                    if not pattern.match(raw_key):
                        continue
                    matched = True

                    if field_name == "_architects" and not architects:
                        parts = [s.strip() for s in SPLIT_RE.split(raw_val) if 2 < len(s.strip()) < 80]
                        architects = [{"name": n} for n in parts if n]

                    elif field_name == "_area" and area_sqm is None:
                        m2 = re.search(r"([\d,\.]+)", raw_val)
                        if m2:
                            try:
                                area_sqm = float(m2.group(1).replace(",", ""))
                            except ValueError:
                                pass

                    elif field_name == "_year" and year is None:
                        m2 = re.search(r"(20\d{2}|19[5-9]\d)", raw_val)
                        if m2:
                            year = int(m2.group(1))

                    elif field_name == "_location" and not location:
                        parts = [s.strip() for s in re.split(r"[,，/]", raw_val) if s.strip()]
                        if len(parts) >= 2:
                            location = {"city": parts[0], "country": parts[-1]}
                        elif parts:
                            location = {"city": parts[0]}

                    else:
                        # 已知 extra 字段
                        if field_name not in extra_fields:
                            parts = [s.strip() for s in SPLIT_RE.split(raw_val) if s.strip()]
                            extra_fields[field_name] = parts if len(parts) > 1 else (parts[0] if parts else raw_val)
                    break

                if not matched:
                    # 完全未知字段 → snake_case key 入 extra_fields
                    key_norm = re.sub(r"[\s\-／/]+", "_", raw_key.lower())
                    key_norm = re.sub(r"[^\w]", "", key_norm)[:40]
                    if key_norm and key_norm not in extra_fields:
                        parts = [s.strip() for s in SPLIT_RE.split(raw_val) if s.strip()]
                        extra_fields[key_norm] = parts if len(parts) > 1 else (parts[0] if parts else raw_val)

        # ════════════════════════════════════════════════════════════════════
        # 阶段 4：HTML 回退
        # ════════════════════════════════════════════════════════════════════
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)[:200]
        if not title:
            title_tag = soup.find("title")
            if title_tag:
                title = re.sub(r"\s*[|\-–]\s*.+$", "", title_tag.get_text(strip=True))

        # 描述回退：取最长的 <p>（不含导航/页脚）
        if not description:
            best = ""
            for p in content_root.find_all("p"):
                t = p.get_text(strip=True)
                if len(t) > len(best) and len(t) < 5000:
                    best = t
            description = best or None

        # ════════════════════════════════════════════════════════════════════
        # 阶段 5：语言检测 + 双语字段分配
        # ════════════════════════════════════════════════════════════════════
        # 简单启发：CJK 字符占比 > 30% → 中文；< 5% → 英文；否则双语
        if description:
            cjk_count = sum(1 for c in description if "\u4e00" <= c <= "\u9fff")
            ratio = cjk_count / max(len(description), 1)
            if ratio > 0.30:
                lang = "zh"
            elif ratio < 0.05:
                lang = "en"
            else:
                lang = "bilingual"
        elif lang_meta:
            lang = "zh" if lang_meta.startswith("zh") else "en"
        else:
            lang = "unknown"

        title_zh = title if lang in ("zh", "bilingual") else None
        title_en = title if lang in ("en", "bilingual") else None
        desc_zh = description if lang in ("zh", "bilingual") else None
        desc_en = description if lang in ("en",) else None

        # ════════════════════════════════════════════════════════════════════
        # 组装 ProjectData
        # ════════════════════════════════════════════════════════════════════
        if not title:
            logger.warning(f"[universal_extract] 无法提取标题: {url}")
            return None

        tags_raw = []
        for tag_el in soup.find_all("a", rel="tag"):
            t = tag_el.get_text(strip=True)
            if t:
                tags_raw.append(t)

        return ProjectData(
            source=_src,
            source_id=_sid,
            url=url,
            title=title,
            description=description,
            architects=architects,
            location=location if location else None,
            area_sqm=area_sqm,
            year=year,
            tags=tags_raw,
            publish_date=publish_date,
            lang=lang,
            title_zh=title_zh,
            title_en=title_en,
            description_zh=desc_zh,
            description_en=desc_en,
            extra_fields=extra_fields if extra_fields else None,
        )

    def _is_project_url(self, url: str) -> bool:
        """
        判断 URL 是否为项目详情页（子类可覆盖）。

        默认规则：路径中包含 4 位以上纯数字段（常见文章 ID 格式）。
        """
        return bool(re.search(r"/\d{4,}/", url))

    def _fetch_html_pw(self, url: str, wait_selector: Optional[str] = None) -> str:
        """
        通用 Playwright 获取页面 HTML（BaseSpider 默认实现）。

        新网站爬虫可直接使用，无需重写：
            html = self.run_in_browser_thread(self._fetch_html_pw, url)

        Args:
            url: 目标页面地址
            wait_selector: 可选 CSS 选择器，等待该元素出现后再取 HTML
                           未提供时等待 2-4s 随机延迟
        """
        import time as _t

        page = self.get_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=8000)
                except Exception:
                    pass
            else:
                _t.sleep(random.uniform(2, 4))
            return page.content()
        except Exception as e:
            logger.error(f"_fetch_html_pw 失败: {url} - {e}")
            return ""
        finally:
            self.close_page(page)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# ============================================================================
# 导出
# ============================================================================

__all__ = ["BaseSpider", "ProjectData"]
