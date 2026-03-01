"""
批量爬取所有功能分类的项目链接
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_project_analyzer.crawlers.category_crawler import CategoryCrawler
from loguru import logger


def crawl_all_function_categories():
    """爬取所有功能分类"""

    logger.info("\n" + "=" * 70)
    logger.info("🚀 批量爬取Archdaily所有功能分类")
    logger.info("=" * 70)

    # 创建爬虫
    crawler = CategoryCrawler(categories_file="archdaily_categories_cleaned.json", headless=False)  # 可视化运行

    # 显示待爬取的分类
    function_categories = crawler.categories.get("functions", {})

    # 过滤掉"更多XXX"的链接，只保留核心8个分类
    core_categories = {name: url for name, url in function_categories.items() if not name.startswith("更多")}

    logger.info(f"\n📊 核心功能分类: {len(core_categories)} 个")
    for i, name in enumerate(core_categories.keys(), 1):
        logger.info(f"  {i}. {name}")

    logger.info(f"\n⚙️ 爬取配置:")
    logger.info(f"  - 每个分类最多爬取: 20 页")
    logger.info(f"  - 每个分类最多项目: 500 个")
    logger.info(f"  - 输出文件: archdaily_all_function_projects.json")

    # 确认开始
    print("\n")
    confirm = input("是否开始爬取？(输入 yes 继续): ")
    if confirm.lower() != "yes":
        logger.info("❌ 用户取消")
        return

    # 批量爬取
    results = {}

    for i, (category_name, category_url) in enumerate(core_categories.items(), 1):
        logger.info(f"\n{'─'*70}")
        logger.info(f"📂 [{i}/{len(core_categories)}] {category_name}")
        logger.info(f"{'─'*70}")

        try:
            # 爬取分类
            project_urls = crawler.crawl_category(
                category_url, max_pages=20, max_projects=500  # 每个分类最多20页  # 每个分类最多500个项目
            )

            results[category_name] = project_urls

            logger.info(f"✅ {category_name}: {len(project_urls)} 个项目")

            # 保存中间结果
            crawler._save_results(results, "archdaily_all_function_projects.json")

            # 避免频繁请求
            import time

            time.sleep(3)

        except Exception as e:
            logger.error(f"❌ 爬取 {category_name} 失败: {e}")
            results[category_name] = []
            continue

    # 最终保存
    crawler._save_results(results, "archdaily_all_function_projects.json")

    # 统计
    total_projects = sum(len(urls) for urls in results.values())
    unique_projects = len(set(url for urls in results.values() for url in urls))

    logger.info(f"\n{'='*70}")
    logger.info(f"🎉 所有功能分类爬取完成！")
    logger.info(f"{'='*70}")
    logger.info(f"📊 统计:")
    logger.info(f"  - 分类数量: {len(results)}")
    logger.info(f"  - 总项目链接: {total_projects} 个")
    logger.info(f"  - 唯一项目: {unique_projects} 个")
    logger.info(f"  - 平均每分类: {total_projects // len(results) if results else 0} 个")
    logger.info(f"💾 已保存到: archdaily_all_function_projects.json")

    # 详细统计
    logger.info(f"\n📋 各分类详情:")
    for category_name, project_urls in results.items():
        logger.info(f"  {category_name:20s}: {len(project_urls):4d} 个项目")


if __name__ == "__main__":
    crawl_all_function_categories()
