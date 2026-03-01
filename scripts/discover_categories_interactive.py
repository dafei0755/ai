"""
Archdaily 分类发现工具（交互式版本）
通过点击菜单按钮，提取完整的分类体系（包括一级、二级分类）
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://www.archdaily.cn"


def discover_categories_interactive():
    """通过交互式点击菜单，发现完整的分类体系"""

    categories = {
        "functions": {},  # 功能分类（一级+二级）
        "regions": {},  # 地区分类
        "architects": {},  # 建筑师（从搜索页）
        "years": {},  # 年份
        "topics": {},  # 主题标签
        "materials": {},  # 材料
        "brands": {},  # 品牌
    }

    with sync_playwright() as p:
        print("\n🚀 Archdaily分类发现工具（交互式版本）")
        print("=" * 60)

        # 启动浏览器（可视化）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = context.new_page()

        # ============ 1. 提取功能分类 ============
        print("\n📂 步骤1: 提取功能分类（一级+二级）")
        print("-" * 60)

        try:
            # 访问首页
            print(f"📄 访问首页: {BASE_URL}/cn")
            page.goto(f"{BASE_URL}/cn", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # 点击"分类"按钮
            print("🖱️  点击「分类」按钮...")
            # 尝试多个可能的选择器
            try:
                page.click("text=分类", timeout=5000)
            except:
                try:
                    page.click("button:has-text('分类')", timeout=5000)
                except:
                    print("⚠️  未找到「分类」按钮，尝试其他方法...")

            page.wait_for_timeout(2000)

            # 提取分类链接
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # 保存HTML供调试
            debug_file = Path("_archdaily_categories_menu.html")
            debug_file.write_text(html, encoding="utf-8")
            print(f"💾 保存分类菜单HTML: {debug_file}")

            # 查找所有分类链接
            # 从截图看，分类结构可能是：
            # 一级分类（如"文化建筑"）-> 二级分类（如"游客中心"）
            all_links = soup.find_all("a", href=True)

            function_count = 0
            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # 识别功能分类的URL模式
                # 可能是 /cn/search/projects/categories/xxx 或其他模式
                if text and len(text) > 0 and len(text) < 50:
                    # 根据实际结构调整
                    if any(
                        keyword in text
                        for keyword in ["建筑", "中心", "场馆", "馆", "厅", "设施", "住宅", "商业", "办公", "工业", "基础设施"]
                    ):
                        full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                        if full_url not in categories["functions"].values():
                            categories["functions"][text] = full_url
                            function_count += 1
                            if function_count <= 10:
                                print(f"  ✓ {text}")

            print(f"\n📊 发现 {len(categories['functions'])} 个功能分类")

        except Exception as e:
            print(f"❌ 提取功能分类失败: {e}")

        # ============ 2. 提取地区分类 ============
        print("\n🌍 步骤2: 提取地区分类")
        print("-" * 60)

        try:
            # 访问首页
            page.goto(f"{BASE_URL}/cn", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # 点击"所有国家/地区"按钮
            print("🖱️  点击「所有国家/地区」按钮...")
            try:
                page.click("text=所有国家", timeout=5000)
            except:
                try:
                    page.click("text=国家", timeout=5000)
                except:
                    print("⚠️  未找到地区按钮，尝试其他方法...")

            page.wait_for_timeout(2000)

            # 提取地区链接
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            all_links = soup.find_all("a", href=True)
            region_count = 0

            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # 地区URL可能包含 /country/ 或 search?country=
                if ("/country/" in href or "country=" in href) and text:
                    full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                    if full_url not in categories["regions"].values():
                        categories["regions"][text] = full_url
                        region_count += 1
                        if region_count <= 10:
                            print(f"  ✓ {text}")

            print(f"\n📊 发现 {len(categories['regions'])} 个地区")

        except Exception as e:
            print(f"❌ 提取地区分类失败: {e}")

        # ============ 3. 提取建筑师（从搜索页） ============
        print("\n👷 步骤3: 提取建筑师列表（从搜索页）")
        print("-" * 60)

        try:
            # 访问建筑师搜索页
            architect_search_url = f"{BASE_URL}/cn/search/cn/offices"
            print(f"📄 访问建筑师搜索页: {architect_search_url}")
            page.goto(architect_search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # 提取建筑师链接
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # 保存HTML供调试
            debug_file = Path("_archdaily_architects_search.html")
            debug_file.write_text(html, encoding="utf-8")
            print(f"💾 保存建筑师搜索页HTML: {debug_file}")

            all_links = soup.find_all("a", href=True)
            architect_count = 0

            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # 建筑师URL模式: /cn/office/xxx
                if "/office/" in href and text and len(text) > 2:
                    full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                    # 去除参数
                    full_url = full_url.split("?")[0]

                    if text not in categories["architects"]:
                        categories["architects"][text] = full_url
                        architect_count += 1
                        if architect_count <= 20:
                            print(f"  ✓ {text}")

            print(f"\n📊 发现 {len(categories['architects'])} 个建筑师")

        except Exception as e:
            print(f"❌ 提取建筑师失败: {e}")

        # ============ 4. 提取其他维度（材料、品牌等） ============
        print("\n🔧 步骤4: 提取材料和品牌")
        print("-" * 60)

        try:
            # 访问首页
            page.goto(f"{BASE_URL}/cn", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # 点击"材料"按钮
            print("🖱️  点击「材料」按钮...")
            try:
                page.click("text=材料", timeout=5000)
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                all_links = soup.find_all("a", href=True)
                material_count = 0

                for link in all_links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    if text and 2 < len(text) < 30:
                        if any(keyword in text for keyword in ["木", "钢", "混凝土", "玻璃", "砖", "石", "材料"]):
                            full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                            if full_url not in categories["materials"].values():
                                categories["materials"][text] = full_url
                                material_count += 1
                                if material_count <= 10:
                                    print(f"  ✓ {text}")

                print(f"\n📊 发现 {len(categories['materials'])} 个材料")

            except:
                print("⚠️  未找到材料分类")

            # 点击"品牌"按钮
            page.goto(f"{BASE_URL}/cn", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            print("🖱️  点击「品牌」按钮...")
            try:
                page.click("text=品牌", timeout=5000)
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                all_links = soup.find_all("a", href=True)
                brand_count = 0

                for link in all_links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    if "/brand/" in href and text and len(text) > 2:
                        full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                        if text not in categories["brands"]:
                            categories["brands"][text] = full_url
                            brand_count += 1
                            if brand_count <= 10:
                                print(f"  ✓ {text}")

                print(f"\n📊 发现 {len(categories['brands'])} 个品牌")

            except:
                print("⚠️  未找到品牌分类")

        except Exception as e:
            print(f"❌ 提取材料/品牌失败: {e}")

        # ============ 5. 生成年份和主题（从之前的结果） ============
        print("\n📅 步骤5: 生成年份范围")
        print("-" * 60)

        # 年份：2010-2026
        for year in range(2026, 2009, -1):
            url = f"{BASE_URL}/cn/search?year={year}"
            categories["years"][str(year)] = url

        print(f"📊 生成 {len(categories['years'])} 个年份（2010-2026）")

        # 主题标签（从之前的简单版本导入）
        print("\n🏷️  步骤6: 导入主题标签")
        print("-" * 60)

        try:
            old_categories_file = Path("archdaily_categories.json")
            if old_categories_file.exists():
                with open(old_categories_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    categories["topics"] = old_data.get("topics", {})
                    print(f"📊 导入 {len(categories['topics'])} 个主题标签")
        except:
            pass

        # 关闭浏览器
        browser.close()

        # ============ 6. 保存结果 ============
        print("\n💾 步骤7: 保存完整分类映射")
        print("=" * 60)

        output_file = Path("archdaily_categories_full.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 已保存到: {output_file}")

        # 打印统计
        print("\n📊 最终统计：")
        print("-" * 60)
        for category_type, items in categories.items():
            print(f"  {category_type:15s}: {len(items):4d} 个")

        print("\n🎉 完整分类发现完成！")
        print("\n📝 下一步:")
        print("  1. 查看完整分类: archdaily_categories_full.json")
        print("  2. 检查调试文件: _archdaily_categories_menu.html")
        print("  3. 实现分类爬取器")


if __name__ == "__main__":
    discover_categories_interactive()
