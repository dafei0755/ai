"""
单元测试 — P0/P1 自学习子系统修复

覆盖:
- P0-1: LearningScheduler auto-start in server lifespan
- P0-2: FewShotSelectorV2 content loading + singleton + project_input construction
- P0-3: Dimension auto-promotion write path + category mapping
- P1-1: admin_routes get_control_status method name fix

Version: v7.620
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ============================================================================
# P0-1: LearningScheduler auto-start
# ============================================================================


class TestP0_1_LearningSchedulerAutoStart:
    """P0-1: 验证 LearningScheduler 在 server lifespan 中被自动启动"""

    def test_scheduler_singleton_returns_same_instance(self):
        """get_learning_scheduler() 应返回同一实例"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            get_learning_scheduler,
        )

        s1 = get_learning_scheduler()
        s2 = get_learning_scheduler()
        assert s1 is s2

    def test_scheduler_registers_default_tasks(self):
        """LearningScheduler 初始化时应注册 3 个默认任务"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()
        assert "motivation_pattern_analysis" in scheduler.tasks
        assert "taxonomy_promotion_check" in scheduler.tasks
        assert "dimension_auto_promotion" in scheduler.tasks
        assert len(scheduler.tasks) == 3

    @pytest.mark.asyncio
    async def test_scheduler_start_sets_running_flag(self):
        """start() 应将 _running 设为 True"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()
        await scheduler.start()
        assert scheduler._running is True
        # 清理
        await scheduler.stop()
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_scheduler_start_idempotent(self):
        """重复调用 start() 不应创建多个后台任务"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        scheduler = LearningScheduler()
        await scheduler.start()
        task1 = scheduler._background_task
        await scheduler.start()  # 第二次调用
        task2 = scheduler._background_task
        assert task1 is task2  # 同一个任务
        await scheduler.stop()

    def test_lifespan_contains_scheduler_start_call(self):
        """server.py lifespan 函数中应包含 LearningScheduler 启动代码"""
        import inspect
        from intelligent_project_analyzer.api.server import lifespan

        source = inspect.getsource(lifespan)
        assert "get_learning_scheduler" in source
        assert "_learning_scheduler.start()" in source or "await _learning_scheduler.start()" in source


# ============================================================================
# P0-2: FewShotSelectorV2 fixes
# ============================================================================


class TestP0_2_FewShotSelectorV2ContentLoading:
    """P0-2: 验证 FewShotSelectorV2 的内容加载和单例模式"""

    def _create_selector_with_temp_dir(self, tmp_path):
        """创建使用临时目录的 selector"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            FewShotSelectorV2,
        )

        # 创建空注册表
        registry_path = tmp_path / "examples_registry.yaml"
        registry_path.write_text(yaml.dump({"examples": []}), encoding="utf-8")
        return FewShotSelectorV2(examples_dir=tmp_path)

    def test_load_example_content_from_yaml(self, tmp_path):
        """load_example_content 应从 YAML 文件加载实际内容"""
        selector = self._create_selector_with_temp_dir(tmp_path)

        # 创建示例 YAML 文件
        example_data = {
            "example": {
                "project_info": {
                    "name": "测试菜市场改造",
                    "description": "深圳蛇口菜市场空间改造设计",
                },
                "ideal_tasks": [
                    {"title": "搜索 苏州黄桥菜市场的空间设计策略"},
                    {"title": "搜索 日本筑地市场的空间组织逻辑"},
                    {"title": "搜索 西班牙博盖利亚市场的空间体验设计"},
                ],
            }
        }
        example_file = tmp_path / "test_example.yaml"
        example_file.write_text(yaml.dump(example_data, allow_unicode=True), encoding="utf-8")

        # 调用 load_example_content
        meta = {"file": "test_example.yaml", "name": "测试示例"}
        content = selector.load_example_content(meta)

        assert "测试菜市场改造" in content
        assert "深圳蛇口菜市场空间改造设计" in content
        assert "苏州黄桥菜市场" in content
        assert "日本筑地市场" in content

    def test_load_example_content_missing_file(self, tmp_path):
        """文件不存在时应返回空字符串"""
        selector = self._create_selector_with_temp_dir(tmp_path)
        meta = {"file": "nonexistent.yaml"}
        content = selector.load_example_content(meta)
        assert content == ""

    def test_load_example_content_no_file_field(self, tmp_path):
        """meta 中无 file 字段时应返回空字符串"""
        selector = self._create_selector_with_temp_dir(tmp_path)
        meta = {"name": "no file"}
        content = selector.load_example_content(meta)
        assert content == ""

    def test_load_example_content_caches_yaml(self, tmp_path):
        """重复加载同一文件应使用缓存"""
        selector = self._create_selector_with_temp_dir(tmp_path)

        example_file = tmp_path / "cached_example.yaml"
        example_file.write_text(
            yaml.dump({"example": {"project_info": {"name": "缓存测试"}, "ideal_tasks": []}}),
            encoding="utf-8",
        )

        meta = {"file": "cached_example.yaml"}
        selector.load_example_content(meta)
        assert "cached_example.yaml" in selector.examples_cache

        # 第二次调用应命中缓存
        selector.load_example_content(meta)
        assert len(selector.examples_cache) == 1

    def test_load_example_content_limits_tasks(self, tmp_path):
        """应限制最多显示 8 个任务"""
        selector = self._create_selector_with_temp_dir(tmp_path)

        tasks = [{"title": f"任务 {i}"} for i in range(15)]
        example_file = tmp_path / "many_tasks.yaml"
        example_file.write_text(
            yaml.dump({"example": {"project_info": {"name": "多任务"}, "ideal_tasks": tasks}}, allow_unicode=True),
            encoding="utf-8",
        )

        content = selector.load_example_content({"file": "many_tasks.yaml"})
        # 应只包含前 8 个任务
        assert "任务 7" in content
        assert "任务 8" not in content

    def test_singleton_get_few_shot_selector_v2(self):
        """get_few_shot_selector_v2() 应返回同一实例"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            get_few_shot_selector_v2,
        )

        # 重置全局单例
        import intelligent_project_analyzer.services.few_shot_selector_v2 as mod

        mod._few_shot_selector_v2 = None

        s1 = get_few_shot_selector_v2()
        s2 = get_few_shot_selector_v2()
        assert s1 is s2

        # 清理
        mod._few_shot_selector_v2 = None


class TestP0_2_ProjectInputConstruction:
    """P0-2: 验证 task_oriented_expert_factory 中 project_input 的构建"""

    def test_calculate_project_extended_features_basic(self):
        """calculate_project_extended_features 应从 structured_data 计算特征"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            calculate_project_extended_features,
        )

        structured_data = {
            "project_type": "commercial retail interior design",
            "project_info": {
                "feature_vector": {
                    "commercial": 0.8,
                    "cultural": 0.3,
                    "historical": 0.2,
                    "symbolic": 0.1,
                }
            },
        }
        user_input = "我需要一个创新的商业空间设计"

        features = calculate_project_extended_features(structured_data, user_input)

        assert features["discipline"] == "interior"
        assert features["commercial_sensitivity"] > 0.5
        assert features["innovation_quotient"] > 0.5  # "创新" keyword
        assert "cultural_depth" in features
        assert "urgency" in features

    def test_calculate_project_extended_features_urgency(self):
        """紧急关键词应提高 urgency"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            calculate_project_extended_features,
        )

        features = calculate_project_extended_features({}, "紧急！需要尽快完成")
        assert features["urgency"] == 0.7

    def test_calculate_project_extended_features_empty_input(self):
        """空输入应返回中性默认值"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            calculate_project_extended_features,
        )

        features = calculate_project_extended_features({}, "")
        assert features["discipline"] == "multidisciplinary"
        assert features["urgency"] == 0.4
        assert features["innovation_quotient"] == 0.5

    def test_factory_s7_block_uses_singleton_import(self):
        """task_oriented_expert_factory S7.2 block 应使用 get_few_shot_selector_v2"""
        import inspect
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
            TaskOrientedExpertFactory,
        )

        source = inspect.getsource(TaskOrientedExpertFactory)
        assert "get_few_shot_selector_v2" in source
        assert "calculate_project_extended_features" in source

    def test_factory_s7_block_uses_load_example_content(self):
        """S7.2 block 应调用 load_example_content 而非读取 metadata"""
        import inspect
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
            TaskOrientedExpertFactory,
        )

        source = inspect.getsource(TaskOrientedExpertFactory)
        assert "load_example_content" in source
        # 旧代码不应存在
        assert 'meta.get("content"' not in source


