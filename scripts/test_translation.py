#!/usr/bin/env python3
"""
测试翻译功能

测试Dezeen文章的自动翻译
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from loguru import logger

from intelligent_project_analyzer.external_data_system.spiders.dezeen_spider import DezeenSpider
from intelligent_project_analyzer.external_data_system.translation import get_translator


def test_translation(url: str = None, engine: str = "deepseek"):
    """测试翻译功能"""

    # 默认URL
    if not url:
        url = "https://www.dezeen.com/2026/02/10/sou-fujimoto-baccarat-residences/"

    print("=" * 100)
    print(f"测试翻译功能 (引擎: {engine})".center(100))
    print("=" * 100)
    print(f"\n📍 URL: {url}\n")

    # 1. 爬取英文内容
    print("步骤 1: 爬取英文内容")
    print("-" * 100)

    spider = DezeenSpider(use_playwright=True)
    project_data = spider.fetch_project_detail(url)

    if not project_data:
        print("❌ 爬取失败")
        return False

    print(f"✅ 爬取成功")
    print(f"   标题: {project_data.title}")
    print(f"   描述长度: {len(project_data.description)} 字符")
    print(f"   建筑师: {project_data.architects}")

    # 2. 翻译内容
    print(f"\n步骤 2: 翻译为中文 (引擎: {engine})")
    print("-" * 100)

    translator = get_translator(engine=engine)
    translation = translator.translate_project(project_data)

    if "error" in translation:
        print(f"❌ 翻译失败: {translation['error']}")
        return False

    print(f"✅ 翻译成功")
    print(f"   翻译质量: {translation['quality']:.2f}")

    # 3. 展示对比
    print("\n步骤 3: 双语对比")
    print("=" * 100)

    print("\n📌 标题对比:")
    print(f"   英文: {project_data.title}")
    print(f"   中文: {translation['title_zh']}")

    print("\n📝 描述对比 (前500字符):")
    print("\n[英文原文]")
    print("-" * 100)
    print(project_data.description[:500])
    print("...")

    print("\n[中文翻译]")
    print("-" * 100)
    print(translation["description_zh"][:500])
    print("...")

    # 4. 质量分析
    print("\n步骤 4: 质量分析")
    print("=" * 100)

    # 长度比例
    len_ratio = len(translation["description_zh"]) / len(project_data.description)
    print(f"长度比例: {len_ratio:.2f} (正常范围: 0.8-1.5)")

    # 建筑师保留
    if project_data.architects:
        preserved = [
            arch
            for arch in project_data.architects
            if arch in translation["title_zh"] or arch in translation["description_zh"]
        ]
        print(f"建筑师保留: {len(preserved)}/{len(project_data.architects)} {preserved}")

    # 翻译质量判断
    quality = translation["quality"]
    if quality >= 0.8:
        grade = "优秀 ⭐⭐⭐⭐⭐"
    elif quality >= 0.6:
        grade = "良好 ⭐⭐⭐⭐"
    elif quality >= 0.4:
        grade = "一般 ⭐⭐⭐"
    else:
        grade = "较差 ⭐⭐"

    print(f"\n总体评价: {grade}")
    print(f"质量评分: {quality:.2f} / 1.0")

    # 5. 成本估算
    print("\n步骤 5: 成本估算")
    print("=" * 100)

    # 估算token数
    input_tokens = len(project_data.title) + len(project_data.description[:3000])
    output_tokens = len(translation["title_zh"]) + len(translation["description_zh"])

    # Deepseek定价 (2024年价格)
    cost_per_1k_input = 0.001  # ¥0.001/1k tokens
    cost_per_1k_output = 0.002  # ¥0.002/1k tokens

    total_cost = input_tokens / 1000 * cost_per_1k_input + output_tokens / 1000 * cost_per_1k_output

    print(f"输入tokens: ~{input_tokens:,}")
    print(f"输出tokens: ~{output_tokens:,}")
    print(f"单篇成本: ¥{total_cost:.4f}")
    print(f"千篇成本: ¥{total_cost * 1000:.2f}")

    print("\n" + "=" * 100)
    print("✅ 测试完成！")
    print("=" * 100)

    return True


def main():
    parser = argparse.ArgumentParser(description="测试翻译功能")
    parser.add_argument("--url", type=str, help="测试URL（默认使用Sou Fujimoto文章）")
    parser.add_argument(
        "--engine", choices=["deepseek", "gpt4", "claude"], default="deepseek", help="翻译引擎（默认: deepseek）"
    )

    args = parser.parse_args()

    success = test_translation(args.url, args.engine)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
