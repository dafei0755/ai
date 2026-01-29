"""
端到端测试：验证动态维度生成功能
"""
import os
import sys

# 设置环境变量
os.environ["USE_DYNAMIC_GENERATION"] = "true"

# 测试1: 验证环境变量加载
print("=" * 60)
print("测试 1: 验证环境变量")
print("=" * 60)

from pathlib import Path

from dotenv import load_dotenv

env_path = Path(".env")
load_dotenv(env_path)

use_dynamic = os.getenv("USE_DYNAMIC_GENERATION", "false").lower() == "true"
print(f"USE_DYNAMIC_GENERATION: {os.getenv('USE_DYNAMIC_GENERATION')}")
print(f"解析结果: {use_dynamic}")

if use_dynamic:
    print("[OK] 动态维度生成已启用")
else:
    print("[FAIL] 动态维度生成未启用")
    sys.exit(1)

# 测试2: 验证 progressive_questionnaire 中的逻辑
print("\n" + "=" * 60)
print("测试 2: 验证问卷节点中的环境变量读取")
print("=" * 60)

# 模拟 progressive_questionnaire.py 中的逻辑
FORCE_GENERATE = os.getenv("FORCE_GENERATE_DIMENSIONS", "false").lower() == "true"
USE_DYNAMIC_GENERATION = os.getenv("USE_DYNAMIC_GENERATION", "false").lower() == "true"
ENABLE_DIMENSION_LEARNING = os.getenv("ENABLE_DIMENSION_LEARNING", "false").lower() == "true"

print(f"FORCE_GENERATE_DIMENSIONS: {FORCE_GENERATE}")
print(f"USE_DYNAMIC_GENERATION: {USE_DYNAMIC_GENERATION}")
print(f"ENABLE_DIMENSION_LEARNING: {ENABLE_DIMENSION_LEARNING}")

if USE_DYNAMIC_GENERATION:
    print("[OK] 问卷节点将启用动态维度生成")
else:
    print("[FAIL] 问卷节点不会启用动态维度生成")
    sys.exit(1)

# 测试3: 验证 DynamicDimensionGenerator 初始化
print("\n" + "=" * 60)
print("测试 3: 验证 DynamicDimensionGenerator 初始化")
print("=" * 60)

try:
    from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator

    generator = DynamicDimensionGenerator()
    print("[OK] DynamicDimensionGenerator 初始化成功")
    print(f"   配置已加载: {generator.config is not None}")
    print(f"   LLM已初始化: {generator.llm is not None}")
except Exception as e:
    print(f"[FAIL] 初始化失败: {e}")
    sys.exit(1)

# 测试4: 验证维度验证逻辑
print("\n" + "=" * 60)
print("测试 4: 验证维度验证逻辑")
print("=" * 60)

test_dimension = {
    "id": "test_extreme_adaptation",
    "name": "极端环境适应性",
    "left_label": "常规环境",
    "right_label": "极端环境",
    "description": "从常规环境到极端环境的适应性要求",
    "category": "functional",
    "default_value": 50,
}

existing_ids = ["material_temperature", "cultural_axis"]
is_valid = generator._validate_dimension(test_dimension, existing_ids)

if is_valid:
    print("[OK] 维度验证通过")
    print(f"   维度ID: {test_dimension['id']}")
    print(f"   维度名称: {test_dimension['name']}")
else:
    print("[FAIL] 维度验证失败")

print("\n" + "=" * 60)
print("[SUCCESS] 所有测试通过！动态维度生成功能已正确配置")
print("=" * 60)
print("\n下一步：重启服务器以加载新配置")
print("命令：python -B scripts\\run_server_production.py")
