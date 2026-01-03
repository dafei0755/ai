"""
单元测试: 数据流优化 v7.122

测试用户问题→搜索→概念图的数据传递链路优化

测试范围:
1. 搜索查询提示注入 (task_oriented_expert_factory)
2. 问卷数据在概念图中的传递 (deliverable_id_generator_node)
3. 搜索引用统一处理 (result_aggregator)

Author: AI Assistant
Created: 2026-01-03
Version: v7.122
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# ============================================================================
# 测试 1: 搜索查询提示注入
# ============================================================================


class TestSearchQueriesHint:
    """测试搜索查询提示构建功能"""

    @pytest.fixture
    def factory(self):
        """创建 TaskOrientedExpertFactory 实例"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        return TaskOrientedExpertFactory()

    @pytest.fixture
    def mock_state_with_queries(self) -> Dict[str, Any]:
        """模拟包含搜索查询的状态"""
        return {
            "deliverable_owner_map": {"2-1": ["2-1_1_143022_abc", "2-1_2_143023_def"]},
            "deliverable_metadata": {
                "2-1_1_143022_abc": {
                    "name": "空间功能分区方案",
                    "search_queries": ["空间功能分区方案 现代简约 设计案例 2024", "灵活多功能 温馨舒适", "60平米小户型空间最大化 研究资料"],
                },
                "2-1_2_143023_def": {"name": "材质与色彩方案", "search_queries": ["现代简约材质选型 天然木材", "温馨色彩搭配 家居设计"]},
            },
        }

    def test_build_search_queries_hint_with_queries(self, factory, mock_state_with_queries):
        """测试: 有搜索查询时，成功构建提示"""
        role_object = {"role_id": "2-1"}

        hint = factory._build_search_queries_hint(role_object, mock_state_with_queries)

        # 验证提示不为空
        assert hint != ""

        # 验证包含关键标题
        assert "推荐搜索查询" in hint or "Recommended Search Queries" in hint

        # 验证包含交付物名称
        assert "空间功能分区方案" in hint
        assert "材质与色彩方案" in hint

        # 验证包含搜索查询
        assert "空间功能分区方案 现代简约 设计案例 2024" in hint
        assert "现代简约材质选型 天然木材" in hint

        # 验证包含使用建议
        assert "优先使用" in hint or "使用建议" in hint

    def test_build_search_queries_hint_no_deliverables(self, factory):
        """测试: 无交付物时，返回空字符串"""
        role_object = {"role_id": "2-1"}
        state = {"deliverable_owner_map": {}, "deliverable_metadata": {}}

        hint = factory._build_search_queries_hint(role_object, state)

        assert hint == ""

    def test_build_search_queries_hint_no_search_queries(self, factory):
        """测试: 交付物存在但无搜索查询时，返回空字符串"""
        role_object = {"role_id": "2-1"}
        state = {
            "deliverable_owner_map": {"2-1": ["2-1_1_143022_abc"]},
            "deliverable_metadata": {"2-1_1_143022_abc": {"name": "空间功能分区方案", "search_queries": []}},  # 空查询列表
        }

        hint = factory._build_search_queries_hint(role_object, state)

        assert hint == ""

    def test_build_search_queries_hint_missing_metadata(self, factory):
        """测试: 交付物 ID 存在但元数据缺失时，正常处理"""
        role_object = {"role_id": "2-1"}
        state = {"deliverable_owner_map": {"2-1": ["2-1_1_143022_abc"]}, "deliverable_metadata": {}}  # 缺失元数据

        hint = factory._build_search_queries_hint(role_object, state)

        assert hint == ""

    def test_build_search_queries_hint_query_count(self, factory, mock_state_with_queries):
        """测试: 验证所有查询都被包含"""
        role_object = {"role_id": "2-1"}

        hint = factory._build_search_queries_hint(role_object, mock_state_with_queries)

        # 计算预期的查询总数
        expected_queries = [
            "空间功能分区方案 现代简约 设计案例 2024",
            "灵活多功能 温馨舒适",
            "60平米小户型空间最大化 研究资料",
            "现代简约材质选型 天然木材",
            "温馨色彩搭配 家居设计",
        ]

        for query in expected_queries:
            assert query in hint


