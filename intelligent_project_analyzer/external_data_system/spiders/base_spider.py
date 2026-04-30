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
from typing import Optional, Dict, Any, List, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
import time
import random
import concurrent.futures
from pathlib import Path
import json
from loguru import logger
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

T = TypeVar('T')


@dataclass
class ProjectData:
    """标准化项目数据结构"""

    # 必需字段
    source: str  # archdaily/gooood/dezeen
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

    # 原始数据（调试用）
    raw_html: Optional[str] = None

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
        }

    def validate(self) -> bool:
        """验证数据完整性"""
        if not all([self.source, self.source_id, self.url, self.title]):
            return False
        if not self.description or len(self.description) < 50:
            logger.warning(f"描述过短: {self.url}")
            return False
        return True


class BaseSpider(ABC):
    """
    爬虫基类

    核心设计：所有Playwright操作在专用线程中执行，避免与FastAPI的asyncio事件循环冲突。
    使用 run_in_browser_thread() 将任何函数调度到Playwright线程。
    """

    # 反自动化检测脚本
    ANTI_DETECTION_SCRIPT = """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    """

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

        # User-Agent池
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]

        # 统计信息
        self.stats = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "retries": 0,
        }

    # ========================================================================
    # 生命周期管理
    # ========================================================================

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
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ],
        )

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

    def get_page(self) -> Page:
        """
        创建新页面（含独立上下文）。

        注意：此方法应在浏览器线程中调用（通过 run_in_browser_thread）。
        """
        if not self.browser:
            raise RuntimeError("浏览器未启动，请先调用 start()")

        context = self.browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={'width': 1920, 'height': 1080},
        )

        # 注入反自动化检测脚本
        context.add_init_script(self.ANTI_DETECTION_SCRIPT)

        # 加载Cookie
        if self.save_cookies:
            cookie_path = self.cookie_dir / f"{self.get_name()}_cookies.json"
            if cookie_path.exists():
                try:
                    with open(cookie_path, 'r') as f:
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
                with open(cookie_path, 'w') as f:
                    json.dump(cookies, f)
            except Exception:
                pass

    # ========================================================================
    # 请求工具（在浏览器线程中调用）
    # ========================================================================

    def fetch_with_retry(self, url: str, page: Optional[Page] = None) -> Optional[Page]:
        """
        带重试的页面加载（在浏览器线程中调用）。

        Args:
            url: 目标URL
            page: 已有页面（可选，不传则新建）

        Returns:
            Page对象（成功）或None（失败）
        """
        should_close_page = (page is None)
        if page is None:
            page = self.get_page()

        for attempt in range(self.max_retries):
            try:
                self.stats["requests"] += 1
                response = page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)

                if response and response.ok:
                    self.stats["successes"] += 1
                    self.save_page_cookies(page)
                    time.sleep(self.request_delay + random.uniform(0, 1))
                    return page
                else:
                    raise Exception(f"HTTP {response.status if response else 'Unknown'}")

            except Exception as e:
                self.stats["retries"] += 1
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {url} - {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.stats["failures"] += 1
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
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return self.get_base_url().rstrip('/') + url
        return url

    def extract_source_id(self, url: str) -> str:
        """从URL提取项目ID（默认实现，子类可覆盖）"""
        return url.split('/')[-1].split('?')[0]

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# ============================================================================
# 导出
# ============================================================================

__all__ = ['BaseSpider', 'ProjectData']
