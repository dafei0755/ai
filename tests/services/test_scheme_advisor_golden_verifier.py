from intelligent_project_analyzer.services.scheme_advisor_golden_verifier import (
    apply_review_csv_file,
    apply_review_rows_to_golden_annotation,
    build_golden_verification_report,
    build_golden_quality_gate_report,
    build_missing_gold_review_rows,
    build_review_completion_report,
    build_review_suggestion_rows,
    build_review_workbench_rows,
    sync_review_csv_rows_from_workbench,
    main,
    write_missing_gold_review_artifacts,
    write_review_suggestion_artifacts,
    write_review_workbench_artifacts,
)
import pytest


def test_golden_verifier_checks_only_human_filled_expectations():
    pressure_result = {
        "items": [
            {
                "id": 2,
                "project_type": "personal_residential",
                "candidate_spatial_extent": "住宅/单项目级",
            }
        ]
    }
    golden_annotation = {
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "personal_residential",
                "gold_expected_spatial_extent": "住宅/单项目级",
                "gold_expected_project_stage": "",
            }
        ]
    }

    report = build_golden_verification_report(pressure_result, golden_annotation)

    assert report["summary"]["active_gold_items"] == 1
    assert report["summary"]["checks"] == 2
    assert report["summary"]["passed"] == 2
    assert report["summary"]["failed"] == 0
    assert report["items"][0]["status"] == "pass"


def test_golden_verifier_reports_mismatches_without_stopping_other_checks():
    pressure_result = {
        "items": [
            {
                "id": 2,
                "project_type": "urban_renewal_heritage",
                "candidate_core_tension": "历史建筑价值优先",
            }
        ]
    }
    golden_annotation = {
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "personal_residential",
                "gold_expected_core_tension": "成就表达、家族传承与日常安住的平衡",
            }
        ]
    }

    report = build_golden_verification_report(pressure_result, golden_annotation)

    assert report["summary"]["checks"] == 2
    assert report["summary"]["failed"] == 2
    assert report["items"][0]["status"] == "fail"
    assert {check["field"] for check in report["items"][0]["checks"]} == {
        "gold_expected_project_type",
        "gold_expected_core_tension",
    }


def test_golden_quality_gate_requires_required_p0_items_to_have_gold_fields():
    pressure_result = {
        "items": [
            {
                "id": 2,
                "project_type": "personal_residential",
                "candidate_core_tension": "成就表达、家族传承与日常安住的平衡",
                "candidate_allowed_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
            }
        ]
    }
    golden_annotation = {
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "",
                "gold_expected_core_tension": "",
                "gold_expected_output_depth": "",
            }
        ]
    }

    report = build_golden_quality_gate_report(
        pressure_result,
        golden_annotation,
        required_item_ids=[2],
        required_gold_fields=[
            "gold_expected_project_type",
            "gold_expected_core_tension",
            "gold_expected_output_depth",
        ],
    )

    assert report["summary"]["gate_status"] == "fail"
    assert report["summary"]["required_items"] == 1
    assert report["summary"]["required_items_with_complete_gold"] == 0
    assert report["failures"][0]["code"] == "required_gold_fields_missing"
    assert report["failures"][0]["id"] == 2


def test_golden_quality_gate_summarizes_missing_gold_fields_for_review_action():
    pressure_result = {
        "items": [
            {
                "id": 2,
                "input_mode": "project",
                "project_type": "personal_residential",
                "candidate_core_tension": "身份表达、家族传承与日常安住",
                "candidate_allowed_output_depth": "条件方案级：可给方案框架，但要声明前提和缺口",
            },
            {
                "id": 83,
                "input_mode": "decision_argument",
                "project_type": None,
                "candidate_core_tension": "材料替换的短期成本、长期价值与证据链是否成立",
                "candidate_allowed_output_depth": "决策论证级：可给判断框架与证据清单，不输出空间方案",
            },
        ]
    }
    golden_annotation = {
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "",
                "gold_expected_core_tension": "身份表达、家族传承与日常安住",
                "gold_expected_output_depth": "",
            },
            {
                "id": 83,
                "gold_expected_project_type": "",
                "gold_expected_core_tension": "",
                "gold_expected_output_depth": "决策论证级：可给判断框架与证据清单，不输出空间方案",
            },
        ]
    }

    report = build_golden_quality_gate_report(
        pressure_result,
        golden_annotation,
        required_item_ids=[2, 83],
        required_gold_fields=[
            "gold_expected_project_type",
            "gold_expected_core_tension",
            "gold_expected_output_depth",
        ],
    )

    assert report["summary"]["gate_status"] == "fail"
    assert report["summary"]["missing_required_gold_items"] == 2
    assert report["summary"]["missing_required_gold_fields"] == 3
    assert report["summary"]["missing_required_gold_by_field"] == {
        "gold_expected_project_type": 1,
        "gold_expected_core_tension": 1,
        "gold_expected_output_depth": 1,
    }
    assert report["missing_gold_summary"][0] == {
        "id": "2",
        "input_mode": "project",
        "missing_fields": ["gold_expected_project_type", "gold_expected_output_depth"],
        "next_action": "人工复核并填写缺失的黄金字段；不要直接采用系统建议值。",
    }
    assert report["missing_gold_summary"][1] == {
        "id": "83",
        "input_mode": "decision_argument",
        "missing_fields": ["gold_expected_core_tension"],
        "next_action": "人工复核并填写缺失的黄金字段；不要直接采用系统建议值。",
    }


