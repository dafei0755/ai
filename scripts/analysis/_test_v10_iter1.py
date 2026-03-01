"""v10.0 Iteration 1 smoke tests"""

import sys

sys.path.insert(0, ".")


def main():
    passed = 0
    total = 6

    # Test 1: DWP with new visual fields
    from intelligent_project_analyzer.core.task_oriented_models import (
        DeliverableWorkPackage,
        DeliverableOutput,
        DeliverableFormat,
        Priority,
    )

    dwp = DeliverableWorkPackage(
        dwp_id="DWP-001",
        name="Test DWP",
        description="Test",
        deliverable_type="analysis_report",
        format=DeliverableFormat.ANALYSIS,
        source_task_ids=["CT-001"],
        owner_role_id="2-1",
        success_criteria=["完成测试"],
        visual_type="photorealistic_rendering",
        keywords=["keyword1", "keyword2"],
    )
    assert dwp.visual_type == "photorealistic_rendering"
    assert dwp.keywords == ["keyword1", "keyword2"]
    passed += 1
    print("✅ Test 1: DWP visual fields OK")

    # Test 2: DeliverableOutput.dwp_id is now str with default
    do = DeliverableOutput(
        content="test content",
        format="analysis",
        quality_score=0.9,
        deliverable_name="测试交付物",
        completion_status="completed",
    )
    assert isinstance(do.dwp_id, str)
    assert do.dwp_id == ""
    assert do.source_task_id == ""
    passed += 1
    print("✅ Test 2: DeliverableOutput dwp_id default OK")

    # Test 3: import deliverable_id_generator_node functions
    from intelligent_project_analyzer.workflow.nodes.deliverable_id_generator_node import (
        _build_metadata_from_dwps,
        _extract_keywords_from_questionnaire,
        deliverable_id_generator_node,
    )

    passed += 1
    print("✅ Test 3: Import OK")

    # Test 4: _build_metadata_from_dwps
    dwp_dicts = [
        {
            "dwp_id": "DWP-001",
            "name": "整体设计方案",
            "description": "项目整体设计",
            "owner_role_id": "2-1",
            "visual_type": "photorealistic_rendering",
            "keywords": ["现代", "简约"],
            "format": "architectural_design",
            "source_task_ids": ["CT-001"],
        },
        {
            "dwp_id": "DWP-002",
            "name": "叙事方案",
            "description": "文化叙事",
            "owner_role_id": "3-1",
            "visual_type": "artistic_rendering",
            "keywords": ["文化", "传承"],
            "format": "narrative",
            "source_task_ids": ["CT-002"],
        },
    ]
    selected_roles = [
        {"role_id": "2-1", "dynamic_role_name": "设计总监"},
        {"role_id": "3-1", "dynamic_role_name": "叙事专家"},
    ]
    qk = {"material_keywords": ["木"], "emotional_keywords": ["温馨"], "style_label": "现代"}

    result = _build_metadata_from_dwps(dwp_dicts, selected_roles, qk)
    meta = result["deliverable_metadata"]
    owner_map = result["deliverable_owner_map"]

    assert len(meta) == 2, f"Expected 2 metadata, got {len(meta)}"
    assert len(owner_map) == 2
    assert len(owner_map["2-1"]) == 1
    assert len(owner_map["3-1"]) == 1

    for did, m in meta.items():
        assert "dwp_id" in m, f"Missing dwp_id in {did}"
        assert m["dwp_id"].startswith("DWP-")
        assert "constraints" in m
        assert m["constraints"]["visual_type"] in ("photorealistic_rendering", "artistic_rendering")
    passed += 1
    print("✅ Test 4: _build_metadata_from_dwps OK")

    # Test 5: deliverable_id_generator_node DWP-first path
    state = {
        "deliverable_work_packages": dwp_dicts,
        "strategic_analysis": {"selected_roles": selected_roles},
        "questionnaire_summary": {"profile_label": "现代", "answers": {"gap_answers": {}, "radar_values": {}}},
    }
    result = deliverable_id_generator_node(state)
    assert len(result["deliverable_metadata"]) == 2
    assert "[DWP-First]" in result["detail"]
    passed += 1
    print("✅ Test 5: DWP-first path in node OK")

    # Test 6: Legacy path (no DWPs)
    state_legacy = {
        "deliverable_work_packages": [],
        "strategic_analysis": {"selected_roles": ["2-1", "3-1"]},
        "user_input": "test project",
        "structured_requirements": {},
        "questionnaire_summary": {"profile_label": "", "answers": {"gap_answers": {}, "radar_values": {}}},
    }
    result_legacy = deliverable_id_generator_node(state_legacy)
    assert len(result_legacy["deliverable_metadata"]) > 0
    assert "[DWP-First]" not in result_legacy.get("detail", "")
    passed += 1
    print("✅ Test 6: Legacy path still works")

    print(f"\n🎉 All {passed}/{total} v10.0 Iteration 1 tests passed!")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
