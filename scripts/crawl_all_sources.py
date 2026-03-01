"""
启动完整爬取（首次冷启动）

按策略爬取所有网站的数据
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from datetime import datetime


def crawl_archdaily(max_projects: int = 10000):
    """
    爬取 Archdaily

    Args:
        max_projects: 最大项目数（默认10,000）
    """
    logger.info("=" * 60)
    logger.info(f"Archdaily 完整爬取 (目标: {max_projects} 个项目)")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.external_data_system.spiders import ArchdailyCrawler
        from intelligent_project_analyzer.external_data_system import get_external_db

        crawler = ArchdailyCrawler()
        db = get_external_db()

        start_time = datetime.now()
        logger.info(f"开始时间: {start_time}")

        # 分批爬取（每批50个）
        batch_size = 50
        total_saved = 0

        for batch_num in range(max_projects // batch_size + 1):
            start_page = batch_num + 1
            logger.info(f"\n📦 批次 {batch_num + 1} (页码: {start_page})")

            # 爬取一批
            projects = crawler.crawl_batch(max_projects=batch_size, start_page=start_page)

            if not projects:
                logger.warning("无更多项目，停止爬取")
                break

            # 保存到数据库
            saved = save_projects_to_db(db, projects)
            total_saved += saved

            logger.info(f"已保存: {saved}/{len(projects)} 个项目")
            logger.info(f"累计进度: {total_saved}/{max_projects}")

            if total_saved >= max_projects:
                logger.info("达到目标数量，停止爬取")
                break

        elapsed = datetime.now() - start_time
        logger.success(f"\n✅ Archdaily 爬取完成！")
        logger.info(f"总项目数: {total_saved}")
        logger.info(f"总耗时: {elapsed}")

        return total_saved

    except Exception as e:
        logger.error(f"❌ Archdaily 爬取失败: {e}")
        import traceback

        traceback.print_exc()
        return 0


def crawl_gooood(max_projects: int = 5000):
    """
    爬取 Gooood

    Args:
        max_projects: 最大项目数（默认5,000）
    """
    logger.info("\n" + "=" * 60)
    logger.info(f"Gooood 完整爬取 (目标: {max_projects} 个项目)")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.external_data_system.spiders import GoooodCrawler
        from intelligent_project_analyzer.external_data_system import get_external_db

        crawler = GoooodCrawler()
        db = get_external_db()

        start_time = datetime.now()
        logger.info(f"开始时间: {start_time}")

        # 分批爬取
        batch_size = 30
        total_saved = 0

        for batch_num in range(max_projects // batch_size + 1):
            start_page = batch_num + 1
            logger.info(f"\n📦 批次 {batch_num + 1} (页码: {start_page})")

            projects = crawler.crawl_batch(max_projects=batch_size, start_page=start_page)

            if not projects:
                break

            saved = save_projects_to_db(db, projects)
            total_saved += saved

            logger.info(f"已保存: {saved}/{len(projects)} 个项目")
            logger.info(f"累计进度: {total_saved}/{max_projects}")

            if total_saved >= max_projects:
                break

        elapsed = datetime.now() - start_time
        logger.success(f"\n✅ Gooood 爬取完成！")
        logger.info(f"总项目数: {total_saved}")
        logger.info(f"总耗时: {elapsed}")

        return total_saved

    except Exception as e:
        logger.error(f"❌ Gooood 爬取失败: {e}")
        import traceback

        traceback.print_exc()
        return 0


def save_projects_to_db(db, projects):
    """保存项目到数据库"""
    from intelligent_project_analyzer.external_data_system.models import ExternalProject
    from intelligent_project_analyzer.external_data_system.utils import DataValidator

    saved_count = 0

    with db.get_session() as session:
        for project_data in projects:
            try:
                # 检查是否已存在
                existing = session.query(ExternalProject).filter(ExternalProject.url == project_data.url).first()

                if existing:
                    logger.debug(f"跳过重复: {project_data.title}")
                    continue

                # 计算质量分数
                project_dict = {
                    "title": project_data.title,
                    "description": project_data.description,
                    "source": project_data.source,
                    "source_id": project_data.source_id,
                    "url": project_data.url,
                    "architects": project_data.architects,
                    "location": project_data.location,
                    "year": project_data.year,
                    "area_sqm": project_data.area_sqm,
                    "images": project_data.images,
                    "tags": project_data.tags,
                    "categories": [project_data.primary_category] if project_data.primary_category else [],
                }

                quality_score = DataValidator.calculate_completeness(project_dict)

                # 创建项目
                project = ExternalProject(
                    source=project_data.source,
                    source_id=project_data.source_id,
                    url=project_data.url,
                    title=project_data.title,
                    description=project_data.description,
                    architects=project_data.architects,
                    location=project_data.location,
                    year=project_data.year,
                    area_sqm=project_data.area_sqm,
                    primary_category=project_data.primary_category,
                    sub_categories=project_data.sub_categories,
                    tags=project_data.tags,
                    quality_score=quality_score,
                )

                session.add(project)
                session.commit()

                saved_count += 1
                logger.debug(f"✅ {project_data.title} (质量: {quality_score:.2f})")

            except Exception as e:
                logger.error(f"保存失败: {e}")
                session.rollback()
                continue

    return saved_count


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="完整爬取所有网站")
    parser.add_argument("--archdaily", type=int, default=1000, help="Archdaily 目标数量")
    parser.add_argument("--gooood", type=int, default=500, help="Gooood 目标数量")
    parser.add_argument("--skip-archdaily", action="store_true", help="跳过 Archdaily")
    parser.add_argument("--skip-gooood", action="store_true", help="跳过 Gooood")

    args = parser.parse_args()

    logger.info("🚀 开始完整爬取任务")
    logger.info("=" * 60)
    logger.info("根据 CRAWLER_STRATEGY.md 策略执行")
    logger.info("=" * 60)

    results = {}

    # Archdaily
    if not args.skip_archdaily:
        results["Archdaily"] = crawl_archdaily(args.archdaily)

    # Gooood
    if not args.skip_gooood:
        results["Gooood"] = crawl_gooood(args.gooood)

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("爬取结果汇总")
    logger.info("=" * 60)

    total = 0
    for source, count in results.items():
        logger.info(f"{source}: {count} 个项目")
        total += count

    logger.success(f"\n🎉 完整爬取完成！共 {total} 个项目")
    logger.info("\n📌 下一步:")
    logger.info("  1. 查看数据质量: python scripts/monitor_data_quality.py")
    logger.info("  2. 生成向量索引: 运行 batch_generate_embeddings_task")
    logger.info("  3. 配置数据库索引: python scripts/setup_database_indexes.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
