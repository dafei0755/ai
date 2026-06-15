import csv
import json
from pathlib import Path


AUDIT_DIR = Path("docs/system-completeness-audit")
BASE_JSON = AUDIT_DIR / "scheme-advisor-190-golden-annotation-base-2026-03-22.json"
BASE_CSV = AUDIT_DIR / "scheme-advisor-190-golden-annotation-base-2026-03-22.csv"
PRESSURE_JSON = AUDIT_DIR / "scheme-advisor-pressure-test-2026-03-22.json"
LOW_JSON = AUDIT_DIR / "scheme-advisor-low-confidence-attribution-2026-03-22.json"
PRIORITY_JSON = AUDIT_DIR / "scheme-advisor-golden-review-priority-2026-03-22.json"
PRIORITY_CSV = AUDIT_DIR / "scheme-advisor-golden-review-priority-2026-03-22.csv"
BATCH01_JSON = AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-2026-03-22.json"
BATCH01_CSV = AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-2026-03-22.csv"
BATCH01_SUGGESTIONS_JSON = AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-suggestions-2026-03-22.json"
BATCH01_SUGGESTIONS_CSV = AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-suggestions-2026-03-22.csv"
REVIEW_WORKBENCH_JSON = AUDIT_DIR / "scheme-advisor-golden-review-workbench-2026-03-22.json"
REVIEW_WORKBENCH_CSV = AUDIT_DIR / "scheme-advisor-golden-review-workbench-2026-03-22.csv"
REVIEW_WORKBENCH_MD = AUDIT_DIR / "scheme-advisor-golden-review-workbench-2026-03-22.md"
MISSING_GOLD_REVIEW_WORKBENCH_CSV = AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.csv"
UPDATED_GOLDEN_JSON = AUDIT_DIR / "scheme-advisor-190-golden-annotation-updated-2026-03-22.json"
REVIEW_SYNC_REPORT_JSON = AUDIT_DIR / "scheme-advisor-golden-review-workbench-sync-report-2026-03-22.json"
QUALITY_GATE_JSON = AUDIT_DIR / "scheme-advisor-golden-quality-gate-2026-03-22.json"
QUALITY_GATE_RUNBOOK_MD = AUDIT_DIR / "scheme-advisor-golden-quality-gate-runbook-2026-03-22.md"
REVIEW_COMPLETION_JSON = AUDIT_DIR / "scheme-advisor-golden-review-completion-2026-03-22.json"
REVIEW_COMPLETION_MD = AUDIT_DIR / "scheme-advisor-golden-review-completion-2026-03-22.md"
REVIEW_STATUS_JSON = AUDIT_DIR / "scheme-advisor-golden-review-status-2026-03-22.json"
SYSTEMIC_REMEDIATION_JSON = AUDIT_DIR / "scheme-advisor-systemic-remediation-backlog-2026-03-22.json"
SYSTEMIC_REMEDIATION_CSV = AUDIT_DIR / "scheme-advisor-systemic-remediation-backlog-2026-03-22.csv"


