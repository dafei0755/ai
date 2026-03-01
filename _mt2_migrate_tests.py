"""MT-2: 将 tests/ 根目录的平铺测试文件移入对应子目录"""
import shutil
import os
from pathlib import Path

TESTS_ROOT = Path("tests")

# 目标子目录 → 文件列表
MAPPING: dict[str, list[str]] = {
    "api": [
        "test_api_fallback.py",
        "test_session_deletion_permission.py",
    ],
    "agents": [
        "test_conversation_agent.py",
        "test_conversation_v714.py",
        "test_expert_collaboration_upgrade.py",
        "test_feasibility_analyst.py",
        "test_followup_agent_v715.py",
        "test_philosophy_questions.py",
        "test_post_completion_followup.py",
        "test_questionnaire_data_utilization.py",
        "test_questionnaire_generation.py",
        "test_questionnaire_generators.py",
        "test_questionnaire_step1.py",
        "test_questionnaire_summary.py",
        "test_questionnaire_type_fix.py",
        "test_step3_llm_v7107.py",
        "test_v7106_task_precision.py",
        "test_v716_agents.py",
        "test_v716_integration.py",
        "test_v717_capability_detector.py",
        "test_v717_stategraph_agent.py",
        "test_v717_two_phase.py",
    ],
    "services": [
        "test_bocha_name_fix.py",
        "test_complexity_assessment.py",
        "test_concept_image_url_fix.py",
        "test_content_safety.py",
        "test_content_safety_core.py",
        "test_dynamic_dimension_fix.py",
        "test_dynamic_dimension_generator_v105.py",
        "test_emoji_fix_v7_120.py",
        "test_few_shot_optimization.py",
        "test_json_schema_upgrade.py",
        "test_jtbd_transform.py",
        "test_llm_dimension_generation.py",
        "test_llm_fallback.py",
        "test_motivation_diversity.py",
        "test_motivation_labels.py",
        "test_motivation_label_fix.py",
        "test_motivation_system.py",
        "test_openrouter.py",
        "test_openrouter_load_balancer.py",
        "test_quality_preflight_fix.py",
        "test_role_id_normalization.py",
        "test_search_query_data_utilization.py",
        "test_task_oriented_model_schema_fix.py",
        "test_tencent_content_safety.py",
        "test_unified_input_validator.py",
        "test_v2_1_few_shot.py",
        "test_v2_2_few_shot.py",
        "test_v2_models.py",
        "test_v3_1_few_shot.py",
        "test_v3_2_few_shot.py",
        "test_v3_v4_models.py",
        "test_v4_1_few_shot.py",
        "test_v4_2_few_shot.py",
        "test_v5_0_few_shot.py",
        "test_v5_1_few_shot.py",
        "test_v5_2_few_shot.py",
        "test_v5_models.py",
        "test_v6_1_few_shot.py",
        "test_v6_2_few_shot.py",
        "test_v6_3_few_shot.py",
        "test_v6_4_few_shot.py",
        "test_v6_models.py",
        "test_v7601_optimizations.py",
        "test_v7_0_few_shot.py",
    ],
    "interaction": [
        "test_dynamic_question_adjustment.py",
        "test_progressive_questionnaire_lite.py",
        "test_v780_progressive_questionnaire.py",
    ],
    "integration": [
        "test_content_safety_guard_integration.py",
        "test_integration.py",
        "test_requirements_analyst_integration.py",
        "test_system_followup_flow.py",
        "test_v15_questionnaire_integration.py",
        "test_v15_workflow_integration.py",
        "test_v717_workflow_integration.py",
        "test_v718_questionnaire_integration.py",
    ],
    "e2e": [
        "test_requirements_analyst_e2e.py",
        "test_ux_improvement.py",
        "test_v717_e2e_real_llm.py",
    ],
    "regression": [
        "test_requirements_analyst_regression.py",
        "test_v93_regression.py",
    ],
    "unit": [
        "test_fixtures.py",
        "test_minimal.py",
        "test_p0_p1_p2_comprehensive.py",
        "test_p1_features.py",
        "test_p2_features.py",
        "test_phase2_features.py",
        "test_phase2_lite.py",
        "test_phase2_lite_fixed.py",
        "test_priority_config.py",
        "test_requirements_analyst_unit.py",
    ],
    "report": [
        "test_report_iterations.py",
    ],
    "tools": [
        "test_tool_langchain_wrapper.py",
    ],
    "workflow": [
        "test_workflow_flags.py",
        "test_workflow_persistence.py",
    ],
}

# 脚本文件（非测试，留在根目录或移到 tools/）
SCRIPT_FILES = [
    "check_all_tools_name.py",
    "run_geoip_tests.py",
    "verify_geoip.py",
]

moved = 0
skipped = 0
errors = []

for subdir, files in MAPPING.items():
    dest_dir = TESTS_ROOT / subdir
    dest_dir.mkdir(exist_ok=True)
    for fname in files:
        src = TESTS_ROOT / fname
        dst = dest_dir / fname
        if not src.exists():
            print(f"  SKIP (not found): {fname}")
            skipped += 1
            continue
        if dst.exists():
            print(f"  SKIP (exists in dest): {subdir}/{fname}")
            skipped += 1
            continue
        try:
            shutil.move(str(src), str(dst))
            print(f"  MOVE: {fname} → {subdir}/")
            moved += 1
        except Exception as e:
            errors.append(f"{fname}: {e}")
            print(f"  ERROR: {fname}: {e}")

print(f"\n=== 完成 ===")
print(f"  已移动: {moved} 个文件")
print(f"  已跳过: {skipped} 个文件")
if errors:
    print(f"  错误数: {len(errors)}")
    for e in errors:
        print(f"    {e}")

# 检查根目录剩余的 test_*.py 文件
remaining = sorted(f.name for f in TESTS_ROOT.iterdir() if f.is_file() and f.name.startswith("test_"))
print(f"\n根目录剩余 test_*.py 文件 ({len(remaining)} 个):")
for f in remaining:
    print(f"  {f}")
