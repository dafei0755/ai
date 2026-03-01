"""
Archdaily分类发现工具

目标：
1. 分析首页导航结构
2. 提取所有分类链接（功能、地区、建筑师、年份）
3. 生成分类映射表
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, List
from loguru import logger


class CategoryDiscoverer:
    """Archdaily分类发现器"""

    BASE_URL = "https://www.archdaily.cn"

    def __init__(self):
        self.categories = {
            "functions": {},  # 功能分类
            "regions": {},  # 地区分类
            "architects": {},  # 建筑师分类
            "years": {},  # 年份分类
            "topics": {},  # 主题分类
        }

    def discover_all(self) -> Dict[str, Dict[str, str]]:
        """发现所有分类"""
        logger.info("🔍 开始发现Archdaily分类体系...")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            try:
                # 访问首页
                logger.info(f"📄 访问首页: {self.BASE_URL}/cn")
                page.goto(f"{self.BASE_URL}/cn", wait_until="domcontentloaded")

                # 等待页面加载
                page.wait_for_timeout(3000)

                # 获取HTML
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # 保存HTML用于分析
                logger.info("💾 保存首页HTML用于分析")
                with open("_archdaily_homepage.html", "w", encoding="utf-8") as f:
                    f.write(html)

                # 1. 发现功能分类（从导航栏）
                self._discover_function_categories(soup, page)

                # 2. 发现地区分类（需要点击下拉菜单）
                self._discover_region_categories_interactive(page)

                # 3. 发现建筑师分类
                self._discover_architect_categories_interactive(page)

                # 4. 发现年份范围
                self._discover_year_range()

                # 5. 发现主题/标签
                self._discover_topics(soup)

                # 6. 从页面链接推测URL模式
                self._discover_url_patterns(soup)

            finally:
                browser.close()

        return self.categories

    def _discover_function_categories(self, soup: BeautifulSoup, page=None):
        """发现功能分类（从导航栏）"""
        logger.info("🏗️ 发现功能分类...")

        # 查找导航栏中的分类链接
        # 可能的选择器：nav, .nav, .menu, .navigation
        nav_selectors = ["nav.afd-nav", "div.afd-nav", "ul.nav-menu", "div.navigation", "nav"]

        for selector in nav_selectors:
            nav = soup.select_one(selector)
            if nav:
                logger.info(f"✓ 找到导航栏: {selector}")

                # 提取所有链接
                links = nav.find_all("a", href=True)

                for link in links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    # 过滤出分类链接
                    # 模式1: /cn/tag/xxx
                    # 模式2: /cn/search?category=xxx
                    if "/tag/" in href or "category=" in href:
                        # 提取分类名称
                        if text and text not in ["首页", "Home", "登录", "注册"]:
                            full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                            self.categories["functions"][text] = full_url
                            logger.debug(f"  - {text}: {href}")

                break

        logger.info(f"✅ 发现 {len(self.categories['functions'])} 个功能分类")

    def _discover_region_categories_interactive(self, page):
        """发现地区分类（交互式）"""
        logger.info("🌍 发现地区分类...")

        try:
            # 尝试找到地区下拉菜单
            # 可能的文本："国家", "地区", "Countries", "Regions"
            region_triggers = ['text="国家"', 'text="地区"', 'text="Countries"', 'text="所有国家"']

            for trigger in region_triggers:
                try:
                    logger.debug(f"尝试点击: {trigger}")
                    page.click(trigger, timeout=2000)
                    page.wait_for_timeout(1000)

                    # 获取展开后的HTML
                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # 查找地区链接容器
                    # 可能的选择器：.dropdown-menu, .country-list, .region-list
                    region_containers = soup.select(
                        ".dropdown-menu, .country-list, .region-list, [class*='country'], [class*='region']"
                    )

                    for container in region_containers:
                        links = container.find_all("a", href=True)

                        for link in links:
                            href = link.get("href", "")
                            text = link.get_text(strip=True)

                            # 地区链接模式
                            if "country=" in href or "/country/" in href:
                                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                                self.categories["regions"][text] = full_url
                                logger.debug(f"  - {text}: {href}")

                    if self.categories["regions"]:
                        logger.info(f"✅ 发现 {len(self.categories['regions'])} 个地区")
                        return

                except Exception as e:
                    logger.debug(f"  未找到: {trigger}")
                    continue

        except Exception as e:
            logger.warning(f"⚠️ 地区分类发现失败: {e}")

        if not self.categories["regions"]:
            logger.info("ℹ️ 未发现地区分类（可能需要登录或不同交互方式）")

    def _discover_architect_categories_interactive(self, page):
        """发现建筑师分类（交互式）"""
        logger.info("👷 发现建筑师分类...")

        try:
            # 尝试找到建筑师下拉菜单
            architect_triggers = ['text="建筑师"', 'text="Architects"', 'text="事务所"', 'text="Offices"']

            for trigger in architect_triggers:
                try:
                    logger.debug(f"尝试点击: {trigger}")
                    page.click(trigger, timeout=2000)
                    page.wait_for_timeout(1000)

                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # 查找建筑师链接
                    architect_containers = soup.select(
                        ".dropdown-menu, .architect-list, .office-list, [class*='architect'], [class*='office']"
                    )

                    for container in architect_containers:
                        links = container.find_all("a", href=True)

                        for link in links:
                            href = link.get("href", "")
                            text = link.get_text(strip=True)

                            # 建筑师链接模式: /cn/office/xxx
                            if "/office/" in href:
                                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                                self.categories["architects"][text] = full_url
                                logger.debug(f"  - {text}: {href}")

                    if self.categories["architects"]:
                        logger.info(f"✅ 发现 {len(self.categories['architects'])} 个建筑师")
                        return

                except Exception as e:
                    logger.debug(f"  未找到: {trigger}")
                    continue

        except Exception as e:
            logger.warning(f"⚠️ 建筑师分类发现失败: {e}")

        if not self.categories["architects"]:
            logger.info("ℹ️ 未发现建筑师分类（可能需要登录或不同交互方式）")

    def _discover_year_range(self):
        """发现年份范围"""
        logger.info("📅 生成年份范围...")

        # 生成2010-2026年的所有年份
        current_year = 2026
        start_year = 2010

        for year in range(current_year, start_year - 1, -1):
            # 假设URL模式：/cn/search?year=YYYY
            url = f"{self.BASE_URL}/cn/search?year={year}"
            self.categories["years"][str(year)] = url

        logger.info(f"✅ 生成 {len(self.categories['years'])} 个年份")

    def _discover_topics(self, soup: BeautifulSoup):
        """发现主题/标签"""
        logger.info("🏷️ 发现主题标签...")

        # 查找标签云或主题列表
        # 可能的选择器：.tags, .topics, .tag-cloud
        tag_selectors = [".tags", ".topics", ".tag-cloud", "[class*='tag']"]

        for selector in tag_selectors:
            tag_containers = soup.select(selector)

            for container in tag_containers:
                links = container.find_all("a", href=True)

                for link in links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    # 标签链接模式: /cn/tag/xxx
                    if "/tag/" in href and text:
                        full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                        self.categories["topics"][text] = full_url

        if self.categories["topics"]:
            logger.info(f"✅ 发现 {len(self.categories['topics'])} 个主题标签")
        else:
            logger.info("ℹ️ 未发现主题标签")

    def save_to_file(self, filepath: str = "archdaily_categories.json"):
        """保存分类映射到文件"""
        logger.info(f"💾 保存分类映射到: {filepath}")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.categories, f, ensure_ascii=False, indent=2)

        logger.success(f"✅ 已保存到: {filepath}")

    def print_summary(self):
        """打印分类摘要"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 Archdaily分类体系摘要")
        logger.info("=" * 80)

        for dimension, categories in self.categories.items():
            logger.info(f"\n{dimension.upper()}:")
            logger.info(f"  总数: {len(categories)}")

            # 打印前10个示例
            if categories:
                logger.info(f"  示例:")
                for i, (name, url) in enumerate(list(categories.items())[:10]):
                    logger.info(f"    {i+1}. {name}")
                    logger.info(f"       → {url}")

                if len(categories) > 10:
                    logger.info(f"    ... 还有 {len(categories) - 10} 个")

        logger.info("\n" + "=" * 80)
        logger.info(f"📈 总计: {sum(len(cats) for cats in self.categories.values())} 个分类")
        logger.info("=" * 80 + "\n")


def main():
    """主函数"""
    logger.info("🚀 Archdaily分类发现工具")
    logger.info("=" * 80)

    discoverer = CategoryDiscoverer()

    # 发现所有分类
    categories = discoverer.discover_all()

    # 打印摘要
    discoverer.print_summary()

    # 保存到文件
    discoverer.save_to_file("archdaily_categories.json")

    logger.success("🎉 分类发现完成！")


if __name__ == "__main__":
    main()
