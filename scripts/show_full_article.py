#!/usr/bin/env python3
"""展示文章的完整爬取内容"""

import sys
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.external_data_system.spiders.dezeen_spider import DezeenSpider


def show_full_article(url: str = None):
    """展示文章完整内容"""

    if not url:
        url = "https://www.dezeen.com/2026/02/10/sou-fujimoto-baccarat-residences/"

    print("=" * 100)
    print(f"文章完整爬取结果".center(100))
    print("=" * 100)
    print(f"\n📍 URL: {url}\n")

    # 创建spider
    spider = DezeenSpider(use_playwright=True)

    # 爬取文章
    print("正在爬取...\n")
    project_data = spider.fetch_project_detail(url)

    if not project_data:
        print("❌ 爬取失败")
        return False

    # 展示详细信息
    print("=" * 100)
    print("📋 基本信息")
    print("=" * 100)
    print(f"标题: {project_data.title}")
    print(f"来源: {project_data.source}")
    print(f"来源ID: {project_data.source_id}")
    print(f"发布日期: {project_data.publish_date}")
    print(f"项目年份: {project_data.year}")

    print("\n" + "=" * 100)
    print("👥 建筑师/设计师")
    print("=" * 100)
    if project_data.architects:
        for i, arch in enumerate(project_data.architects, 1):
            print(f"  {i}. {arch}")
    else:
        print("  未提取到建筑师信息")

    print("\n" + "=" * 100)
    print("📍 位置信息")
    print("=" * 100)
    if project_data.location:
        for key, value in project_data.location.items():
            print(f"  {key}: {value}")
    else:
        print("  未提取到位置信息")

    print("\n" + "=" * 100)
    print("🏷️ 分类与标签")
    print("=" * 100)
    print(f"主分类: {project_data.primary_category or '无'}")
    if project_data.sub_categories:
        print(f"子分类: {', '.join(project_data.sub_categories)}")
    if project_data.tags:
        print(f"\n标签 (共{len(project_data.tags)}个):")
        for i, tag in enumerate(project_data.tags, 1):
            print(f"  {i:2d}. {tag}")

    print("\n" + "=" * 100)
    print("📝 完整描述内容")
    print("=" * 100)
    print(f"字符数: {len(project_data.description)}")
    print(f"段落数: {project_data.description.count(chr(10) + chr(10)) + 1}")
    print("\n" + "-" * 100)
    print(project_data.description)
    print("-" * 100)

    print("\n" + "=" * 100)
    print("🖼️ 图片列表")
    print("=" * 100)
    print(f"图片总数: {len(project_data.images)}")
    if project_data.images:
        for i, img_url in enumerate(project_data.images, 1):
            print(f"  {i:2d}. {img_url}")

    # 质量评估
    print("\n" + "=" * 100)
    print("⭐ 质量评估")
    print("=" * 100)

    from intelligent_project_analyzer.external_data_system.utils.data_processing import DataValidator

    validator = DataValidator()

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

    print(f"完整度评分: {quality_score:.2f} / 1.0")

    # 评分等级
    if quality_score >= 0.8:
        grade = "优秀 ⭐⭐⭐⭐⭐"
    elif quality_score >= 0.6:
        grade = "良好 ⭐⭐⭐⭐"
    elif quality_score >= 0.4:
        grade = "一般 ⭐⭐⭐"
    else:
        grade = "较差 ⭐⭐"

    print(f"评级: {grade}")

    # 详细评分
    print("\n评分详情:")
    print(f"  ✅ 标题: {len(project_data.title)} 字符")
    print(f"  ✅ 描述: {len(project_data.description)} 字符")
    print(f"  {'✅' if project_data.architects else '❌'} 建筑师: {len(project_data.architects)} 个")
    print(f"  {'✅' if project_data.location else '❌'} 位置: {'有' if project_data.location else '无'}")
    print(f"  {'✅' if project_data.year else '❌'} 年份: {project_data.year or '无'}")
    print(f"  ✅ 图片: {len(project_data.images)} 张")
    print(f"  ✅ 标签: {len(project_data.tags)} 个")

    print("\n" + "=" * 100)
    print("完成！")
    print("=" * 100)

    return True


def main():
    parser = argparse.ArgumentParser(description="展示文章完整内容")
    parser.add_argument("--url", type=str, help="文章URL")

    args = parser.parse_args()

    success = show_full_article(args.url)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
