"""
从Gooood分类中爬取数据

测试真实建筑项目的数据质量
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
import json


def view_category_data(category: str = "architecture", num_projects: int = 5):
    """
    从指定分类爬取数据

    Args:
        category: 分类名称 (architecture/landscape/interior/planning等)
        num_projects: 爬取项目数量
    """
    logger.info("=" * 80)
    logger.info(f"Gooood 分类数据查看器 - {category} (爬取 {num_projects} 个项目)")
    logger.info("=" * 80)

    try:
        from intelligent_project_analyzer.external_data_system.spiders.gooood_spider import GoooodSpider
        from intelligent_project_analyzer.external_data_system.utils import DataValidator

        # 创建爬虫
        spider = GoooodSpider()

        # 爬取分类列表
        logger.info(f"\n📥 开始从 '{category}' 分类爬取项目...\n")

        projects = []
        page = 1

        while len(projects) < num_projects and page <= 10:
            # 获取分类项目列表
            project_list = spider.fetch_project_list(page=page, category=category)

            if not project_list:
                logger.warning(f"⚠️ 第 {page} 页无数据")
                break

            logger.info(f"📄 第 {page} 页找到 {len(project_list)} 个项目")

            # 爬取详情
            for item in project_list:
                if len(projects) >= num_projects:
                    break

                project = spider.fetch_project_detail(item["url"])

                if project:
                    projects.append(project)
                    logger.info(f"✅ 已爬取: {project.title}")

            page += 1

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

            # 建筑师
            print("\n【建筑师】")
            if project.architects:
                for arch in project.architects:
                    print(f"  - {arch.get('name', 'N/A')}")
                    if arch.get("firm"):
                        print(f"    公司: {arch['firm']}")
            else:
                print("  无建筑师信息")

            # 位置
            print("\n【位置】")
            if project.location:
                city = project.location.get("city", "")
                country = project.location.get("country", "")
                if city or country:
                    print(f"  {city}, {country}")
                else:
                    print("  无具体位置")
            else:
                print("  无位置信息")

            # 项目参数
            print("\n【项目参数】")
            print(f"  年份: {project.year or 'N/A'}")
            if project.area_sqm:
                print(f"  面积: {project.area_sqm} m²")
            else:
                print("  面积: N/A")

            # 分类和标签
            print("\n【分类与标签】")
            if project.primary_category:
                print(f"  主分类: {project.primary_category}")
            if project.sub_categories:
                print(f"  子分类: {', '.join(project.sub_categories[:5])}")
            if project.tags:
                print(f"  标签: {', '.join(project.tags[:10])}")

            # 图片
            print("\n【图片】")
            print(f"  数量: {len(project.images)} 张")

            # 描述
            print("\n【描述】")
            desc_len = len(project.description) if project.description else 0
            print(f"  长度: {desc_len} 字符")
            if project.description and desc_len > 0:
                preview = project.description[:200]
                print(f"  预览: {preview}...")
            else:
                print("  ⚠️ 无描述内容")

            # 数据质量
            print("\n【质量评分】")
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

            quality_score = DataValidator.calculate_completeness(project_dict)

            if quality_score >= 0.8:
                rating = "🌟🌟🌟 优秀"
            elif quality_score >= 0.6:
                rating = "🌟🌟 良好"
            elif quality_score >= 0.4:
                rating = "🌟 一般"
            else:
                rating = "⚠️ 需改进"

            print(f"  分数: {quality_score:.2f}")
            print(f"  等级: {rating}")

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

        avg_images = sum(len(p.images) for p in projects) / total if total > 0 else 0

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

        print(f"\n分类: {category}")
        print(f"总项目数: {total}")
        print(f"\n字段完整率:")
        print(f"  建筑师: {with_architects}/{total} ({with_architects/total*100:.1f}%)")
        print(f"  位置: {with_location}/{total} ({with_location/total*100:.1f}%)")
        print(f"  年份: {with_year}/{total} ({with_year/total*100:.1f}%)")
        print(f"  面积: {with_area}/{total} ({with_area/total*100:.1f}%)")
        print(f"  描述(>100字): {with_description}/{total} ({with_description/total*100:.1f}%)")

        print(f"\n图片统计:")
        print(f"  平均: {avg_images:.1f} 张/项目")
        print(f"  总计: {sum(len(p.images) for p in projects)} 张")

        print(f"\n质量评分:")
        print(f"  平均分: {avg_quality:.2f}")
        if scores:
            print(f"  最高分: {max(scores):.2f}")
            print(f"  最低分: {min(scores):.2f}")

        # 质量分布
        excellent = sum(1 for s in scores if s >= 0.8)
        good = sum(1 for s in scores if 0.6 <= s < 0.8)
        fair = sum(1 for s in scores if 0.4 <= s < 0.6)
        poor = sum(1 for s in scores if s < 0.4)

        print(f"\n质量分布:")
        print(f"  优秀(≥0.8): {excellent} 个 ({excellent/total*100:.1f}%)")
        print(f"  良好(0.6-0.8): {good} 个 ({good/total*100:.1f}%)")
        print(f"  一般(0.4-0.6): {fair} 个 ({fair/total*100:.1f}%)")
        print(f"  需改进(<0.4): {poor} 个 ({poor/total*100:.1f}%)")

        logger.success(f"\n✅ 数据查看完成！")

        # 保存JSON
        output_file = Path(f"data/gooood_{category}_data.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        export_data = []
        for p in projects:
            project_dict = {
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
            }
            project_dict["quality_score"] = DataValidator.calculate_completeness(
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
            )
            export_data.append(project_dict)

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

    parser = argparse.ArgumentParser(description="从Gooood分类爬取数据")
    parser.add_argument(
        "-c", "--category", type=str, default="architecture", help="分类名称（architecture/landscape/interior/planning等）"
    )
    parser.add_argument("-n", "--num", type=int, default=10, help="爬取项目数量（默认10个）")

    args = parser.parse_args()

    # 常见分类提示
    print("\n💡 Gooood常见分类:")
    print("  - architecture (建筑)")
    print("  - landscape (景观)")
    print("  - interior (室内)")
    print("  - planning (规划)")
    print("  - residential (住宅)")
    print("  - public (公共建筑)")
    print("  - commercial (商业)")
    print("  - cultural (文化建筑)")
    print()

    success = view_category_data(args.category, args.num)
    sys.exit(0 if success else 1)
