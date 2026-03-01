"""
测试搜索查询数据利用优化 (v7.121)

验证搜索查询生成是否充分利用：
- 用户原始输入 (user_input)
- 问卷摘要 (questionnaire_summary)
- 交付物元数据
"""

import pytest

from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator


def test_generate_queries_with_user_input():
    """测试：包含用户输入时生成更精准查询"""
    generator = SearchStrategyGenerator(llm_model=None)

    queries = generator.generate_deliverable_queries(
        deliverable_name="用户画像",
        keywords=["独立女性"],
        user_input="我是海归女性，喜欢Audrey Hepburn优雅风格，需要一个有归属感的私密空间",
        questionnaire_summary={},
        num_queries=3,
    )

    assert len(queries) == 3
    # 验证查询不是完全空白
    for query in queries:
        assert len(query) > 5

    # 验证包含deliverable_name或keywords或user_input的部分内容
    queries_str = " ".join(queries)
    # 应该包含以下之一：deliverable_name, keywords, 或 user_input的部分内容
    has_context = (
        "用户画像" in queries_str
        or "独立女性" in queries_str
        or "Audrey" in queries_str
        or "海归" in queries_str
        or "优雅" in queries_str
    )
    assert has_context, f"查询缺少相关内容: {queries}"


def test_generate_queries_with_questionnaire_summary():
    """测试：包含问卷摘要时生成个性化查询"""
    generator = SearchStrategyGenerator(llm_model=None)

    queries = generator.generate_deliverable_queries(
        deliverable_name="用户画像",
        keywords=["独立女性"],
        questionnaire_summary={
            "style_preferences": ["现代简约", "优雅"],
            "functional_requirements": ["私密空间", "工作区域"],
            "emotional_requirements": ["归属感", "自由度"],
        },
        num_queries=3,
    )

    assert len(queries) == 3

    # 验证查询包含问卷关键词
    queries_str = " ".join(queries)
    # 至少应该包含风格偏好或情感需求之一
    contains_style = any(style in queries_str for style in ["现代简约", "优雅"])
    contains_emotion = any(emotion in queries_str for emotion in ["归属感", "自由度"])

    assert contains_style or contains_emotion, f"查询未包含问卷关键词: {queries}"


def test_generate_queries_with_both_user_and_questionnaire():
    """测试：同时包含用户输入和问卷摘要时的整合能力"""
    generator = SearchStrategyGenerator(llm_model=None)

    queries = generator.generate_deliverable_queries(
        deliverable_name="空间布局方案",
        deliverable_description="设计室内空间的功能布局",
        keywords=["现代", "简约"],
        user_input="我希望有一个开放式的客厅，同时保持卧室的私密性",
        questionnaire_summary={
            "style_preferences": ["北欧风", "极简"],
            "functional_requirements": ["开放式厨房", "独立书房"],
            "emotional_requirements": ["温馨", "舒适"],
        },
        num_queries=3,
    )

    assert len(queries) == 3

    # 验证查询质量
    queries_str = " ".join(queries)
    # 应该包含交付物名称
    assert "空间布局" in queries_str or "布局方案" in queries_str or "空间" in queries_str

    # 应该包含风格或情感关键词
    has_context = any(keyword in queries_str for keyword in ["北欧风", "极简", "温馨", "舒适", "现代", "简约"])
    assert has_context, f"查询缺少上下文信息: {queries}"


def test_fallback_without_user_data():
    """测试：无用户数据时的降级方案"""
    generator = SearchStrategyGenerator(llm_model=None)

    queries = generator.generate_deliverable_queries(deliverable_name="用户画像", keywords=["独立女性"], num_queries=3)

    assert len(queries) == 3
    # 降级方案仍应生成有效查询
    assert all(len(q) > 0 for q in queries)
    assert "用户画像" in queries[0]


def test_questionnaire_summary_structure():
    """测试：不同问卷摘要结构的兼容性"""
    generator = SearchStrategyGenerator(llm_model=None)

    # 测试空摘要
    queries_empty = generator.generate_deliverable_queries(
        deliverable_name="测试交付物", questionnaire_summary={}, num_queries=3
    )
    assert len(queries_empty) == 3

    # 测试部分摘要（只有风格）
    queries_partial = generator.generate_deliverable_queries(
        deliverable_name="测试交付物", questionnaire_summary={"style_preferences": ["现代"]}, num_queries=3
    )
    assert len(queries_partial) == 3
    assert "现代" in " ".join(queries_partial)

    # 测试完整摘要
    queries_full = generator.generate_deliverable_queries(
        deliverable_name="测试交付物",
        questionnaire_summary={
            "style_preferences": ["现代", "简约"],
            "functional_requirements": ["开放式"],
            "emotional_requirements": ["温馨"],
        },
        num_queries=3,
    )
    assert len(queries_full) == 3
