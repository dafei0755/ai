import json
from pathlib import Path

import yaml

from intelligent_project_analyzer.services.scheme_advisor_pressure_runner import (
    _promote_activation_pack_candidates,
    _allowed_output_depth,
    _layer_boundary_issues,
    _pressure_exit_code,
    _space_axis_summary_key,
    _warning_governance_profile,
    analyze_prompt,
    derive_semantic_axes,
    evaluate_semantic_alignment,
    load_simulation_questions,
    run_pressure_suite,
    write_markdown_report,
)
from intelligent_project_analyzer.services import scheme_advisor_semantic_axes
from intelligent_project_analyzer.services.scheme_advisor_public_labels import public_label
from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
    SEMANTIC_AXIS_REGISTRY_PATH,
    axis_label,
    load_semantic_axis_registry,
)
from intelligent_project_analyzer.services.scheme_advisor_context_intelligence import (
    SchemeAdvisorContextIntelligence,
)
from intelligent_project_analyzer.services.scheme_advisor_entry_service import (
    SchemeAdvisorEntryService,
)


PROMPT_FILE = Path("sf/2026.3.22/模拟问题集合.txt")
PRESSURE_JSON_REPORT = Path(
    "docs/system-completeness-audit/scheme-advisor-pressure-test-2026-03-22.json"
)
SPACE_AXIS_REGISTRY = Path(
    "intelligent_project_analyzer/config/registries/space_axis_registry.yaml"
)


def _pressure_space_axis_ids() -> set[str]:
    report = json.loads(PRESSURE_JSON_REPORT.read_text(encoding="utf-8"))
    return set((report.get("summary") or {}).get("space_axis_counts") or {})


def test_loads_full_simulation_question_set():
    questions = load_simulation_questions(PROMPT_FILE)

    assert len(questions) == 190
    assert questions[0]["id"] == 1
    assert questions[-1]["id"] == 190


def test_pressure_summary_tracks_round_two_generic_fallback_count():
    result = run_pressure_suite(path=PROMPT_FILE, limit=3)

    assert "round_2_generic_fallback_count" in result["summary"]
    assert result["summary"]["round_2_generic_fallback_count"] == 0


def test_pressure_summary_tracks_layer_boundary_violations():
    result = run_pressure_suite(path=PROMPT_FILE, limit=8)

    assert "layer_boundary_violation_count" in result["summary"]
    assert result["summary"]["layer_boundary_violation_count"] == 0
    for item in result["items"]:
        assert item["layer_boundary_issues"] == []


def test_pressure_summary_exposes_unified_quality_issue_counts():
    result = run_pressure_suite(path=PROMPT_FILE, limit=8)
    counts = result["summary"]["quality_issue_counts"]

    expected_keys = {
        "wrong_domain_reference",
        "english_key_visible",
        "generic_step_title_visible",
        "core_subject_missing",
        "low_classification_confidence",
        "knowledge_coverage_gap",
    }

    assert expected_keys.issubset(counts)
    assert all(isinstance(counts[key], int) for key in expected_keys)
    for item in result["items"]:
        assert "question_quality_issues" in item
        assert "display_safety_issues" in item
        assert "governance_candidate_emitted" in item
        assert isinstance(item["governance_candidate_emitted"], bool)


def test_pressure_summary_groups_knowledge_coverage_gaps_by_axis_and_project_type():
    result = run_pressure_suite(path=PROMPT_FILE, limit=12)
    summary = result["summary"]

    axis_counts = summary["knowledge_coverage_gap_axis_counts"]
    project_type_counts = summary["knowledge_coverage_gap_project_type_counts"]

    assert axis_counts
    assert project_type_counts
    assert all(isinstance(count, int) for count in axis_counts.values())
    assert all(isinstance(count, int) for count in project_type_counts.values())
    assert sum(axis_counts.values()) <= summary["quality_issue_counts"]["knowledge_coverage_gap"]
    assert sum(project_type_counts.values()) <= summary["quality_issue_counts"]["knowledge_coverage_gap"]
    assert "methodology_not_project" not in axis_counts
    assert "-" not in project_type_counts


def test_layer_boundary_guard_detects_cross_layer_leakage():
    issues = _layer_boundary_issues(
        {
            "input_mode": "project",
            "mode": "project",
            "project_type": "personal_residential",
            "space_axis_id": "methodology_not_project",
            "space_axis_label": "方法论问题，不进入空间分类主轴",
        }
    )

    assert "project_input_must_not_use_non_project_space_axis" in issues

    issues = _layer_boundary_issues(
        {
            "input_mode": "methodology",
            "mode": "methodology",
            "project_type": "commercial_dining",
            "space_axis_id": "methodology_not_project",
        }
    )

    assert "non_project_input_must_not_keep_project_type" in issues


def test_pressure_space_axes_are_registry_governed():
    registry = yaml.safe_load(SPACE_AXIS_REGISTRY.read_text(encoding="utf-8")) or {}
    registered_axes = set((registry.get("axes") or {}).keys())

    missing_axes = sorted(_pressure_space_axis_ids() - registered_axes)

    assert missing_axes == []


def test_pressure_space_axes_have_user_visible_public_labels():
    fallback_label = "待确认项"
    missing_labels = [
        axis_id
        for axis_id in sorted(_pressure_space_axis_ids())
        if public_label(axis_id) == fallback_label or "_" in public_label(axis_id)
    ]

    assert missing_labels == []


