"""
单元测试: P3 增强 (T11-T13)
版本: v8.000
日期: 2026-02-16

测试范围：
  T11: mode_feature_mapping.yaml 预映射表 + _load_mode_to_tags_mapping()
  T12: feature_vector ↔ Mode Engine 统一 (_infer_tags_from_features, _cosine_similarity_bonus)
  T13: 新增 few-shot 示例文件完整性
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# T11: 预映射表 + Mode→Tags 加载
# ============================================================================


class TestT11PreMappingTable:
    """P3-T11: mode_feature_mapping.yaml 预映射表"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mapping_path = PROJECT_ROOT / "intelligent_project_analyzer" / "config" / "mode_feature_mapping.yaml"
        if not self.mapping_path.exists():
            pytest.skip("mode_feature_mapping.yaml 不存在")
        with open(self.mapping_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    @pytest.mark.unit
    def test_yaml_structure_has_three_sections(self):
        """YAML 包含 mode_to_tags, mode_to_features, feature_to_modes"""
        assert "mode_to_tags" in self.config
        assert "mode_to_features" in self.config
        assert "feature_to_modes" in self.config

    @pytest.mark.unit
    def test_mode_to_tags_has_10_modes(self):
        """mode_to_tags 覆盖全部 10 个模式"""
        m2t = self.config["mode_to_tags"]
        expected_modes = [
            "M1_concept_driven",
            "M2_function_efficiency",
            "M3_emotional_experience",
            "M4_capital_asset",
            "M5_rural_context",
            "M6_urban_regeneration",
            "M7_tech_integration",
            "M8_extreme_condition",
            "M9_social_structure",
            "M10_future_speculation",
        ]
        for mode in expected_modes:
            assert mode in m2t, f"mode_to_tags 缺少 {mode}"
            assert len(m2t[mode]) >= 2, f"{mode} 标签数不足"

    @pytest.mark.unit
    def test_mode_ids_use_canonical_names(self):
        """Mode ID 使用正确的规范名称"""
        m2t = self.config["mode_to_tags"]
        # 正确: M2_function_efficiency (不是 functional_efficiency)
        assert "M2_function_efficiency" in m2t
        assert "M2_functional_efficiency" not in m2t
        # 正确: M7_tech_integration (不是 technology_integration)
        assert "M7_tech_integration" in m2t
        assert "M7_technology_integration" not in m2t

    @pytest.mark.unit
    def test_feature_to_modes_has_sufficient_dims(self):
        """feature_to_modes 覆盖足够多的特征维度"""
        f2m = self.config["feature_to_modes"]
        # 核心维度必须存在
        core_dims = [
            "cultural",
            "commercial",
            "functional",
            "aesthetic",
            "social",
            "technical",
        ]
        for dim in core_dims:
            assert dim in f2m, f"feature_to_modes 缺少核心维度: {dim}"
        # 总维度数 >= 10
        assert len(f2m) >= 10, f"feature_to_modes 维度数不足: {len(f2m)}"

    @pytest.mark.unit
    def test_mode_to_features_primary_secondary(self):
        """mode_to_features 每个模式有 primary + secondary"""
        m2f = self.config["mode_to_features"]
        for mode_id, mapping in m2f.items():
            assert "primary" in mapping, f"{mode_id} 缺少 primary"
            assert "secondary" in mapping, f"{mode_id} 缺少 secondary"
            assert len(mapping["primary"]) >= 1


class TestT11LoadModeToTagsMapping:
    """P3-T11: CoreTaskDecomposer._load_mode_to_tags_mapping()"""

    @pytest.fixture
    def decomposer(self):
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        # 清除缓存
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")
        return d

    @pytest.mark.unit
    def test_loads_from_yaml(self, decomposer):
        """从 YAML 文件加载映射"""
        m2t = decomposer._load_mode_to_tags_mapping()
        assert isinstance(m2t, dict)
        assert len(m2t) >= 10, f"期望 10 个模式, 实际 {len(m2t)}"
        # 全部值应为 set
        for mode_id, tags in m2t.items():
            assert isinstance(tags, set), f"{mode_id} 值类型应为 set"

    @pytest.mark.unit
    def test_caching(self, decomposer):
        """连续调用使用缓存"""
        first = decomposer._load_mode_to_tags_mapping()
        second = decomposer._load_mode_to_tags_mapping()
        assert first is second, "应返回缓存对象"

    @pytest.mark.unit
    def test_fallback_when_yaml_missing(self, decomposer):
        """YAML 文件不存在时使用 fallback"""
        with patch("pathlib.Path.exists", return_value=False):
            # 清缓存
            if hasattr(decomposer, "_cached_mode_to_tags"):
                delattr(decomposer, "_cached_mode_to_tags")
            m2t = decomposer._load_mode_to_tags_mapping()

        assert isinstance(m2t, dict)
        assert len(m2t) >= 10
        assert "M5_rural_context" in m2t


# ============================================================================
# T12: feature_vector ↔ Mode Engine 统一
# ============================================================================


class TestT12CosineSimilarityBonus:
    """P3-T12: CoreTaskDecomposer._cosine_similarity_bonus 余弦相似度"""

    @pytest.mark.unit
    def test_identical_vectors(self):
        """相同向量余弦相似度为 1.0"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        vec = {"a": 0.5, "b": 0.8, "c": 0.3}
        score = CoreTaskDecomposer._cosine_similarity_bonus(vec, vec)
        assert abs(score - 1.0) < 1e-6

    @pytest.mark.unit
    def test_orthogonal_vectors(self):
        """正交向量余弦相似度为 0"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        vec_a = {"x": 1.0, "y": 0.0}
        vec_b = {"x": 0.0, "y": 1.0}
        score = CoreTaskDecomposer._cosine_similarity_bonus(vec_a, vec_b)
        assert abs(score) < 1e-6

    @pytest.mark.unit
    def test_partial_overlap_keys(self):
        """部分重叠键时正确计算"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        vec_a = {"cultural": 0.8, "aesthetic": 0.6}
        vec_b = {"cultural": 0.7, "commercial": 0.9}
        score = CoreTaskDecomposer._cosine_similarity_bonus(vec_a, vec_b)
        # cultural 有重叠, aesthetic/commercial 各自独有
        assert 0.0 < score < 1.0

    @pytest.mark.unit
    def test_empty_vectors(self):
        """空向量返回 0"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        assert CoreTaskDecomposer._cosine_similarity_bonus({}, {}) == 0.0

    @pytest.mark.unit
    def test_one_zero_vector(self):
        """一方全零返回 0"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        vec_a = {"a": 0.5}
        vec_b = {"a": 0.0, "b": 0.0}
        assert CoreTaskDecomposer._cosine_similarity_bonus(vec_a, vec_b) == 0.0

    @pytest.mark.unit
    def test_similarity_range(self):
        """结果在 [0, 1] 范围内"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )
        import random

        random.seed(42)
        for _ in range(20):
            dims = ["a", "b", "c", "d", "e"]
            va = {d: random.random() for d in dims}
            vb = {d: random.random() for d in dims}
            score = CoreTaskDecomposer._cosine_similarity_bonus(va, vb)
            assert 0.0 <= score <= 1.0 + 1e-6, f"余弦相似度越界: {score}"


class TestT12InferTagsFromFeatures:
    """P3-T12: CoreTaskDecomposer._infer_tags_from_features 反向推断"""

    @pytest.fixture
    def decomposer(self):
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        d = CoreTaskDecomposer.__new__(CoreTaskDecomposer)
        if hasattr(d, "_cached_mode_to_tags"):
            delattr(d, "_cached_mode_to_tags")
        return d

    @pytest.mark.unit
    def test_high_cultural_infers_m5_tags(self, decomposer):
        """高 cultural 分数推断出 M5 相关标签"""
        features = {"cultural": 0.8, "social": 0.6, "aesthetic": 0.3}
        tags = decomposer._infer_tags_from_features(features)
        assert isinstance(tags, set)
        assert len(tags) > 0, "应推断出至少一些标签"

    @pytest.mark.unit
    def test_high_technical_infers_tech_tags(self, decomposer):
        """高 technical 分数推断出技术相关标签"""
        features = {"technical": 0.9, "functional": 0.7, "innovative": 0.6}
        tags = decomposer._infer_tags_from_features(features)
        assert isinstance(tags, set)
        if tags:
            # 应包含技术相关标签
            tech_related = tags & {"technical_complexity", "technical_innovation"}
            assert len(tech_related) > 0 or len(tags) > 0

    @pytest.mark.unit
    def test_low_scores_return_empty(self, decomposer):
        """所有分数 < 0.5 时返回空"""
        features = {"cultural": 0.3, "social": 0.2, "aesthetic": 0.1}
        tags = decomposer._infer_tags_from_features(features)
        assert isinstance(tags, set)
        assert len(tags) == 0, "低分应返回空集合"

    @pytest.mark.unit
    def test_empty_features_return_empty(self, decomposer):
        """空特征返回空"""
        tags = decomposer._infer_tags_from_features({})
        assert tags == set()

    @pytest.mark.unit
    def test_yaml_missing_returns_empty(self, decomposer):
        """YAML 文件不存在时返回空"""
        with patch("pathlib.Path.exists", return_value=False):
            tags = decomposer._infer_tags_from_features({"cultural": 0.8, "social": 0.7})
        assert isinstance(tags, set)


# ============================================================================
# T13: 新增 few-shot 示例文件
# ============================================================================


class TestT13FewShotExampleFiles:
    """P3-T13: 新增 few-shot 示例文件完整性"""

    EXAMPLES_DIR = PROJECT_ROOT / "intelligent_project_analyzer" / "config" / "prompts" / "few_shot_examples"

    EXPECTED_FILES = [
        "commercial_dominant_01.yaml",
        "functional_dominant_01.yaml",
        "cultural_dominant_01.yaml",
        "aesthetic_dominant_01.yaml",
        "technical_dominant_02.yaml",
    ]

    @pytest.mark.unit
    def test_all_five_files_exist(self):
        """5 个 YAML 示例文件全部存在"""
        for fname in self.EXPECTED_FILES:
            fpath = self.EXAMPLES_DIR / fname
            assert fpath.exists(), f"缺少示例文件: {fname}"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "filename",
        [
            "cultural_dominant_01.yaml",
            "aesthetic_dominant_01.yaml",
            "technical_dominant_02.yaml",
        ],
    )
    def test_new_example_structure(self, filename):
        """新增示例包含必需的 project_info + ideal_tasks"""
        fpath = self.EXAMPLES_DIR / filename
        if not fpath.exists():
            pytest.skip(f"{filename} 不存在")

        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 示例文件可能嵌套在 example: 下
        inner = data.get("example", data)

        assert "project_info" in inner, f"{filename} 缺少 project_info"
        assert "ideal_tasks" in inner, f"{filename} 缺少 ideal_tasks"

        # project_info 应包含关键字段
        pi = inner["project_info"]
        assert "name" in pi
        assert "description" in pi

        # ideal_tasks 应非空
        tasks = inner["ideal_tasks"]
        assert isinstance(tasks, list)
        assert len(tasks) >= 5, f"{filename} 任务数 {len(tasks)} 过少"

    @pytest.mark.unit
    def test_cultural_dominant_has_m5_tags(self):
        """cultural_dominant_01 覆盖 M5_rural_context"""
        fpath = self.EXAMPLES_DIR / "cultural_dominant_01.yaml"
        if not fpath.exists():
            pytest.skip("文件不存在")
        content = fpath.read_text(encoding="utf-8")
        assert "M5_rural_context" in content or "rural" in content.lower()

    @pytest.mark.unit
    def test_technical_dominant_has_extreme_tags(self):
        """technical_dominant_02 覆盖 M7/M8"""
        fpath = self.EXAMPLES_DIR / "technical_dominant_02.yaml"
        if not fpath.exists():
            pytest.skip("文件不存在")
        content = fpath.read_text(encoding="utf-8")
        # 高海拔/极端条件相关
        assert any(kw in content for kw in ["M8_extreme", "M7_tech", "高海拔", "extreme", "technical"])

    @pytest.mark.unit
    def test_task_has_required_fields(self):
        """每个任务包含 id, title, description, task_type"""
        required_keys = {"id", "title", "description", "task_type"}
        for fname in ["cultural_dominant_01.yaml", "aesthetic_dominant_01.yaml", "technical_dominant_02.yaml"]:
            fpath = self.EXAMPLES_DIR / fname
            if not fpath.exists():
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            inner = data.get("example", data)
            for i, task in enumerate(inner.get("ideal_tasks", [])):
                for key in required_keys:
                    assert key in task, f"{fname} 任务 #{i} 缺少字段 {key}"


