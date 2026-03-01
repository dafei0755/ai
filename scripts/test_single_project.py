"""
测试：爬取单个项目的完整内容
查看数据结构和未来用途
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_project_analyzer.crawlers.archdaily_crawler import ArchdailyCrawler
from loguru import logger


def test_single_project_crawl():
    """测试爬取单个项目"""

    # 从之前的测试结果中选一个项目
    test_result_file = Path("test_category_crawl_result.json")

    if test_result_file.exists():
        with open(test_result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            project_url = data["projects"][0]  # 第一个项目
    else:
        # 备用URL
        project_url = "https://www.archdaily.cn/cn/1037243/yi-dan-shi-san-ji-nian-guan-itm-yooehwa-architects"

    logger.info("\n" + "=" * 70)
    logger.info("🧪 测试：爬取单个项目的完整内容")
    logger.info("=" * 70)
    logger.info(f"\n📍 项目URL: {project_url}")

    # 创建爬虫
    crawler = ArchdailyCrawler()

    # 爬取项目详情
    logger.info("\n🔄 开始爬取...")
    project_data = crawler.parse_project_page(project_url)

    if not project_data:
        logger.error("❌ 爬取失败")
        return

    # 显示数据结构
    logger.info("\n✅ 爬取成功！")
    logger.info("\n" + "=" * 70)
    logger.info("📊 数据结构预览")
    logger.info("=" * 70)

    # 基本信息
    logger.info(f"\n📌 基本信息:")
    logger.info(f"  标题: {project_data.title}")
    logger.info(f"  URL: {project_data.url}")
    logger.info(f"  来源: {project_data.source}")

    # 元数据
    logger.info(f"\n🏗️  项目元数据:")
    logger.info(f"  建筑师: {project_data.architects or '未知'}")
    logger.info(f"  面积: {project_data.area or '未知'}")
    logger.info(f"  年份: {project_data.year or '未知'}")
    logger.info(f"  位置: {project_data.location or '未知'}")

    # 内容
    logger.info(f"\n📝 项目描述:")
    description = project_data.description or ""
    if description:
        preview = description[:200] + "..." if len(description) > 200 else description
        logger.info(f"  {preview}")
        logger.info(f"  (完整长度: {len(description)} 字符)")
    else:
        logger.info("  (无描述)")

    # 图片
    logger.info(f"\n🖼️  项目图片:")
    logger.info(f"  图片数量: {len(project_data.images)}")
    if project_data.images:
        logger.info(f"  示例:")
        for i, img in enumerate(project_data.images[:3], 1):
            logger.info(f"    {i}. {img}")

    # 标签
    logger.info(f"\n🏷️  项目标签:")
    logger.info(f"  标签数量: {len(project_data.tags)}")
    if project_data.tags:
        logger.info(f"  标签: {', '.join(project_data.tags[:10])}")

    # 其他字段
    logger.info(f"\n📈 其他信息:")
    logger.info(f"  浏览量: {project_data.views or 0}")
    logger.info(f"  发布日期: {project_data.publish_date or '未知'}")

    # 保存完整数据
    output_file = "sample_project_data.json"
    project_dict = {
        "url": project_data.url,
        "title": project_data.title,
        "source": project_data.source,
        "architects": project_data.architects,
        "area": project_data.area,
        "year": project_data.year,
        "location": project_data.location,
        "description": project_data.description,
        "description_length": len(project_data.description or ""),
        "images": project_data.images,
        "image_count": len(project_data.images),
        "tags": project_data.tags,
        "tag_count": len(project_data.tags),
        "views": project_data.views,
        "publish_date": str(project_data.publish_date) if project_data.publish_date else None,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(project_dict, f, ensure_ascii=False, indent=2)

    logger.info(f"\n💾 完整数据已保存到: {output_file}")

    # 说明未来用途
    print("\n" + "=" * 70)
    print("🎯 数据在LangGraph资料库中的用途")
    print("=" * 70)

    print("\n1. 📚 文本语义搜索：")
    print("   - description（项目描述）→ 向量化存储")
    print("   - 用户查询 → 匹配最相关的项目")
    print("   - 示例：'可持续发展的图书馆' → 返回相关描述")

    print("\n2. 🔍 多维度过滤：")
    print("   - architects（建筑师）→ 按设计师过滤")
    print("   - location（位置）→ 按地区过滤")
    print("   - year（年份）→ 按时间过滤")
    print("   - area（面积）→ 按规模过滤")

    print("\n3. 🏷️  标签分类：")
    print("   - tags → 功能分类（文化/教育/住宅等）")
    print("   - 示例：tags=['博物馆', '文化建筑'] → 自动归类")

    print("\n4. 🖼️  视觉参考：")
    print("   - images → 展示给用户")
    print("   - 未来可做图像相似度搜索")

    print("\n5. 📊 项目推荐：")
    print("   - 用户收藏A项目 → 推荐相似项目B、C、D")
    print("   - 基于：相同建筑师/相同标签/相似描述")

    print("\n6. 💬 LLM增强：")
    print("   - description + metadata → 作为LLM上下文")
    print("   - 用户问：'这个项目的设计理念是什么？'")
    print("   - LLM基于description生成回答")

    print("\n7. 📈 数据分析：")
    print("   - views（浏览量）→ 热门项目排序")
    print("   - publish_date → 最新项目筛选")

    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    test_single_project_crawl()
