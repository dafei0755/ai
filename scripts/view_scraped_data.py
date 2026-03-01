"""
查看爬取到的数据

展示Gooood爬虫的详细爬取结果
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
import json


def view_gooood_data(num_projects: int = 5):
    """
    查看Gooood爬取的数据

    Args:
        num_projects: 爬取项目数量
    """
    logger.info("=" * 80)
    logger.info(f"Gooood 数据查看器 - 爬取 {num_projects} 个项目")
    logger.info("=" * 80)

    try:
        from intelligent_project_analyzer.external_data_system.spiders.gooood_spider import GoooodCrawler
        from intelligent_project_analyzer.external_data_system.utils import DataValidator

        # 创建爬虫
        crawler = GoooodCrawler()

        # 爬取项目
        logger.info(f"\n📥 开始爬取 {num_projects} 个项目...\n")
        projects = crawler.crawl_batch(max_projects=num_projects, start_page=1)

        if not projects:
            logger.error("❌ 未能爬取到任何项目")
            return False

        logger.success(f"\n✅ 成功爬取 {len(projects)} 个项目\n")

        # 逐个展示详细数据
        for i, project in enumerate(projects, 1):
            logger.info("=" * 80)
            logger.info(f"项目 {i}/{len(projects)}")
            logger.info("=" * 80)

            # 基础信息
            print("\n【基础信息】")
            print(f"  标题: {project.title}")
            print(f"  URL: {project.url}")
            print(f"  来源: {project.source}")
            print(f"  来源ID: {project.source_id}")

            # 建筑师
            print("\n【建筑师】")
            if project.architects:
                for arch in project.architects:
                    print(f"  - 名称: {arch.get('name', 'N/A')}")
                    if arch.get("firm"):
                        print(f"    公司: {arch['firm']}")
            else:
                print("  无建筑师信息")

            # 位置
            print("\n【位置】")
            if project.location:
                city = project.location.get("city", "N/A")
                country = project.location.get("country", "N/A")
                print(f"  城市: {city}")
                print(f"  国家: {country}")
            else:
                print("  无位置信息")

            # 项目参数
            print("\n【项目参数】")
            print(f"  年份: {project.year or 'N/A'}")
            print(f"  面积: {project.area_sqm or 'N/A'} m²" if project.area_sqm else "  面积: N/A")

            # 分类和标签
            print("\n【分类与标签】")
            print(f"  主分类: {project.primary_category or 'N/A'}")
            if project.sub_categories:
                print(f"  子分类: {', '.join(project.sub_categories[:5])}")
            if project.tags:
                print(f"  标签: {', '.join(project.tags[:10])}")

            # 图片
            print("\n【图片】")
            print(f"  图片数量: {len(project.images)}")
            if project.images:
                print("  图片URL预览（前5张）:")
                for j, img in enumerate(project.images[:5], 1):
                    if isinstance(img, dict):
                        url = img.get("url", str(img))
                        caption = img.get("caption", "")
                        print(f"    {j}. {url}")
                        if caption:
                            print(f"       说明: {caption}")
                    else:
                        print(f"    {j}. {img}")

            # 描述
            print("\n【描述】")
            desc_len = len(project.description) if project.description else 0
            print(f"  长度: {desc_len} 字符")
            if project.description and desc_len > 0:
                # 显示前500字符
                preview = project.description[:500]
                print(f"  内容预览:")
                print(f"  {preview}")
                if desc_len > 500:
                    print(f"  ... (还有 {desc_len - 500} 字符)")
            else:
                print("  无描述内容")

            # 数据质量评估
            print("\n【数据质量】")
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
            quality_score = DataValidator.calculate_completeness(project_dict)

            print(f"  验证状态: {'✅ 通过' if is_valid else '⚠️ 警告'}")
            if not is_valid:
                print(f"  问题: {', '.join(errors)}")
            print(f"  完整度评分: {quality_score:.2f}")

            # 评级
            if quality_score >= 0.8:
                rating = "🌟🌟🌟 优秀"
            elif quality_score >= 0.6:
                rating = "🌟🌟 良好"
            elif quality_score >= 0.4:
                rating = "🌟 一般"
            else:
                rating = "⚠️ 需改进"
            print(f"  质量等级: {rating}")

            # 分隔符
            print("\n" + "-" * 80 + "\n")

        # 统计摘要
        logger.info("=" * 80)
        logger.info("数据统计摘要")
        logger.info("=" * 80)

        total = len(projects)
        with_architects = sum(1 for p in projects if p.architects)
        with_location = sum(1 for p in projects if p.location)
        with_year = sum(1 for p in projects if p.year)
        with_area = sum(1 for p in projects if p.area_sqm)
        with_description = sum(1 for p in projects if p.description and len(p.description) > 100)

        avg_images = sum(len(p.images) for p in projects) / total

        scores = []
        for p in projects:
            project_dict = {
                "title": p.title,
                "description": p.description,
                "source": p.source,
                "source_id": p.source_id,
                "url": p.url,
                "architects": p.architects,
                "location": p.location,
                "year": p.year,
                "area_sqm": p.area_sqm,
                "images": p.images,
                "tags": p.tags,
                "categories": [p.primary_category] if p.primary_category else [],
            }
            scores.append(DataValidator.calculate_completeness(project_dict))

        avg_quality = sum(scores) / total if scores else 0

        print(f"\n总项目数: {total}")
        print(f"\n字段完整率:")
        print(f"  建筑师: {with_architects}/{total} ({with_architects/total*100:.1f}%)")
        print(f"  位置: {with_location}/{total} ({with_location/total*100:.1f}%)")
        print(f"  年份: {with_year}/{total} ({with_year/total*100:.1f}%)")
        print(f"  面积: {with_area}/{total} ({with_area/total*100:.1f}%)")
        print(f"  描述(>100字): {with_description}/{total} ({with_description/total*100:.1f}%)")

        print(f"\n图片统计:")
        print(f"  平均图片数: {avg_images:.1f} 张/项目")
        print(f"  总图片数: {sum(len(p.images) for p in projects)} 张")

        print(f"\n质量评分:")
        print(f"  平均分: {avg_quality:.2f}")
        print(f"  最高分: {max(scores):.2f}")
        print(f"  最低分: {min(scores):.2f}")

        # 质量分布
        excellent = sum(1 for s in scores if s >= 0.8)
        good = sum(1 for s in scores if 0.6 <= s < 0.8)
        fair = sum(1 for s in scores if 0.4 <= s < 0.6)
        poor = sum(1 for s in scores if s < 0.4)

        print(f"\n质量分布:")
        print(f"  优秀(≥0.8): {excellent} 个")
        print(f"  良好(0.6-0.8): {good} 个")
        print(f"  一般(0.4-0.6): {fair} 个")
        print(f"  需改进(<0.4): {poor} 个")

        logger.success(f"\n✅ 数据查看完成！")

        # 保存JSON
        output_file = Path("data/gooood_sample_data.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        export_data = [
            {
                "title": p.title,
                "url": p.url,
                "source": p.source,
                "source_id": p.source_id,
                "architects": p.architects,
                "location": p.location,
                "year": p.year,
                "area_sqm": p.area_sqm,
                "primary_category": p.primary_category,
                "sub_categories": p.sub_categories,
                "tags": p.tags,
                "images": p.images,
                "description": p.description,
                "quality_score": DataValidator.calculate_completeness(
                    {
                        "title": p.title,
                        "description": p.description,
                        "source": p.source,
                        "source_id": p.source_id,
                        "url": p.url,
                        "architects": p.architects,
                        "location": p.location,
                        "year": p.year,
                        "area_sqm": p.area_sqm,
                        "images": p.images,
                        "tags": p.tags,
                        "categories": [p.primary_category] if p.primary_category else [],
                    }
                ),
            }
            for p in projects
        ]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"\n📄 数据已保存到: {output_file}")

        return True

    except Exception as e:
        logger.error(f"❌ 查看数据失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="查看Gooood爬取的数据")
    parser.add_argument("-n", "--num", type=int, default=5, help="爬取项目数量（默认5个）")

    args = parser.parse_args()

    success = view_gooood_data(args.num)
    sys.exit(0 if success else 1)
