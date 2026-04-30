"""
ArchDaily 中文站爬虫（archdaily.cn）

继承自 ArchdailySpider，覆盖中文站专有配置：
- 目标域名：https://www.archdaily.cn
- 项目 URL 格式：/cn/<id>/<slug>
- 中文分类 & 内容
"""

import re
from datetime import datetime
from typing import List, Optional, Dict
from loguru import logger

from .archdaily_spider import ArchdailySpider
from .base_spider import ProjectData


class ArchdailyCNSpider(ArchdailySpider):
    """ArchDaily 中文站爬虫"""

    CATEGORIES = {
        "住宅": "https://www.archdaily.cn/cn/search/projects/categories/housing",
        "文化建筑": "https://www.archdaily.cn/cn/search/projects/categories/cultural-architecture",
        "商业建筑": "https://www.archdaily.cn/cn/search/projects/categories/commercial-architecture",
        "教育建筑": "https://www.archdaily.cn/cn/search/projects/categories/education-architecture",
        "办公建筑": "https://www.archdaily.cn/cn/search/projects/categories/offices",
        "体育建筑": "https://www.archdaily.cn/cn/search/projects/categories/sports-architecture",
        "工业建筑": "https://www.archdaily.cn/cn/search/projects/categories/industrial-architecture",
        "基础设施": "https://www.archdaily.cn/cn/search/projects/categories/infrastructure",
    }

    def get_name(self) -> str:
        return "archdaily_cn"

    def get_base_url(self) -> str:
        return "https://www.archdaily.cn"

    def get_categories(self) -> Dict[str, str]:
        return self.CATEGORIES

    # ── URL 规范化：确保域名指向 archdaily.cn ────────────────────────────
    def normalize_url(self, url: str) -> str:
        url = super().normalize_url(url)
        # 若爬到的链接仍指向 archdaily.com，替换为 cn 域
        url = url.replace("www.archdaily.com/cn/", "www.archdaily.cn/cn/")
        return url

    # ── 分类列表页爬取：中文站项目 URL 格式为 /cn/<digits>/ ──────────────
    def _crawl_category_impl(self, category_url: str, max_pages: int) -> List[str]:
        """在浏览器线程中执行分类爬取（中文站版）"""
        page = self.get_page()
        all_urls = set()

        try:
            for page_num in range(1, max_pages + 1):
                current_url = (
                    category_url if page_num == 1
                    else f"{category_url}/page/{page_num}"
                )
                logger.info(f"  爬取第{page_num}页: {current_url}")

                result_page = self.fetch_with_retry(current_url, page)
                if not result_page:
                    logger.warning(f"  第{page_num}页加载失败")
                    break

                page.wait_for_timeout(3000)

                page_urls: List[str] = []
                for link in page.locator('a').all():
                    try:
                        href = link.get_attribute('href') or ''
                        # 中文站项目 URL：/cn/<数字>/ 或 archdaily.cn/cn/<数字>/
                        if re.search(r'/cn/(\d{4,})', href):
                            full_url = self.normalize_url(href)
                            # 保证指向 archdaily.cn
                            if 'archdaily.cn' not in full_url:
                                full_url = full_url.replace('archdaily.com', 'archdaily.cn')
                            if '?' in full_url:
                                full_url = full_url.split('?')[0]
                            if full_url not in all_urls:
                                all_urls.add(full_url)
                                page_urls.append(full_url)
                    except Exception:
                        pass

                if not page_urls:
                    logger.info("  未找到更多项目，停止翻页")
                    break

                logger.info(f"  第{page_num}页找到 {len(page_urls)} 个新项目")
        finally:
            self.close_page(page)

        return list(all_urls)

    # ── 项目详情解析 ─────────────────────────────────────────────────────
    def _parse_project_impl(self, url: str) -> Optional[ProjectData]:
        """在浏览器线程中解析项目页面（中文站版）"""
        page = self.get_page()

        try:
            result_page = self.fetch_with_retry(url, page)
            if not result_page:
                return None

            source_id = self.extract_source_id(url)

            # ── 标题 ──────────────────────────────────────────────────────
            title = None
            for sel in [
                'h1.afd-title-line--big',
                'h1[class*="title"]',
                'h1',
                'meta[property="og:title"]',
            ]:
                try:
                    if sel.startswith('meta'):
                        val = page.locator(sel).get_attribute('content')
                    else:
                        val = page.locator(sel).first.inner_text(timeout=5000)
                    if val and val.strip():
                        title = re.sub(
                            r'\s*[|\-]\s*ArchDaily.*$', '', val.strip(),
                            flags=re.IGNORECASE
                        ).strip()
                        break
                except Exception:
                    continue

            if not title:
                logger.error(f"无法提取标题: {url}")
                return None

            # ── 描述 ──────────────────────────────────────────────────────
            description_parts: List[str] = []
            for desc_sel in ['div.afd-project-description', 'article']:
                try:
                    container = page.locator(desc_sel).first
                    for p in container.locator('p').all():
                        text = p.inner_text().strip()
                        if text and len(text) > 10:
                            description_parts.append(text)
                    if description_parts:
                        break
                except Exception:
                    pass
            description = "\n\n".join(description_parts) or None

            # ── 建筑师 ───────────────────────────────────────────────────
            architects: List[Dict] = []
            for arch_sel in [
                'div.authors-container a',
                'span.author a',
                'a[href*="/office/"]',
                'a[href*="/arquiteto/"]',
            ]:
                try:
                    elem = page.locator(arch_sel).first
                    text = elem.inner_text(timeout=3000).strip()
                    href = elem.get_attribute('href')
                    if text:
                        architects.append({
                            "name": text,
                            "firm": text,
                            "url": self.normalize_url(href) if href else None,
                        })
                        break
                except Exception:
                    pass

            # ── 面积 / 年份 / 地点（从 .afd-specs__item 解析）────────────
            area_sqm = None
            year = None
            location: Dict = {}
            try:
                for item in page.locator('.afd-specs__item').all():
                    try:
                        # 尝试 span 型（含 .afd-specs__key / .afd-specs__value）
                        try:
                            key = item.locator('.afd-specs__key').first.inner_text(timeout=500)
                            key = key.strip().rstrip(':：').strip()
                            value = item.locator('.afd-specs__value').first.inner_text(timeout=500).strip()
                        except Exception:
                            # SVG 图标型：整体文字如 "面积:\xa0\n3600 m²"
                            full_text = item.inner_text(timeout=500).strip()
                            m_kv = re.match(
                                r'^([^:\uff1a\n]+)[:\uff1a][\xa0\s\n]*(.+)$',
                                full_text, re.DOTALL
                            )
                            if not m_kv:
                                continue
                            key = m_kv.group(1).strip()
                            value = m_kv.group(2).strip().split('\n')[0].strip()

                        if '面积' in key or 'Area' in key:
                            m = re.search(r'([\d,\.]+)', value)
                            if m:
                                area_sqm = float(m.group(1).replace(',', ''))
                        elif '年份' in key or 'Year' in key:
                            m = re.search(r'(\d{4})', value)
                            if m:
                                year = int(m.group(1))
                        elif '城市' in key or 'City' in key:
                            location['city'] = value.strip()
                        elif '地区' in key or '国家' in key or 'Country' in key:
                            location['country'] = value.split('\n')[0].strip()
                    except Exception:
                        pass
            except Exception:
                pass

            # 补充：从 header-location 获取位置（如 "那格浦尔, 印度"）
            if not location:
                try:
                    loc_text = page.locator('.afd-specs__header-location').first.inner_text(timeout=3000).strip()
                    if loc_text:
                        parts = [p.strip() for p in loc_text.split(',') if p.strip()]
                        if len(parts) >= 2:
                            location = {"city": parts[0], "country": parts[-1]}
                        elif len(parts) == 1:
                            location = {"country": parts[0]}
                except Exception:
                    pass

            # ── 不抓取图片 ───────────────────────────────────────────────
            images: List[Dict] = []

            # ── 标签（仅保留分类/tag 链接，过滤系统标签）────────────────
            tags: List[str] = []
            try:
                for tag_el in page.locator('[class*="tag"] a').all():
                    try:
                        href = tag_el.get_attribute('href', timeout=500) or ''
                        text = tag_el.inner_text(timeout=500).strip()
                        if text and ('categories' in href or '/tag/' in href):
                            tags.append(text)
                    except Exception:
                        pass
            except Exception:
                pass

            # ── 分类：面包屑第3项（ArchDaily > 项目 > [类别] > ...）────
            primary_category = None
            try:
                crumbs = page.locator('[class*="breadcrumb"] a').all()
                if len(crumbs) >= 3:
                    primary_category = crumbs[2].inner_text(timeout=3000).strip()
            except Exception:
                pass

            # ── 发布日期 ─────────────────────────────────────────────────
            publish_date = None
            for sel, attr in [
                ('meta[property="article:published_time"]', 'content'),
                ('meta[name="publish-date"]', 'content'),
                ('time[datetime]', 'datetime'),
            ]:
                try:
                    val = page.locator(sel).first.get_attribute(attr, timeout=3000)
                    if val:
                        try:
                            publish_date = datetime.fromisoformat(val.replace('Z', '+00:00'))
                        except ValueError:
                            try:
                                publish_date = datetime.strptime(val[:10], '%Y-%m-%d')
                            except ValueError:
                                pass
                        if publish_date:
                            break
                except Exception:
                    pass

            return ProjectData(
                source="archdaily_cn",
                source_id=source_id,
                url=url,
                title=title,
                description=description,
                architects=architects,
                location=location or None,
                area_sqm=area_sqm,
                year=year,
                primary_category=primary_category,
                tags=tags,
                images=images,
                publish_date=publish_date,
            )

        except Exception as e:
            logger.error(f"解析失败: {url} - {e}")
            return None
        finally:
            self.close_page(page)

    def extract_source_id(self, url: str) -> str:
        """中文站 URL 格式：/cn/<id>/"""
        m = re.search(r'/cn/(\d+)', url)
        if m:
            return m.group(1)
        return url.rstrip('/').split('/')[-1]


__all__ = ['ArchdailyCNSpider']
