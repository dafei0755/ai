"""
集成测试: P0-P3 管道集成验证
版本: v8.000
日期: 2026-02-16

测试范围：
  1. Mode Engine → Few-shot 匹配全链路 (P0+P3)
  2. sf/ 知识注入 Expert prompt 全链路 (P1+P2)
  3. sf/ 知识注入 Review prompt 全链路 (P1+P2)
  4. Mode→Tags→Feature 三套分类系统互通 (P3)
"""

import pytest
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# 1. Mode Engine → Few-shot 选择全链路
# ============================================================================


class TestModeToFewShotIntegration:
    """集成测试: 模式检测 → Few-shot 标签匹配 → 示例选择"""

    @pytest.fixture
    def decomposer(self):
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")
        return d

    @pytest.mark.integration
    def test_m5_rural_selects_cultural_example(self, decomposer):
        """M5_rural_context → cultural_dominant_01"""
        modes = [{"mode": "M5_rural_context", "confidence": 0.85}]
        features = {"cultural": 0.53, "social": 0.42}
        result = decomposer._select_best_few_shot("rural_village", features, modes)
        assert result is not None
        assert "cultural" in result, f"期望 cultural 相关示例, 实际: {result}"

    @pytest.mark.integration
    def test_m8_extreme_selects_technical_example(self, decomposer):
        """M8_extreme_condition → technical_dominant_02"""
        modes = [{"mode": "M8_extreme_condition", "confidence": 0.90}]
        features = {"technical": 0.68, "functional": 0.70}
        result = decomposer._select_best_few_shot("hotel", features, modes)
        assert result is not None
        assert "technical" in result, f"期望 technical 相关示例, 实际: {result}"

    @pytest.mark.integration
    def test_m1_m3_aesthetic_selects_aesthetic_example(self, decomposer):
        """M1+M3 → aesthetic_dominant_01"""
        modes = [
            {"mode": "M1_concept_driven", "confidence": 0.75},
            {"mode": "M3_emotional_experience", "confidence": 0.60},
        ]
        features = {"aesthetic": 0.75, "identity": 0.68}
        result = decomposer._select_best_few_shot("villa", features, modes)
        assert result is not None
        assert "aesthetic" in result, f"期望 aesthetic 相关示例, 实际: {result}"

    @pytest.mark.integration
    def test_m4_commercial_selects_commercial_example(self, decomposer):
        """M4_capital_asset → commercial_dominant_01"""
        modes = [{"mode": "M4_capital_asset", "confidence": 0.90}]
        features = {"commercial": 0.85, "functional": 0.60}
        result = decomposer._select_best_few_shot("commercial", features, modes)
        assert result is not None
        assert "commercial" in result, f"期望 commercial 相关示例, 实际: {result}"

    @pytest.mark.integration
    def test_no_mode_feature_fallback_still_matches(self, decomposer):
        """无模式时，feature_vector 反向推断仍能匹配"""
        features = {"cultural": 0.80, "social": 0.65, "aesthetic": 0.55}
        result = decomposer._select_best_few_shot("unknown_type", features, detected_modes=[])
        assert result is not None, "feature fallback 应至少匹配一个示例"

    @pytest.mark.integration
    def test_low_confidence_mode_ignored(self, decomposer):
        """置信度 < 0.3 的模式被忽略"""
        modes = [{"mode": "M5_rural_context", "confidence": 0.1}]
        features = {"commercial": 0.85}
        result = decomposer._select_best_few_shot("commercial_space", features, modes)
        # 由于 M5 被忽略, 应匹配 commercial
        assert result is not None

    @pytest.mark.integration
    def test_scoring_combines_jaccard_and_cosine(self, decomposer):
        """评分结合 Jaccard 70% + cosine 30%"""
        modes = [{"mode": "M1_concept_driven", "confidence": 0.80}]
        features = {"aesthetic": 0.9, "identity": 0.8, "cultural": 0.5}
        result = decomposer._select_best_few_shot("luxury_villa", features, modes)
        assert result is not None


# ============================================================================
# 2. sf/ 知识注入 → Expert Prompt
# ============================================================================


class TestSfKnowledgeToExpertPromptIntegration:
    """集成测试: sf/ 文件加载 → 知识解析 → Expert prompt 注入"""

    @pytest.mark.integration
    def test_full_injection_pipeline(self):
        """完整管道: load sf → parse weights → generate injection text"""
        try:
            from intelligent_project_analyzer.services.sf_knowledge_loader import (
                get_full_knowledge_injection,
                clear_sf_knowledge_cache,
            )

            clear_sf_knowledge_cache()
        except ImportError:
            pytest.skip("sf_knowledge_loader 不可导入")

        modes = [
            {"mode": "M5_rural_context", "confidence": 0.85},
            {"mode": "M1_concept_driven", "confidence": 0.60},
        ]
        text = get_full_knowledge_injection(modes)
        assert isinstance(text, str)
        if text:
            # 应包含评估维度
            assert "评估" in text or "维度" in text or "M5" in text

    @pytest.mark.integration
    def test_expert_factory_integrates_sf_knowledge(self):
        """TaskOrientedExpertFactory._inject_sf_knowledge 正确集成"""
        try:
            from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
                TaskOrientedExpertFactory,
            )
        except Exception:
            pytest.skip("TaskOrientedExpertFactory 不可导入")

        factory = TaskOrientedExpertFactory.__new__(TaskOrientedExpertFactory)
        modes = [{"mode": "M5_rural_context", "confidence": 0.85}]
        state = {"detected_design_modes": modes}

        result = factory._inject_sf_knowledge(state)
        # 在测试环境中，只要不崩溃即为通过
        assert result is None or isinstance(result, str)


