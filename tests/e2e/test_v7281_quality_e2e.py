"""
v7.281 答案质量评估机制 - 端到端测试

测试内容：
1. 完整搜索流程中的质量评估
2. 前后端数据交互
3. 用户可见的质量指标展示
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from intelligent_project_analyzer.services.ucppt_search_engine import (
    AnswerFramework,
    RoundInsights,
    SearchFramework,
    SearchTarget,
    UcpptSearchEngine,
)

# ==================== Fixtures ====================


@pytest.fixture
def mock_search_sources():
    """模拟搜索结果来源"""
    return [
        {
            "id": f"src_{i}",
            "title": f"测试来源 {i}",
            "url": f"https://example.com/source/{i}",
            "content": f"这是来源 {i} 的详细内容...",
            "snippet": f"来源 {i} 的摘要",
            "_round": (i % 5) + 1,
            "quality_score": 0.7 + (i % 3) * 0.1,
        }
        for i in range(1, 31)
    ]


@pytest.fixture
def mock_complete_framework():
    """创建完整的搜索框架"""
    framework = AnswerFramework(
        original_query="如何设计一个8平米的日式侘寂风格卧室，预算3万元",
        answer_goal="为用户提供完整的日式侘寂风格小户型卧室设计方案，包含材料选择、空间布局和预算分配",
    )

    # 模拟5轮搜索的洞察
    framework.round_insights = [
        RoundInsights(
            round_number=1,
            target_aspect="侘寂美学理论基础",
            search_query="侘寂美学 wabi-sabi 核心理念 设计原则",
            key_findings=[
                "侘寂美学强调不完美之美和自然朴素",
                "核心元素包括：简约、质朴、自然、岁月痕迹",
                "色彩以中性色和大地色系为主",
            ],
            inferred_insights=["用户追求的是精神层面的宁静而非奢华"],
            info_sufficiency=0.85,
            info_quality=0.9,
            alignment_score=0.88,
            best_source_urls=["https://example.com/1", "https://example.com/2", "https://example.com/3"],
            sources_count=10,
        ),
        RoundInsights(
            round_number=2,
            target_aspect="小户型卧室布局",
            search_query="8平米 小户型卧室 空间布局 收纳设计",
            key_findings=[
                "8平米卧室推荐L型或一字型布局",
                "床头不宜靠窗，建议靠实墙",
                "充分利用垂直空间做收纳",
            ],
            inferred_insights=["动线设计对小空间至关重要"],
            info_sufficiency=0.8,
            info_quality=0.85,
            alignment_score=0.85,
            best_source_urls=["https://example.com/4", "https://example.com/5"],
            sources_count=8,
        ),
        RoundInsights(
            round_number=3,
            target_aspect="日式卧室材料选择",
            search_query="日式风格 卧室材料 木材 草编 3万预算",
            key_findings=[
                "榉木是性价比较高的日式风格木材",
                "草编元素（榻榻米垫、草编收纳）增添日式氛围",
                "障子纸可用于隔断或灯具",
            ],
            inferred_insights=["在3万预算内应优先投资在视觉焦点区域"],
            info_sufficiency=0.75,
            info_quality=0.8,
            alignment_score=0.82,
            best_source_urls=["https://example.com/6"],
            sources_count=6,
        ),
        RoundInsights(
            round_number=4,
            target_aspect="色彩与灯光设计",
            search_query="日式侘寂 色彩搭配 灯光设计 氛围营造",
            key_findings=[
                "主色调建议米白、浅灰、原木色",
                "避免高饱和度色彩，保持整体素雅",
                "灯光以暖白色为主，多点位分散布置",
            ],
            inferred_insights=["间接照明更符合侘寂美学的意境"],
            info_sufficiency=0.7,
            info_quality=0.75,
            alignment_score=0.8,
            best_source_urls=["https://example.com/7", "https://example.com/8"],
            sources_count=5,
        ),
        RoundInsights(
            round_number=5,
            target_aspect="预算分配与实施",
            search_query="卧室装修 3万预算 日式风格 预算分配",
            key_findings=[
                "3万预算分配建议：硬装40%、软装35%、家具25%",
                "可考虑部分DIY降低成本",
                "关键投资点：床垫、窗帘、灯具",
            ],
            inferred_insights=["预算有限时应优先保证睡眠质量相关投入"],
            info_sufficiency=0.7,
            info_quality=0.7,
            alignment_score=0.78,
            best_source_urls=["https://example.com/9"],
            sources_count=4,
        ),
    ]

    return framework


# ==================== 1. 完整流程端到端测试 ====================


class TestFullFlowE2E:
    """完整搜索流程端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_quality_assessment_flow(self, mock_complete_framework, mock_search_sources):
        """测试完整的质量评估流程"""
        engine = UcpptSearchEngine()
        framework = mock_complete_framework
        sources = mock_search_sources

        # Step 1: 执行冲突检测
        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)

        assert conflict_result is not None
        assert "has_conflicts" in conflict_result
        # 示例数据应该没有冲突
        assert conflict_result["has_conflicts"] == False

        # Step 2: 模拟答案生成
        mock_answer = """
        # 8平米日式侘寂风格卧室设计方案

        ## 1. 设计理念
        根据侘寂美学的核心理念[1][2]，本方案强调自然朴素和不完美之美。

        ## 2. 空间布局
        参考小户型布局研究[3][4]，建议采用L型布局，床头靠实墙。

        ## 3. 材料选择
        材料方面[5][6]，推荐使用榉木和草编元素。

        ## 4. 色彩方案
        色彩以米白、浅灰、原木色为主[7][8]，灯光采用暖白色。

        ## 5. 预算分配
        3万预算分配建议[9][10]：硬装40%、软装35%、家具25%。

        综合以上研究[11][12]，这是一个完整可行的设计方案。
        """

        # Step 3: 执行引用校验
        citation_result = engine._validate_citation_references(mock_answer, len(sources))

        assert citation_result["valid"] == True
        assert citation_result["total_citations"] == 12
        assert len(citation_result["invalid_citations"]) == 0

        # Step 4: 计算置信度
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=len(sources),
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 验证置信度结果
        assert confidence_result["overall_confidence"] >= 0.6  # 应该是中等以上
        assert confidence_result["confidence_level"] in ["高", "中"]
        assert "dimension_scores" in confidence_result
        assert len(confidence_result["dimension_scores"]) == 5

        # Step 5: 构造并验证 SSE 事件
        event = {
            "type": "answer_quality_assessment",
            "data": {
                "confidence": confidence_result,
                "citation": citation_result,
                "conflicts": {
                    "has_conflicts": conflict_result["has_conflicts"],
                    "count": len(conflict_result.get("conflicts", [])),
                },
                "message": f"答案置信度: {confidence_result['confidence_level']} ({confidence_result['overall_confidence']:.0%})",
            },
        }

        # 验证事件可被正确序列化
        event_json = json.dumps(event, ensure_ascii=False)
        parsed_event = json.loads(event_json)

        assert parsed_event["type"] == "answer_quality_assessment"
        assert "confidence" in parsed_event["data"]

    @pytest.mark.asyncio
    async def test_quality_assessment_with_conflicts(self, mock_search_sources):
        """测试有冲突情况下的质量评估"""
        engine = UcpptSearchEngine()

        # 创建有冲突的框架
        framework = AnswerFramework(
            original_query="日式卧室材料选择",
            answer_goal="推荐合适的材料",
        )

        # 创建冲突的洞察
        framework.round_insights = [
            RoundInsights(
                round_number=1,
                key_findings=["推荐使用橡木，耐用且美观"],
                inferred_insights=["应该选择硬木材质"],
                info_quality=0.8,
                info_sufficiency=0.8,
                alignment_score=0.8,
            ),
            RoundInsights(
                round_number=2,
                key_findings=["不推荐使用橡木，价格过高"],
                inferred_insights=["不应该选择进口木材"],
                info_quality=0.85,
                info_sufficiency=0.8,
                alignment_score=0.85,
            ),
        ]

        # 执行冲突检测
        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)

        # 应该检测到冲突
        assert conflict_result["has_conflicts"] == True or len(conflict_result["conflicts"]) > 0

        # 计算置信度 - 有冲突应影响一致性得分
        citation_result = {"citation_coverage": 0.3, "valid": True, "total_citations": 5}
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=10,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 一致性得分应该低于1.0
        assert confidence_result["dimension_scores"]["consistency"] < 1.0


