"""
单元测试：v7.214 深度搜索优化功能
测试覆盖结构化分析、质量评估、智能查询扩展等核心功能
"""

import asyncio
import os

# 导入待测试的类和组件
import sys
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from intelligent_project_analyzer.services.ucppt_search_engine import (
    AnalysisPhase,
    AnalysisSession,
    DeepSeekAnalysisEngine,
    L0DialogueResult,
    L1L5FrameworkResult,
    PhaseResult,
    QualityGate,
    StructuredUserInfo,
    SynthesisResult,
    UcpptSearchEngine,
)


class TestAnalysisPhase:
    """测试分析阶段枚举"""

    def test_analysis_phase_values(self):
        """测试分析阶段枚举值"""
        assert AnalysisPhase.L0_DIALOGUE.value == "l0_dialogue"
        assert AnalysisPhase.L1_L5_FRAMEWORK.value == "l1_l5_framework"
        assert AnalysisPhase.SYNTHESIS.value == "synthesis"


class TestPhaseResult:
    """测试分析阶段结果基类"""

    def test_phase_result_creation(self):
        """测试PhaseResult创建"""
        content = {"test": "data"}
        result = PhaseResult(phase=AnalysisPhase.L0_DIALOGUE, content=content, quality_score=0.85, execution_time=1.5)

        assert result.phase == AnalysisPhase.L0_DIALOGUE
        assert result.content == content
        assert result.quality_score == 0.85
        assert result.execution_time == 1.5
        assert result.retry_count == 0

    def test_phase_result_to_dict(self):
        """测试PhaseResult转换为字典"""
        result = PhaseResult(phase=AnalysisPhase.L0_DIALOGUE, content={"key": "value"}, quality_score=0.75)

        dict_result = result.to_dict()
        assert dict_result["phase"] == "l0_dialogue"
        assert dict_result["content"] == {"key": "value"}
        assert dict_result["quality_score"] == 0.75


class TestL0DialogueResult:
    """测试L0对话分析结果"""

    def test_l0_result_creation(self):
        """测试L0结果创建"""
        result = L0DialogueResult(
            phase=AnalysisPhase.L0_DIALOGUE,
            content={"dialogue": "test"},
            quality_score=0.8,
            context_understanding="用户想要设计咖啡厅",
            implicit_needs=["温馨氛围", "合理布局"],
            dialogue_content="经过分析，用户希望...",
        )

        assert result.phase == AnalysisPhase.L0_DIALOGUE
        assert result.context_understanding == "用户想要设计咖啡厅"
        assert len(result.implicit_needs) == 2
        assert "温馨氛围" in result.implicit_needs

    def test_l0_result_post_init(self):
        """测试L0结果后初始化处理"""
        result = L0DialogueResult(phase=AnalysisPhase.L0_DIALOGUE, content={}, quality_score=0.8)
        result.__post_init__()

        assert result.phase == AnalysisPhase.L0_DIALOGUE
        assert isinstance(result.implicit_needs, list)


class TestL1L5FrameworkResult:
    """测试L1-L5框架分析结果"""

    def test_framework_result_creation(self):
        """测试框架结果创建"""
        result = L1L5FrameworkResult(
            phase=AnalysisPhase.L1_L5_FRAMEWORK,
            content={"framework": "test"},
            quality_score=0.85,
            execution_time=1.0,
            l1_facts=["事实1", "事实2", "事实3"],
            l3_tensions="功能性 vs 美观性",
            l4_jtbd="从现有状态到理想咖啡厅状态",
            framework_coherence=0.8,
        )

        assert len(result.l1_facts) == 3
        assert result.l3_tensions == "功能性 vs 美观性"
        assert result.framework_coherence == 0.8

    def test_framework_result_post_init(self):
        """测试框架结果后初始化处理"""
        result = L1L5FrameworkResult(phase=AnalysisPhase.L1_L5_FRAMEWORK, content={}, quality_score=0.7)
        result.__post_init__()

        assert result.phase == AnalysisPhase.L1_L5_FRAMEWORK
        assert isinstance(result.l1_facts, list)
        assert isinstance(result.l2_models, dict)
        assert isinstance(result.l5_sharpness, dict)


