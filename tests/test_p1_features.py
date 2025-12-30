"""P1功能单元测试 - LLM语义检测和增强正则检测"""

import pytest
from intelligent_project_analyzer.security.llm_safety_detector import LLMSafetyDetector
from intelligent_project_analyzer.security.enhanced_regex_detector import EnhancedRegexDetector


class TestLLMSafetyDetector:
    """LLM语义安全检测器测试"""

    def test_detector_without_llm(self):
        """测试未配置LLM时的行为"""
        detector = LLMSafetyDetector(llm_model=None)
        result = detector.check("测试文本")
        assert result["is_safe"] is True
        assert result["confidence"] == 0.0

    def test_response_parsing(self):
        """测试响应解析"""
        detector = LLMSafetyDetector()

        # 测试标准JSON
        response = '{"is_safe": false, "confidence": 0.9, "violation": {"category": "色情低俗", "reason": "包含色情内容", "severity": "high"}}'
        result = detector._parse_response(response)
        assert result["is_safe"] is False
        assert result["confidence"] == 0.9
        assert result["violation"]["category"] == "色情低俗"

        # 测试markdown包裹的JSON
        response_md = '```json\n{"is_safe": true, "confidence": 1.0}\n```'
        result_md = detector._parse_response(response_md)
        assert result_md["is_safe"] is True
        assert result_md["confidence"] == 1.0

    def test_confidence_threshold(self):
        """测试置信度阈值"""
        # 低于阈值的结果应该被忽略
        detector = LLMSafetyDetector(confidence_threshold=0.8)

        # 模拟低置信度结果
        response = '{"is_safe": false, "confidence": 0.5, "violation": {"category": "测试", "severity": "low"}}'
        # 注意：实际测试需要mock LLM调用