# ============================================================================
# P0-3: Dimension auto-promotion write path + category mapping
# ============================================================================


class TestP0_3_DimensionAutoPromotion:
    """P0-3: 验证维度自动晋升写入 ontology.yaml 的完整路径"""

    def test_category_mapping_exists(self):
        """LearningScheduler 应包含 _CATEGORY_MAPPING"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        mapping = LearningScheduler._CATEGORY_MAPPING
        assert isinstance(mapping, dict)
        assert len(mapping) >= 6

    def test_category_mapping_values_are_tuples(self):
        """每个映射值应为 (project_type, category) 元组"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        for key, value in LearningScheduler._CATEGORY_MAPPING.items():
            assert isinstance(value, tuple), f"{key} 的值不是元组"
            assert len(value) == 2, f"{key} 的元组长度不为 2"

    def test_category_mapping_known_categories(self):
        """已知 LLM 提取的 category 应正确映射"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        mapping = LearningScheduler._CATEGORY_MAPPING

        # 空间类 → ontological_foundations
        assert mapping["spatial_experience"] == ("meta_framework", "ontological_foundations")
        assert mapping["material_system"] == ("meta_framework", "ontological_foundations")

        # 用户类 → contemporary_imperatives
        assert mapping["user_behavior"] == ("meta_framework", "contemporary_imperatives")

        # 商业类 → business_positioning
        assert mapping["business_logic"] == ("commercial_retail", "business_positioning")

        # 临时分类 → universal_dimensions
        assert mapping["extracted_from_expert"] == ("meta_framework", "universal_dimensions")

    def test_default_category_fallback(self):
        """未知 category 应回退到 meta_framework.universal_dimensions"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        assert LearningScheduler._DEFAULT_CATEGORY == ("meta_framework", "universal_dimensions")

    @pytest.mark.asyncio
    async def test_auto_promotion_calls_ontology_editor(self):
        """auto-promotion 应调用 OntologyEditor.append_dimension"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = [
            {
                "id": 1,
                "confidence_score": 0.95,
                "dimension_data": json.dumps(
                    {
                        "name": "空间节奏感",
                        "category": "spatial_experience",
                        "description": "空间的压缩与释放节奏",
                        "ask_yourself": "空间节奏如何影响体验？",
                        "examples": "走廊压缩, 大厅释放",
                    }
                ),
            }
        ]
        mock_db.approve_candidate.return_value = True

        mock_editor = MagicMock()
        mock_editor.append_dimension.return_value = True

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

        assert result["status"] == "success"
        assert result["auto_promoted"] == 1

    @pytest.mark.asyncio
    async def test_auto_promotion_uses_category_mapping(self):
        """auto-promotion 应使用 _CATEGORY_MAPPING 映射 category"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = [
            {
                "id": 42,
                "confidence_score": 0.92,
                "dimension_data": json.dumps(
                    {
                        "name": "用户行为模式",
                        "category": "user_behavior",
                        "description": "用户在空间中的行为模式",
                        "ask_yourself": "用户如何使用这个空间？",
                        "examples": "停留, 穿行, 聚集",
                    }
                ),
            }
        ]
        mock_db.approve_candidate.return_value = True

        mock_editor = MagicMock()
        mock_editor.append_dimension.return_value = True

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
            await LearningScheduler._run_dimension_auto_promotion()

        # 验证 append_dimension 被调用时使用了正确的映射
        call_args = mock_editor.append_dimension.call_args
        assert call_args.kwargs["project_type"] == "meta_framework"
        assert call_args.kwargs["category"] == "contemporary_imperatives"

    @pytest.mark.asyncio
    async def test_auto_promotion_refreshes_ontology_cache(self):
        """晋升成功后应刷新 ontology 缓存"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = [
            {
                "id": 1,
                "confidence_score": 0.95,
                "dimension_data": json.dumps(
                    {
                        "name": "测试维度",
                        "category": "extracted_from_expert",
                        "description": "测试",
                        "ask_yourself": "测试？",
                        "examples": "测试",
                    }
                ),
            }
        ]
        mock_db.approve_candidate.return_value = True

        mock_editor = MagicMock()
        mock_editor.append_dimension.return_value = True

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
            await LearningScheduler._run_dimension_auto_promotion()

        mock_ontology_service.reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_promotion_skips_low_confidence(self):
        """置信度 < 0.9 的候选不应被晋升"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = [
            {"id": 1, "confidence_score": 0.85, "dimension_data": "{}"},
            {"id": 2, "confidence_score": 0.5, "dimension_data": "{}"},
        ]

        mock_editor = MagicMock()

        with patch(
            "intelligent_project_analyzer.learning.database_manager.get_db_manager",
            return_value=mock_db,
        ), patch(
            "intelligent_project_analyzer.services.ontology_editor.get_ontology_editor",
            return_value=mock_editor,
        ):
            result = await LearningScheduler._run_dimension_auto_promotion()

        assert result["auto_promoted"] == 0
        mock_editor.append_dimension.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_promotion_handles_editor_failure(self):
        """OntologyEditor 写入失败时不应 approve_candidate"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = [
            {
                "id": 1,
                "confidence_score": 0.95,
                "dimension_data": json.dumps(
                    {
                        "name": "失败测试",
                        "category": "spatial_experience",
                        "description": "测试",
                        "ask_yourself": "？",
                        "examples": "无",
                    }
                ),
            }
        ]

        mock_editor = MagicMock()
        mock_editor.append_dimension.return_value = False  # 写入失败

        with patch(
            "intelligent_project_analyzer.learning.database_manager.get_db_manager",
            return_value=mock_db,
        ), patch(
            "intelligent_project_analyzer.services.ontology_editor.get_ontology_editor",
            return_value=mock_editor,
        ):
            result = await LearningScheduler._run_dimension_auto_promotion()

        assert result["auto_promoted"] == 0
        assert result["failed"] == 1
        mock_db.approve_candidate.assert_not_called()


# ============================================================================
# P1-1: admin_routes get_control_status fix
# ============================================================================


class TestP1_1_AdminRoutesMethodName:
    """P1-1: 验证 admin_routes 使用正确的方法名"""

    def test_adaptive_quality_controller_has_get_control_status(self):
        """AdaptiveQualityController 应有 get_control_status 方法"""
        from intelligent_project_analyzer.services.adaptive_quality_controller import (
            AdaptiveQualityController,
        )

        controller = AdaptiveQualityController()
        assert hasattr(controller, "get_control_status")
        assert callable(controller.get_control_status)

    def test_adaptive_quality_controller_no_get_status(self):
        """AdaptiveQualityController 不应有 get_status 方法（旧名称）"""
        from intelligent_project_analyzer.services.adaptive_quality_controller import (
            AdaptiveQualityController,
        )

        controller = AdaptiveQualityController()
        assert not hasattr(controller, "get_status")

    def test_get_control_status_returns_expected_fields(self):
        """get_control_status 应返回预期字段"""
        from intelligent_project_analyzer.services.adaptive_quality_controller import (
            AdaptiveQualityController,
        )

        controller = AdaptiveQualityController()
        status = controller.get_control_status()

        assert "timestamp" in status
        assert "current_quality_level" in status
        assert "current_action" in status
        assert "emergency_mode" in status
        assert "quality_history_size" in status

    def test_admin_routes_uses_get_control_status(self):
        """admin_routes 应调用 get_control_status 而非 get_status"""
        import inspect
        from intelligent_project_analyzer.api import admin_routes

        source = inspect.getsource(admin_routes)
        assert "get_control_status()" in source
        # 确保旧的错误调用不存在
        assert "adaptive_quality_controller.get_status()" not in source