def test_runtime_pressure_copy_does_not_expose_decision_workflow_jargon():
    questions = load_simulation_questions(PROMPT_FILE)
    representative_prompts = [
        next(item for item in questions if item["id"] == 2),
        next(item for item in questions if item["id"] == 13),
    ]
    forbidden_terms = ["风险阈值", "预算押注", "决策级变量"]

    for item in representative_prompts:
        result = analyze_prompt(item["prompt"], question_id=item["id"])
        visible = " ".join(
            [
                result.get("reply_preview") or "",
                result.get("round_2_card_title") or "",
                " ".join(result.get("card_pages") or []),
                " ".join(result.get("round_2_pages") or []),
                result.get("round_2_reply_preview") or "",
            ]
        )

        for term in forbidden_terms:
            assert term not in visible, f"question {item['id']} exposes terminal jargon: {term}"


def test_pressure_exit_code_fails_on_round_two_generic_fallbacks():
    assert _pressure_exit_code({"failed": 0, "round_2_generic_fallback_count": 0}) == 0
    assert _pressure_exit_code({"failed": 1, "round_2_generic_fallback_count": 0}) == 1
    assert _pressure_exit_code({"failed": 0, "round_2_generic_fallback_count": 1}) == 1
    assert _pressure_exit_code(
        {
            "failed": 0,
            "round_2_generic_fallback_count": 0,
            "layer_boundary_violation_count": 1,
        }
    ) == 1


def test_semantic_axes_extract_project_meaning_without_case_specific_branching():
    prompt = (
        "深圳湾一线海景别墅，业主为第一代创业者，从草根奋斗至资本成功，"
        "对空间的期待既包含成就象征，也包含家族传承与内心回归。"
    )

    axes = derive_semantic_axes(prompt)

    assert "residential" in axes["space_domains"]
    assert "founder_owner" in axes["subject_profiles"]
    assert "identity_expression" in axes["founding_drivers"]
    assert "family_legacy" in axes["founding_drivers"]
    assert "waterfront_view" in axes["site_resources"]


def test_semantic_alignment_blocks_wrong_template_and_internal_step_titles():
    prompt = (
        "深圳湾一线海景别墅，业主为第一代创业者，从草根奋斗至资本成功，"
        "对空间的期待既包含成就象征，也包含家族传承与内心回归。"
    )
    visible_text = (
        "这更像是一个小面积高周转的个人住宅。"
        "第一，门头与地铁客流；第二，出杯和外卖自提。"
        "成立路径 硬约束 取舍边界 household structure"
    )

    issues = evaluate_semantic_alignment(
        prompt,
        visible_text,
        project_type="personal_residential",
        card_pages=["成立路径", "硬约束", "取舍边界"],
    )
    codes = {issue["code"] for issue in issues}

    assert "commercial_template_leakage" in codes
    assert "generic_step_title_visible" in codes
    assert "english_key_visible" in codes


def test_non_beverage_prompt_uses_semantic_entry_instead_of_store_template():
    prompt = (
        "四川广元苍溪云峰镇狮岭村进行新农村建设升级，计划打造具有文化示范意义的民宿集群。"
        "要求深度挖掘在地农耕文化、产业结构与乡村经济逻辑，同时融合安藤忠雄的精神性空间、"
        "隈研吾的材料诗性，以及刘家琨、王澍、谢柯等中国建筑师的地域智慧，"
        "形成商业成功与文化深度兼具的项目模型。请提出整体规划与室内设计概念框架。"
    )

    result = analyze_prompt(prompt, question_id=3)
    blocking_codes = {issue["code"] for issue in result["blocking_issues"]}

    assert "commercial_template_leakage" not in blocking_codes
    assert "generic_step_title_visible" not in blocking_codes
    assert "小面积高周转" not in result["reply_preview"]
    assert result["card_pages"]

def test_residential_club_prompt_is_not_forced_into_beverage_template():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 92)

    result = analyze_prompt(prompt, question_id=92)
    blocking_codes = {issue["code"] for issue in result["blocking_issues"]}

    assert result["project_type"] != "commercial_dining"
    assert "generic_step_title_visible" not in blocking_codes
    assert result["card_pages"] != [
        "先看顾客为什么买",
        "先看门头和菜单",
        "先看出杯和取餐",
        "钱先花在哪里",
    ]


def test_non_food_operational_efficiency_does_not_leak_order_pickup_template():
    prompt = (
        "一个位于深圳前海的跨境电商直播基地，需要整合直播间、选品仓储、培训教室与数据监控中心。"
        "项目目标是“7×24小时高效率运转”。请提出完整空间设计框架，包括动线系统、声学控制、"
        "灯光系统与数据中心嵌入策略。"
    )

    result = analyze_prompt(prompt, question_id=90)
    blocking_codes = {issue["code"] for issue in result["blocking_issues"]}
    visible_text = result["reply_preview"] + " ".join(result["card_pages"])

    assert result["project_type"] != "commercial_dining"
    assert "commercial_template_leakage" not in blocking_codes
    assert "点单、制作、取餐" not in visible_text


def test_explicit_home_object_outranks_style_and_story_terms():
    prompt = (
        "客户希望新家融入大量旧货市场淘来的老家具与旧物件，年代风格各异。"
        "请提出完整设计策略，包括风格整合逻辑、视觉焦点建立、材质过渡机制与叙事路径构建。"
    )

    result = analyze_prompt(prompt, question_id=71)

    assert result["project_type"] == "personal_residential"
    assert result["confidence"] >= 0.55
    assert "memory_object_integration" in result["semantic_axes"]["spatial_design_drivers"]
    assert "旧物" in result["reply_preview"]
    assert "记忆" in result["reply_preview"]
    assert "第一代创业者" not in result["reply_preview"]
    assert "深圳湾一线海景" not in result["reply_preview"]


