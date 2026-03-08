"""
集成测试 — S7 Few-Shot Pipeline + S1 Dimension Promotion Pipeline

覆盖:
- S7: factory → selector → content loading → prompt injection
- S1: extractor → scheduler → ontology_editor → cache refresh

Version: v7.620
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ============================================================================
# S7 集成测试: Few-Shot Pipeline
# ============================================================================


class TestS7Integration_FewShotPipeline:
    """S7 集成: factory 构建 project_input → selector 匹配 → content 加载 → prompt 注入"""

    @pytest.fixture
    def temp_examples_dir(self, tmp_path):
        """创建包含注册表和示例文件的临时目录"""
        # 创建示例 YAML
        example_data = {
            "example": {
                "project_info": {
                    "name": "商业综合体改造",
                    "description": "城市核心区商业综合体空间改造设计",
                },
                "ideal_tasks": [
                    {"title": "搜索 标杆商业综合体的空间设计策略"},
                    {"title": "搜索 动线组织与业态分布逻辑"},
                ],
            }
        }
        example_file = tmp_path / "commercial_dominant_01.yaml"
        example_file.write_text(yaml.dump(example_data, allow_unicode=True), encoding="utf-8")

        # 创建注册表
        registry = {
            "examples": [
                {
                    "id": "commercial_dominant_01",
                    "name": "商业综合体改造",
                    "file": "commercial_dominant_01.yaml",
                    "layer": 1,
                    "strength": "strong",
                    "tags_matrix": {
                        "space_type": ["commercial", "retail"],
                        "scale": ["large"],
                        "design_style": ["modern"],
                        "project_stage": ["renovation"],
                        "client_type": ["corporate"],
                        "budget_level": ["high"],
                        "location_type": ["urban"],
                    },
                    "feature_vector": {
                        "commercial": 0.9,
                        "cultural": 0.2,
                        "functional": 0.7,
                    },
                }
            ]
        }
        registry_file = tmp_path / "examples_registry.yaml"
        registry_file.write_text(yaml.dump(registry, allow_unicode=True), encoding="utf-8")

        return tmp_path

    def test_selector_match_and_load_content_pipeline(self, temp_examples_dir):
        """完整管线: 构建 project_input → 匹配 → 加载内容"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            FewShotSelectorV2,
            calculate_project_extended_features,
        )

        selector = FewShotSelectorV2(examples_dir=temp_examples_dir)

        # 1. 构建 project_input（模拟 factory 中的逻辑）
        structured_reqs = {
            "project_type": "commercial retail interior",
            "project_info": {"feature_vector": {"commercial": 0.8, "cultural": 0.1}},
        }
        user_input = "商业空间改造设计"
        extended_features = calculate_project_extended_features(structured_reqs, user_input)

        project_input = {
            "tags_matrix": {},
            "feature_vector": structured_reqs.get("project_info", {}).get("feature_vector", {}),
            **extended_features,
        }

        # 2. 匹配
        matched = selector.match_examples_v2(project_input, user_id="test-session", top_k=2)

        # 3. 加载内容
        loaded_contents = []
        for ex in matched:
            meta = ex.get("metadata", {})
            content = selector.load_example_content(meta)
            if content:
                loaded_contents.append(content)

        # 验证: 至少匹配到 1 个示例且内容非空
        assert len(matched) >= 1
        assert len(loaded_contents) >= 1
        assert "商业综合体改造" in loaded_contents[0]
        assert "标杆商业综合体" in loaded_contents[0]

    def test_project_input_with_dict_project_type(self):
        """project_type 为 dict 时应正确处理"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            calculate_project_extended_features,
        )

        # project_type 可能是 dict 格式
        structured_reqs = {
            "project_type": {"primary": "landscape park design", "secondary": "urban"},
        }
        features = calculate_project_extended_features(structured_reqs, "公园设计")
        # 不应抛出异常
        assert "discipline" in features

    def test_few_shot_injection_into_prompt(self, temp_examples_dir):
        """验证 few-shot 内容能正确注入到 system prompt"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            FewShotSelectorV2,
        )

        selector = FewShotSelectorV2(examples_dir=temp_examples_dir)

        # 模拟匹配结果
        project_input = {
            "tags_matrix": {"space_type": ["commercial"]},
            "feature_vector": {"commercial": 0.9},
            "discipline": "interior",
            "urgency": 0.4,
            "innovation_quotient": 0.5,
            "commercial_sensitivity": 0.8,
            "cultural_depth": 0.2,
        }
        matched = selector.match_examples_v2(project_input, user_id="test", top_k=1)

        # 构建 few-shot block（模拟 factory 逻辑）
        base_prompt = "你是一个设计专家。"
        few_shot_texts = []
        for ex in matched:
            content = selector.load_example_content(ex.get("metadata", {}))
            if content:
                few_shot_texts.append(content)

        if few_shot_texts:
            few_shot_block = "\n\n## 参考示例\n" + "\n---\n".join(few_shot_texts)
            base_prompt = base_prompt + few_shot_block

        assert "## 参考示例" in base_prompt
        assert "商业综合体改造" in base_prompt

    def test_record_usage_after_injection(self, temp_examples_dir):
        """注入后应记录使用历史"""
        from intelligent_project_analyzer.services.few_shot_selector_v2 import (
            FewShotSelectorV2,
        )

        selector = FewShotSelectorV2(examples_dir=temp_examples_dir)

        project_input = {
            "tags_matrix": {"space_type": ["commercial"]},
            "feature_vector": {"commercial": 0.9},
        }
        matched = selector.match_examples_v2(project_input, user_id="user-1", top_k=1)

        for ex in matched:
            selector.record_usage(ex.get("example_id", ""), "user-1")

        # 验证历史已记录
        assert selector.user_history["user-1"] is not None


