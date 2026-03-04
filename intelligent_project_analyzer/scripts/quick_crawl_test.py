"""
快速爬取测试脚本

用于首次验证爬虫功能（小规模测试）

功能：
- 仅爬取1-2个项目
- 延迟加长到5秒（更安全）
- 打印详细调试信息

Author: AI Architecture Team
Version: v8.110.0
Date: 2026-02-17
"""

import sys
from pathlib import Path

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.crawlers import (
    ArchdailyCrawler,
    CrawlerConfig,
    GoooodCrawler,
)

# 配置日志（DEBUG级别）
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="DEBUG",
)


def test_archdaily():
    """测试Archdaily爬虫"""
    logger.info("=" * 80)
    logger.info("🧪 测试Archdaily爬虫")
    logger.info("=" * 80)

    # 配置（保守参数）
    config = CrawlerConfig(
        max_retries=3,
        request_delay=5.0,  # 5秒延迟（更安全）
        timeout=60,  # 60秒超时（更宽松）
        days_back=60,  # 最近60天（范围更大）
        min_views=0,  # 不限浏览量（测试阶段）
        max_projects=2,  # 仅2个项目
        use_proxy=False,
        use_login=False,  # 暂不登录
    )

    crawler = None
    try:
        crawler = ArchdailyCrawler(config=config, category="residential")
        projects = crawler.fetch()

        logger.success(f"\n✅ 爬取成功: {len(projects)} 个项目")

        # 打印详细信息
        for idx, project in enumerate(projects, 1):
            logger.info(f"\n项目 {idx}:")
            logger.info(f"   标题: {project.title}")
            logger.info(f"   URL: {project.url}")
            logger.info(f"   描述长度: {len(project.description)} 字符")
            logger.info(f"   建筑师: {project.architects}")
            logger.info(f"   面积: {project.area}")
            logger.info(f"   年份: {project.year}")
            logger.info(f"   位置: {project.location}")
            logger.info(f"   标签: {', '.join(project.tags[:5])}")
            logger.info(f"   图片数: {len(project.images)}")
            logger.info(f"   浏览量: {project.views}")
            logger.info(f"   发布日期: {project.publish_date}")
            logger.info(f"   描述预览: {project.description[:200]}...")

        return True

    except Exception as e:
        logger.error(f"❌ 爬取失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # 关闭Playwright浏览器（释放资源）
        if crawler:
            try:
                crawler.close()
                logger.info("🛑 Archdaily爬虫已关闭")
            except Exception:
                pass


def test_gooood():
    """测试Gooood爬虫"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 测试Gooood爬虫")
    logger.info("=" * 80)

    # 配置（保守参数）
    config = CrawlerConfig(
        max_retries=3,
        request_delay=5.0,
        timeout=60,
        days_back=60,
        min_views=0,
        max_projects=2,
        use_proxy=False,
        use_login=False,
    )

    crawler = None
    try:
        crawler = GoooodCrawler(config=config, category="residential")
        projects = crawler.fetch()

        logger.success(f"\n✅ 爬取成功: {len(projects)} 个项目")

        # 打印详细信息
        for idx, project in enumerate(projects, 1):
            logger.info(f"\n项目 {idx}:")
            logger.info(f"   标题: {project.title}")
            logger.info(f"   URL: {project.url}")
            logger.info(f"   描述长度: {len(project.description)} 字符")
            logger.info(f"   建筑师: {project.architects}")
            logger.info(f"   面积: {project.area}")
            logger.info(f"   年份: {project.year}")
            logger.info(f"   标签: {', '.join(project.tags[:5])}")
            logger.info(f"   图片数: {len(project.images)}")
            logger.info(f"   描述预览: {project.description[:200]}...")

        return True

    except Exception as e:
        logger.error(f"❌ 爬取失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # 关闭Playwright浏览器（释放资源）
        if crawler:
            try:
                crawler.close()
                logger.info("🛑 Gooood爬虫已关闭")
            except Exception:
                pass


def main():
    """主函数"""
    logger.info("🚀 快速爬取测试\n")
    logger.warning("⚠️ 测试模式:")
    logger.warning("   - 每个来源仅爬取2个项目")
    logger.warning("   - 请求延迟5秒（避免被封）")
    logger.warning("   - DEBUG日志级别（查看详细过程）")
    logger.warning("   - 不检查浏览量和发布日期")

    input("\n按回车键开始测试...")

    results = []

    # 测试Archdaily
    results.append(("Archdaily", test_archdaily()))

    # 测试Gooood
    results.append(("Gooood", test_gooood()))

    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("📊 测试结果")
    logger.info("=" * 80)

    for name, result in results:
        status = "✅ 成功" if result else "❌ 失败"
        logger.info(f"   {name}: {status}")

    success_count = sum(1 for _, result in results if result)
    logger.info(f"\n   总计: {success_count}/{len(results)} 成功")

    if success_count == 0:
        logger.error("\n❌ 所有爬虫失败，可能原因:")
        logger.info("   1. 网络连接问题")
        logger.info("   2. 网站结构已变化（选择器不匹配）")
        logger.info("   3. 被目标网站封禁（需要登录或代理）")
        logger.info("   4. 请求超时（网络太慢）")
        logger.info("\n💡 解决方案:")
        logger.info("   - 检查网络连接")
        logger.info("   - 查看上面的错误信息，更新选择器")
        logger.info("   - 配置登录（crawler_credentials.py）")
        logger.info("   - 增加超时时间（timeout参数）")

    elif success_count < len(results):
        logger.warning("\n⚠️ 部分爬虫失败")
        logger.info("   - 检查失败的爬虫错误信息")
        logger.info("   - 可能是网站结构不同")

    else:
        logger.success("\n🎉 所有爬虫测试通过！")
        logger.info("\n📝 下一步:")
        logger.info("   1. 运行完整爬取: python intelligent_project_analyzer/scripts/crawl_external_layer2.py --test")
        logger.info("   2. 配置登录: 编辑 config/crawler_credentials.py")
        logger.info("   3. 生产环境运行: python intelligent_project_analyzer/scripts/crawl_external_layer2.py")


if __name__ == "__main__":
    main()
