"""
混合网页内容提取器 (v7.196)

组合方案：
- Trafilatura：处理静态网页（高效轻量，无需渲染）
- Playwright：处理动态网页（JavaScript 渲染，SPA 支持）

策略：
1. 首先尝试 Trafilatura（快速，0.5-2秒）
2. 如果内容过短或提取失败，降级到 Playwright（慢，3-10秒）
3. 智能识别动态网站域名，直接使用 Playwright

v7.196 改进：
- 增强日志：记录每个 URL 的提取方法和失败原因
- URL 缓存：避免重复提取相同 URL
- 慢站点超时：对已知慢站点设置更长超时
- 重试机制：Playwright 失败时重试一次

作者: AI Assistant
日期: 2026-01-10
"""

import asyncio
import os
import re
import ssl
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Trafilatura 导入（静态提取）
try:
    import trafilatura
    from trafilatura.settings import use_config

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    trafilatura = None
    logger.warning("⚠️ trafilatura 未安装，静态提取功能不可用")

# Playwright 导入（动态渲染）
try:
    from playwright.async_api import Browser, Page, async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    logger.warning("⚠️ playwright 未安装，动态渲染功能不可用")


# ==================== 配置 ====================

# 环境变量配置
CONTENT_EXTRACTION_ENABLED = os.getenv("CONTENT_EXTRACTION_ENABLED", "true").lower() == "true"
CONTENT_EXTRACTION_MAX_LENGTH = int(os.getenv("CONTENT_EXTRACTION_MAX_LENGTH", "2000"))  # 每页最大提取字符数
CONTENT_EXTRACTION_MIN_LENGTH = int(os.getenv("CONTENT_EXTRACTION_MIN_LENGTH", "300"))  # 低于此长度触发 Playwright
CONTENT_EXTRACTION_TIMEOUT = int(os.getenv("CONTENT_EXTRACTION_TIMEOUT", "15"))  # v7.200: 超时秒数（10→15秒）
CONTENT_EXTRACTION_CACHE_SIZE = int(os.getenv("CONTENT_EXTRACTION_CACHE_SIZE", "100"))  # 缓存大小
CONTENT_EXTRACTION_RETRY_COUNT = int(os.getenv("CONTENT_EXTRACTION_RETRY_COUNT", "1"))  # 重试次数

# v7.216: SSL容错机制配置
SSL_RETRY_ATTEMPTS = int(os.getenv("SSL_RETRY_ATTEMPTS", "3"))  # SSL错误重试次数
SSL_VERIFY_ENABLED = os.getenv("SSL_VERIFY_ENABLED", "true").lower() == "true"  # SSL证书验证
SSL_FALLBACK_ENABLED = os.getenv("SSL_FALLBACK_ENABLED", "true").lower() == "true"  # SSL降级模式

# 已知需要动态渲染的域名（SPA、重 JS 网站）
DYNAMIC_DOMAINS = {
    # 社交媒体
    "weibo.com",
    "m.weibo.cn",
    "zhihu.com",
    "zhuanlan.zhihu.com",
    "xiaohongshu.com",
    "xhslink.com",
    "douyin.com",
    "tiktok.com",
    # 电商平台
    "taobao.com",
    "tmall.com",
    "jd.com",
    # 设计/建筑相关
    "archdaily.cn",
    "gooood.cn",
    "pinterest.com",
    # 其他动态站点
    "bilibili.com",
}

# 低质量站点（跳过深度提取）
LOW_QUALITY_DOMAINS = {
    "baijiahao.baidu.com",
    "zhidao.baidu.com",
    "tieba.baidu.com",
    "wenku.baidu.com",
    "haokan.baidu.com",
}

# v7.199: 持续失败的域名（自动跳过）
# 这些域名在多次尝试后仍然失败，暂时跳过以提高效率
PERSISTENT_FAILURE_DOMAINS = {
    "hotel.csair.com",  # 持续 ERR_HTTP2_PROTOCOL_ERROR
    "www.0516-sj.com",  # 持续超时
    "www.feidesign09.com",  # 持续超时
    "www.isococ.com",  # 502 Bad Gateway
}

