"""
爬虫完整性测试

测试所有爬虫的数据完整性和稳定性
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def test_archdaily_spider():
    """测试 Archdaily 爬虫"""
    logger.info("=" * 60)
    logger.info("测试 Archdaily 爬虫")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.external_data_system.spiders import ArchdailyCrawler
        from intelligent_project_analyzer.external_data_system.utils import DataValidator

        crawler = ArchdailyCrawler()

        # 测试爬取前3个项目
        logger.info("📥 爬取前3个项目进行测试...")
        projects = crawler.crawl_batch(max_projects=3, start_page=1)

        if not projects:
            logger.error("❌ 未能爬取任何项目")
            return False

        logger.success(f"✅ 成功爬取 {len(projects)} 个项目")

        # 验证数据完整性
        for i, project in enumerate(projects, 1):
            logger.info(f"\n--- 项目 {i}: {project.title} ---")

            # 转为字典
            project_dict = {
                "title": project.title,
                "description": project.description,
                "source": project.source,
                "source_id": project.source_id,
                "url": project.url,
                "architects": project.architects,
                "location": project.location,
                "year": project.year,
                "area_sqm": project.area_sqm,
                "images": project.images,
                "tags": project.tags,
                "categories": [project.primary_category] if project.primary_category else [],
            }

            # 验证
            is_valid, errors = DataValidator.validate_project(project_dict)
            score = DataValidator.calculate_completeness(project_dict)

            logger.info(f"URL: {project.url}")
            logger.info(f"建筑师: {project.architects}")
            logger.info(f"位置: {project.location}")
            logger.info(f"年份: {project.year}")
            logger.info(f"面积: {project.area_sqm}㎡" if project.area_sqm else "面积: N/A")
            logger.info(f"图片数: {len(project.images)}")
            logger.info(f"分类: {project.primary_category}")
            logger.info(f"标签: {project.tags}")
            logger.info(f"质量分数: {score:.2f}")

            if not is_valid:
                logger.warning(f"验证问题: {errors}")

            # 检查关键字段
            assert project.title, "缺少标题"
            assert project.url, "缺少URL"
            assert project.description, "缺少描述"
            assert len(project.images) >= 3, f"图片数不足3张: {len(project.images)}"
            assert score >= 0.6, f"质量分数过低: {score}"

        logger.success("\n✅ Archdaily 爬虫测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ Archdaily 爬虫测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_gooood_spider():
    """测试 Gooood 爬虫"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 Gooood 爬虫")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.external_data_system.spiders import GoooodCrawler
        from intelligent_project_analyzer.external_data_system.utils import DataValidator

        crawler = GoooodCrawler()

        # 测试爬取前3个项目
        logger.info("📥 爬取前3个项目进行测试...")
        projects = crawler.crawl_batch(max_projects=3, start_page=1)

        if not projects:
            logger.error("❌ 未能爬取任何项目")
            return False

        logger.success(f"✅ 成功爬取 {len(projects)} 个项目")

        # 验证数据完整性
        for i, project in enumerate(projects, 1):
            logger.info(f"\n--- 项目 {i}: {project.title} ---")

            project_dict = {
                "title": project.title,
                "description": project.description,
                "source": project.source,
                "source_id": project.source_id,
                "url": project.url,
                "architects": project.architects,
                "location": project.location,
                "year": project.year,
                "area_sqm": project.area_sqm,
                "images": project.images,
                "tags": project.tags,
                "categories": [project.primary_category] if project.primary_category else [],
            }

            is_valid, errors = DataValidator.validate_project(project_dict)
            score = DataValidator.calculate_completeness(project_dict)

            logger.info(f"URL: {project.url}")
            logger.info(f"建筑师: {project.architects}")
            logger.info(f"位置: {project.location}")
            logger.info(f"年份: {project.year}")
            logger.info(f"图片数: {len(project.images)}")
            logger.info(f"质量分数: {score:.2f}")

            if not is_valid:
                logger.warning(f"验证问题: {errors}")

            # 检查关键字段
            assert project.title, "缺少标题"
            assert project.url, "缺少URL"
            assert len(project.images) >= 2, f"图片数不足2张: {len(project.images)}"

        logger.success("\n✅ Gooood 爬虫测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ Gooood 爬虫测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_rate_limiter():
    """测试频率控制"""
    logger.info("\n" + "=" * 60)
    logger.info("测试频率控制")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.external_data_system.utils import get_rate_limiter
        import time

        limiter = get_rate_limiter("test")

        logger.info("⏱️ 测试5次请求...")
        start_time = time.time()

        for i in range(5):
            limiter.wait()
            logger.info(f"  请求 {i+1} (耗时: {time.time() - start_time:.1f}s)")

        elapsed = time.time() - start_time
        logger.info(f"总耗时: {elapsed:.1f}s")

        # 检查平均间隔（应该在3-5秒之间）
        avg_delay = elapsed / 4  # 4个间隔
        assert 2.5 < avg_delay < 6, f"平均延迟异常: {avg_delay:.1f}s"

        logger.success("✅ 频率控制测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 频率控制测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 开始爬虫完整性测试")

    results = {
        "Archdaily爬虫": test_archdaily_spider(),
        "Gooood爬虫": test_gooood_spider(),
        "频率控制": test_rate_limiter(),
    }

    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    for name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{name}: {status}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    if passed == total:
        logger.success(f"\n🎉 所有测试通过！({passed}/{total})")
        logger.info("\n📌 下一步:")
        logger.info("  1. 运行首次完整爬取: python scripts/crawl_all_sources.py")
        logger.info(
            "  2. 启动 Celery 定时任务: celery -A intelligent_project_analyzer.external_data_system.celery_app worker -l info"
        )
        logger.info(
            "  3. 启动 Celery Beat: celery -A intelligent_project_analyzer.external_data_system.celery_app beat -l info"
        )
        return 0
    else:
        logger.error(f"\n⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