def test_missing_gold_review_rows_filter_workbench_by_quality_gate_missing_items():
    quality_gate_report = {
        "missing_gold_summary": [
            {
                "id": "2",
                "input_mode": "project",
                "missing_fields": ["gold_expected_project_type", "gold_expected_output_depth"],
                "next_action": "人工复核并填写缺失的黄金字段；不要直接采用系统建议值。",
            },
            {
                "id": "83",
                "input_mode": "decision_argument",
                "missing_fields": ["gold_expected_core_tension"],
                "next_action": "人工复核并填写缺失的黄金字段；不要直接采用系统建议值。",
            },
        ]
    }
    review_workbench = {
        "items": [
            {
                "id": 2,
                "prompt_excerpt": "深圳湾一线海景别墅...",
                "candidate_project_type": "personal_residential",
                "candidate_core_tension": "身份表达、家族传承与日常安住",
                "candidate_allowed_output_depth": "条件方案级：可给方案框架，但要声明前提和缺口",
                "suggested_gold_expected_project_type": "personal_residential",
                "suggested_gold_expected_core_tension": "身份表达、家族传承与日常安住",
                "suggested_gold_expected_output_depth": "条件方案级：可给方案框架，但要声明前提和缺口",
                "gold_expected_project_type": "",
                "gold_expected_core_tension": "",
                "gold_expected_output_depth": "",
            },
            {
                "id": 83,
                "prompt_excerpt": "材料更换是否值得...",
                "candidate_project_type": "",
                "candidate_core_tension": "材料替换的短期成本、长期价值与证据链是否成立",
                "candidate_allowed_output_depth": "决策论证级：可给判断框架与证据清单，不输出空间方案",
                "suggested_gold_expected_project_type": "",
                "suggested_gold_expected_core_tension": "材料替换的短期成本、长期价值与证据链是否成立",
                "suggested_gold_expected_output_depth": "决策论证级：可给判断框架与证据清单，不输出空间方案",
                "gold_expected_project_type": "",
                "gold_expected_core_tension": "",
                "gold_expected_output_depth": "",
            },
            {
                "id": 99,
                "prompt_excerpt": "不在门禁缺口中",
            },
        ]
    }

    rows = build_missing_gold_review_rows(quality_gate_report, review_workbench)

    assert [row["id"] for row in rows] == ["2", "83"]
    assert rows[0]["missing_fields"] == "gold_expected_project_type；gold_expected_output_depth"
    assert rows[0]["fields_to_fill"] == "gold_expected_project_type；gold_expected_output_depth"
    assert rows[0]["fields_to_fill_zh"] == "空间分类；输出深度"
    assert "稳定空间类型" in rows[0]["field_review_guidance"]
    assert "人工确认后" in rows[0]["human_review_policy"]
    assert rows[0]["suggested_gold_expected_project_type"] == "personal_residential"
    assert rows[1]["input_mode"] == "decision_argument"
    assert rows[1]["missing_fields"] == "gold_expected_core_tension"
    assert rows[1]["fields_to_fill"] == "gold_expected_core_tension"
    assert rows[1]["fields_to_fill_zh"] == "核心矛盾"
    assert rows[1]["suggested_gold_expected_project_type"] == ""


