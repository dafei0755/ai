#!/usr/bin/env python3
"""分析各个目标网站的结构和分类"""

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
from pathlib import Path
from typing import Dict, List, Any
import time


class WebsiteAnalyzer:
    """网站结构分析器"""

    def __init__(self):
        self.results = {}

    def analyze_archdaily(self) -> Dict[str, Any]:
        """分析Archdaily网站结构"""
        print("\n" + "=" * 80)
        print("分析 Archdaily.com")
        print("=" * 80)

        base_url = "https://www.archdaily.com"
        result = {
            "name": "Archdaily",
            "base_url": base_url,
            "categories": [],
            "list_url_patterns": [],
            "pagination_type": "",
            "notes": [],
        }

        try:
            # 获取首页
            response = requests.get(base_url, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")

            # 查找导航分类
            nav = soup.find("nav") or soup.find("header")
            if nav:
                links = nav.find_all("a", href=True)
                categories = []
                for link in links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    if "/category/" in href or "/tag/" in href:
                        categories.append({"name": text, "url": href if href.startswith("http") else base_url + href})

                result["categories"] = categories[:20]  # 前20个
                print(f"✅ 发现 {len(categories)} 个分类")

            # 分析列表页结构
            list_test_url = f"{base_url}/search/projects"
            print(f"\n测试列表页: {list_test_url}")
            response = requests.get(list_test_url, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")

            # 查找文章列表
            articles = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and "project" in x.lower())
            print(f"✅ 列表页发现 {len(articles)} 个项目")

            # 查找分页
            pagination = soup.find("div", class_=lambda x: x and "pagination" in x.lower() if x else False)
            if pagination:
                result["pagination_type"] = "传统分页"
                print("✅ 分页类型: 传统分页")
            else:
                result["pagination_type"] = "无限滚动或API"
                print("⚠️  未发现传统分页，可能使用无限滚动")

            result["list_url_patterns"] = [
                f"{base_url}/search/projects?page={{page}}",
                f"{base_url}/category/{{category}}?page={{page}}",
            ]

            result["notes"] = ["使用传统HTML结构", "支持按分类浏览", "可能有API接口", "建议先爬取分类列表，再按分类爬取项目"]

        except Exception as e:
            print(f"❌ 分析失败: {e}")
            result["error"] = str(e)

        return result

    def analyze_gooood(self) -> Dict[str, Any]:
        """分析Gooood网站结构"""
        print("\n" + "=" * 80)
        print("分析 Gooood.cn")
        print("=" * 80)

        base_url = "https://www.gooood.cn"
        result = {
            "name": "Gooood",
            "base_url": base_url,
            "categories": [],
            "list_url_patterns": [],
            "pagination_type": "",
            "notes": [],
        }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # 获取首页
                print(f"访问首页: {base_url}")
                page.goto(base_url, wait_until="networkidle", timeout=30000)
                time.sleep(2)

                # 查找分类菜单
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # 查找导航分类
                nav_links = soup.find_all("a", href=True)
                categories = []
                for link in nav_links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    if "/category/" in href or "/type/" in href or "/series/" in href:
                        full_url = href if href.startswith("http") else base_url + href
                        categories.append(
                            {
                                "name": text,
                                "url": full_url,
                                "type": "type" if "/type/" in href else "series" if "/series/" in href else "category",
                            }
                        )

                # 去重
                seen = set()
                unique_categories = []
                for cat in categories:
                    if cat["url"] not in seen:
                        seen.add(cat["url"])
                        unique_categories.append(cat)

                result["categories"] = unique_categories[:30]
                print(f"✅ 发现 {len(unique_categories)} 个分类")

                # 按类型分组
                by_type = {}
                for cat in unique_categories:
                    cat_type = cat.get("type", "other")
                    if cat_type not in by_type:
                        by_type[cat_type] = []
                    by_type[cat_type].append(cat["name"])

                print(f"\n分类统计:")
                for cat_type, names in by_type.items():
                    print(f"  {cat_type}: {len(names)} 个 - {', '.join(names[:5])}")

                # 测试分类列表页
                if unique_categories:
                    test_cat = unique_categories[0]
                    print(f"\n测试分类页: {test_cat['url']}")
                    page.goto(test_cat["url"], wait_until="networkidle", timeout=30000)
                    page.wait_for_selector("article.sg-article-item", timeout=10000)
                    time.sleep(2)

                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")
                    articles = soup.find_all("article", class_="sg-article-item")
                    print(f"✅ 分类页发现 {len(articles)} 个项目")

                    # 查找分页
                    pagination = soup.find("div", class_="pagination") or soup.find("nav", class_="navigation")
                    if pagination:
                        result["pagination_type"] = "传统分页"
                        print("✅ 分页类型: 传统分页")
                    else:
                        result["pagination_type"] = "动态加载"
                        print("⚠️  未发现传统分页，使用Vue动态加载")

                browser.close()

            result["list_url_patterns"] = [
                f"{base_url}/",
                f"{base_url}/category/type/{{category}}/page/{{page}}",
                f"{base_url}/category/series/{{series}}/page/{{page}}",
            ]

            result["notes"] = [
                "使用Vue.js单页应用",
                "必须使用Playwright爬取",
                "分类包括type(类型)和series(专栏)",
                "建议先爬取各分类列表，建立项目索引",
                "支持按分类和专栏浏览",
            ]

        except Exception as e:
            print(f"❌ 分析失败: {e}")
            result["error"] = str(e)

        return result

    def analyze_dezeen(self) -> Dict[str, Any]:
        """分析Dezeen网站结构"""
        print("\n" + "=" * 80)
        print("分析 Dezeen.com")
        print("=" * 80)

        base_url = "https://www.dezeen.com"
        result = {
            "name": "Dezeen",
            "base_url": base_url,
            "categories": [],
            "list_url_patterns": [],
            "pagination_type": "",
            "notes": [],
        }

        try:
            # 获取首页
            response = requests.get(
                base_url,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            soup = BeautifulSoup(response.content, "html.parser")

            # 查找导航分类
            nav = soup.find("nav") or soup.find("header")
            if nav:
                links = nav.find_all("a", href=True)
                categories = []
                for link in links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    if "architecture" in href.lower() or "design" in href.lower() or "interiors" in href.lower():
                        categories.append({"name": text, "url": href if href.startswith("http") else base_url + href})

                result["categories"] = categories[:20]
                print(f"✅ 发现 {len(categories)} 个分类")

            # 测试建筑分类
            arch_url = f"{base_url}/architecture/"
            print(f"\n测试分类页: {arch_url}")
            response = requests.get(
                arch_url,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            soup = BeautifulSoup(response.content, "html.parser")

            # 查找文章列表
            articles = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and "post" in x.lower())
            print(f"✅ 分类页发现 {len(articles)} 个项目")

            # 查找分页
            pagination = soup.find("div", class_="pagination") or soup.find("nav", attrs={"role": "navigation"})
            if pagination:
                result["pagination_type"] = "传统分页"
                print("✅ 分页类型: 传统分页")
            else:
                result["pagination_type"] = "无限滚动"
                print("⚠️  可能使用无限滚动")

            result["list_url_patterns"] = [
                f"{base_url}/architecture/page/{{page}}/",
                f"{base_url}/interiors/page/{{page}}/",
                f"{base_url}/design/page/{{page}}/",
            ]

            result["notes"] = ["使用WordPress结构", "传统HTML渲染", "按主题分类（建筑、室内、设计）", "建议按分类爬取全部列表", "可能有RSS feed"]

        except Exception as e:
            print(f"❌ 分析失败: {e}")
            result["error"] = str(e)

        return result

    def save_results(self, output_file: str = "data/website_structures.json"):
        """保存分析结果"""
        output_path = Path(__file__).parent.parent / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 分析结果已保存到: {output_path}")

    def run(self):
        """运行所有分析"""
        print("开始分析各网站结构...")

        # 分析Archdaily
        self.results["archdaily"] = self.analyze_archdaily()
        time.sleep(2)

        # 分析Gooood
        self.results["gooood"] = self.analyze_gooood()
        time.sleep(2)

        # 分析Dezeen
        self.results["dezeen"] = self.analyze_dezeen()

        # 保存结果
        self.save_results()

        # 打印汇总
        print("\n" + "=" * 80)
        print("分析汇总")
        print("=" * 80)
        for name, data in self.results.items():
            print(f"\n{data['name']}:")
            print(f"  分类数: {len(data.get('categories', []))}")
            print(f"  分页类型: {data.get('pagination_type', '未知')}")
            print(f"  URL模式: {len(data.get('list_url_patterns', []))} 个")
            if "error" in data:
                print(f"  ⚠️  错误: {data['error']}")


if __name__ == "__main__":
    analyzer = WebsiteAnalyzer()
    analyzer.run()