def test_residential_object_outranks_gallery_metaphor():
    prompt = (
        "一位极简主义艺术收藏家希望住宅成为“白盒子画廊”，但仍需日常居住功能。"
        "请提出完整设计概念，包括可隐藏生活系统、展览级灯光控制与艺术安全保护机制。"
    )

    result = analyze_prompt(prompt, question_id=102)

    assert result["project_type"] == "personal_residential"
    assert result["confidence"] >= 0.55
    assert "art_living_balance" in result["semantic_axes"]["spatial_design_drivers"]
    assert "urban_renewal" not in result["semantic_axes"]["space_domains"]
    assert "艺术收藏" in result["reply_preview"]
    assert "日常生活" in result["reply_preview"]
    assert "第一代创业者" not in result["reply_preview"]
    assert "深圳湾一线海景" not in result["reply_preview"]


def test_old_wharf_public_living_room_is_urban_regeneration_context():
    prompt = (
        "一个沿江老码头区域准备改造为城市公共客厅，集市集、展览与轻餐饮于一体。"
        "请提出完整空间设计概念，包括滨水界面重构、活动可变模块与城市记忆叙事系统。"
    )

    axes = derive_semantic_axes(prompt)
    issues = evaluate_semantic_alignment(
        prompt,
        "这更像是一个城市更新和公共再生问题，需要看场地记忆、公共停留和后续运营。",
        project_type="urban_renewal_heritage",
        card_pages=["哪些历史、社区或场地记忆必须保留"],
    )

    assert "urban_renewal" in axes["space_domains"]
    assert "heritage_context" in axes["site_resources"]
    assert "renovation" in axes["lifecycle"]
    assert {issue["code"] for issue in issues} == set()


def test_hospitality_project_type_outranks_residential_metaphor_in_opening():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 1)

    result = analyze_prompt(prompt, question_id=1)

    assert result["project_type"] == "commercial_hospitality"
    assert "居住关系与生活秩序" not in result["reply_preview"]
    assert "住宿体验" in result["reply_preview"]
    assert "运营模型" in result["reply_preview"]


def test_special_function_project_type_outranks_room_word_in_opening():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 27)

    result = analyze_prompt(prompt, question_id=27)

    assert result["project_type"] == "special_function"
    assert "居住关系与生活秩序" not in result["reply_preview"]
    assert "设备" in result["reply_preview"]
    assert "环境控制" in result["reply_preview"]


def test_methodology_question_gets_transferable_framework_not_project_rejection():
    prompt = (
        "请系统分析农耕文化与城市化进程如何影响当代室内设计概念结构，"
        "提出方法论框架与实际应用路径。"
    )

    result = analyze_prompt(prompt, question_id=13)

    assert result["semantic_axes"]["problem_modes"] == ["methodology_discussion"]
    assert "可迁移" in result["reply_preview"]
    assert "方法论" in result["reply_preview"]
    assert "给我一个具体项目" not in result["reply_preview"]
    assert "你给我一个具体项目" not in result["reply_preview"]
    assert result["card_pages"] == ["方法主轴", "适用边界", "落地验证"]


def test_material_replacement_value_argument_is_methodology_not_unknown_space():
    prompt = (
        "施工图深化阶段，设计师提出将进口天然大理石替换为新型环保回收材料（水磨石基底），"
        "造价反而高出20%。业主注重成本控制。请提出完整论证逻辑，说明该替换如何带来"
        "长期运营价值、品牌溢价与可持续形象。"
    )

    result = analyze_prompt(prompt, question_id=83)

    assert result["mode"] == "methodology"
    assert "value_argument" in result["semantic_axes"]["problem_modes"]
    assert "material_sustainability_value" in result["semantic_axes"]["spatial_design_drivers"]
    assert result["space_axis_id"] == "methodology_not_project"
    assert "材料" in result["reply_preview"]
    assert "这个空间主要服务谁" not in result["reply_preview"]


def test_analogy_translation_question_is_supported_as_method_tool():
    prompt = (
        "将劳斯莱斯Arcadia轿跑车的定制体系转译为高净值住宅设计流程，"
        "提出完整方法论，包括客户访谈模型、材料定制逻辑、专属符号系统与交付仪式设计。"
    )

    result = analyze_prompt(prompt, question_id=14)

    assert "analogy_translation" in result["semantic_axes"]["problem_modes"]
    assert "方法转译" in result["reply_preview"]
    assert "住宅" in result["reply_preview"]
    assert "给我一个具体项目" not in result["reply_preview"]
    assert result["card_pages"] == ["方法主轴", "适用边界", "落地验证"]


def test_concrete_project_anchor_outranks_translation_words():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 17)

    result = analyze_prompt(prompt, question_id=17)

    assert result["mode"] == "project"
    assert result["project_type"] is not None
    assert "invalid_context_packet" not in {
        issue["code"] for issue in result["blocking_issues"]
    }


def test_concrete_project_anchor_outranks_process_words():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 84)

    result = analyze_prompt(prompt, question_id=84)

    assert result["mode"] == "project"
    assert result["project_type"] is not None
    assert "invalid_context_packet" not in {
        issue["code"] for issue in result["blocking_issues"]
    }


def test_methodology_pressure_item_does_not_require_activation_pack():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 13)

    result = analyze_prompt(prompt, question_id=13)
    warning_codes = {issue["code"] for issue in result["warning_issues"]}

    assert result["mode"] == "methodology"
    assert result["activation_pack_status"] == "not_required"
    assert result["allowed_output_depth"] == "methodology_framework"
    assert "missing_activation_pack" not in warning_codes
    assert "activation_pack_candidate" not in warning_codes


