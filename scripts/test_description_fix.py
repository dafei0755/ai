#!/usr/bin/env python3
"""测试修复后的description提取"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_project_analyzer.external_data_system.spiders.gooood_spider import GoooodSpider


def test_full_description():
    """测试完整description提取"""

    spider = GoooodSpider(use_playwright=True)

    # 测试URL
    test_url = "https://www.gooood.cn/overseas-mingrui-jiang.htm"

    print(f"测试URL: {test_url}")
    print("=" * 80)

    # 爬取项目
    project = spider.parse_project_page(test_url)

    if project:
        desc = project.description
        paragraphs = desc.split("\n\n")

        print(f"\n✅ 爬取成功!")
        print(f"\n基本信息:")
        print(f"  标题: {project.title}")
        print(f"  URL: {project.url}")
        print(f"\n描述统计:")
        print(f"  总字符数: {len(desc)}")
        print(f"  段落数: {len(paragraphs)}")
        print(f"  平均每段: {len(desc) // len(paragraphs) if paragraphs else 0} 字符")

        print(f"\n前3段预览:")
        for idx, para in enumerate(paragraphs[:3], 1):
            preview = para[:100] + "..." if len(para) > 100 else para
            print(f"  段落{idx}: {preview}")

        print(f"\n后3段预览:")
        for idx, para in enumerate(paragraphs[-3:], len(paragraphs) - 2):
            preview = para[:100] + "..." if len(para) > 100 else para
            print(f"  段落{idx}: {preview}")

        # 对比
        print("\n" + "=" * 80)
        print("对比结果:")
        print(f"  调试脚本发现: 142个段落")
        print(f"  当前提取到: {len(paragraphs)}个段落")

        if len(paragraphs) >= 100:
            print(f"  ✅ 完整提取成功! (段落数: {len(paragraphs)})")
        elif len(paragraphs) >= 50:
            print(f"  🟡 部分提取 (段落数: {len(paragraphs)}, 可能过滤了一些短段落)")
        else:
            print(f"  ❌ 仍然不完整 (段落数: {len(paragraphs)})")
    else:
        print("❌ 爬取失败")


if __name__ == "__main__":
    test_full_description()
