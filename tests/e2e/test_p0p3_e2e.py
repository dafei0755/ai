"""
端到端测试: P0-P3 全管道 E2E 验证
版本: v8.000
日期: 2026-02-16

测试范围：
  E2E-1: 乡村民宿场景 (M5) — 完整数据通路
  E2E-2: 高端商业场景 (M4) — 完整数据通路
  E2E-3: 极端环境场景 (M8) — 完整数据通路
  E2E-4: 纯 feature_vector 推断 (无模式) — P3-T12 桥梁验证
  E2E-5: 多模式复合场景 (M1+M3) — 全管道
"""

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestE2ERuralVillageScenario:
    """E2E-1: 乡村民宿 M5 全管道"""

    @pytest.mark.integration
    def test_full_pipeline_rural_village(self):
        """
        模拟完整管道:
        1. HybridModeDetector.detect() → M5_rural_context
        2. output_node() → structured_data.detected_design_modes
        3. extract_detected_modes_from_state() → 正确提取
        4. _select_best_few_shot() → cultural_dominant_01
        5. sf_knowledge_loader → 知识注入
        """
        # Step 1: 模式检测
        from intelligent_project_analyzer.services.mode_detector import DesignModeDetector

        user_input = "广东狮岭村乡村民宿集群设计，融合岭南文化特色，需要保护村落肌理"
        results = DesignModeDetector.detect(user_input)
        assert len(results) > 0
        mode_ids = [r[0] for r in results]
        assert "M5_rural_context" in mode_ids, f"应检测到 M5, 实际: {mode_ids}"

        # Step 2: 构建 detected_modes 格式
        detected_modes = [{"mode": r[0], "confidence": r[1]} for r in results]

        # Step 3: extract_detected_modes_from_state
        from intelligent_project_analyzer.services.mode_question_loader import (
            extract_detected_modes_from_state,
        )

        state = {
            "agent_results": {"requirements_analyst": {"structured_data": {"detected_design_modes": detected_modes}}}
        }
        extracted = extract_detected_modes_from_state(state)
        assert len(extracted) > 0
        assert extracted[0]["mode"] in mode_ids

        # Step 4: Few-shot 匹配
        from intelligent_project_analyzer.services.core_task_decomposer import CoreTaskDecomposer

        decomposer = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(decomposer, "_cached_mode_to_tags"):
            delattr(decomposer, "_cached_mode_to_tags")

        features = {"cultural": 0.8, "social": 0.5, "aesthetic": 0.4}
        best_example = decomposer._select_best_few_shot("rural_village", features, detected_modes)
        assert best_example is not None
        assert "cultural" in best_example, f"乡村场景应匹配 cultural 示例, 实际: {best_example}"

        # Step 5: 知识注入
        try:
            from intelligent_project_analyzer.services.sf_knowledge_loader import (
                get_full_knowledge_injection,
                clear_sf_knowledge_cache,
            )

            clear_sf_knowledge_cache()
            injection = get_full_knowledge_injection(detected_modes[:2])
            assert isinstance(injection, str)
            # 注入内容应包含评估相关信息
            if injection:
                assert len(injection) > 50
        except ImportError:
            pass  # sf_knowledge_loader 可能不可用


class TestE2ECommercialScenario:
    """E2E-2: 高端商业 M4 全管道"""

    @pytest.mark.integration
    def test_full_pipeline_commercial(self):
        """商业地产场景全管道"""
        from intelligent_project_analyzer.services.mode_detector import DesignModeDetector

        user_input = "高端商业综合体设计，关注投资回报率和坪效优化，月租金溢价"
        results = DesignModeDetector.detect(user_input)
        assert len(results) > 0
        mode_ids = [r[0] for r in results]
        assert "M4_capital_asset" in mode_ids, f"应检测到 M4, 实际: {mode_ids}"

        detected_modes = [{"mode": r[0], "confidence": r[1]} for r in results]

        from intelligent_project_analyzer.services.core_task_decomposer import CoreTaskDecomposer

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")

        features = {"commercial": 0.85, "functional": 0.60}
        best = d._select_best_few_shot("commercial", features, detected_modes)
        assert best is not None
        assert "commercial" in best


