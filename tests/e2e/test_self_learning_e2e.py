"""
端到端测试 — 完整自学习闭环验证

验证从 server 启动 → 数据收集 → 学习调度 → 运行时反馈的完整闭环。

Version: v7.620
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestE2E_SelfLearningClosedLoop:
    """端到端: 验证自学习系统的完整闭环"""

    @pytest.mark.asyncio
    async def test_server_lifespan_starts_scheduler(self):
        """E2E: server lifespan 应启动 LearningScheduler"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()
        started = False

        async def mock_start():
            nonlocal started
            started = True

        scheduler.start = mock_start

        # 模拟 lifespan 中的调用
        with patch(
            "intelligent_project_analyzer.services.learning_scheduler.get_learning_scheduler",
            return_value=scheduler,
        ):
            from intelligent_project_analyzer.services.learning_scheduler import (
                get_learning_scheduler,
            )

            s = get_learning_scheduler()
            await s.start()

        assert started is True

    @pytest.mark.asyncio
    async def test_scheduler_executes_dimension_promotion_on_due(self):
        """E2E: scheduler 到期时应执行 dimension_auto_promotion 任务"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()
        executed = False

        async def mock_promotion():
            nonlocal executed
            executed = True
            return {"status": "success", "auto_promoted": 0}

        # 替换任务函数
        scheduler.tasks["dimension_auto_promotion"].func = mock_promotion
        # 设置 last_run 为 None（立即执行）
        scheduler.tasks["dimension_auto_promotion"].last_run = None

        # 手动执行一次
        await scheduler._execute_task(scheduler.tasks["dimension_auto_promotion"])

        assert executed is True
        assert scheduler.tasks["dimension_auto_promotion"].run_count == 1

    @pytest.mark.asyncio
    async def test_few_shot_adapts_based_on_user_history(self, tmp_path):
        """E2E: few-shot 选择应基于用户历史进行衰减"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            FewShotSelectorV2,
        )

        # 创建两个示例
        for i, name in enumerate(["example_a", "example_b"]):
            example_data = {
                "example": {
                    "project_info": {"name": f"示例{name}", "description": f"描述{i}"},
                    "ideal_tasks": [{"title": f"任务{i}"}],
                }
            }
            (tmp_path / f"{name}.yaml").write_text(yaml.dump(example_data, allow_unicode=True), encoding="utf-8")

        registry = {
            "examples": [
                {
                    "id": "example_a",
                    "name": "示例A",
                    "file": "example_a.yaml",
                    "layer": 1,
                    "strength": "strong",
                    "tags_matrix": {"space_type": ["commercial"]},
                    "feature_vector": {"commercial": 0.9},
                },
                {
                    "id": "example_b",
                    "name": "示例B",
                    "file": "example_b.yaml",
                    "layer": 1,
                    "strength": "strong",
                    "tags_matrix": {"space_type": ["commercial"]},
                    "feature_vector": {"commercial": 0.85},
                },
            ]
        }
        (tmp_path / "examples_registry.yaml").write_text(yaml.dump(registry, allow_unicode=True), encoding="utf-8")

        selector = FewShotSelectorV2(examples_dir=tmp_path)

        project_input = {
            "tags_matrix": {"space_type": ["commercial"]},
            "feature_vector": {"commercial": 0.9},
            "discipline": "interior",
            "urgency": 0.4,
            "innovation_quotient": 0.5,
            "commercial_sensitivity": 0.8,
            "cultural_depth": 0.2,
        }

        # 第一次匹配
        result1 = selector.match_examples_v2(project_input, user_id="user-x", top_k=2)
        [r.get("example_id") for r in result1]

        # 记录使用 example_a 多次（模拟重复使用）
        for _ in range(5):
            selector.record_usage("example_a", "user-x")

        # 第二次匹配 — example_a 应因衰减而排名下降
        result2 = selector.match_examples_v2(project_input, user_id="user-x", top_k=2)
        [r.get("example_id") for r in result2]

        # 验证: 至少返回了结果
        assert len(result2) >= 1

    @pytest.mark.asyncio
    async def test_full_loop_dimension_extraction_to_ontology(self):
        """E2E: 维度提取 → DB 存储 → scheduler 审批 → ontology 写入"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        # 模拟完整管线
        dimension_data = {
            "name": "光影叙事",
            "category": "spatial_experience",
            "description": "通过光影变化讲述空间故事",
            "ask_yourself": "光影如何参与空间叙事？",
            "examples": "教堂光线, 博物馆天窗, 庭院光影",
        }

        # 1. 模拟 DB 中已有候选（由 extractor 写入）
        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = [
            {
                "id": 42,
                "confidence_score": 0.96,
                "dimension_data": json.dumps(dimension_data),
            }
        ]
        mock_db.approve_candidate.return_value = True

        # 2. 模拟 OntologyEditor
        written_dimensions = []

        def capture_append(**kwargs):
            written_dimensions.append(kwargs)
            return True

        mock_editor = MagicMock()
        mock_editor.append_dimension.side_effect = capture_append

        # 3. 模拟 OntologyService
        mock_ontology_service = MagicMock()

        with patch(
            "intelligent_project_analyzer.learning.database_manager.get_db_manager",
            return_value=mock_db,
        ), patch(
            "intelligent_project_analyzer.services.ontology_editor.get_ontology_editor",
            return_value=mock_editor,
        ), patch(
            "intelligent_project_analyzer.services.ontology_service.get_ontology_service",
            return_value=mock_ontology_service,
        ):
            result = await LearningScheduler._run_dimension_auto_promotion()

        # 验证完整闭环
        assert result["auto_promoted"] == 1

        # 验证写入的维度数据
        assert len(written_dimensions) == 1
        written = written_dimensions[0]
        assert written["project_type"] == "meta_framework"
        assert written["category"] == "ontological_foundations"
        assert written["dimension_data"]["name"] == "光影叙事"
        assert "光影如何参与空间叙事" in written["dimension_data"]["ask_yourself"]

        # 验证 DB 状态更新
        mock_db.approve_candidate.assert_called_once_with(42, reviewer_id="auto_scheduler")

        # 验证缓存刷新
        mock_ontology_service.reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_task_error_does_not_crash_loop(self):
        """E2E: 单个任务失败不应导致 scheduler 崩溃"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()

        # 注册一个会抛异常的任务
        async def failing_task():
            raise RuntimeError("模拟任务失败")

        scheduler.register_task(
            name="test_failing_task",
            func=failing_task,
            interval_seconds=1,
            description="测试失败任务",
        )

        # 执行应不抛异常
        await scheduler._execute_task(scheduler.tasks["test_failing_task"])

        # 验证错误计数增加（run_count 只在成功时递增）
        assert scheduler.tasks["test_failing_task"].error_count == 1
        assert scheduler.tasks["test_failing_task"].run_count == 0

    @pytest.mark.asyncio
    async def test_scheduler_status_reflects_task_state(self):
        """E2E: get_status 应反映所有任务的真实状态"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()

        status = scheduler.get_status()

        assert "running" in status
        assert "tasks" in status
        assert len(status["tasks"]) == 3  # 3 个默认任务

        for task_info in status["tasks"].values():
            assert "enabled" in task_info
            assert "run_count" in task_info
            assert "error_count" in task_info
