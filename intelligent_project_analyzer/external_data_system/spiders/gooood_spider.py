"""
Gooood 爬虫

数据源: https://www.gooood.cn
内容语言: bilingual（中英双语；中文为主）
反爬策略: 中等（Playwright + UA 伪装 + 随机延迟 4-6 s + Vue.js 动态渲染）
分类数量: 60+（基于 2026-02-25 扫描：data/gooood_types.json）
字段覆盖: architects / location / year / area / tags
调度: disabled — tue 02:00 (Asia/Shanghai)
接入时间: 2026-02

URL 格式:
  分类页: https://www.gooood.cn/filter/type/{slug}/country/all/material/all/office/all
  翻页:    …/page/{n}/
  项目页: https://www.gooood.cn/<slug>-<id>.htm

注意事项:
  - 分类页使用 Vue.js 动态渲染，必须等待 .project-card-container 了载
  - architects 匹配中英双语标签：设计/Design方/Architects 等 10 个关键词
  - area 支持 万平方米/ha/亩 单位自动转换
  - year 仅含 1950~CY+2 范围，不扫描正文避免误匹
"""

import random
import re
import time
from datetime import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from ..utils.lang_utils import split_bilingual_paragraphs, split_bilingual_title
from .base_spider import BaseSpider, ProjectData
from .registry import register_spider


