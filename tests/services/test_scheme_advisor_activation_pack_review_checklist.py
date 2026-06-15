from pathlib import Path

from intelligent_project_analyzer.services.scheme_advisor_activation_pack_review_checklist import (
    build_review_checklist,
    write_review_checklist_markdown,
)


def _sample_scope_draft_report():
    return {
        "schema_version": "activation_pack_scope_draft_report.v1",
        "governance_boundary": {
            "runtime_load_allowed": False,
            "formal_pack_write_allowed": False,
            "human_review_required": True,
        },
        "drafts": [
            {
                "draft_id": "activation_scope_draft.public_cultural.cultural_public_experience",
                "project_type": "public_cultural",
                "space_axis_id": "cultural_public_experience",
                "space_axis_label": "文化公共空间：叙事体验、展陈秩序与公众使用",
                "sample_count": 12,
                "average_confidence": 0.823,
                "priority_score": 136,
                "runtime_load_allowed": False,
                "sample_ids": [45, 54, 70],
                "must_define_sections": [
                    "routing_boundary",
                    "required_slots",
                    "risk_control",
                    "knowledge_recall_plan",
                ],
                "minimum_review_gates": [
                    "确认是否确实需要正式激活包，而不是继续使用基础空间推理框架。",
                    "确认适用边界、不适用边界和父级项目类型。",
                ],
            }
        ],
    }


def test_review_checklist_requires_human_decision_and_forbids_runtime_write():
    checklist = build_review_checklist(_sample_scope_draft_report())

    assert checklist["schema_version"] == "activation_pack_scope_review_checklist.v1"
    assert checklist["governance_boundary"]["runtime_load_allowed"] is False
    assert checklist["governance_boundary"]["formal_pack_write_allowed"] is False
    assert checklist["governance_boundary"]["human_review_required"] is True
    assert checklist["allowed_decisions"] == [
        "approve_for_formal_pack_authoring",
        "request_more_evidence",
        "keep_observing",
        "reject_scope",
    ]

    item = checklist["review_items"][0]
    assert item["draft_id"] == "activation_scope_draft.public_cultural.cultural_public_experience"
    assert item["default_decision"] == "request_more_evidence"
    assert item["required_review_roles"] == [
        "domain_expert",
        "knowledge_architect",
        "product_owner",
    ]
    assert item["promotion_blockers"] == []
    assert "适用边界" in " ".join(item["checkpoints"])
    assert "不适用边界" in " ".join(item["checkpoints"])
    assert "required_slots" in " ".join(item["checkpoints"])


def test_review_checklist_blocks_drafts_that_allow_runtime_loading():
    scope_report = _sample_scope_draft_report()
    scope_report["drafts"][0]["runtime_load_allowed"] = True

    checklist = build_review_checklist(scope_report)
    item = checklist["review_items"][0]

    assert item["default_decision"] == "reject_scope"
    assert "runtime_load_allowed_must_be_false" in item["promotion_blockers"]


def test_review_checklist_markdown_is_actionable_and_chinese(tmp_path: Path):
    checklist = build_review_checklist(_sample_scope_draft_report())
    output_path = tmp_path / "review-checklist.md"

    write_review_checklist_markdown(checklist, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert "# 激活包范围草案人工复核清单" in text
    assert "不得自动写入正式激活包" in text
    assert "approve_for_formal_pack_authoring" in text
    assert "文化公共空间" in text
    assert "琛" not in text
    assert "鍊" not in text
