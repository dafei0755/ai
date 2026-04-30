"""
Dezeen 爬虫

爬取 Dezeen.com 的建筑设计项目数据
特点：国际最权威的建筑设计杂志之一，内容全英文
注意：需要Playwright绕过反爬虫机制，需要更长的超时时间
"""

import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from .base_spider import BaseSpider, ProjectData
from ..utils import get_rate_limiter


class DezeenSpider(BaseSpider):
    """Dezeen 网站爬虫"""

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
        self.rate_limiter = get_rate_limiter('dezeen')
        self.use_playwright = use_playwright
        self.wait_after_load = 5

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

    def crawl_category(self, category_url: str, max_pages: int = 20) -> List[str]:
        category = category_url.replace(self.base_url, '').strip('/')
        logger.info(f"爬取分类: {category}")

        urls = []
        for page in range(1, max_pages + 1):
            project_list = self.fetch_project_list(page=page, category=category)
            if not project_list:
                logger.info(f"第{page}页无项目，停止爬取")
                break
            logger.info(f"第{page}页找到 {len(project_list)} 个项目")
            urls.extend([item['url'] for item in project_list])
            # 频率控制已由 rate_limiter 处理，此处不需额外阈塞调用线程

        return urls

    # ========================================================================
    # 项目列表爬取
    # ========================================================================

    def fetch_project_list(self, page: int = 1, category: str = "") -> List[Dict[str, str]]:
        if category:
            url = f"{self.base_url}/{category}/" if page == 1 else f"{self.base_url}/{category}/page/{page}/"
        else:
            url = self.base_url if page == 1 else f"{self.base_url}/page/{page}/"

        logger.info(f"获取项目列表: {url}")
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
                response = page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                if not response or response.status in [403, 404]:
                    logger.warning(f"响应状态码: {response.status if response else 'None'}")
                    return ""
            except PlaywrightTimeout:
                logger.warning(f"页面加载超时（{self.timeout/1000}秒），尝试继续解析")

            time.sleep(self.wait_after_load)

            try:
                page.wait_for_selector('article, .dezeen-article, .post', timeout=10000)
            except PlaywrightTimeout:
                logger.warning("文章元素加载超时，尝试解析现有内容")

            return page.content()
        finally:
            self.close_page(page)

    def _parse_list_html(self, html: str) -> List[Dict[str, str]]:
        """解析列表页HTML"""
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        projects = []

        articles = (
            soup.find_all('article') or
            soup.find_all('div', class_=lambda x: x and 'post' in x.lower() if x else False) or
            soup.find_all('div', class_=lambda x: x and 'article' in x.lower() if x else False)
        )

        for article in articles:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue

                href = link_elem.get('href', '')
                if not href or not re.search(r'/\d{4}/\d{2}/\d{2}/', href):
                    continue

                if href.startswith('http'):
                    project_url = href
                else:
                    project_url = f"{self.base_url}{href}" if href.startswith('/') else f"{self.base_url}/{href}"

                title_elem = link_elem.find('h2') or link_elem.find('h3') or article.find('h2') or article.find('h3')
                title = title_elem.get_text(strip=True) if title_elem else link_elem.get('title', '')
                if not title:
                    continue

                img_elem = article.find('img')
                preview_image = img_elem.get('src', '') or img_elem.get('data-src', '') if img_elem else ''

                projects.append({
                    'url': project_url,
                    'title': title,
                    'preview_image': preview_image,
                })
            except Exception as e:
                logger.warning(f"解析项目卡片失败: {e}")
                continue

        logger.info(f"找到 {len(projects)} 个项目")
        return projects

    # ========================================================================
    # 项目详情爬取
    # ========================================================================

    def fetch_project_detail(self, url: str) -> Optional[ProjectData]:
        logger.info(f"爬取项目详情: {url}")
        self.rate_limiter.wait()

        try:
            html = self.run_in_browser_thread(self._fetch_detail_pw_impl, url)
            if not html:
                self.rate_limiter.report_error() if hasattr(self.rate_limiter, 'report_error') else self.rate_limiter.report_block()
                return None

            soup = BeautifulSoup(html, 'html.parser')
            data = self._extract_project_data(soup, url)

            if data:
                logger.info(f"项目爬取成功: {data.title}")
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
                response = page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                if not response or response.status != 200:
                    logger.error(f"响应状态码: {response.status if response else 'None'}")
                    return ""
            except PlaywrightTimeout:
                logger.warning("页面加载超时，尝试继续解析")

            time.sleep(self.wait_after_load)
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
            source_id = url.rstrip('/').split('/')[-1]
            architects = self._extract_architects(soup)
            location = self._extract_location(soup)
            year = self._extract_year(soup)
            categories = self._extract_categories(soup)
            primary_category = categories[0] if categories else None
            sub_categories = categories[1:] if len(categories) > 1 else []
            tags = self._extract_tags(soup)
            images = self._extract_images(soup)
            publish_date = self._extract_publish_date(soup)

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
            )
        except Exception as e:
            logger.error(f"提取项目数据失败: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        og_title = soup.find('meta', {'property': 'og:title'})
        if og_title:
            title = og_title.get('content', '')
            if title:
                title = re.sub(r'\s*[\|\-]\s*Dezeen.*$', '', title, flags=re.IGNORECASE)
                return title.strip()

        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            if title and len(title) < 200 and 'dezeen-logo' not in title.lower():
                return title

        title_elem = soup.find('title')
        if title_elem:
            title = title_elem.get_text(strip=True)
            title = re.sub(r'\s*[\|\-]\s*Dezeen.*$', '', title, flags=re.IGNORECASE)
            return title.strip() if title else None

        return None

    def _extract_description(self, soup: BeautifulSoup) -> str:
        article_body = (
            soup.find('div', class_=lambda x: x and 'post-content' in x.lower() if x else False) or
            soup.find('div', class_=lambda x: x and 'entry-content' in x.lower() if x else False) or
            soup.find('div', class_=lambda x: x and 'article-content' in x.lower() if x else False) or
            soup.find('article')
        )
        if not article_body:
            return ""

        valid_paragraphs = []
        for p in article_body.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) < 30:
                continue
            if any(kw in text.lower() for kw in [
                'subscribe', 'newsletter', 'follow us', 'read more',
                'see also', 'related:', 'advertisement', 'sponsored'
            ]):
                continue
            valid_paragraphs.append(text)

        return '\n\n'.join(valid_paragraphs)

    def _extract_architects(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        names: List[str] = []
        author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'author'})
        if author_meta:
            author = author_meta.get('content', '')
            if author and author.lower() not in ['dezeen', 'admin']:
                names.append(author)

        for p in soup.find_all('p', limit=10):
            text = p.get_text()
            by_match = re.search(r'\bby\s+([A-Z][a-zA-Z\s&,]+(?:Architects?|Studio|Design)?)', text)
            if by_match:
                architect = by_match.group(1).strip()
                if architect and len(architect) < 100:
                    names.append(architect)
                    break

        return [{"name": n} for n in list(dict.fromkeys(names))]

    def _extract_location(self, soup: BeautifulSoup) -> Dict[str, Any]:
        location = {}
        h1 = soup.find('h1')
        if h1:
            match = re.search(r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z][a-z]+)', h1.get_text())
            if match:
                location['city'] = match.group(1).strip()
                location['country'] = match.group(2).strip()

        if not location:
            for p in soup.find_all('p', limit=5):
                match = re.search(r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z][a-z]+)', p.get_text())
                if match:
                    location['city'] = match.group(1).strip()
                    location['country'] = match.group(2).strip()
                    break

        return location

    def _extract_year(self, soup: BeautifulSoup) -> Optional[int]:
        time_elem = soup.find('time', {'datetime': True})
        if time_elem:
            match = re.search(r'(\d{4})', time_elem.get('datetime', ''))
            if match:
                return int(match.group(1))

        date_meta = soup.find('meta', {'property': 'article:published_time'})
        if date_meta:
            match = re.search(r'(\d{4})', date_meta.get('content', ''))
            if match:
                return int(match.group(1))

        return None

    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        categories = []
        for link in soup.find_all('a', href=True, limit=20):
            href = link.get('href', '')
            if re.match(r'^/(architecture|interiors|design)/?$', href):
                cat = href.strip('/')
                if cat and cat not in categories:
                    categories.append(cat)
        return categories

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        tags = []
        for link in soup.find_all('a', href=lambda x: x and '/tag/' in x if x else False):
            tag = link.get_text(strip=True)
            if tag and len(tag) < 50:
                tags.append(tag)
        return tags[:20]

    def _extract_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        raw: List[str] = []
        article_body = soup.find('article') or soup.find('div', class_=lambda x: x and 'content' in x.lower() if x else False)
        if article_body:
            for img in article_body.find_all('img'):
                src = img.get('src', '') or img.get('data-src', '')
                if src and src.startswith('http'):
                    if any(skip in src.lower() for skip in ['logo', 'icon', 'avatar', 'placeholder']):
                        continue
                    raw.append(src)
        caption_map: Dict[str, str] = {}
        for fig in (article_body.find_all('figure') if article_body else []):
            img = fig.find('img')
            cap = fig.find('figcaption')
            if img and cap:
                caption_map[img.get('src', '') or img.get('data-src', '')] = cap.get_text(strip=True)
        return [{"url": s, "caption": caption_map.get(s, "")} for s in raw[:50]]

    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        time_elem = soup.find('time', {'datetime': True})
        raw: Optional[str] = None
        if time_elem:
            raw = time_elem.get('datetime')
        if not raw:
            date_meta = soup.find('meta', {'property': 'article:published_time'})
            if date_meta:
                raw = date_meta.get('content')
        if not raw:
            return None
        try:
            # ISO 8601 格式: 2024-01-15T10:30:00+00:00
            return datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            try:
                return datetime.strptime(raw[:10], '%Y-%m-%d')
            except (ValueError, TypeError):
                return None


__all__ = ['DezeenSpider']
