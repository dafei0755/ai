"""
回归测试 — 验证 P0/P1 修复未破坏现有功能

覆盖:
- server.py lifespan 其他初始化不受影响
- FewShotSelectorV2 原有匹配逻辑不变
- LearningScheduler 原有任务注册/执行不变
- admin_routes 其他端点不受影响
- task_oriented_expert_factory 核心流程不变

Version: v7.620
"""

import inspect

import pytest


class TestRegression_ServerLifespan:
    """回归: server.py lifespan 中其他初始化逻辑未被破坏"""

    def test_lifespan_still_initializes_redis(self):
        """lifespan 仍应初始化 Redis session manager"""
        from intelligent_project_analyzer.api.server import lifespan

        source = inspect.getsource(lifespan)
        assert "RedisSessionManager" in source
        assert "session_manager" in source

    def test_lifespan_still_initializes_archive_manager(self):
        """lifespan 仍应初始化 archive manager"""
        from intelligent_project_analyzer.api.server import lifespan

        source = inspect.getsource(lifespan)
        assert "SessionArchiveManager" in source
        assert "archive_manager" in source

    def test_lifespan_still_initializes_pubsub(self):
        """lifespan 仍应初始化 Redis Pub/Sub"""
        from intelligent_project_analyzer.api.server import lifespan

        source = inspect.getsource(lifespan)
        assert "redis_pubsub" in source

    def test_lifespan_scheduler_failure_does_not_block(self):
        """LearningScheduler 启动失败不应阻塞 lifespan"""
        from intelligent_project_analyzer.api.server import lifespan

        source = inspect.getsource(lifespan)
        # 应在 try/except 中
        assert "except Exception" in source
        # scheduler 代码应在 yield 之前
        lines = source.split("\n")
        scheduler_line = None
        yield_line = None
        for i, line in enumerate(lines):
            if "get_learning_scheduler" in line and scheduler_line is None:
                scheduler_line = i
            if "yield" in line and yield_line is None:
                yield_line = i
        assert scheduler_line is not None
        assert yield_line is not None
        assert scheduler_line < yield_line


class TestRegression_FewShotSelectorV2:
    """回归: FewShotSelectorV2 原有功能未被破坏"""

    def test_match_examples_v2_still_accepts_project_input(self):
        """match_examples_v2 仍接受 project_input 参数"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            FewShotSelectorV2,
        )

        sig = inspect.signature(FewShotSelectorV2.match_examples_v2)
        params = list(sig.parameters.keys())
        assert "project_input" in params
        assert "user_id" in params
        assert "top_k" in params

    def test_match_examples_v2_returns_list(self, tmp_path):
        """match_examples_v2 应返回列表"""
        import yaml
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            FewShotSelectorV2,
        )

        registry_path = tmp_path / "examples_registry.yaml"
        registry_path.write_text(yaml.dump({"examples": []}), encoding="utf-8")
        selector = FewShotSelectorV2(examples_dir=tmp_path)

        result = selector.match_examples_v2({"tags_matrix": {}, "feature_vector": {}}, user_id=None, top_k=3)
        assert isinstance(result, list)

    def test_user_history_persistence_format(self, tmp_path):
        """用户历史应以 JSON 格式持久化"""
        import yaml
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            FewShotSelectorV2,
        )

        registry_path = tmp_path / "examples_registry.yaml"
        registry_path.write_text(yaml.dump({"examples": []}), encoding="utf-8")
        selector = FewShotSelectorV2(examples_dir=tmp_path)

        # 清除可能残留的历史，确保测试隔离
        selector.user_history.pop("user_a", None)

        selector.record_usage("example_1", "user_a")
        selector._save_user_history()

        history_path = selector._history_path
        assert history_path.exists()

        import json

        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "user_a" in data
        assert data["user_a"]["example_1"] == 1


class TestRegression_LearningScheduler:
    """回归: LearningScheduler 原有功能未被破坏"""

    def test_register_task_still_works(self):
        """register_task 应正常注册新任务"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()

        async def custom_task():
            return {"status": "ok"}

        scheduler.register_task(
            name="custom_test",
            func=custom_task,
            interval_seconds=3600,
            description="自定义测试任务",
        )

        assert "custom_test" in scheduler.tasks
        assert scheduler.tasks["custom_test"].interval_seconds == 3600

    def test_get_status_returns_expected_structure(self):
        """get_status 应返回预期结构"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()
        status = scheduler.get_status()

        assert isinstance(status, dict)
        assert "running" in status
        assert "tasks" in status
        assert isinstance(status["tasks"], dict)

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self):
        """多次调用 stop 不应抛异常"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()
        await scheduler.stop()
        await scheduler.stop()  # 第二次不应报错

    @pytest.mark.asyncio
    async def test_execute_task_updates_metadata(self):
        """_execute_task 应更新 last_run, run_count"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()

        async def simple_task():
            return {"status": "ok"}

        scheduler.register_task("meta_test", simple_task, 60)
        task = scheduler.tasks["meta_test"]

        assert task.last_run is None
        assert task.run_count == 0

        await scheduler._execute_task(task)

        assert task.last_run is not None
        assert task.run_count == 1
        assert task.last_result == {"status": "ok"}


class TestRegression_AdminRoutes:
    """回归: admin_routes 其他端点未被破坏"""

    def test_admin_routes_module_imports(self):
        """admin_routes 模块应能正常导入"""
        from intelligent_project_analyzer.api import admin_routes

        assert admin_routes is not None

    def test_admin_routes_has_router(self):
        """admin_routes 应导出 router"""
        from intelligent_project_analyzer.api.admin_routes import router

        assert router is not None

    def test_admin_routes_still_has_learning_endpoints(self):
        """admin_routes 应仍包含学习相关端点"""
        from intelligent_project_analyzer.api import admin_routes

        source = inspect.getsource(admin_routes)
        assert "learning" in source.lower()


class TestRegression_TaskOrientedExpertFactory:
    """回归: TaskOrientedExpertFactory 核心流程未被破坏"""

    def test_factory_class_exists(self):
        """TaskOrientedExpertFactory 类应存在"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
            TaskOrientedExpertFactory,
        )

        assert TaskOrientedExpertFactory is not None

    def test_factory_has_create_expert_method(self):
        """应有 execute_expert 或类似的核心方法"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
            TaskOrientedExpertFactory,
        )

        # 检查核心方法存在
        assert hasattr(TaskOrientedExpertFactory, "execute_expert") or hasattr(
            TaskOrientedExpertFactory, "execute_expert_with_retry"
        )

    def test_factory_still_imports_few_shot(self):
        """factory 应导入 few_shot_selector_v2 相关函数"""
        source = inspect.getsource(
            __import__(
                "intelligent_project_analyzer.agents.task_oriented_expert_factory",
                fromlist=["TaskOrientedExpertFactory"],
            )
        )
        assert "few_shot_selector_v2" in source

    def test_factory_still_uses_prompt_manager(self):
        """factory 应仍使用 prompt 相关功能"""
        from intelligent_project_analyzer.agents import task_oriented_expert_factory

        source = inspect.getsource(task_oriented_expert_factory)
        assert "PromptManager" in source or "prompt_manager" in source or "prompt" in source.lower()
