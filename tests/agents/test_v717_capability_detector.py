"""
v7.17 P2 测试脚本：程序化能力边界检测
测试 CapabilityDetector 的检测准确性
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_project_analyzer.utils.capability_detector import (
    CapabilityDetector,
    check_capability,
    check_info_sufficient,
    CapabilityLevel,
)


def test_deliverable_detection():
    """测试交付物能力检测"""
    print("=" * 60)
    print("测试1：交付物能力检测")
    print("=" * 60)

    test_cases = [
        # (输入, 预期能力级别, 预期类型)
        ("我需要8个中餐包房的命名方案，4个字，来源苏东坡诗词", CapabilityLevel.FULL, "naming_list"),
        ("帮我做一个设计策略文档", CapabilityLevel.FULL, "design_strategy"),
        ("需要一份用户画像分析报告", CapabilityLevel.FULL, "user_persona"),
        ("请提供CAD施工图", CapabilityLevel.PARTIAL, "design_strategy"),  # 应转化
        ("需要精确的材料清单和报价", CapabilityLevel.PARTIAL, "material_guidance"),  # 应转化
        ("做一个3D效果图", CapabilityLevel.PARTIAL, "design_strategy"),  # 应转化
    ]

    for user_input, expected_level, expected_type in test_cases:
        results = CapabilityDetector.detect_deliverable_capability(user_input)

        if results:
            first = results[0]
            level_match = first.capability_level == expected_level

            # 检查类型匹配
            if first.within_capability:
                type_match = first.original_type == expected_type
            else:
                type_match = first.transformed_type == expected_type

            status = "✅" if (level_match and type_match) else "❌"
            print(f"\n{status} 输入: {user_input[:30]}...")
            print(f"   预期: {expected_level.value} → {expected_type}")
            print(
                f"   实际: {first.capability_level.value} → {first.original_type if first.within_capability else first.transformed_type}"
            )
            print(f"   关键词: {first.detected_keywords}")
        else:
            print(f"\n❌ 输入: {user_input[:30]}... - 未检测到交付物")


def test_info_sufficiency():
    """测试信息充足性检测"""
    print("\n" + "=" * 60)
    print("测试2：信息充足性检测")
    print("=" * 60)

    test_cases = [
        # (输入, 预期是否充足)
        ("我是一位32岁的前金融律师，有一套75平米的一居室公寓，预算60万，想要现代简约风格", True),
        ("我想装修一下房子", False),
        ("帮我设计一个办公空间，200平米，预算100万，3个月工期，需要会议室和开放工位", True),
        ("需要一个好看的设计", False),
    ]

    for user_input, expected_sufficient in test_cases:
        result = CapabilityDetector.check_info_sufficiency(user_input)

        match = result.is_sufficient == expected_sufficient
        status = "✅" if match else "❌"

        print(f"\n{status} 输入: {user_input[:40]}...")
        print(f"   预期: {'充足' if expected_sufficient else '不足'}")
        print(f"   实际: {'充足' if result.is_sufficient else '不足'} (得分: {result.score:.2f})")
        print(f"   已识别: {result.present_elements}")
        print(f"   缺失: {result.missing_elements[:3]}")


def test_full_capability_check():
    """测试完整能力检测"""
    print("\n" + "=" * 60)
    print("测试3：完整能力检测")
    print("=" * 60)

    user_input = """
    我是一位32岁的前金融律师，刚刚辞职转型为生活美学博主。
    我有一套75平米的一居室公寓，位于上海，高层，南向。
    预算60万，希望4个月内完成。

    我需要：
    1. 设计策略文档
    2. 8个空间命名方案
    3. CAD施工图（希望有）
    4. 精确的材料清单和报价
    """

    result = check_capability(user_input)

    print(f"\n📋 完整检测结果:")
    print(f"\n信息充足性:")
    print(f"   - 是否充足: {result['info_sufficiency']['is_sufficient']}")
    print(f"   - 得分: {result['info_sufficiency']['score']:.2f}")
    print(f"   - 已识别: {result['info_sufficiency']['present_elements']}")

    print(f"\n交付物能力:")
    print(f"   - 匹配度: {result['deliverable_capability']['capability_score']:.0%}")
    print(f"   - 检测到: {result['deliverable_capability']['total_detected']}个")
    print(f"   - 需转化: {result['deliverable_capability']['transformations_needed']}个")

    print(f"\n在能力范围内的交付物:")
    for d in result["capable_deliverables"]:
        print(f"   - {d['type']} (关键词: {d['keywords']})")

    print(f"\n需要转化的需求:")
    for t in result["transformations"]:
        print(f"   - {t['original']} → {t['transformed_to']}")
        print(f"     原因: {t['reason'][:50]}...")

    print(f"\n推荐行动: {result['recommended_action']}")

    print(f"\n预检测提示 (将注入 Phase1):")
    for hint in result["pre_phase1_hints"]:
        print(f"   {hint}")


def test_convenience_functions():
    """测试便捷函数"""
    print("\n" + "=" * 60)
    print("测试4：便捷函数")
    print("=" * 60)

    # 测试 check_info_sufficient
    sufficient_input = "我是32岁女性，有75平米公寓，预算60万，想要现代简约风格的设计"
    insufficient_input = "装修房子"

    print(f"\n充足输入: {check_info_sufficient(sufficient_input)} (预期: True)")
    print(f"不足输入: {check_info_sufficient(insufficient_input)} (预期: False)")


if __name__ == "__main__":
    test_deliverable_detection()
    test_info_sufficiency()
    test_full_capability_check()
    test_convenience_functions()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
