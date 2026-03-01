"""
Archdaily分类发现工具（简化版）

目标：
1. 分析首页HTML结构
2. 提取所有可能的分类链接
3. 生成分类映射表
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, List
from loguru import logger


def discover_archdaily_categories():
    """发现Archdaily分类"""

    BASE_URL = "https://www.archdaily.cn"
    categories = {
        "functions": {},  # 功能分类
        "regions": {},  # 地区分类
        "architects": {},  # 建筑师分类
        "years": {},  # 年份分类
        "topics": {},  # 主题分类
    }

    logger.info("🔍 开始发现Archdaily分类体系...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # 访问首页
            logger.info(f"📄 访问首页: {BASE_URL}/cn")
            page.goto(f"{BASE_URL}/cn", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)  # 等待5秒

            # 获取HTML
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # 保存HTML用于分析
            logger.info("💾 保存首页HTML")
            with open("_archdaily_homepage.html", "w", encoding="utf-8") as f:
                f.write(html)

            # 收集所有链接
            logger.info("🔗 分析所有链接...")
            all_links = soup.find_all("a", href=True)
            logger.info(f"   找到 {len(all_links)} 个链接")

            # 分析URL模式
            url_patterns = {
                "tag": [],
                "office": [],
                "search_category": [],
                "search_country": [],
                "search_year": [],
                "other": [],
            }

            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                if not text or len(text) > 50:
                    continue

                # 分析URL模式
                if "/tag/" in href:
                    url_patterns["tag"].append((text, href))
                elif "/office/" in href:
                    url_patterns["office"].append((text, href))
                elif "category=" in href:
                    url_patterns["search_category"].append((text, href))
                elif "country=" in href:
                    url_patterns["search_country"].append((text, href))
                elif "year=" in href:
                    url_patterns["search_year"].append((text, href))
                elif "/cn/" in href and text:
                    url_patterns["other"].append((text, href))

            # 打印发现的模式
            logger.info("\n📊 发现的URL模式:")
            for pattern, links in url_patterns.items():
                unique_links = list(set(links))  # 去重
                if unique_links:
                    logger.info(f"\n  {pattern.upper()}: {len(unique_links)} 个")
                    # 打印前10个示例
                    for i, (text, href) in enumerate(unique_links[:10]):
                        logger.info(f"    {i+1}. {text}")
                        logger.info(f"       → {href}")
                    if len(unique_links) > 10:
                        logger.info(f"    ... 还有 {len(unique_links) - 10} 个")

            # 添加到分类中
            logger.info("\n📝 整理分类...")

            # 主题/标签
            for text, href in set(url_patterns["tag"]):
                full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                categories["topics"][text] = full_url

            # 建筑师
            for text, href in set(url_patterns["office"]):
                full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                categories["architects"][text] = full_url

            # 年份（生成2010-2026）
            logger.info("📅 生成年份范围...")
            for year in range(2026, 2009, -1):
                url = f"{BASE_URL}/cn/search?year={year}"
                categories["years"][str(year)] = url

            # 打印摘要
            logger.info("\n" + "=" * 80)
            logger.info("📊 分类摘要")
            logger.info("=" * 80)
            for dim, cats in categories.items():
                logger.info(f"  {dim}: {len(cats)} 个")
            logger.info("=" * 80)

            # 保存到文件
            output_file = "archdaily_categories.json"
            logger.info(f"\n💾 保存分类到: {output_file}")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(categories, f, ensure_ascii=False, indent=2)

            logger.success(f"✅ 已保存到: {output_file}")

        finally:
            browser.close()

    return categories


def main():
    """主函数"""
    logger.info("🚀 Archdaily分类发现工具（简化版）")
    logger.info("=" * 80)

    try:
        categories = discover_archdaily_categories()
        logger.success("\n🎉 分类发现完成！")

        # 提示下一步
        logger.info("\n📝 下一步:")
        logger.info("  1. 查看分类映射: archdaily_categories.json")
        logger.info("  2. 查看首页HTML: _archdaily_homepage.html")
        logger.info("  3. 实现分类爬取器")

    except Exception as e:
        logger.error(f"❌ 发现失败: {e}")
        raise


if __name__ == "__main__":
    main()