class GoooodSpider(BaseSpider):
    """Gooood 网站爬虫

    分类目录树来源：https://www.gooood.cn/filter/type/all/...（复合检索）
    API 来源：https://dashboard.gooood.cn/api/wp/v2/type（2026-02-25 扫描确认）
    """

    SOURCE_NAME: str = "gooood"
    DISPLAY_NAME: str = "谷德设计网"
    SCHEDULE = {
        "enabled": False,  # 待开放；改 True 即接入调度
        "priority": 2,  # 并行批次优先级（1 最高）
        "day_of_week": "tue",
        "hour": 2,
        "minute": 0,  # 基准分钟，调度器叠加 [0,30) 随机偏移
    }

    # ========================================================================
    # 空间类型分类目录树（基准数据，2026-02-26 dashboard API 扫描，共 50 类顶级空间类型）
    # 数据来源：https://dashboard.gooood.cn/api/wp/v2/type（296条含子类，116条顶级）
    # 仅保留"空间/项目类型"维度，已排除：
    #   - 非空间类：工业设计、产品设计、摄影、绘画、插画、平面设计、服装设计、品牌等
    #   - 极少文章类（< 96篇）已合并进父类中，不单独爬取
    # URL 格式：/filter/type/{slug}/country/all/material/all/office/all
    #
    # 爬取策略：checkpoint 机制（data/crawl_checkpoints.json）
    #   - 首次运行：无 checkpoint，从第1页爬到最后，自动覆盖全量历史
    #   - 后续运行：遇到上次第1页第1条 URL 时停止翻页，只取新增内容
    #   无需区分"全量"和"增量"模式
    # ========================================================================
    CATEGORIES = {
        # ── 核心建筑类型（≥ 1000 篇）──────────────────────────────────────────
        "商业建筑": "https://www.gooood.cn/filter/type/commercial-architecture/country/all/material/all/office/all",
        "休闲娱乐": "https://www.gooood.cn/filter/type/hospitality/country/all/material/all/office/all",
        "住宅建筑": "https://www.gooood.cn/filter/type/residential-architecture/country/all/material/all/office/all",
        "文化建筑": "https://www.gooood.cn/filter/type/culture-architecture/country/all/material/all/office/all",
        "公共空间": "https://www.gooood.cn/filter/type/public-space/country/all/material/all/office/all",
        "教育建筑": "https://www.gooood.cn/filter/type/educational-architecture/country/all/material/all/office/all",
        "装置": "https://www.gooood.cn/filter/type/installation/country/all/material/all/office/all",
        # ── 重要空间类型（500–999 篇）────────────────────────────────────────
        "咖啡厅": "https://www.gooood.cn/filter/type/cafe/country/all/material/all/office/all",
        "公园": "https://www.gooood.cn/filter/type/park/country/all/material/all/office/all",
        "公共职能建筑": "https://www.gooood.cn/filter/type/pubilc-architecture/country/all/material/all/office/all",
        "交通建筑": "https://www.gooood.cn/filter/type/transportation/country/all/material/all/office/all",
        "庭院": "https://www.gooood.cn/filter/type/garden/country/all/material/all/office/all",
        "绿色建筑": "https://www.gooood.cn/filter/type/green-architecture/country/all/material/all/office/all",
        "体育建筑": "https://www.gooood.cn/filter/type/sports-architecture/country/all/material/all/office/all",
        "综合体": "https://www.gooood.cn/filter/type/complex/country/all/material/all/office/all",
        # ── 补充空间类型（200–499 篇）────────────────────────────────────────
        "塔楼": "https://www.gooood.cn/filter/type/tower/country/all/material/all/office/all",
        "酒吧": "https://www.gooood.cn/filter/type/bar/country/all/material/all/office/all",
        "工作室": "https://www.gooood.cn/filter/type/studio/country/all/material/all/office/all",
        "民宿": "https://www.gooood.cn/filter/type/guest-house/country/all/material/all/office/all",
        "广场": "https://www.gooood.cn/filter/type/plaza/country/all/material/all/office/all",
        "工业建筑": "https://www.gooood.cn/filter/type/industrial-architecture/country/all/material/all/office/all",
        "中国乡建": "https://www.gooood.cn/filter/type/rural-reconstruction-of-china/country/all/material/all/office/all",
        "高层建筑": "https://www.gooood.cn/filter/type/high-rise/country/all/material/all/office/all",
        "工业建筑改造": "https://www.gooood.cn/filter/type/industrial-architecture-renovation/country/all/material/all/office/all",
        "宗教建筑": "https://www.gooood.cn/filter/type/religious-architecture/country/all/material/all/office/all",
        "园区": "https://www.gooood.cn/filter/type/campus/country/all/material/all/office/all",
        "水池": "https://www.gooood.cn/filter/type/pool/country/all/material/all/office/all",
        "屋顶花园": "https://www.gooood.cn/filter/type/roof-garden/country/all/material/all/office/all",
        "医疗建筑": "https://www.gooood.cn/filter/type/healthcare-architecture/country/all/material/all/office/all",
        "社区中心": "https://www.gooood.cn/filter/type/community-center/country/all/material/all/office/all",
        "滨海建筑": "https://www.gooood.cn/filter/type/coastal-architecture/country/all/material/all/office/all",
        "区域规划": "https://www.gooood.cn/filter/type/master-plan/country/all/material/all/office/all",
        # ── 细分空间类型（96–199 篇）─────────────────────────────────────────
        "甜品店": "https://www.gooood.cn/filter/type/dessert-shop/country/all/material/all/office/all",
        "热带建筑": "https://www.gooood.cn/filter/type/tropical-architecture/country/all/material/all/office/all",
        "中庭": "https://www.gooood.cn/filter/type/atrium/country/all/material/all/office/all",
        "城市更新": "https://www.gooood.cn/filter/type/revitalization/country/all/material/all/office/all",
        "摩天楼": "https://www.gooood.cn/filter/type/skyscraper/country/all/material/all/office/all",
        "茶室": "https://www.gooood.cn/filter/type/tea-house/country/all/material/all/office/all",
        "书店": "https://www.gooood.cn/filter/type/bookstore/country/all/material/all/office/all",
        "与动物有关的项目": "https://www.gooood.cn/filter/type/animal-related-projects/country/all/material/all/office/all",
        "楼梯": "https://www.gooood.cn/filter/type/staircase/country/all/material/all/office/all",
        "步道": "https://www.gooood.cn/filter/type/path/country/all/material/all/office/all",
        "游乐场": "https://www.gooood.cn/filter/type/playground/country/all/material/all/office/all",
        "艺术中心": "https://www.gooood.cn/filter/type/arts-center/country/all/material/all/office/all",
        "生态修复": "https://www.gooood.cn/filter/type/restoration/country/all/material/all/office/all",
        "古建保护与开发": "https://www.gooood.cn/filter/type/conservation-of-historic-buildings/country/all/material/all/office/all",
        "灯光设计": "https://www.gooood.cn/filter/type/lighting-design/country/all/material/all/office/all",
        "平台": "https://www.gooood.cn/filter/type/platform/country/all/material/all/office/all",
        "公厕": "https://www.gooood.cn/filter/type/public-toilet/country/all/material/all/office/all",
        "Spa": "https://www.gooood.cn/filter/type/spa/country/all/material/all/office/all",
    }

    # 网站各分类文章数（2026-02-26 dashboard API 扫描确认，用于进度展示）
    CATEGORY_TOTALS: Dict[str, int] = {
        "商业建筑": 6169,
        "休闲娱乐": 5666,
        "住宅建筑": 5482,
        "文化建筑": 3545,
        "公共空间": 2140,
        "教育建筑": 1681,
        "装置": 1383,
        "咖啡厅": 988,
        "公园": 936,
        "公共职能建筑": 755,
        "交通建筑": 604,
        "庭院": 577,
        "绿色建筑": 558,
        "体育建筑": 530,
        "综合体": 527,
        "塔楼": 485,
        "酒吧": 479,
        "工作室": 413,
        "民宿": 408,
        "广场": 403,
        "工业建筑": 398,
        "中国乡建": 395,
        "高层建筑": 389,
        "工业建筑改造": 368,
        "宗教建筑": 348,
        "园区": 318,
        "水池": 285,
        "屋顶花园": 272,
        "医疗建筑": 269,
        "社区中心": 265,
        "滨海建筑": 263,
        "区域规划": 263,
        "甜品店": 222,
        "热带建筑": 210,
        "中庭": 204,
        "城市更新": 203,
        "摩天楼": 186,
        "茶室": 182,
        "书店": 171,
        "与动物有关的项目": 165,
        "楼梯": 145,
        "步道": 144,
        "游乐场": 136,
        "艺术中心": 130,
        "生态修复": 118,
        "古建保护与开发": 111,
        "灯光设计": 108,
        "平台": 105,
        "公厕": 97,
        "Spa": 96,
    }

    def __init__(self, use_playwright: bool = True):
        super().__init__()
        self.source = "gooood"
        self.base_url = "https://www.gooood.cn"
        self.use_playwright = use_playwright
        # 最近一次列表页解析到的最大页码（page 1 解析后设置）
        self._last_max_page: int | None = None

    # ========================================================================
    # BaseSpider 抽象方法实现
    # ========================================================================

    def get_name(self) -> str:
        return "gooood"

    def get_base_url(self) -> str:
        return "https://www.gooood.cn"

    def parse_project_page(self, url: str) -> ProjectData | None:
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
        stop_url: str | None = None,
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
        first_url: str | None = None  # 本次第1页第1条，用于更新 checkpoint

        for page in range(1, max_pages + 1):
            project_list = self.fetch_project_list(page=page, type_slug=type_slug)
            if not project_list:
                logger.info(f"第{page}页无项目，停止翻页（新增 {len(new_urls)} 条）")
                break

            page_urls = [item["url"] for item in project_list]

            # 记录本次第1页第1条作为新 checkpoint
            if page == 1 and page_urls:
                first_url = page_urls[0]

            # checkpoint 检查：遇到上次基准 URL 即停止
            if stop_url and stop_url in page_urls:
                idx = page_urls.index(stop_url)
                new_urls.extend(page_urls[:idx])
                logger.info(f"第{page}页遇到 checkpoint，收集前{idx}条，停止翻页（新增 {len(new_urls)} 条）")
                break

            logger.debug(f"第{page}页: {len(page_urls)} 条")
            new_urls.extend(page_urls)

        # 将本次第1条 URL 附在返回值末尾供 spider_manager 更新 checkpoint
        # 格式："__checkpoint__:<url>" ["|total:<N>"] —— total 即该分类网站估算总量
        if first_url:
            sentinel = f"__checkpoint__:{first_url}"
            if self._last_max_page and self._last_max_page > 1 and len(new_urls) > 0:
                # 用实际每页条数动态估算总量（gooood 实际返回约20条/页，
                # 不再硬编码12，用本次已采集条数除以已爬页数得到平均值）
                pages_used = min(page, self._last_max_page)
                items_per_page = max(12, round(len(new_urls) / pages_used)) if pages_used > 0 else 20
                est_total = self._last_max_page * items_per_page
                sentinel += f"|total:{est_total}"
                logger.info(f"  分类网站估算总量: {self._last_max_page} 页 × {items_per_page} = {est_total} 条")
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
            logger.warning("category 参数已废弃，请使用 type_slug")

        # 构建正确的 filter URL
        if type_slug and type_slug != "all":
            base_filter = f"{self.base_url}/filter/type/{type_slug}/country/all/material/all/office/all"
        else:
            base_filter = f"{self.base_url}/filter/type/all/country/all/material/all/office/all"

        # 统一加结尾斜杠，避免第1页不带斜杠触发不必要的重定向
        if page == 1:
            url = base_filter + "/"
        else:
            url = f"{base_filter}/page/{page}/"

        logger.debug(f"获取项目列表: {url}")

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

            # 若首次获取为空（可能是加载慢）：等待后重试一次
            if not projects and html:
                logger.warning(f"列表页解析为空，10s 后重试: {url}")
                time.sleep(random.uniform(8, 15))
                html = self.run_in_browser_thread(self._fetch_list_pw_impl, url)
                projects = self._parse_list_html(html)

            self.rate_limiter.report_success()
            return projects
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            self.rate_limiter.report_block()
            return []

    def _fetch_list_pw_impl(self, url: str) -> str:
        """在浏览器线程中获取列表页HTML（domcontentloaded + 显式元素等待，
        避免 networkidle 在含分析脚本的 SPA 上长时间挂起）"""
        page = self.get_page()
        try:
            # domcontentloaded 比 networkidle 快且稳定；动态内容由下方 wait_for_selector 兜底
            response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            if response and response.status in (403, 429, 503):
                logger.warning(f"列表页返回 HTTP {response.status}，触发反爬保护: {url}")
                return ""

            # filter 页面是 Vue 渲染，等待文章卡片出现
            selectors = [
                "div.post-box",  # 居常用分类列表卡片（2026-02 确认）
                "h2.entry-title",  # 备用
                ".post-wrapper",  # 备用
                "article",  # 通用备选
            ]
            loaded = False
            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=12000)  # 比以前的8s更宽松
                    loaded = True
                    break
                except PlaywrightTimeout:
                    continue

            if not loaded:
                logger.warning(f"Vue 元素等待超时，回退到额外等待: {url}")
                page.wait_for_timeout(int(random.uniform(3000, 7000)))

            return page.content()
        finally:
            self.close_page(page)

    def _parse_list_html(self, html: str) -> List[Dict[str, str]]:
        """解析列表页HTML，提取项目卡片

        结构（2026-02）：div.post-box > h2.entry-title > a.cover-link
        """
        soup = BeautifulSoup(html, "html.parser")
        projects = []

        for box in soup.find_all("div", class_="post-box"):
            try:
                # a.cover-link 在 h2.entry-title 内，含标题文字
                title_h2 = box.find("h2", class_="entry-title")
                if not title_h2:
                    continue
                link_elem = title_h2.find("a", class_="cover-link", href=True)
                if not link_elem:
                    continue

                href = link_elem.get("href", "")
                if not href:
                    continue

                if href.startswith("http"):
                    project_url = href
                else:
                    project_url = f"{self.base_url}{href}" if href.startswith("/") else f"{self.base_url}/{href}"

                title = link_elem.get_text(strip=True)
                if not title:
                    continue

                projects.append(
                    {
                        "url": project_url,
                        "title": title,
                        "preview_image": "",  # 不爬取预览图，节省带宽
                    }
                )
            except Exception as e:
                logger.warning(f"解析项目卡片失败: {e}")
                continue

        logger.debug(f"找到 {len(projects)} 个项目")

        # 解析分页最大页码（.paginations 里最大的数字链接）
        try:
            max_p = 1
            for a in soup.select(".paginations a[href]"):
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

    def fetch_project_detail(self, url: str, _retry: int = 0) -> ProjectData | None:
        """获取项目详情（线程安全，失败自动重试最多2次）"""
        MAX_DETAIL_RETRIES = 2
        logger.debug(f"爬取项目详情: {url}" + (f" (重试 {_retry}/{MAX_DETAIL_RETRIES})" if _retry else ""))

        try:
            self.rate_limiter.wait()

            if self.use_playwright:
                html = self.run_in_browser_thread(self._fetch_detail_pw_impl, url)
                if not html:
                    self.rate_limiter.report_block()
                    if _retry < MAX_DETAIL_RETRIES:
                        logger.warning(f"页面获取为空，{5 + _retry * 5}s 后重试: {url}")
                        time.sleep(5 + _retry * 5)
                        return self.fetch_project_detail(url, _retry=_retry + 1)
                    return None
            else:
                response = requests.get(url, headers=self._get_headers(), timeout=30)
                response.raise_for_status()
                html = response.text

            soup = BeautifulSoup(html, "html.parser")

            source_id = url.rstrip("/").split("/")[-1]

            title_elem = soup.find("h1", class_="entry-title")
            title = title_elem.get_text(strip=True) if title_elem else "Untitled"

            # 若标题为 Untitled 且还有重试机会，说明页面未完全渲染
            if title == "Untitled" and _retry < MAX_DETAIL_RETRIES:
                logger.warning(f"标题未渲染，{5 + _retry * 5}s 后重试: {url}")
                time.sleep(5 + _retry * 5)
                return self.fetch_project_detail(url, _retry=_retry + 1)

            description = self._extract_description(soup)

            # 若描述过短且还有重试机会，说明 Vue 正文段落未渲染完毕
            if len(description or "") < 50 and _retry < MAX_DETAIL_RETRIES:
                logger.warning(
                    f"描述内容过短({len(description or '')}字符) retry={_retry}/{MAX_DETAIL_RETRIES}，"
                    f"{8 + _retry * 5}s 后重试: {url}"
                )
                time.sleep(8 + _retry * 5)
                return self.fetch_project_detail(url, _retry=_retry + 1)

            architects = self._extract_architects(soup)
            location = self._extract_location(soup)
            year = self._extract_year(soup, description)
            area_sqm = self._extract_area(soup, description)
            images = []  # 不爬取项目图片（节省带宽与存储）
            categories = self._extract_categories(soup) or []
            primary_category = categories[0] if categories else None
            tags = self._extract_tags(soup) or []

            # ── gooood 特有字段───────────────────────────────────
            extra_fields = self._extract_extra_fields(soup)

            # ── 发布日期 ─────────────────────────────────────────────────
            publish_date = self._extract_publish_date(soup)

            # ── 双语内容处理 ────────────────────────────────────────────
            # gooood 正文：中英双语交替段落
            desc_parts = split_bilingual_paragraphs(description or "")
            logger.debug(
                f"[双语拆分] 原始={len(description or '')}字符, "
                f"zh={len(desc_parts.get('zh') or '')}字符, "
                f"en={len(desc_parts.get('en') or '')}字符"
            )
            # gooood 标题：通常"中文 / English, City / Firm"
            title_parts = split_bilingual_title(title)

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
                publish_date=publish_date,
                # 双语字段
                lang="bilingual",
                title_zh=title_parts["zh"] or title,
                title_en=title_parts["en"] or None,
                description_zh=desc_parts["zh"] or None,
                description_en=desc_parts["en"] or None,
                # 扩展字段
                extra_fields=extra_fields if extra_fields else None,
            )

            logger.debug(f"项目爬取成功: {title} (描述 {len(description)}字符)")
            self.rate_limiter.report_success()
            return project

        except Exception as e:
            logger.error(f"爬取项目详情失败: {e}")
            import traceback

            traceback.print_exc()
            self.rate_limiter.report_block()
            return None

    def _fetch_detail_pw_impl(self, url: str) -> str:
        """在浏览器线程中获取详情页HTML（稳定优先，确保内容渲染完成）"""
        page = self.get_page()
        try:
            # 详情页用 networkidle 确保 Vue 异步内容加载完成
            page.goto(url, wait_until="networkidle", timeout=45000)

            # 第一步：等待正文容器出现
            _detail_selectors = [
                "div.entry-content",  # 正文容器（99% 详情页有）
                "h1.entry-title",  # 标题（主标题）
                "article",  # 通用后备
            ]
            loaded = False
            for sel in _detail_selectors:
                try:
                    page.wait_for_selector(sel, timeout=10000)
                    loaded = True
                    break
                except PlaywrightTimeout:
                    continue

            if not loaded:
                logger.warning(f"内容选择器等待超时，额外等待 5s: {url}")
                page.wait_for_timeout(5000)

            # 第二步：等待段落内容实际渲染（gooood 是 Vue SPA，容器先出现，段落异步填充）
            try:
                page.wait_for_selector("div.entry-content p", timeout=12000)
            except PlaywrightTimeout:
                logger.warning(f"段落内容等待超时，额外等待 5s: {url}")
                page.wait_for_timeout(5000)

            # 第三步：确保标题也已渲染
            try:
                page.wait_for_selector("h1.entry-title", timeout=5000)
            except PlaywrightTimeout:
                pass  # 标题超时不阻塞，后续会用 Untitled 兜底

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
        content_div = soup.find("div", class_="entry-content")
        if not content_div:
            return self._extract_description_fallback(soup)
        paragraphs = []
        for p in content_div.find_all("p"):
            # 仅跳过 <figcaption> 内的 <p>（图注），不跳过 <figure> 内的正文段落
            if p.find_parent("figcaption"):
                continue
            text = p.get_text(strip=True)
            if not text or len(text) <= 8:
                continue
            # 过滤已知干扰文本
            if text in ["收藏本文", "Collect this article"]:
                continue
            # 过滤图片说明行（▼ 开头的短注释）
            if text.startswith("▼") and len(text) < 80:
                continue
            paragraphs.append(text)

        # DIAG: 段落过滤统计
        _all_p = content_div.find_all("p")
        _figcaption_skipped = sum(1 for p in _all_p if p.find_parent("figcaption"))
        _short_skipped = sum(
            1
            for p in _all_p
            if not p.find_parent("figcaption") and (not p.get_text(strip=True) or len(p.get_text(strip=True)) <= 8)
        )
        _noise_skipped = sum(1 for p in _all_p if p.get_text(strip=True) in ["收藏本文", "Collect this article"])
        _arrow_skipped = sum(
            1 for p in _all_p if p.get_text(strip=True).startswith("▼") and len(p.get_text(strip=True)) < 80
        )
        logger.debug(
            f"[描述提取] 原始<p>={len(_all_p)}, "
            f"figcaption跳过={_figcaption_skipped}, 过短跳过={_short_skipped}, "
            f"噪声跳过={_noise_skipped}, ▼跳过={_arrow_skipped}, 保留={len(paragraphs)}"
        )

        result = "\n\n".join(paragraphs)
        # 如果提取结果仍然太短，尝试 fallback
        if len(result) < 50:
            logger.debug(f"[描述提取] 主提取过短({len(result)}字符)，尝试fallback")
            fallback = self._extract_description_fallback(soup)
            logger.debug(f"[描述提取] fallback={len(fallback)}字符 vs 主={len(result)}字符")
            if len(fallback) > len(result):
                logger.debug("[描述提取] 采用fallback")
                return fallback
        return result

    def _extract_description_fallback(self, soup: BeautifulSoup) -> str:
        """从 meta 标签或 entry-content 全文提取描述（兜底）"""
        # 尝试 1：<meta name="description">
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            desc = meta["content"].strip()
            logger.debug(f"[fallback] meta description={len(desc)}字符")
            if len(desc) >= 50:
                logger.debug("[fallback] 采用meta description")
                return desc
        else:
            logger.debug("[fallback] 无meta description")
        # 尝试 2：entry-content 的全部文本（去除脚本/样式）
        content_div = soup.find("div", class_="entry-content")
        if content_div:
            for tag in content_div.find_all(["script", "style", "nav"]):
                tag.decompose()
            text = content_div.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 8]
            logger.debug(f"[fallback] entry-content全文行数={len(lines)}")
            return "\n\n".join(lines[:30])
        logger.warning("[fallback] 无entry-content div，返回空")
        return ""

    def _extract_architects(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        提取建筑师/设计方信息。

        支持的字段标签（中英文）：
          主创建筑师、主持建筑师、设计师、建筑师、设计单位、设计团队、主创设计师、
          设计事务所、设计方、Architect、Architects、Design、Design Team、
          Lead Architect、Principal Architect

        策略：
        1. 扫描 entry-content 中所有 <p>，寻找 "标签：值" 结构的行
        2. 每行可能包含多个设计方，用 /、、、; 分隔
        3. 去重、剔除过长或明显非名称的字符串
        """
        LABEL_PATTERN = re.compile(
            r"^[\s\u3000]*"
            r"(?:主创建筑师|主持建筑师|主创设计师|设计师|建筑师|设计单位|设计团队|设计事务所|设计方|"
            r"设计|Architects?|Design(?:\s+Team)?|Lead\s+Architect|Principal\s+Architect)"
            r"[\s\u3000]*[:：]\s*",
            re.IGNORECASE,
        )
        SPLIT_PATTERN = re.compile(r"[/／;；、,，\n]+")
        NOISE_KEYWORDS = {"http", "www", ".com", ".cn", "版权", "copyright", "©"}

        seen: set = set()
        architects: List[Dict[str, str]] = []

        content_div = soup.find("div", class_="entry-content")
        if not content_div:
            return architects

        for p in content_div.find_all("p"):
            text = p.get_text(separator="\n", strip=True)
            for line in text.splitlines():
                line = line.strip()
                if not LABEL_PATTERN.match(line):
                    continue
                # 去掉标签部分，取值
                value = LABEL_PATTERN.sub("", line).strip()
                if not value:
                    continue
                # 按分隔符拆分多个名称
                for raw_name in SPLIT_PATTERN.split(value):
                    name = raw_name.strip()
                    # 过滤：空/过长/含噪声关键词
                    if not name or len(name) > 80:
                        continue
                    if any(kw in name.lower() for kw in NOISE_KEYWORDS):
                        continue
                    if name not in seen:
                        seen.add(name)
                        architects.append({"name": name})

        return architects

    def _extract_location(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        提取项目地点信息。

        支持的字段标签（中英文）：
          项目地点、地点、项目位置、位置、所在地、地址、项目城市、
          Location、Project Location、Address、Country

        策略：
        1. 扫描 entry-content 中所有 <p> 的每一行，寻找地点标签行
        2. 将地点字符串按 逗号/中文逗号/斜杠 分割，最后一段为国家，第一段为城市
        3. Fallback：检查 JSON-LD 结构化数据中的 contentLocation 字段
        """
        LABEL_PATTERN = re.compile(
            r"^[\s\u3000]*"
            r"(?:项目地点|项目位置|项目城市|地点|位置|所在地|地址|"
            r"Location|Project\s+Location|Address|Country)"
            r"[\s\u3000]*[:：]\s*",
            re.IGNORECASE,
        )
        SPLIT_PATTERN = re.compile(r"[,，/／|]")

        content_div = soup.find("div", class_="entry-content")
        if content_div:
            for p in content_div.find_all("p"):
                text = p.get_text(separator="\n", strip=True)
                for line in text.splitlines():
                    line = line.strip()
                    if not LABEL_PATTERN.match(line):
                        continue
                    value = LABEL_PATTERN.sub("", line).strip()
                    if not value:
                        continue
                    parts = [s.strip() for s in SPLIT_PATTERN.split(value) if s.strip()]
                    if len(parts) >= 2:
                        return {"city": parts[0], "country": parts[-1]}
                    elif parts:
                        return {"city": parts[0]}

        # Fallback：JSON-LD 结构化数据
        import json

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.get_text())
                loc = data.get("contentLocation") or data.get("locationCreated") or {}
                if isinstance(loc, dict):
                    address = loc.get("address", {})
                    city = address.get("addressLocality") or loc.get("name", "")
                    country = address.get("addressCountry", "")
                    if city:
                        result: Dict[str, str] = {"city": city}
                        if country:
                            result["country"] = country
                        return result
            except Exception:
                pass

        return {}

    def _extract_year(self, soup: BeautifulSoup, description: str = "") -> int | None:
        """
        提取项目竣工/建成年份。

        支持的字段标签（中英文）：
          竣工时间、竣工年份、建成时间、建成年份、完工时间、完成时间、
          项目年份、建设年份、设计时间、竣工年、建成年、
          Year、Completion Year、Completion Date、Project Year

        策略：
        1. 优先从明确的年份字段标签行提取（精确）
        2. 绝不从自由文本 description 提取（误报率极高）
        3. 年份合法范围：1950 ~ 当前年份 + 2
        """
        import datetime

        CURRENT_YEAR = datetime.date.today().year
        YEAR_MIN, YEAR_MAX = 1950, CURRENT_YEAR + 2

        LABEL_PATTERN = re.compile(
            r"^[\s\u3000]*"
            r"(?:竣工时间|竣工年份|竣工年|建成时间|建成年份|建成年|完工时间|完成时间|"
            r"项目年份|建设年份|建设时间|设计时间|"
            r"Year|Completion\s+(?:Year|Date)|Project\s+Year|Built|Completed)"
            r"[\s\u3000]*[:：\-]\s*",
            re.IGNORECASE,
        )
        YEAR_RE = re.compile(r"(?<!\d)(20\d{2}|19[5-9]\d)(?!\d)")

        content_div = soup.find("div", class_="entry-content")
        if content_div:
            for p in content_div.find_all("p"):
                text = p.get_text(separator="\n", strip=True)
                for line in text.splitlines():
                    line = line.strip()
                    if not LABEL_PATTERN.match(line):
                        continue
                    value = LABEL_PATTERN.sub("", line).strip()
                    m = YEAR_RE.search(value)
                    if m:
                        year = int(m.group(1))
                        if YEAR_MIN <= year <= YEAR_MAX:
                            return year

        return None

    def _extract_area(self, soup: BeautifulSoup, description: str) -> float | None:
        """
        提取项目面积（统一转换为 m²）。

        支持的字段标签（中英文）：
          建筑面积、用地面积、总面积、基地面积、占地面积、建设面积、面积、
          Floor Area、Site Area、Total Area、Area、GFA

        支持的面积单位及换算：
          m²、㎡、sqm、sq.m、square meters → × 1
          万平方米                          → × 10,000
          ha、公顷                          → × 10,000
          亩                               → × 666.67

        合法范围：10 ~ 10,000,000 m²
        """
        LABEL_PATTERN = re.compile(
            r"^[\s\u3000]*"
            r"(?:建筑面积|用地面积|总面积|基地面积|占地面积|建设面积|面积|"
            r"Floor\s+Area|Site\s+Area|Total\s+Area|GFA|Area)"
            r"[\s\u3000]*[:：]\s*",
            re.IGNORECASE,
        )
        # 匹配数字 + 单位
        AREA_RE = re.compile(
            r"(\d[\d,\s]*(?:\.\d+)?)\s*" r"(万平方米|平方米|㎡|m²|sqm|sq\.m|square\s*meters?|公顷|ha|亩)",
            re.IGNORECASE,
        )
        AREA_MIN, AREA_MAX = 10.0, 10_000_000.0

        UNIT_FACTOR = {
            "万平方米": 10_000,
            "平方米": 1,
            "㎡": 1,
            "m²": 1,
            "sqm": 1,
            "sq.m": 1,
            "square meter": 1,
            "square meters": 1,
            "公顷": 10_000,
            "ha": 10_000,
            "亩": 666.67,
        }

        def _parse_match(m: re.Match) -> float | None:
            raw_num = m.group(1).replace(",", "").replace(" ", "")
            unit_raw = m.group(2).strip().lower()
            try:
                num = float(raw_num)
            except ValueError:
                return None
            # 查找换算系数
            factor = 1.0
            for key, val in UNIT_FACTOR.items():
                if unit_raw == key.lower() or unit_raw.startswith(key.lower()[:4]):
                    factor = val
                    break
            result = num * factor
            if AREA_MIN <= result <= AREA_MAX:
                return round(result, 2)
            return None

        # 1. 优先从带有面积标签的行提取
        content_div = soup.find("div", class_="entry-content")
        if content_div:
            for p in content_div.find_all("p"):
                text = p.get_text(separator="\n", strip=True)
                for line in text.splitlines():
                    line = line.strip()
                    if not LABEL_PATTERN.match(line):
                        continue
                    m = AREA_RE.search(line)
                    if m:
                        val = _parse_match(m)
                        if val is not None:
                            return val

        # 2. Fallback：从 description 中匹配（必须有单位）
        for m in AREA_RE.finditer(description):
            val = _parse_match(m)
            if val is not None:
                return val

        return None

    def _extract_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        # 不爬取图片及说明文字（脱离图片，这些备注说明失去意义）
        return []

    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        categories = []
        breadcrumb = soup.find("nav", class_="breadcrumb")
        if breadcrumb:
            for link in breadcrumb.find_all("a"):
                text = link.get_text(strip=True)
                if text and text not in ["Home", "首页", "Gooood"]:
                    categories.append(text)
        cat_links = soup.find_all("a", rel="category tag")
        for link in cat_links:
            text = link.get_text(strip=True)
            if text and text not in categories:
                categories.append(text)
        return categories

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        tags = []
        tag_links = soup.find_all("a", rel="tag")
        for link in tag_links:
            text = link.get_text(strip=True)
            if text:
                tags.append(text)
        return tags

    def _extract_extra_fields(self, soup: BeautifulSoup) -> Dict:
        """
        提取 gooood 特有的结构化字段（不属于标准 ProjectData 字段集的信息）。

        扫描 entry-content 中的 "标签：值" 行，识别以下字段：
          - owner         : 业主 / 建设方 / 客户 / 甲方 / Client / Owner
          - landscape_architect: 景观设计 / 景观 / Landscape
          - structural_engineer: 结构设计 / 结构工程师 / Structural
          - interior_designer  : 室内设计 / 室内 / Interior Design
          - lighting_designer  : 照明设计 / Lighting
        """
        FIELD_MAP = {
            r"业主|建设方|客户|甲方|委托方|Client|Owner": "owner",
            r"景观设计|景观|Landscape\s*(?:Architect(?:ure)?)?": "landscape_architect",
            r"结构设计|结构工程师?|Structural\s*(?:Engineer(?:ing)?)?": "structural_engineer",
            r"室内设计师?|室内|Interior\s*(?:Design(?:er)?)?": "interior_designer",
            r"照明设计|灯光设计|Lighting\s*(?:Design(?:er)?)?": "lighting_designer",
        }
        import re as _re

        LABEL_PATTERN = _re.compile(
            r"^[\s\u3000]*(" + "|".join(FIELD_MAP.keys()) + r")[\s\u3000]*[:：]\s*",
            _re.IGNORECASE,
        )
        SPLIT_PAT = _re.compile(r"[/／;；、,，\n]+")

        extra: Dict = {}
        content_div = soup.find("div", class_="entry-content")
        if not content_div:
            return extra

        for p in content_div.find_all("p"):
            text = p.get_text(separator="\n", strip=True)
            for line in text.splitlines():
                line = line.strip()
                m = LABEL_PATTERN.match(line)
                if not m:
                    continue
                label_raw = m.group(1)
                value = LABEL_PATTERN.sub("", line).strip()
                if not value:
                    continue
                # 判断归属字段
                for pattern, key in FIELD_MAP.items():
                    if _re.search(pattern, label_raw, _re.IGNORECASE):
                        parts = [s.strip() for s in SPLIT_PAT.split(value) if s.strip()]
                        extra[key] = parts if len(parts) > 1 else parts[0]
                        break
        return extra

    def _extract_publish_date(self, soup: BeautifulSoup) -> datetime | None:
        """
        从 gooood 详情页提取发布日期。

        尝试以下来源（优先级递减）：
        1. <meta property="article:published_time">
        2. <time datetime="...">
        3. <span class="entry-date"> 内文本
        """
        # 方式1：Open Graph meta
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            try:
                return datetime.fromisoformat(meta["content"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # 方式2：<time> 标签
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            try:
                return datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # 方式3：entry-date 文本解析
        import re as _re

        date_elem = soup.find("span", class_="entry-date") or soup.find("time")
        if date_elem:
            text = date_elem.get_text(strip=True)
            m = _re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", text)
            if m:
                try:
                    return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    pass

        return None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.gooood.cn/",
            "DNT": "1",
        }


# ── 注册到 SpiderRegistry ──────────────────────────────────────────────────
register_spider(GoooodSpider.SOURCE_NAME)(GoooodSpider)

__all__ = ["GoooodSpider"]
