"""
测试问卷数据利用功能（v7.121）

验证 deliverable_id_generator_node.py 是否正确读取和利用问卷数据
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intelligent_project_analyzer.workflow.nodes.deliverable_id_generator_node import (
    _extract_keywords_from_questionnaire,
    _generate_role_specific_deliverables,
)


def test_extract_keywords_from_questionnaire():
    """Test keyword extraction from questionnaire"""

    # Mock questionnaire data
    gap_answers = {
        "q1": "希望客厅有大量自然光，但阳台朝北采光不足，需要通过设计改善。预算50万，希望用环保材料。",
        "q2": "想保留渔村特色，比如渔网纹理、海洋蓝色、风化木质感。但不要太复古，要现代感。",
        "q3": "家里有两个小孩，需要考虑安全性和收纳空间。",
    }

    profile_label = "现代海洋风"

    radar_values = {"美学风格": 8.5, "功能性": 9.0, "预算控制": 7.0, "安全性": 8.0, "收纳能力": 9.5}

    # Extract keywords
    keywords = _extract_keywords_from_questionnaire(gap_answers, profile_label, radar_values)

    # Verify results
    print("[TEST] Keyword extraction:")
    print(f"  Style label: {keywords.get('style_label')}")
    print(f"  Material keywords: {keywords.get('material_keywords')}")
    print(f"  Functional keywords: {keywords.get('functional_keywords')}")
    print(f"  Budget keywords: {keywords.get('budget_keywords')}")
    print(f"  Emotional keywords: {keywords.get('emotional_keywords')}")
    print(f"  Color palette: {keywords.get('color_palette')}")

    # Assertions
    assert keywords.get("style_label") == "现代海洋风"
    assert "50万预算" in keywords.get("budget_keywords", [])
    assert "采光" in keywords.get("functional_keywords", [])
    assert "安全" in keywords.get("functional_keywords", []) or "儿童" in keywords.get("functional_keywords", [])
    assert "现代" in keywords.get("emotional_keywords", [])

    print("[PASS] Keyword extraction test passed!\n")
    return keywords


def test_generate_role_specific_deliverables():
    """Test deliverable generation with project context"""

    # Mock data
    role_id = "2-1"
    role_base_type = "V2"
    user_input = "renovate 60sqm Shekou fishing village apartment, budget 500k, preserve culture"

    structured_requirements = {
        "physical_context": {"location": "Shenzhen Shekou Fishing Village", "space_type": "60sqm old apartment"},
        "design_challenge": {"budget": "500k"},
    }

    questionnaire_keywords = {
        "style_label": "Modern Maritime",
        "material_keywords": ["fishing net texture", "weathered wood", "eco-friendly materials"],
        "functional_keywords": ["lighting optimization", "safety", "storage"],
        "budget_keywords": ["500k budget"],
        "emotional_keywords": ["modern"],
        "color_palette": "ocean blue, weathered wood tones",
    }

    confirmed_core_tasks = []

    # Generate deliverables
    deliverables = _generate_role_specific_deliverables(
        role_id=role_id,
        role_base_type=role_base_type,
        user_input=user_input,
        structured_requirements=structured_requirements,
        questionnaire_keywords=questionnaire_keywords,
        confirmed_core_tasks=confirmed_core_tasks,
    )

    # Verify results
    print("[PASS] Deliverable generation test:")
    for idx, deliverable in enumerate(deliverables, 1):
        print(f"\n  Deliverable {idx}:")
        print(f"    Name: {deliverable.get('name')}")
        print(f"    Description: {deliverable.get('description')}")
        print(f"    Keywords: {deliverable.get('keywords')}")
        print(f"    Constraints: {deliverable.get('constraints')}")

    # Assertions
    assert len(deliverables) > 0
    first_deliverable = deliverables[0]

    # Check project-specific keywords
    keywords = first_deliverable.get("keywords", [])
    assert any(
        "Shekou" in str(k) or "fishing" in str(k) or "Maritime" in str(k) for k in keywords
    ), f"Keywords should include project features, actual: {keywords}"

    # Check constraints include questionnaire data
    constraints = first_deliverable.get("constraints", {})
    must_include = constraints.get("must_include", [])
    assert any(
        "lighting" in str(item) or "net" in str(item) or "wood" in str(item) for item in must_include
    ), f"Constraints should include questionnaire details, actual: {must_include}"

    print("\n[PASS] Deliverable generation test passed!\n")
    return deliverables


def test_fallback_without_questionnaire():
    """Test fallback mechanism without questionnaire data"""

    # Empty questionnaire data
    keywords = _extract_keywords_from_questionnaire({}, "", {})

    # Generate deliverables (should fallback to templates)
    deliverables = _generate_role_specific_deliverables(
        role_id="4-1",
        role_base_type="V4",
        user_input="",
        structured_requirements={},
        questionnaire_keywords=keywords,
        confirmed_core_tasks=[],
    )

    print("[PASS] Fallback mechanism test:")
    print(f"  Generated {len(deliverables)} deliverables without questionnaire data")
    assert len(deliverables) > 0, "Should fallback to original templates"
    print("[PASS] Fallback mechanism test passed!\n")


if __name__ == "__main__":
    print("=" * 80)
    print("[v7.121] Questionnaire Data Utilization Test")
    print("=" * 80)
    print()

    try:
        # Test 1: Keyword extraction
        keywords = test_extract_keywords_from_questionnaire()

        # Test 2: Deliverable generation
        deliverables = test_generate_role_specific_deliverables()

        # Test 3: Fallback mechanism
        test_fallback_without_questionnaire()

        print("=" * 80)
        print("[PASS] All tests passed! Questionnaire data utilization is working.")
        print("=" * 80)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
