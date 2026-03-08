"""
网站结构调试脚本（使用Playwright）

从首页开始分析网站结构：
- 保存HTML内容
- 保存页面截图
- 分析DOM结构
- 查找分页规律

Author: AI Architecture Team
Version: v8.111.0
Date: 2026-02-17
"""

import sys
from pathlib import Path

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import sync_playwright

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)


def analyze_archdaily():
    """分析Archdaily网站结构"""
    logger.info("=" * 80)
    logger.info("🔍 分析Archdaily网站结构")
    logger.info("=" * 80)

    # 要测试的URL
    test_urls = [
        ("首页", "https://www.archdaily.cn/cn"),
        ("住宅分类", "https://www.archdaily.cn/cn/search/cn/projects/categories/houses"),
        ("搜索页", "https://www.archdaily.cn/cn/search/cn/projects"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 显示浏览器窗口（调试）
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )

        for idx, (name, url) in enumerate(test_urls, 1):
            logger.info(f"\n📄 测试 {idx}/3: {name}")
            logger.info(f"   URL: {url}")

            page = context.new_page()

            try:
                # 访问页面
                logger.info("   ⏳ 加载页面...")
                page.goto(url, wait_until="networkidle", timeout=60000)

                # 等待几秒（让JS完全执行）
                logger.info("   ⏳ 等待JavaScript执行...")
                page.wait_for_timeout(5000)

                # 截图
                screenshot_path = f"_debug_archdaily_{idx}_{name}.png"
                page.screenshot(path=screenshot_path, full_page=False)
                logger.success(f"   📸 截图保存: {screenshot_path}")

                # 保存HTML
                html = page.content()
                html_path = f"_debug_archdaily_{idx}_{name}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                logger.success(f"   💾 HTML保存: {html_path}")

                # 分析DOM结构
                soup = BeautifulSoup(html, "html.parser")

                logger.info("\n   🔍 DOM结构分析:")

                # 查找article标签
                articles = soup.find_all("article")
                logger.info(f"      - Article标签: {len(articles)} 个")
                if articles:
                    logger.info(f"        首个article的class: {articles[0].get('class')}")

                # 查找包含project的元素
                project_elements = soup.find_all(class_=lambda x: x and "project" in str(x).lower())
                logger.info(f"      - class包含'project'的元素: {len(project_elements)} 个")
                if project_elements:
                    for elem in project_elements[:3]:
                        logger.info(f"        - {elem.name} class={elem.get('class')}")

                # 查找包含item的元素
                item_elements = soup.find_all(class_=lambda x: x and "item" in str(x).lower())
                logger.info(f"      - class包含'item'的元素: {len(item_elements)} 个")
                if item_elements:
                    for elem in item_elements[:3]:
                        logger.info(f"        - {elem.name} class={elem.get('class')}")

                # 查找所有img标签
                images = soup.find_all("img")
                logger.info(f"      - 图片标签: {len(images)} 个")

                # 查找链接
                links = soup.find_all("a", href=True)
                project_links = [
                    l.get("href")
                    for l in links
                    if l.get("href") and "/cn/" in l.get("href") and any(char.isdigit() for char in l.get("href"))
                ]
                logger.info(f"      - 可能的项目链接: {len(project_links)} 个")
                if project_links:
                    logger.info("        示例:")
                    for link in project_links[:5]:
                        logger.info(f"          - {link}")

                # 查找分页元素
                pagination = soup.find_all(class_=lambda x: x and "pag" in str(x).lower())
                logger.info(f"      - 分页相关元素: {len(pagination)} 个")
                if pagination:
                    for elem in pagination[:3]:
                        logger.info(f"        - {elem.name} class={elem.get('class')}")

                # 查找data-*属性（可能用于JS加载）
                data_attrs = []
                for tag in soup.find_all(True):
                    for attr in tag.attrs:
                        if attr.startswith("data-"):
                            data_attrs.append((tag.name, attr, tag.get(attr)))

                logger.info(f"      - data-*属性: {len(data_attrs)} 个")
                if data_attrs:
                    unique_data_attrs = list(set([attr for _, attr, _ in data_attrs]))
                    logger.info(f"        唯一属性: {', '.join(unique_data_attrs[:10])}")

            except Exception as e:
                logger.error(f"   ❌ 分析失败: {e}")

            finally:
                page.close()

        browser.close()


def analyze_gooood():
    """分析Gooood网站结构"""
    logger.info("\n" + "=" * 80)
    logger.info("🔍 分析Gooood网站结构")
    logger.info("=" * 80)

    # 要测试的URL
    test_urls = [
        ("首页", "https://www.gooood.cn"),
        ("住宅分类", "https://www.gooood.cn/residential"),
        ("住宅第2页", "https://www.gooood.cn/residential/page/2"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 显示浏览器窗口
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )

        for idx, (name, url) in enumerate(test_urls, 1):
            logger.info(f"\n📄 测试 {idx}/3: {name}")
            logger.info(f"   URL: {url}")

            page = context.new_page()

            try:
                # 访问页面
                logger.info("   ⏳ 加载页面...")
                page.goto(url, wait_until="networkidle", timeout=60000)

                # 等待几秒
                logger.info("   ⏳ 等待JavaScript执行...")
                page.wait_for_timeout(5000)

                # 截图
                screenshot_path = f"_debug_gooood_{idx}_{name}.png"
                page.screenshot(path=screenshot_path, full_page=False)
                logger.success(f"   📸 截图保存: {screenshot_path}")

                # 保存HTML
                html = page.content()
                html_path = f"_debug_gooood_{idx}_{name}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                logger.success(f"   💾 HTML保存: {html_path}")

                # 分析DOM结构
                soup = BeautifulSoup(html, "html.parser")

                logger.info("\n   🔍 DOM结构分析:")

                # 查找article标签
                articles = soup.find_all("article")
                logger.info(f"      - Article标签: {len(articles)} 个")
                if articles:
                    for article in articles[:3]:
                        logger.info(f"        class={article.get('class')}")

                # 查找post相关元素
                post_elements = soup.find_all(class_=lambda x: x and "post" in str(x).lower())
                logger.info(f"      - class包含'post'的元素: {len(post_elements)} 个")
                if post_elements:
                    for elem in post_elements[:3]:
                        logger.info(f"        - {elem.name} class={elem.get('class')}")

                # 查找链接
                links = soup.find_all("a", href=True)
                project_links = [
                    l.get("href")
                    for l in links
                    if l.get("href") and "gooood.cn" in l.get("href") and l.get("href").count("/") >= 3
                ]
                logger.info(f"      - 可能的项目链接: {len(project_links)} 个")
                if project_links:
                    logger.info("        示例:")
                    for link in project_links[:5]:
                        logger.info(f"          - {link}")

                # 查找图片
                images = soup.find_all("img")
                logger.info(f"      - 图片标签: {len(images)} 个")

                # 查找分页
                pagination = soup.find_all(class_=lambda x: x and "pag" in str(x).lower())
                logger.info(f"      - 分页相关元素: {len(pagination)} 个")

                # 查找导航
                nav_elements = soup.find_all(class_=lambda x: x and "nav" in str(x).lower())
                logger.info(f"      - 导航相关元素: {len(nav_elements)} 个")

            except Exception as e:
                logger.error(f"   ❌ 分析失败: {e}")

            finally:
                page.close()

        browser.close()


def main():
    """主函数"""
    import sys

    logger.info("🚀 网站结构调试工具\n")
    logger.warning("⚠️ 此脚本会:")
    logger.warning("   1. 打开浏览器窗口（非无头模式）")
    logger.warning("   2. 访问多个页面")
    logger.warning("   3. 保存截图和HTML文件")
    logger.warning("   4. 分析DOM结构\n")

    # 支持命令行参数
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("选择要分析的网站 [1=Archdaily, 2=Gooood, 3=两者]: ").strip()

    if choice == "1":
        analyze_archdaily()
    elif choice == "2":
        analyze_gooood()
    elif choice == "3":
        analyze_archdaily()
        analyze_gooood()
    else:
        logger.error("❌ 无效选择")
        return

    logger.info("\n" + "=" * 80)
    logger.success("✅ 分析完成！")
    logger.info("\n📝 下一步:")
    logger.info("   1. 查看保存的截图（_debug_*.png）")
    logger.info("   2. 查看保存的HTML（_debug_*.html）")
    logger.info("   3. 根据实际结构更新爬虫选择器")
    logger.info("   4. 找出分页规律")


if __name__ == "__main__":
    main()
