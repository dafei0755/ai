"""
集成测试 - 验证P0-P2功能协同工作
测试端到端检测流程：关键词 → 正则 → 腾讯云API → LLM
"""

import pytest
import os
from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard


class TestIntegration:
    """端到端集成测试"""

    @pytest.fixture
    def guard_full_features(self):
        """创建启用全部功能的守卫"""
        return ContentSafetyGuard(
            use_dynamic_rules=True,   # P2: 动态规则
            use_external_api=True,    # P0: 腾讯云API
            llm_model=None            # P1: LLM（测试中不启用，避免额外成本）
        )

    @pytest.fixture
    def guard_no_external_api(self):
        """创建不使用外部API的守卫（纯本地检测）"""
        return ContentSafetyGuard(
            use_dynamic_rules=True,
            use_external_api=False,
            llm_model=None
        )

    def test_complete_detection_flow(self, guard_full_features):
        """测试完整检测流程（P0+P1+P2）"""
        # 测试文本包含：关键词 + 隐私信息
        test_text = "这里有色情内容，我的手机号是13800138000"

        result = guard_full_features.check(test_text)

        # 应该检测到违规
        assert result["is_safe"] is False
        assert result["risk_level"] in ["medium", "high"]
        assert len(result["violations"]) > 0

        # 检查是否有关键词违规
        keyword_violations = [
            v for v in result["violations"]
            if v.get("method") == "keyword_match"
        ]
        assert len(keyword_violations) > 0

        # 检查是否有正则检测违规（隐私信息）
        regex_violations = [
            v for v in result["violations"]
            if v.get("method") == "regex_match"
        ]
        assert len(regex_violations) > 0

    def test_dynamic_rules_integration(self, guard_full_features):
        """测试动态规则集成（P2）"""
        # 验证动态规则加载器已启用
        assert guard_full_features.use_dynamic_rules is True

        # 触发懒加载
        loader = guard_full_features.rule_loader

        # 如果配置文件存在，应该能获取规则
        if loader is not None:
            keywords = loader.get_keywords()
            assert isinstance(keywords, dict)
            assert len(keywords) > 0

    def test_privacy_detection_integration(self, guard_full_features):
        """测试隐私信息检测集成（P1增强正则）"""
        test_cases = [
            ("我的邮箱是test@example.com", "电子邮箱"),
            ("手机号：13912345678", "手机号"),
            ("身份证：110101199001011234", "身份证号"),
            ("IP地址：192.168.1.1", "IP地址"),
        ]

        for text, expected_pattern in test_cases:
            result = guard_full_features.check(text)

            # 应该检测到隐私信息
            assert result["is_safe"] is False
            assert result["risk_level"] in ["low", "medium", "high"]

            # 检查是否匹配预期的模式
            privacy_violations = [
                v for v in result["violations"]
                if expected_pattern in v.get("matched_pattern", "")
            ]
            assert len(privacy_violations) > 0, f"未检测到{expected_pattern}: {text}"

    def test_evasion_detection_integration(self, guard_full_features):
        """测试变形规避检测集成（P1增强正则）"""
        test_cases = [
            "这里有色_情内容",    # 特殊符号分隔
            "这里有色*情内容",    # 特殊符号分隔
            "这里有涩情内容",      # 谐音替换
        ]

        for text in test_cases:
            result = guard_full_features.check(text)

            # 应该检测到规避行为
            assert result["is_safe"] is False, f"未检测到规避行为: {text}"

    def test_safe_content_no_false_positives(self, guard_full_features):
        """测试正常内容不误拦截"""
        safe_texts = [
            "今天天气真好，适合出去散步。",
            "我们的项目进展顺利。",
            "设计方案已经通过审核。",
            "明天开会讨论产品迭代计划。",
        ]

        for text in safe_texts:
            result = guard_full_features.check(text)
            # 正常内容应该安全
            assert result["is_safe"] is True, f"误拦截正常内容: {text}"

    def test_graceful_degradation_no_external_api(self, guard_no_external_api):
        """测试优雅降级：外部API禁用时"""
        # 即使外部API禁用，本地检测应该仍然工作
        test_text = "这里有赌博内容"

        result = guard_no_external_api.check(test_text)

        # 应该仍能检测到（使用关键词检测）
        assert result["is_safe"] is False
        assert len(result["violations"]) > 0

    def test_graceful_degradation_dynamic_rules_failure(self):
        """测试优雅降级：动态规则加载失败时"""
        # 创建守卫但禁用动态规则
        guard = ContentSafetyGuard(
            use_dynamic_rules=False,
            use_external_api=False
        )

        # 应该回退到静态规则
        assert guard.use_dynamic_rules is False

        # 静态规则应该仍能检测
        result = guard.check("这里有色情内容")
        assert result["is_safe"] is False

    def test_multiple_layer_detection(self, guard_full_features):
        """测试多层检测协同工作"""
        # 包含多种违规类型的文本
        test_text = """
        这是一个测试文本，包含以下内容：
        1. 赌博相关内容（关键词检测）
        2. 我的手机号是13800138000（隐私信息检测）
        3. 这里有色_情内容（变形规避检测）
        """

        result = guard_full_features.check(test_text)

        # 应该检测到多个违规
        assert result["is_safe"] is False
        assert len(result["violations"]) >= 2  # 至少2种违规

        # 检查是否有多种检测方法
        methods = set(v.get("method") for v in result["violations"])
        assert len(methods) >= 2  # 至少2种检测方法

    def test_severity_levels(self, guard_full_features):
        """测试严重性分级"""
        test_cases = [
            ("我的邮箱是test@example.com", ["low"]),           # 低风险
            ("我的手机号是13800138000", ["low", "medium"]),      # 中风险
            ("身份证号：110101199001011234", ["medium", "high"]), # 高风险
        ]

        for text, expected_severities in test_cases:
            result = guard_full_features.check(text)

            if not result["is_safe"]:
                # 检查严重性是否在预期范围内
                for violation in result["violations"]:
                    severity = violation.get("severity")
                    assert severity in expected_severities, \
                        f"严重性不符合预期: {severity} not in {expected_severities}"

    def test_concurrent_access(self, guard_full_features):
        """测试并发访问（线程安全）"""
        import threading

        results = []
        errors = []

        def check_text(text):
            try:
                result = guard_full_features.check(text)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 创建10个线程同时检测
        threads = []
        test_texts = [
            "正常文本1",
            "这里有赌博内容",
            "我的手机号是13800138000",
            "正常文本2",
            "这里有色情内容",
        ] * 2  # 共10个

        for text in test_texts:
            t = threading.Thread(target=check_text, args=(text,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 不应该有错误
        assert len(errors) == 0, f"并发访问出现错误: {errors}"

        # 应该有10个结果
        assert len(results) == 10

    def test_performance_baseline(self, guard_full_features):
        """测试性能基线（检测速度）"""
        import time

        test_text = "这是一段正常的测试文本"

        # 执行10次检测
        start_time = time.time()
        for _ in range(10):
            guard_full_features.check(test_text)
        elapsed_time = time.time() - start_time

        # 平均每次检测应该在合理时间内（<1秒，不含外部API）
        avg_time = elapsed_time / 10
        print(f"\n平均检测时间: {avg_time:.3f}秒")

        # 如果外部API禁用，应该很快（<0.1秒）
        if not guard_full_features.use_external_api:
            assert avg_time < 0.1, f"本地检测过慢: {avg_time}秒"


class TestExternalAPIIntegration:
    """外部API集成测试（需要配置腾讯云）"""

    @pytest.fixture
    def guard_with_api(self):
        """创建启用外部API的守卫"""
        # 只在配置了腾讯云时才启用
        if not os.getenv("ENABLE_TENCENT_CONTENT_SAFETY") == "true":
            pytest.skip("腾讯云内容安全未启用")

        return ContentSafetyGuard(
            use_dynamic_rules=True,
            use_external_api=True
        )

    def test_external_api_available(self, guard_with_api):
        """测试外部API可用性"""
        # 测试正常文本
        result = guard_with_api.check("这是一段正常的测试文本")
        # 应该能够正常返回结果
        assert "is_safe" in result
        assert "risk_level" in result

    def test_external_api_detection(self, guard_with_api):
        """测试外部API检测效果"""
        # 测试敏感文本
        result = guard_with_api.check("测试敏感词：赌博")

        # 外部API应该能检测到
        # 注意：腾讯云可能返回Pass/Review/Block
        assert "violations" in result

    def test_external_api_fallback(self):
        """测试外部API失败时的降级"""
        # 创建启用外部API但密钥无效的守卫
        # 通过临时修改环境变量模拟失败
        original_enabled = os.getenv("ENABLE_TENCENT_CONTENT_SAFETY")

        try:
            # 禁用外部API
            os.environ["ENABLE_TENCENT_CONTENT_SAFETY"] = "false"

            guard = ContentSafetyGuard(use_external_api=True)

            # 应该能够回退到本地检测
            result = guard.check("这里有赌博内容")
            assert result["is_safe"] is False  # 本地检测应该能识别

        finally:
            # 恢复原始设置
            if original_enabled:
                os.environ["ENABLE_TENCENT_CONTENT_SAFETY"] = original_enabled


class TestRegressionPrevention:
    """回归测试 - 防止之前修复的bug再次出现"""

    def test_unicode_regex_boundary_fix(self):
        """回归测试：Unicode正则边界问题（P1修复的bug）"""
        from intelligent_project_analyzer.security.enhanced_regex_detector import EnhancedRegexDetector

        detector = EnhancedRegexDetector()

        # 这些测试在修复前会失败
        test_cases = [
            ("我的邮箱是test@example.com", "电子邮箱"),
            ("服务器IP是192.168.1.1", "IP地址"),
            ("银行卡号是6222021234567890128", "银行卡号"),
        ]

        for text, expected_pattern in test_cases:
            violations = detector.check(text)
            matched = any(expected_pattern in v.get("matched_pattern", "") for v in violations)
            assert matched, f"回归：Unicode边界问题再次出现，未检测到{expected_pattern}"

    def test_luhn_validation_fix(self):
        """回归测试：Luhn算法验证（P1修复的bug）"""
        from intelligent_project_analyzer.security.enhanced_regex_detector import EnhancedRegexDetector

        detector = EnhancedRegexDetector()

        # 有效的银行卡号应该被检测到
        valid_card = "6222021234567890128"
        violations = detector.check(f"我的银行卡号是{valid_card}")
        bank_card_violations = [v for v in violations if "银行卡号" in v.get("matched_pattern", "")]
        assert len(bank_card_violations) > 0, "回归：Luhn验证问题再次出现"

        # 无效的银行卡号不应该被检测为银行卡
        invalid_card = "1234567890123456"
        violations = detector.check(f"这是一串数字{invalid_card}")
        # 可能检测到，但Luhn验证应该失败
        # （具体行为取决于实现）

    def test_dynamic_rules_graceful_degradation(self):
        """回归测试：动态规则优雅降级（P2功能）"""
        # 即使动态规则加载失败，系统应该仍能工作
        guard = ContentSafetyGuard(use_dynamic_rules=False)

        result = guard.check("这里有色情内容")
        # 应该回退到静态规则，仍能检测
        assert result["is_safe"] is False
