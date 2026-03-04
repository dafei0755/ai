"""
单元测试: P1 知识层 (T5-T7b)
版本: v8.000
日期: 2026-02-16

测试范围：
  T5: sf/13_Evaluation_Matrix 内容完整性
  T6: sf/14_Output_Standards 内容完整性
  T7a: review_agents.yaml v2.3 评估矩阵集成
  T7b: result_aggregator.yaml v3.2 输出标准集成
"""

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# T5: 13_Evaluation_Matrix 内容完整性
# ============================================================================


class TestT5EvaluationMatrix:
    """P1-T5: sf/13_Evaluation_Matrix 文件完整性"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.filepath = PROJECT_ROOT / "sf" / "13_Evaluation_Matrix"
        if not self.filepath.exists():
            pytest.skip("sf/13_Evaluation_Matrix 文件不存在")
        self.content = self.filepath.read_text(encoding="utf-8")

    @pytest.mark.unit
    def test_file_exists_and_not_empty(self):
        """文件存在且内容不少于 400 行"""
        lines = self.content.split("\n")
        assert len(lines) >= 400, f"期望 >= 400 行，实际 {len(lines)} 行"

    @pytest.mark.unit
    def test_ten_evaluation_dimensions(self):
        """包含 10 个评估维度"""
        expected_dims = [
            "concept_integrity",
            "spatial_logic",
            "narrative_coherence",
            "material_fitness",
            "functional_efficiency",
            "technical_feasibility",
            "commercial_closure",
            "cultural_authenticity",
            "social_impact",
            "interdisciplinary_integration",
        ]
        for dim in expected_dims:
            assert dim in self.content, f"缺少评估维度: {dim}"

    @pytest.mark.unit
    def test_five_maturity_levels(self):
        """包含 L1-L5 成熟度等级"""
        for level in ["L1", "L2", "L3", "L4", "L5"]:
            assert level in self.content, f"缺少成熟度等级: {level}"

    @pytest.mark.unit
    def test_mode_evaluation_weights_yaml_block(self):
        """包含机器可读的 mode_evaluation_weights YAML 块"""
        assert "mode_evaluation_weights:" in self.content
        # 验证至少包含 5 个模式的权重
        import re

        modes_in_weights = re.findall(r"(M\d+_\w+):", self.content[self.content.index("mode_evaluation_weights:") :])
        assert len(modes_in_weights) >= 5, f"mode_evaluation_weights 中只找到 {len(modes_in_weights)} 个模式"


# ============================================================================
# T6: 14_Output_Standards 内容完整性
# ============================================================================


class TestT6OutputStandards:
    """P1-T6: sf/14_Output_Standards 文件完整性"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.filepath = PROJECT_ROOT / "sf" / "14_Output_Standards"
        if not self.filepath.exists():
            pytest.skip("sf/14_Output_Standards 文件不存在")
        self.content = self.filepath.read_text(encoding="utf-8")

    @pytest.mark.unit
    def test_file_exists_and_not_empty(self):
        """文件存在且内容不少于 250 行"""
        lines = self.content.split("\n")
        assert len(lines) >= 250, f"期望 >= 250 行，实际 {len(lines)} 行"

    @pytest.mark.unit
    def test_deliverable_types(self):
        """包含 T1-T5 交付物类型"""
        for t in ["T1", "T2", "T3", "T4", "T5"]:
            assert t in self.content, f"缺少交付物类型: {t}"

    @pytest.mark.unit
    def test_quality_floor_section(self):
        """包含质量底线 Q1-Q5"""
        for q in ["Q1", "Q2", "Q3", "Q4", "Q5"]:
            assert q in self.content, f"缺少质量底线: {q}"

    @pytest.mark.unit
    def test_mode_deliverable_mapping(self):
        """包含模式-交付物映射"""
        # 至少有几个模式ID出现
        import re

        mode_ids = re.findall(r"M\d+_\w+", self.content)
        assert len(mode_ids) >= 5, f"只找到 {len(mode_ids)} 个模式引用"


# ============================================================================
# T7a: review_agents.yaml 评估矩阵集成
# ============================================================================


class TestT7aReviewAgentsConfig:
    """P1-T7a: review_agents.yaml 包含评估矩阵集成配置"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.filepath = PROJECT_ROOT / "intelligent_project_analyzer" / "config" / "prompts" / "review_agents.yaml"
        if not self.filepath.exists():
            pytest.skip("review_agents.yaml 不存在")
        self.content = self.filepath.read_text(encoding="utf-8")

    @pytest.mark.unit
    def test_version_at_least_v2_3(self):
        """版本 >= v2.3"""
        assert "v2.3" in self.content or "v2.4" in self.content or "v3" in self.content

    @pytest.mark.unit
    def test_evaluation_matrix_integration_key(self):
        """包含 evaluation_matrix_integration 配置"""
        assert "evaluation_matrix_integration" in self.content


# ============================================================================
# T7b: result_aggregator.yaml 输出标准集成
# ============================================================================


class TestT7bResultAggregatorConfig:
    """P1-T7b: result_aggregator.yaml 包含输出标准集成配置"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.filepath = PROJECT_ROOT / "intelligent_project_analyzer" / "config" / "prompts" / "result_aggregator.yaml"
        if not self.filepath.exists():
            pytest.skip("result_aggregator.yaml 不存在")
        self.content = self.filepath.read_text(encoding="utf-8")

    @pytest.mark.unit
    def test_version_at_least_v3_2(self):
        """版本 >= v3.2"""
        assert "v3.2" in self.content or "v3.3" in self.content or "v4" in self.content

    @pytest.mark.unit
    def test_output_quality_standards_key(self):
        """包含 output_quality_standards 配置"""
        assert "output_quality_standards" in self.content
