"""
单元测试：设计模式检测器（Mode Detector）
版本: v1.0
日期: 2026-02-12

测试范围：
1. DesignModeDetector - 关键词快速检测
2. HybridModeDetector - 混合策略检测
3. 10种设计模式的识别准确性
"""

import pytest
from intelligent_project_analyzer.services.mode_detector import (
    DesignModeDetector,
    HybridModeDetector,
    get_mode_name,
    detect_design_modes,
)


class TestDesignModeDetector:
    """测试基础关键词检测器"""

    def test_m1_concept_driven_detection(self):
        """测试M1概念驱动型检测"""
        user_input = """
        我想设计一个高端住宅项目，强调品牌精神和文化母题的表达。
        空间需要围绕"文人精神"这个核心概念展开，追求内在的艺术价值。
        """

        results = DesignModeDetector.detect(user_input)

        # 验证检测到M1
        assert len(results) > 0
        top_mode = results[0][0]
        assert top_mode == "M1_concept_driven"

        # 验证置信度
        confidence = results[0][1]
        assert confidence > 0.5

    def test_m2_function_efficiency_detection(self):
        """测试M2功能效率型检测"""
        user_input = """
        办公空间设计，需要优化动线流程，提升运转效率。
        重点是标准化办公流程，减少干扰，确保系统高效运行。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        top_mode = results[0][0]
        assert top_mode == "M2_function_efficiency"
        assert results[0][1] > 0.6

    def test_m3_emotional_experience_detection(self):
        """测试M3情绪体验型检测"""
        user_input = """
        精品酒店设计，追求沉浸式体验，通过五感调动创造记忆锚点。
        空间需要有明确的情绪节奏，从压缩到释放到高潮。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        top_mode = results[0][0]
        assert top_mode == "M3_emotional_experience"
        assert results[0][1] > 0.5

    def test_m4_capital_asset_detection(self):
        """测试M4资产资本型检测"""
        user_input = """
        商业地产项目，关注投资回报率和坪效优化。
        需要提升租金溢价和现金流，确保资产价值最大化。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        mode_ids = [r[0] for r in results]
        assert "M4_capital_asset" in mode_ids

    def test_m5_rural_context_detection(self):
        """测试M5乡建在地型检测"""
        user_input = """
        乡村民宿项目，需要体现地域文化和本地材料特色。
        设计要融入村落肌理，构建农文旅经济闭环。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        mode_ids = [r[0] for r in results]
        assert "M5_rural_context" in mode_ids

    def test_m6_urban_regeneration_detection(self):
        """测试M6城市更新型检测"""
        user_input = """
        老街区改造项目，厂房改造，重构城市片区价值。
        需要打造公共界面，植入新业态，形成城市IP。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        mode_ids = [r[0] for r in results]
        assert "M6_urban_regeneration" in mode_ids

    def test_m7_tech_integration_detection(self):
        """测试M7技术整合型检测"""
        user_input = """
        智能住宅设计，全屋智能系统，AI技术深度整合。
        需要预留技术接口，支持系统可迭代升级。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        mode_ids = [r[0] for r in results]
        assert "M7_tech_integration" in mode_ids

    def test_m8_extreme_condition_detection(self):
        """测试M8极端环境型检测"""
        user_input = """
        西藏林芝高海拔酒店，海拔3000米，需要考虑供氧系统。
        极寒环境，必须处理抗风压、保温、紫外线防护。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        top_mode = results[0][0]
        assert top_mode == "M8_extreme_condition"

        # M8权重更高，应有高置信度
        assert results[0][1] > 0.7

    def test_m9_social_structure_detection(self):
        """测试M9社会结构型检测"""
        user_input = """
        三代同堂住宅，多代同堂家庭设计。
        需要处理代际关系、隐私分区、权力距离，设计冲突缓冲空间。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        top_mode = results[0][0]
        assert top_mode == "M9_social_structure"

        # M9权重高，特征明确
        assert results[0][1] > 0.7

    def test_m10_future_speculation_detection(self):
        """测试M10未来推演型检测"""
        user_input = """
        长周期战略项目，需要预判未来生活方式趋势。
        设计可迭代接口，为远程办公、AI技术预留升级空间。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        mode_ids = [r[0] for r in results]
        assert "M10_future_speculation" in mode_ids

    def test_m11_healthcare_healing_detection(self):
        """测试M11健康疗愈型检测"""
        user_input = """
        养老护理中心设计，需要为失智老人提供安全感和尊严。
        空间要降低焦虑，配置昼夜节律照明和无障碍动线。
        """

        results = DesignModeDetector.detect(user_input)

        assert len(results) > 0
        mode_ids = [r[0] for r in results]
        assert "M11_healthcare_healing" in mode_ids

    def test_multi_mode_detection(self):
        """测试多模式组合检测"""
        user_input = """
        高端酒店投资项目，既要追求情绪体验，也要关注资产回报。
        通过沉浸式设计提升客单价和RevPAR。
        """

        results = DesignModeDetector.detect(user_input)

        # 应检测到多个模式
        assert len(results) >= 2

        mode_ids = [r[0] for r in results]
        # M3情绪体验 + M4资产资本
        assert "M3_emotional_experience" in mode_ids
        assert "M4_capital_asset" in mode_ids

    def test_no_clear_mode_fallback(self):
        """测试无明确模式时的默认处理"""
        user_input = "帮我设计一个房子"

        primary_mode = DesignModeDetector.detect_primary_mode(user_input)

        # 应返回默认模式M2
        assert primary_mode == "M2_function_efficiency"


class TestHybridModeDetector:
    """测试混合检测器"""

    def test_sync_detection(self):
        """测试同步检测（仅关键词）"""
        user_input = "西藏高原民宿，海拔3500米，供氧系统设计"

        results = HybridModeDetector.detect_sync(user_input)

        assert len(results) > 0
        assert results[0]["mode"] == "M8_extreme_condition"
        assert results[0]["detected_by"] == "keyword"
        assert results[0]["confidence"] > 0.5

    def test_with_structured_requirements(self):
        """测试结合结构化需求的检测"""
        user_input = "酒店设计"
        structured_reqs = {"project_type": {"primary": "精品酒店", "secondary": ["沉浸式体验", "情绪调动"]}}

        results = HybridModeDetector.detect_sync(user_input, structured_requirements=structured_reqs)

        assert len(results) > 0
        mode_ids = [r["mode"] for r in results]
        assert "M3_emotional_experience" in mode_ids


class TestUtilityFunctions:
    """测试工具函数"""

    def test_get_mode_name(self):
        """测试模式名称获取"""
        assert get_mode_name("M1_concept_driven") == "概念驱动型设计"
        assert get_mode_name("M8_extreme_condition") == "极端环境型设计"
        assert get_mode_name("invalid_mode") == "invalid_mode"

    def test_detect_design_modes_convenience(self):
        """测试便捷函数"""
        user_input = "高海拔酒店，西藏林芝"

        results = detect_design_modes(user_input)

        assert isinstance(results, list)
        assert len(results) > 0
        assert "mode" in results[0]
        assert "confidence" in results[0]


class TestModeSignatures:
    """测试模式特征定义的完整性"""

    def test_all_modes_defined(self):
        """验证所有11个模式都有定义"""
        expected_modes = [
            "M1_concept_driven",
            "M2_function_efficiency",
            "M3_emotional_experience",
            "M4_capital_asset",
            "M5_rural_context",
            "M6_urban_regeneration",
            "M7_tech_integration",
            "M8_extreme_condition",
            "M9_social_structure",
            "M10_future_speculation",
            "M11_healthcare_healing",
        ]

        signatures = DesignModeDetector.MODE_SIGNATURES

        for mode in expected_modes:
            assert mode in signatures

            # 验证必需字段
            assert "name" in signatures[mode]
            assert "keywords" in signatures[mode]
            assert "scenarios" in signatures[mode]
            assert "weight" in signatures[mode]
            assert isinstance(signatures[mode]["keywords"], list)
            assert isinstance(signatures[mode]["scenarios"], list)

    def test_keywords_coverage(self):
        """验证关键词覆盖度"""
        for mode_id, signature in DesignModeDetector.MODE_SIGNATURES.items():
            # 每个模式至少5个关键词
            assert len(signature["keywords"]) >= 5, f"{mode_id} 关键词数量不足: {len(signature['keywords'])}"

            # 每个模式至少3个场景
            assert len(signature["scenarios"]) >= 3, f"{mode_id} 场景数量不足: {len(signature['scenarios'])}"


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_input(self):
        """测试空输入"""
        results = DesignModeDetector.detect("")

        # 应返回默认模式或空列表
        # 根据实现，可能返回置信度很低的结果
        if results:
            assert all(r[1] < 0.5 for r in results)

    def test_very_short_input(self):
        """测试极短输入"""
        results = DesignModeDetector.detect("办公室")

        if results:
            assert results[0][0] == "M2_function_efficiency"

    def test_chinese_english_mixed(self):
        """测试中英混合输入"""
        user_input = "Smart office design with AI integration and high efficiency"

        # 英文关键词应该也能工作（转小写后）
        results = DesignModeDetector.detect(user_input)

        # 不要求一定命中模式，但应稳定返回列表
        assert isinstance(results, list)


# ═══════════════════════════════════════════════════════════
# 集成测试标记（需要LLM的测试）
# ═══════════════════════════════════════════════════════════


@pytest.mark.llm
class TestLLMBasedDetection:
    """需要LLM的测试（标记为llm，默认跳过）"""

    def test_llm_enhanced_detection(self):
        """测试LLM增强检测（需要真实LLM）"""
        # 这个测试需要真实的LLM客户端
        # 在集成测试中运行
        pytest.skip("需要真实LLM客户端")


# ═══════════════════════════════════════════════════════════
# 性能测试
# ═══════════════════════════════════════════════════════════


class TestPerformance:
    """性能测试"""

    def test_detection_speed(self):
        """测试检测速度（应<50ms）"""
        import time

        user_input = "西藏高原酒店设计，海拔3000米，需要供氧系统"

        start = time.time()
        results = DesignModeDetector.detect(user_input)
        elapsed = (time.time() - start) * 1000

        assert elapsed < 50, f"检测耗时{elapsed:.1f}ms，超过50ms阈值"
        assert len(results) > 0

    def test_batch_detection_performance(self):
        """测试批量检测性能"""
        import time

        test_inputs = [
            "高端住宅品牌设计",
            "办公空间效率优化",
            "酒店情绪体验设计",
            "商业地产投资回报",
            "乡村民宿在地文化",
            "老街区城市更新",
            "智能家居技术整合",
            "西藏高原极端环境",
            "三代同堂社会结构",
            "未来办公空间推演",
        ]

        start = time.time()
        for input_text in test_inputs:
            DesignModeDetector.detect(input_text)
        total_elapsed = (time.time() - start) * 1000

        avg_elapsed = total_elapsed / len(test_inputs)

        assert avg_elapsed < 50, f"平均耗时{avg_elapsed:.1f}ms，超过50ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
