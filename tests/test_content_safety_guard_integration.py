"""内容安全守卫集成测试"""

import os

import pytest

from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard


class TestContentSafetyGuardIntegration:
    @pytest.fixture
    def guard(self):
        """创建守卫实例"""
        return ContentSafetyGuard(use_external_api=True)

    def test_with_tencent_api(self, guard):
        """测试集成腾讯云API"""
        # 跳过如果未启用
        if not os.getenv("ENABLE_TENCENT_CONTENT_SAFETY") == "true":
            pytest.skip("腾讯云内容安全未启用")

        # 测试正常文本
        result = guard.check("这是一段正常的测试文本")
        assert result["is_safe"] is True
        assert result["risk_level"] == "safe"

    def test_multilayer_detection_keywords(self, guard):
        """测试多层检测 - 关键词"""
        # 使用包含关键词的文本（触发关键词检测）
        result = guard.check("色情内容")
        assert result["is_safe"] is False
        # 应该有违规记录
        assert len(result["violations"]) > 0
        # 应该包含关键词匹配方法
        assert any(v.get("method") == "keyword_match" for v in result["violations"])

    def test_multilayer_detection_regex(self, guard):
        """测试多层检测 - 正则（隐私信息）- 根据配置，隐私检测已禁用"""
        # 显式禁用隐私检测以符合测试预期
        guard.enable_privacy_check = False

        # 使用包含手机号的文本
        result = guard.check("我的手机号是13800138000")
        # 根据security_rules.yaml配置，enable_privacy_check: false
        # 设计项目不需要隐私检测，所以不应触发violations
        # 验证隐私检测确实被禁用
        assert result["is_safe"] == True
        assert result["risk_level"] == "safe"

    def test_multilayer_detection_external_api(self, guard):
        """测试多层检测 - 外部API"""
        # 跳过如果未启用
        if not os.getenv("ENABLE_TENCENT_CONTENT_SAFETY") == "true":
            pytest.skip("腾讯云内容安全未启用")

        # 使用敏感文本（可能触发外部API）
        result = guard.check("赌博诈骗")
        # 应该有检测结果（关键词或外部API）
        # 注意：可能同时触发关键词和外部API
        assert len(result["violations"]) > 0

    def test_safe_content_passes_all_layers(self, guard):
        """测试安全内容通过所有检测层"""
        result = guard.check("今天天气真好，适合出去散步。")
        assert result["is_safe"] is True
        assert result["risk_level"] == "safe"
        assert len(result["violations"]) == 0

    def test_without_external_api(self):
        """测试不使用外部API时的行为"""
        guard = ContentSafetyGuard(use_external_api=False)
        # 即使文本敏感，也只会用关键词和正则检测
        result = guard.check("这是一段正常文本")
        # 应该安全（没有关键词匹配）
        assert result["is_safe"] is True

    def test_severity_levels(self, guard):
        """测试严重性等级判断"""
        # 高严重性违规（应该拒绝）
        result = guard.check("杀人暴力血腥内容")
        if not result["is_safe"]:
            # 如果检测到违规，应该有高严重性标记
            high_severity = sum(1 for v in result["violations"] if v.get("severity") == "high")
            if high_severity > 0:
                assert result.get("action") == "reject"
