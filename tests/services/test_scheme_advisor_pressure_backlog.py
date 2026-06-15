from intelligent_project_analyzer.services.scheme_advisor_pressure_backlog import (
    build_optimization_backlog,
    write_backlog_markdown,
)
from pathlib import Path


def _sample_pressure_result():
    return {
        "summary": {"total": 2, "passed": 2, "failed": 0, "with_warnings": 2},
        "items": [
            {
                "id": 1,
                "project_type": "personal_residential",
                "confidence": 0.5,
                "prompt": "深圳湾一线海景别墅，业主为第一代创业者。",
                "warning_issues": [
                    {"code": "low_classification_confidence"},
                    {"code": "coverage_gap"},
                    {"code": "knowledge_gap_ticket"},
                ],
                "governance_signals": [{"code": "activation_pack_candidate"}],
            },
            {
                "id": 2,
                "project_type": "commercial_dining",
                "confidence": 0.9,
                "prompt": "30平米奶茶店，半年回本。",
                "warning_issues": [],
                "governance_signals": [{"code": "activation_pack_candidate"}],
            },
        ],
    }


def test_pressure_backlog_uses_readable_chinese_governance_text():
    backlog = build_optimization_backlog(_sample_pressure_result())

    rule = backlog["governance_boundary"]["rule"]
    allowed = " ".join(backlog["governance_boundary"]["allowed_here"])

    assert "不得自动写入正式 Registry 或知识库" in rule
    assert "候选清单" in allowed
    assert "琛" not in rule
    assert "鍊" not in allowed
    assert backlog["summary"]["activation_pack_candidate_types"] == 2