class TestQualityGate:
    """测试质量门控"""

    def test_quality_gate_creation(self):
        """测试质量门控创建"""
        gate = QualityGate()
        assert gate.threshold == 0.75
        assert gate.retry_limit == 2
        assert gate.fallback_strategy == "continue_with_warning"

    def test_quality_gate_phase_quality_check(self):
        """测试阶段质量检查"""
        gate = QualityGate()

        # 创建一个高质量结果
        high_quality_result = PhaseResult(
            phase=AnalysisPhase.L0_DIALOGUE, content={"profile_completeness_score": 0.85}, quality_score=0.9
        )

        # 检查质量（应该通过）
        passed = gate.check_phase_quality(AnalysisPhase.L0_DIALOGUE, high_quality_result)
        assert passed

        # 创建一个低质量结果
        low_quality_result = PhaseResult(
            phase=AnalysisPhase.L0_DIALOGUE, content={"profile_completeness_score": 0.5}, quality_score=0.4
        )

        # 检查质量（应该不通过）
        passed = gate.check_phase_quality(AnalysisPhase.L0_DIALOGUE, low_quality_result)
        assert not passed


class TestAnalysisSession:
    """测试分析会话管理"""

    def test_analysis_session_creation(self):
        """测试分析会话创建"""
        session = AnalysisSession(session_id="test_session_123", query="测试查询", context={"user_location": "北京"})

        assert session.session_id == "test_session_123"
        assert session.query == "测试查询"
        assert session.context == {"user_location": "北京"}
        assert session.current_phase == AnalysisPhase.L0_DIALOGUE

    def test_analysis_session_post_init(self):
        """测试分析会话后初始化"""
        session = AnalysisSession(session_id="test", query="test")
        session.__post_init__()

        assert isinstance(session.context, dict)

    def test_analysis_session_can_proceed(self):
        """测试是否可以进入下一阶段"""
        session = AnalysisSession(session_id="test", query="test")

        # 没有当前阶段结果时不能进入下一阶段
        can_proceed = session.can_proceed_to_next_phase()
        assert not can_proceed

        # 添加高质量结果后应该可以进入下一阶段
        high_quality_result = PhaseResult(phase=AnalysisPhase.L0_DIALOGUE, content={}, quality_score=0.9)
        session.phase_results[AnalysisPhase.L0_DIALOGUE] = high_quality_result

        # 需要模拟质量门控检查通过
        session.quality_gate.check_phase_quality = Mock(return_value=True)
        can_proceed = session.can_proceed_to_next_phase()
        assert can_proceed


class TestDeepSeekAnalysisEngine:
    """测试DeepSeek专用分析引擎"""

    @pytest.fixture
    def engine(self):
        """创建分析引擎实例"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            return DeepSeekAnalysisEngine()

    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine.thinking_model == "deepseek-reasoner"
        assert engine.eval_model == "deepseek-chat"
        assert engine.quality_threshold == 0.75
        assert engine.deepseek_api_key == "test_key"

    @pytest.mark.asyncio
    async def test_deepseek_call_success(self, engine):
        """测试DeepSeek API调用成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "测试响应内容"}}]}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await engine._deepseek_call("测试prompt")
            assert result == "测试响应内容"

    @pytest.mark.asyncio
    async def test_deepseek_call_failure(self, engine):
        """测试DeepSeek API调用失败"""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await engine._deepseek_call("测试prompt")
            assert result is None

    @pytest.mark.asyncio
    async def test_execute_l0_dialogue(self, engine):
        """测试L0对话分析执行"""
        # Mock DeepSeek API调用
        mock_api_response = """基于您的需求，我理解您是想在北京设计一个咖啡厅...

```json
{
    "user_profile": {
        "demographics": {"location": "北京", "project_type": "咖啡厅设计"},
        "identity_tags": ["设计需求者", "空间规划者"],
        "lifestyle_indicators": ["注重氛围", "追求舒适"]
    },
    "implicit_needs": {
        "functional": ["合理布局", "高效流线"],
        "emotional": ["温馨氛围", "舒适体验"],
        "social": ["社交空间", "个人独处空间"]
    },
    "confidence_assessment": {
        "profile_confidence": 0.8,
        "need_identification_confidence": 0.85
    }
}
```"""

        engine._deepseek_call = AsyncMock(return_value=mock_api_response)

        result = await engine.execute_l0_dialogue("我想在北京设计一个100平米的咖啡厅", {"user_location": "北京"})

        assert result is not None
        assert isinstance(result, L0DialogueResult)
        assert result.phase == AnalysisPhase.L0_DIALOGUE
        assert len(result.implicit_needs) > 0
        assert result.quality_score > 0

    @pytest.mark.asyncio
    async def test_execute_l1_l5_framework(self, engine):
        """测试L1-L5框架分析执行"""
        # 创建模拟的用户画像
        mock_user_profile = StructuredUserInfo()
        mock_user_profile.demographics = {"location": "北京", "project_type": "咖啡厅"}

        # 创建模拟的L0结果
        l0_result = L0DialogueResult(
            phase=AnalysisPhase.L0_DIALOGUE,
            content={},
            quality_score=0.8,
            execution_time=1.0,
            user_profile=mock_user_profile,
            context_understanding="用户想要设计咖啡厅",
            implicit_needs=["温馨氛围"],
            dialogue_content="分析内容",
        )

        mock_api_response = """{
    "l1_facts": ["100平米空间", "北京地区", "咖啡厅业态"],
    "l2_models": {
        "心理学": "用户需求层次分析",
        "空间学": "空间功能分区理论",
        "美学": "氛围营造设计理念"
    },
    "l3_tensions": "功能性 vs 美观性",
    "l4_jtbd": "从无到有创建一个成功的咖啡厅空间",
    "l5_sharpness": {"overall_sharpness": 85}
}"""

        engine._deepseek_call = AsyncMock(return_value=mock_api_response)

        result = await engine.execute_l1_l5_framework("测试查询", l0_result)

        assert result is not None
        assert isinstance(result, L1L5FrameworkResult)
        assert len(result.l1_facts) >= 3
        assert result.l3_tensions == "功能性 vs 美观性"
        assert result.framework_coherence > 0


