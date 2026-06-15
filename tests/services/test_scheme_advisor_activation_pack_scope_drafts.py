from pathlib import Path

from intelligent_project_analyzer.services.scheme_advisor_activation_pack_scope_drafts import (
    build_scope_draft_report,
    write_scope_draft_markdown,
)


def _sample_backlog():
    return {
        "activation_pack_priority_queue": [
            {
                "project_type": "public_cultural",
                "space_axis_id": "cultural_public_experience",
                "space_axis_label": "公共文化体验",
                "sample_count": 8,
                "sample_ids": [101, 102, 103],
                "average_confidence": 0.82,
                "priority_score": 96,
                "readiness_band": "ready_for_scope",
            },
            {
                "project_type": "personal_residential",
                "space_axis_id": "private_residential_life_order",
                "space_axis_label": "私宅生活秩序",
                "sample_count": 4,
                "sample_ids": [201, 202],
                "average_confidence": 0.75,
                "priority_score": 55,
                "readiness_band": "candidate_pool",
            },
        ]
    }


def _sample_pressure_result():
    return {
        "items": [
            {
                "id": 101,
                "project_type": "public_cultural",
                "space_axis_id": "cultural_public_experience",
                "prompt": "小型私人博物馆与教学空间，需要展陈路径与教学空间比例。",
            },
            {
                "id": 102,
                "project_type": "public_cultural",
                "space_axis_id": "cultural_public_experience",
                "prompt": "城市文化展馆，需要公众教育路径和展陈节奏。",
            },
            {
                "id": 103,
                "project_type": "public_cultural",
                "space_axis_id": "cultural_public_experience",
                "prompt": "艺术中心更新，需要公共体验和文化叙事。",
            },
            {
                "id": 201,
                "project_type": "personal_residential",
                "space_axis_id": "private_residential_life_order",
                "prompt": "深圳湾一线海景别墅，业主为第一代创业者。",
            },
        ]
    }


def test_scope_draft_report_only_uses_ready_clusters_and_is_not_runtime_loadable():
    report = build_scope_draft_report(
        _sample_backlog(),
        _sample_pressure_result(),
        max_drafts=3,
    )

    assert report["schema_version"] == "activation_pack_scope_draft_report.v1"
    assert report["governance_boundary"]["runtime_load_allowed"] is False
    assert report["governance_boundary"]["formal_pack_write_allowed"] is False
    assert len(report["drafts"]) == 1

    draft = report["drafts"][0]
    assert draft["draft_id"] == "activation_scope_draft.public_cultural.cultural_public_experience"
    assert draft["status"] == "draft_needs_human_review"
    assert draft["runtime_load_allowed"] is False
    assert draft["project_type"] == "public_cultural"
    assert draft["space_axis_id"] == "cultural_public_experience"
    assert draft["sample_count"] == 8
    assert draft["sample_prompts"][0]["id"] == 101
    assert "正式激活包" in " ".join(draft["minimum_review_gates"])
    assert "required_slots" in draft["must_define_sections"]
    assert "risk_control" in draft["must_define_sections"]


def test_scope_draft_report_respects_max_drafts():
    backlog = _sample_backlog()
    backlog["activation_pack_priority_queue"].insert(
        0,
        {
            "project_type": "commercial_retail",
            "space_axis_id": "retail_brand_conversion",
            "space_axis_label": "零售品牌转化",
            "sample_count": 9,
            "sample_ids": [301],
            "average_confidence": 0.88,
            "priority_score": 108,
            "readiness_band": "ready_for_scope",
        },
    )
    pressure = _sample_pressure_result()
    pressure["items"].append(
        {
            "id": 301,
            "project_type": "commercial_retail",
            "space_axis_id": "retail_brand_conversion",
            "prompt": "零售旗舰店，需要品牌差异化和消费转化路径。",
        }
    )

    report = build_scope_draft_report(backlog, pressure, max_drafts=1)

    assert [draft["project_type"] for draft in report["drafts"]] == ["commercial_retail"]


def test_scope_draft_markdown_declares_human_review_boundary(tmp_path: Path):
    report = build_scope_draft_report(
        _sample_backlog(),
        _sample_pressure_result(),
        max_drafts=3,
    )
    output_path = tmp_path / "scope-drafts.md"

    write_scope_draft_markdown(report, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "# 激活包范围草案" in text
    assert "不是正式运行时激活包" in text
    assert "activation_scope_draft.public_cultural.cultural_public_experience" in text
    assert "小型私人博物馆" in text