# ============================================================================
# S1 集成测试: Dimension Promotion Pipeline
# ============================================================================


class TestS1Integration_DimensionPromotionPipeline:
    """S1 集成: extractor 提取 → DB 存储 → scheduler 审批 → ontology 写入 → 缓存刷新"""

    @pytest.mark.asyncio
    async def test_full_promotion_pipeline(self, tmp_path):
        """完整管线: 候选维度 → 自动审批 → 写入 ontology → 刷新缓存"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        # 模拟 DB 返回高置信度候选
        candidate = {
            "id": 100,
            "confidence_score": 0.95,
            "dimension_data": json.dumps(
                {
                    "name": "材料触感体验",
                    "category": "material_system",
                    "description": "材料表面触感对空间体验的影响",
                    "ask_yourself": "用户触摸材料时会有什么感受？",
                    "examples": "粗糙石材, 光滑金属, 温暖木材",
                }
            ),
        }

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = [candidate]
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

        # 验证完整管线
        assert result["status"] == "success"
        assert result["auto_promoted"] == 1

        # 验证 ontology_editor 被正确调用
        mock_editor.append_dimension.assert_called_once()
        call_kwargs = mock_editor.append_dimension.call_args.kwargs
        assert call_kwargs["project_type"] == "meta_framework"
        assert call_kwargs["category"] == "ontological_foundations"  # material_system 映射
        assert call_kwargs["dimension_data"]["name"] == "材料触感体验"

        # 验证 DB approve 被调用
        mock_db.approve_candidate.assert_called_once_with(100, reviewer_id="auto_scheduler")

        # 验证缓存刷新
        mock_ontology_service.reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_mixed_confidence_candidates(self):
        """混合置信度候选: 只有高置信度的被晋升"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        candidates = [
            {
                "id": 1,
                "confidence_score": 0.95,
                "dimension_data": json.dumps(
                    {
                        "name": "高置信度维度",
                        "category": "spatial_experience",
                        "description": "测试",
                        "ask_yourself": "？",
                        "examples": "无",
                    }
                ),
            },
            {
                "id": 2,
                "confidence_score": 0.75,  # 低于阈值
                "dimension_data": json.dumps(
                    {
                        "name": "低置信度维度",
                        "category": "user_behavior",
                        "description": "测试",
                        "ask_yourself": "？",
                        "examples": "无",
                    }
                ),
            },
            {
                "id": 3,
                "confidence_score": 0.92,
                "dimension_data": json.dumps(
                    {
                        "name": "中高置信度维度",
                        "category": "business_logic",
                        "description": "测试",
                        "ask_yourself": "？",
                        "examples": "无",
                    }
                ),
            },
        ]

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = candidates
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

        assert result["auto_promoted"] == 2  # id=1 和 id=3
        assert result["pending_reviewed"] == 3
        assert mock_editor.append_dimension.call_count == 2

    @pytest.mark.asyncio
    async def test_partial_failure_pipeline(self):
        """部分写入失败时: 成功的应 approve, 失败的不应 approve"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        candidates = [
            {
                "id": 1,
                "confidence_score": 0.95,
                "dimension_data": json.dumps(
                    {
                        "name": "成功维度",
                        "category": "spatial_experience",
                        "description": "测试",
                        "ask_yourself": "？",
                        "examples": "无",
                    }
                ),
            },
            {
                "id": 2,
                "confidence_score": 0.95,
                "dimension_data": json.dumps(
                    {
                        "name": "失败维度",
                        "category": "material_system",
                        "description": "测试",
                        "ask_yourself": "？",
                        "examples": "无",
                    }
                ),
            },
        ]

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = candidates
        mock_db.approve_candidate.return_value = True

        mock_editor = MagicMock()
        # 第一次成功，第二次失败
        mock_editor.append_dimension.side_effect = [True, False]

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

        assert result["auto_promoted"] == 1
        assert result["failed"] == 1
        # 只有 id=1 被 approve
        mock_db.approve_candidate.assert_called_once_with(1, reviewer_id="auto_scheduler")

    @pytest.mark.asyncio
    async def test_dimension_data_as_dict_not_string(self):
        """dimension_data 已经是 dict 时也应正确处理"""
        from intelligent_project_analyzer.services.learning_scheduler import (
            LearningScheduler,
        )

        mock_db = MagicMock()
        mock_db.get_pending_candidates.return_value = [
            {
                "id": 1,
                "confidence_score": 0.95,
                "dimension_data": {  # 直接是 dict
                    "name": "直接字典维度",
                    "category": "environmental_response",
                    "description": "测试",
                    "ask_yourself": "？",
                    "examples": "无",
                },
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

        assert result["auto_promoted"] == 1
        call_kwargs = mock_editor.append_dimension.call_args.kwargs
        assert call_kwargs["project_type"] == "meta_framework"
        assert call_kwargs["category"] == "ontological_foundations"

    @pytest.mark.asyncio
    async def test_unknown_category_uses_default(self):
        """未知 category 应使用默认映射"""
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
                        "name": "未知分类维度",
                        "category": "completely_unknown_category",
                        "description": "测试",
                        "ask_yourself": "？",
                        "examples": "无",
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

        call_kwargs = mock_editor.append_dimension.call_args.kwargs
        assert call_kwargs["project_type"] == "meta_framework"
        assert call_kwargs["category"] == "universal_dimensions"  # 默认回退