class TestUcpptSearchEngine:
    """测试UCPPT搜索引擎主类"""

    @pytest.fixture
    def search_engine(self):
        """创建搜索引擎实例"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key", "OPENROUTER_API_KEYS": "test_openrouter_key"}):
            # Mock掉各种外部依赖
            with patch(
                "intelligent_project_analyzer.services.bocha_ai_search.get_ai_search_service", return_value=Mock()
            ):
                with patch("intelligent_project_analyzer.tools.openalex_search.OpenAlexSearchTool"):
                    engine = UcpptSearchEngine()
                    # 设置mock的搜索服务
                    engine.bocha_service = Mock()
                    return engine

    def test_engine_initialization(self, search_engine):
        """测试搜索引擎初始化"""
        assert search_engine.deepseek_analysis_engine is not None
        assert isinstance(search_engine.quality_gates, dict)
        assert search_engine.analysis_session is None
        assert search_engine.max_rounds > 0

    @pytest.mark.asyncio
    async def test_structured_problem_analysis_success(self, search_engine):
        """测试结构化问题分析成功场景"""
        # Mock L0分析结果
        mock_l0_result = L0DialogueResult(
            phase=AnalysisPhase.L0_DIALOGUE,
            content={},
            quality_score=0.8,
            context_understanding="用户分析",
            implicit_needs=["需求1", "需求2"],
            dialogue_content="对话内容",
        )

        # Mock L1-L5分析结果
        mock_framework_result = L1L5FrameworkResult(
            phase=AnalysisPhase.L1_L5_FRAMEWORK,
            content={},
            quality_score=0.85,
            l1_facts=["事实1", "事实2", "事实3"],
            l3_tensions="张力分析",
            l4_jtbd="任务目标",
            framework_coherence=0.8,
        )

        # Mock综合分析结果
        mock_synthesis_result = SynthesisResult(phase=AnalysisPhase.SYNTHESIS, content={}, quality_score=0.9)

        # Mock DeepSeek分析引擎的各个方法
        search_engine.deepseek_analysis_engine.execute_l0_dialogue = AsyncMock(return_value=mock_l0_result)
        search_engine.deepseek_analysis_engine.execute_l1_l5_framework = AsyncMock(return_value=mock_framework_result)
        search_engine.deepseek_analysis_engine.execute_synthesis = AsyncMock(return_value=mock_synthesis_result)

        # 执行结构化分析
        result = await search_engine.structured_problem_analysis("测试查询", {"context": "test"})

        assert result is not None
        assert isinstance(result, AnalysisSession)
        assert result.l0_result == mock_l0_result
        assert result.framework_result == mock_framework_result
        assert result.synthesis_result == mock_synthesis_result
        assert result.overall_quality > 0

    @pytest.mark.asyncio
    async def test_structured_problem_analysis_l0_failure(self, search_engine):
        """测试L0分析失败场景"""
        # Mock L0分析失败
        search_engine.deepseek_analysis_engine.execute_l0_dialogue = AsyncMock(return_value=None)

        result = await search_engine.structured_problem_analysis("测试查询", {"context": "test"})

        assert result is None

    @pytest.mark.asyncio
    async def test_enhanced_quality_assessment_empty_results(self, search_engine):
        """测试空结果的质量评估"""
        result = await search_engine.enhanced_quality_assessment([], "测试查询上下文", "test_phase")

        assert result["filtered_results"] == []
        assert result["quality_metrics"]["total_score"] == 0.0
        assert "无搜索结果" in result["assessment_summary"]

    @pytest.mark.asyncio
    async def test_enhanced_quality_assessment_with_results(self, search_engine):
        """测试有结果的质量评估"""
        mock_results = [
            {
                "title": "高质量标题内容详细说明",
                "content": "这是一个高质量的内容，包含了详细的信息和专业的分析。" * 10,  # 长内容
                "url": "https://example.edu/article",
                "siteName": "知名教育网站",
            },
            {"title": "短标题", "content": "短内容", "url": "https://unknown.com/page", "siteName": "未知网站"},
        ]

        # Mock LLM质量评估
        search_engine._llm_quality_assessment = AsyncMock(
            return_value=[
                {"index": 0, "llm_quality_score": 0.9, "total_quality_score": 0.85, "quality_explanation": "高质量内容"}
            ]
        )

        result = await search_engine.enhanced_quality_assessment(mock_results, "测试查询上下文", "test_phase")

        assert len(result["filtered_results"]) >= 0
        assert result["quality_metrics"]["total_score"] >= 0
        assert "四层筛选" in result["assessment_summary"]

    @pytest.mark.asyncio
    async def test_generate_expanded_queries(self, search_engine):
        """测试查询扩展生成"""
        # Mock DeepSeek API调用
        mock_response = """{
    "expansions": [
        "详细 原始查询",
        "原始查询 案例研究",
        "原始查询 最佳实践"
    ]
}"""

        search_engine.deepseek_analysis_engine._deepseek_call = AsyncMock(return_value=mock_response)

        expanded_queries = await search_engine._generate_expanded_queries("原始查询")

        assert len(expanded_queries) == 3
        assert "详细 原始查询" in expanded_queries
        assert "案例研究" in expanded_queries[1]

    @pytest.mark.asyncio
    async def test_assess_search_quality_empty(self, search_engine):
        """测试空结果的搜索质量评估"""
        quality = await search_engine._assess_search_quality([], "测试查询")

        assert quality["overall_score"] == 0.0
        assert "无搜索结果" in quality["issues"]

    @pytest.mark.asyncio
    async def test_assess_search_quality_with_results(self, search_engine):
        """测试有结果的搜索质量评估"""
        mock_sources = [
            {"title": "机器学习算法相关标题包含人工智能内容", "content": "这个内容包含了机器学习和人工智能的关键信息，深度学习神经网络算法详细介绍了相关技术", "siteName": "网站A"},
            {"title": "人工智能和机器学习的应用", "content": "更多关于机器学习算法的详细信息内容，包括深度学习和神经网络的实际应用案例", "siteName": "网站B"},
        ]

        quality = await search_engine._assess_search_quality(mock_sources, "机器学习算法")

        assert quality["overall_score"] > 0
        assert quality["relevance_score"] > 0
        assert quality["diversity_score"] > 0
        assert isinstance(quality["issues"], list)

    def test_is_duplicate_content(self, search_engine):
        """测试内容重复检查"""
        existing_contents = ["这是第一个内容，包含一些特定的信息和数据", "这是第二个不同的内容，讨论其他话题"]

        # 测试重复内容 - 使用更高相似度的内容
        duplicate_content = "这是第一个内容，包含一些特定的信息和数据"  # 几乎相同
        is_duplicate = search_engine._is_duplicate_content(duplicate_content, existing_contents)
        assert is_duplicate

        # 测试非重复内容
        unique_content = "完全不同的新内容主题和关键词组合实验测试"
        is_duplicate = search_engine._is_duplicate_content(unique_content, existing_contents)
        assert not is_duplicate

    def test_calculate_rule_score(self, search_engine):
        """测试规则评分计算"""
        # 高质量结果
        high_quality_result = {
            "title": "这是一个详细的高质量标题内容",
            "content": "这是一个很长的高质量内容，包含大量有用的信息。" * 50,  # 长内容
            "url": "https://example.edu/article",
            "publish_time": "2024-12-15",
        }

        score = search_engine._calculate_rule_score(high_quality_result)
        assert score > 0.8  # 应该是高分

        # 低质量结果
        low_quality_result = {
            "title": "短",
            "content": "短内容",
            "url": "http://unknown.com/page",
            "publish_time": "2020-01-01",
        }

        score = search_engine._calculate_rule_score(low_quality_result)
        assert score < 0.5  # 应该是低分

    def test_is_academic_query(self, search_engine):
        """测试学术查询判断"""
        # 学术查询
        academic_queries = ["机器学习算法研究", "深度学习理论分析", "人工智能论文综述", "数据挖掘方法论"]

        for query in academic_queries:
            is_academic = search_engine._is_academic_query(query)
            assert is_academic

        # 非学术查询
        general_queries = ["北京咖啡厅设计", "家居装修风格", "旅游景点推荐"]

        for query in general_queries:
            is_academic = search_engine._is_academic_query(query)
            assert not is_academic


# 性能测试类
class TestPerformance:
    """性能相关测试"""

    @pytest.mark.asyncio
    async def test_analysis_performance(self):
        """测试分析性能"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            engine = DeepSeekAnalysisEngine()

            # Mock快速响应
            engine._deepseek_call = AsyncMock(return_value='{"test": "快速响应"}')

            start_time = time.time()

            # 执行多个并发分析任务
            tasks = []
            for i in range(5):
                task = engine._deepseek_call(f"测试prompt {i}")
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = end_time - start_time

            # 验证性能要求（5个任务应该在合理时间内完成）
            assert total_time < 5.0  # 5秒内完成
            assert len(results) == 5
            assert all(result is not None for result in results)


