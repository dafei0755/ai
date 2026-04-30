"""
Archdaily爬虫（重构版）

继承自BaseSpider，实现统一接口
"""

import re
from typing import List, Optional, Dict
from loguru import logger

from .base_spider import BaseSpider, ProjectData


class ArchdailySpider(BaseSpider):
    """Archdaily爬虫"""

    CATEGORIES = {
        "Housing": "https://www.archdaily.com/search/projects/categories/housing",
        "Cultural": "https://www.archdaily.com/search/projects/categories/cultural-architecture",
        "Commercial": "https://www.archdaily.com/search/projects/categories/commercial-architecture",
        "Education": "https://www.archdaily.com/search/projects/categories/education-architecture",
        "Office": "https://www.archdaily.com/search/projects/categories/offices",
        "Sports": "https://www.archdaily.com/search/projects/categories/sports-architecture",
        "Industrial": "https://www.archdaily.com/search/projects/categories/industrial-architecture",
        "Infrastructure": "https://www.archdaily.com/search/projects/categories/infrastructure",
    }

    def get_name(self) -> str:
        return "archdaily"

    def get_base_url(self) -> str:
        return "https://www.archdaily.com"

    def get_categories(self) -> Dict[str, str]:
        return self.CATEGORIES

    def crawl_category(self, category_url: str, max_pages: int = 20) -> List[str]:
        """爬取分类页面，获取项目URL列表（线程安全）"""
        return self.run_in_browser_thread(self._crawl_category_impl, category_url, max_pages)

    def _crawl_category_impl(self, category_url: str, max_pages: int) -> List[str]:
        """在浏览器线程中执行分类爬取"""
        page = self.get_page()
        all_urls = set()

        try:
            for page_num in range(1, max_pages + 1):
                if page_num == 1:
                    current_url = category_url
                else:
                    current_url = f"{category_url}/page/{page_num}"

                logger.info(f"  爬取第{page_num}页: {current_url}")

                result_page = self.fetch_with_retry(current_url, page)
                if not result_page:
                    logger.warning(f"  第{page_num}页加载失败")
                    break

                page.wait_for_timeout(3000)

                all_page_links = page.locator('a').all()

                page_urls = []
                for link in all_page_links:
                    try:
                        href = link.get_attribute('href')
                        if href and re.search(r'/(10\d{5,7})/', href):
                            full_url = self.normalize_url(href)
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

    def parse_project_page(self, url: str) -> Optional[ProjectData]:
        """解析项目页面（线程安全）"""
        return self.run_in_browser_thread(self._parse_project_impl, url)

    def _parse_project_impl(self, url: str) -> Optional[ProjectData]:
        """在浏览器线程中执行项目解析"""
        page = self.get_page()

        try:
            result_page = self.fetch_with_retry(url, page)
            if not result_page:
                return None

            source_id = self.extract_source_id(url)

            # 标题（多选择器回退，兼容 archdaily 改版）
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
                        # 去掉末尾 " | ArchDaily" 等后缀
                        import re as _re
                        title = _re.sub(r'\s*[|\-]\s*ArchDaily.*$', '', val.strip(), flags=_re.IGNORECASE).strip()
                        break
                except Exception:
                    continue

            if not title:
                logger.error(f"无法提取标题: {url}")
                return None

            # 描述
            description_parts = []
            try:
                desc_container = page.locator('div.afd-project-description').first
                paragraphs = desc_container.locator('p').all()
                for p in paragraphs:
                    text = p.inner_text().strip()
                    if text and len(text) > 10:
                        description_parts.append(text)

                if not description_parts:
                    article_paragraphs = page.locator('article p').all()
                    for p in article_paragraphs:
                        text = p.inner_text().strip()
                        if text and len(text) > 10:
                            description_parts.append(text)
            except Exception as e:
                logger.warning(f"描述提取失败: {e}")

            description = "\n\n".join(description_parts) if description_parts else None

            # 建筑师
            architects = []
            try:
                architect_text = page.locator('div.authors-container a').first.inner_text()
                firm_link = page.locator('div.authors-container a').first.get_attribute('href')
                architects.append({
                    "name": architect_text,
                    "firm": architect_text,
                    "url": self.normalize_url(firm_link) if firm_link else None,
                })
            except Exception:
                pass

            # 元数据
            area_sqm = None
            year = None
            location = {}

            try:
                info_items = page.locator('li.info-item').all()
                for item in info_items:
                    try:
                        label = item.locator('.info-label').inner_text().strip()
                        value = item.locator('.info-value').inner_text().strip()

                        if '面积' in label or 'Area' in label:
                            match = re.search(r'([\d,\.]+)', value)
                            if match:
                                area_sqm = float(match.group(1).replace(',', ''))
                        elif '年份' in label or 'Year' in label:
                            match = re.search(r'(\d{4})', value)
                            if match:
                                year = int(match.group(1))
                        elif '地点' in label or 'Location' in label:
                            parts = value.split(',')
                            if len(parts) >= 2:
                                location['city'] = parts[0].strip()
                                location['country'] = parts[-1].strip()
                            else:
                                location['country'] = value.strip()
                    except Exception:
                        pass
            except Exception:
                pass

            # 图片（多选择器回退）
            images = []
            for img_sel in ['div.image-container img', 'figure img', 'article img', 'img[src*="archdaily"]']:
                try:
                    gallery_images = page.locator(img_sel).all()
                    for img in gallery_images[:20]:
                        try:
                            src = img.get_attribute('data-src') or img.get_attribute('src')
                            if src and src.startswith('http') and 'placeholder' not in src:
                                images.append({
                                    "url": self.normalize_url(src),
                                    "caption": img.get_attribute('alt') or "",
                                })
                        except Exception:
                            pass
                    if images:
                        break
                except Exception:
                    pass

            # 标签
            tags = []
            try:
                tag_elements = page.locator('a.afd-tag').all()
                for tag in tag_elements:
                    try:
                        tag_text = tag.inner_text().strip()
                        if tag_text:
                            tags.append(tag_text)
                    except Exception:
                        pass
            except Exception:
                pass

            # 分类
            primary_category = None
            try:
                breadcrumb = page.locator('nav.breadcrumb a').all()
                if len(breadcrumb) >= 2:
                    primary_category = breadcrumb[-1].inner_text().strip()
            except Exception:
                pass

            return ProjectData(
                source="archdaily",
                source_id=source_id,
                url=url,
                title=title,
                description=description,
                architects=architects,
                location=location if location else None,
                area_sqm=area_sqm,
                year=year,
                primary_category=primary_category,
                tags=tags,
                images=images,
                publish_date=None,
            )

        except Exception as e:
            logger.error(f"解析失败: {url} - {e}")
            return None
        finally:
            self.close_page(page)

    def extract_source_id(self, url: str) -> str:
        match = re.search(r'/cn/(\d+)/', url)
        if match:
            return match.group(1)
        return super().extract_source_id(url)


# 向后兼容
class ArchdailyCrawler(ArchdailySpider):
    pass


__all__ = ['ArchdailySpider', 'ArchdailyCrawler']