def test_partial_specialist_project_is_activation_pack_candidate_not_missing_pack():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 17)

    result = analyze_prompt(prompt, question_id=17)
    warning_codes = {issue["code"] for issue in result["warning_issues"]}
    governance_signal_codes = {issue["code"] for issue in result["governance_signals"]}

    assert result["mode"] == "project"
    assert result["activation_pack_status"] == "candidate_needed"
    assert result["knowledge_coverage_level"] == "partial_specialist"
    assert result["coverage_ceiling_level"] == "conditional_framework"
    assert result["allowed_output_depth"] == "conditional_design_framework"
    assert "knowledge_coverage_watch" in governance_signal_codes
    assert "activation_pack_candidate" not in governance_signal_codes
    assert "activation_pack_candidate" not in warning_codes
    assert "missing_activation_pack" not in warning_codes


def test_stable_partial_coverage_gap_is_governance_signal_not_user_warning():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 2)

    result = analyze_prompt(prompt, question_id=2)
    warning_codes = {issue["code"] for issue in result["warning_issues"]}
    governance_signal_codes = {issue["code"] for issue in result["governance_signals"]}

    assert result["mode"] == "project"
    assert result["project_type"] == "personal_residential"
    assert result["coverage_ceiling_level"] == "conditional_framework"
    assert result["allowed_output_depth"] == "conditional_design_framework"
    assert "coverage_gap" not in warning_codes
    assert "knowledge_gap_ticket" not in warning_codes
    assert "coverage_gap" in governance_signal_codes
    assert "knowledge_gap_ticket" in governance_signal_codes
    assert result["input_mode"] == "project"
    assert result["candidate_core_tension"]
    assert "家族" in result["candidate_core_tension"] or "身份" in result["candidate_core_tension"]
    assert result["candidate_allowed_output_depth"] == "条件方案级：可给方案框架，但要声明前提和缺口"


def test_project_core_tension_prefers_prompt_specific_founder_story_over_axis_label():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 2)

    result = analyze_prompt(prompt, question_id=2)

    assert result["mode"] == "project"
    assert result["candidate_core_tension"] != "身份表达、家族传承与日常安住"
    assert any(
        term in result["candidate_core_tension"]
        for term in ["第一代创业者", "创业者", "草根", "资本成功", "成就象征", "内心回归"]
    )
    assert any(term in result["candidate_core_tension"] for term in ["家族", "传承", "身份", "精神"])


def test_project_core_tension_keeps_brand_subject_and_emotional_driver():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 5)

    result = analyze_prompt(prompt, question_id=5)

    assert result["mode"] == "project"
    assert result["candidate_core_tension"] != "命名、象征转译与空间气质"
    assert "女性" in result["candidate_core_tension"]
    assert "Tiffany" in result["candidate_core_tension"]
    assert "富人区" not in set(result["candidate_core_tension"].split("、"))
    assert any(term in result["candidate_core_tension"] for term in ["被珍视", "仪式感", "自我认同", "Tiffany"])


def test_project_core_tension_keeps_hospitality_business_and_owner_signals():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 1)

    result = analyze_prompt(prompt, question_id=1)

    assert result["mode"] == "project"
    assert result["candidate_core_tension"] != "身体体验、私密训练与社交转化"
    assert any(term in result["candidate_core_tension"] for term in ["雅诗阁", "旗舰", "高端市场", "超值", "运营效率"])
    assert any(term in result["candidate_core_tension"] for term in ["艺术策展", "女性艺术策展人", "生活方式"])


def test_project_core_tension_filters_request_list_and_isolated_generic_terms():
    questions = load_simulation_questions(PROMPT_FILE)
    prompts_by_id = {item["id"]: item["prompt"] for item in questions}

    founder_result = analyze_prompt(prompts_by_id[2], question_id=2)
    coffee_result = analyze_prompt(prompts_by_id[79], question_id=79)

    assert all(not part.startswith("包括") for part in founder_result["candidate_core_tension"].split("、"))
    assert "心理" not in set(coffee_result["candidate_core_tension"].split("、"))


def test_value_argument_pressure_item_is_not_forced_into_project_type():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 83)

    result = analyze_prompt(prompt, question_id=83)

    assert result["mode"] == "methodology"
    assert result["input_mode"] == "decision_argument"
    assert result["project_type"] is None
    assert result["candidate_core_tension"]
    assert "价值" in result["candidate_core_tension"] or "成本" in result["candidate_core_tension"]
    assert result["candidate_allowed_output_depth"] == "决策论证级：可给判断框架与证据清单，不输出空间方案"


def test_methodology_items_keep_specific_core_tension_not_generic_label():
    questions = load_simulation_questions(PROMPT_FILE)
    prompts_by_id = {item["id"]: item["prompt"] for item in questions}

    culture_result = analyze_prompt(prompts_by_id[13], question_id=13)
    translation_result = analyze_prompt(prompts_by_id[14], question_id=14)

    assert culture_result["mode"] == "methodology"
    assert culture_result["input_mode"] == "methodology"
    assert culture_result["candidate_core_tension"] != "方法论问题，不进入空间分类主轴"
    assert "文化" in culture_result["candidate_core_tension"] or "空间秩序" in culture_result["candidate_core_tension"]

    assert translation_result["mode"] == "methodology"
    assert translation_result["input_mode"] == "methodology"
    assert translation_result["candidate_core_tension"] != "方法论问题，不进入空间分类主轴"
    assert (
        "高净值" in translation_result["candidate_core_tension"]
        or "转译" in translation_result["candidate_core_tension"]
    )


def test_project_mode_value_argument_words_do_not_downgrade_to_decision_argument():
    questions = load_simulation_questions(PROMPT_FILE)
    prompts_by_id = {item["id"]: item["prompt"] for item in questions}

    for question_id in [69, 76, 167]:
        result = analyze_prompt(prompts_by_id[question_id], question_id=question_id)

        assert result["mode"] == "project"
        assert result["project_type"] is not None
        assert result["input_mode"] == "project"
        assert result["candidate_allowed_output_depth"] != "决策论证级：可给判断框架与证据清单，不输出空间方案"


