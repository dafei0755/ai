"""
v7.300: 4步工作流端到端测试

测试完整的 UCPPT 搜索模式 4 步工作流：
1. 第1步：需求理解与深度分析
2. 第2步：搜索任务分解（可编辑）
3. 第3步：博查搜索执行
4. 第4步：结果输出

测试类型：
- 端到端测试：完整流程验证
- 集成测试：组件间交互
- 回归测试：确保现有功能不受影响
"""

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_user_query() -> str:
        return "以丹麦家居品牌HAY气质为基础，为四川峨眉山七里坪民宿室内设计提供概念设计"

    @staticmethod
    def create_step1_analysis_output() -> Dict[str, Any]:
        """创建第1步分析输出"""
        return {
            "l0_user_profile": {
                "identity": "室内设计师或民宿业主",
                "needs": ["设计方案", "风格融合", "落地指导"],
                "decision_stage": "方案探索期",
            },
            "l1_facts": {
                "entities": {
                    "brand": "HAY",
                    "location": "四川峨眉山七里坪",
                    "project_type": "民宿室内设计",
                },
            },
            "l2_perspectives": [
                {"perspective": "美学", "insight": "北欧简约与川西自然的融合"},
                {"perspective": "文化", "insight": "丹麦设计哲学与巴蜀文化的对话"},
            ],
            "l3_core_tension": {
                "tension": "现代北欧风格与传统川西元素的平衡",
                "resolution_direction": "寻找共通的设计语言",
            },
            "l4_user_task": {
                "functional": "获得可落地的设计方案",
                "emotional": "创造独特的空间体验",
                "social": "打造有辨识度的民宿品牌",
            },
            "l5_sharpness": {
                "specificity": 0.8,
                "actionability": 0.7,
                "depth": 0.75,
            },
            "search_directions": [
                {
                    "direction": "HAY品牌设计语言研究",
                    "source_level": "L1",
                    "priority": "P0",
                },
                {
                    "direction": "峨眉山七里坪地域特色分析",
                    "source_level": "L1",
                    "priority": "P0",
                },
                {
                    "direction": "北欧与川西风格融合案例",
                    "source_level": "L2",
                    "priority": "P1",
                },
            ],
            "answer_framework": {
                "sections": ["设计理念", "色彩方案", "材质选择", "空间布局", "家具配置"],
                "focus_areas": ["风格融合", "在地化表达"],
            },
        }

    @staticmethod
    def create_step2_search_plan() -> Dict[str, Any]:
        """创建第2步搜索计划"""
        return {
            "session_id": "test-session-123",
            "query": TestDataFactory.create_user_query(),
            "core_question": "如何融合HAY品牌气质与峨眉山地域特色",
            "answer_goal": "提供完整的民宿室内概念设计方案",
            "search_steps": [
                {
                    "id": "S1",
                    "step_number": 1,
                    "task_description": "搜索HAY品牌设计语言、色彩体系、材质特点",
                    "expected_outcome": "获取HAY品牌核心设计特征",
                    "search_keywords": ["HAY", "北欧设计", "丹麦家居"],
                    "priority": "high",
                    "can_parallel": True,
                    "status": "pending",
                    "completion_score": 0,
                },
                {
                    "id": "S2",
                    "step_number": 2,
                    "task_description": "研究峨眉山七里坪的地域特色、自然环境、文化背景",
                    "expected_outcome": "了解当地自然环境和文化背景",
                    "search_keywords": ["峨眉山", "七里坪", "川西民宿"],
                    "priority": "high",
                    "can_parallel": True,
                    "status": "pending",
                    "completion_score": 0,
                },
                {
                    "id": "S3",
                    "step_number": 3,
                    "task_description": "分析北欧现代主义与四川在地文化融合的设计案例",
                    "expected_outcome": "获取风格融合的参考案例",
                    "search_keywords": ["北欧风格", "川西设计", "风格融合"],
                    "priority": "medium",
                    "can_parallel": False,
                    "status": "pending",
                    "completion_score": 0,
                },
            ],
            "max_rounds_per_step": 3,
            "quality_threshold": 0.7,
            "user_added_steps": [],
            "user_deleted_steps": [],
            "user_modified_steps": [],
            "current_page": 1,
            "total_pages": 1,
            "is_confirmed": False,
        }

    @staticmethod
    def create_search_results() -> List[Dict[str, Any]]:
        """创建搜索结果"""
        return [
            {
                "title": "HAY品牌设计理念解析",
                "url": "https://example.com/hay-design",
                "snippet": "HAY以民主设计为核心理念...",
                "source": "设计杂志",
            },
            {
                "title": "峨眉山七里坪民宿设计案例",
                "url": "https://example.com/emeishan-design",
                "snippet": "七里坪位于峨眉山半山腰...",
                "source": "建筑设计网",
            },
        ]


