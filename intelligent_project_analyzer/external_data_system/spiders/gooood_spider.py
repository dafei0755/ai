"""
Gooood 爬虫

爬取 Gooood.cn 的建筑项目数据
特点：中英双语内容，中国及亚洲项目为主
注意：分类页面使用Vue.js动态渲染，需要Playwright

分类基准：基于 2026-02-25 扫描数据（data/gooood_types.json）
URL 格式：https://www.gooood.cn/filter/type/{slug}/country/all/material/all/office/all
翻页格式：https://www.gooood.cn/filter/type/{slug}/country/all/material/all/office/all/page/{n}/
"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import requests
from loguru import logger
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from .base_spider import BaseSpider, ProjectData
from ..utils import get_rate_limiter


class GoooodSpider(BaseSpider):
    """Gooood 网站爬虫

    分类目录树来源：https://www.gooood.cn/filter/type/all/...（复合检索）
    API 来源：https://dashboard.gooood.cn/api/wp/v2/type（2026-02-25 扫描确认）
    """

    # ========================================================================
    # 空间类型分类目录树（基准数据，2026-02-25 扫描确认，共 24 类）
    # 仅保留"空间/项目类型"维度，排除专辑/地区/材料/公司/产品设计/摄影等非空间分类
    # URL 格式：/filter/type/{slug}/country/all/material/all/office/all
    #
    # 爬取策略：checkpoint 机制（data/crawl_checkpoints.json）
    #   - 首次运行：无 checkpoint，从第1页爬到最后，自动覆盖全量历史
    #   - 后续运行：遇到上次第1页第1条 URL 时停止翻页，只取新增内容
    #   无需区分"全量"和"增量"模式
    # ========================================================================
    CATEGORIES = {
        # 核心空间类型（文章数 ≥ 500）
        "商业建筑":     "https://www.gooood.cn/filter/type/commercial-architecture/country/all/material/all/office/all",
        "休闲娱乐":     "https://www.gooood.cn/filter/type/hospitality/country/all/material/all/office/all",
        "住宅建筑":     "https://www.gooood.cn/filter/type/residential-architecture/country/all/material/all/office/all",
        "文化建筑":     "https://www.gooood.cn/filter/type/culture-architecture/country/all/material/all/office/all",
        "公共空间":     "https://www.gooood.cn/filter/type/public-space/country/all/material/all/office/all",
        "教育建筑":     "https://www.gooood.cn/filter/type/educational-architecture/country/all/material/all/office/all",
        "装置艺术":     "https://www.gooood.cn/filter/type/installation/country/all/material/all/office/all",
        "公共职能建筑": "https://www.gooood.cn/filter/type/pubilc-architecture/country/all/material/all/office/all",
        "交通建筑":     "https://www.gooood.cn/filter/type/transportation/country/all/material/all/office/all",
        "绿色建筑":     "https://www.gooood.cn/filter/type/green-architecture/country/all/material/all/office/all",
        "体育建筑":     "https://www.gooood.cn/filter/type/sports-architecture/country/all/material/all/office/all",
        "综合体":       "https://www.gooood.cn/filter/type/complex/country/all/material/all/office/all",
        # 补充空间类型（文章数 100–499）
        "高层建筑":     "https://www.gooood.cn/filter/type/high-rise/country/all/material/all/office/all",
        "工业建筑":     "https://www.gooood.cn/filter/type/industrial-architecture/country/all/material/all/office/all",
        "中国乡建":     "https://www.gooood.cn/filter/type/rural-reconstruction-of-china/country/all/material/all/office/all",
        "工业建筑改造": "https://www.gooood.cn/filter/type/industrial-architecture-renovation/country/all/material/all/office/all",
        "宗教建筑":     "https://www.gooood.cn/filter/type/religious-architecture/country/all/material/all/office/all",
        "园区":         "https://www.gooood.cn/filter/type/campus/country/all/material/all/office/all",
        "医疗建筑":     "https://www.gooood.cn/filter/type/healthcare-architecture/country/all/material/all/office/all",
        "社区中心":     "https://www.gooood.cn/filter/type/community-center/country/all/material/all/office/all",
        "滨海建筑":     "https://www.gooood.cn/filter/type/coastal-architecture/country/all/material/all/office/all",
        "热带建筑":     "https://www.gooood.cn/filter/type/tropical-architecture/country/all/material/all/office/all",
        "城市更新":     "https://www.gooood.cn/filter/type/revitalization/country/all/material/all/office/all",
        "古建保护":     "https://www.gooood.cn/filter/type/conservation-of-historic-buildings/country/all/material/all/office/all",
    }

    # 网站各分类已知文章数（定期手动更新，用于进度展示）
    CATEGORY_TOTALS: Dict[str, int] = {
        "商业建筑":     6169,
        "休闲娱乐":     5666,
        "住宅建筑":     5481,
        "文化建筑":     3545,
        "公共空间":     2140,
        "教育建筑":     1681,
        "装置艺术":     1383,
        "公共职能建筑":  755,
        "交通建筑":      604,
        "绿色建筑":      558,
        "体育建筑":      530,
        "综合体":        527,
        "高层建筑":      389,
        "工业建筑":      398,
        "中国乡建":      395,
        "工业建筑改造":  368,
        "宗教建筑":      348,
        "园区":          318,
        "医疗建筑":      269,
        "社区中心":      265,
        "滨海建筑":      263,
        "热带建筑":      210,
        "城市更新":      203,
        "古建保护":      111,
    }

    def __init__(self, use_playwright: bool = True):
        super().__init__()
        self.source = "gooood"
        self.base_url = "https://www.gooood.cn"
        self.rate_limiter = get_rate_limiter('gooood')
        self.use_playwright = use_playwright
        # 最近一次列表页解析到的最大页码（page 1 解析后设置）
        self._last_max_page: Optional[int] = None

    # ========================================================================
    # BaseSpider 抽象方法实现
    # ========================================================================

    def get_name(self) -> str:
        return "gooood"

    def get_base_url(self) -> str:
        return "https://www.gooood.cn"

    def parse_project_page(self, url: str) -> Optional[ProjectData]:
        """解析项目页面（线程安全，可从任意线程调用）"""
        return self.fetch_project_detail(url)

    def get_categories(self) -> Dict[str, str]:
        return self.CATEGORIES

    def close(self):
        self.stop()

    def crawl_category(
        self,
        category_url: str,
        max_pages: int = 500,
        stop_url: Optional[str] = None,
    ) -> List[str]:
        """爬取分类页面，获取项目URL列表

        checkpoint 机制：
          - stop_url 为上次爬取时第1页第1条文章的 URL（由 spider_manager 传入）
          - 翻页过程中遇到 stop_url 即停止，只返回比它更新的文章
          - stop_url=None（首次运行）→ 爬完所有历史数据

        支持的 URL 格式：
          https://www.gooood.cn/filter/type/{slug}/country/all/material/all/office/all
        """
        # 从 filter URL 提取 type slug
        type_slug = ""
        if "/filter/type/" in category_url:
            m = re.search(r"/filter/type/([^/]+)/", category_url)
            if m:
                type_slug = m.group(1)
        elif "/category/" in category_url:
            parts = category_url.split("/category/")
            type_slug = parts[1].rstrip("/") if len(parts) > 1 else ""
            logger.warning(f"旧版 category URL 已失效，请换用 filter URL: {category_url}")

        logger.info(f"爬取分类 type_slug={type_slug or 'ALL'}, stop_url={'有' if stop_url else '无（首次全量）'}")

        new_urls: List[str] = []
        first_url: Optional[str] = None  # 本次第1页第1条，用于更新 checkpoint

        for page in range(1, max_pages + 1):
            project_list = self.fetch_project_list(page=page, type_slug=type_slug)
            if not project_list:
                logger.info(f"第{page}页无项目，停止翻页（新增 {len(new_urls)} 条）")
                break

            page_urls = [item['url'] for item in project_list]

            # 记录本次第1页第1条作为新 checkpoint
            if page == 1 and page_urls:
                first_url = page_urls[0]

            # checkpoint 检查：遇到上次基准 URL 即停止
            if stop_url and stop_url in page_urls:
                idx = page_urls.index(stop_url)
                new_urls.extend(page_urls[:idx])
                logger.info(f"第{page}页遇到 checkpoint，收集前{idx}条，停止翻页（新增 {len(new_urls)} 条）")
                break

            logger.info(f"第{page}页: {len(page_urls)} 条")
            new_urls.extend(page_urls)

        # 将本次第1条 URL 附在返回值末尾供 spider_manager 更新 checkpoint
        # 格式："__checkpoint__:<url>" ["|total:<N>"] —— total 即该分类网站估算总量
        if first_url:
            sentinel = f"__checkpoint__:{first_url}"
            if self._last_max_page and self._last_max_page > 1 and len(new_urls) > 0:
                # items_per_page: 用本次第1页的条数估算
                # new_urls 未包含 sentinel，所以如果没有提前停止，第1页条数=new_urls 中第一批
                # 简化：用 ceil(len(new_urls) / pages_used) 
                # 更简单：直接用 max_page * gooood 已知每页条数 12 估算
                # gooood 每页固定 12 条，根据实际分页数计算
                est_total = self._last_max_page * 12
                sentinel += f"|total:{est_total}"
                logger.info(f"  分类网站估算总量: {self._last_max_page} 页 × 12 = {est_total} 条")
            new_urls.append(sentinel)

        return new_urls

    # ========================================================================
    # Gooood 特定方法
    # ========================================================================

    def fetch_project_list(self, page: int = 1, type_slug: str = "", category: str = "") -> List[Dict[str, str]]:
        """获取项目列表

        Args:
            page: 页码（从1开始）
            type_slug: 分类 slug，来自 CATEGORIES（新版 filter 格式）
            category: 旧版兼容参数，不推荐使用
        """
        # 兼容旧版 category 参数
        if not type_slug and category:
            type_slug = category
            logger.warning(f"category 参数已废弃，请使用 type_slug")

        # 构建正确的 filter URL
        if type_slug and type_slug != "all":
            base_filter = f"{self.base_url}/filter/type/{type_slug}/country/all/material/all/office/all"
        else:
            base_filter = f"{self.base_url}/filter/type/all/country/all/material/all/office/all"

        if page == 1:
            url = base_filter
        else:
            url = f"{base_filter}/page/{page}/"

        logger.info(f"获取项目列表: {url}")

        if self.use_playwright:
            return self._fetch_list_playwright(url)
        else:
            return self._fetch_list_requests(url)

    def _fetch_list_requests(self, url: str) -> List[Dict[str, str]]:
        """使用requests获取项目列表（服务端渲染页面）"""
        try:
            self.rate_limiter.wait()
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            projects = self._parse_list_html(response.text)
            self.rate_limiter.report_success()
            return projects
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            self.rate_limiter.report_block()
            return []

    def _fetch_list_playwright(self, url: str) -> List[Dict[str, str]]:
        """使用Playwright获取项目列表（Vue.js动态渲染页面）"""
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
        """在浏览器线程中获取列表页HTML（支持 filter URL 的 Vue 渲染）"""
        page = self.get_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=45000)
            # filter 页面是 Vue 渲染，优先等待文章卡片
            selectors = [
                'article.sg-article-item',   # filter 分类页
                '.sg-article-item',           # 备用
                'article',                    # 通用
            ]
            loaded = False
            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=8000)
                    loaded = True
                    break
                except PlaywrightTimeout:
                    continue
            if not loaded:
                logger.warning(f"等待文章元素超时，尝试直接获取内容: {url}")
                page.wait_for_timeout(3000)
            return page.content()
        finally:
            self.close_page(page)

    def _parse_list_html(self, html: str) -> List[Dict[str, str]]:
        """解析列表页HTML，提取项目卡片"""
        soup = BeautifulSoup(html, 'html.parser')
        projects = []

        for article in soup.find_all('article', class_=re.compile(r'sg-article-item')):
            try:
                link_elem = article.find('a')
                if not link_elem:
                    continue

                href = link_elem.get('href', '')
                if not href:
                    continue

                if href.startswith('http'):
                    project_url = href
                else:
                    project_url = f"{self.base_url}{href}" if href.startswith('/') else f"{self.base_url}/{href}"

                title = link_elem.get('title', '') or link_elem.get_text(strip=True)
                if not title:
                    continue

                img_elem = article.find('img')
                preview_image = img_elem.get('src', '') if img_elem else ''

                projects.append({
                    'url': project_url,
                    'title': title,
                    'preview_image': preview_image,
                })
            except Exception as e:
                logger.warning(f"解析项目卡片失败: {e}")
                continue

        logger.info(f"找到 {len(projects)} 个项目")

        # 解析分页最大页码（.paginations 里最大的数字链接）
        try:
            max_p = 1
            for a in soup.select('.paginations a[href]'):
                try:
                    n = int(a.get_text(strip=True))
                    if n > max_p:
                        max_p = n
                except ValueError:
                    pass
            if max_p > 1:
                self._last_max_page = max_p
        except Exception:
            pass

        return projects

    def fetch_project_detail(self, url: str) -> Optional[ProjectData]:
        """获取项目详情（线程安全）"""
        logger.info(f"爬取项目详情: {url}")

        try:
            self.rate_limiter.wait()

            if self.use_playwright:
                html = self.run_in_browser_thread(self._fetch_detail_pw_impl, url)
                if not html:
                    self.rate_limiter.report_block()
                    return None
            else:
                response = requests.get(url, headers=self._get_headers(), timeout=30)
                response.raise_for_status()
                html = response.text

            soup = BeautifulSoup(html, 'html.parser')

            source_id = url.rstrip('/').split('/')[-1]

            title_elem = soup.find('h1', class_='entry-title')
            title = title_elem.get_text(strip=True) if title_elem else "Untitled"

            description = self._extract_description(soup)
            architects = self._extract_architects(soup)
            location = self._extract_location(soup)
            year = self._extract_year(soup, description)
            area_sqm = self._extract_area(soup, description)
            images = self._extract_images(soup) or []
            categories = self._extract_categories(soup) or []
            primary_category = categories[0] if categories else None
            tags = self._extract_tags(soup) or []

            project = ProjectData(
                source=self.source,
                source_id=source_id,
                url=url,
                title=title,
                description=description,
                architects=architects,
                location=location,
                year=year,
                area_sqm=area_sqm,
                images=images,
                primary_category=primary_category,
                sub_categories=categories[1:] if len(categories) > 1 else [],
                tags=tags,
            )

            logger.info(f"项目爬取成功: {title}")
            self.rate_limiter.report_success()
            return project

        except Exception as e:
            logger.error(f"爬取项目详情失败: {e}")
            import traceback
            traceback.print_exc()
            self.rate_limiter.report_block()
            return None

    def _fetch_detail_pw_impl(self, url: str) -> str:
        """在浏览器线程中获取详情页HTML"""
        page = self.get_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            try:
                page.wait_for_selector('div.client-render', timeout=10000)
                page.wait_for_timeout(2000)
            except PlaywrightTimeout:
                logger.warning("等待内容渲染超时")
            html = page.content()
            logger.debug(f"页面内容获取成功，长度: {len(html)} 字节")
            return html
        except Exception as e:
            logger.error(f"Playwright获取页面失败: {e}")
            return ""
        finally:
            self.close_page(page)

    # ========================================================================
    # 数据提取方法
    # ========================================================================

    def _extract_description(self, soup: BeautifulSoup) -> str:
        content_div = soup.find('div', class_='entry-content')
        if not content_div:
            return ""
        paragraphs = []
        for p in content_div.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 20 and text not in ['收藏本文', 'Collect this article']:
                paragraphs.append(text)
        return '\n\n'.join(paragraphs)

    def _extract_architects(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        architects = []
        content_div = soup.find('div', class_='entry-content')
        if content_div:
            for p in content_div.find_all('p'):
                text = p.get_text()
                if 'architect' in text.lower() or '建筑师' in text or '设计' in text:
                    match = re.search(r'(?:architect|建筑师|设计)[:：]\s*(.+)', text, re.IGNORECASE)
                    if match:
                        name = match.group(1).strip()
                        architects.append({"name": name})
                        break
        return architects

    def _extract_location(self, soup: BeautifulSoup) -> Dict[str, str]:
        content_div = soup.find('div', class_='entry-content')
        location = {}
        if content_div:
            for p in content_div.find_all('p'):
                text = p.get_text()
                if 'location' in text.lower() or '位置' in text or '地点' in text:
                    match = re.search(r'(?:location|位置|地点)[:：]\s*(.+)', text, re.IGNORECASE)
                    if match:
                        location_str = match.group(1).strip()
                        parts = re.split(r'[,，]', location_str)
                        if len(parts) >= 2:
                            location = {"city": parts[0].strip(), "country": parts[-1].strip()}
                        else:
                            location = {"city": location_str}
                        break
        return location

    def _extract_year(self, soup: BeautifulSoup, description: str = "") -> Optional[int]:
        if description:
            year_match = re.search(r'\b(20\d{2}|19\d{2})\b', description)
            if year_match:
                return int(year_match.group(1))
        content_div = soup.find('div', class_='entry-content')
        if content_div:
            for p in content_div.find_all('p'):
                text = p.get_text()
                if 'year' in text.lower() or '年份' in text or '完成时间' in text:
                    year_match = re.search(r'\b(20\d{2}|19\d{2})\b', text)
                    if year_match:
                        return int(year_match.group(1))
        return None

    def _extract_area(self, soup: BeautifulSoup, description: str) -> Optional[float]:
        area_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:m²|sqm|square meters|平方米)', description, re.IGNORECASE)
        if area_match:
            return float(area_match.group(1).replace(',', ''))
        content_div = soup.find('div', class_='entry-content')
        if content_div:
            for p in content_div.find_all('p'):
                text = p.get_text()
                if 'area' in text.lower() or '面积' in text:
                    area_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:m²|sqm|平方米)', text, re.IGNORECASE)
                    if area_match:
                        return float(area_match.group(1).replace(',', ''))
        return None

    def _extract_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        raw: List[str] = []
        content_div = soup.find('div', class_='entry-content')
        if content_div:
            for img in content_div.find_all('img'):
                src = img.get('src', '')
                if src and 'loading' not in src:
                    width = img.get('width')
                    if width:
                        try:
                            if int(width) > 200:
                                raw.append(src)
                        except (ValueError, TypeError):
                            raw.append(src)
                    else:
                        raw.append(src)
        seen: List[str] = list(dict.fromkeys(raw))[:30]
        return [{"url": s, "caption": ""} for s in seen]

    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        categories = []
        breadcrumb = soup.find('nav', class_='breadcrumb')
        if breadcrumb:
            for link in breadcrumb.find_all('a'):
                text = link.get_text(strip=True)
                if text and text not in ['Home', '首页', 'Gooood']:
                    categories.append(text)
        cat_links = soup.find_all('a', rel='category tag')
        for link in cat_links:
            text = link.get_text(strip=True)
            if text and text not in categories:
                categories.append(text)
        return categories

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        tags = []
        tag_links = soup.find_all('a', rel='tag')
        for link in tag_links:
            text = link.get_text(strip=True)
            if text:
                tags.append(text)
        return tags

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.gooood.cn/",
            "DNT": "1",
        }


__all__ = ['GoooodSpider']