class TestEnhancedRegexDetector:
    """增强正则检测器测试"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return EnhancedRegexDetector(
            enable_privacy_check=True,
            enable_evasion_check=True
        )

    def test_phone_number_detection(self, detector):
        """测试手机号检测"""
        text = "我的手机号是13800138000"
        violations = detector.check(text)
        assert len(violations) > 0
        assert any(v["matched_pattern"] == "手机号" for v in violations)

    def test_id_card_detection(self, detector):
        """测试身份证号检测"""
        text = "我的身份证号是110101199001011234"
        violations = detector.check(text)
        assert len(violations) > 0
        assert any(v["matched_pattern"] == "身份证号" for v in violations)

    def test_email_detection(self, detector):
        """测试邮箱检测"""
        text = "我的邮箱是test@example.com"
        violations = detector.check(text)
        assert len(violations) > 0
        assert any(v["matched_pattern"] == "电子邮箱" for v in violations)

    def test_bank_card_detection(self, detector):
        """测试银行卡号检测"""
        # 使用一个有效的测试银行卡号（通过Luhn算法验证）
        text = "我的银行卡号是6222021234567890128"
        violations = detector.check(text)
        # 银行卡检测会验证Luhn算法
        bank_card_violations = [v for v in violations if v["matched_pattern"] == "银行卡号"]
        # 有效卡号应该被检测到
        assert len(bank_card_violations) > 0

    def test_ip_address_detection(self, detector):
        """测试IP地址检测"""
        text = "服务器IP是192.168.1.1"
        violations = detector.check(text)
        assert len(violations) > 0
        assert any(v["matched_pattern"] == "IP地址(IPv4)" for v in violations)

    def test_license_plate_detection(self, detector):
        """测试车牌号检测"""
        text = "我的车牌号是京A12345"
        violations = detector.check(text)
        assert len(violations) > 0
        assert any(v["matched_pattern"] == "车牌号" for v in violations)

    def test_evasion_detection_special_chars(self, detector):
        """测试特殊符号分隔检测"""
        text = "色_情内容"
        violations = detector.check(text)
        evasion_violations = [v for v in violations if v["category"] == "变形规避"]
        assert len(evasion_violations) > 0

    def test_evasion_detection_homophone(self, detector):
        """测试谐音替换检测"""
        text = "涩情内容"
        violations = detector.check(text)
        homophone_violations = [v for v in violations if "谐音替换" in v["matched_pattern"]]
        assert len(homophone_violations) > 0

    def test_evasion_detection_letter_replacement(self, detector):
        """测试字母替换检测"""
        text = "这是sex内容"
        violations = detector.check(text)
        letter_violations = [v for v in violations if "字母拼音" in v["matched_pattern"]]
        assert len(letter_violations) > 0

    def test_sensitive_data_masking(self, detector):
        """测试敏感信息脱敏"""
        # 测试手机号脱敏
        masked = detector._mask_sensitive("13800138000", "手机号")
        assert "****" in masked
        assert masked.startswith("138")
        assert masked.endswith("8000")

        # 测试身份证号脱敏
        masked_id = detector._mask_sensitive("110101199001011234", "身份证号")
        assert "********" in masked_id
        assert masked_id.startswith("110101")
        assert masked_id.endswith("1234")

    def test_bank_card_luhn_validation(self, detector):
        """测试银行卡Luhn算法验证"""
        # 有效的测试卡号（通过Luhn算法验证）
        assert detector._is_valid_bank_card("6222021234567890128") is True

        # 无效的卡号
        assert detector._is_valid_bank_card("1234567890123456") is False

    def test_safe_content_no_violations(self, detector):
        """测试正常内容不触发检测"""
        text = "今天天气真好，适合出去散步。"
        violations = detector.check(text)
        assert len(violations) == 0

    def test_disable_privacy_check(self):
        """测试禁用隐私检测"""
        detector = EnhancedRegexDetector(
            enable_privacy_check=False,
            enable_evasion_check=True
        )
        text = "我的手机号是13800138000"
        violations = detector.check(text)
        # 不应检测到隐私信息
        privacy_violations = [v for v in violations if v["category"] == "隐私信息"]
        assert len(privacy_violations) == 0

    def test_disable_evasion_check(self):
        """测试禁用变形规避检测"""
        detector = EnhancedRegexDetector(
            enable_privacy_check=True,
            enable_evasion_check=False
        )
        text = "色_情内容"
        violations = detector.check(text)
        # 不应检测到变形规避
        evasion_violations = [v for v in violations if v["category"] == "变形规避"]
        assert len(evasion_violations) == 0

    def test_violation_stats(self, detector):
        """测试违规统计"""
        text = "我的手机号是13800138000，邮箱是test@example.com，这里有色_情内容"
        violations = detector.check(text)

        stats = detector.get_stats(violations)
        assert stats["total"] > 0
        assert stats["privacy_count"] > 0
        assert stats["evasion_count"] > 0
        assert "隐私信息" in stats["by_category"]
        assert "变形规避" in stats["by_category"]


class TestContentSafetyGuardP1Integration:
    """P1功能集成测试"""

    def test_enhanced_regex_integration(self):
        """测试增强正则检测集成"""
        from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard

        guard = ContentSafetyGuard()

        # 测试隐私信息检测
        result = guard.check("我的手机号是13800138000")
        assert result["is_safe"] is False
        assert any(v["category"] == "隐私信息" for v in result["violations"])

        # 测试变形规避检测
        result2 = guard.check("这里有色_情内容")
        assert result2["is_safe"] is False
        assert len(result2["violations"]) > 0

    def test_llm_integration_without_model(self):
        """测试LLM集成（无模型配置时）"""
        from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard

        guard = ContentSafetyGuard(llm_model=None)

        # LLM未配置，应该跳过LLM检测
        result = guard.check("这是一段测试文本")
        # 应该能正常运行，不会抛出异常

    def test_fallback_to_basic_regex(self):
        """测试回退到基础正则检测"""
        from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard

        guard = ContentSafetyGuard()

        # 即使增强检测失败，也应该能回退到基础检测
        result = guard._check_patterns_basic("我的手机号是13800138000")
        assert len(result) > 0
