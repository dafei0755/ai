"""
新爬虫接入模板 (_template_spider.py)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【极简接入模式】BaseSpider.universal_extract() 一键提取
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

新站接入只需 4 步：

 [1] 复制本文件，重命名类和 SOURCE_NAME
 [2] 填写 get_base_url() 和 get_categories()
 [3] 实现 crawl_category()（翻页逻辑，返回 URL 列表）
 [4] parse_project_page() 一行调用：
         return self.universal_extract(html, url)

 universal_extract() 内置 4 层提取策略，适配任意网站：
   1. og: / twitter: meta 标签 → title, description, publish_date
   2. JSON-LD / Schema.org     → architects, location, year, awards, …
   3. 通用 "标签：值" 段落扫描 → 已知字段→标准字段，未知字段→ extra_fields JSONB
   4. 基础 HTML 回退           → h1, time, article 等

 字段覆盖不了的内容自动进入 extra_fields（JSONB），无需修改数据结构。

 如果该网站有特殊结构，可覆盖部分方法而不是全部重写：
   - 覆盖 _extract_architects / _extract_location 等基类方法（可选）
   - 提取完额外字段后手动补进 project_data.extra_fields（可选）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
import random
import time
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from .base_spider import BaseSpider, ProjectData
from ..utils import get_rate_limiter
from ..utils.lang_utils import split_bilingual_paragraphs, split_bilingual_title
from .registry import register_spider


class TemplateSpider(BaseSpider):
    """
    新站接入模板爬虫（复制此文件后重命名类和 SOURCE_NAME）

    数据流设计：
      crawl_category()  →  fetch_project_detail()  →  ProjectData
          翻页              提取结构化字段                统一数据结构
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 必须填写的类属性（Step 2）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    SOURCE_NAME: str = "template"  # 唯一标识，全小写下划线
    DISPLAY_NAME: str = "模板站点"  # 供 UI / 日志显示

    SCHEDULE: Dict[str, Any] = {
        "enabled": False,  # ← 调试完成后改为 True
        "priority": 99,  # 并行批次优先级，越小越优先（1=高）
        "day_of_week": "fri",  # 调度星期（mon~sun）
        "hour": 3,  # UTC+8 小时
        "minute": 0,  # 基准分钟（调度器会叠加随机 [0,30)）
    }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 分类目录（Step 4）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    CATEGORIES: Dict[str, str] = {
        # TODO: 填写 {分类名称: 分类入口URL}
        # "住宅": "https://www.example.com/category/residential",
    }

    # ── 内部常量 ─────────────────────────────────────────────────

    # 等待列表页内容渲染的 CSS 选择器（Step 5）
    _LIST_SELECTOR = "TODO: article.item, .project-card"

    # 等待详情页内容渲染的 CSS 选择器（Step 6）
    _DETAIL_SELECTOR = "TODO: .project-content, article.post"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 初始化
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def __init__(self) -> None:
        super().__init__()
        self.rate_limiter = get_rate_limiter(self.SOURCE_NAME)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BaseSpider 抽象方法实现（Step 3 + 5 + 6）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_name(self) -> str:
        return self.SOURCE_NAME

    def get_base_url(self) -> str:
        return "https://www.example.com"  # TODO: 替换为目标网站根域

    def get_categories(self) -> Dict[str, str]:
        return self.CATEGORIES

    # ── 分类翻页（Step 5）────────────────────────────────────────

    def crawl_category(
        self,
        category_url: str,
        max_pages: int = 200,
        stop_url: Optional[str] = None,
    ) -> List[str]:
        """
        翻页爬取分类列表，返回项目 URL 列表。

        末尾附加 checkpoint 哨兵，供 SpiderManager 解析::

            ["url1", "url2", ..., "__checkpoint__:<first_url>"]

        stop_url 机制：
          - stop_url=None  → 全量爬取（首次运行）
          - stop_url=<url> → 遇到此 URL 时停止（增量爬取）
        """
        seen_urls: set = set()
        ordered_urls: List[str] = []
        first_url: Optional[str] = None

        for page_num in range(1, max_pages + 1):
            # TODO: 构造翻页 URL（不同站点格式不同）
            if page_num == 1:
                page_url = category_url.rstrip("/") + "/"
            else:
                page_url = f"{category_url.rstrip('/')}/page/{page_num}/"

            # robots.txt 合规检查
            if not self._is_allowed_by_robots(page_url):
                logger.warning(f"robots.txt 不允许: {page_url}")
                break

            self.rate_limiter.wait()

            html = self.run_in_browser_thread(self._fetch_list_pw_impl, page_url)
            if not html:
                self.rate_limiter.report_block()
                break

            urls: List[str] = self._parse_list_html(html)
            self.rate_limiter.report_success()

            if not urls:
                # 空页重试一次
                wait_s = random.uniform(8, 15)
                logger.info(f"  列表为空，等待 {wait_s:.1f}s 后重试 page={page_num}")
                time.sleep(wait_s)
                html2 = self.run_in_browser_thread(self._fetch_list_pw_impl, page_url)
                urls = self._parse_list_html(html2) if html2 else []
                if not urls:
                    break

            stop_hit = False
            for url in urls:
                if first_url is None:
                    first_url = url
                if url == stop_url:
                    stop_hit = True
                    break
                if url not in seen_urls:
                    seen_urls.add(url)
                    ordered_urls.append(url)

            if stop_hit:
                break

        if first_url:
            ordered_urls.append(f"__checkpoint__:{first_url}")

        logger.info(f"[{self.SOURCE_NAME}] 分类爬取完成，共 {len(ordered_urls)} 个 URL")
        return ordered_urls

    def parse_project_page(self, url: str) -> Optional[ProjectData]:
        """
        详情页解析入口（供 SpiderManager 调用）。

        ─── 极简模式（推荐，大多数网站直接可用）────────────────────────
        调用 BaseSpider.universal_extract() 自动完成：
          · og: meta → title / description
          · JSON-LD  → architects / location / year / awards
          · label:value 扫描 → 已知字段→标准字段，未知→ extra_fields
          · HTML 回退 → h1 / time / article

        ─── 精细模式（可选，网站结构特殊时覆盖）───────────────────────
        取消注释 fetch_project_detail()，在其中手动提取并补充
        project_data.extra_fields / primary_category 等字段。
        """
        logger.info(f"[{self.SOURCE_NAME}] 爬取详情: {url}")
        try:
            self.rate_limiter.wait()
            # _fetch_html_pw 是 BaseSpider 内置方法，无需重写
            html = self.run_in_browser_thread(self._fetch_html_pw, url)
            if not html:
                self.rate_limiter.report_block()
                return None
            project = self.universal_extract(html, url)
            if project:
                self.rate_limiter.report_success()
            return project
        except Exception as e:
            logger.error(f"  ✗ 详情爬取失败: {url} — {e}")
            self.rate_limiter.report_block()
            return None

    # ─── 精细模式示例（可选）────────────────────────────────────────
    # 如需补充 universal_extract 无法自动提取的字段，取消注释并实现：
    #
    # def fetch_project_detail(self, url: str) -> Optional[ProjectData]:
    #     html = self.run_in_browser_thread(self._fetch_html_pw, url)
    #     project = self.universal_extract(html, url)   # 先走通用提取
    #     if project:
    #         soup = BeautifulSoup(html, 'html.parser')
    #         # 补充该网站特有字段
    #         extra = project.extra_fields or {}
    #         programme_el = soup.select_one('.programme-type')
    #         if programme_el:
    #             extra['programme'] = programme_el.get_text(strip=True)
    #         project.extra_fields = extra
    #         project.primary_category = ...  # 从面包屑 / tag 提取
    #     return project

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Playwright 实现（在浏览器线程中执行）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _fetch_list_pw_impl(self, url: str) -> str:
        page = self.get_page()
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            if resp and resp.status in (403, 429, 503):
                logger.warning(f"  列表页 HTTP {resp.status}: {url}")
                return ""
            try:
                page.wait_for_selector(self._LIST_SELECTOR, timeout=12000)
            except PlaywrightTimeout:
                logger.warning("  列表页渲染超时，继续解析现有内容")
            page.wait_for_timeout(int(random.uniform(2500, 5000)))
            return page.content()
        except Exception as e:
            logger.error(f"  Playwright 列表页失败: {e}")
            return ""
        finally:
            self.close_page(page)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HTML 解析（Step 5 + 7）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _parse_list_html(self, html: str) -> List[str]:
        """从列表页 HTML 提取项目 URL 列表（Step 5）。"""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        urls: List[str] = []
        # TODO: 替换为实际的文章卡片选择器
        for article in soup.find_all("article"):
            a = article.find("a", href=True)
            if a:
                url = self.normalize_url(a["href"])
                if self._is_project_url(url):
                    urls.append(url)
        return urls

    # ── 5 大提取方法（Step 7）────────────────────────────────────
    # 参考 gooood_spider.py 中的完整实现，以下为极简骨架

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取标题（优先 og:title，其次 h1）。"""
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return og["content"].strip()
        h1 = soup.find("h1")
        return h1.get_text(strip=True) if h1 else "Untitled"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """
        提取正文描述。

        通用策略：
        - 找到主内容区容器（.entry-content / article / .post-body）
        - 提取所有 <p>，跳过 <figure> 内的图注段落
        - 过滤长度 < 20 字符的噪声行
        """
        # TODO: 替换 'div.entry-content' 为目标站点的内容容器选择器
        content_div = soup.find("div", class_="entry-content")
        if not content_div:
            content_div = soup.find("article")
        if not content_div:
            return ""

        paras: List[str] = []
        for p in content_div.find_all("p"):
            if p.find_parent("figure"):
                continue
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                paras.append(text)
        return "\n\n".join(paras)

    def _extract_architects(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        提取建筑师/设计方（通用正则结构）。

        复制 gooood_spider._extract_architects 的 LABEL_PATTERN 正则，
        根据目标站点增减中英文字段标签。
        """
        LABEL_PATTERN = re.compile(
            r"^[\s\u3000]*"
            r"(?:主创建筑师|主持建筑师|设计师|建筑师|设计单位|设计团队|设计方|"
            r"Architects?|Design(?:\s+Team)?|Lead\s+Architect)"
            r"[\s\u3000]*[:：]\s*",
            re.IGNORECASE,
        )
        SPLIT_PATTERN = re.compile(r"[/／;；、,，\n]+")
        NOISE_KW = {"http", "www", ".com", ".cn", "版权", "copyright", "©"}

        seen: set = set()
        architects: List[Dict[str, str]] = []

        # TODO: 替换 'div.entry-content' 为目标站点内容区选择器
        content_div = soup.find("div", class_="entry-content") or soup.find("article")
        if not content_div:
            return architects

        for p in content_div.find_all("p"):
            for line in p.get_text(separator="\n", strip=True).splitlines():
                line = line.strip()
                if not LABEL_PATTERN.match(line):
                    continue
                value = LABEL_PATTERN.sub("", line).strip()
                for raw in SPLIT_PATTERN.split(value):
                    name = raw.strip()
                    if not name or len(name) > 80:
                        continue
                    if any(kw in name.lower() for kw in NOISE_KW):
                        continue
                    if name not in seen:
                        seen.add(name)
                        architects.append({"name": name})
        return architects

    def _extract_location(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        提取项目地点（通用正则结构）。

        参考 gooood_spider._extract_location。
        """
        LABEL_PATTERN = re.compile(
            r"^[\s\u3000]*" r"(?:项目地点|项目位置|地点|位置|所在地|地址|Location|Address)" r"[\s\u3000]*[:：]\s*",
            re.IGNORECASE,
        )
        SPLIT_PATTERN = re.compile(r"[,，/／|]")

        # TODO: 替换为目标站点的内容区选择器
        content_div = soup.find("div", class_="entry-content") or soup.find("article")
        if content_div:
            for p in content_div.find_all("p"):
                for line in p.get_text(separator="\n", strip=True).splitlines():
                    line = line.strip()
                    if not LABEL_PATTERN.match(line):
                        continue
                    value = LABEL_PATTERN.sub("", line).strip()
                    parts = [s.strip() for s in SPLIT_PATTERN.split(value) if s.strip()]
                    if len(parts) >= 2:
                        return {"city": parts[0], "country": parts[-1]}
                    elif parts:
                        return {"city": parts[0]}
        return {}

    def _extract_year(self, soup: BeautifulSoup) -> Optional[int]:
        """
        提取竣工/建成年份（仅从带关键词的字段行提取，不扫描自由文本）。

        参考 gooood_spider._extract_year。
        """
        import datetime

        CURRENT_YEAR = datetime.date.today().year
        LABEL_PATTERN = re.compile(
            r"^[\s\u3000]*"
            r"(?:竣工时间|竣工年份|建成时间|建成年份|完成时间|项目年份|"
            r"Year|Completion\s+(?:Year|Date)|Built)"
            r"[\s\u3000]*[:：\-]\s*",
            re.IGNORECASE,
        )
        YEAR_RE = re.compile(r"(?<!\d)(20\d{2}|19[5-9]\d)(?!\d)")

        content_div = soup.find("div", class_="entry-content") or soup.find("article")
        if content_div:
            for p in content_div.find_all("p"):
                for line in p.get_text(separator="\n", strip=True).splitlines():
                    line = line.strip()
                    if not LABEL_PATTERN.match(line):
                        continue
                    m = YEAR_RE.search(LABEL_PATTERN.sub("", line))
                    if m:
                        year = int(m.group(1))
                        if 1950 <= year <= CURRENT_YEAR + 2:
                            return year
        return None

    def _extract_area(self, soup: BeautifulSoup, description: str) -> Optional[float]:
        """
        提取面积并统一转换为 m²。

        参考 gooood_spider._extract_area（支持 万平方米/ha/公顷/亩）。
        """
        LABEL_PATTERN = re.compile(
            r"^[\s\u3000]*" r"(?:建筑面积|用地面积|总面积|基地面积|面积|Floor\s+Area|Site\s+Area|Area|GFA)" r"[\s\u3000]*[:：]\s*",
            re.IGNORECASE,
        )
        AREA_RE = re.compile(
            r"(\d[\d,\s]*(?:\.\d+)?)\s*" r"(万平方米|平方米|㎡|m²|sqm|sq\.m|square\s*meters?|公顷|ha|亩)",
            re.IGNORECASE,
        )
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

        def _parse(m: re.Match) -> Optional[float]:
            try:
                num = float(m.group(1).replace(",", "").replace(" ", ""))
            except ValueError:
                return None
            unit = m.group(2).strip().lower()
            factor = next((v for k, v in UNIT_FACTOR.items() if unit.startswith(k.lower()[:4])), 1.0)
            val = num * factor
            return round(val, 2) if 10 <= val <= 10_000_000 else None

        content_div = soup.find("div", class_="entry-content") or soup.find("article")
        if content_div:
            for p in content_div.find_all("p"):
                for line in p.get_text(separator="\n", strip=True).splitlines():
                    if LABEL_PATTERN.match(line):
                        m = AREA_RE.search(line)
                        if m:
                            val = _parse(m)
                            if val is not None:
                                return val

        for m in AREA_RE.finditer(description):
            val = _parse(m)
            if val is not None:
                return val
        return None

    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        """从面包屑或分类标签提取分类列表（Step 7，根据站点结构调整）。"""
        categories: List[str] = []
        # TODO: 替换为目标站点的面包屑/分类选择器
        breadcrumb = soup.find("nav", class_="breadcrumb")
        if breadcrumb:
            for a in breadcrumb.find_all("a"):
                text = a.get_text(strip=True)
                if text and text not in {"Home", "首页"}:
                    categories.append(text)
        return categories

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """提取标签（Step 7，根据站点结构调整）。"""
        # TODO: 替换为目标站点的标签选择器
        tags: List[str] = []
        for a in soup.find_all("a", rel="tag"):
            text = a.get_text(strip=True)
            if text:
                tags.append(text)
        return tags[:30]  # 最多 30 个标签


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 9：注册到 SpiderRegistry（ENABLED=False 时不会被调度）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 注意：模板爬虫默认不注册（SOURCE_NAME="template" 已在 SCHEDULE.enabled=False）
# 实际使用时取消注释：
# register_spider(TemplateSpider.SOURCE_NAME)(TemplateSpider)

__all__ = ["TemplateSpider"]
