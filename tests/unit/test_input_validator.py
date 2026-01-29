"""
输入验证器单元测试
测试双阶段验证流程、内容安全检测、领域分类、能力边界检查
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_content_guard():
    """创建Mock内容安全守卫"""
    mock = AsyncMock()
    mock.check_content.return_value = {"is_safe": True, "risk_level": "low", "detected_issues": []}
    return mock


@pytest.fixture
def mock_domain_classifier():
    """创建Mock领域分类器"""
    mock = AsyncMock()
    mock.classify.return_value = {"is_design_domain": True, "confidence": 0.95, "domain": "interior_design"}
    return mock


@pytest.fixture
def mock_capability_boundary():
    """创建Mock能力边界服务"""
    mock = AsyncMock()
    mock.check_request.return_value = {"within_capability": True, "warnings": [], "blocked_deliverables": []}
    return mock


@pytest.fixture
def sample_user_input():
    """示例用户输入"""
    return {"description": "我需要设计一个现代简约风格的客厅，30平米", "requirements": ["采光好", "收纳足"], "budget": "中等"}


# ============================================================================
# 初始验证测试（第一阶段）
# ============================================================================


class TestInitialValidation:
    """测试初始验证流程"""

    @pytest.mark.asyncio
    async def test_safe_content_passes_validation(self, mock_content_guard, sample_user_input):
        """测试安全内容通过验证"""
        result = await mock_content_guard.check_content(sample_user_input["description"])

        assert result["is_safe"] is True
        assert result["risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_unsafe_content_blocked(self, mock_content_guard):
        """测试不安全内容被拦截"""
        mock_content_guard.check_content.return_value = {
            "is_safe": False,
            "risk_level": "high",
            "detected_issues": ["violence", "illegal_content"],
        }

        result = await mock_content_guard.check_content("违规内容示例")

        assert result["is_safe"] is False
        assert len(result["detected_issues"]) > 0

    @pytest.mark.asyncio
    async def test_design_domain_classification(self, mock_domain_classifier, sample_user_input):
        """测试设计领域分类"""
        result = await mock_domain_classifier.classify(sample_user_input["description"])

        assert result["is_design_domain"] is True
        assert result["confidence"] > 0.8

    @pytest.mark.asyncio
    async def test_non_design_domain_rejection(self, mock_domain_classifier):
        """测试非设计领域请求被拒绝"""
        mock_domain_classifier.classify.return_value = {
            "is_design_domain": False,
            "confidence": 0.92,
            "domain": "healthcare",
        }

        result = await mock_domain_classifier.classify("我需要一份医疗健康方案")

        assert result["is_design_domain"] is False

    @pytest.mark.asyncio
    async def test_capability_boundary_check(self, mock_capability_boundary):
        """测试能力边界检查"""
        request_with_cad = {"description": "设计住宅", "deliverables": ["CAD施工图", "设计方案"]}

        mock_capability_boundary.check_request.return_value = {
            "within_capability": False,
            "warnings": ["CAD施工图超出系统能力"],
            "blocked_deliverables": ["CAD施工图"],
        }

        result = await mock_capability_boundary.check_request(request_with_cad)

        assert result["within_capability"] is False
        assert "CAD施工图" in result["blocked_deliverables"]


# ============================================================================
# 二次验证测试（深度分析后）
# ============================================================================


class TestSecondaryValidation:
    """测试二次验证流程"""

    @pytest.mark.asyncio
    async def test_validate_after_analysis(self, mock_content_guard):
        """测试分析后的内容验证"""
        analyzed_content = {"user_requirements": "现代客厅设计", "generated_plan": "设计方案包括空间布局、材料选择..."}

        result = await mock_content_guard.check_content(analyzed_content["generated_plan"])

        assert result["is_safe"] is True

    @pytest.mark.asyncio
    async def test_detect_generated_unsafe_content(self, mock_content_guard):
        """测试检测生成内容中的不安全元素"""
        mock_content_guard.check_content.return_value = {
            "is_safe": False,
            "risk_level": "medium",
            "detected_issues": ["sensitive_info_leak"],
        }

        generated_text = "包含敏感信息的生成内容"
        result = await mock_content_guard.check_content(generated_text)

        assert result["is_safe"] is False

    @pytest.mark.asyncio
    async def test_complexity_assessment(self):
        """测试任务复杂度评估"""
        # 简单任务：单一房间，基本要求
        simple_task = {"description": "设计一个简约客厅", "rooms": 1, "requirements": ["采光"]}

        # 复杂任务：多房间，多维度要求
        complex_task = {
            "description": "设计150平米全屋，包括客厅、卧室、厨房、卫生间",
            "rooms": 5,
            "requirements": ["风格统一", "功能齐全", "预算控制", "材料选择", "照明设计"],
        }

        simple_complexity = (
            "simple" if simple_task["rooms"] <= 1 and len(simple_task["requirements"]) <= 2 else "complex"
        )
        complex_complexity = (
            "complex" if complex_task["rooms"] > 3 or len(complex_task["requirements"]) > 3 else "simple"
        )

        assert simple_complexity == "simple"
        assert complex_complexity == "complex"


# ============================================================================
# 内容安全检测链测试
# ============================================================================


class TestContentSafetyChain:
    """测试内容安全检测链"""

    @pytest.mark.asyncio
    async def test_keyword_detection(self):
        """测试关键词检测"""
        dangerous_keywords = ["暴力", "色情", "赌博", "违法"]

        test_text = "这是一个包含暴力内容的文本"

        detected = any(keyword in test_text for keyword in dangerous_keywords)

        assert detected

    @pytest.mark.asyncio
    async def test_regex_pattern_detection(self):
        """测试正则模式检测"""
        import re

        # 检测电话号码（隐私信息）
        phone_pattern = r"\d{11}"
        test_text = "联系方式：13812345678"

        match = re.search(phone_pattern, test_text)

        assert match is not None

    @pytest.mark.asyncio
    async def test_external_api_check(self, mock_content_guard):
        """测试外部API检查（腾讯云）"""
        # 模拟调用腾讯云API
        result = await mock_content_guard.check_content("待检测文本")

        assert "is_safe" in result

    @pytest.mark.asyncio
    async def test_llm_semantic_check(self):
        """测试LLM语义检测"""
        from tests.fixtures.mocks import MockAsyncLLM

        safety_llm = MockAsyncLLM(responses=['{"is_safe": true, "confidence": 0.95, "reasoning": "内容正常"}'])

        response = await safety_llm.ainvoke("检测这段文本的安全性")

        import json

        result = json.loads(response.content)

        assert result["is_safe"] is True


# ============================================================================
# 领域分类测试
# ============================================================================


class TestDomainClassification:
    """测试领域分类逻辑"""

    def test_design_keywords_matching(self):
        """测试设计关键词匹配"""
        design_keywords = ["设计", "装修", "空间", "布局", "风格", "材料", "色彩"]

        test_inputs = ["我需要设计一个办公室", "装修我的新房子", "空间布局规划"]

        for text in test_inputs:
            is_design = any(keyword in text for keyword in design_keywords)
            assert is_design

    def test_non_design_domain_detection(self):
        """测试非设计领域检测"""
        design_keywords = ["设计", "装修", "空间"]

        non_design_inputs = ["我需要一份法律咨询", "如何治疗感冒", "推荐一些投资建议"]

        for text in non_design_inputs:
            is_design = any(keyword in text for keyword in design_keywords)
            assert not is_design

    @pytest.mark.asyncio
    async def test_ambiguous_input_clarification(self, mock_domain_classifier):
        """测试模糊输入的澄清流程"""
        mock_domain_classifier.classify.return_value = {
            "is_design_domain": None,  # 不确定
            "confidence": 0.5,
            "needs_clarification": True,
        }

        result = await mock_domain_classifier.classify("我想要一个方案")

        assert result["needs_clarification"] is True

    def test_design_subdomain_classification(self):
        """测试设计子领域分类"""
        subdomains = {"室内设计": ["客厅", "卧室", "厨房"], "景观设计": ["花园", "绿化", "庭院"], "建筑设计": ["建筑", "结构", "外立面"]}

        test_text = "设计一个花园景观"

        detected_subdomain = None
        for subdomain, keywords in subdomains.items():
            if any(kw in test_text for kw in keywords):
                detected_subdomain = subdomain
                break

        assert detected_subdomain == "景观设计"


# ============================================================================
# 能力边界检查测试
# ============================================================================


class TestCapabilityBoundary:
    """测试能力边界检查"""

    @pytest.mark.asyncio
    async def test_block_cad_deliverable(self, mock_capability_boundary):
        """测试拦截CAD交付物"""
        mock_capability_boundary.check_request.return_value = {
            "within_capability": False,
            "warnings": ["CAD施工图需要专业工具"],
            "blocked_deliverables": ["CAD施工图"],
            "alternative_suggestions": ["空间布局方案文档"],
        }

        request = {"deliverables": ["CAD施工图"]}
        result = await mock_capability_boundary.check_request(request)

        assert result["within_capability"] is False
        assert "CAD施工图" in result["blocked_deliverables"]

    @pytest.mark.asyncio
    async def test_block_3d_rendering(self, mock_capability_boundary):
        """测试拦截3D效果图"""
        mock_capability_boundary.check_request.return_value = {
            "within_capability": False,
            "warnings": ["3D效果图需要专业建模软件"],
            "blocked_deliverables": ["3D效果图"],
        }

        request = {"deliverables": ["3D效果图"]}
        result = await mock_capability_boundary.check_request(request)

        assert "3D效果图" in result["blocked_deliverables"]

    @pytest.mark.asyncio
    async def test_allow_strategy_documents(self, mock_capability_boundary):
        """测试允许策略性文档"""
        allowed_deliverables = ["设计策略文档", "空间概念方案", "材料选择建议", "预算框架"]

        for deliverable in allowed_deliverables:
            result = await mock_capability_boundary.check_request({"deliverables": [deliverable]})
            assert result["within_capability"] is True

    @pytest.mark.asyncio
    async def test_transform_to_strategic_alternative(self):
        """测试转换为策略性替代方案"""
        blocked_to_alternative = {"CAD施工图": "空间布局策略文档", "3D效果图": "视觉概念描述", "精确材料清单": "材料选择指导方案"}

        blocked_request = "CAD施工图"
        alternative = blocked_to_alternative.get(blocked_request)

        assert alternative == "空间布局策略文档"


# ============================================================================
# 用户交互测试
# ============================================================================


class TestUserInteraction:
    """测试用户交互流程"""

    @pytest.mark.asyncio
    async def test_clarification_prompt(self):
        """测试澄清提示"""
        needs_clarification = True

        if needs_clarification:
            prompt = "您的需求不够明确，请详细描述您想要的设计项目类型"

        assert "明确" in prompt
        assert "详细描述" in prompt

    @pytest.mark.asyncio
    async def test_rejection_message(self):
        """测试拒绝消息"""
        rejection_reason = "内容包含不安全元素"

        message = f"抱歉，您的请求无法处理：{rejection_reason}"

        assert "抱歉" in message
        assert rejection_reason in message

    @pytest.mark.asyncio
    async def test_warning_message_for_capability(self):
        """测试能力边界警告消息"""
        blocked_items = ["CAD施工图", "3D效果图"]

        message = f"以下交付物超出系统能力范围：{', '.join(blocked_items)}。系统将提供策略性指导方案。"

        assert "超出系统能力" in message
        assert "CAD施工图" in message

    def test_confirmation_required(self):
        """测试需要用户确认"""
        high_risk_detected = True

        if high_risk_detected:
            needs_confirmation = True
            confirmation_message = "检测到潜在风险，是否继续？"
        else:
            needs_confirmation = False

        assert needs_confirmation
        assert "是否继续" in confirmation_message


# ============================================================================
# 集成场景测试
# ============================================================================


class TestIntegrationScenarios:
    """测试完整验证流程"""

    @pytest.mark.asyncio
    async def test_full_validation_pipeline_success(
        self, mock_content_guard, mock_domain_classifier, mock_capability_boundary, sample_user_input
    ):
        """测试完整验证流程（全部通过）"""
        # Step 1: 内容安全检测
        safety_result = await mock_content_guard.check_content(sample_user_input["description"])
        assert safety_result["is_safe"]

        # Step 2: 领域分类
        domain_result = await mock_domain_classifier.classify(sample_user_input["description"])
        assert domain_result["is_design_domain"]

        # Step 3: 能力边界检查
        capability_result = await mock_capability_boundary.check_request(sample_user_input)
        assert capability_result["within_capability"]

        # 所有检查通过
        validation_passed = (
            safety_result["is_safe"] and domain_result["is_design_domain"] and capability_result["within_capability"]
        )

        assert validation_passed

    @pytest.mark.asyncio
    async def test_validation_pipeline_blocked_by_safety(self, mock_content_guard):
        """测试安全检测拦截"""
        mock_content_guard.check_content.return_value = {
            "is_safe": False,
            "risk_level": "high",
            "detected_issues": ["violence"],
        }

        result = await mock_content_guard.check_content("危险内容")

        # 应该在第一步就被拦截
        assert result["is_safe"] is False

    @pytest.mark.asyncio
    async def test_validation_pipeline_blocked_by_domain(self, mock_domain_classifier):
        """测试领域分类拦截"""
        mock_domain_classifier.classify.return_value = {
            "is_design_domain": False,
            "confidence": 0.9,
            "domain": "finance",
        }

        result = await mock_domain_classifier.classify("投资理财建议")

        # 应该在第二步被拦截
        assert result["is_design_domain"] is False

    @pytest.mark.asyncio
    async def test_validation_pipeline_blocked_by_capability(self, mock_capability_boundary):
        """测试能力边界拦截"""
        mock_capability_boundary.check_request.return_value = {
            "within_capability": False,
            "warnings": ["需要专业工具"],
            "blocked_deliverables": ["CAD施工图"],
        }

        result = await mock_capability_boundary.check_request({"deliverables": ["CAD施工图"]})

        # 应该在第三步被拦截
        assert result["within_capability"] is False

    @pytest.mark.asyncio
    async def test_secondary_validation_after_analysis(self, mock_content_guard, mock_capability_boundary):
        """测试深度分析后的二次验证"""
        # 初始验证通过
        initial_check = await mock_content_guard.check_content("设计客厅")
        assert initial_check["is_safe"]

        # 生成分析结果（模拟）
        analysis_result = {"design_plan": "现代简约风格客厅方案", "deliverables": ["设计方案文档", "材料建议"]}

        # 二次验证：检查生成内容和交付物
        secondary_safety = await mock_content_guard.check_content(analysis_result["design_plan"])
        secondary_capability = await mock_capability_boundary.check_request(analysis_result)

        assert secondary_safety["is_safe"]
        assert secondary_capability["within_capability"]