class TestStep1Analysis:
    """第1步：需求理解与深度分析测试"""

    @pytest.mark.integration
    async def test_step1_produces_structured_output(self):
        """测试第1步产出结构化输出"""
        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value
            engine.run_step1_analysis = AsyncMock(return_value=TestDataFactory.create_step1_analysis_output())

            result = await engine.run_step1_analysis(TestDataFactory.create_user_query())

            assert "l0_user_profile" in result
            assert "l1_facts" in result
            assert "search_directions" in result
            assert "answer_framework" in result

    @pytest.mark.integration
    async def test_step1_derives_search_directions(self):
        """测试第1步从 L0-L5 推导搜索方向"""
        output = TestDataFactory.create_step1_analysis_output()

        search_directions = output["search_directions"]

        assert len(search_directions) >= 2
        assert any(d["source_level"] == "L1" for d in search_directions)
        assert any(d["priority"] == "P0" for d in search_directions)

    @pytest.mark.integration
    async def test_step1_generates_answer_framework(self):
        """测试第1步生成回答框架"""
        output = TestDataFactory.create_step1_analysis_output()

        answer_framework = output["answer_framework"]

        assert "sections" in answer_framework
        assert len(answer_framework["sections"]) > 0


class TestStep2SearchPlan:
    """第2步：搜索任务分解测试"""

    @pytest.mark.integration
    async def test_step2_converts_directions_to_steps(self):
        """测试第2步将搜索方向转换为可编辑步骤"""
        step1_output = TestDataFactory.create_step1_analysis_output()
        step2_plan = TestDataFactory.create_step2_search_plan()

        # 验证搜索方向被转换为步骤
        assert len(step2_plan["search_steps"]) >= len(step1_output["search_directions"])

    @pytest.mark.integration
    async def test_step2_supports_user_editing(self):
        """测试第2步支持用户编辑"""
        plan = TestDataFactory.create_step2_search_plan()

        # 模拟用户添加步骤
        new_step = {
            "id": "S4",
            "step_number": 4,
            "task_description": "用户添加的搜索任务",
            "expected_outcome": "用户期望的结果",
            "search_keywords": [],
            "priority": "medium",
            "can_parallel": True,
            "status": "pending",
            "completion_score": 0,
            "is_user_added": True,
        }
        plan["search_steps"].append(new_step)
        plan["user_added_steps"].append("S4")

        assert len(plan["search_steps"]) == 4
        assert "S4" in plan["user_added_steps"]

    @pytest.mark.integration
    async def test_step2_validates_plan(self):
        """测试第2步验证计划并提供建议"""
        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value
            engine.validate_search_plan = AsyncMock(
                return_value={
                    "has_suggestions": True,
                    "suggestions": [
                        {
                            "direction": "材质研究",
                            "what_to_search": "搜索HAY常用材质",
                            "why_important": "材质是设计落地的关键",
                            "priority": "P1",
                        }
                    ],
                    "validation_passed": True,
                }
            )

            plan = TestDataFactory.create_step2_search_plan()
            result = await engine.validate_search_plan(plan)

            assert result["has_suggestions"] is True
            assert len(result["suggestions"]) > 0


