from intelligent_project_analyzer.services.scheme_advisor_systemic_remediation_backlog import (
    build_systemic_remediation_backlog,
)


def _sample_golden_annotation():
    return {
        "summary": {
            "total": 190,
            "needs_human_review": 126,
            "remediation_family_counts": {
                "住宅身份/家庭关系/情绪修复": 47,
                "空间尺度与阶段封顶": 30,
                "商业运营闭环/效率与体验": 21,
                "非空间类型入口/设计决策论证": 11,
                "类型边界低置信": 6,
            },
        },
        "items": [
            {
                "id": 2,
                "remediation_family": "住宅身份/家庭关系/情绪修复",
                "current_project_type": "personal_residential",
                "confidence": 0.9,
                "candidate_core_tension": "成就表达、家族传承与日常安住的平衡",
            },
            {
                "id": 50,
                "remediation_family": "住宅身份/家庭关系/情绪修复",
                "current_project_type": "children_family",
                "confidence": 0.32,
                "candidate_core_tension": "情绪支持、隐私边界与日常使用秩序",
            },
            {
                "id": 83,
                "remediation_family": "非空间类型入口/设计决策论证",
                "current_project_type": "-",
                "confidence": 0,
                "candidate_core_tension": "材料替代的长期价值论证",
            },
        ],
    }


def _sample_suggestions():
    return {
        "summary": {"total": 29, "ready_for_fast_review": 3, "needs_human_decision": 26},
        "items": [
            {
                "id": 2,
                "suggestion_decision": "ready_for_fast_review",
                "suggested_gold_expected_project_type": "personal_residential",
            },
            {
                "id": 50,
                "suggestion_decision": "needs_human_decision",
                "suggested_gold_expected_project_type": "",
            },
        ],
    }


def _sample_pressure_result():
    return {
        "summary": {
            "total": 190,
            "passed": 190,
            "failed": 0,
            "with_warnings": 0,
            "with_governance_signals": 1,
        },
        "items": [
            {
                "id": 191,
                "warning_issues": [],
                "governance_signals": [{"code": "activation_pack_candidate"}],
            }
        ],
    }


def test_systemic_remediation_backlog_is_module_based_not_case_patch():
    backlog = build_systemic_remediation_backlog(_sample_golden_annotation(), _sample_suggestions())

    assert backlog["schema_version"] == "scheme_advisor_systemic_remediation_backlog.v1"
    assert backlog["summary"]["total_pressure_items"] == 190
    assert backlog["summary"]["needs_human_review"] == 126
    assert backlog["summary"]["must_not_hardcode_cases"] is True
    assert len(backlog["items"]) >= 6

    modules = {item["module"] for item in backlog["items"]}
    assert "SpaceClassificationService" in modules
    assert "SchemeAdvisorEntryService" in modules
    assert "FrontendHumanLanguageMapping" in modules

    for item in backlog["items"]:
        assert item["governance_mode"] in {"algorithmic_rule", "registry_governed", "review_workflow", "ui_mapping"}
        assert item["mechanism"]
        assert item["verification_gate"]
        assert "单个案例" not in item["mechanism"]
        assert item["sample_ids"] != [2]


def test_systemic_remediation_prioritizes_classification_and_human_language():
    backlog = build_systemic_remediation_backlog(_sample_golden_annotation(), _sample_suggestions())
    by_module = {item["module"]: item for item in backlog["items"]}

    classification = by_module["SpaceClassificationService"]
    assert classification["priority"] == "P0"
    assert classification["evidence_count"] >= 6
    assert "主轴" in classification["mechanism"]
    assert "190 条" in classification["verification_gate"]

    frontend = by_module["FrontendHumanLanguageMapping"]
    assert frontend["priority"] == "P0"
    assert "英文内部字段" in frontend["risk"]
    assert "人话标签" in frontend["mechanism"]


def test_frontend_language_action_exposes_machine_readable_guardrail():
    backlog = build_systemic_remediation_backlog(_sample_golden_annotation(), _sample_suggestions())
    by_module = {item["module"]: item for item in backlog["items"]}

    guardrail = by_module["FrontendHumanLanguageMapping"]["ui_guardrail"]

    assert guardrail["scope"] == "terminal_user_visible_copy"
    assert guardrail["violation_policy"] == "fail_review"
    assert "heritage value" in guardrail["forbidden_terms"]
    assert "preservation grade" in guardrail["forbidden_terms"]
    assert "core_tension" in guardrail["forbidden_terms"]
    assert "用中文业务标签替换内部字段名" in guardrail["required_action"]


def test_frontend_language_guardrail_blocks_fixed_flow_titles_and_internal_runtime_terms():
    backlog = build_systemic_remediation_backlog(_sample_golden_annotation(), _sample_suggestions())
    by_module = {item["module"]: item for item in backlog["items"]}

    forbidden_terms = set(by_module["FrontendHumanLanguageMapping"]["ui_guardrail"]["forbidden_terms"])

    assert {
        "选择判断路径",
        "成立路径",
        "硬约束",
        "取舍边界",
        "风险阈值",
        "预算押注",
        "决策级变量",
        "activation pack",
        "knowledge package",
    }.issubset(forbidden_terms)