# v7.199: 失败URL缓存（运行时记录）
_failed_urls_cache: Dict[str, int] = {}  # url -> 失败次数
FAILURE_THRESHOLD = 2  # 失败次数阈值，超过后跳过

# v7.200: 已知慢站点（需要更长超时）- 扩展覆盖更多学术/设计站点
SLOW_DOMAINS = {
    # 设计/建筑媒体
    "archdaily.cn": 18,
    "archdaily.com": 18,
    "gooood.cn": 18,
    "dezeen.com": 15,
    "designboom.com": 15,
    "architizer.com": 15,
    "interiordesign.net": 15,
    "behance.net": 15,
    "dribbble.com": 15,
    "awwwards.com": 15,
    "nngroup.com": 15,
    # 学术数据库（通常较慢）
    "cnki.net": 20,
    "wanfangdata.com.cn": 20,
    "cqvip.com": 20,
    "researchgate.net": 18,
    "sciencedirect.com": 18,
    "springer.com": 18,
    "arxiv.org": 15,
    # 社交媒体
    "pinterest.com": 18,
    "zhihu.com": 15,
    "xiaohongshu.com": 18,
    "medium.com": 15,
    # 其他
    "uxdesign.cc": 15,
    "smashingmagazine.com": 15,
}


class ExtractionMethod(Enum):
    """提取方法枚举"""

    TRAFILATURA = "trafilatura"
    PLAYWRIGHT = "playwright"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class ExtractionResult:
    """提取结果"""

    url: str
    content: str
    title: Optional[str] = None
    method: ExtractionMethod = ExtractionMethod.FAILED
    extraction_time: float = 0.0
    error: Optional[str] = None
    from_cache: bool = False  # v7.196: 是否来自缓存
    retry_count: int = 0  # v7.196: 重试次数


class LRUCache:
    """简单的 LRU 缓存实现"""

    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, ExtractionResult] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> Optional[ExtractionResult]:
        if key in self._cache:
            # 移动到末尾（最近使用）
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: ExtractionResult) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                # 移除最久未使用的项
                self._cache.popitem(last=False)
        self._cache[key] = value

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


