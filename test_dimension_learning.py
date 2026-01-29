"""
测试维度学习功能 (ENABLE_DIMENSION_LEARNING=true)
验证 AdaptiveDimensionGenerator 是否正确启用和工作
"""

import os
import sys

# 设置环境变量
os.environ["ENABLE_DIMENSION_LEARNING"] = "true"

from intelligent_project_analyzer.services.adaptive_dimension_generator import AdaptiveDimensionGenerator


def test_dimension_learning_enabled():
    """测试维度学习是否启用"""
    print("=" * 60)
    print("测试 1: 验证维度学习是否启用")
    print("=" * 60)

    generator = AdaptiveDimensionGenerator()

    # 验证学习开关
    assert generator.learning_enabled is True, "❌ 学习开关未启用"
    print("✅ 学习开关已启用: ENABLE_DIMENSION_LEARNING=true")

    # 验证组件初始化
    assert generator.base_selector is not None, "❌ 基础选择器未初始化"
    print("✅ 基础选择器已初始化")

    assert generator.evaluator is not None, "❌ 评估器未初始化"
    print("✅ 评估器已初始化")

    assert generator.tracker is not None, "❌ 追踪器未初始化"
    print("✅ 追踪器已初始化")

    print("\n✅ 测试 1 通过: 维度学习功能已正确启用\n")


def test_learning_weight_calculation():
    """测试学习权重计算"""
    print("=" * 60)
    print("测试 2: 验证学习权重计算")
    print("=" * 60)

    generator = AdaptiveDimensionGenerator()

    # 测试不同历史数据量的权重
    test_cases = [
        (0, 0.10, "minimal"),
        (25, 0.10, "minimal"),
        (50, 0.20, "low"),
        (100, 0.20, "low"),
        (200, 0.40, "medium"),
        (350, 0.40, "medium"),
        (500, 0.70, "high"),
        (1000, 0.70, "high"),
    ]

    for count, expected_weight, expected_stage in test_cases:
        weight, stage = generator.get_learning_weight(count)
        assert weight == expected_weight, f"❌ 历史数据量 {count} 的权重错误: 期望 {expected_weight}, 实际 {weight}"
        assert stage == expected_stage, f"❌ 历史数据量 {count} 的阶段错误: 期望 {expected_stage}, 实际 {stage}"
        print(f"✅ 历史数据量 {count:4d} → 权重 {weight:.0%} ({stage})")

    print("\n✅ 测试 2 通过: 学习权重计算正确\n")


def test_dimension_selection():
    """测试维度选择功能"""
    print("=" * 60)
    print("测试 3: 验证维度选择功能")
    print("=" * 60)

    generator = AdaptiveDimensionGenerator()

    # 测试基本维度选择
    project_type = "residential_space"
    user_input = "设计一个现代简约风格的公寓，注重功能性和美观性"

    try:
        dimensions = generator.select_for_project(
            project_type=project_type,
            user_input=user_input,
            min_dimensions=9,
            max_dimensions=12,
        )

        assert isinstance(dimensions, list), "❌ 返回结果不是列表"
        assert len(dimensions) >= 9, f"❌ 维度数量不足: {len(dimensions)} < 9"
        assert len(dimensions) <= 12, f"❌ 维度数量过多: {len(dimensions)} > 12"

        print(f"✅ 成功选择 {len(dimensions)} 个维度")

        # 验证维度结构
        for i, dim in enumerate(dimensions[:3], 1):  # 只检查前3个
            assert "id" in dim, f"❌ 维度 {i} 缺少 id 字段"
            assert "name" in dim, f"❌ 维度 {i} 缺少 name 字段"
            assert "left_label" in dim, f"❌ 维度 {i} 缺少 left_label 字段"
            assert "right_label" in dim, f"❌ 维度 {i} 缺少 right_label 字段"
            print(f"✅ 维度 {i}: {dim['name']} ({dim['left_label']} ↔ {dim['right_label']})")

        if len(dimensions) > 3:
            print(f"   ... 还有 {len(dimensions) - 3} 个维度")

        print("\n✅ 测试 3 通过: 维度选择功能正常\n")

    except Exception as e:
        print(f"❌ 测试 3 失败: {e}")
        raise


def test_special_scene_detection():
    """测试特殊场景检测"""
    print("=" * 60)
    print("测试 4: 验证特殊场景检测")
    print("=" * 60)

    generator = AdaptiveDimensionGenerator()

    # 测试极端环境场景
    test_cases = [
        {"user_input": "设计一个南极科考站的居住空间", "expected_scenes": ["extreme_environment"], "description": "极端环境场景"},
        {"user_input": "设计一个医院的儿童病房", "expected_scenes": ["medical_needs"], "description": "医疗需求场景"},
        {"user_input": "设计一个传统中式茶室，体现禅意文化", "expected_scenes": ["cultural_depth"], "description": "文化深度场景"},
    ]

    for case in test_cases:
        try:
            dimensions = generator.select_for_project(
                project_type="commercial_space",
                user_input=case["user_input"],
                special_scenes=case["expected_scenes"],
                min_dimensions=9,
                max_dimensions=12,
            )

            print(f"✅ {case['description']}: 选择了 {len(dimensions)} 个维度")

        except Exception as e:
            print(f"❌ {case['description']} 失败: {e}")
            raise

    print("\n✅ 测试 4 通过: 特殊场景检测正常\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试维度学习功能 (ENABLE_DIMENSION_LEARNING=true)")
    print("=" * 60 + "\n")

    try:
        test_dimension_learning_enabled()
        test_learning_weight_calculation()
        test_dimension_selection()
        test_special_scene_detection()

        print("=" * 60)
        print("🎉 所有测试通过！维度学习功能正常工作")
        print("=" * 60)
        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试失败: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
