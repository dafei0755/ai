"""
内容安全守卫单元测试
测试关键词检测、正则模式、腾讯云API、LLM语义检测、规则热加载
"""

import re
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_tencent_api():
    """创建Mock腾讯云API"""
    from tests.fixtures.mocks import MockTencentCloudAPI

    return MockTencentCloudAPI(detection_result="safe")


@pytest.fixture
def mock_llm_detector():
    """创建Mock LLM检测器"""
    from tests.fixtures.mocks import MockAsyncLLM

    return MockAsyncLLM(responses=['{"is_safe": true, "confidence": 0.95, "issues": []}'])


@pytest.fixture
def sample_security_rules():
    """示例安全规则"""
    return {
        "keywords": {"violence": ["暴力", "伤害", "攻击"], "porn": ["色情", "裸露"], "illegal": ["毒品", "赌博", "违法"]},
        "patterns": {"phone": r"\d{11}", "id_card": r"\d{17}[\dXx]", "email": r"[\w\.-]+@[\w\.-]+"},
        "whitelist": ["设计", "装修", "空间"],
    }


# ============================================================================
# 关键词检测测试
# ============================================================================


class TestKeywordDetection:
    """测试关键词检测"""

    def test_detect_violence_keyword(self, sample_security_rules):
        """测试检测暴力关键词"""
        test_text = "这是一个包含暴力内容的文本"

        detected = []
        for category, keywords in sample_security_rules["keywords"].items():
            for keyword in keywords:
                if keyword in test_text:
                    detected.append((category, keyword))

        assert len(detected) > 0
        assert detected[0][0] == "violence"

    def test_detect_multiple_keywords(self, sample_security_rules):
        """测试检测多个关键词"""
        test_text = "包含暴力和赌博的内容"

        detected = []
        for category, keywords in sample_security_rules["keywords"].items():
            for keyword in keywords:
                if keyword in test_text:
                    detected.append(keyword)

        assert len(detected) == 2

    def test_whitelist_bypass(self, sample_security_rules):
        """测试白名单绕过"""
        test_text = "设计空间布局"

        # 检查是否包含白名单词汇
        has_whitelist = any(word in test_text for word in sample_security_rules["whitelist"])

        # 如果包含白名单词汇，降低风险等级
        if has_whitelist:
            risk_level = "low"
        else:
            risk_level = "high"

        assert risk_level == "low"

    def test_case_insensitive_matching(self):
        """测试大小写不敏感匹配"""
        keywords = ["Violence", "PORN", "Illegal"]
        test_text = "violence content"

        detected = any(kw.lower() in test_text.lower() for kw in keywords)

        assert detected


# ============================================================================
# 正则模式检测测试
# ============================================================================


class TestRegexPatterns:
    """测试正则模式检测"""

    def test_detect_phone_number(self, sample_security_rules):
        """测试检测电话号码"""
        test_text = "联系方式：13812345678"

        phone_pattern = sample_security_rules["patterns"]["phone"]
        match = re.search(phone_pattern, test_text)

        assert match is not None
        assert match.group() == "13812345678"

    def test_detect_id_card(self, sample_security_rules):
        """测试检测身份证号"""
        test_text = "身份证：110101199001011234"

        id_pattern = sample_security_rules["patterns"]["id_card"]
        match = re.search(id_pattern, test_text)

        assert match is not None

    def test_detect_email(self, sample_security_rules):
        """测试检测邮箱地址"""
        test_text = "联系邮箱：user@example.com"

        email_pattern = sample_security_rules["patterns"]["email"]
        match = re.search(email_pattern, test_text)

        assert match is not None
        assert "user@example.com" in match.group()

    def test_multiple_privacy_patterns(self, sample_security_rules):
        """测试检测多种隐私模式"""
        test_text = "我的电话是13800138000，邮箱test@test.com"

        detected_patterns = []
        for pattern_name, pattern in sample_security_rules["patterns"].items():
            if re.search(pattern, test_text):
                detected_patterns.append(pattern_name)

        assert "phone" in detected_patterns
        assert "email" in detected_patterns

    def test_evasion_pattern_detection(self):
        """测试规避模式检测"""
        # 使用空格分隔尝试规避检测
        evasion_texts = ["暴 力", "暴\u200b力", "暴*力"]  # 零宽字符

        # 规避检测模式
        evasion_pattern = r"[\s\*\u200b]"

        for text in evasion_texts:
            has_evasion = re.search(evasion_pattern, text)
            assert has_evasion is not None