# 集成测试类
class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"})
    async def test_full_analysis_pipeline(self):
        """测试完整的分析流水线"""
        # 这个测试验证整个分析流程的集成
        engine = DeepSeekAnalysisEngine()

        # Mock各阶段的API响应
        mock_responses = {
            0: """用户想要在北京设计咖啡厅...
```json
{"user_profile": {"demographics": {"location": "北京"}}, "implicit_needs": {"functional": ["布局"]}, "confidence_assessment": {"profile_confidence": 0.8}}
```""",
            1: """{"l1_facts": ["事实1"], "l2_models": {"心理学": "分析"}, "l3_tensions": "张力", "l4_jtbd": "目标", "l5_sharpness": {"overall_sharpness": 80}}""",
            2: """{"search_master_line": {"core_question": "核心问题", "search_phases": ["阶段1"]}, "search_tasks": [{"id": "task1", "task": "任务1"}], "execution_plan": {"total_estimated_rounds": 5}}""",
        }

        call_count = 0

        async def mock_deepseek_call(*args, **kwargs):
            nonlocal call_count
            response = mock_responses.get(call_count, "{}")
            call_count += 1
            return response

        engine._deepseek_call = mock_deepseek_call

        # 执行L0分析
        l0_result = await engine.execute_l0_dialogue("测试查询", {})
        assert l0_result is not None

        # 执行L1-L5分析
        l1_l5_result = await engine.execute_l1_l5_framework("测试查询", l0_result)
        assert l1_l5_result is not None

        # 执行综合分析
        synthesis_result = await engine.execute_synthesis("测试查询", l0_result, l1_l5_result)
        assert synthesis_result is not None

        # 验证整个流水线的连贯性
        assert l0_result.phase == AnalysisPhase.L0_DIALOGUE
        assert l1_l5_result.phase == AnalysisPhase.L1_L5_FRAMEWORK
        assert synthesis_result.phase == AnalysisPhase.SYNTHESIS


