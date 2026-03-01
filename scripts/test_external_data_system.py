"""
外部数据系统测试脚本

测试完整的爬取→存储→查询流程
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from intelligent_project_analyzer.external_data_system import get_spider_manager
from intelligent_project_analyzer.external_data_system.models import get_external_db, ExternalProject


def test_spider_registration():
    """测试爬虫注册"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 测试1: 爬虫注册")
    logger.info("=" * 80)

    manager = get_spider_manager()
    logger.info(f"✅ 已注册爬虫: {list(manager.spiders.keys())}")

    return len(manager.spiders) > 0


def test_crawl_single_project():
    """测试爬取单个项目"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 测试2: 爬取单个项目")
    logger.info("=" * 80)

    manager = get_spider_manager()
    spider = manager.get_spider("archdaily")

    if not spider:
        logger.error("❌ 爬虫未找到")
        return False

    # 测试URL
    test_url = "https://www.archdaily.cn/cn/1016091/tan-na-ta-pu-kuang-jia-hua-yuan-rad-plus-ar"

    logger.info(f"🔍 测试URL: {test_url}")

    with spider:
        project_data = spider.parse_project_page(test_url)

        if project_data:
            logger.success(f"✅ 项目解析成功:")
            logger.info(f"   标题: {project_data.title}")
            logger.info(f"   描述长度: {len(project_data.description or '')} 字符")
            logger.info(f"   建筑师: {project_data.architects}")
            logger.info(f"   图片数: {len(project_data.images)}")
            logger.info(f"   标签数: {len(project_data.tags)}")
            logger.info(f"   质量验证: {'✅ 通过' if project_data.validate() else '❌ 失败'}")

            # 存储到数据库
            from intelligent_project_analyzer.external_data_system.models import ExternalProject, ExternalProjectImage
            from datetime import datetime

            db = get_external_db()
            with db.get_session() as session:
                # 检查是否已存在
                existing = session.query(ExternalProject).filter(ExternalProject.url == project_data.url).first()

                if existing:
                    logger.info(f"   数据库记录: 已存在 (ID: {existing.id})")
                else:
                    # 创建新记录
                    project = ExternalProject(
                        source=project_data.source,
                        source_id=project_data.source_id,
                        url=project_data.url,
                        title=project_data.title,
                        description=project_data.description,
                        architects=project_data.architects,
                        location=project_data.location,
                        area_sqm=project_data.area_sqm,
                        year=project_data.year,
                        primary_category=project_data.primary_category,
                        sub_categories=project_data.sub_categories,
                        tags=project_data.tags,
                        views=project_data.views,
                        publish_date=project_data.publish_date,
                        crawled_at=datetime.now(),
                        quality_score=0.85,  # 临时评分
                    )
                    session.add(project)
                    session.flush()

                    # 添加图片
                    for idx, img in enumerate(project_data.images[:5]):  # 只保存前5张
                        image = ExternalProjectImage(
                            project_id=project.id,
                            url=img.get("url"),
                            caption=img.get("caption"),
                            order_index=idx,
                            is_cover=(idx == 0),
                        )
                        session.add(image)

                    session.commit()
                    logger.success(f"   ✅ 已保存到数据库 (ID: {project.id})")

            return True
        else:
            logger.error("❌ 项目解析失败")
            return False


def test_crawl_category():
    """测试爬取分类（少量页面）"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 测试3: 爬取分类")
    logger.info("=" * 80)

    manager = get_spider_manager()
    spider = manager.get_spider("archdaily")

    if not spider:
        logger.error("❌ 爬虫未找到")
        return False

    # 测试居住建筑分类（只爬1页）
    category_url = "https://www.archdaily.cn/cn/search/projects/categories/housing"

    logger.info(f"🔍 测试分类: {category_url}")

    with spider:
        project_urls = spider.crawl_category(category_url, max_pages=1)

        logger.success(f"✅ 找到 {len(project_urls)} 个项目URL")

        if project_urls:
            logger.info("   示例URL:")
            for url in project_urls[:3]:
                logger.info(f"   - {url}")

        return len(project_urls) > 0


def test_database_query():
    """测试数据库查询"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 测试4: 数据库查询")
    logger.info("=" * 80)

    db = get_external_db()

    with db.get_session() as session:
        # 统计数据
        total_count = session.query(ExternalProject).count()
        logger.info(f"📊 总项目数: {total_count}")

        if total_count > 0:
            # 查询最新的5个项目
            recent_projects = session.query(ExternalProject).order_by(ExternalProject.crawled_at.desc()).limit(5).all()

            logger.info("📝 最近的项目:")
            for p in recent_projects:
                logger.info(f"   - [{p.source}] {p.title[:50]}... ({p.year or 'N/A'})")

            # 按数据源统计
            from sqlalchemy import func

            source_stats = (
                session.query(
                    ExternalProject.source,
                    func.count(ExternalProject.id).label("count"),
                    func.avg(ExternalProject.quality_score).label("avg_quality"),
                )
                .group_by(ExternalProject.source)
                .all()
            )

            logger.info("📊 数据源统计:")
            for stat in source_stats:
                logger.info(f"   - {stat.source}: {stat.count} 个项目, 平均质量: {stat.avg_quality:.2f}")

        return True


def test_spider_manager():
    """测试SpiderManager完整流程"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 测试5: SpiderManager同步（小规模）")
    logger.info("=" * 80)

    manager = get_spider_manager()

    # 同步居住建筑分类（只爬1页，最多3个项目）
    logger.info("🚀 开始小规模同步测试...")

    # 临时修改限制
    success = manager.sync_source(
        source="archdaily",
        category="居住建筑",
        max_pages=1,
    )

    if success:
        logger.success("✅ 同步测试成功")

        # 查看同步历史
        history = manager.get_sync_history(limit=1)
        if history:
            last_sync = history[0]
            logger.info(f"📊 同步统计:")
            logger.info(f"   - 总计: {last_sync['projects_total']} 个")
            logger.info(f"   - 新增: {last_sync['projects_new']} 个")
            logger.info(f"   - 更新: {last_sync['projects_updated']} 个")
            logger.info(f"   - 失败: {last_sync['projects_failed']} 个")

        return True
    else:
        logger.error("❌ 同步测试失败")
        return False


def main():
    """运行所有测试"""
    logger.info("🚀 外部数据系统完整测试")
    logger.info(f"时间: {__import__('datetime').datetime.now()}")

    tests = [
        ("爬虫注册", test_spider_registration),
        ("爬取单个项目", test_crawl_single_project),
        ("爬取分类", test_crawl_category),
        ("数据库查询", test_database_query),
        # ("SpiderManager同步", test_spider_manager),  # 可选（耗时较长）
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"❌ 测试失败: {test_name} - {e}")
            logger.exception(e)
            results.append((test_name, False))

    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("📊 测试结果总结")
    logger.info("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"  {status} - {test_name}")

    logger.info("")
    logger.info(f"总计: {passed}/{total} 个测试通过 ({passed/total*100:.1f}%)")

    if passed == total:
        logger.success("\n🎉 所有测试通过！外部数据系统运行正常。")
        logger.info("📝 下一步:")
        logger.info("   1. 运行大规模爬取: python scripts/crawl_all_categories.py")
        logger.info("   2. 启动后端API: uvicorn intelligent_project_analyzer.api.server:app --reload")
        logger.info("   3. 访问监控页面: http://localhost:3000/admin/external-data")
        return 0
    else:
        logger.error("\n⚠️ 部分测试失败，请检查日志。")
        return 1


if __name__ == "__main__":
    exit(main())