def test_activation_pack_candidate_is_governance_signal_not_runtime_warning():
    annotation = _sample_golden_annotation()
    annotation["items"].append(
        {
            "id": 191,
            "remediation_family": "常规空间分类复核",
            "current_project_type": "public_cultural",
            "confidence": 0.9,
            "warning_codes": "coverage_gap；activation_pack_candidate",
        }
    )

    backlog = build_systemic_remediation_backlog(annotation, _sample_suggestions())

    assert "activation_pack_candidate" not in backlog["summary"]["warning_counts"]
    assert backlog["summary"]["governance_signal_counts"]["activation_pack_candidate"] == 1
    assert any("基础空间推理框架" in principle for principle in backlog["principles"])

    knowledge = {item["module"]: item for item in backlog["items"]}["KnowledgeCoverageAndRecall"]
    assert "基础空间推理框架" in knowledge["mechanism"]
    assert "无专科包" not in knowledge["verification_gate"]


def test_systemic_backlog_reports_golden_pressure_drift_without_auto_sync():
    annotation = _sample_golden_annotation()
    annotation["items"].append(
        {
            "id": 191,
            "remediation_family": "常规空间分类复核",
            "current_project_type": "public_cultural",
            "confidence": 0.9,
            "warning_codes": "coverage_gap；activation_pack_candidate",
        }
    )

    backlog = build_systemic_remediation_backlog(
        annotation,
        _sample_suggestions(),
        pressure_result=_sample_pressure_result(),
    )

    drift = backlog["summary"]["baseline_drift"]

    assert drift["has_drift"] is True
    assert drift["policy"] == "report_only_never_auto_sync"
    assert drift["requires_human_review"] is True
    assert {
        "field": "warning_counts.coverage_gap",
        "golden": 1,
        "pressure": 0,
    } in drift["items"]
    assert "latest_pressure_summary" in backlog["summary"]


def test_systemic_remediation_backlog_uses_readable_chinese_governance_copy():
    backlog = build_systemic_remediation_backlog(_sample_golden_annotation(), _sample_suggestions())
    by_module = {item["module"]: item for item in backlog["items"]}

    assert any("不把单个案例写成固定规则" in item for item in backlog["principles"])
    assert any("基础空间推理框架" in item for item in backlog["principles"])
    assert any("不得自动进入正式 Registry 或知识库" in item for item in backlog["principles"])

    classification = by_module["SpaceClassificationService"]
    assert "空间主轴判定算法" in classification["mechanism"]
    assert "190 条 golden baseline 回归" in classification["verification_gate"]

    entry = by_module["SchemeAdvisorEntryService"]
    assert "核心矛盾" in entry["mechanism"]
    assert "真实目标" in entry["verification_gate"]

    frontend = by_module["FrontendHumanLanguageMapping"]
    assert "内部字段" in frontend["risk"]
    assert "人话标签" in frontend["mechanism"]
    assert "用中文业务标签替换内部字段名" in frontend["ui_guardrail"]["required_action"]

    encoded_text = "\n".join(
        backlog["principles"]
        + [
            str(item.get(key, ""))
            for item in backlog["items"]
            for key in ("risk", "mechanism", "verification_gate")
        ]
    )
    for marker in ["銆", "€", "绌洪", "鐭", "瑙", "鏍", "鍗"]:
        assert marker not in encoded_text


def test_systemic_remediation_items_include_algorithmic_methodology_not_sample_enumeration():
    backlog = build_systemic_remediation_backlog(_sample_golden_annotation(), _sample_suggestions())

    for item in backlog["items"]:
        assert item["decision_inputs"], item["module"]
        assert item["generalization_method"], item["module"]
        assert item["anti_hardcoding_policy"] == "样本编号只作为证据，不得作为运行时分支条件。"
        assert item["algorithm_verification"], item["module"]
        assert "sample_ids" not in item["generalization_method"]
        assert "id ==" not in item["generalization_method"]

    classification = {item["module"]: item for item in backlog["items"]}["SpaceClassificationService"]
    assert "空间载体" in classification["decision_inputs"]
    assert "使用者身份" in classification["decision_inputs"]
    assert "分层评分" in classification["generalization_method"]

    coverage = {item["module"]: item for item in backlog["items"]}["KnowledgeCoverageAndRecall"]
    assert "知识覆盖等级" in coverage["decision_inputs"]
    assert "先走基础空间推理框架" in coverage["generalization_method"]


def test_latest_governance_signals_are_routed_to_review_queues_not_left_as_counts():
    pressure_result = {
        "summary": {
            "total": 4,
            "passed": 4,
            "failed": 0,
            "with_warnings": 0,
            "with_governance_signals": 4,
        },
        "items": [
            {
                "id": 1,
                "governance_signals": [{"code": "coverage_gap"}],
            },
            {
                "id": 2,
                "governance_signals": [{"code": "knowledge_gap_ticket"}],
            },
            {
                "id": 3,
                "governance_signals": [{"code": "activation_pack_candidate"}],
            },
            {
                "id": 4,
                "governance_signals": [{"code": "knowledge_coverage_watch"}],
            },
        ],
    }

    backlog = build_systemic_remediation_backlog(
        _sample_golden_annotation(),
        _sample_suggestions(),
        pressure_result=pressure_result,
    )
    routing = backlog["summary"]["governance_signal_routing"]

    assert routing["coverage_gap"]["review_queue"] == "space_registry_review"
    assert routing["knowledge_gap_ticket"]["review_queue"] == "knowledge_asset_review"
    assert routing["activation_pack_candidate"]["review_queue"] == "activation_pack_review"
    assert routing["knowledge_coverage_watch"]["review_queue"] == "coverage_watch_pool"

    for code, route in routing.items():
        assert route["count"] == 1, code
        assert route["must_not_auto_promote"] is True
        assert route["candidate_kind"]
        assert route["allowed_action"]
        assert route["verification_gate"]
