#!/usr/bin/env python3
"""
深度分析Dezeen的完整分类结构
多维度排查：主分类、子分类、标签、筛选器
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
import re
import json


def analyze_page_categories(page, url, main_category):
    """分析单个页面的所有分类链接"""
    print(f"\n{'='*80}")
    print(f"正在分析: {main_category} - {url}")
    print(f"{'='*80}")

    # 重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️ 加载失败 (尝试 {attempt+1}/{max_retries}): {e}")
                page.wait_for_timeout(2000)
            else:
                print(f"  ❌ 加载失败，跳过: {e}")
                return []

    # 滚动页面以加载所有内容
    for i in range(3):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        page.wait_for_timeout(500)

    categories = []

    # 查找所有链接
    all_links = page.locator("a").all()

    for link in all_links:
        href = link.get_attribute("href")
        text = link.text_content()

        if href and text:
            text = text.strip()
            # 匹配子分类链接
            # 格式: /architecture/xxx/, /design/xxx/, /interiors/xxx/
            pattern = rf"^https://www\.dezeen\.com/{main_category}/[\w-]+/?$"
            if re.match(pattern, href):
                if text and len(text) > 0 and len(text) < 100:
                    if not any(skip in text.lower() for skip in ["view", "more", "read", "comment", "»"]):
                        sub_path = href.replace(f"https://www.dezeen.com/{main_category}/", "").rstrip("/")
                        if sub_path:  # 确保是子分类，不是主分类本身
                            categories.append({"name": text, "url": href, "sub_category": sub_path})

    # 去重
    unique_cats = {}
    for cat in categories:
        key = cat["url"]
        if key not in unique_cats or len(cat["name"]) < len(unique_cats[key]["name"]):
            unique_cats[key] = cat

    return list(unique_cats.values())


def deep_analyze_dezeen():
    """深度分析Dezeen"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 第一步：分析首页，找出主分类
        print("\n【第一步】分析首页主分类")
        page.goto("https://www.dezeen.com", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        main_categories = {}
        all_links = page.locator("a").all()

        for link in all_links:
            href = link.get_attribute("href")
            text = link.text_content()

            if href and text:
                text = text.strip()
                # 主分类格式: /architecture/, /design/, /interiors/, /technology/
                if re.match(r"^https://www\.dezeen\.com/(architecture|design|interiors|technology)/?$", href):
                    main_cat = href.split("/")[-2] if href.endswith("/") else href.split("/")[-1]
                    if main_cat not in main_categories:
                        main_categories[main_cat] = {"name": text, "url": href, "subcategories": []}

        print(f"找到 {len(main_categories)} 个主分类:")
        for cat in main_categories.keys():
            print(f"  - {cat}")

        # 第二步：深入每个主分类，查找子分类
        print("\n【第二步】深入分析每个主分类的子分类")

        for main_cat, info in main_categories.items():
            subcats = analyze_page_categories(page, info["url"], main_cat)
            info["subcategories"] = subcats
            print(f"\n{main_cat.upper()}: 找到 {len(subcats)} 个子分类")
            for subcat in sorted(subcats, key=lambda x: x["name"]):
                print(f"  - {subcat['name']} ({subcat['sub_category']})")

        # 第三步：检查是否有更多分类（通过搜索或筛选）
        print("\n【第三步】检查额外的分类和标签")

        # 访问项目搜索页，查看筛选器
        search_urls = [
            "https://www.dezeen.com/architecture/projects/",
            "https://www.dezeen.com/design/products/",
            "https://www.dezeen.com/interiors/",
        ]

        extra_categories = []
        for search_url in search_urls:
            try:
                page.goto(search_url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # 查找筛选器中的分类
                filter_links = page.locator(
                    'a[href*="/architecture/"], a[href*="/design/"], a[href*="/interiors/"]'
                ).all()

                for link in filter_links[:50]:  # 限制数量
                    href = link.get_attribute("href")
                    text = link.text_content()

                    if href and text and len(text.strip()) > 0:
                        text = text.strip()
                        if re.match(r"^https://www\.dezeen\.com/(architecture|design|interiors)/[\w-]+/?$", href):
                            extra_categories.append({"name": text, "url": href})
            except Exception as e:
                print(f"  分析 {search_url} 时出错: {e}")

        # 合并额外发现的分类
        print(f"\n通过搜索页发现额外分类: {len(extra_categories)} 个")

        # 第四步：统计和输出
        print("\n" + "=" * 80)
        print("【最终统计】")
        print("=" * 80)

        total_count = 0
        all_categories_list = []

        for main_cat, info in sorted(main_categories.items()):
            count = len(info["subcategories"]) + 1  # +1 是主分类本身
            total_count += count

            print(f"\n【{main_cat.upper()}】: {count} 个分类")
            print(f"  └─ {info['name']} (主分类)")
            print(f"     {info['url']}")

            all_categories_list.append({"name": info["name"], "url": info["url"], "type": "main"})

            for subcat in sorted(info["subcategories"], key=lambda x: x["name"]):
                print(f"  └─ {subcat['name']}")
                print(f"     {subcat['url']}")

                all_categories_list.append(
                    {"name": subcat["name"], "url": subcat["url"], "type": "sub", "parent": main_cat}
                )

        print(f"\n总计: {total_count} 个分类（包括主分类和子分类）")

        # 输出JSON格式
        print("\n" + "=" * 80)
        print("JSON格式（用于website_structures.json）:")
        print("=" * 80)
        print('"categories": [')
        json_items = []
        for cat in all_categories_list:
            json_items.append(f'  {{"name": "{cat["name"]}", "url": "{cat["url"]}"}}')
        print(",\n".join(json_items))
        print("]")

        # 保存到文件
        output_file = Path(__file__).parent.parent / "data" / "dezeen_categories.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {"main_categories": main_categories, "all_categories": all_categories_list, "total_count": total_count},
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"\n✅ 完整分类已保存到: {output_file}")

        # 保存截图
        page.goto("https://www.dezeen.com/architecture/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        screenshot_path = Path(__file__).parent.parent / "data" / "dezeen_architecture.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"📸 Architecture页面截图: {screenshot_path}")

        browser.close()


if __name__ == "__main__":
    deep_analyze_dezeen()