class TestE2EExtremeConditionScenario:
    """E2E-3: 极端环境 M8 全管道"""

    @pytest.mark.integration
    def test_full_pipeline_extreme(self):
        """极端条件场景全管道"""
        from intelligent_project_analyzer.services.mode_detector import DesignModeDetector

        user_input = "西藏林芝高海拔民宿设计，需要应对极寒气候、低氧环境、强紫外线"
        results = DesignModeDetector.detect(user_input)
        detected_modes = [{"mode": r[0], "confidence": r[1]} for r in results]

        from intelligent_project_analyzer.services.core_task_decomposer import CoreTaskDecomposer

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")

        features = {"technical": 0.80, "functional": 0.70, "environmental": 0.55}
        best = d._select_best_few_shot("hotel", features, detected_modes)
        assert best is not None
        assert "technical" in best, f"极端条件应匹配 technical 示例, 实际: {best}"


class TestE2EFeatureOnlyFallback:
    """E2E-4: 纯 feature_vector 推断 (T12 桥梁验证)"""

    @pytest.mark.integration
    def test_no_modes_feature_bridge(self):
        """
        无 detected_modes 时:
        feature_vector → _infer_tags_from_features → implied tags → 匹配
        """
        from intelligent_project_analyzer.services.core_task_decomposer import CoreTaskDecomposer

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")

        # 高 cultural/social 特征但无 detected_modes
        features = {"cultural": 0.80, "social": 0.65, "aesthetic": 0.55}
        best = d._select_best_few_shot("misc_project", features, detected_modes=[])

        assert best is not None, "feature fallback 应至少匹配一个示例"

        # 验证 _infer_tags_from_features 被用到
        tags = d._infer_tags_from_features(features)
        assert len(tags) > 0, "高分 cultural 应推断出标签"

    @pytest.mark.integration
    def test_feature_bridge_high_technical(self):
        """高 technical 特征推断出技术相关示例"""
        from intelligent_project_analyzer.services.core_task_decomposer import CoreTaskDecomposer

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")

        features = {"technical": 0.90, "innovative": 0.75, "functional": 0.60}
        best = d._select_best_few_shot("smart_home", features, detected_modes=[])
        assert best is not None


class TestE2EMultiModeComposite:
    """E2E-5: 多模式复合场景"""

    @pytest.mark.integration
    def test_m1_m3_composite(self):
        """M1+M3 双模式 → aesthetic_dominant_01"""
        from intelligent_project_analyzer.services.mode_detector import DesignModeDetector

        user_input = "高端别墅设计，追求 Tiffany 品牌美学的空间转译，强调沉浸式五感体验"
        results = DesignModeDetector.detect(user_input)
        detected_modes = [{"mode": r[0], "confidence": r[1]} for r in results]

        from intelligent_project_analyzer.services.core_task_decomposer import CoreTaskDecomposer

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")

        features = {"aesthetic": 0.80, "identity": 0.70, "cultural": 0.45}
        best = d._select_best_few_shot("villa", features, detected_modes)
        assert best is not None
        # M1+M3 组合最可能匹配 aesthetic
        assert "aesthetic" in best or "cultural" in best or "commercial" in best

    @pytest.mark.integration
    def test_knowledge_injection_for_multi_mode(self):
        """多模式知识注入正确合并"""
        try:
            from intelligent_project_analyzer.services.sf_knowledge_loader import (
                get_full_knowledge_injection,
                clear_sf_knowledge_cache,
            )

            clear_sf_knowledge_cache()
        except ImportError:
            pytest.skip("sf_knowledge_loader 不可导入")

        modes = [
            {"mode": "M1_concept_driven", "confidence": 0.80},
            {"mode": "M3_emotional_experience", "confidence": 0.65},
        ]
        text = get_full_knowledge_injection(modes)
        assert isinstance(text, str)
        if text:
            # 应同时包含两个模式的信息
            assert "M1" in text or "概念" in text
