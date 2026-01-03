"""
测试role_id标准化函数和交付物匹配逻辑

用于验证v7.109修复：任务审批界面显示搜索查询和概念图配置
"""

import sys

sys.path.insert(0, r"d:\11-20\langgraph-design")

from intelligent_project_analyzer.interaction.role_task_unified_review import _normalize_role_id


def test_normalize_role_id():
    """测试role_id标准化函数"""
    print("=" * 60)
    print("Test _normalize_role_id function")
    print("=" * 60)

    test_cases = [
        ("V2_设计总监_2-1", "2-1"),
        ("V3_叙事专家_3-1", "3-1"),
        ("V4_设计研究员_4-1", "4-1"),
        ("V5_场景专家_5-1", "5-1"),
        ("V6_首席工程师_6-1", "6-1"),
        ("2-1", "2-1"),
        ("3-1", "3-1"),
        ("", ""),
        (None, "None"),
    ]

    all_passed = True
    for input_id, expected_output in test_cases:
        result = _normalize_role_id(input_id)
        status = "PASS" if result == expected_output else "FAIL"

        if result != expected_output:
            all_passed = False

        print(f"[{status}] Input: {input_id!r:30} -> Output: {result!r:10} (Expected: {expected_output!r})")

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All test cases passed!")
    else:
        print("[FAIL] Some test cases failed!")
    print("=" * 60)
    return all_passed


def test_matching_scenario():
    """模拟交付物匹配场景"""
    print("\n" + "=" * 60)
    print("Test deliverable matching scenario")
    print("=" * 60)

    # 模拟deliverable_metadata
    deliverable_metadata = {
        "2-1_1_143022_abc": {
            "id": "2-1_1_143022_abc",
            "name": "整体设计方案",
            "description": "设计整体方案",
            "owner_role": "V2_设计总监_2-1",  # 完整格式
            "search_queries": ["整体设计方案 设计案例", "整体设计方案 最佳实践", "整体设计方案 研究资料"],
            "concept_image_config": {"count": 1, "editable": False, "max_count": 1},
        },
        "3-1_1_143025_def": {
            "id": "3-1_1_143025_def",
            "name": "用户体验叙事",
            "description": "用户体验故事",
            "owner_role": "V3_叙事专家_3-1",
            "search_queries": ["用户体验叙事案例", "storytelling best practices", "narrative design research"],
            "concept_image_config": {"count": 1, "editable": False, "max_count": 1},
        },
    }

    # 模拟selected_roles中的role_id（可能是完整格式或短格式）
    test_scenarios = [
        {"role_id": "V2_设计总监_2-1", "deliv_name": "整体设计方案", "expected_match": "2-1_1_143022_abc"},  # 完整格式
        {"role_id": "2-1", "deliv_name": "整体设计方案", "expected_match": "2-1_1_143022_abc"},  # 短格式
        {"role_id": "V3_叙事专家_3-1", "deliv_name": "用户体验叙事", "expected_match": "3-1_1_143025_def"},
    ]

    all_passed = True
    for scenario in test_scenarios:
        role_id = scenario["role_id"]
        deliv_name = scenario["deliv_name"]
        expected_match = scenario["expected_match"]

        # 标准化role_id
        normalized_role_id = _normalize_role_id(role_id)

        # 尝试匹配
        matching_metadata = None
        for deliv_id, metadata in deliverable_metadata.items():
            normalized_owner = _normalize_role_id(metadata.get("owner_role", ""))

            if metadata.get("name") == deliv_name and normalized_owner == normalized_role_id:
                matching_metadata = {
                    "id": deliv_id,
                    "name": metadata.get("name"),
                    "search_queries": metadata.get("search_queries", []),
                    "concept_image_config": metadata.get("concept_image_config", {}),
                }
                break

        if matching_metadata and matching_metadata["id"] == expected_match:
            print(f"\n[PASS] Scenario:")
            print(f"   Role ID: {role_id}")
            print(f"   Normalized: {normalized_role_id}")
            print(f"   Deliverable: {deliv_name}")
            print(f"   Matched ID: {matching_metadata['id']}")
            print(f"   Search queries: {len(matching_metadata['search_queries'])} items")
            print(f"   Concept config: {matching_metadata['concept_image_config']}")
        else:
            all_passed = False
            print(f"\n[FAIL] Scenario:")
            print(f"   Role ID: {role_id}")
            print(f"   Deliverable: {deliv_name}")
            print(f"   Expected: {expected_match}")
            print(f"   Actual: {matching_metadata['id'] if matching_metadata else 'None'}")

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All matching scenarios passed!")
    else:
        print("[FAIL] Some matching scenarios failed!")
    print("=" * 60)
    return all_passed


if __name__ == "__main__":
    print("\n[TEST] Starting role_id normalization and matching tests\n")

    test1_passed = test_normalize_role_id()
    test2_passed = test_matching_scenario()

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Normalization Test: {'PASS' if test1_passed else 'FAIL'}")
    print(f"Matching Test: {'PASS' if test2_passed else 'FAIL'}")

    if test1_passed and test2_passed:
        print("\n[SUCCESS] All tests passed! Fix should work correctly.")
        sys.exit(0)
    else:
        print("\n[WARNING] Some tests failed! Please check the code.")
        sys.exit(1)