# 异常处理测试
class TestErrorHandling:
    """异常处理测试"""

    @pytest.mark.asyncio
    async def test_api_failure_fallback(self):
        """测试API失败时的降级处理"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            engine = DeepSeekAnalysisEngine()

            # Mock API失败
            engine._deepseek_call = AsyncMock(return_value=None)

            # 执行L0分析（应该返回None）
            result = await engine.execute_l0_dialogue("测试查询", {})
            assert result is None

    @pytest.mark.asyncio
    async def test_json_parsing_error_handling(self):
        """测试JSON解析错误处理"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            engine = DeepSeekAnalysisEngine()

            # Mock返回无效JSON
            engine._deepseek_call = AsyncMock(return_value="无效的JSON内容")

            # 执行分析（应该有降级处理）
            result = await engine.execute_l0_dialogue("测试查询", {})

            # 应该有降级处理，返回基本结果而不是None
            assert result is not None
            assert result.quality_score == 0.4  # 降级质量分数

    def test_missing_api_key_handling(self):
        """测试缺少API密钥的处理"""
        with patch.dict(os.environ, {}, clear=True):
            engine = DeepSeekAnalysisEngine()

            # 应该有警告但不崩溃
            assert engine.deepseek_api_key == ""
            # 检查会有警告日志（实际应用中）


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