def test_write_missing_gold_review_artifacts_outputs_actionable_files(tmp_path):
    quality_gate_path = tmp_path / "quality-gate.json"
    workbench_path = tmp_path / "workbench.json"
    output_json = tmp_path / "missing.json"
    output_csv = tmp_path / "missing.csv"
    output_md = tmp_path / "missing.md"

    quality_gate_path.write_text(
        """
        {
          "summary": {"gate_status": "fail"},
          "missing_gold_summary": [
            {
              "id": "83",
              "input_mode": "decision_argument",
              "missing_fields": ["gold_expected_core_tension"],
              "next_action": "人工复核并填写缺失的黄金字段；不要直接采用系统建议值。"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    workbench_path.write_text(
        """
        {
          "items": [
            {
              "id": 83,
              "prompt_excerpt": "材料替换是否值得？",
              "candidate_core_tension": "材料替换的短期成本、长期价值与证据链是否成立",
              "suggested_gold_expected_core_tension": "材料替换的短期成本、长期价值与证据链是否成立",
              "gold_expected_core_tension": ""
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    report = write_missing_gold_review_artifacts(
        quality_gate_path=quality_gate_path,
        review_workbench_path=workbench_path,
        output_json=output_json,
        output_csv=output_csv,
        output_md=output_md,
    )

    assert report["schema_version"] == "scheme_advisor_missing_gold_review_workbench.v1"
    assert report["summary"]["total"] == 1
    assert report["items"][0]["id"] == "83"
    assert report["items"][0]["fields_to_fill_zh"] == "核心矛盾"
    assert "gold_expected_core_tension" in output_csv.read_text(encoding="utf-8-sig")
    assert "待填字段（中文）" in output_csv.read_text(encoding="utf-8-sig")
    md = output_md.read_text(encoding="utf-8")
    assert "待人工补齐 Golden 字段" in md
    assert "材料替换是否值得？" in md
    assert "核心矛盾" in md
    assert "不要直接采用系统建议值" in md


def test_golden_quality_gate_uses_input_mode_specific_required_fields():
    pressure_result = {
        "items": [
            {
                "id": 83,
                "input_mode": "decision_argument",
                "project_type": None,
                "candidate_core_tension": "短期成本与长期价值是否成立",
                "candidate_allowed_output_depth": "决策论证级：可给判断框架与证据清单，不输出空间方案",
            }
        ]
    }
    golden_annotation = {
        "items": [
            {
                "id": 83,
                "gold_expected_project_type": "",
                "gold_expected_core_tension": "短期成本与长期价值是否成立",
                "gold_expected_output_depth": "决策论证级：可给判断框架与证据清单，不输出空间方案",
            }
        ]
    }

    report = build_golden_quality_gate_report(
        pressure_result,
        golden_annotation,
        required_item_ids=[83],
        required_gold_fields=[
            "gold_expected_project_type",
            "gold_expected_core_tension",
            "gold_expected_output_depth",
        ],
    )

    assert report["summary"]["gate_status"] == "pass"
    assert report["summary"]["required_items_with_complete_gold"] == 1
    assert report["summary"]["passed_checks"] == 2
    assert report["failures"] == []


def test_review_completion_report_shows_missing_gold_fields_without_filling_them():
    review_rows = [
        {
            "id": "50",
            "gold_expected_project_type": "",
            "gold_expected_core_tension": "family_privacy_balance",
            "gold_expected_output_depth": "",
        },
        {
            "id": "28",
            "gold_expected_project_type": "personal_residential",
            "gold_expected_core_tension": "achievement_family_balance",
            "gold_expected_output_depth": "strategy_level",
        },
    ]

    report = build_review_completion_report(
        review_rows,
        required_gold_fields=[
            "gold_expected_project_type",
            "gold_expected_core_tension",
            "gold_expected_output_depth",
        ],
    )

    assert report["schema_version"] == "scheme_advisor_golden_review_completion.v1"
    assert report["summary"]["total_rows"] == 2
    assert report["summary"]["complete_rows"] == 1
    assert report["summary"]["incomplete_rows"] == 1
    assert report["summary"]["missing_by_field"] == {
        "gold_expected_project_type": 1,
        "gold_expected_core_tension": 0,
        "gold_expected_output_depth": 1,
    }
    assert report["incomplete_items"] == [
        {
            "id": "50",
            "missing_fields": ["gold_expected_project_type", "gold_expected_output_depth"],
        }
    ]
    assert review_rows[0]["gold_expected_project_type"] == ""


def test_golden_quality_gate_fails_when_required_gold_item_no_longer_matches_pressure():
    pressure_result = {
        "items": [
            {
                "id": 2,
                "project_type": "urban_renewal_heritage",
                "candidate_core_tension": "历史建筑价值优先",
                "candidate_allowed_output_depth": "方案框架级：可进入结构化设计建议",
            }
        ]
    }
    golden_annotation = {
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "personal_residential",
                "gold_expected_core_tension": "成就表达、家族传承与日常安住的平衡",
                "gold_expected_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
            }
        ]
    }

    report = build_golden_quality_gate_report(
        pressure_result,
        golden_annotation,
        required_item_ids=[2],
        required_gold_fields=[
            "gold_expected_project_type",
            "gold_expected_core_tension",
            "gold_expected_output_depth",
        ],
    )

    assert report["summary"]["gate_status"] == "fail"
    assert report["summary"]["failed_checks"] == 3
    assert report["failures"][0]["code"] == "golden_mismatch"


def test_golden_quality_gate_passes_when_required_gold_item_is_complete_and_matching():
    pressure_result = {
        "items": [
            {
                "id": 2,
                "project_type": "personal_residential",
                "candidate_core_tension": "成就表达、家族传承与日常安住的平衡",
                "candidate_allowed_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
            }
        ]
    }
    golden_annotation = {
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "personal_residential",
                "gold_expected_core_tension": "成就表达、家族传承与日常安住的平衡",
                "gold_expected_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
            }
        ]
    }

    report = build_golden_quality_gate_report(
        pressure_result,
        golden_annotation,
        required_item_ids=[2],
        required_gold_fields=[
            "gold_expected_project_type",
            "gold_expected_core_tension",
            "gold_expected_output_depth",
        ],
    )

    assert report["summary"]["gate_status"] == "pass"
    assert report["summary"]["required_items_with_complete_gold"] == 1
    assert report["summary"]["passed_checks"] == 3
    assert report["failures"] == []


