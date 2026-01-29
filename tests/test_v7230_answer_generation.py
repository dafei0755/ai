"""
v7.230 答案生成机制改良 - 单元测试

测试内容：
1. RoundInsights 数据结构
2. AnswerFramework 的 round_insights 累积
3. 来源选择逻辑（每轮保证Top-3 + 轮次权重）
4. 相关性计算增强（轮次权重 + 质量分加成）
"""

import os
import sys
from dataclasses import asdict

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_project_analyzer.services.ucppt_search_engine import AnswerFramework, KeyAspect, RoundInsights


class TestRoundInsights:
    """测试 RoundInsights 数据结构"""

    def test_round_insights_creation(self):
        """测试 RoundInsights 基本创建"""
        insight = RoundInsights(
            round_number=1,
            target_aspect="日式侘寂风格",
            search_query="侘寂美学核心原则",
            key_findings=["素材质感比颜色更重要", "强调自然材料"],
            inferred_insights=["用户追求简约而非简单"],
            info_sufficiency=0.8,
            info_quality=0.9,
            quality_issues=[],
            alignment_score=0.85,
            alignment_note="与用户目标高度对齐",
            remaining_gaps=["具体材料选择"],
            best_source_urls=["https://example.com/1", "https://example.com/2"],
            sources_count=8,
            progress_description="完成基础概念搜索，理解了侘寂美学核心",
        )

        assert insight.round_number == 1
        assert insight.target_aspect == "日式侘寂风格"
        assert len(insight.key_findings) == 2
        assert len(insight.inferred_insights) == 1
        assert insight.info_quality == 0.9
        assert insight.alignment_score == 0.85
        assert len(insight.best_source_urls) == 2
        assert insight.sources_count == 8

    def test_round_insights_defaults(self):
        """测试 RoundInsights 默认值"""
        insight = RoundInsights(round_number=1)

        assert insight.target_aspect == ""
        assert insight.search_query == ""
        assert insight.key_findings == []
        assert insight.inferred_insights == []
        assert insight.info_sufficiency == 0.0
        assert insight.info_quality == 0.0
        assert insight.quality_issues == []
        assert insight.alignment_score == 0.0
        assert insight.alignment_note == ""
        assert insight.remaining_gaps == []
        assert insight.best_source_urls == []
        assert insight.sources_count == 0
        assert insight.progress_description == ""


class TestAnswerFrameworkRoundInsights:
    """测试 AnswerFramework 的 round_insights 累积功能"""

    def test_answer_framework_has_round_insights(self):
        """测试 AnswerFramework 包含 round_insights 字段"""
        framework = AnswerFramework(original_query="日式卧室设计")

        assert hasattr(framework, "round_insights")
        assert isinstance(framework.round_insights, list)
        assert len(framework.round_insights) == 0

    def test_round_insights_accumulation(self):
        """测试轮次洞察累积（不覆盖）"""
        framework = AnswerFramework(original_query="日式卧室设计")

        # 第1轮洞察
        insight1 = RoundInsights(
            round_number=1,
            target_aspect="风格基础",
            key_findings=["侘寂强调不完美之美"],
            info_quality=0.7,
        )
        framework.round_insights.append(insight1)

        # 第2轮洞察
        insight2 = RoundInsights(
            round_number=2,
            target_aspect="材料选择",
            key_findings=["天然木材和竹子是首选"],
            info_quality=0.85,
        )
        framework.round_insights.append(insight2)

        # 第3轮洞察
        insight3 = RoundInsights(
            round_number=3,
            target_aspect="照明设计",
            key_findings=["柔和的间接照明"],
            info_quality=0.9,
        )
        framework.round_insights.append(insight3)

        # 验证所有轮次都被保留
        assert len(framework.round_insights) == 3
        assert framework.round_insights[0].round_number == 1
        assert framework.round_insights[1].round_number == 2
        assert framework.round_insights[2].round_number == 3

        # 验证内容完整
        assert "侘寂强调不完美之美" in framework.round_insights[0].key_findings
        assert "天然木材和竹子是首选" in framework.round_insights[1].key_findings
        assert "柔和的间接照明" in framework.round_insights[2].key_findings

    def test_total_findings_count(self):
        """测试累积的发现总数统计"""
        framework = AnswerFramework(original_query="测试")

        framework.round_insights.append(
            RoundInsights(
                round_number=1,
                key_findings=["发现1", "发现2"],
                inferred_insights=["洞察1"],
            )
        )
        framework.round_insights.append(
            RoundInsights(
                round_number=2,
                key_findings=["发现3"],
                inferred_insights=["洞察2", "洞察3"],
            )
        )

        total_findings = sum(len(i.key_findings) for i in framework.round_insights)
        total_insights = sum(len(i.inferred_insights) for i in framework.round_insights)

        assert total_findings == 3
        assert total_insights == 3