def test_activation_pack_candidate_is_promoted_by_batch_evidence_not_single_case():
    repeatable_items = [
        {
            "id": index,
            "mode": "project",
            "project_type": "public_cultural",
            "confidence": 0.8,
            "semantic_axes": {"space_domains": ["cultural_exhibition"]},
            "governance_signals": [{"code": "knowledge_coverage_watch"}],
        }
        for index in range(1, 4)
    ]
    one_off_special = {
        "id": 99,
        "mode": "project",
        "project_type": "special_function",
        "confidence": 0.82,
        "semantic_axes": {
            "space_domains": ["technical_special"],
            "spatial_design_drivers": ["extreme_resilience_prototype"],
        },
        "governance_signals": [{"code": "knowledge_coverage_watch"}],
    }

    promoted = _promote_activation_pack_candidates(repeatable_items + [one_off_special])
    by_id = {item["id"]: item for item in promoted}

    assert {
        signal["code"]
        for signal in by_id[1]["governance_signals"]
    } == {"activation_pack_candidate"}
    assert by_id[1]["activation_pack_candidate_group_size"] == 3
    assert {
        signal["code"]
        for signal in by_id[99]["governance_signals"]
    } == {"knowledge_coverage_watch"}


def test_general_method_only_output_is_capped_to_strategy_framework():
    assert _allowed_output_depth(
        mode="project",
        confidence=0.74,
        coverage_ceiling={
            "coverage_level": "general_method_only",
            "ceiling_level": "strategy_framework",
        },
    ) == "strategy_framework"


def test_low_confidence_project_is_capped_to_conditional_judgement():
    assert _allowed_output_depth(
        mode="project",
        confidence=0.42,
        coverage_ceiling={
            "coverage_level": "knowledge_gap",
            "ceiling_level": "conditional_framework",
        },
    ) == "conditional_judgement"


def test_active_missing_slots_prevent_full_specialist_depth_even_with_specialist_coverage():
    assert _allowed_output_depth(
        mode="project",
        confidence=0.86,
        coverage_ceiling={
            "coverage_level": "specialist_covered",
            "ceiling_level": "full_specialist",
        },
        active_missing_slot_count=2,
    ) == "conditional_design_framework"


def test_full_specialist_depth_requires_specialist_coverage_and_no_active_missing_slots():
    assert _allowed_output_depth(
        mode="project",
        confidence=0.86,
        coverage_ceiling={
            "coverage_level": "specialist_covered",
            "ceiling_level": "full_specialist",
        },
        active_missing_slot_count=0,
    ) == "full_specialist_design"


def test_tea_entry_has_formal_activation_pack_without_candidate_warning():
    prompt = (
        "深圳市南山区来福士广场，负一楼，30平米商铺，地铁通道与商场的连接处，"
        "打算做一个奶茶店，希望半年能收回成本，我需要一份完整的设计建议。"
    )

    result = analyze_prompt(prompt, question_id=9001)
    warning_codes = {issue["code"] for issue in result["warning_issues"]}

    assert result["project_type"] == "commercial_dining"
    assert result["subdomain_id"] == "tea_drink_store"
    assert result["activation_pack_id"] == "tea_drink_store_pack"
    assert result["activation_pack_status"] == "formal_bound"
    assert result["knowledge_coverage_level"] == "specialist_covered"
    assert result["coverage_ceiling_level"] == "full_specialist"
    assert result["active_missing_slot_count"] > 0
    assert result["allowed_output_depth"] == "conditional_design_framework"
    assert "activation_pack_candidate" not in warning_codes
    assert "missing_activation_pack" not in warning_codes


def test_pressure_runner_exposes_space_axis_for_systemic_analysis():
    result = analyze_prompt(
        "\u6df1\u5733\u5e02\u5357\u5c71\u533a\u6765\u798f\u58eb\u5e7f\u573a"
        "\uff0c\u8d1f\u4e00\u697c\uff0c30\u5e73\u7c73\u5546\u94fa"
        "\uff0c\u5730\u94c1\u901a\u9053\u4e0e\u5546\u573a\u7684\u8fde\u63a5\u5904"
        "\uff0c\u6253\u7b97\u505a\u4e00\u4e2a\u5976\u8336\u5e97"
        "\uff0c\u5e0c\u671b\u534a\u5e74\u80fd\u6536\u56de\u6210\u672c"
        "\uff0c\u6211\u9700\u8981\u4e00\u4efd\u5b8c\u6574\u7684\u8bbe\u8ba1\u5efa\u8bae\u3002",
        question_id=9002,
    )

    assert result["space_axis_id"] == "commercial_operation_roi"
    assert "回本" in result["space_axis_label"]


def test_pressure_runner_exposes_round_two_semantic_questions():
    result = analyze_prompt(
        (
            "深圳市南山区来福士广场，负一楼，30平米商铺，地铁通道与商场的连接处，"
            "打算做一个奶茶店，希望半年能收回成本，我需要一份完整的设计建议。"
        ),
        question_id=9005,
    )

    round_2_text = (
        result["round_2_card_title"]
        + " ".join(result["round_2_pages"])
        + result["round_2_reply_preview"]
    )

    assert result["round_2_card_title"]
    assert result["round_2_pages"]
    assert "最不能跑偏" not in round_2_text
    assert "最后确认优先级" not in round_2_text
    assert any(term in round_2_text for term in ["商业", "回本", "运营", "客流"])