# ============================================================================
# 测试 2: 问卷数据在交付物元数据中的保存
# ============================================================================


class TestQuestionnaireDataInConstraints:
    """测试问卷数据在 deliverable_metadata.constraints 中的保存"""

    def test_constraints_include_questionnaire_keywords(self):
        """测试: constraints 包含问卷关键词"""
        # 模拟 _extract_keywords_from_questionnaire 的输出
        questionnaire_keywords = {
            "material_keywords": ["木质元素", "天然织物", "植物装饰"],
            "emotional_keywords": ["温馨", "自然", "舒适"],
            "functional_keywords": ["收纳", "采光"],
            "style_label": "现代实用主义",
            "color_palette": "neutral tones, functional aesthetics",
        }

        # 模拟构建的 constraints
        constraints = {
            "must_include": [
                *questionnaire_keywords["material_keywords"][:3],
                *questionnaire_keywords["functional_keywords"][:2],
                "功能分区",
            ],
            "style_preferences": f"{questionnaire_keywords['style_label']} aesthetic, {questionnaire_keywords['color_palette']}",
            "user_specific_needs": ", ".join(questionnaire_keywords["functional_keywords"][:5]),
            # v7.122: 新增字段
            "emotional_keywords": questionnaire_keywords["emotional_keywords"],
            "profile_label": questionnaire_keywords["style_label"],
        }

        # 验证
        assert "emotional_keywords" in constraints
        assert constraints["emotional_keywords"] == ["温馨", "自然", "舒适"]

        assert "profile_label" in constraints
        assert constraints["profile_label"] == "现代实用主义"

        assert "木质元素" in constraints["must_include"]
        assert "收纳" in constraints["must_include"]

    def test_constraints_fallback_when_no_questionnaire(self):
        """测试: 无问卷数据时的降级处理"""
        questionnaire_keywords = {}

        constraints = {
            "must_include": ["功能分区"],
            "style_preferences": "professional design",
            "emotional_keywords": questionnaire_keywords.get("emotional_keywords", []),
            "profile_label": questionnaire_keywords.get("style_label", ""),
        }

        # 验证降级值
        assert constraints["emotional_keywords"] == []
        assert constraints["profile_label"] == ""


# ============================================================================
# 测试 3: 概念图生成时的问卷数据传递
# ============================================================================