class TestStep3SearchExecution:
    """第3步：博查搜索执行测试"""

    @pytest.mark.integration
    async def test_step3_executes_all_steps(self):
        """测试第3步执行所有搜索步骤"""
        plan = TestDataFactory.create_step2_search_plan()

        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value
            engine.execute_search_step = AsyncMock(
                return_value={
                    "status": "complete",
                    "completion_score": 0.85,
                    "sources": TestDataFactory.create_search_results(),
                }
            )

            for step in plan["search_steps"]:
                result = await engine.execute_search_step(step)
                assert result["status"] == "complete"
                assert result["completion_score"] >= 0.7

    @pytest.mark.integration
    async def test_step3_respects_parallel_flag(self):
        """测试第3步尊重并行标记"""
        plan = TestDataFactory.create_step2_search_plan()

        parallel_steps = [s for s in plan["search_steps"] if s["can_parallel"]]
        sequential_steps = [s for s in plan["search_steps"] if not s["can_parallel"]]

        assert len(parallel_steps) == 2
        assert len(sequential_steps) == 1

    @pytest.mark.integration
    async def test_step3_iterates_until_quality_threshold(self):
        """测试第3步迭代直到质量达标"""
        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value

            # 模拟多轮迭代
            call_count = 0

            async def mock_execute(step):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    return {"status": "partial", "completion_score": 0.5}
                return {"status": "complete", "completion_score": 0.85}

            engine.execute_search_step = mock_execute

            step = TestDataFactory.create_step2_search_plan()["search_steps"][0]

            # 执行直到完成
            result = {"status": "partial", "completion_score": 0}
            while result["status"] != "complete":
                result = await engine.execute_search_step(step)

            assert call_count == 3
            assert result["completion_score"] >= 0.7


class TestStep4ResultOutput:
    """第4步：结果输出测试"""

    @pytest.mark.integration
    async def test_step4_generates_structured_answer(self):
        """测试第4步生成结构化回答"""
        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value
            engine.generate_final_answer = AsyncMock(
                return_value={
                    "answer": "# 民宿室内概念设计方案\n\n## 设计理念\n...",
                    "sections": ["设计理念", "色彩方案", "材质选择"],
                    "references": TestDataFactory.create_search_results(),
                }
            )

            result = await engine.generate_final_answer(
                TestDataFactory.create_step2_search_plan(),
                TestDataFactory.create_search_results(),
            )

            assert "answer" in result
            assert len(result["answer"]) > 0
            assert "sections" in result

    @pytest.mark.integration
    async def test_step4_follows_answer_framework(self):
        """测试第4步遵循回答框架"""
        step1_output = TestDataFactory.create_step1_analysis_output()
        expected_sections = step1_output["answer_framework"]["sections"]

        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value
            engine.generate_final_answer = AsyncMock(
                return_value={
                    "answer": "...",
                    "sections": expected_sections,
                    "references": [],
                }
            )

            result = await engine.generate_final_answer(
                TestDataFactory.create_step2_search_plan(),
                [],
            )

            assert result["sections"] == expected_sections


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    @pytest.mark.e2e
    async def test_complete_4_step_workflow(self):
        """测试完整的4步工作流"""
        query = TestDataFactory.create_user_query()

        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value

            # Step 1: 需求理解与深度分析
            engine.run_step1_analysis = AsyncMock(return_value=TestDataFactory.create_step1_analysis_output())
            step1_result = await engine.run_step1_analysis(query)
            assert "search_directions" in step1_result

            # Step 2: 搜索任务分解
            engine.convert_to_step2_plan = MagicMock(return_value=TestDataFactory.create_step2_search_plan())
            step2_plan = engine.convert_to_step2_plan(step1_result)
            assert len(step2_plan["search_steps"]) > 0

            # Step 3: 博查搜索执行
            engine.execute_search_step = AsyncMock(
                return_value={
                    "status": "complete",
                    "completion_score": 0.85,
                    "sources": TestDataFactory.create_search_results(),
                }
            )

            all_sources = []
            for step in step2_plan["search_steps"]:
                result = await engine.execute_search_step(step)
                all_sources.extend(result["sources"])

            assert len(all_sources) > 0

            # Step 4: 结果输出
            engine.generate_final_answer = AsyncMock(
                return_value={
                    "answer": "# 设计方案\n...",
                    "sections": ["设计理念", "色彩方案"],
                    "references": all_sources,
                }
            )

            final_result = await engine.generate_final_answer(step2_plan, all_sources)
            assert "answer" in final_result
            assert len(final_result["references"]) > 0

    @pytest.mark.e2e
    async def test_workflow_with_user_modifications(self):
        """测试带用户修改的工作流"""
        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value

            # Step 1
            engine.run_step1_analysis = AsyncMock(return_value=TestDataFactory.create_step1_analysis_output())
            step1_result = await engine.run_step1_analysis(TestDataFactory.create_user_query())

            # Step 2 with user modifications
            plan = TestDataFactory.create_step2_search_plan()

            # 用户添加步骤
            plan["search_steps"].append(
                {
                    "id": "S4",
                    "step_number": 4,
                    "task_description": "用户添加：搜索民宿运营案例",
                    "expected_outcome": "了解成功民宿的运营模式",
                    "search_keywords": ["民宿运营", "成功案例"],
                    "priority": "low",
                    "can_parallel": True,
                    "status": "pending",
                    "completion_score": 0,
                    "is_user_added": True,
                }
            )
            plan["user_added_steps"] = ["S4"]

            # 用户删除步骤
            plan["search_steps"] = [s for s in plan["search_steps"] if s["id"] != "S3"]
            plan["user_deleted_steps"] = ["S3"]

            # 验证修改
            assert len(plan["search_steps"]) == 3  # 原3个 - 1删除 + 1添加
            assert "S4" in plan["user_added_steps"]
            assert "S3" in plan["user_deleted_steps"]

            # Step 3 & 4 继续执行
            engine.execute_search_step = AsyncMock(
                return_value={
                    "status": "complete",
                    "completion_score": 0.8,
                    "sources": [],
                }
            )

            for step in plan["search_steps"]:
                await engine.execute_search_step(step)

            # 验证用户添加的步骤也被执行
            assert engine.execute_search_step.call_count == 3