REQUIRED_BASE_FIELDS = {
    "id",
    "prompt_excerpt",
    "current_project_type",
    "confidence",
    "warning_codes",
    "candidate_spatial_extent",
    "candidate_project_stage",
    "candidate_user_intent",
    "candidate_core_tension",
    "candidate_allowed_output_depth",
    "remediation_family",
    "needs_human_review",
    "gold_expected_project_type",
    "gold_expected_spatial_extent",
    "gold_expected_project_stage",
    "gold_expected_core_tension",
    "gold_expected_output_depth",
    "review_decision",
    "review_note",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_golden_annotation_base_covers_all_190_pressure_prompts():
    data = _load_json(BASE_JSON)

    assert data["schema_version"] == "scheme_advisor_golden_annotation_base.v1"
    assert data["summary"]["total"] == 190
    assert len(data["items"]) == 190
    assert REQUIRED_BASE_FIELDS.issubset(set(data["fields"]))
    assert all(REQUIRED_BASE_FIELDS.issubset(item) for item in data["items"])


def test_golden_annotation_csv_is_excel_friendly_and_aligned_with_json():
    data = _load_json(BASE_JSON)
    with BASE_CSV.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == data["summary"]["total"]
    assert REQUIRED_BASE_FIELDS.issubset(rows[0])
    assert rows[1]["candidate_core_tension"] == "成就表达、家族传承与日常安住的平衡"


def test_golden_annotation_groups_are_systemic_not_case_by_case():
    data = _load_json(BASE_JSON)
    counts = data["summary"]["remediation_family_counts"]

    assert counts["空间尺度与阶段封顶"] >= 20
    assert counts["住宅身份/家庭关系/情绪修复"] >= 20
    assert counts["未来/极端环境韧性空间"] >= 10
    assert "类型边界低置信" in counts


def test_low_confidence_attribution_keeps_governance_scope_explicit():
    data = _load_json(LOW_JSON)

    assert data["schema_version"] == "scheme_advisor_low_confidence_attribution.v1"
    assert data["summary"]["total"] == len(data["items"])
    assert data["summary"]["total"] > 0
    assert data["summary"]["by_remediation_family"]["空间尺度与阶段封顶"] >= 1
    assert data["summary"]["by_candidate_output_depth"]["条件判断级：先补类型/尺度/阶段，避免直接给确定方案"] >= 1


def test_no_mojibake_or_placeholder_family_names_in_golden_outputs():
    data = _load_json(BASE_JSON)
    blob = json.dumps(data, ensure_ascii=False)

    forbidden_fragments = ["????", "待定", "TODO", "以后再说"]
    assert not any(fragment in blob for fragment in forbidden_fragments)
    assert "成就表达、家族传承与日常安住的平衡" in blob


def test_priority_review_artifact_focuses_human_effort_on_high_risk_rows():
    data = _load_json(PRIORITY_JSON)
    with PRIORITY_CSV.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert data["schema_version"] == "scheme_advisor_golden_review_priority.v1"
    assert data["summary"]["total"] == len(rows)
    assert data["summary"]["total"] >= 40
    assert data["items"][0]["review_priority"] == "P0"
    assert data["items"][0]["remediation_family"] in {
        "非空间类型入口/设计决策论证",
        "空间尺度与阶段封顶",
        "未来/极端环境韧性空间",
        "类型边界低置信",
    }
    assert all(row["review_priority"] in {"P0", "P1", "P2"} for row in rows)
    assert any(row["id"] == "2" for row in rows)


def test_first_p0_review_batch_is_small_balanced_and_actionable():
    data = _load_json(BATCH01_JSON)
    with BATCH01_CSV.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert data["schema_version"] == "scheme_advisor_golden_review_batch.v1"
    assert data["batch_id"] == "scheme-advisor-p0-batch-01"
    assert data["summary"]["total"] == len(rows)
    assert 20 <= len(rows) <= 32
    assert data["summary"]["priority_counts"]["P0"] >= 20
    assert data["summary"]["anchor_items"] >= 1
    assert len(data["summary"]["family_counts"]) >= 6
    assert all(row["review_task"] for row in rows)
    assert all(row["fill_fields"] == "gold_expected_project_type;gold_expected_spatial_extent;gold_expected_project_stage;gold_expected_core_tension;gold_expected_output_depth" for row in rows)
    assert any(row["id"] == "2" and row["review_priority"] == "P1" for row in rows)


def test_first_p0_review_suggestions_are_advisory_not_approved_gold():
    data = _load_json(BATCH01_SUGGESTIONS_JSON)
    with BATCH01_SUGGESTIONS_CSV.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    markdown = (AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-suggestions-2026-03-22.md").read_text(
        encoding="utf-8"
    )

    assert data["schema_version"] == "scheme_advisor_golden_review_suggestions.v1"
    assert data["summary"]["total"] == len(rows)
    assert data["summary"]["needs_human_decision"] > data["summary"]["ready_for_fast_review"]
    assert "suggested_gold_expected_project_type" in rows[0]
    assert "gold_expected_project_type" not in rows[0]
    assert any(row["id"] == "2" and row["suggested_gold_expected_project_type"] == "personal_residential" for row in rows)
    assert any(row["id"] == "50" and row["suggested_gold_expected_project_type"] == "" for row in rows)
    assert "问题摘要" in markdown
    assert "建议空间尺度" in markdown
    assert "建议项目阶段" in markdown
    assert "建议输出深度" in markdown
    assert "一个再婚家庭" in markdown


def test_golden_review_workbench_combines_suggestions_and_blank_human_fields():
    data = _load_json(REVIEW_WORKBENCH_JSON)
    with REVIEW_WORKBENCH_CSV.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    markdown = REVIEW_WORKBENCH_MD.read_text(encoding="utf-8")

    assert data["schema_version"] == "scheme_advisor_golden_review_workbench.v1"
    assert data["summary"]["total"] == len(rows) == 29
    assert data["summary"]["ready_for_fast_review"] == 3
    assert data["summary"]["needs_human_decision"] == 26
    assert data["summary"]["gold_fields_are_blank"] is True
    assert "suggested_gold_expected_project_type" in rows[0]
    assert "gold_expected_project_type" in rows[0]
    assert all(row["gold_expected_project_type"] == "" for row in rows)
    assert any(row["id"] == "2" and row["suggested_gold_expected_project_type"] == "personal_residential" for row in rows)
    assert "人工确认后填写" in markdown
    assert "不要直接把建议值当事实" in markdown


def test_golden_workbench_sync_report_does_not_auto_promote_suggestions():
    data = _load_json(REVIEW_SYNC_REPORT_JSON)

    assert data["schema_version"] == "scheme_advisor_golden_review_workbench_sync.v1"
    assert data["summary"]["review_rows"] == 29
    assert data["summary"]["workbench_rows"] == 28
    assert data["summary"]["updated_rows"] == 0
    assert data["summary"]["copied_fields"] == 0
    assert data["summary"]["missing_workbench_rows"] == 1
    assert data["missing_workbench_ids"] == ["2"]
    assert data["source_workbench_csv_path"].endswith("scheme-advisor-missing-gold-review-workbench-2026-03-22.csv")


def test_quality_gate_artifact_is_derived_from_p0_review_batch():
    gate = _load_json(QUALITY_GATE_JSON)
    batch = _load_json(BATCH01_JSON)
    p0_ids = {
        str(item["id"])
        for item in batch["items"]
        if item.get("review_priority") == "P0"
    }
    failure_ids = {str(failure["id"]) for failure in gate.get("failures", [])}

    assert gate["schema_version"] == "scheme_advisor_golden_quality_gate.v1"
    assert gate["source_pressure_path"].endswith(str(PRESSURE_JSON).replace("\\", "/")) or gate[
        "source_pressure_path"
    ].endswith(str(PRESSURE_JSON))
    assert gate["source_golden_path"].endswith(str(UPDATED_GOLDEN_JSON).replace("\\", "/")) or gate[
        "source_golden_path"
    ].endswith(str(UPDATED_GOLDEN_JSON))
    assert gate["summary"]["required_items"] == len(p0_ids)
    assert gate["summary"]["required_fields"] == [
        "gold_expected_project_type",
        "gold_expected_core_tension",
        "gold_expected_output_depth",
    ]
    assert gate["summary"]["gate_status"] in {"pass", "fail"}
    if gate["summary"]["gate_status"] == "fail":
        assert failure_ids
        assert failure_ids.issubset(p0_ids)
    else:
        assert gate["failures"] == []


def test_quality_gate_runbook_preserves_human_review_boundary():
    text = QUALITY_GATE_RUNBOOK_MD.read_text(encoding="utf-8")

    assert "人工复核" in text
    assert "不得由系统自动填写 gold" in text
    assert "scheme-advisor-golden-review-batch-01-p0-2026-03-22.csv" in text
    assert "python scripts/build_scheme_advisor_golden_review_workbench.py" in text
    assert "scheme-advisor-golden-review-workbench-2026-03-22.csv" in text
    assert "scheme-advisor-missing-gold-review-workbench-2026-03-22.csv" in text
    assert "python scripts/sync_scheme_advisor_golden_review_from_workbench.py" in text
    assert "scheme-advisor-golden-review-workbench-sync-report-2026-03-22.json" in text
    assert "scheme-advisor-190-golden-annotation-base-2026-03-22.json" in text
    assert "apply_review_csv_file" in text
    assert "python scripts/apply_scheme_advisor_golden_review.py" in text
    assert "scheme-advisor-190-golden-annotation-updated-2026-03-22.json" in text
    assert "python scripts/check_scheme_advisor_golden_review_progress.py" in text
    assert "scheme-advisor-golden-review-completion-2026-03-22.json" in text
    assert "python scripts/build_scheme_advisor_golden_review_status.py" in text
    assert "scheme-advisor-golden-review-status-2026-03-22.json" in text
    assert "python scripts/run_scheme_advisor_golden_quality_gate.py" in text
    assert "退出码 1" in text
    assert "gate_status: fail" in text


def test_review_completion_artifacts_show_human_fill_gaps():
    data = _load_json(REVIEW_COMPLETION_JSON)
    markdown = REVIEW_COMPLETION_MD.read_text(encoding="utf-8")

    assert data["schema_version"] == "scheme_advisor_golden_review_completion.v1"
    assert data["summary"]["total_rows"] == 29
    assert data["summary"]["incomplete_rows"] >= 1
    assert "gold_expected_project_type" in data["summary"]["missing_by_field"]
    assert "# 方案高参 Golden 复核进度" in markdown
    assert "未完成" in markdown
    assert "| 50 |" in markdown
    assert "`gold_expected_project_type`" in markdown


def test_golden_review_status_artifact_is_admin_ready_summary():
    data = _load_json(REVIEW_STATUS_JSON)

    assert data["schema_version"] == "scheme_advisor_golden_review_status.v1"
    assert data["review_status"] == "needs_human_review"
    assert data["next_action"] == "fill_required_gold_fields"
    assert data["completion"]["total_rows"] == 29
    assert data["completion"]["incomplete_rows"] == 29
    assert data["review_workbench"]["summary"]["total"] == 28
    assert data["review_workbench"]["summary"]["policy"] == "human_review_only_never_auto_fill_gold"
    assert data["workbench_sync"]["summary"]["updated_rows"] == 0
    assert data["workbench_sync"]["summary"]["copied_fields"] == 0
    assert data["apply_report"]["review_rows"] == 29
    assert data["quality_gate"]["gate_status"] == "fail"
    assert data["quality_gate"]["required_items"] == 28


def test_systemic_remediation_backlog_is_module_level_and_not_case_patch():
    data = _load_json(SYSTEMIC_REMEDIATION_JSON)
    with SYSTEMIC_REMEDIATION_CSV.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert data["schema_version"] == "scheme_advisor_systemic_remediation_backlog.v1"
    assert data["summary"]["total_pressure_items"] == 190
    assert data["summary"]["needs_human_review"] == 126
    assert data["summary"]["must_not_hardcode_cases"] is True
    assert data["summary"]["systemic_actions"] == len(rows)
    assert data["summary"]["systemic_actions"] >= 8

    modules = {row["module"] for row in rows}
    assert {"SpaceClassificationService", "SchemeAdvisorEntryService", "FrontendHumanLanguageMapping"}.issubset(modules)
    assert all(row["mechanism"] and row["verification_gate"] for row in rows)
    assert not any("单个案例" in row["mechanism"] for row in rows)
