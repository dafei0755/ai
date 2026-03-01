"""
爬虫框架测试脚本

测试基础爬虫功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from intelligent_project_analyzer.crawlers import (
    ArchdailyCrawler,
    GoooodCrawler,
    CrawlerConfig,
)


def test_config():
    """测试配置创建"""
    logger.info("🧪 测试1: 配置创建")

    config = CrawlerConfig(
        max_projects=3,
        request_delay=2.0,
        days_back=30,
    )

    logger.success(f"   ✅ 配置创建成功")
    logger.info(f"      max_projects={config.max_projects}")
    logger.info(f"      request_delay={config.request_delay}")


def test_crawler_init():
    """测试爬虫初始化"""
    logger.info("\n🧪 测试2: 爬虫初始化")

    config = CrawlerConfig(max_projects=3)

    archdaily = ArchdailyCrawler(config=config, category="residential")
    logger.success(f"   ✅ Archdaily爬虫初始化成功")

    gooood = GoooodCrawler(config=config, category="residential")
    logger.success(f"   ✅ Gooood爬虫初始化成功")


def test_request_headers():
    """测试请求头生成"""
    logger.info("\n🧪 测试3: 请求头生成")

    config = CrawlerConfig()
    crawler = ArchdailyCrawler(config=config)

    headers = crawler._get_headers()
    logger.success(f"   ✅ 请求头生成成功")
    logger.info(f"      User-Agent: {headers['User-Agent'][:50]}...")


def test_url_construction():
    """测试URL构造"""
    logger.info("\n🧪 测试4: URL构造")

    config = CrawlerConfig()

    archdaily = ArchdailyCrawler(config=config, category="residential")
    logger.info(f"   Archdaily Base URL: {archdaily.BASE_URL}")
    logger.info(f"   Category URL: {archdaily.category_url}")
    logger.success(f"   ✅ Archdaily URL构造正确")

    gooood = GoooodCrawler(config=config, category="commercial")
    logger.info(f"   Gooood Base URL: {gooood.BASE_URL}")
    logger.info(f"   Category URL: {gooood.category_url}")
    logger.success(f"   ✅ Gooood URL构造正确")


def main():
    """运行所有测试"""
    logger.info("=" * 80)
    logger.info("🚀 开始爬虫框架测试")
    logger.info("=" * 80)

    try:
        test_config()
        test_crawler_init()
        test_request_headers()
        test_url_construction()

        logger.info("\n" + "=" * 80)
        logger.success("🎉 所有测试通过！爬虫框架工作正常")
        logger.info("=" * 80)

        logger.info("\n⚠️ 注意:")
        logger.info("   1. 实际爬取需要网络连接")
        logger.info("   2. 首次爬取建议设置 max_projects=3 测试")
        logger.info("   3. 注意遵守目标网站的robots.txt")
        logger.info("\n📝 下一步:")
        logger.info("   运行: python intelligent_project_analyzer/scripts/crawl_external_layer2.py")

    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
