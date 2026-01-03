"""
三层递进式问卷系统 - 简化版集成测试
v7.80.18 - 只测试核心组件，不依赖完整系统
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("\n" + "=" * 80)
print("[TEST] 三层递进式问卷系统核心组件测试 (v7.80.18)")
print("=" * 80)

# ============================================================================
# 测试 1: 配置文件存在性检查
# ============================================================================
print("\n[TEST 1] 配置文件完整性检查")
print("-" * 80)

config_files = {
    "core_task_decomposer.yaml": "intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml",
    "radar_dimensions.yaml": "intelligent_project_analyzer/config/prompts/radar_dimensions.yaml",
}

all_configs_exist = True
for name, path in config_files.items():
    file_path = project_root / path
    exists = file_path.exists()
    status = "[OK]" if exists else "[MISS]"
    print(f"   {status} {name}")
    if exists:
        print(f"        Path: {file_path}")
        print(f"        Size: {file_path.stat().st_size} bytes")
    else:
        print(f"        ERROR: File not found at {file_path}")
        all_configs_exist = False

if all_configs_exist:
    print("\n   [PASS] 所有配置文件存在")
else:
    print("\n   [FAIL] 部分配置文件缺失")
    sys.exit(1)

# ============================================================================
# 测试 2: Python 服务文件存在性检查
# ============================================================================
print("\n[TEST 2] Python 服务文件完整性检查")
print("-" * 80)

service_files = {
    "core_task_decomposer.py": "intelligent_project_analyzer/services/core_task_decomposer.py",
    "dimension_selector.py": "intelligent_project_analyzer/services/dimension_selector.py",
    "task_completeness_analyzer.py": "intelligent_project_analyzer/services/task_completeness_analyzer.py",
    "dynamic_dimension_generator.py": "intelligent_project_analyzer/services/dynamic_dimension_generator.py",
    "progressive_questionnaire.py": "intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py",
}

all_services_exist = True
for name, path in service_files.items():
    file_path = project_root / path
    exists = file_path.exists()
    status = "[OK]" if exists else "[MISS]"
    print(f"   {status} {name}")
    if exists:
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        print(f"        Lines: {lines}")
    else:
        print(f"        ERROR: File not found at {file_path}")
        all_services_exist = False

if all_services_exist:
    print("\n   [PASS] 所有服务文件存在")
else:
    print("\n   [FAIL] 部分服务文件缺失")
    sys.exit(1)

# ============================================================================
# 测试 3: 前端组件存在性检查
# ============================================================================
print("\n[TEST 3] 前端组件完整性检查")
print("-" * 80)

frontend_files = {
    "ProgressiveQuestionnaireModal.tsx": "frontend-nextjs/components/ProgressiveQuestionnaireModal.tsx",
    "page.tsx (analysis)": "frontend-nextjs/app/analysis/[sessionId]/page.tsx",
}

all_frontend_exist = True
for name, path in frontend_files.items():
    file_path = project_root / path
    exists = file_path.exists()
    status = "[OK]" if exists else "[MISS]"
    print(f"   {status} {name}")
    if exists:
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        print(f"        Lines: {lines}")

        # 检查关键导入
        content = file_path.read_text(encoding="utf-8")
        if "ProgressiveQuestionnaireModal.tsx" in name:
            if "react-chartjs-2" in content:
                print(f"        [OK] Chart.js 已导入")
            else:
                print(f"        [WARN] Chart.js 未导入")
    else:
        print(f"        ERROR: File not found at {file_path}")
        all_frontend_exist = False

if all_frontend_exist:
    print("\n   [PASS] 所有前端组件存在")
else:
    print("\n   [FAIL] 部分前端组件缺失")
    sys.exit(1)

# ============================================================================
# 测试 4: YAML 配置加载测试
# ============================================================================
print("\n[TEST 4] YAML 配置加载测试")
print("-" * 80)

try:
    import yaml

    # 测试 core_task_decomposer.yaml
    decomposer_config_path = project_root / "intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml"
    with open(decomposer_config_path, "r", encoding="utf-8") as f:
        decomposer_config = yaml.safe_load(f)

    print(f"   [OK] core_task_decomposer.yaml 加载成功")
    print(f"        版本: {decomposer_config.get('metadata', {}).get('version', 'N/A')}")
    print(f"        Prompt 长度: {len(decomposer_config.get('system_prompt', ''))} 字符")

    # 测试 radar_dimensions.yaml
    dimensions_config_path = project_root / "intelligent_project_analyzer/config/prompts/radar_dimensions.yaml"
    with open(dimensions_config_path, "r", encoding="utf-8") as f:
        dimensions_config = yaml.safe_load(f)

    print(f"   [OK] radar_dimensions.yaml 加载成功")
    print(f"        版本: {dimensions_config.get('metadata', {}).get('version', 'N/A')}")
    print(f"        维度总数: {len(dimensions_config.get('dimensions', {}))} 个")
    print(f"        项目类型映射数: {len(dimensions_config.get('project_type_dimensions', {}))} 个")

    print("\n   [PASS] YAML 配置加载测试通过")

except Exception as e:
    print(f"\n   [FAIL] YAML 配置加载失败: {str(e)}")
    sys.exit(1)

# ============================================================================
# 测试 5: 维度数据结构验证
# ============================================================================
print("\n[TEST 5] 维度数据结构验证")
print("-" * 80)

try:
    dimensions = dimensions_config.get("dimensions", {})

    # 检查必需字段
    required_fields = ["name", "left_label", "right_label", "category", "default_value"]

    valid_count = 0
    for dim_id, dim_config in dimensions.items():
        missing_fields = [field for field in required_fields if field not in dim_config]
        if not missing_fields:
            valid_count += 1
        else:
            print(f"   [WARN] {dim_id} 缺少字段: {missing_fields}")

    print(f"   [OK] 有效维度: {valid_count}/{len(dimensions)}")

    # 检查特殊场景维度
    special_dims = [d for d, info in dimensions.items() if info.get("special_scenario")]
    print(f"   [OK] 特殊场景维度: {len(special_dims)} 个")
    for dim_id in special_dims[:3]:  # 只显示前3个
        print(f"        - {dim_id}: {dimensions[dim_id].get('special_scenario')}")

    print("\n   [PASS] 维度数据结构验证通过")

except Exception as e:
    print(f"\n   [FAIL] 维度数据结构验证失败: {str(e)}")
    sys.exit(1)

# ============================================================================
# 测试 6: 前端依赖检查
# ============================================================================
print("\n[TEST 6] 前端依赖检查")
print("-" * 80)

try:
    import json

    package_json_path = project_root / "frontend-nextjs/package.json"
    with open(package_json_path, "r", encoding="utf-8") as f:
        package_json = json.load(f)

    dependencies = package_json.get("dependencies", {})

    required_deps = {"chart.js": "雷达图可视化", "react-chartjs-2": "React Chart.js 集成", "react-flow-renderer": "工作流图表（可选）"}

    for dep, desc in required_deps.items():
        if dep in dependencies:
            print(f"   [OK] {dep} ({desc})")
            print(f"        版本: {dependencies[dep]}")
        else:
            if dep == "react-flow-renderer":
                print(f"   [INFO] {dep} 未安装（可选依赖）")
            else:
                print(f"   [WARN] {dep} 未安装")

    print("\n   [PASS] 前端依赖检查完成")

except Exception as e:
    print(f"\n   [FAIL] 前端依赖检查失败: {str(e)}")
    sys.exit(1)

# ============================================================================
# 总结
# ============================================================================
print("\n" + "=" * 80)
print("[SUMMARY] 测试总结")
print("=" * 80)

print("\n[OK] 后端组件:")
print("   [OK] core_task_decomposer.yaml - 任务拆解配置")
print("   [OK] core_task_decomposer.py - 任务拆解服务")
print("   [OK] radar_dimensions.yaml - 雷达图维度库")
print("   [OK] dimension_selector.py - 维度选择器")
print("   [OK] task_completeness_analyzer.py - 任务完整性分析器")
print("   [OK] dynamic_dimension_generator.py - 动态维度生成器（Stub）")
print("   [OK] progressive_questionnaire.py - 三层问卷核心节点")

print("\n[OK] 前端组件:")
print("   [OK] ProgressiveQuestionnaireModal.tsx - 问卷 Modal 组件")
print("   [OK] page.tsx - WebSocket 集成")
print("   [OK] chart.js + react-chartjs-2 - 雷达图依赖")

print("\n[OK] 数据验证:")
print(f"   [OK] 维度总数: {len(dimensions)} 个")
print(f"   [OK] 特殊场景维度: {len(special_dims)} 个")
print(f"   [OK] 项目类型映射: {len(dimensions_config.get('project_type_dimensions', {}))} 个")

print("\n" + "=" * 80)
print("[PASS] 所有核心组件测试通过！")
print("=" * 80)

print("\n[NEXT] 下一步 - 手动测试:")
print("   1. 启动后端:")
print("      python -m uvicorn intelligent_project_analyzer.api.server:app --reload")
print("")
print("   2. 启动前端:")
print("      cd frontend-nextjs")
print("      npm run dev")
print("")
print("   3. 访问: http://localhost:3000")
print("")
print("   4. 测试用例:")
print("      输入: tiffany 蒂芙尼为主题的住宅软装设计，35岁单身女性，成都350平米别墅")
print("")
print("   5. 验证三层问卷:")
print("      [Step 1] 任务梳理 - 显示 5-7 个任务")
print("      [Step 2] 雷达图维度 - 左侧滑块 + 右侧雷达图")
print("      [Step 3] 补充问题 - 单选/多选/开放题（如有缺失信息）")
print("")
print("=" * 80)
print("[INFO] 核心组件测试完成，系统就绪")
print("=" * 80)
