"""
Dezeen 爬虫

数据源: https://www.dezeen.com
内容语言: en（全英文；中文译文由 translator 后续填充）
反爬策略: 中等（Playwright + UA 伪装 + 随机延迟 4-6 s + 超时设置 60 s）
分类数量: 5（Architecture / Interiors / Design / Landscape / Urban Design）
字段覆盖: architects / location / year / tags
调度: disabled — wed 02:00 (Asia/Shanghai)
接入时间: 2026-02

项目 URL 格式:
  https://www.dezeen.com/<yyyy>/<mm>/<dd>/<slug>/

注意事项:
  - 内容全英文，就算 title_zh / description_zh 当前为空，后续由翻译服务填入
  - area_sqm 尚未实现（Dezeen 页面很少列出面积）
  - 列表页用 /‹yyyy›/‹mm›/‹dd›/ 过滤无关链接
"""

import re
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from .base_spider import BaseSpider, ProjectData
from ..utils import get_rate_limiter
from .registry import register_spider


class DezeenSpider(BaseSpider):
    """Dezeen 网站爬虫"""

    SOURCE_NAME: str = "dezeen"
    DISPLAY_NAME: str = "Dezeen"
    SCHEDULE = {
        "enabled": False,  # 待开放；改 True 即接入调度
        "priority": 3,
        "day_of_week": "wed",
        "hour": 2,
        "minute": 0,
    }

    CATEGORIES = {
        "Architecture": "https://www.dezeen.com/architecture",
        "Interiors": "https://www.dezeen.com/interiors",
        "Design": "https://www.dezeen.com/design",
        "Landscape": "https://www.dezeen.com/landscape",
        "Urban Design": "https://www.dezeen.com/urbanism-and-infrastructure",
    }

    def __init__(self, use_playwright: bool = True):
        super().__init__(timeout=60000)  # Dezeen需要更长超时
        self.source = "dezeen"
        self.base_url = "https://www.dezeen.com"
        self.rate_limiter = get_rate_limiter("dezeen")
        self.use_playwright = use_playwright

    # ========================================================================
    # BaseSpider 抽象方法实现
    # ========================================================================

    def get_name(self) -> str:
        return "dezeen"

    def get_base_url(self) -> str:
        return "https://www.dezeen.com"

    def parse_project_page(self, url: str) -> Optional[ProjectData]:
        return self.fetch_project_detail(url)

    def get_categories(self) -> Dict[str, str]:
        return self.CATEGORIES

    def close(self):
        self.stop()

    def crawl_category(
        self,
        category_url: str,
        max_pages: int = 20,
        stop_url: Optional[str] = None,
    ) -> List[str]:
        category = category_url.replace(self.base_url, "").strip("/")
        logger.info(f"爬取分类: {category}, stop_url={'有' if stop_url else '无（首次全量）'}")

        urls: List[str] = []
        first_url: Optional[str] = None
        consecutive_empty = 0  # 连续空页计数（防单次抖动提前结束）

        for page_num in range(1, max_pages + 1):
            project_list = self.fetch_project_list(page=page_num, category=category)

            if not project_list:
                consecutive_empty += 1
                if consecutive_empty == 1:
                    # 第一次空页：等待后重试一次，避免动态加载慢导致漏页
                    logger.warning(f"第{page_num}页无项目（可能加载慢），{10}s 后重试...")
                    time.sleep(random.uniform(8, 15))
                    project_list = self.fetch_project_list(page=page_num, category=category)

                if not project_list:
                    logger.info(f"第{page_num}页重试仍无项目，停止爬取")
                    break
                consecutive_empty = 0
            else:
                consecutive_empty = 0

            page_urls = [item["url"] for item in project_list]
            logger.debug(f"第{page_num}页找到 {len(page_urls)} 个项目")

            if page_num == 1 and page_urls:
                first_url = page_urls[0]

            # stop_url 检查
            if stop_url and stop_url in page_urls:
                idx = page_urls.index(stop_url)
                urls.extend(page_urls[:idx])
                logger.info(f"第{page_num}页遇到 checkpoint，" f"收集前{idx}条，停止翻页（新增 {len(urls)} 条）")
                break

            urls.extend(page_urls)

        if first_url:
            urls.append(f"__checkpoint__:{first_url}")

        return urls

    # ========================================================================
    # 项目列表爬取
    # ========================================================================

    def fetch_project_list(self, page: int = 1, category: str = "") -> List[Dict[str, str]]:
        if category:
            url = f"{self.base_url}/{category}/" if page == 1 else f"{self.base_url}/{category}/page/{page}/"
        else:
            url = self.base_url if page == 1 else f"{self.base_url}/page/{page}/"

        logger.debug(f"获取项目列表: {url}")
        self.rate_limiter.wait()

        try:
            html = self.run_in_browser_thread(self._fetch_list_pw_impl, url)
            projects = self._parse_list_html(html)
            self.rate_limiter.report_success()
            return projects
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            self.rate_limiter.report_block()
            return []

    def _fetch_list_pw_impl(self, url: str) -> str:
        """在浏览器线程中获取列表页HTML"""
        page = self.get_page()
        try:
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                if not response or response.status in [403, 404]:
                    logger.warning(f"响应状态码: {response.status if response else 'None'}")
                    return ""
            except PlaywrightTimeout:
                logger.warning(f"页面加载超时（{self.timeout/1000}秒），尝试继续解析")

            time.sleep(random.uniform(3, 8))

            try:
                page.wait_for_selector("article, .dezeen-article, .post", timeout=12000)
            except PlaywrightTimeout:
                logger.warning("文章元素加载超时，尝试解析现有内容")

            return page.content()
        finally:
            self.close_page(page)

    def _parse_list_html(self, html: str) -> List[Dict[str, str]]:
        """解析列表页HTML"""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        projects = []

        articles = (
            soup.find_all("article")
            or soup.find_all("div", class_=lambda x: x and "post" in x.lower() if x else False)
            or soup.find_all("div", class_=lambda x: x and "article" in x.lower() if x else False)
        )

        for article in articles:
            try:
                link_elem = article.find("a", href=True)
                if not link_elem:
                    continue

                href = link_elem.get("href", "")
                if not href or not re.search(r"/\d{4}/\d{2}/\d{2}/", href):
                    continue

                if href.startswith("http"):
                    project_url = href
                else:
                    project_url = f"{self.base_url}{href}" if href.startswith("/") else f"{self.base_url}/{href}"

                title_elem = link_elem.find("h2") or link_elem.find("h3") or article.find("h2") or article.find("h3")
                title = title_elem.get_text(strip=True) if title_elem else link_elem.get("title", "")
                if not title:
                    continue

                img_elem = article.find("img")
                preview_image = img_elem.get("src", "") or img_elem.get("data-src", "") if img_elem else ""

                projects.append(
                    {
                        "url": project_url,
                        "title": title,
                        "preview_image": preview_image,
                    }
                )
            except Exception as e:
                logger.warning(f"解析项目卡片失败: {e}")
                continue

        logger.debug(f"找到 {len(projects)} 个项目")
        return projects

    # ========================================================================
    # 项目详情爬取
    # ========================================================================

    def fetch_project_detail(self, url: str) -> Optional[ProjectData]:
        logger.debug(f"爬取项目详情: {url}")
        self.rate_limiter.wait()

        try:
            html = self.run_in_browser_thread(self._fetch_detail_pw_impl, url)
            if not html:
                self.rate_limiter.report_error() if hasattr(
                    self.rate_limiter, "report_error"
                ) else self.rate_limiter.report_block()
                return None

            soup = BeautifulSoup(html, "html.parser")
            data = self._extract_project_data(soup, url)

            if data:
                logger.debug(f"项目爬取成功: {data.title}")
                self.rate_limiter.report_success()
                return data
            else:
                logger.error("数据提取失败")
                return None

        except Exception as e:
            logger.error(f"爬取失败: {e}")
            self.rate_limiter.report_block()
            return None

    def _fetch_detail_pw_impl(self, url: str) -> str:
        """在浏览器线程中获取详情页HTML"""
        page = self.get_page()
        try:
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                if not response or response.status != 200:
                    logger.error(f"响应状态码: {response.status if response else 'None'}")
                    return ""
            except PlaywrightTimeout:
                logger.warning("页面加载超时，尝试继续解析")

            time.sleep(random.uniform(3, 8))
            return page.content()
        except Exception as e:
            logger.error(f"Playwright获取页面失败: {e}")
            return ""
        finally:
            self.close_page(page)

    # ========================================================================
    # 数据提取
    # ========================================================================

    def _extract_project_data(self, soup: BeautifulSoup, url: str) -> Optional[ProjectData]:
        try:
            title = self._extract_title(soup)
            if not title:
                logger.warning("未找到标题")
                return None

            description = self._extract_description(soup)
            source_id = url.rstrip("/").split("/")[-1]
            architects = self._extract_architects(soup)
            location = self._extract_location(soup)
            year = self._extract_year(soup)
            categories = self._extract_categories(soup)
            primary_category = categories[0] if categories else None
            sub_categories = categories[1:] if len(categories) > 1 else []
            tags = self._extract_tags(soup)
            images = self._extract_images(soup)
            publish_date = self._extract_publish_date(soup)

            # ── dezeen 特有字段：文章类型、JSON-LD环境信息────────────
            import json as _json

            extra_fields: Dict = {}
            # 1. 文章类型（如 architecture / interiors / design / technology 等）
            article_type_meta = soup.find("meta", {"property": "article:section"})
            if article_type_meta and article_type_meta.get("content"):
                extra_fields["article_type"] = article_type_meta["content"].lower()
            # 2. 关键词（article:tag）
            kw_meta = soup.find("meta", {"name": "keywords"})
            if kw_meta and kw_meta.get("content"):
                kws = [k.strip() for k in kw_meta["content"].split(",") if k.strip()]
                if kws:
                    extra_fields["keywords"] = kws
            # 3. 从 JSON-LD 读取作者和奖项信息
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    ld = _json.loads(script.get_text())
                    if isinstance(ld, dict):
                        if ld.get("@type") in ("Article", "NewsArticle"):
                            author = ld.get("author")
                            if author:
                                if isinstance(author, dict):
                                    extra_fields["author"] = author.get("name", "")
                                elif isinstance(author, list):
                                    extra_fields["author"] = [a.get("name", "") for a in author if isinstance(a, dict)]

                except Exception:
                    pass

            return ProjectData(
                source="dezeen",
                source_id=source_id,
                url=url,
                title=title,
                description=description,
                architects=architects,
                location=location,
                area_sqm=None,
                year=year,
                primary_category=primary_category,
                sub_categories=sub_categories,
                tags=tags,
                images=images,
                publish_date=publish_date,
                raw_html=str(soup),
                # 双语字段：dezeen 全英文，中文译文由 translator 后续填充
                lang="en",
                title_en=title,
                description_en=description,
                # 扩展字段
                extra_fields=extra_fields if extra_fields else None,
            )
        except Exception as e:
            logger.error(f"提取项目数据失败: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title:
            title = og_title.get("content", "")
            if title:
                title = re.sub(r"\s*[\|\-]\s*Dezeen.*$", "", title, flags=re.IGNORECASE)
                return title.strip()

        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
            if title and len(title) < 200 and "dezeen-logo" not in title.lower():
                return title

        title_elem = soup.find("title")
        if title_elem:
            title = title_elem.get_text(strip=True)
            title = re.sub(r"\s*[\|\-]\s*Dezeen.*$", "", title, flags=re.IGNORECASE)
            return title.strip() if title else None

        return None

    def _extract_description(self, soup: BeautifulSoup) -> str:
        article_body = (
            soup.find("div", class_=lambda x: x and "post-content" in x.lower() if x else False)
            or soup.find("div", class_=lambda x: x and "entry-content" in x.lower() if x else False)
            or soup.find("div", class_=lambda x: x and "article-content" in x.lower() if x else False)
            or soup.find("article")
        )
        if not article_body:
            return ""

        valid_paragraphs = []
        for p in article_body.find_all("p"):
            # 跳过 <figure> 内的 <p>（图注/说明文字）
            if p.find_parent("figure"):
                continue
            text = p.get_text(strip=True)
            if len(text) < 30:
                continue
            if any(
                kw in text.lower()
                for kw in [
                    "subscribe",
                    "newsletter",
                    "follow us",
                    "read more",
                    "see also",
                    "related:",
                    "advertisement",
                    "sponsored",
                ]
            ):
                continue
            valid_paragraphs.append(text)

        return "\n\n".join(valid_paragraphs)

    def _extract_architects(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        names: List[str] = []
        author_meta = soup.find("meta", {"name": "author"}) or soup.find("meta", {"property": "author"})
        if author_meta:
            author = author_meta.get("content", "")
            if author and author.lower() not in ["dezeen", "admin"]:
                names.append(author)

        for p in soup.find_all("p", limit=10):
            text = p.get_text()
            by_match = re.search(r"\bby\s+([A-Z][a-zA-Z\s&,]+(?:Architects?|Studio|Design)?)", text)
            if by_match:
                architect = by_match.group(1).strip()
                if architect and len(architect) < 100:
                    names.append(architect)
                    break

        return [{"name": n} for n in list(dict.fromkeys(names))]

    def _extract_location(self, soup: BeautifulSoup) -> Dict[str, Any]:
        location = {}
        h1 = soup.find("h1")
        if h1:
            match = re.search(r"\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z][a-z]+)", h1.get_text())
            if match:
                location["city"] = match.group(1).strip()
                location["country"] = match.group(2).strip()

        if not location:
            for p in soup.find_all("p", limit=5):
                match = re.search(r"\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z][a-z]+)", p.get_text())
                if match:
                    location["city"] = match.group(1).strip()
                    location["country"] = match.group(2).strip()
                    break

        return location

    def _extract_year(self, soup: BeautifulSoup) -> Optional[int]:
        time_elem = soup.find("time", {"datetime": True})
        if time_elem:
            match = re.search(r"(\d{4})", time_elem.get("datetime", ""))
            if match:
                return int(match.group(1))

        date_meta = soup.find("meta", {"property": "article:published_time"})
        if date_meta:
            match = re.search(r"(\d{4})", date_meta.get("content", ""))
            if match:
                return int(match.group(1))

        return None

    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        categories = []
        for link in soup.find_all("a", href=True, limit=20):
            href = link.get("href", "")
            if re.match(r"^/(architecture|interiors|design)/?$", href):
                cat = href.strip("/")
                if cat and cat not in categories:
                    categories.append(cat)
        return categories

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        tags = []
        for link in soup.find_all("a", href=lambda x: x and "/tag/" in x if x else False):
            tag = link.get_text(strip=True)
            if tag and len(tag) < 50:
                tags.append(tag)
        return tags[:20]

    def _extract_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        # 不爬取图片及说明文字（脱离图片，这些备注说明失去意义）
        return []

    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        time_elem = soup.find("time", {"datetime": True})
        raw: Optional[str] = None
        if time_elem:
            raw = time_elem.get("datetime")
        if not raw:
            date_meta = soup.find("meta", {"property": "article:published_time"})
            if date_meta:
                raw = date_meta.get("content")
        if not raw:
            return None
        try:
            # ISO 8601 格式: 2024-01-15T10:30:00+00:00
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            try:
                return datetime.strptime(raw[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                return None


# ── 注册到 SpiderRegistry ──────────────────────────────────────────────────
register_spider(DezeenSpider.SOURCE_NAME)(DezeenSpider)

__all__ = ["DezeenSpider"]
