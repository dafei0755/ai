#!/usr/bin/env python3
"""
分析Dezeen的分类结构
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
import re


def analyze_dezeen():
    """分析Dezeen的分类菜单"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("访问Dezeen首页...")
        page.goto("https://www.dezeen.com", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        print("\n查找分类链接...")

        all_categories = {}  # path -> name

        # 查找所有链接
        all_links = page.locator("a").all()
        print(f"页面共有 {len(all_links)} 个链接\n")

        for link in all_links:
            href = link.get_attribute("href")
            text = link.text_content()

            if href and text:
                text = text.strip()
                # 筛选分类链接 - Dezeen的分类URL格式
                if re.match(r"^https://www\.dezeen\.com/(architecture|design|interiors|technology)[/\w-]*/?$", href):
                    if text and len(text) > 0 and len(text) < 80 and not text.startswith("View"):
                        path = href.replace("https://www.dezeen.com/", "").rstrip("/")
                        if path not in all_categories or len(text) < len(all_categories[path]):
                            all_categories[path] = text

        print(f"\n{'='*80}")
        print(f"发现的分类 ({len(all_categories)} 个):")
        print(f"{'='*80}")

        # 按主分类分组
        grouped = {}
        for path, name in all_categories.items():
            main_cat = path.split("/")[0]
            if main_cat not in grouped:
                grouped[main_cat] = []
            grouped[main_cat].append({"name": name, "url": f"https://www.dezeen.com/{path}/", "path": path})

        for main_cat, items in sorted(grouped.items()):
            print(f"\n【{main_cat.upper()}】 ({len(items)} 个)")
            for item in sorted(items, key=lambda x: x["name"]):
                print(f"  - {item['name']}")
                print(f"    {item['url']}")

        # 输出JSON格式
        print(f"\n\n{'='*80}")
        print("JSON格式（可直接复制到website_structures.json）:")
        print(f"{'='*80}")
        print('"categories": [')
        all_items = []
        for main_cat, items in sorted(grouped.items()):
            for item in sorted(items, key=lambda x: x["name"]):
                all_items.append(f'  {{"name": "{item["name"]}", "url": "{item["url"]}"}}')
        print(",\n".join(all_items))
        print("]")

        # 保存截图
        screenshot_path = Path(__file__).parent.parent / "data" / "dezeen_homepage.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"\n📸 截图已保存: {screenshot_path}")

        browser.close()


if __name__ == "__main__":
    analyze_dezeen()
