#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试关键词提取功能

验证分词效果和停用词过滤
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.api.admin_routes import extract_meaningful_keywords

# 测试用例
TEST_CASES = [
    {
        "name": "用户反馈的问题文本",
        "text": "基于建造一座小型的私他唯一的要求是让建筑和移位匿名",
        "expected_bad_words": ["基于", "建造一座", "小型的私", "他唯一的", "要求是", "让建筑和", "移位匿名"],
    },
    {
        "name": "正常的室内设计需求",
        "text": "我需要设计一个150平米的现代简约风格住宅，三室两厅，预算30万，希望注重收纳和采光。",
        "expected_good_words": ["现代", "简约", "风格", "住宅", "三室", "两厅", "预算", "收纳", "采光"],
    },
    {
        "name": "别墅设计需求",
        "text": "设计一个独栋别墅，建筑面积500平米，要求新中式风格，包含地下室、泳池和花园。",
        "expected_good_words": ["独栋", "别墅", "建筑面积", "新中式", "风格", "地下室", "泳池", "花园"],
    },
    {
        "name": "商业空间需求",
        "text": "咖啡厅室内设计，面积200平米，工业风格，预算50万，需要吧台、卡座和包间。",
        "expected_good_words": ["咖啡厅", "室内设计", "面积", "工业风", "吧台", "卡座", "包间"],
    },
]


def test_keyword_extraction():
    """测试关键词提取功能"""
    print("=" * 70)
    print(" 🧪 关键词提取测试")
    print("=" * 70)
    print()

    for i, case in enumerate(TEST_CASES, 1):
        print(f"【测试 {i}】{case['name']}")
        print(f"原文: {case['text']}")
        print()

        # 提取关键词
        keywords = extract_meaningful_keywords(case["text"])

        print(f"✅ 提取到 {len(keywords)} 个关键词:")
        print(f"   {', '.join(keywords)}")
        print()

        # 检查不应该出现的无意义词
        if "expected_bad_words" in case:
            bad_words_found = [w for w in case["expected_bad_words"] if w in keywords]
            if bad_words_found:
                print(f"❌ 发现无意义词: {', '.join(bad_words_found)}")
            else:
                print(f"✅ 无意义词已过滤")

        # 检查应该出现的有意义词
        if "expected_good_words" in case:
            good_words_found = [w for w in case["expected_good_words"] if w in keywords]
            good_words_missing = [w for w in case["expected_good_words"] if w not in keywords]

            if good_words_found:
                print(f"✅ 找到关键词: {', '.join(good_words_found)}")
            if good_words_missing:
                print(f"⚠️ 遗漏关键词: {', '.join(good_words_missing)}")

        print("-" * 70)
        print()


def test_stopwords_filtering():
    """测试停用词过滤"""
    print("=" * 70)
    print(" 🚫 停用词过滤测试")
    print("=" * 70)
    print()

    # 应该被过滤的文本
    stopword_text = "的了是在我有和就不人都一一个上也很到说要去你会着没有看好自己这"
    keywords = extract_meaningful_keywords(stopword_text)

    print(f"输入: {stopword_text}")
    print(f"提取结果: {keywords if keywords else '(空)'}")

    if not keywords:
        print("✅ 停用词过滤正常：纯停用词文本返回空列表")
    else:
        print(f"❌ 停用词过滤失败：仍然提取到 {len(keywords)} 个词")

    print()


def test_edge_cases():
    """测试边界情况"""
    print("=" * 70)
    print(" ⚠️ 边界情况测试")
    print("=" * 70)
    print()

    test_cases = [
        ("空字符串", ""),
        ("纯空格", "   "),
        ("纯数字", "123456789"),
        ("纯英文", "hello world design"),
        ("中英混合", "现代modern简约simple风格style"),
        ("包含标点", "【设计】需求：现代！简约？风格。"),
    ]

    for name, text in test_cases:
        keywords = extract_meaningful_keywords(text)
        print(f"【{name}】")
        print(f"   输入: '{text}'")
        print(f"   输出: {keywords if keywords else '(空)'}")
        print()


if __name__ == "__main__":
    # 检查jieba是否安装
    try:
        import jieba

        print("✅ jieba 已安装，将使用智能分词")
    except ImportError:
        print("⚠️ jieba 未安装，将使用简单规则分词")
        print("   安装命令: pip install jieba")

    print()

    # 运行测试
    test_keyword_extraction()
    test_stopwords_filtering()
    test_edge_cases()

    # 总结
    print("=" * 70)
    print(" ✅ 测试完成")
    print("=" * 70)
    print()
    print("💡 提示:")
    print("   - 如果jieba未安装，请运行: pip install jieba")
    print("   - 分词质量会更好，能正确识别复合词")
    print()