# ==================== 2. 前端数据格式测试 ====================


class TestFrontendDataFormat:
    """测试前端期望的数据格式"""

    def test_quality_assessment_matches_frontend_interface(self, mock_complete_framework):
        """验证质量评估数据匹配前端 TypeScript 接口"""
        engine = UcpptSearchEngine()
        framework = mock_complete_framework

        # 执行评估
        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)
        citation_result = engine._validate_citation_references("测试引用[1][2][3]", 10)
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=10,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 构造前端期望的数据结构
        frontend_data = {
            "confidence": {
                "overall_confidence": confidence_result["overall_confidence"],
                "confidence_level": confidence_result["confidence_level"],
                "dimension_scores": confidence_result["dimension_scores"],
                "confidence_note": confidence_result["confidence_note"],
            },
            "citation": {
                "valid": citation_result["valid"],
                "total_citations": citation_result["total_citations"],
                "valid_citations": citation_result["valid_citations"],
                "invalid_citations": citation_result["invalid_citations"],
                "citation_coverage": citation_result["citation_coverage"],
                "warning": citation_result["warning"],
            },
            "conflicts": {
                "has_conflicts": conflict_result["has_conflicts"],
                "count": len(conflict_result.get("conflicts", [])),
            },
        }

        # 验证类型
        assert isinstance(frontend_data["confidence"]["overall_confidence"], float)
        assert isinstance(frontend_data["confidence"]["confidence_level"], str)
        assert isinstance(frontend_data["confidence"]["dimension_scores"], dict)
        assert isinstance(frontend_data["citation"]["valid"], bool)
        assert isinstance(frontend_data["citation"]["total_citations"], int)
        assert isinstance(frontend_data["conflicts"]["has_conflicts"], bool)

        # 验证值范围
        assert 0 <= frontend_data["confidence"]["overall_confidence"] <= 1
        assert frontend_data["confidence"]["confidence_level"] in ["高", "中", "低"]

        # 验证维度得分
        expected_dimensions = ["info_sufficiency", "info_quality", "source_coverage", "consistency", "goal_alignment"]
        for dim in expected_dimensions:
            assert dim in frontend_data["confidence"]["dimension_scores"]
            assert 0 <= frontend_data["confidence"]["dimension_scores"][dim] <= 1

    def test_json_serialization(self, mock_complete_framework):
        """测试 JSON 序列化"""
        engine = UcpptSearchEngine()
        framework = mock_complete_framework

        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)
        citation_result = engine._validate_citation_references("测试[1][2]", 10)
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=10,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 构造完整事件
        event = {
            "type": "answer_quality_assessment",
            "data": {
                "confidence": confidence_result,
                "citation": citation_result,
                "conflicts": {
                    "has_conflicts": conflict_result["has_conflicts"],
                    "count": len(conflict_result.get("conflicts", [])),
                },
            },
        }

        # 应该可以序列化
        json_str = json.dumps(event, ensure_ascii=False, default=str)
        assert json_str is not None

        # 应该可以反序列化
        parsed = json.loads(json_str)
        assert parsed["type"] == "answer_quality_assessment"