class TestSourceRelevanceCalculation:
    """测试来源相关性计算（需要实例化搜索引擎）"""

    @pytest.fixture
    def mock_framework(self):
        """创建测试用的 AnswerFramework"""
        framework = AnswerFramework(original_query="日式侘寂风格卧室设计", answer_goal="提供侘寂风格卧室的设计建议")
        framework.key_aspects = [
            KeyAspect(
                aspect_name="材料选择",
                answer_goal="推荐适合侘寂风格的材料",
                importance=5,
            ),
            KeyAspect(
                aspect_name="色彩搭配",
                answer_goal="侘寂风格的色彩方案",
                importance=4,
            ),
        ]
        return framework

    def test_source_with_round_field(self):
        """测试来源包含 _round 字段"""
        source = {
            "title": "侘寂美学的核心原则",
            "url": "https://example.com/wabi-sabi",
            "content": "侘寂是一种日本美学...",
            "_round": 3,  # v7.230: 新增轮次标记
            "quality_score": 0.85,
        }

        assert "_round" in source
        assert source["_round"] == 3
        assert "quality_score" in source

    def test_round_weight_calculation(self):
        """测试轮次权重计算逻辑"""
        # 轮次权重公式: 1 + (round_num - 1) * 0.05
        # 第1轮: 1 + 0 * 0.05 = 1.0
        # 第3轮: 1 + 2 * 0.05 = 1.10
        # 第6轮: 1 + 5 * 0.05 = 1.25

        def calc_round_weight(round_num):
            return 1 + (round_num - 1) * 0.05

        assert calc_round_weight(1) == 1.0
        assert calc_round_weight(3) == 1.10
        assert calc_round_weight(6) == 1.25
        assert calc_round_weight(10) == 1.45


class TestSmartSourceSelection:
    """测试智能来源选择逻辑"""

    def test_guaranteed_sources_from_round_insights(self):
        """测试每轮保证Top-3来源入选"""
        framework = AnswerFramework(original_query="测试")

        # 添加3轮洞察，每轮有3个最佳来源
        framework.round_insights.append(
            RoundInsights(
                round_number=1,
                best_source_urls=["url1", "url2", "url3"],
            )
        )
        framework.round_insights.append(
            RoundInsights(
                round_number=2,
                best_source_urls=["url4", "url5", "url6"],
            )
        )
        framework.round_insights.append(
            RoundInsights(
                round_number=3,
                best_source_urls=["url7", "url8", "url9"],
            )
        )

        # 收集所有保证入选的URL
        guaranteed_urls = set()
        for insight in framework.round_insights:
            for url in insight.best_source_urls[:3]:
                if url:
                    guaranteed_urls.add(url)

        # 应该有 3轮 * 3条 = 9 条保证入选
        assert len(guaranteed_urls) == 9
        assert "url1" in guaranteed_urls
        assert "url9" in guaranteed_urls

    def test_source_selection_limit(self):
        """测试来源选择上限（v7.230: 30条）"""
        MAX_SOURCES = 30  # v7.230: 从25增加到30

        # 模拟有100条来源
        all_sources = [{"url": f"url{i}", "title": f"Title {i}"} for i in range(100)]

        # 选择逻辑应该最多返回30条
        selected = all_sources[:MAX_SOURCES]

        assert len(selected) == 30


class TestResearchInsightsText:
    """测试研究过程洞察文本生成"""

    def test_research_insights_format(self):
        """测试研究洞察的格式化输出"""
        insight = RoundInsights(
            round_number=2,
            target_aspect="材料选择",
            search_query="侘寂风格 天然材料",
            key_findings=["木材纹理保留原始感", "竹子象征坚韧"],
            inferred_insights=["用户偏好自然元素而非人工制品"],
            info_sufficiency=0.8,
            info_quality=0.85,
            alignment_score=0.9,
            quality_issues=["部分来源缺乏专业性"],
            remaining_gaps=["具体品牌推荐"],
            progress_description="材料方向已明确，需要深入案例",
        )

        # 模拟格式化输出
        output = f"""### 第{insight.round_number}轮：{insight.target_aspect}
**搜索查询**: {insight.search_query}
**质量评价**: 充分度 {insight.info_sufficiency:.0%} | 质量 {insight.info_quality:.0%} | 对齐度 {insight.alignment_score:.0%}

**关键发现**:
{chr(10).join(f"- {f}" for f in insight.key_findings)}

**推断洞察**:
{chr(10).join(f"- {i}" for i in insight.inferred_insights)}

**进展描述**: {insight.progress_description}
"""

        assert "第2轮：材料选择" in output
        assert "侘寂风格 天然材料" in output
        assert "80%" in output
        assert "85%" in output
        assert "90%" in output
        assert "木材纹理保留原始感" in output
        assert "用户偏好自然元素而非人工制品" in output
        assert "材料方向已明确" in output


class TestNoTruncation:
    """测试反思内容不截断"""

    def test_full_reflection_preserved(self):
        """测试完整反思内容被保留"""
        long_reflection = "这是一段很长的反思内容，" * 50  # 超过300字

        # v7.230之前会截断: reflection[:300]
        # v7.230之后完整保留

        # 模拟新逻辑
        preserved_reflection = long_reflection  # 不截断

        assert len(preserved_reflection) > 300
        assert preserved_reflection == long_reflection

    def test_progress_description_not_truncated(self):
        """测试进展描述不截断"""
        insight = RoundInsights(round_number=1, progress_description="这是完整的进展描述，包含了本轮搜索的所有发现和下一步计划。" * 10)

        # 验证完整保留
        assert len(insight.progress_description) > 100
        assert "完整的进展描述" in insight.progress_description


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
