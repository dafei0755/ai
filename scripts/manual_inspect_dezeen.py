#!/usr/bin/env python3
"""
手动查看Dezeen页面，分析实际的分类组织方式
检查是否使用标签、项目类型等其他方式
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
import time


def manual_inspect_dezeen():
    """手动检查Dezeen的内容组织"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        urls_to_check = [
            ("Architecture主页", "https://www.dezeen.com/architecture/"),
            ("Design主页", "https://www.dezeen.com/design/"),
            ("Interiors主页", "https://www.dezeen.com/interiors/"),
        ]

        for name, url in urls_to_check:
            print(f"\n{'='*80}")
            print(f"检查: {name}")
            print(f"URL: {url}")
            print(f"{'='*80}")

            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)

            # 查找所有可见的文本链接
            print("\n查找导航链接...")
            nav_links = page.locator("nav a, .nav a, .menu a, .filter a, .category a").all()

            found_categories = set()
            for link in nav_links[:50]:  # 限制数量
                try:
                    href = link.get_attribute("href")
                    text = link.text_content()
                    if text and href:
                        text = text.strip()
                        if len(text) > 0 and len(text) < 50:
                            found_categories.add(f"{text}: {href}")
                except:
                    pass

            if found_categories:
                print(f"\n找到 {len(found_categories)} 个导航链接:")
                for cat in sorted(found_categories):
                    print(f"  - {cat}")

            # 查找文章中的分类标签
            print("\n查找文章分类标签...")
            article_tags = page.locator('article a, .article a, [class*="tag"] a, [class*="category"] a').all()

            tags = set()
            for tag in article_tags[:100]:
                try:
                    href = tag.get_attribute("href")
                    text = tag.text_content()
                    if text and href and ("architecture" in href or "design" in href or "interiors" in href):
                        text = text.strip()
                        if len(text) > 0 and len(text) < 50:
                            tags.add(f"{text}: {href}")
                except:
                    pass

            if tags:
                print(f"\n找到 {len(tags)} 个标签:")
                for tag in sorted(list(tags)[:20]):  # 只显示前20个
                    print(f"  - {tag}")

            # 滚动并截图
            page.evaluate("window.scrollTo(0, 800)")
            page.wait_for_timeout(1000)

            screenshot_name = name.replace(" ", "_").lower() + ".png"
            screenshot_path = Path(__file__).parent.parent / "data" / screenshot_name
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"\n📸 截图已保存: {screenshot_path}")

            # 暂停以便观察
            print("\n>>> 暂停5秒以便观察页面...")
            time.sleep(5)

        print("\n\n" + "=" * 80)
        print("手动检查完成")
        print("=" * 80)
        print("\n💡 观察结果:")
        print("  1. Dezeen可能使用TAG系统而非固定分类层级")
        print("  2. 内容按时间倒序显示，没有明显的子分类菜单")
        print("  3. 建议索引策略：按主分类（4个）爬取所有项目，而非按子分类")

        browser.close()


if __name__ == "__main__":
    manual_inspect_dezeen()