def test_round_two_uses_specific_axis_for_representative_general_domains():
    samples = [
        (
            "一个沿江老码头区域准备改造为城市公共客厅，集市集、展览与轻餐饮于一体。"
            "请提出完整空间设计概念，包括滨水界面重构、活动可变模块与城市记忆叙事系统。",
            ["更新", "再生", "场地", "记忆", "公共"],
        ),
        (
            "一位因意外需终身使用轮椅的30岁前运动员，希望住宅完全无障碍，同时保持现代感与活力，"
            "避免残疾人之家的视觉印象。请提出完整设计方案，包括动线半径计算、家具高度控制、"
            "卫生间改造策略与视觉年轻化表达。",
            ["无障碍", "尊严", "安全", "活力", "照护"],
        ),
        (
            "一家AI生成内容公司希望办公室呈现无边界创作场，空间需激发灵感并支持快速协作。"
            "请提出完整设计框架，包括可移动创作单元、数字投影系统与灵感展示墙逻辑。",
            ["办公", "协作", "创作", "效率", "组织"],
        ),
        (
            "以季裕棠的叙事手法，为400㎡大平层设计概念。业主为00后英国海归富二代，"
            "性格桀骜、热爱潮玩。请重点围绕客厅空间提出精神表达系统，构建空间层次、"
            "材质克制与叙事张力，避免低级奢华。",
            ["居住", "生活", "主人", "精神", "日常"],
        ),
        (
            "某科技巨头准备建设数据遗产博物馆，展示人类数字文明演进。空间需呈现技术史与人类情感交织的叙事。"
            "请提出完整室内设计框架，包括展陈路径、沉浸式互动与数字装置整合策略。",
            ["展陈", "叙事", "参观", "信息", "体验"],
        ),
        (
            "某山区旅游目的地计划打造山谷度假聚落，包含民宿、艺术驻留、餐饮与市集空间。"
            "请从建筑布局、景观动线与室内叙事三个层面提出完整规划策略，"
            "解释如何通过地形顺应、视线组织与空间节奏形成独特目的地记忆。",
            ["度假", "目的地", "住宿", "运营", "停留"],
        ),
        (
            "一位跨国时尚博主希望在上海打造“流动式生活空间”，可快速调整用于派对、拍摄与居住。"
            "请提出完整设计方案，包括可移动家具系统、灯光模块化与社交展示逻辑。",
            ["多场景", "切换", "派对", "拍摄", "居住"],
        ),
    ]

    for index, (prompt, expected_terms) in enumerate(samples, start=9100):
        result = analyze_prompt(prompt, question_id=index)
        round_2_text = (
            result["round_2_card_title"]
            + " ".join(result["round_2_pages"])
            + result["round_2_reply_preview"]
        )

        assert "当前项目主轴" not in round_2_text
        assert any(term in round_2_text for term in expected_terms), round_2_text


def test_concrete_commercial_project_with_methodology_words_stays_project_mode():
    result = analyze_prompt(
        (
            "南充嘉陵区铜锣湾广场，50000㎡两层商业街区，面临300米内王府井商场竞争。"
            "请提出完整商业空间升级框架，包括客群分层定位、主力店与次主力动线组织、"
            "社交场景植入、夜经济激活策略、材料成本控制与品牌差异化形象塑造。"
        ),
        question_id=9003,
    )

    assert result["mode"] == "project"
    assert result["project_type"] == "commercial_retail"
    assert result["space_axis_id"] == "retail_brand_conversion"
    assert result["space_axis_id"] != "methodology_not_project"


def test_rural_private_dwelling_uses_residential_axis_not_hospitality_axis():
    result = analyze_prompt(
        (
            "四川广元农村300㎡田园民居，业主为50岁男性室内设计师，长期离家在外发展，"
            "内心存在对乡土的复杂情感。请以安藤忠雄为其设计为假设前提，"
            "提出完整室内设计概念框架，围绕光的控制、混凝土与在地材料的张力、"
            "空间的沉默感、与自然对话的界面关系，以及如何在朴素乡村环境中实现精神性空间的建构。"
        ),
        question_id=9004,
    )

    assert result["mode"] == "project"
    assert result["project_type"] == "rural_construction"
    assert result["space_axis_id"] == "private_residential_life_order"
    assert result["space_axis_id"] != "hospitality_culture_operation"