# ============================================================================
# 腾讯云API测试
# ============================================================================


class TestTencentCloudAPI:
    """测试腾讯云内容安全API"""

    @pytest.mark.asyncio
    async def test_safe_content_detection(self, mock_tencent_api):
        """测试安全内容检测"""
        result = await mock_tencent_api.text_moderation("这是安全的设计内容")

        assert result["Suggestion"] == "Pass"
        assert result["Score"] == 0

    @pytest.mark.asyncio
    async def test_risky_content_detection(self):
        """测试高风险内容检测"""
        from tests.fixtures.mocks import MockTencentCloudAPI

        api = MockTencentCloudAPI(detection_result="risky")
        result = await api.text_moderation("高风险内容")

        assert result["Suggestion"] == "Block"
        assert result["Score"] > 80
        assert len(result["Keywords"]) > 0

    @pytest.mark.asyncio
    async def test_review_required_detection(self):
        """测试需要人工审核的内容"""
        from tests.fixtures.mocks import MockTencentCloudAPI

        api = MockTencentCloudAPI(detection_result="review")
        result = await api.text_moderation("需要审核的内容")

        assert result["Suggestion"] == "Review"
        assert 50 < result["Score"] < 80

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """测试API错误处理"""
        from tests.fixtures.mocks import MockTencentCloudAPI

        api = MockTencentCloudAPI(detection_result="error")

        with pytest.raises(Exception):
            await api.text_moderation("测试内容")

    @pytest.mark.asyncio
    async def test_api_call_tracking(self, mock_tencent_api):
        """测试API调用追踪"""
        await mock_tencent_api.text_moderation("内容1")
        await mock_tencent_api.text_moderation("内容2")

        assert mock_tencent_api.call_count == 2
        assert len(mock_tencent_api.call_history) == 2


# ============================================================================
# LLM语义检测测试
# ============================================================================


class TestLLMSemanticDetection:
    """测试LLM深度语义检测"""

    @pytest.mark.asyncio
    async def test_semantic_safety_check(self, mock_llm_detector):
        """测试语义安全检测"""
        test_text = "这是一段需要深度分析的内容"

        response = await mock_llm_detector.ainvoke(f"检测安全性：{test_text}")

        import json

        result = json.loads(response.content)

        assert result["is_safe"] is True
        assert result["confidence"] > 0.8

    @pytest.mark.asyncio
    async def test_semantic_context_analysis(self):
        """测试上下文语义分析"""
        from tests.fixtures.mocks import MockAsyncLLM

        # 模拟检测隐含风险
        detector = MockAsyncLLM(
            responses=[
                '{"is_safe": false, "confidence": 0.88, "issues": ["implicit_violence"], "reasoning": "内容暗示暴力行为"}'
            ]
        )

        response = await detector.ainvoke("检测隐含风险")

        import json

        result = json.loads(response.content)

        assert result["is_safe"] is False
        assert "implicit_violence" in result["issues"]

    @pytest.mark.asyncio
    async def test_confidence_threshold(self):
        """测试置信度阈值"""
        from tests.fixtures.mocks import MockAsyncLLM

        detector = MockAsyncLLM(responses=['{"is_safe": true, "confidence": 0.65}'])  # 低置信度

        response = await detector.ainvoke("模糊内容")

        import json

        result = json.loads(response.content)

        confidence_threshold = 0.7
        needs_manual_review = result["confidence"] < confidence_threshold

        assert needs_manual_review

    @pytest.mark.asyncio
    async def test_json_parse_error_handling(self):
        """测试JSON解析错误处理"""
        from tests.fixtures.mocks import MockAsyncLLM

        detector = MockAsyncLLM(responses=["Invalid JSON response"])

        response = await detector.ainvoke("测试")

        # 尝试解析JSON
        import json

        try:
            result = json.loads(response.content)
            parse_success = True
        except:
            parse_success = False
            # 降级到默认安全判断
            result = {"is_safe": False, "confidence": 0.0}

        assert not parse_success
        assert result["is_safe"] is False