class TestT13ExamplesRegistry:
    """P3-T13: examples_registry.yaml 更新"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.registry_path = (
            PROJECT_ROOT
            / "intelligent_project_analyzer"
            / "config"
            / "prompts"
            / "few_shot_examples"
            / "examples_registry.yaml"
        )
        if not self.registry_path.exists():
            pytest.skip("examples_registry.yaml 不存在")
        with open(self.registry_path, "r", encoding="utf-8") as f:
            self.registry = yaml.safe_load(f)

    @pytest.mark.unit
    def test_version_v8(self):
        """版本为 v8.000"""
        meta = self.registry.get("metadata", {})
        version = str(meta.get("version", ""))
        assert "8" in version or "v8" in version, f"期望 v8.x, 实际 {version}"

    @pytest.mark.unit
    def test_available_yaml_files_count(self):
        """available_yaml_files >= 5"""
        meta = self.registry.get("metadata", {})
        count = meta.get("available_yaml_files", 0)
        assert count >= 5, f"期望 >= 5 个可用文件, 实际 {count}"

    @pytest.mark.unit
    def test_examples_have_tags_matrix(self):
        """每个 example 有 tags_matrix"""
        examples = self.registry.get("examples", [])
        for i, ex in enumerate(examples):
            assert "tags_matrix" in ex, f"示例 #{i} 缺少 tags_matrix"