def test_pressure_backlog_markdown_is_readable_chinese():
    backlog = build_optimization_backlog(_sample_pressure_result())
    output_dir = Path(".pytest_tmp")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "scheme_advisor_pressure_backlog_test.md"

    write_backlog_markdown(backlog, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "# 方案高参压测优化待办清单" in text
    assert "## 治理边界" in text
    assert "低置信样本复核" in text
    assert "琛" not in text
    assert "鍊" not in text
    output_path.unlink(missing_ok=True)


def test_pressure_backlog_separates_coverage_watch_from_activation_pack_candidates():
    pressure_result = _sample_pressure_result()
    pressure_result["items"].append(
        {
            "id": 3,
            "project_type": "special_function",
            "confidence": 0.82,
            "prompt": "future resilience prototype",
            "warning_issues": [],
            "governance_signals": [{"code": "knowledge_coverage_watch"}],
        }
    )

    backlog = build_optimization_backlog(pressure_result)

    assert backlog["summary"]["activation_pack_candidate_types"] == 2
    assert backlog["summary"]["knowledge_coverage_watch_types"] == 1
    assert backlog["knowledge_coverage_watch"][0]["project_type"] == "special_function"


def test_pressure_backlog_routes_each_gap_to_governed_review_track():
    backlog = build_optimization_backlog(_sample_pressure_result())

    coverage = backlog["coverage_gap_by_type"][0]
    knowledge = backlog["knowledge_gap_by_type"][0]
    activation = next(
        row for row in backlog["activation_pack_candidates"]
        if row["project_type"] == "personal_residential"
    )

    assert coverage["candidate_kind"] == "registry_boundary_candidate"
    assert coverage["governance_mode"] == "registry_governed"
    assert coverage["review_queue"] == "space_registry_review"
    assert coverage["promotion_rule"] == "human_review_required"
    assert "回归" in coverage["verification_gate"]

    assert knowledge["candidate_kind"] == "knowledge_card_candidate"
    assert knowledge["governance_mode"] == "knowledge_governed"
    assert knowledge["review_queue"] == "knowledge_asset_review"
    assert knowledge["promotion_rule"] == "human_review_required"

    assert activation["candidate_kind"] == "activation_pack_candidate"
    assert activation["governance_mode"] == "knowledge_governed"
    assert activation["review_queue"] == "activation_pack_review"
    assert activation["promotion_rule"] == "frequency_and_value_then_human_review"


def test_pressure_backlog_reads_coverage_gaps_from_governance_signals():
    pressure_result = {
        "summary": {"total": 1, "passed": 1, "failed": 0, "with_warnings": 0},
        "items": [
            {
                "id": 11,
                "project_type": "personal_residential",
                "confidence": 0.9,
                "prompt": "深圳湾一线海景别墅，业主为第一代创业者。",
                "warning_issues": [],
                "governance_signals": [
                    {"code": "coverage_gap"},
                    {"code": "knowledge_gap_ticket"},
                ],
            }
        ],
    }

    backlog = build_optimization_backlog(pressure_result)

    assert backlog["summary"]["coverage_gap_types"] == 1
    assert backlog["summary"]["knowledge_gap_types"] == 1
    assert backlog["coverage_gap_by_type"][0]["project_type"] == "personal_residential"
    assert backlog["knowledge_gap_by_type"][0]["project_type"] == "personal_residential"


def test_activation_pack_priority_queue_clusters_by_type_and_space_axis():
    items = []
    for index in range(1, 7):
        items.append(
            {
                "id": index,
                "project_type": "type_a",
                "space_axis_id": "axis_focus",
                "space_axis_label": "聚焦主轴",
                "confidence": 0.86,
                "prompt": f"高频聚焦样本 {index}",
                "warning_issues": [],
                "governance_signals": [{"code": "activation_pack_candidate"}],
            }
        )
    for index in range(7, 10):
        items.append(
            {
                "id": index,
                "project_type": "type_b",
                "space_axis_id": "axis_small",
                "space_axis_label": "小样本主轴",
                "confidence": 0.82,
                "prompt": f"中频样本 {index}",
                "warning_issues": [],
                "governance_signals": [{"code": "activation_pack_candidate"}],
            }
        )
    items.append(
        {
            "id": 10,
            "project_type": "type_a",
            "space_axis_id": "axis_single",
            "space_axis_label": "单点主轴",
            "confidence": 0.9,
            "prompt": "单点样本",
            "warning_issues": [],
            "governance_signals": [{"code": "activation_pack_candidate"}],
        }
    )

    backlog = build_optimization_backlog(
        {"summary": {"total": 10, "passed": 10, "failed": 0}, "items": items}
    )
    queue = backlog["activation_pack_priority_queue"]

    assert [row["project_type"] for row in queue[:2]] == ["type_a", "type_b"]
    assert queue[0]["space_axis_id"] == "axis_focus"
    assert queue[0]["sample_count"] == 6
    assert queue[0]["readiness_band"] == "ready_for_scope"
    assert queue[0]["priority_score"] > queue[1]["priority_score"]
    assert queue[1]["readiness_band"] == "candidate_pool"
    assert queue[-1]["readiness_band"] == "observe_only"
    assert queue[-1]["requires_human_review"] is True


def test_activation_pack_priority_queue_is_rendered_in_markdown():
    items = [
        {
            "id": index,
            "project_type": "type_a",
            "space_axis_id": "axis_focus",
            "space_axis_label": "聚焦主轴",
            "confidence": 0.86,
            "prompt": f"高频聚焦样本 {index}",
            "warning_issues": [],
            "governance_signals": [{"code": "activation_pack_candidate"}],
        }
        for index in range(1, 7)
    ]
    backlog = build_optimization_backlog(
        {"summary": {"total": 6, "passed": 6, "failed": 0}, "items": items}
    )
    output_dir = Path(".pytest_tmp")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "activation_pack_priority_queue_test.md"

    write_backlog_markdown(backlog, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "## P2 激活包建设优先队列" in text
    assert "优先定义包范围" in text
    assert "axis_focus" in text
    output_path.unlink(missing_ok=True)