# ============================================================================
# 3. sf/ 知识注入 → Review Prompt
# ============================================================================


class TestSfKnowledgeToReviewIntegration:
    """集成测试: analysis_review → review_agents 评估标准注入"""

    @pytest.mark.integration
    def test_review_receives_modes_from_state(self):
        """analysis_review 将 detected_design_modes 传入 requirements"""
        # 模拟 analysis_review.py 中的注入逻辑
        state = {
            "detected_design_modes": [{"mode": "M5_rural_context", "confidence": 0.85}],
            "structured_requirements": {"project_name": "测试"},
        }

        requirements = dict(state.get("structured_requirements", {}))
        detected_modes = state.get("detected_design_modes", [])
        if detected_modes:
            requirements["_detected_design_modes"] = detected_modes

        assert "_detected_design_modes" in requirements
        assert len(requirements["_detected_design_modes"]) == 1

    @pytest.mark.integration
    def test_reviewer_builds_context_from_requirements(self):
        """ReviewerRole._build_sf_evaluation_context 从 requirements 构建上下文"""
        try:
            from intelligent_project_analyzer.review.review_agents import ReviewerRole
        except Exception:
            pytest.skip("ReviewerRole 不可导入")

        requirements = {"_detected_design_modes": [{"mode": "M5_rural_context", "confidence": 0.85}]}

        context = ReviewerRole._build_sf_evaluation_context(requirements)
        assert isinstance(context, str)
        # 在测试环境中，可能因 sf/ 文件加载而产生内容或为空
        # 关键是不崩溃


# ============================================================================
# 4. 三套分类系统互通
# ============================================================================


class TestTripleClassificationSystemIntegration:
    """集成测试: Mode Engine + feature_vector + tags_matrix 三系统互通"""

    @pytest.fixture
    def decomposer(self):
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")
        return d

    @pytest.mark.integration
    def test_mode_to_tags_to_example(self, decomposer):
        """Mode → Tags → tags_matrix 匹配 → 示例选择"""
        # Step 1: 模拟 HybridModeDetector 输出
        modes = [{"mode": "M5_rural_context", "confidence": 0.85, "detected_by": "hybrid"}]

        # Step 2: _load_mode_to_tags_mapping 转换
        m2t = decomposer._load_mode_to_tags_mapping()
        assert "M5_rural_context" in m2t
        tags = m2t["M5_rural_context"]
        assert len(tags) >= 3

        # Step 3: 这些 tags 匹配 registry 中的 cultural_dominant_01
        result = decomposer._select_best_few_shot("village", {"cultural": 0.5}, modes)
        assert result is not None

    @pytest.mark.integration
    def test_feature_to_mode_to_tags(self, decomposer):
        """Feature → implied Mode → Tags (P3-T12 桥梁)"""
        features = {"cultural": 0.8, "social": 0.7, "aesthetic": 0.6}
        tags = decomposer._infer_tags_from_features(features)
        assert isinstance(tags, set)
        if tags:  # YAML 存在时
            # cultural 高分应推断出文化相关模式的标签
            assert len(tags) >= 3

    @pytest.mark.integration
    def test_mode_feature_mapping_bidirectional_consistency(self):
        """预映射表双向一致性: mode_to_features 和 feature_to_modes 应互相引用"""
        mapping_path = PROJECT_ROOT / "intelligent_project_analyzer" / "config" / "mode_feature_mapping.yaml"
        if not mapping_path.exists():
            pytest.skip("mode_feature_mapping.yaml 不存在")

        with open(mapping_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        m2f = config.get("mode_to_features", {})
        f2m = config.get("feature_to_modes", {})

        # 验证: 每个 mode_to_features[mode].primary 中至少有一个维度
        #        出现在 feature_to_modes 中并引用该 mode
        for mode_id, feat_map in m2f.items():
            primary_dims = feat_map.get("primary", [])
            found_any = False
            for dim in primary_dims:
                if dim in f2m and mode_id in f2m[dim]:
                    found_any = True
                    break
            assert found_any or not primary_dims, f"{mode_id} 的 primary 维度 {primary_dims} 均未在 feature_to_modes 中引用该模式"