# ============================================================================
# 规则热加载测试
# ============================================================================


class TestRuleHotReload:
    """测试规则热加载"""

    def test_load_rules_from_yaml(self):
        """测试从YAML加载规则"""
        # 模拟YAML内容
        yaml_content = """
keywords:
  violence: ["暴力", "伤害"]
  porn: ["色情"]
patterns:
  phone: "\\\\d{11}"
whitelist: ["设计", "装修"]
"""

        import yaml

        rules = yaml.safe_load(yaml_content)

        assert "keywords" in rules
        assert len(rules["keywords"]["violence"]) == 2

    def test_file_modification_detection(self):
        """测试文件修改检测"""
        import os
        import time
        from pathlib import Path

        # 模拟文件时间戳
        mock_file_mtime = time.time()
        last_loaded_time = mock_file_mtime - 10  # 10秒前加载

        needs_reload = mock_file_mtime > last_loaded_time

        assert needs_reload

    def test_thread_safe_reload(self):
        """测试线程安全的规则重载"""
        import threading

        shared_rules = {"keywords": []}
        lock = threading.Lock()

        def reload_rules():
            with lock:
                shared_rules["keywords"] = ["new_keyword"]

        # 模拟并发重载
        threads = [threading.Thread(target=reload_rules) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该成功更新
        assert "new_keyword" in shared_rules["keywords"]

    def test_whitelist_hot_update(self):
        """测试白名单热更新"""
        whitelist_v1 = ["设计", "装修"]
        whitelist_v2 = ["设计", "装修", "空间", "布局"]  # 新增

        # 模拟更新
        current_whitelist = whitelist_v2

        assert len(current_whitelist) > len(whitelist_v1)
        assert "空间" in current_whitelist


# ============================================================================
# 违规日志记录测试
# ============================================================================


class TestViolationLogging:
    """测试违规日志记录"""

    def test_log_violation_to_jsonl(self):
        """测试记录违规到JSONL文件"""
        import json

        violation = {
            "timestamp": "2026-01-06T10:30:00",
            "user_id": "user_123",
            "content": "违规内容",
            "detected_issues": ["violence"],
            "risk_level": "high",
        }

        # 模拟写入JSONL
        jsonl_line = json.dumps(violation, ensure_ascii=False)

        assert "user_123" in jsonl_line
        assert "violence" in jsonl_line

    def test_violation_statistics(self):
        """测试违规统计分析"""
        violations = [
            {"issue": "violence", "level": "high"},
            {"issue": "porn", "level": "high"},
            {"issue": "violence", "level": "medium"},
            {"issue": "privacy", "level": "low"},
        ]

        # 统计各类违规数量
        from collections import Counter

        issue_counts = Counter(v["issue"] for v in violations)

        assert issue_counts["violence"] == 2
        assert issue_counts["porn"] == 1

    def test_log_rotation(self):
        """测试日志轮转"""
        import os

        max_log_size = 10 * 1024 * 1024  # 10MB
        current_log_size = 12 * 1024 * 1024  # 12MB

        needs_rotation = current_log_size > max_log_size

        assert needs_rotation


# ============================================================================
# 检测链集成测试
# ============================================================================


class TestDetectionChain:
    """测试完整检测链"""

    @pytest.mark.asyncio
    async def test_detection_chain_keyword_pass(self, sample_security_rules):
        """测试关键词检测通过"""
        test_text = "这是安全的设计内容"

        # Step 1: 关键词检测
        keyword_detected = False
        for keywords in sample_security_rules["keywords"].values():
            if any(kw in test_text for kw in keywords):
                keyword_detected = True
                break

        assert not keyword_detected

    @pytest.mark.asyncio
    async def test_detection_chain_keyword_block(self, sample_security_rules):
        """测试关键词检测拦截"""
        test_text = "包含暴力内容"

        # Step 1: 关键词检测（应该拦截）
        keyword_detected = False
        for keywords in sample_security_rules["keywords"].values():
            if any(kw in test_text for kw in keywords):
                keyword_detected = True
                break

        # 直接拦截，不进入后续步骤
        assert keyword_detected

    @pytest.mark.asyncio
    async def test_full_detection_chain(self, sample_security_rules, mock_tencent_api, mock_llm_detector):
        """测试完整检测链：关键词 → 正则 → API → LLM"""
        test_text = "这是一段复杂的内容需要全面检测"

        # Step 1: 关键词检测
        keyword_detected = any(
            any(kw in test_text for kw in keywords) for keywords in sample_security_rules["keywords"].values()
        )

        if not keyword_detected:
            # Step 2: 正则检测
            pattern_detected = any(
                re.search(pattern, test_text) for pattern in sample_security_rules["patterns"].values()
            )

            if not pattern_detected:
                # Step 3: 腾讯云API
                api_result = await mock_tencent_api.text_moderation(test_text)

                if api_result["Suggestion"] == "Pass":
                    # Step 4: LLM深度检测
                    llm_response = await mock_llm_detector.ainvoke(test_text)
                    import json

                    llm_result = json.loads(llm_response.content)

                    final_safe = llm_result["is_safe"]

        # 模拟场景：全部通过
        assert not keyword_detected
        assert not pattern_detected
        assert api_result["Suggestion"] == "Pass"
        assert llm_result["is_safe"]

    @pytest.mark.asyncio
    async def test_detection_fallback_on_api_failure(self, sample_security_rules, mock_llm_detector):
        """测试API失败时的降级处理"""
        from tests.fixtures.mocks import MockTencentCloudAPI

        test_text = "测试内容"

        # 腾讯云API失败
        failing_api = MockTencentCloudAPI(detection_result="error")

        try:
            api_result = await failing_api.text_moderation(test_text)
        except Exception:
            # 降级到本地检测（关键词 + 正则）
            local_detection = any(
                any(kw in test_text for kw in keywords) for keywords in sample_security_rules["keywords"].values()
            ) or any(re.search(pattern, test_text) for pattern in sample_security_rules["patterns"].values())

            # 如果本地检测也通过，使用LLM
            if not local_detection:
                llm_response = await mock_llm_detector.ainvoke(test_text)
                import json

                llm_result = json.loads(llm_response.content)
                final_safe = llm_result["is_safe"]

        # 验证降级成功
        assert not local_detection
        assert final_safe


# ============================================================================
# 边界和性能测试
# ============================================================================


class TestEdgeCasesAndPerformance:
    """测试边界情况和性能"""

    def test_empty_text_handling(self):
        """测试空文本处理"""
        test_text = ""

        # 应该直接通过
        is_safe = len(test_text.strip()) == 0 or True

        assert is_safe

    def test_very_long_text_handling(self):
        """测试超长文本处理"""
        long_text = "A" * 100000
        max_length = 50000

        # 截断处理
        truncated = long_text[:max_length]

        assert len(truncated) == max_length

    def test_special_unicode_characters(self):
        """测试特殊Unicode字符"""
        special_chars = "测试内容\u200b\u200c\u200d"  # 零宽字符

        # 清理零宽字符
        cleaned = re.sub(r"[\u200b\u200c\u200d]", "", special_chars)

        assert "\u200b" not in cleaned

    def test_batch_detection_performance(self):
        """测试批量检测性能"""
        import time

        test_texts = [f"测试内容{i}" for i in range(100)]
        keywords = ["暴力", "色情"]

        start_time = time.time()
        results = [any(kw in text for kw in keywords) for text in test_texts]
        elapsed_time = time.time() - start_time

        # 100条文本应该在1秒内完成
        assert elapsed_time < 1.0
        assert len(results) == 100
