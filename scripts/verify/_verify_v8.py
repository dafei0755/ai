"""v8.0 集成验证脚本"""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("v8.0 雷达图维度生成集成验证")
print("=" * 60)

errors = []

# 1. 验证模块导入
print("\n[1] 模块导入验证...")
try:
    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import ProgressiveQuestionnaireNode

    print("   OK: progressive_questionnaire")
except Exception as e:
    errors.append(f"progressive_questionnaire import: {e}")
    print(f"   FAIL: {e}")

try:
    from intelligent_project_analyzer.services.project_specific_dimension_generator import (
        ProjectSpecificDimensionGenerator,
    )

    print("   OK: project_specific_dimension_generator")
except Exception as e:
    errors.append(f"dimension_generator import: {e}")
    print(f"   FAIL: {e}")

try:
    from intelligent_project_analyzer.core.state import ProjectAnalysisState

    print("   OK: state (ProjectAnalysisState)")
except Exception as e:
    errors.append(f"state import: {e}")
    print(f"   FAIL: {e}")

# 2. 验证 Prompt YAML
print("\n[2] Prompt YAML 验证...")
try:
    import yaml

    yaml_path = "intelligent_project_analyzer/config/prompts/project_specific_dimensions_prompt.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "system_prompt" in data, "缺少 system_prompt"
    assert "user_prompt" in data, "缺少 user_prompt"
    assert "few_shot_examples" in data, "缺少 few_shot_examples"
    print(f"   OK: YAML 加载成功, keys={list(data.keys())}")
    print(f"   OK: few_shot_examples 数量={len(data['few_shot_examples'])}")
except Exception as e:
    errors.append(f"YAML: {e}")
    print(f"   FAIL: {e}")

# 3. 验证 Generator 类结构
print("\n[3] Generator 类结构验证...")
try:
    gen = ProjectSpecificDimensionGenerator()
    assert hasattr(gen, "generate_dimensions"), "缺少 generate_dimensions 方法"
    assert hasattr(gen, "_build_user_prompt"), "缺少 _build_user_prompt 方法"
    assert hasattr(gen, "_extract_dimensions"), "缺少 _extract_dimensions 方法"
    assert hasattr(gen, "_validate_dimension"), "缺少 _validate_dimension 方法"
    assert hasattr(gen, "VALID_SOURCES"), "缺少 VALID_SOURCES"
    print(f"   OK: VALID_SOURCES = {gen.VALID_SOURCES}")
    print(f"   OK: 所有必要方法存在")
except Exception as e:
    errors.append(f"Generator 结构: {e}")
    print(f"   FAIL: {e}")

# 4. 验证 state 字段
print("\n[4] State 字段验证...")
try:
    import typing

    annotations = ProjectAnalysisState.__annotations__
    assert "dimension_generation_method" in annotations, "缺少 dimension_generation_method"
    print(f"   OK: dimension_generation_method 字段已添加")
except Exception as e:
    errors.append(f"State 字段: {e}")
    print(f"   FAIL: {e}")

# 5. 验证 step2_radar 方法签名
print("\n[5] step2_radar 方法验证...")
try:
    method = ProgressiveQuestionnaireNode.step2_radar
    assert callable(method), "step2_radar 不可调用"
    import inspect

    source = inspect.getsource(method)
    assert "USE_PROJECT_SPECIFIC" in source, "缺少 USE_PROJECT_SPECIFIC 环境变量"
    assert "_skip_legacy" in source, "缺少 _skip_legacy 标志"
    assert "dimension_generation_method" in source, "缺少 dimension_generation_method"
    assert "ProjectSpecificDimensionGenerator" in source, "缺少 Generator 导入"
    assert "dimension_layers" in source, "缺少 dimension_layers payload"
    print(f"   OK: step2_radar 包含所有 v8.0 关键标记")
except Exception as e:
    errors.append(f"step2_radar: {e}")
    print(f"   FAIL: {e}")

# 6. 验证维度验证逻辑
print("\n[6] 维度验证逻辑测试...")
try:
    gen = ProjectSpecificDimensionGenerator()

    # 有效维度
    valid_dim = {
        "id": "test_dim_1",
        "name": "测试维度",
        "left_label": "左侧",
        "right_label": "右侧",
        "description": "用于测试的维度",
        "default_value": 40,
        "category": "calibration",
        "source": "calibration",
    }
    is_valid = gen._validate_dimension(valid_dim, set())
    assert is_valid, "有效维度验证失败"
    print(f"   OK: 有效维度通过验证")

    # 无效维度 - 缺少字段
    invalid_dim = {"id": "x", "name": "y"}
    is_valid = gen._validate_dimension(invalid_dim, set())
    assert not is_valid, "无效维度应该被拒绝"
    print(f"   OK: 无效维度被正确拒绝")

    # 校准维度 default=50 应被修正为 decision (三不问规则)
    bad_calibration = {**valid_dim, "id": "test_dim_2", "default_value": 50}
    is_valid = gen._validate_dimension(bad_calibration, set())
    assert is_valid, "default=50 的 calibration 维度应被修正(非拒绝)"
    assert bad_calibration["source"] == "decision", f"source 应被修正为 decision, 实际为 {bad_calibration['source']}"
    print(f"   OK: 三不问规则生效 (source 已从 calibration 修正为 {bad_calibration['source']})")

    print(f"   OK: 维度验证逻辑全部通过")
except Exception as e:
    errors.append(f"维度验证: {e}")
    print(f"   FAIL: {e}")

# 总结
print("\n" + "=" * 60)
if errors:
    print(f"FAILED: {len(errors)} 个错误")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL PASSED: v8.0 集成验证全部通过")
    sys.exit(0)