# ==================== 3. 用户体验测试 ====================


class TestUserExperience:
    """测试用户可见的质量指标"""

    def test_confidence_message_generation(self, mock_complete_framework):
        """测试置信度消息生成"""
        engine = UcpptSearchEngine()
        framework = mock_complete_framework

        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)
        citation_result = {"citation_coverage": 0.4, "valid": True, "total_citations": 10}
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=30,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 构造用户消息
        message = f"答案置信度: {confidence_result['confidence_level']} ({confidence_result['overall_confidence']:.0%})"

        # 消息应该包含置信度等级和百分比
        assert confidence_result["confidence_level"] in message
        assert "%" in message

    def test_confidence_note_is_meaningful(self, mock_complete_framework):
        """测试置信度说明的可读性"""
        engine = UcpptSearchEngine()
        framework = mock_complete_framework

        # 高质量场景
        conflict_result = {"has_conflicts": False, "conflicts": []}
        citation_result = {"citation_coverage": 0.5, "valid": True}
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=30,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        note = confidence_result["confidence_note"]

        # 说明应该是中文，有意义
        assert len(note) > 10
        assert any(word in note for word in ["信息", "来源", "质量", "可信", "充分"])

    def test_warning_for_low_quality(self):
        """测试低质量时的警告"""
        engine = UcpptSearchEngine()

        # 创建低质量框架
        framework = AnswerFramework(original_query="测试")
        framework.round_insights = [
            RoundInsights(
                round_number=1,
                info_quality=0.3,
                info_sufficiency=0.3,
                alignment_score=0.3,
            )
        ]

        # 低质量引用
        citation_result = engine._validate_citation_references("只有[1]一个引用", 20)

        # 有冲突
        conflict_result = {"has_conflicts": True, "conflicts": [{}]}

        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=20,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 应该是低置信度
        assert confidence_result["confidence_level"] == "低" or confidence_result["overall_confidence"] < 0.55

        # 说明应该提醒用户
        note = confidence_result["confidence_note"]
        assert any(word in note for word in ["谨慎", "验证", "不够", "冲突", "补充"])


