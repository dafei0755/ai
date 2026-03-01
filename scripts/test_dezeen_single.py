#!/usr/bin/env python3
"""测试Dezeen单篇文章爬取"""

import sys
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.external_data_system.spiders.dezeen_spider import DezeenSpider
from loguru import logger


def test_dezeen_single_article(url: str = None):
    """测试单篇文章爬取"""

    # 默认测试URL（使用比较老的经典文章，不容易404）
    if not url:
        # 这个URL来自2023年，比较稳定
        url = "https://www.dezeen.com/2023/12/22/best-houses-2023/"
        logger.info("使用默认测试URL (2023年最佳住宅)")

    logger.info("=" * 80)
    logger.info(f"测试URL: {url}")
    logger.info("=" * 80)

    # 创建spider
    spider = DezeenSpider(use_playwright=True)

    # 爬取文章
    logger.info("开始爬取...")
    project_data = spider.fetch_project_detail(url)

    if project_data:
        logger.success("✅ 爬取成功!")
        logger.info("=" * 80)
        logger.info("项目数据:")
        logger.info("=" * 80)
        logger.info(f"标题: {project_data.title}")
        logger.info(f"来源: {project_data.source}")
        logger.info(f"来源ID: {project_data.source_id}")
        logger.info(f"URL: {project_data.url}")
        logger.info(f"描述长度: {len(project_data.description)} 字符")
        logger.info(f"描述预览: {project_data.description[:300]}...")
        logger.info(f"建筑师: {project_data.architects}")
        logger.info(f"位置: {project_data.location}")
        logger.info(f"年份: {project_data.year}")
        logger.info(f"主分类: {project_data.primary_category}")
        logger.info(f"子分类: {project_data.sub_categories}")
        logger.info(f"标签数: {len(project_data.tags)}")
        logger.info(f"标签: {project_data.tags[:10]}")
        logger.info(f"图片数: {len(project_data.images)}")
        logger.info(f"发布日期: {project_data.publish_date}")
        logger.info("=" * 80)

        # 质量评估
        from intelligent_project_analyzer.external_data_system.utils.data_processing import DataValidator

        validator = DataValidator()

        # 将ProjectData转换为字典
        data_dict = {
            "source": project_data.source,
            "source_id": project_data.source_id,
            "url": project_data.url,
            "title": project_data.title,
            "description": project_data.description,
            "architects": project_data.architects,
            "location": project_data.location,
            "area_sqm": project_data.area_sqm,
            "year": project_data.year,
            "primary_category": project_data.primary_category,
            "sub_categories": project_data.sub_categories,
            "tags": project_data.tags,
            "images": project_data.images,
        }

        quality_score = validator.calculate_completeness(data_dict)
        logger.info(f"质量分数: {quality_score:.2f}")

        if quality_score >= 0.6:
            logger.success(f"✅ 数据质量良好 (>= 0.6)")
        else:
            logger.warning(f"⚠️ 数据质量较低 (< 0.6)")

        return True
    else:
        logger.error("❌ 爬取失败")
        return False


def main():
    parser = argparse.ArgumentParser(description="测试Dezeen单篇文章爬取")
    parser.add_argument("--url", type=str, help="要测试的文章URL")

    args = parser.parse_args()

    success = test_dezeen_single_article(args.url)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
