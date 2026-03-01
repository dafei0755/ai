"""
tests/unit/services/test_change_intent_detector.py

MT-5 验收测试：语义变更感知检测器（词表版）

测试覆盖：
  TC-01: 颜色变更 → VISUAL_ONLY
  TC-02: 材质变更 → VISUAL_ONLY
  TC-03: 装饰变更 → VISUAL_ONLY
  TC-04: 空间类型变更（客厅→卧室）→ SPATIAL_ZONE
  TC-05: 功能区划变更（打通）→ SPATIAL_ZONE
  TC-06: 身份变更（独居→养老）→ IDENTITY_PATTERN
  TC-07: 生活方式变更（电竞）→ IDENTITY_PATTERN
  TC-08: 混合文本（身份词优先于空间词）→ IDENTITY_PATTERN
  TC-09: 空文本 → VISUAL_ONLY（默认分支）
  TC-10: 空间词 + 身份词共存 → IDENTITY_PATTERN（优先级规则）

MT-5 验收标准：
  pytest tests/unit/services/test_change_intent_detector.py 通过（含 10 组典型用例）
  路由热路径延迟增加 < 5ms
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from intelligent_project_analyzer.services.change_intent_detector import (
    ChangeIntentType,
    DetectionResult,
    detect_change_intent,
    detect_change_intent_detailed,
    reload_keywords,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def clear_keyword_cache():
    """每个测试前后清除 lru_cache，保证词表状态干净。"""
    reload_keywords()
    yield
    reload_keywords()


# ═══════════════════════════════════════════════════════════════════════════
# TC-01: 颜色变更 → VISUAL_ONLY
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestVisualOnlyDetection:
    """颜色/材质/装饰类变更应当识别为 VISUAL_ONLY。"""

    def test_tc01_color_change(self):
        """TC-01: 颜色变更 → VISUAL_ONLY"""
        intent = detect_change_intent("把墙壁换成米白色，更温馨一些")
        assert intent == ChangeIntentType.VISUAL_ONLY

    def test_tc02_material_change(self):
        """TC-02: 材质变更 → VISUAL_ONLY"""
        intent = detect_change_intent("地板改用橡木实木，墙面换成哑光涂料")
        assert intent == ChangeIntentType.VISUAL_ONLY

    def test_tc03_decoration_change(self):
        """TC-03: 装饰变更 → VISUAL_ONLY"""
        intent = detect_change_intent("软装风格改为北欧简约，添加更多绿植装饰")
        assert intent == ChangeIntentType.VISUAL_ONLY

    def test_tc09_empty_text(self):
        """TC-09: 空文本 → VISUAL_ONLY（默认分支）"""
        assert detect_change_intent("") == ChangeIntentType.VISUAL_ONLY
        assert detect_change_intent("   ") == ChangeIntentType.VISUAL_ONLY

    def test_detailed_no_hit(self):
        """详细返回值：无命中时 source='none'，matched_keywords 为空集。"""
        result = detect_change_intent_detailed("换个颜色就好了")
        assert isinstance(result, DetectionResult)
        assert result.intent == ChangeIntentType.VISUAL_ONLY
        assert result.source == "none"
        assert len(result.matched_keywords) == 0


# ═══════════════════════════════════════════════════════════════════════════
# TC-04 / TC-05: 空间类型变更 → SPATIAL_ZONE
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestSpatialZoneDetection:
    """空间类型/功能区划变更应当识别为 SPATIAL_ZONE。"""

    def test_tc04_room_type_change(self):
        """TC-04: 空间类型变更（客厅→卧室）→ SPATIAL_ZONE"""
        intent = detect_change_intent("把客厅改成卧室，增加一间卧室")
        assert intent == ChangeIntentType.SPATIAL_ZONE

    def test_tc05_open_plan_change(self):
        """TC-05: 开放式格局变更（打通）→ SPATIAL_ZONE"""
        intent = detect_change_intent("客餐厅打通，做成开放式")
        assert intent == ChangeIntentType.SPATIAL_ZONE

    def test_spatial_study_room(self):
        """书房关键词 → SPATIAL_ZONE"""
        intent = detect_change_intent("需要一间独立书房给孩子学习用")
        assert intent == ChangeIntentType.SPATIAL_ZONE

    def test_spatial_detailed_result(self):
        """详细返回值：空间词命中时 source='spatial'，matched_keywords 非空。"""
        result = detect_change_intent_detailed("把阳台改造成花园")
        assert result.intent == ChangeIntentType.SPATIAL_ZONE
        assert result.source == "spatial"
        assert len(result.matched_keywords) > 0
        assert "阳台" in result.matched_keywords


# ═══════════════════════════════════════════════════════════════════════════
# TC-06 / TC-07: 身份/生活方式变更 → IDENTITY_PATTERN
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestIdentityPatternDetection:
    """居住身份/生活方式变更应当识别为 IDENTITY_PATTERN（最高优先级）。"""

    def test_tc06_lifestyle_change_elderly(self):
        """TC-06: 身份变更（养老）→ IDENTITY_PATTERN"""
        intent = detect_change_intent("父母要来同住，需要考虑养老需求和无障碍设计")
        assert intent == ChangeIntentType.IDENTITY_PATTERN

    def test_tc07_lifestyle_gaming(self):
        """TC-07: 生活方式变更（电竞）→ IDENTITY_PATTERN"""
        intent = detect_change_intent("我是电竞主播，需要专业的直播区域")
        assert intent == ChangeIntentType.IDENTITY_PATTERN

    def test_identity_single_living(self):
        """独居关键词 → IDENTITY_PATTERN"""
        intent = detect_change_intent("我是独居女性，安全性要放在第一位")
        assert intent == ChangeIntentType.IDENTITY_PATTERN

    def test_identity_pet_owner(self):
        """宠物关键词 → IDENTITY_PATTERN"""
        intent = detect_change_intent("家里有两只猫咪，需要专门的宠物区域")
        assert intent == ChangeIntentType.IDENTITY_PATTERN

    def test_identity_detailed_result(self):
        """详细返回值：身份词命中时 source='identity'。"""
        result = detect_change_intent_detailed("远程办公需求增加了，需要一个安静的工作空间")
        assert result.intent == ChangeIntentType.IDENTITY_PATTERN
        assert result.source == "identity"


# ═══════════════════════════════════════════════════════════════════════════
# TC-08 / TC-10: 优先级规则验证
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPriorityRules:
    """当多类关键词同时出现时，身份词优先于空间词，空间词优先于无命中。"""

    def test_tc08_identity_over_spatial(self):
        """TC-08: 混合文本（身份词 + 空间词）→ IDENTITY_PATTERN（优先级更高）"""
        intent = detect_change_intent("想把客厅改成电竞直播区域")
        assert intent == ChangeIntentType.IDENTITY_PATTERN

    def test_tc10_identity_beats_spatial(self):
        """TC-10: 空间词 + 身份词共存 → IDENTITY_PATTERN"""
        intent = detect_change_intent("独居老人居住，需要改造卧室和卫生间为无障碍设计")
        assert intent == ChangeIntentType.IDENTITY_PATTERN

    def test_spatial_beats_no_keywords(self):
        """空间词优先于无命中 → SPATIAL_ZONE（而不是 VISUAL_ONLY）"""
        intent = detect_change_intent("书房的灯光颜色稍微调整一下")
        # 书房是空间词，即使出现"颜色"这样的视觉词，空间词优先
        assert intent == ChangeIntentType.SPATIAL_ZONE

    def test_visual_fallback_no_structural_keywords(self):
        """纯视觉描述（无空间词和身份词）→ VISUAL_ONLY"""
        intent = detect_change_intent("整体配色改成莫兰迪色系，更高级一些")
        assert intent == ChangeIntentType.VISUAL_ONLY


# ═══════════════════════════════════════════════════════════════════════════
# 性能测试: 热路径延迟 < 5ms
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPerformance:
    """路由热路径延迟不得超过 5ms（MT-5 验收标准）。"""

    def test_latency_under_5ms(self):
        """单次调用延迟 < 5ms（缓存预热后）。"""
        # 预热缓存
        detect_change_intent("预热调用")

        iterations = 100
        test_texts = [
            "把客厅改成卧室",
            "颜色换成米白色",
            "我是电竞主播需要直播区",
            "地板换成实木",
            "",
        ]

        start = time.perf_counter()
        for _ in range(iterations):
            for text in test_texts:
                detect_change_intent(text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        per_call_ms = elapsed_ms / (iterations * len(test_texts))
        assert per_call_ms < 5.0, (
            f"单次调用延迟 {per_call_ms:.3f}ms 超过 5ms 限制。" f"（{iterations * len(test_texts)} 次调用总耗时 {elapsed_ms:.1f}ms）"
        )