# ==================== 4. 边界条件测试 ====================


class TestE2EEdgeCases:
    """端到端边界条件测试"""

    @pytest.mark.asyncio
    async def test_empty_search_results(self):
        """测试空搜索结果的情况"""
        engine = UcpptSearchEngine()

        framework = AnswerFramework(original_query="无结果的查询")
        framework.round_insights = []

        # 应该处理空结果
        conflict_result = engine._detect_cross_round_conflicts([])
        citation_result = engine._validate_citation_references("无引用的答案", 0)
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=[],
            sources_count=0,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 应该返回有意义的默认值
        assert confidence_result is not None
        assert confidence_result["overall_confidence"] >= 0

    @pytest.mark.asyncio
    async def test_very_long_answer(self):
        """测试非常长的答案"""
        engine = UcpptSearchEngine()

        # 生成长答案（模拟2000字）
        long_answer = "这是一段很长的答案。" * 100
        for i in range(1, 31):
            long_answer += f" 根据研究[{i}]，这是重要的发现。"

        # 应该正确处理
        result = engine._validate_citation_references(long_answer, 50)

        assert result["total_citations"] == 30
        assert result["valid"]

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self):
        """测试特殊字符"""
        engine = UcpptSearchEngine()

        # 包含各种特殊字符
        special_answer = """
        根据研究[1]，日式设计（wabi-sabi）很重要！
        专家[2]指出：「简约」是核心。
        另外[3]，预算约 ¥30,000 - ¥50,000。
        参考[4]&[5]的建议，以及[6]（含emoji 🎌）。
        """

        result = engine._validate_citation_references(special_answer, 10)

        # 应该正确提取引用
        assert result["total_citations"] == 6
        assert all(c <= 10 for c in result["valid_citations"])


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
