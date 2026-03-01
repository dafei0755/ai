"""
测试维度提取器 (Test Dimension Extractor)

测试从专家输出中提取分析维度的功能。

版本: v3.0
创建日期: 2026-02-10
"""

import pytest
from intelligent_project_analyzer.learning.dimension_extractor import DimensionExtractor, ExtractedDimension


class TestDimensionExtractor:
    """测试维度提取器"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return DimensionExtractor(enable_llm=False)

    def test_initialization(self, extractor):
        """测试初始化"""
        assert extractor is not None
        assert extractor.enable_llm is False
        assert len(extractor.patterns) > 0

    def test_pattern_matching_how_questions(self, extractor):
        """测试识别"如何"问题"""
        text = """
        在设计住宅时，我们需要考虑：
        1. 如何平衡私密性与开放性？
        2. 如何让自然光充分进入室内？
        3. 如何设计灵活的空间布局？
        """

        matches = extractor._apply_pattern_matching(text)
        assert "how_questions" in matches
        assert len(matches["how_questions"]) == 3

    def test_pattern_matching_dimension_markers(self, extractor):
        """测试识别维度标记"""
        text = """
        从功能角度来看，需要考虑空间的可达性。
        从美学维度分析，色彩搭配至关重要。
        评估社交层面的互动需求。
        """

        matches = extractor._apply_pattern_matching(text)
        assert "dimension_marker" in matches
        assert len(matches["dimension_marker"]) >= 2

    def test_extract_dimension_name(self, extractor):
        """测试从问题中提取维度名称"""
        question = "如何平衡私密性与开放性？"
        name = extractor._extract_dimension_name_from_question(question)
        assert name is not None
        assert "平衡私密性" in name or "开放性" in name

    def test_extract_from_text_simple(self, extractor):
        """测试简单文本提取"""
        text = """
        在商业空间设计中，关键问题包括：

        1. 如何优化客流动线以提高转化率？
        商业空间的成功取决于顾客的移动路径设计。

        2. 如何营造独特的品牌氛围？
        空间应该传达品牌的核心价值观。
        """

        candidates = extractor.extract_from_text_sync(
            text=text, project_type="commercial_enterprise", expert_role="spatial_planner"
        )

        assert len(candidates) > 0
        assert all(isinstance(c, ExtractedDimension) for c in candidates)
        assert all(c.confidence >= 0.5 for c in candidates)

    def test_deduplicate_candidates(self, extractor):
        """测试候选维度去重"""
        candidates = [
            ExtractedDimension(
                name="空间流动性",
                category="spatial",
                description="测试",
                ask_yourself="如何？",
                examples="示例",
                confidence=0.8,
                source_context="",
                project_type="test",
            ),
            ExtractedDimension(
                name="空间流动性",  # 重复
                category="spatial",
                description="测试2",
                ask_yourself="如何？",
                examples="示例",
                confidence=0.7,
                source_context="",
                project_type="test",
            ),
        ]

        filtered = extractor._deduplicate_and_filter(candidates)
        assert len(filtered) == 1

    def test_score_candidates(self, extractor):
        """测试候选维度打分"""
        text = "空间流动性 是设计的核心。空间流动性 影响用户体验。空间流动性 需要仔细规划。"

        candidates = [
            ExtractedDimension(
                name="空间流动性",
                category="spatial",
                description="测试",
                ask_yourself="如何？",
                examples="示例",
                confidence=0.6,
                source_context="",
                project_type="test",
            )
        ]

        scored = extractor._score_candidates(candidates, text)
        # 出现3次，应该提升置信度
        assert scored[0].confidence > 0.6

    def test_to_yaml_format(self):
        """测试转换为YAML格式"""
        dim = ExtractedDimension(
            name="测试维度 (Test Dimension)",
            category="test_category",
            description="这是一个测试维度的描述。",
            ask_yourself="如何测试这个维度？",
            examples="示例1, 示例2, 示例3",
            confidence=0.85,
            source_context="test",
            project_type="test_type",
        )

        yaml_str = dim.to_yaml_format()
        assert "name:" in yaml_str
        assert "测试维度" in yaml_str
        assert "description:" in yaml_str
        assert "ask_yourself:" in yaml_str
        assert "examples:" in yaml_str