class WebContentExtractor:
    """
    混合网页内容提取器

    使用策略：
    1. 检查是否为低质量域名 → 跳过
    2. 检查是否为持续失败域名 → 跳过 (v7.199)
    3. 检查是否为已知动态域名 → 直接 Playwright
    4. 尝试 Trafilatura → 成功则返回
    5. 内容不足 → 降级 Playwright

    v7.199 改进：
    - 持续失败域名自动跳过
    - 运行时失败URL记录
    - 失败次数阈值控制

    v7.196 改进：
    - URL 缓存避免重复提取
    - 慢站点自适应超时
    - 失败重试机制
    - 增强诊断日志
    """

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._browser_lock = asyncio.Lock()
        self._cache = LRUCache(max_size=CONTENT_EXTRACTION_CACHE_SIZE)  # v7.196: URL 缓存

        # Trafilatura 配置
        if TRAFILATURA_AVAILABLE:
            self._traf_config = use_config()
            self._traf_config.set("DEFAULT", "EXTRACTION_TIMEOUT", str(CONTENT_EXTRACTION_TIMEOUT))

    async def _get_browser(self) -> Optional[Browser]:
        """获取或创建 Playwright 浏览器实例（单例）"""
        if not PLAYWRIGHT_AVAILABLE:
            return None

        async with self._browser_lock:
            if self._browser is None:
                try:
                    self._playwright = await async_playwright().start()
                    self._browser = await self._playwright.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                        ],
                    )
                    logger.info("✅ [WebExtractor] Playwright 浏览器初始化成功")
                except Exception as e:
                    logger.error(f"❌ [WebExtractor] Playwright 初始化失败: {e}")
                    return None
            return self._browser

    async def close(self):
        """关闭浏览器资源"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    def _get_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ""

    def _is_dynamic_site(self, url: str) -> bool:
        """检查是否为动态网站"""
        domain = self._get_domain(url)
        for dyn_domain in DYNAMIC_DOMAINS:
            if dyn_domain in domain:
                return True
        return False

    def _is_low_quality_site(self, url: str) -> bool:
        """检查是否为低质量站点"""
        domain = self._get_domain(url)
        for lq_domain in LOW_QUALITY_DOMAINS:
            if lq_domain in domain:
                return True
        return False

    def _is_persistent_failure_site(self, url: str) -> bool:
        """v7.199: 检查是否为持续失败的站点"""
        domain = self._get_domain(url)
        for fail_domain in PERSISTENT_FAILURE_DOMAINS:
            if fail_domain in domain:
                return True
        return False

    def _should_skip_url(self, url: str) -> Tuple[bool, str]:
        """
        v7.199: 综合判断是否应该跳过URL

        Returns:
            (should_skip, reason)
        """
        global _failed_urls_cache

        # 1. 低质量站点
        if self._is_low_quality_site(url):
            return True, "low_quality_site"

        # 2. 持续失败域名
        if self._is_persistent_failure_site(url):
            return True, "persistent_failure_domain"

        # 3. 运行时失败记录
        if url in _failed_urls_cache and _failed_urls_cache[url] >= FAILURE_THRESHOLD:
            return True, f"failed_{_failed_urls_cache[url]}_times"

        return False, ""

    def _record_failure(self, url: str) -> None:
        """v7.199: 记录URL失败"""
        global _failed_urls_cache
        if url in _failed_urls_cache:
            _failed_urls_cache[url] += 1
        else:
            _failed_urls_cache[url] = 1
        logger.debug(f"📝 [WebExtractor] 记录失败: {url} (累计{_failed_urls_cache[url]}次)")

    def _get_timeout_for_url(self, url: str) -> int:
        """获取 URL 对应的超时时间（v7.196: 慢站点自适应超时）"""
        domain = self._get_domain(url)
        for slow_domain, timeout in SLOW_DOMAINS.items():
            if slow_domain in domain:
                return timeout
        return CONTENT_EXTRACTION_TIMEOUT

    def _create_ssl_tolerant_client(self, timeout: int) -> httpx.AsyncClient:
        """v7.216: 创建SSL容错的HTTP客户端"""
        # 基础配置
        client_kwargs = {
            "timeout": timeout,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            "follow_redirects": True,
        }

        # SSL容错配置
        if not SSL_VERIFY_ENABLED:
            # 禁用SSL验证（测试环境）
            client_kwargs["verify"] = False
        else:
            # 创建宽松的SSL上下文
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_OPTIONAL  # 允许自签名证书
            client_kwargs["verify"] = ssl_context

        return httpx.AsyncClient(**client_kwargs)

    @retry(
        stop=stop_after_attempt(SSL_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((ssl.SSLError, httpx.ConnectError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_html_with_ssl_fallback(self, url: str, timeout: int) -> str:
        """v7.216: SSL容错的HTML获取方法"""
        try:
            # 首次尝试：正常SSL验证
            async with self._create_ssl_tolerant_client(timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except (ssl.SSLError, httpx.ConnectError) as e:
            if SSL_FALLBACK_ENABLED:
                logger.warning(f"🔒 [WebExtractor] SSL错误，尝试降级模式 | {url[:50]}... | 错误: {str(e)[:100]}")
                # 降级：禁用SSL验证
                async with httpx.AsyncClient(timeout=timeout, verify=False, follow_redirects=True) as fallback_client:
                    response = await fallback_client.get(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        },
                    )
                    response.raise_for_status()
                    return response.text
            else:
                raise

    async def _extract_with_trafilatura(self, url: str) -> ExtractionResult:
        """使用 Trafilatura 提取静态内容（v7.216: 增强SSL容错）"""
        start_time = time.time()
        timeout = self._get_timeout_for_url(url)  # v7.196: 自适应超时

        if not TRAFILATURA_AVAILABLE:
            return ExtractionResult(url=url, content="", method=ExtractionMethod.FAILED, error="trafilatura 未安装")

        try:
            # v7.216: 使用SSL容错获取HTML
            html_content = await self._fetch_html_with_ssl_fallback(url, timeout)

            # 使用 trafilatura 提取正文
            extracted = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
                config=self._traf_config,
            )

            # 提取标题
            title = trafilatura.extract_metadata(html_content)
            title_text = title.title if title and hasattr(title, "title") else None

            extraction_time = time.time() - start_time

            if extracted and len(extracted) >= CONTENT_EXTRACTION_MIN_LENGTH:
                # 截断到最大长度
                content = extracted[:CONTENT_EXTRACTION_MAX_LENGTH]
                logger.debug(f"✅ [Trafilatura] 提取成功 | {url[:50]}... | {len(content)}字 | {extraction_time:.2f}秒")
                return ExtractionResult(
                    url=url,
                    content=content,
                    title=title_text,
                    method=ExtractionMethod.TRAFILATURA,
                    extraction_time=extraction_time,
                )
            else:
                # 内容过短，需要降级
                return ExtractionResult(
                    url=url,
                    content=extracted or "",
                    title=title_text,
                    method=ExtractionMethod.FAILED,
                    extraction_time=extraction_time,
                    error=f"内容过短: {len(extracted) if extracted else 0}字",
                )

        except (ssl.SSLError, httpx.ConnectError) as e:
            # v7.216: SSL/连接错误详细记录
            extraction_time = time.time() - start_time
            error_type = type(e).__name__
            logger.warning(
                f"🔐 [WebExtractor] {error_type} | {url[:60]} | 耗时={extraction_time:.2f}秒 | 错误={str(e)[:100]}"
            )
            return ExtractionResult(
                url=url,
                content="",
                method=ExtractionMethod.FAILED,
                extraction_time=extraction_time,
                error=f"{error_type}: {str(e)}",
            )
        except httpx.TimeoutException:
            return ExtractionResult(
                url=url,
                content="",
                method=ExtractionMethod.FAILED,
                extraction_time=time.time() - start_time,
                error="请求超时",
            )
        except Exception as e:
            return ExtractionResult(
                url=url,
                content="",
                method=ExtractionMethod.FAILED,
                extraction_time=time.time() - start_time,
                error=str(e),
            )

    async def _extract_with_playwright(self, url: str, retry_attempt: int = 0) -> ExtractionResult:
        """使用 Playwright 提取动态内容（v7.196: 支持重试）"""
        start_time = time.time()
        timeout = self._get_timeout_for_url(url)  # v7.196: 自适应超时

        browser = await self._get_browser()
        if not browser:
            return ExtractionResult(url=url, content="", method=ExtractionMethod.FAILED, error="Playwright 不可用")

        page = None
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers(
                {
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                }
            )

            # 导航到页面（使用自适应超时）
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

            # 等待主要内容加载
            await asyncio.sleep(1.5)  # 等待 JS 渲染

            # 提取标题
            title = await page.title()

            # 提取正文内容
            # 尝试多种常见的正文选择器
            content = ""
            selectors = [
                "article",
                "main",
                ".article-content",
                ".post-content",
                ".content",
                "#content",
                ".entry-content",
                ".rich-text",
                ".Post-RichTextContainer",  # 知乎
                ".note-content",  # 小红书
                '[class*="content"]',
            ]

            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements:
                        text = await el.text_content()
                        if text and len(text) > len(content):
                            content = text
                except:
                    continue

            # 如果没找到，获取 body 全文
            if len(content) < CONTENT_EXTRACTION_MIN_LENGTH:
                body = await page.query_selector("body")
                if body:
                    content = await body.text_content() or ""

            # 清理内容
            content = self._clean_content(content)
            content = content[:CONTENT_EXTRACTION_MAX_LENGTH]

            extraction_time = time.time() - start_time

            if len(content) >= CONTENT_EXTRACTION_MIN_LENGTH:
                logger.debug(f"✅ [Playwright] 提取成功 | {url[:50]}... | {len(content)}字 | {extraction_time:.2f}秒")
                return ExtractionResult(
                    url=url,
                    content=content,
                    title=title,
                    method=ExtractionMethod.PLAYWRIGHT,
                    extraction_time=extraction_time,
                    retry_count=retry_attempt,
                )
            else:
                return ExtractionResult(
                    url=url,
                    content=content,
                    title=title,
                    method=ExtractionMethod.FAILED,
                    extraction_time=extraction_time,
                    error=f"提取内容过短: {len(content)}字",
                    retry_count=retry_attempt,
                )

        except Exception as e:
            extraction_time = time.time() - start_time
            error_msg = str(e)

            # v7.196: 重试机制
            if retry_attempt < CONTENT_EXTRACTION_RETRY_COUNT:
                logger.warning(
                    f"🔄 [Playwright] 重试 {retry_attempt + 1}/{CONTENT_EXTRACTION_RETRY_COUNT} | {url[:50]}... | 错误: {error_msg[:50]}"
                )
                await asyncio.sleep(1)  # 等待 1 秒后重试
                if page:
                    await page.close()
                return await self._extract_with_playwright(url, retry_attempt + 1)

            # v7.196: 增强错误日志
            logger.warning(f"❌ [Playwright] 提取失败 | {url[:60]} | 耗时={extraction_time:.2f}秒 | 错误={error_msg[:80]}")
            return ExtractionResult(
                url=url,
                content="",
                method=ExtractionMethod.FAILED,
                extraction_time=extraction_time,
                error=error_msg,
                retry_count=retry_attempt,
            )
        finally:
            if page:
                await page.close()

    def _clean_content(self, text: str) -> str:
        """清理提取的文本内容"""
        if not text:
            return ""

        # 移除多余空白
        text = re.sub(r"\s+", " ", text)
        # 移除常见噪音
        noise_patterns = [
            r"登录|注册|关注|收藏|分享|点赞|评论",
            r"©.*版权",
            r"备案号[：:]\s*\S+",
            r"举报|投诉",
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, "", text)

        return text.strip()

    async def extract(self, url: str) -> ExtractionResult:
        """
        提取网页内容 - 主入口

        策略：
        1. 检查缓存 → 命中则直接返回
        2. v7.199: 综合跳过检查（低质量/持续失败/运行时失败）
        3. 已知动态站点 → Playwright
        4. 其他 → Trafilatura，失败则降级 Playwright
        """
        if not CONTENT_EXTRACTION_ENABLED:
            return ExtractionResult(url=url, content="", method=ExtractionMethod.SKIPPED, error="内容提取功能已禁用")

        # v7.196: 检查缓存
        cached = self._cache.get(url)
        if cached:
            logger.debug(f"📦 [WebExtractor] 缓存命中 | {url[:50]}...")
            cached.from_cache = True
            return cached

        # v7.199: 综合跳过检查
        should_skip, skip_reason = self._should_skip_url(url)
        if should_skip:
            logger.info(f"⏭️ [WebExtractor] 跳过URL: {url[:60]} | 原因: {skip_reason}")
            result = ExtractionResult(url=url, content="", method=ExtractionMethod.SKIPPED, error=skip_reason)
            return result

        # 2. 检查动态站点 → 直接 Playwright
        if self._is_dynamic_site(url):
            logger.info(f"🎭 [WebExtractor] 动态站点 → Playwright | {url[:60]}")
            result = await self._extract_with_playwright(url)
            self._log_extraction_result(url, result, "动态站点")
            if result.method == ExtractionMethod.FAILED:
                self._record_failure(url)  # v7.199: 记录失败
            else:
                self._cache.set(url, result)
            return result

        # 3. 静态站点 → Trafilatura
        result = await self._extract_with_trafilatura(url)

        # 4. 如果失败或内容不足，降级到 Playwright
        if result.method == ExtractionMethod.FAILED and PLAYWRIGHT_AVAILABLE:
            logger.info(f"🔄 [WebExtractor] Trafilatura 失败({result.error}) → 降级 Playwright | {url[:60]}")
            result = await self._extract_with_playwright(url)
            self._log_extraction_result(url, result, "降级Playwright")
            if result.method == ExtractionMethod.FAILED:
                self._record_failure(url)  # v7.199: 记录失败
        else:
            self._log_extraction_result(url, result, "Trafilatura")

        # 缓存成功结果
        if result.method != ExtractionMethod.FAILED:
            self._cache.set(url, result)

        return result

    def _log_extraction_result(self, url: str, result: ExtractionResult, strategy: str) -> None:
        """v7.196: 增强日志 - 记录每个 URL 的提取详情"""
        domain = self._get_domain(url)
        if result.method in (ExtractionMethod.TRAFILATURA, ExtractionMethod.PLAYWRIGHT):
            logger.info(
                f"✅ [WebExtractor] {strategy} 成功 | "
                f"域名={domain} | 方法={result.method.value} | "
                f"长度={len(result.content)}字 | 耗时={result.extraction_time:.2f}秒"
            )
        else:
            logger.warning(
                f"❌ [WebExtractor] {strategy} 失败 | "
                f"域名={domain} | URL={url[:80]} | "
                f"错误={result.error} | 耗时={result.extraction_time:.2f}秒"
            )

    async def extract_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5,
        max_urls: int = 10,
    ) -> Dict[str, ExtractionResult]:
        """
        批量提取网页内容

        Args:
            urls: URL 列表
            max_concurrent: 最大并发数
            max_urls: 最大提取数量（避免过长延迟）

        Returns:
            URL -> ExtractionResult 映射
        """
        # 限制数量
        urls_to_process = urls[:max_urls]

        results: Dict[str, ExtractionResult] = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def extract_with_semaphore(url: str) -> Tuple[str, ExtractionResult]:
            async with semaphore:
                result = await self.extract(url)
                return url, result

        # 并发提取
        tasks = [extract_with_semaphore(url) for url in urls_to_process]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, tuple):
                url, result = item
                results[url] = result
            elif isinstance(item, Exception):
                logger.warning(f"⚠️ [WebExtractor] 批量提取异常: {item}")

        # 统计
        success_count = sum(
            1 for r in results.values() if r.method in (ExtractionMethod.TRAFILATURA, ExtractionMethod.PLAYWRIGHT)
        )
        cache_hits = sum(1 for r in results.values() if r.from_cache)
        failed_count = sum(1 for r in results.values() if r.method == ExtractionMethod.FAILED)
        skipped_count = sum(1 for r in results.values() if r.method == ExtractionMethod.SKIPPED)

        # v7.196: 增强统计日志
        logger.info(
            f"📊 [WebExtractor] 批量提取完成 | "
            f"成功={success_count}/{len(urls_to_process)} | "
            f"缓存命中={cache_hits} | 失败={failed_count} | 跳过={skipped_count}"
        )

        # v7.196: 记录失败详情
        if failed_count > 0:
            failed_urls = [url for url, r in results.items() if r.method == ExtractionMethod.FAILED]
            for url in failed_urls[:3]:  # 最多记录 3 个
                result = results[url]
                logger.warning(f"   ❌ 失败: {url[:70]} | 原因: {result.error}")

        return results


# ==================== 单例模式 ====================

_extractor_instance: Optional[WebContentExtractor] = None


def get_web_content_extractor() -> WebContentExtractor:
    """获取 WebContentExtractor 单例"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = WebContentExtractor()
    return _extractor_instance


def get_cache_stats() -> Dict[str, int]:
    """v7.196: 获取缓存统计信息"""
    if _extractor_instance:
        return {
            "cache_size": len(_extractor_instance._cache),
            "max_size": CONTENT_EXTRACTION_CACHE_SIZE,
        }
    return {"cache_size": 0, "max_size": CONTENT_EXTRACTION_CACHE_SIZE}


async def cleanup_extractor():
    """清理提取器资源"""
    global _extractor_instance
    if _extractor_instance:
        await _extractor_instance.close()
        _extractor_instance._cache.clear()  # v7.196: 清理缓存
        _extractor_instance = None