def test_pressure_markdown_reports_space_axis_distribution():
    result = {
        "generated_at": "2026-06-15T00:00:00",
        "source_path": "sf/2026.3.22/模拟问题集合.txt",
        "summary": {
            "total": 3,
            "passed": 3,
            "failed": 0,
            "with_warnings": 1,
            "space_axis_counts": {
                "commercial_operation_roi": 2,
                "unclassified_needs_axis": 1,
            },
            "output_depth_counts": {
                "conditional_design_framework": 2,
                "methodology_framework": 1,
            },
            "coverage_ceiling_counts": {
                "conditional_framework": 2,
                "not_applicable": 1,
            },
            "round_2_generic_fallback_count": 0,
        },
        "items": [
            {
                "id": 1,
                "status": "pass",
                "project_type": "commercial_dining",
                "subdomain_id": "tea_drink_store",
                "activation_pack_id": "tea_drink_store_pack",
                "confidence": 0.9,
                "warning_issues": [],
                "governance_signals": [],
                "blocking_issues": [],
                "prompt": "深圳来福士负一楼30平奶茶店，半年回本。",
                "round_2_card_title": "再确认商业回本的优先级",
                "round_2_pages": ["回本打法", "运营风险", "客流转化"],
            }
        ],
    }
    output_dir = Path(".pytest_tmp")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "pressure_axis_report.md"

    write_markdown_report(result, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "## 空间主轴汇总" in text
    assert "| `commercial_operation_roi` | 2 |" in text
    assert "| `unclassified_needs_axis` | 1 |" in text
    assert "## 输出封顶汇总" in text
    assert "| `conditional_design_framework` | 2 |" in text
    assert "## 知识覆盖封顶汇总" in text
    assert "| `conditional_framework` | 2 |" in text
    assert "- 第二轮通用兜底残留: 0" in text
    assert "再确认商业回本的优先级" in text
    assert "回本打法 / 运营风险 / 客流转化" in text
    output_path.unlink(missing_ok=True)


def test_pressure_markdown_reports_unified_quality_issue_counts():
    result = {
        "generated_at": "2026-06-15T00:00:00",
        "source_path": "sf/2026.3.22/模拟问题集合.txt",
        "summary": {
            "total": 2,
            "passed": 2,
            "failed": 0,
            "with_warnings": 0,
            "space_axis_counts": {"commercial_operation_roi": 2},
            "quality_issue_counts": {
                "wrong_domain_reference": 1,
                "english_key_visible": 0,
                "generic_step_title_visible": 0,
                "core_subject_missing": 1,
                "low_classification_confidence": 0,
                "knowledge_coverage_gap": 2,
            },
        },
        "items": [],
    }
    output_dir = Path(".pytest_tmp")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "pressure_quality_report.md"

    write_markdown_report(result, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "## 质量指标汇总" in text
    assert "| `wrong_domain_reference` | 1 | 错误领域引用 |" in text
    assert "| `core_subject_missing` | 1 | 未回应用户输入里的关键主体 |" in text
    assert "| `knowledge_coverage_gap` | 2 | 知识覆盖不足或候选治理信号 |" in text
    output_path.unlink(missing_ok=True)


def test_pressure_markdown_reports_knowledge_gap_clusters():
    result = {
        "generated_at": "2026-06-15T00:00:00",
        "source_path": "sf/2026.3.22/模拟问题集合.txt",
        "summary": {
            "total": 3,
            "passed": 3,
            "failed": 0,
            "with_warnings": 0,
            "space_axis_counts": {"private_residential_life_order": 2},
            "quality_issue_counts": {"knowledge_coverage_gap": 2},
            "knowledge_coverage_gap_axis_counts": {
                "private_residential_life_order": 2,
            },
            "knowledge_coverage_gap_project_type_counts": {
                "personal_residential": 2,
            },
        },
        "items": [],
    }
    output_dir = Path(".pytest_tmp")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "pressure_gap_cluster_report.md"

    write_markdown_report(result, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "## 知识覆盖缺口聚合" in text
    assert "### 按空间主轴" in text
    assert "| `private_residential_life_order` | 2 |" in text
    assert "### 按项目类型" in text
    assert "| `personal_residential` | 2 |" in text
    output_path.unlink(missing_ok=True)


def test_pressure_summary_separates_non_project_modes_from_unknown_axis():
    assert _space_axis_summary_key({
        "space_axis_id": "commercial_operation_roi",
        "mode": "project",
    }) == "commercial_operation_roi"
    assert _space_axis_summary_key({
        "space_axis_id": None,
        "mode": "methodology",
    }) == "methodology_not_project"
    assert _space_axis_summary_key({
        "space_axis_id": "",
        "mode": "redirect",
    }) == "redirect_not_project"
    assert _space_axis_summary_key({
        "space_axis_id": None,
        "mode": "project",
    }) == "unknown"


def test_warning_governance_profile_separates_errors_from_candidate_pool():
    missing = _warning_governance_profile("missing_activation_pack")
    candidate = _warning_governance_profile("activation_pack_candidate")
    low_confidence = _warning_governance_profile("low_classification_confidence")
    knowledge_gap = _warning_governance_profile("knowledge_gap_ticket")

    assert missing["priority"] == "P0"
    assert missing["track"] == "runtime_configuration_gap"
    assert candidate["priority"] == "P3"
    assert candidate["track"] == "activation_pack_candidate_pool"
    assert low_confidence["priority"] == "P1"
    assert knowledge_gap["track"] == "knowledge_asset_pipeline"


def _assert_no_mojibake_markers(text: str) -> None:
    markers = ["鏂规", "绌洪", "鐭ヨ", "鍛婅", "娌荤", "瑕嗙", "鍊欓", "閸", "鐞", "锟", "Ã", "Â"]
    found = [marker for marker in markers if marker in text]
    assert found == []


def test_pressure_markdown_reports_warning_governance_priority():
    result = {
        "generated_at": "2026-06-15T00:00:00",
            "source_path": "sf/2026.3.22/模拟问题集合.txt",
        "summary": {
            "total": 2,
            "passed": 2,
            "failed": 0,
            "with_warnings": 2,
            "space_axis_counts": {"commercial_operation_roi": 2},
        },
        "items": [
            {
                "id": 1,
                "status": "pass",
                "project_type": "commercial_dining",
                "subdomain_id": "tea_drink_store",
                "activation_pack_id": "tea_drink_store_pack",
                "confidence": 0.9,
                "warning_issues": [
                    {"code": "low_classification_confidence", "message": "confidence=0.44"},
                ],
                "blocking_issues": [],
                "prompt": "测试问题一",
            },
            {
                "id": 2,
                "status": "pass",
                "project_type": "personal_residential",
                "subdomain_id": None,
                "activation_pack_id": None,
                "confidence": 0.8,
                "warning_issues": [
                    {"code": "activation_pack_candidate", "message": "candidate"},
                ],
                "blocking_issues": [],
                "prompt": "测试问题二",
            },
        ],
    }
    output_dir = Path(".pytest_tmp")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "pressure_governance_report.md"

    write_markdown_report(result, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "治理优先级" in text
    assert "| `P1` | 1 |" in text
    assert "| `P3` | 1 |" in text
    assert "activation_pack_candidate_pool" in text
    assert "## 治理信号汇总" in text
    assert "## 逐条结果" in text
    _assert_no_mojibake_markers(text)
    output_path.unlink(missing_ok=True)


def test_coffee_prompt_uses_coffee_language_without_internal_step_terms():
    questions = load_simulation_questions(PROMPT_FILE)
    prompt = next(item["prompt"] for item in questions if item["id"] == 79)

    result = analyze_prompt(prompt, question_id=79)
    blocking_codes = {issue["code"] for issue in result["blocking_issues"]}

    assert result["subdomain_id"] == "coffee_shop"
    assert "generic_step_title_visible" not in blocking_codes
    assert "茶饮小店" not in result["reply_preview"]
    assert "成立路径" not in result["reply_preview"]


def test_tea_golden_100_question_file_keeps_domain_context():
    questions = load_simulation_questions(Path("sf/2026.5.23/茶饮空间黄金问题.txt"))

    assert len(questions) == 100
    assert {item["source_group"] for item in questions} >= {
        "site_business_model",
        "opening_validation_review",
    }
    assert all(item["domain_context"] for item in questions)
    assert all("茶饮店项目" in item["domain_context"] for item in questions)


def test_retail_store_diagnostics_do_not_force_tea_subdomain():
    result = analyze_prompt(
        (
            "社区花店门店，顾客会线上预订、到店自提，也有同城配送。"
            "请判断排队、取花、包装和离店动线是否会互相干扰。"
        ),
        question_id=9201,
    )

    visible_text = " ".join(
        [
            result.get("reply_preview") or "",
            " ".join(result.get("card_pages") or []),
            result.get("round_2_reply_preview") or "",
            " ".join(result.get("round_2_pages") or []),
        ]
    )

    assert result["project_type"] != "commercial_dining"
    assert result["subdomain_id"] != "tea_drink_store"
    assert result["activation_pack_id"] != "tea_drink_store_pack"
    assert "茶饮" not in visible_text
    assert "出杯" not in visible_text


def test_tea_golden_questions_route_to_subdomain_specific_axes():
    questions = load_simulation_questions(Path("sf/2026.5.23/茶饮空间黄金问题.txt"))
    by_id = {item["id"]: item for item in questions}
    service = SchemeAdvisorEntryService()

    expected_axes = {
        11: "tea_hard_constraint_feasibility",
        45: "tea_product_menu_operation",
        52: "tea_queue_pickup_flow",
    }

    for question_id, expected_axis in expected_axes.items():
        question = by_id[question_id]
        result = analyze_prompt(
            question["prompt"],
            question_id=question_id,
            service=service,
            domain_context=question["domain_context"],
        )

        assert result["subdomain_id"] == "tea_drink_store"
        assert result["space_axis_id"] == expected_axis


def test_tea_golden_questions_cover_broader_subdomain_axis_map():
    questions = load_simulation_questions(Path("sf/2026.5.23/茶饮空间黄金问题.txt"))
    by_id = {item["id"]: item for item in questions}
    service = SchemeAdvisorEntryService()

    expected_axes = {
        1: "tea_site_business_model",
        20: "tea_visibility_conversion",
        30: "tea_customer_brand_goal",
        34: "tea_store_model_scene_strategy",
        63: "tea_waiting_experience_repurchase",
        72: "tea_brand_price_visual_memory",
        82: "tea_equipment_logistics_maintenance",
        88: "tea_standard_competition_positioning",
        93: "tea_opening_validation_review",
    }

    for question_id, expected_axis in expected_axes.items():
        question = by_id[question_id]
        result = analyze_prompt(
            question["prompt"],
            question_id=question_id,
            service=service,
            domain_context=question["domain_context"],
        )

        assert result["subdomain_id"] == "tea_drink_store"
        assert result["space_axis_id"] == expected_axis


def test_semantic_axis_registry_can_be_governed_outside_code():
    registry_path = Path("tests/fixtures/scheme_advisor_semantic_axes_test.yaml")
    registry = load_semantic_axis_registry(registry_path, use_cache=False)
    axes = derive_semantic_axes("这里包含独有测试词", registry=registry)

    assert axes["test_axis"] == ["test_case"]
    assert scheme_advisor_semantic_axes.axis_label("test_case", registry=registry) == "外部配置命中"


def test_axis_label_public_fallback_never_exposes_machine_keys():
    assert axis_label("heritage_value") == "历史价值"
    assert axis_label("preservation_grade") == "保护等级"
    assert axis_label("structural_condition") == "结构现状"
    assert axis_label("unknown_unmapped_axis") == "待确认项"


def test_semantic_question_options_and_titles_do_not_expose_internal_keys():
    options = SchemeAdvisorContextIntelligence._semantic_options(
        ["heritage_value", "preservation_grade", "unknown_unmapped_axis"],
        fallback=[],
    )
    pages = SchemeAdvisorContextIntelligence._semantic_tension_pages(
        [
            {
                "id": "preservation_grade",
                "title": "preservation grade",
                "prompt": "structural condition",
                "source_axes": [],
            }
        ],
        main_options=options,
        user_options=[],
        boundary_options=[],
    )
    visible_text = " ".join(
        [
            pages[0]["page_title"],
            pages[0]["prompt_text"],
            *[option["label"] for option in pages[0]["options"]],
            *[option["description"] for option in pages[0]["options"]],
        ]
    )

    assert "保护等级" in visible_text
    assert "历史价值" in visible_text
    assert "结构现状" in visible_text
    assert "preservation grade" not in visible_text
    assert "structural condition" not in visible_text
    assert "unknown unmapped axis" not in visible_text


def test_default_semantic_axis_rules_are_externalized():
    assert SEMANTIC_AXIS_REGISTRY_PATH.exists()
    registry_text = SEMANTIC_AXIS_REGISTRY_PATH.read_text(encoding="utf-8")
    source_text = Path(scheme_advisor_semantic_axes.__file__).read_text(encoding="utf-8")

    assert "第一代创业者" in registry_text
    assert "AXIS_RULES" not in source_text
    assert "AXIS_LABELS" not in source_text