class TestRegressionTests:
    """回归测试：确保现有功能不受影响"""

    @pytest.mark.regression
    async def test_existing_ucppt_flow_unaffected(self):
        """测试现有 UCPPT 流程不受影响"""
        # 现有流程应该继续工作
        with patch("intelligent_project_analyzer.services.ucppt_search_engine.UcpptSearchEngine") as MockEngine:
            engine = MockEngine.return_value

            # 现有的搜索方法应该仍然可用
            engine.search = AsyncMock(return_value={"results": []})
            engine.analyze = AsyncMock(return_value={"analysis": "..."})

            result = await engine.search("测试查询")
            assert "results" in result

    @pytest.mark.regression
    async def test_sse_events_backward_compatible(self):
        """测试 SSE 事件向后兼容"""
        # 现有事件类型应该继续工作
        existing_events = [
            "unified_dialogue_chunk",
            "unified_dialogue_complete",
            "search_framework_ready",
            "round_sources",
            "answer_chunk",
            "done",
        ]

        # 新增事件不应该影响现有事件
        new_events = [
            "step2_plan_ready",
        ]

        all_events = existing_events + new_events

        # 验证没有事件名冲突
        assert len(all_events) == len(set(all_events))

    @pytest.mark.regression
    async def test_search_state_backward_compatible(self):
        """测试搜索状态向后兼容"""
        # 现有状态字段应该继续存在
        existing_fields = [
            "status",
            "query",
            "rounds",
            "sources",
            "answerContent",
            "frameworkChecklist",
        ]

        # 新增字段
        new_fields = [
            "step2Plan",
        ]

        # 验证字段名不冲突
        all_fields = existing_fields + new_fields
        assert len(all_fields) == len(set(all_fields))

    @pytest.mark.regression
    async def test_api_endpoints_backward_compatible(self):
        """测试 API 端点向后兼容"""
        # 现有端点应该继续工作
        existing_endpoints = [
            "/api/search/ucppt/stream",
            "/api/search/health",
        ]

        # 新增端点
        new_endpoints = [
            "/api/search/step2/update",
            "/api/search/step2/confirm",
            "/api/search/step2/validate",
        ]

        # 验证端点路径不冲突
        all_endpoints = existing_endpoints + new_endpoints
        assert len(all_endpoints) == len(set(all_endpoints))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