def test_cli_writes_quality_gate_report_when_required_item_ids_are_provided(tmp_path, monkeypatch, capsys):
    pressure_path = tmp_path / "pressure.json"
    golden_path = tmp_path / "golden.json"
    verification_output = tmp_path / "verification.json"
    markdown_output = tmp_path / "verification.md"
    quality_gate_output = tmp_path / "quality-gate.json"

    pressure_path.write_text(
        """{
  "items": [
    {
      "id": 2,
      "project_type": "personal_residential",
      "candidate_core_tension": "achievement_family_balance"
    }
  ]
}""",
        encoding="utf-8",
    )
    golden_path.write_text(
        """{
  "items": [
    {
      "id": 2,
      "gold_expected_project_type": "personal_residential",
      "gold_expected_core_tension": "achievement_family_balance"
    }
  ]
}""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "scheme_advisor_golden_verifier.py",
            "--pressure",
            str(pressure_path),
            "--golden",
            str(golden_path),
            "--output",
            str(verification_output),
            "--markdown-output",
            str(markdown_output),
            "--quality-gate-output",
            str(quality_gate_output),
            "--required-item-ids",
            "2",
            "--required-gold-fields",
            "gold_expected_project_type,gold_expected_core_tension",
        ],
    )

    main()

    captured = capsys.readouterr()
    gate = load_json_for_test(quality_gate_output)
    verification = load_json_for_test(verification_output)

    assert gate["schema_version"] == "scheme_advisor_golden_quality_gate.v1"
    assert gate["summary"]["gate_status"] == "pass"
    assert gate["summary"]["required_items"] == 1
    assert gate["summary"]["passed_checks"] == 2
    assert verification["summary"]["passed"] == 2
    assert '"quality_gate_status": "pass"' in captured.out


def test_cli_can_fail_process_when_quality_gate_fails(tmp_path, monkeypatch):
    pressure_path = tmp_path / "pressure.json"
    golden_path = tmp_path / "golden.json"
    verification_output = tmp_path / "verification.json"
    markdown_output = tmp_path / "verification.md"
    quality_gate_output = tmp_path / "quality-gate.json"

    pressure_path.write_text(
        """{
  "items": [
    {
      "id": 2,
      "project_type": "personal_residential",
      "candidate_core_tension": "achievement_family_balance"
    }
  ]
}""",
        encoding="utf-8",
    )
    golden_path.write_text(
        """{
  "items": [
    {
      "id": 2,
      "gold_expected_project_type": "",
      "gold_expected_core_tension": ""
    }
  ]
}""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "scheme_advisor_golden_verifier.py",
            "--pressure",
            str(pressure_path),
            "--golden",
            str(golden_path),
            "--output",
            str(verification_output),
            "--markdown-output",
            str(markdown_output),
            "--quality-gate-output",
            str(quality_gate_output),
            "--required-item-ids",
            "2",
            "--required-gold-fields",
            "gold_expected_project_type,gold_expected_core_tension",
            "--fail-on-quality-gate",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    gate = load_json_for_test(quality_gate_output)
    assert exc_info.value.code == 1
    assert gate["summary"]["gate_status"] == "fail"
    assert gate["failures"][0]["code"] == "required_gold_fields_missing"


def test_cli_can_take_required_items_from_review_batch(tmp_path, monkeypatch, capsys):
    pressure_path = tmp_path / "pressure.json"
    golden_path = tmp_path / "golden.json"
    review_batch_path = tmp_path / "review-batch.json"
    verification_output = tmp_path / "verification.json"
    markdown_output = tmp_path / "verification.md"
    quality_gate_output = tmp_path / "quality-gate.json"

    pressure_path.write_text(
        """{
  "items": [
    {
      "id": 50,
      "project_type": "children_family",
      "candidate_core_tension": "family_privacy_balance"
    },
    {
      "id": 28,
      "project_type": "personal_residential",
      "candidate_core_tension": "achievement_family_balance"
    },
    {
      "id": 99,
      "project_type": "commercial_dining",
      "candidate_core_tension": "operation_efficiency"
    }
  ]
}""",
        encoding="utf-8",
    )
    golden_path.write_text(
        """{
  "items": [
    {
      "id": 50,
      "gold_expected_project_type": "",
      "gold_expected_core_tension": ""
    },
    {
      "id": 28,
      "gold_expected_project_type": "",
      "gold_expected_core_tension": ""
    },
    {
      "id": 99,
      "gold_expected_project_type": "",
      "gold_expected_core_tension": ""
    }
  ]
}""",
        encoding="utf-8",
    )
    review_batch_path.write_text(
        """{
  "items": [
    {"id": 50, "review_priority": "P0"},
    {"id": 28, "review_priority": "P0"},
    {"id": 99, "review_priority": "P1"}
  ]
}""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "scheme_advisor_golden_verifier.py",
            "--pressure",
            str(pressure_path),
            "--golden",
            str(golden_path),
            "--output",
            str(verification_output),
            "--markdown-output",
            str(markdown_output),
            "--quality-gate-output",
            str(quality_gate_output),
            "--required-review-batch",
            str(review_batch_path),
            "--required-review-priority",
            "P0",
            "--required-gold-fields",
            "gold_expected_project_type,gold_expected_core_tension",
        ],
    )

    main()

    captured = capsys.readouterr()
    gate = load_json_for_test(quality_gate_output)
    failure_ids = {failure["id"] for failure in gate["failures"]}
    assert gate["summary"]["gate_status"] == "fail"
    assert gate["summary"]["required_items"] == 2
    assert failure_ids == {50, 28}
    assert 99 not in failure_ids
    assert '"quality_gate_status": "fail"' in captured.out


def test_golden_verifier_skips_expectations_when_pressure_output_has_no_observed_field():
    pressure_result = {"items": [{"id": 172, "project_type": "landscape_outdoor"}]}
    golden_annotation = {
        "items": [
            {
                "id": 172,
                "gold_expected_project_type": "landscape_outdoor",
                "gold_expected_output_depth": "策略框架级：可给定位/功能/运营逻辑，不输出室内施工级细节",
            }
        ]
    }

    report = build_golden_verification_report(pressure_result, golden_annotation)

    assert report["summary"]["checks"] == 1
    assert report["summary"]["passed"] == 1
    assert report["summary"]["skipped"] == 1
    assert report["items"][0]["status"] == "partial"
    assert report["items"][0]["checks"][1]["status"] == "skipped"


def test_apply_review_rows_updates_only_non_empty_review_fields():
    golden_annotation = {
        "schema_version": "scheme_advisor_golden_annotation_base.v1",
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "old_type",
                "gold_expected_core_tension": "keep_existing_core_tension",
                "review_decision": "",
                "review_note": "",
            }
        ],
    }
    review_rows = [
        {
            "id": "2",
            "gold_expected_project_type": "personal_residential",
            "gold_expected_core_tension": "",
            "review_decision": "approved",
            "review_note": "confirmed by human review",
        }
    ]

    result = apply_review_rows_to_golden_annotation(golden_annotation, review_rows)
    updated_item = result["updated_annotation"]["items"][0]

    assert updated_item["gold_expected_project_type"] == "personal_residential"
    assert updated_item["gold_expected_core_tension"] == "keep_existing_core_tension"
    assert updated_item["review_decision"] == "approved"
    assert result["summary"]["updated_items"] == 1
    assert result["summary"]["updated_fields"] == 3
    assert result["summary"]["skipped_empty_fields"] == 1


def test_apply_review_rows_requires_approved_decision_before_promoting_gold_fields():
    golden_annotation = {
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "",
                "gold_expected_core_tension": "",
                "review_decision": "",
                "review_note": "",
            }
        ]
    }
    review_rows = [
        {
            "id": "2",
            "gold_expected_project_type": "personal_residential",
            "gold_expected_core_tension": "创业者身份和家庭精神表达",
            "review_decision": "",
            "review_note": "draft only",
        }
    ]

    result = apply_review_rows_to_golden_annotation(golden_annotation, review_rows)
    updated_item = result["updated_annotation"]["items"][0]

    assert updated_item["gold_expected_project_type"] == ""
    assert updated_item["gold_expected_core_tension"] == ""
    assert updated_item["review_decision"] == ""
    assert updated_item["review_note"] == "draft only"
    assert result["summary"]["review_rows_pending_decision"] == 1
    assert result["summary"]["updated_fields"] == 1


def test_apply_review_rows_reports_unknown_ids_and_does_not_mutate_source():
    golden_annotation = {
        "items": [
            {
                "id": 2,
                "gold_expected_project_type": "",
            }
        ]
    }
    review_rows = [
        {
            "id": "999",
            "gold_expected_project_type": "commercial_dining",
        }
    ]

    result = apply_review_rows_to_golden_annotation(golden_annotation, review_rows)

    assert result["summary"]["unknown_review_rows"] == 1
    assert result["unknown_ids"] == ["999"]
    assert result["updated_annotation"]["items"][0]["gold_expected_project_type"] == ""
    assert golden_annotation["items"][0]["gold_expected_project_type"] == ""


def test_apply_review_csv_file_writes_updated_copy_and_report_without_overwriting_source(tmp_path):
    golden_path = tmp_path / "golden.json"
    review_csv_path = tmp_path / "review.csv"
    updated_output = tmp_path / "golden.updated.json"
    report_output = tmp_path / "apply-report.json"

    golden_path.write_text(
        """{
  "schema_version": "scheme_advisor_golden_annotation_base.v1",
  "items": [
    {
      "id": 2,
      "gold_expected_project_type": "",
      "gold_expected_spatial_extent": "",
      "review_decision": ""
    }
  ]
}""",
        encoding="utf-8",
    )
    review_csv_path.write_text(
        "id,gold_expected_project_type,gold_expected_spatial_extent,review_decision\n"
        "2,personal_residential,住宅/单项目级,approved\n",
        encoding="utf-8-sig",
    )

    report = apply_review_csv_file(
        golden_path=golden_path,
        review_csv_path=review_csv_path,
        updated_golden_output=updated_output,
        apply_report_output=report_output,
    )

    source = load_json_for_test(golden_path)
    updated = load_json_for_test(updated_output)
    report_file = load_json_for_test(report_output)

    assert source["items"][0]["gold_expected_project_type"] == ""
    assert updated["items"][0]["gold_expected_project_type"] == "personal_residential"
    assert updated["items"][0]["gold_expected_spatial_extent"] == "住宅/单项目级"
    assert report["summary"]["updated_fields"] == 3
    assert report_file["summary"]["updated_fields"] == 3
    assert "updated_annotation" not in report_file


def test_review_suggestion_rows_do_not_promote_low_confidence_type_to_gold():
    review_batch = {
        "items": [
            {
                "id": 50,
                "prompt_excerpt": "一个再婚家庭，需要为两个孩子创造公共交流区和绝对隐私。",
                "current_project_type": "children_family",
                "confidence": 0.32,
                "warning_codes": "low_classification_confidence；coverage_gap",
                "candidate_spatial_extent": "住宅/单项目级",
                "candidate_project_stage": "概念方案",
                "candidate_core_tension": "情绪支持、隐私边界与日常使用秩序",
                "candidate_allowed_output_depth": "条件判断级：先补类型/尺度/阶段，避免直接给确定方案",
                "remediation_family": "住宅身份/家庭关系/情绪修复",
                "review_priority": "P0",
            }
        ]
    }

    rows = build_review_suggestion_rows(review_batch)

    assert len(rows) == 1
    row = rows[0]
    assert "gold_expected_project_type" not in row
    assert row["suggested_gold_expected_project_type"] == ""
    assert row["suggested_gold_expected_spatial_extent"] == "住宅/单项目级"
    assert row["suggested_gold_expected_core_tension"] == "情绪支持、隐私边界与日常使用秩序"
    assert row["suggestion_decision"] == "needs_human_decision"
    assert "分类置信度不足" in row["suggestion_note"]


def test_review_suggestion_artifacts_are_written_without_overwriting_review_csv(tmp_path):
    review_batch_path = tmp_path / "batch.json"
    output_json = tmp_path / "suggestions.json"
    output_csv = tmp_path / "suggestions.csv"
    output_md = tmp_path / "suggestions.md"

    review_batch_path.write_text(
        """{
  "items": [
    {
      "id": 2,
      "prompt_excerpt": "深圳湾一线海景别墅，第一代创业者，家族传承与内心回归。",
      "current_project_type": "personal_residential",
      "confidence": 0.9,
      "warning_codes": "",
      "candidate_spatial_extent": "住宅/单项目级",
      "candidate_project_stage": "概念方案",
      "candidate_core_tension": "成就表达、家族传承与日常安住的平衡",
      "candidate_allowed_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
      "remediation_family": "住宅身份/家庭关系/情绪修复",
      "review_priority": "P1"
    }
  ]
}""",
        encoding="utf-8",
    )

    report = write_review_suggestion_artifacts(
        review_batch_path=review_batch_path,
        output_json=output_json,
        output_csv=output_csv,
        output_md=output_md,
    )

    suggestions = load_json_for_test(output_json)
    assert report["summary"]["total"] == 1
    assert report["summary"]["ready_for_fast_review"] == 1
    assert suggestions["items"][0]["suggested_gold_expected_project_type"] == "personal_residential"
    assert "gold_expected_project_type" not in suggestions["items"][0]
    assert output_csv.read_text(encoding="utf-8-sig").startswith("id,")
    assert "人工复核建议" in output_md.read_text(encoding="utf-8")


def test_review_workbench_combines_candidates_suggestions_and_blank_gold_fields():
    review_batch = {
        "items": [
            {
                "id": 2,
                "review_task": "确认住宅身份主轴",
                "prompt_excerpt": "深圳湾一线海景别墅，第一代创业者。",
                "current_project_type": "personal_residential",
                "confidence": 0.9,
                "candidate_spatial_extent": "住宅/单项目级",
                "candidate_project_stage": "概念方案",
                "candidate_core_tension": "成就表达、家族传承与日常安住的平衡",
                "candidate_allowed_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
                "review_priority": "P1",
                "remediation_family": "住宅身份/家庭关系/情绪修复",
            }
        ]
    }
    suggestions = {
        "items": [
            {
                "id": 2,
                "suggested_gold_expected_project_type": "personal_residential",
                "suggested_gold_expected_spatial_extent": "住宅/单项目级",
                "suggested_gold_expected_project_stage": "概念方案",
                "suggested_gold_expected_core_tension": "成就表达、家族传承与日常安住的平衡",
                "suggested_gold_expected_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
                "suggestion_decision": "ready_for_fast_review",
                "suggestion_note": "可快速复核",
            }
        ]
    }

    rows = build_review_workbench_rows(review_batch, suggestions)

    assert len(rows) == 1
    row = rows[0]
    assert row["suggestion_decision"] == "ready_for_fast_review"
    assert row["candidate_project_type"] == "personal_residential"
    assert row["suggested_gold_expected_project_type"] == "personal_residential"
    assert row["gold_expected_project_type"] == ""
    assert row["gold_expected_core_tension"] == ""
    assert row["review_decision"] == ""
    assert row["review_instruction"] == "人工确认后填写 gold_expected_*，不要直接把建议值当事实。"


def test_review_workbench_artifacts_are_written_as_human_editing_sheet(tmp_path):
    review_batch_path = tmp_path / "batch.json"
    suggestions_path = tmp_path / "suggestions.json"
    output_json = tmp_path / "workbench.json"
    output_csv = tmp_path / "workbench.csv"
    output_md = tmp_path / "workbench.md"

    review_batch_path.write_text(
        """{
  "items": [
    {
      "id": 2,
      "review_task": "确认住宅身份主轴",
      "prompt_excerpt": "深圳湾一线海景别墅，第一代创业者。",
      "current_project_type": "personal_residential",
      "confidence": 0.9,
      "candidate_spatial_extent": "住宅/单项目级",
      "candidate_project_stage": "概念方案",
      "candidate_core_tension": "成就表达、家族传承与日常安住的平衡",
      "candidate_allowed_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
      "review_priority": "P1",
      "remediation_family": "住宅身份/家庭关系/情绪修复"
    }
  ]
}""",
        encoding="utf-8",
    )
    suggestions_path.write_text(
        """{
  "items": [
    {
      "id": 2,
      "suggested_gold_expected_project_type": "personal_residential",
      "suggested_gold_expected_spatial_extent": "住宅/单项目级",
      "suggested_gold_expected_project_stage": "概念方案",
      "suggested_gold_expected_core_tension": "成就表达、家族传承与日常安住的平衡",
      "suggested_gold_expected_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
      "suggestion_decision": "ready_for_fast_review",
      "suggestion_note": "可快速复核"
    }
  ]
}""",
        encoding="utf-8",
    )

    report = write_review_workbench_artifacts(
        review_batch_path=review_batch_path,
        suggestions_path=suggestions_path,
        output_json=output_json,
        output_csv=output_csv,
        output_md=output_md,
    )

    assert report["summary"]["total"] == 1
    assert report["summary"]["ready_for_fast_review"] == 1
    csv_text = output_csv.read_text(encoding="utf-8-sig")
    assert "suggested_gold_expected_project_type" in csv_text
    assert "gold_expected_project_type" in csv_text
    assert ",personal_residential," in csv_text
    assert "人工确认后填写" in output_md.read_text(encoding="utf-8")


def test_sync_review_rows_from_workbench_copies_only_human_filled_gold_fields():
    review_rows = [
        {
            "id": "2",
            "gold_expected_project_type": "",
            "gold_expected_core_tension": "",
            "gold_expected_output_depth": "",
            "review_decision": "",
            "review_note": "",
        }
    ]
    workbench_rows = [
        {
            "id": "2",
            "suggested_gold_expected_project_type": "wrong_auto_suggestion",
            "suggested_gold_expected_core_tension": "wrong_auto_tension",
            "suggested_gold_expected_output_depth": "wrong_auto_depth",
            "gold_expected_project_type": "personal_residential",
            "gold_expected_core_tension": "成就表达、家族传承与日常安住的平衡",
            "gold_expected_output_depth": "通用方法论级：可给空间逻辑，需声明非专科覆盖",
            "review_decision": "approved",
            "review_note": "人工确认。",
        }
    ]

    result = sync_review_csv_rows_from_workbench(review_rows, workbench_rows)

    assert result["summary"]["updated_rows"] == 1
    assert result["summary"]["copied_fields"] == 5
    updated = result["review_rows"][0]
    assert updated["gold_expected_project_type"] == "personal_residential"
    assert updated["gold_expected_core_tension"] == "成就表达、家族传承与日常安住的平衡"
    assert updated["gold_expected_output_depth"] == "通用方法论级：可给空间逻辑，需声明非专科覆盖"
    assert updated["review_decision"] == "approved"
    assert updated["review_note"] == "人工确认。"
    assert updated["gold_expected_project_type"] != "wrong_auto_suggestion"


def test_sync_review_rows_from_workbench_ignores_unfilled_gold_even_when_suggestions_exist():
    review_rows = [
        {
            "id": "50",
            "gold_expected_project_type": "",
            "gold_expected_core_tension": "",
            "gold_expected_output_depth": "",
        }
    ]
    workbench_rows = [
        {
            "id": "50",
            "suggested_gold_expected_project_type": "children_family",
            "suggested_gold_expected_core_tension": "情绪支持、隐私边界与日常使用秩序",
            "suggested_gold_expected_output_depth": "条件判断级：先补类型/尺度/阶段，避免直接给确定方案",
            "gold_expected_project_type": "",
            "gold_expected_core_tension": "",
            "gold_expected_output_depth": "",
        }
    ]

    result = sync_review_csv_rows_from_workbench(review_rows, workbench_rows)

    assert result["summary"]["updated_rows"] == 0
    assert result["summary"]["copied_fields"] == 0
    assert result["summary"]["skipped_empty_fields"] >= 3
    assert result["review_rows"][0]["gold_expected_project_type"] == ""


def load_json_for_test(path):
    import json

    return json.loads(path.read_text(encoding="utf-8"))