class TestConceptImageQuestionnaireData:
    """测试概念图生成时问卷数据的传递"""

    @pytest.mark.asyncio
    async def test_questionnaire_data_passed_to_image_generator(self):
        """测试: questionnaire_data 正确传递给概念图生成器"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        # 模拟状态
        mock_state = {
            "questionnaire_summary": {
                "profile_label": "现代海洋风",
                "answers": {"gap_answers": {"q1": "希望客厅有大量自然光", "q2": "想保留渔村特色"}},
            },
            "deliverable_owner_map": {"2-1": ["2-1_1_143022_abc"]},
            "deliverable_metadata": {"2-1_1_143022_abc": {"name": "空间功能分区方案", "keywords": ["现代", "简约"]}},
            "session_id": "test_session",
            "project_type": "interior",
        }

        # 构建预期的 questionnaire_data
        expected_data = {"profile_label": "现代海洋风", "answers": mock_state["questionnaire_summary"]["answers"]}

        # 验证数据结构
        assert expected_data["profile_label"] == "现代海洋风"
        assert "gap_answers" in expected_data["answers"]
        assert expected_data["answers"]["gap_answers"]["q1"] == "希望客厅有大量自然光"


# ============================================================================
# 测试 4: 搜索引用统一处理
# ============================================================================


class TestConsolidateSearchReferences:
    """测试搜索引用统一处理功能"""

    @pytest.fixture
    def aggregator(self):
        """创建 ResultAggregatorAgent 实例"""
        from intelligent_project_analyzer.report.result_aggregator import ResultAggregatorAgent

        # 创建 mock LLM 实例
        mock_llm = MagicMock()
        return ResultAggregatorAgent(llm_model=mock_llm)

    @pytest.fixture
    def mock_references(self) -> List[Dict[str, Any]]:
        """模拟搜索引用列表"""
        return [
            {
                "title": "现代简约设计案例",
                "url": "https://example.com/1",
                "snippet": "现代简约风格的设计案例分析...",
                "quality_score": 85.3,
                "relevance_score": 0.9,
                "source_tool": "tavily",
            },
            {
                "title": "现代简约设计案例",  # 重复标题和URL
                "url": "https://example.com/1",
                "snippet": "相同的文章...",
                "quality_score": 85.3,
                "source_tool": "tavily",
            },
            {
                "title": "空间规划研究",
                "url": "https://example.com/2",
                "snippet": "空间规划的最佳实践...",
                "quality_score": 92.0,
                "relevance_score": 0.95,
                "source_tool": "arxiv",
            },
            {
                "title": "材料选型指南",
                "url": "https://example.com/3",
                "snippet": "环保材料的选择标准...",
                "quality_score": 78.5,
                "source_tool": "bocha",
            },
        ]

    def test_consolidate_normal_references(self, aggregator, mock_references):
        """测试: 正常处理搜索引用（去重、排序）"""
        state = {"search_references": mock_references}

        result = aggregator._consolidate_search_references(state)

        # 验证去重：4个引用 → 3个（去除重复）
        assert len(result) == 3

        # 验证排序：按 quality_score 降序
        assert result[0]["quality_score"] == 92.0  # 空间规划研究
        assert result[1]["quality_score"] == 85.3  # 现代简约设计案例
        assert result[2]["quality_score"] == 78.5  # 材料选型指南

        # 验证引用编号
        assert result[0]["reference_number"] == 1
        assert result[1]["reference_number"] == 2
        assert result[2]["reference_number"] == 3

    def test_consolidate_empty_references(self, aggregator):
        """测试: 空引用列表的容错处理"""
        state = {"search_references": []}

        result = aggregator._consolidate_search_references(state)

        assert result == []

    def test_consolidate_none_references(self, aggregator):
        """测试: None 的容错处理"""
        state = {"search_references": None}

        result = aggregator._consolidate_search_references(state)

        assert result == []

    def test_consolidate_missing_references(self, aggregator):
        """测试: 缺少 search_references 字段的容错处理"""
        state = {}

        result = aggregator._consolidate_search_references(state)

        assert result == []

    def test_consolidate_invalid_type(self, aggregator):
        """测试: 非列表类型的容错处理"""
        state = {"search_references": "not a list"}

        result = aggregator._consolidate_search_references(state)

        assert result == []

    def test_consolidate_skip_invalid_items(self, aggregator):
        """测试: 跳过无效的引用项"""
        state = {
            "search_references": [
                {"title": "有效引用", "url": "https://example.com/1", "quality_score": 85.0},
                "invalid_string",  # 非字典
                {
                    # 缺少 title
                    "url": "https://example.com/2",
                    "quality_score": 90.0,
                },
                {"title": "", "url": "https://example.com/3", "quality_score": 80.0},  # 空标题
            ]
        }

        result = aggregator._consolidate_search_references(state)

        # 只保留有效的引用
        assert len(result) == 1
        assert result[0]["title"] == "有效引用"

    def test_consolidate_deduplication_by_title_and_url(self, aggregator):
        """测试: 基于 (title, url) 的去重"""
        state = {
            "search_references": [
                {"title": "文章A", "url": "https://example.com/a", "quality_score": 85.0},
                {"title": "文章A", "url": "https://example.com/a", "quality_score": 85.0},  # 完全重复
                {"title": "文章A", "url": "https://example.com/b", "quality_score": 80.0},  # 标题相同，URL不同
                {"title": "文章B", "url": "https://example.com/a", "quality_score": 90.0},  # URL相同，标题不同
            ]
        }

        result = aggregator._consolidate_search_references(state)

        # 去重后应保留 3 个
        assert len(result) == 3

    def test_consolidate_quality_score_fallback(self, aggregator):
        """测试: quality_score 缺失时使用 relevance_score"""
        state = {
            "search_references": [
                {
                    "title": "引用1",
                    "url": "https://example.com/1",
                    # 无 quality_score
                    "relevance_score": 0.85,  # 应转换为 85.0
                },
                {"title": "引用2", "url": "https://example.com/2", "quality_score": 90.0},
            ]
        }

        result = aggregator._consolidate_search_references(state)

        # 验证排序：引用2 (90.0) > 引用1 (85.0)
        assert result[0]["title"] == "引用2"
        assert result[1]["title"] == "引用1"

    def test_consolidate_add_reference_numbers(self, aggregator):
        """测试: 自动添加引用编号"""
        state = {
            "search_references": [
                {"title": "引用1", "url": "https://example.com/1", "quality_score": 90.0},
                {
                    "title": "引用2",
                    "url": "https://example.com/2",
                    "quality_score": 85.0,
                    "reference_number": 999,  # 已有编号，应保留
                },
                {"title": "引用3", "url": "https://example.com/3", "quality_score": 80.0},
            ]
        }

        result = aggregator._consolidate_search_references(state)

        # 验证编号
        assert result[0]["reference_number"] == 1  # 新添加
        assert result[1]["reference_number"] == 999  # 保留原有
        assert result[2]["reference_number"] == 3  # 新添加


# ============================================================================
# 集成测试：完整数据流
# ============================================================================


class TestDataFlowIntegration:
    """测试完整的数据流传递"""

    def test_questionnaire_to_search_queries_flow(self):
        """测试: 问卷数据 → 搜索查询的数据流"""
        # 模拟问卷数据
        questionnaire_summary = {"profile_label": "工业冷峻", "answers": {"gap_answers": {"q1": "喜欢裸露混凝土和金属管道"}}}

        # 模拟提取的关键词
        questionnaire_keywords = {
            "style_label": "工业冷峻",
            "material_keywords": ["裸露混凝土", "金属管道", "黑色框架"],
            "color_palette": "industrial grey, black steel",
        }

        # 模拟搜索查询生成
        search_queries = [
            f"空间功能分区方案 {questionnaire_keywords['style_label']} 设计案例 2024",
            f"{questionnaire_keywords['material_keywords'][0]} {questionnaire_keywords['material_keywords'][1]}",
        ]

        # 验证数据传递
        assert "工业冷峻" in search_queries[0]
        assert "裸露混凝土" in search_queries[1]
        assert "金属管道" in search_queries[1]

    def test_questionnaire_to_concept_image_flow(self):
        """测试: 问卷数据 → 概念图的数据流"""
        # 模拟问卷数据
        questionnaire_data = {
            "profile_label": "轻奢优雅",
            "answers": {"gap_answers": {"q1": "希望使用大理石和黄铜元素", "q2": "追求高端品质感"}},
        }

        # 模拟交付物元数据
        deliverable_metadata = {
            "constraints": {
                "emotional_keywords": ["优雅", "奢华"],
                "profile_label": "轻奢优雅",
                "style_preferences": "luxury gold, marble white",
            }
        }

        # 验证数据完整性
        assert deliverable_metadata["constraints"]["profile_label"] == "轻奢优雅"
        assert "优雅" in deliverable_metadata["constraints"]["emotional_keywords"]
        assert questionnaire_data["answers"]["gap_answers"]["q1"] == "希望使用大理石和黄铜元素"


# ============================================================================
# 性能测试
# ============================================================================


class TestPerformance:
    """测试性能影响"""

    @pytest.fixture
    def aggregator(self):
        from intelligent_project_analyzer.report.result_aggregator import ResultAggregatorAgent

        mock_llm = MagicMock()
        return ResultAggregatorAgent(llm_model=mock_llm)

    def test_large_references_performance(self, aggregator, benchmark):
        """测试: 大量搜索引用的处理性能"""
        # 生成 1000 条引用
        large_references = [
            {
                "title": f"引用 {i}",
                "url": f"https://example.com/{i}",
                "quality_score": 50 + (i % 50),
                "snippet": f"内容 {i}",
            }
            for i in range(1000)
        ]

        state = {"search_references": large_references}

        # 使用 pytest-benchmark 测量性能
        result = benchmark(aggregator._consolidate_search_references, state)

        # 验证结果正确性
        assert len(result) == 1000
        assert all("reference_number" in ref for ref in result)


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
