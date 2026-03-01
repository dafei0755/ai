"""
Archdaily 分类发现工具 v2
改进版：更精准地提取分类，并通过点击按钮提取建筑师
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://www.archdaily.cn"


def clean_url(url):
    """清理URL，去除参数"""
    return url.split("?")[0] if "?" in url else url


def discover_categories_v2():
    """改进版分类发现"""

    categories = {
        "functions": {},  # 功能分类（一级+二级）
        "regions": {},  # 地区分类
        "architects": {},  # 建筑师
        "years": {},  # 年份
        "topics": {},  # 主题标签
    }

    with sync_playwright() as p:
        print("\n🚀 Archdaily分类发现工具 v2")
        print("=" * 60)

        # 启动浏览器
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = context.new_page()

        # ============ 1. 提取功能分类 ============
        print("\n📂 步骤1: 提取功能分类")
        print("-" * 60)

        try:
            page.goto(f"{BASE_URL}/cn", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # 点击"分类"按钮
            print("🖱️  点击「分类」按钮...")
            page.click("text=分类", timeout=5000)
            page.wait_for_timeout(2000)

            # 提取分类链接
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            all_links = soup.find_all("a", href=True)

            # 只保留包含 /categories/ 的分类链接
            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # 功能分类URL模式: /search/cn/projects/categories/xxx
                if "/categories/" in href and text and len(text) < 50:
                    full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                    full_url = clean_url(full_url)

                    if text not in categories["functions"]:
                        categories["functions"][text] = full_url
                        print(f"  ✓ {text}")

            print(f"\n📊 发现 {len(categories['functions'])} 个功能分类")

        except Exception as e:
            print(f"❌ 提取功能分类失败: {e}")

        # ============ 2. 提取地区分类 ============
        print("\n🌍 步骤2: 提取地区分类")
        print("-" * 60)

        try:
            page.goto(f"{BASE_URL}/cn", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # 点击"所有国家/地区"按钮
            print("🖱️  点击「所有国家/地区」按钮...")
            try:
                page.click("text=所有国家/地区", timeout=5000)
            except:
                page.click("text=国家", timeout=5000)

            page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            all_links = soup.find_all("a", href=True)

            # 地区URL模式: /search/projects/country/xxx
            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                if "/country/" in href and text and 2 < len(text) < 50:
                    full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                    full_url = clean_url(full_url)

                    if text not in categories["regions"]:
                        categories["regions"][text] = full_url
                        print(f"  ✓ {text}")

            print(f"\n📊 发现 {len(categories['regions'])} 个地区")

        except Exception as e:
            print(f"❌ 提取地区分类失败: {e}")

        # ============ 3. 提取建筑师（点击首页按钮） ============
        print("\n👷 步骤3: 提取建筑师列表")
        print("-" * 60)

        try:
            page.goto(f"{BASE_URL}/cn", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # 点击"建筑师"按钮
            print("🖱️  点击「建筑师」按钮...")
            page.click("text=建筑师", timeout=5000)
            page.wait_for_timeout(3000)

            # 等待建筑师列表加载
            print("⏳ 等待建筑师列表加载...")
            page.wait_for_timeout(3000)

            # 提取建筑师链接
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # 保存HTML供调试
            debug_file = Path("_archdaily_architects_menu.html")
            debug_file.write_text(html, encoding="utf-8")
            print(f"💾 保存建筑师菜单HTML: {debug_file}")

            all_links = soup.find_all("a", href=True)

            # 建筑师URL模式: /cn/office/xxx
            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                if "/office/" in href and text and 2 < len(text) < 100:
                    full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                    full_url = clean_url(full_url)

                    if text not in categories["architects"]:
                        categories["architects"][text] = full_url
                        if len(categories["architects"]) <= 30:
                            print(f"  ✓ {text}")

            print(f"\n📊 发现 {len(categories['architects'])} 个建筑师")
            print("💡 这是首页显示的推荐建筑师，总数可能达到26,000+")

        except Exception as e:
            print(f"❌ 提取建筑师失败: {e}")

        # ============ 4. 生成年份 ============
        print("\n📅 步骤4: 生成年份范围")
        print("-" * 60)

        for year in range(2026, 2009, -1):
            url = f"{BASE_URL}/cn/search?year={year}"
            categories["years"][str(year)] = url

        print(f"📊 生成 {len(categories['years'])} 个年份（2010-2026）")

        # ============ 5. 导入主题标签 ============
        print("\n🏷️  步骤5: 导入主题标签")
        print("-" * 60)

        try:
            old_file = Path("archdaily_categories.json")
            if old_file.exists():
                with open(old_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    if "topics" in old_data:
                        categories["topics"] = old_data["topics"]
                        print(f"📊 导入 {len(categories['topics'])} 个主题标签")
        except:
            pass

        # 关闭浏览器
        browser.close()

        # ============ 6. 保存结果 ============
        print("\n💾 步骤6: 保存分类映射")
        print("=" * 60)

        output_file = Path("archdaily_categories_cleaned.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 已保存到: {output_file}")

        # 打印统计
        print("\n📊 最终统计：")
        print("-" * 60)
        total = 0
        for category_type, items in categories.items():
            count = len(items)
            total += count
            print(f"  {category_type:15s}: {count:4d} 个")
        print("-" * 60)
        print(f"  {'总计':15s}: {total:4d} 个")

        # 显示部分示例
        print("\n📝 示例分类：")
        print("-" * 60)

        if categories["functions"]:
            print("\n功能分类示例（前5个）：")
            for i, name in enumerate(list(categories["functions"].keys())[:5]):
                print(f"  {i+1}. {name}")

        if categories["regions"]:
            print("\n地区分类示例（前5个）：")
            for i, name in enumerate(list(categories["regions"].keys())[:5]):
                print(f"  {i+1}. {name}")

        if categories["architects"]:
            print("\n建筑师示例（前10个）：")
            for i, name in enumerate(list(categories["architects"].keys())[:10]):
                print(f"  {i+1}. {name}")

        print("\n🎉 分类发现完成！")
        print("\n📝 下一步:")
        print("  1. 查看完整分类: archdaily_categories_cleaned.json")
        print("  2. 实现CategoryCrawler，开始爬取项目")
        print("  3. 建筑师有26,000+个，可以后续从项目中收集")


if __name__ == "__main__":
    discover_categories_v2()
