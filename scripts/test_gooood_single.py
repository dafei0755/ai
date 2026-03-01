"""
测试 Gooood 爬虫 - 单篇文章
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
import json


def test_gooood_single():
    """测试爬取一篇 Gooood 文章"""

    logger.info("=" * 60)
    logger.info("Gooood 单篇文章测试")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.external_data_system.spiders.gooood_spider import GoooodCrawler
        from intelligent_project_analyzer.external_data_system.utils import DataValidator

        # 创建爬虫
        crawler = GoooodCrawler()

        # 爬取1个项目
        logger.info("\n📥 开始爬取...")
        projects = crawler.crawl_batch(max_projects=1, start_page=1)

        if not projects:
            logger.error("❌ 未能爬取到任何项目")
            return False

        project = projects[0]

        # 显示结果
        logger.info("\n" + "=" * 60)
        logger.info("爬取结果")
        logger.info("=" * 60)

        logger.info(f"\n📝 标题: {project.title}")
        logger.info(f"🔗 URL: {project.url}")
        logger.info(f"🏢 来源: {project.source}")
        logger.info(f"🆔 来源ID: {project.source_id}")

        logger.info(f"\n👨‍🎨 建筑师:")
        for arch in project.architects:
            logger.info(f"  - {arch['name']}")

        if project.location:
            logger.info(f"\n📍 位置:")
            logger.info(f"  城市: {project.location.get('city', 'N/A')}")
            logger.info(f"  国家: {project.location.get('country', 'N/A')}")

        if project.year:
            logger.info(f"\n📅 年份: {project.year}")

        if project.area_sqm:
            logger.info(f"\n📏 面积: {project.area_sqm} m²")

        logger.info(f"\n📷 图片数量: {len(project.images)}")
        if project.images:
            logger.info(f"  预览前3张:")
            for i, img in enumerate(project.images[:3], 1):
                logger.info(f"    {i}. {img[:80]}...")

        if project.primary_category:
            logger.info(f"\n🏷️ 主要分类: {project.primary_category}")

        if project.sub_categories:
            logger.info(f"📂 子分类: {', '.join(project.sub_categories[:5])}")

        if project.tags:
            logger.info(f"🔖 标签: {', '.join(project.tags[:10])}")

        logger.info(f"\n📄 描述长度: {len(project.description)} 字符")
        logger.info(f"描述预览:\n{project.description[:300]}...")

        # 验证数据质量
        logger.info("\n" + "=" * 60)
        logger.info("数据质量验证")
        logger.info("=" * 60)

        # 转换为字典进行验证
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

        if is_valid:
            logger.success("✅ 数据验证通过")
        else:
            logger.warning(f"⚠️ 验证警告: {', '.join(errors)}")

        # 计算完整度分数
        quality_score = DataValidator.calculate_completeness(project_dict)
        logger.info(f"\n⭐ 质量分数: {quality_score:.2f}")

        # 评分标准
        if quality_score >= 0.8:
            logger.success("🎉 优秀质量！")
        elif quality_score >= 0.6:
            logger.info("👍 良好质量")
        else:
            logger.warning("⚠️ 质量需改进")

        # 数据结构详情
        logger.info("\n" + "=" * 60)
        logger.info("完整数据结构")
        logger.info("=" * 60)

        print(
            json.dumps(
                {
                    "title": project.title,
                    "url": project.url,
                    "source": project.source,
                    "source_id": project.source_id,
                    "architects": project.architects,
                    "location": project.location,
                    "year": project.year,
                    "area_sqm": project.area_sqm,
                    "primary_category": project.primary_category,
                    "sub_categories": project.sub_categories,
                    "tags": project.tags,
                    "image_count": len(project.images),
                    "description_length": len(project.description),
                    "quality_score": quality_score,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        return True

    except ImportError as e:
        logger.error(f"❌ 导入错误: {e}")
        logger.error("请确保已安装所有依赖: pip install -r requirements.txt")
        return False

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_gooood_single()

    if success:
        logger.success("\n✅ Gooood 爬虫测试成功！")
        logger.info("\n📌 下一步:")
        logger.info("  1. 爬取更多项目: python scripts/crawl_all_sources.py --gooood 100")
        logger.info("  2. 测试所有爬虫: python scripts/test_all_spiders.py")
        sys.exit(0)
    else:
        logger.error("\n❌ 测试失败，请检查错误信息")
        sys.exit(1)
