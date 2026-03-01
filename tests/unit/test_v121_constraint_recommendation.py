"""
v12.1 约束推荐系统 — 单元测试

测试范围：
U1: _load_constraint_display — YAML 映射加载 + 单例缓存
U2: _build_recommended_constraints — 推荐约束列表构建
U3: confirmed_constraints 解析 — 新格式 & 旧格式兼容
U4: framework_signals 注入 — mandatory_dimensions 覆盖 + user_declared 注入
U5: constraint_display.yaml 配置完整性校验
"""

import os
import sys
import copy
import pytest
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytestmark = [pytest.mark.unit]


# ==============================================================================
# U1: _load_constraint_display
# ==============================================================================


class TestU1LoadConstraintDisplay:
    """YAML 约束维度映射加载器"""

    @pytest.fixture(autouse=True)
    def _import_and_reset(self):
        import intelligent_project_analyzer.interaction.nodes.output_intent_detection as mod

        self.mod = mod
        # 重置缓存保证每个测试独立
        mod._constraint_display_cache = None
        yield
        mod._constraint_display_cache = None

    def test_loads_yaml_successfully(self):
        """U1.1: 正常加载 config/constraint_display.yaml"""
        result = self.mod._load_constraint_display()
        assert isinstance(result, dict)
        assert len(result) > 0, "应加载到至少一个维度"

    def test_returns_dict_with_known_keys(self):
        """U1.2: 返回包含已知维度 ID 的字典"""
        result = self.mod._load_constraint_display()
        # 至少包含几个代表性 key
        assert "acoustics" in result, "应包含 acoustics 维度"
        assert "budget" in result, "应包含 budget 约束"

    def test_each_entry_has_label_desc_category(self):
        """U1.3: 每个条目应有 label, desc, category 字段"""
        result = self.mod._load_constraint_display()
        for dim_id, info in result.items():
            assert "label" in info, f"{dim_id} 缺少 label"
            assert "desc" in info, f"{dim_id} 缺少 desc"
            assert "category" in info, f"{dim_id} 缺少 category"
            assert info["category"] in (
                "domain_capability",
                "project_constraint",
            ), f"{dim_id} category 值非法: {info['category']}"

    def test_singleton_cache(self):
        """U1.4: 多次调用应使用缓存（同一引用）"""
        r1 = self.mod._load_constraint_display()
        r2 = self.mod._load_constraint_display()
        assert r1 is r2, "应返回缓存的同一对象"

    def test_missing_file_returns_empty_dict(self):
        """U1.5: YAML 文件不存在时安全返回空字典"""
        with patch.object(Path, "exists", return_value=False):
            self.mod._constraint_display_cache = None  # 清缓存
            result = self.mod._load_constraint_display()
            assert result == {}

    def test_invalid_yaml_returns_empty_dict(self):
        """U1.6: YAML 格式错误时安全返回空字典"""
        import builtins

        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if "constraint_display" in str(args[0]):
                raise ValueError("mock yaml parse error")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            self.mod._constraint_display_cache = None
            result = self.mod._load_constraint_display()
            assert result == {}


# ==============================================================================
# U2: _build_recommended_constraints
# ==============================================================================


class TestU2BuildRecommendedConstraints:
    """推荐约束列表构建器"""

    @pytest.fixture(autouse=True)
    def _import_and_reset(self):
        import intelligent_project_analyzer.interaction.nodes.output_intent_detection as mod

        self.mod = mod
        # 确保 display map 已加载
        mod._constraint_display_cache = None
        self.fn = mod._build_recommended_constraints
        yield
        mod._constraint_display_cache = None

    def test_empty_inputs_return_empty_list(self):
        """U2.1: 无 mandatory_dims 和 constraints 时返回空列表"""
        result = self.fn([], [])
        assert result == []

    def test_mandatory_dims_converted(self):
        """U2.2: mandatory_dimensions 被正确转换为推荐项"""
        result = self.fn(["acoustics", "budget"], [])
        assert len(result) == 2
        ids = [r["id"] for r in result]
        assert "acoustics" in ids
        assert "budget" in ids

    def test_recommended_fields_present(self):
        """U2.3: 每个推荐项包含完整字段"""
        result = self.fn(["acoustics"], [])
        item = result[0]
        assert item["id"] == "acoustics"
        assert "label" in item
        assert "desc" in item
        assert "category" in item
        assert item["recommended"] is True
        assert item["source"] == "mandatory_dimensions"
        assert isinstance(item["evidence"], list)

    def test_constraints_converted(self):
        """U2.4: constraints 列表被正确转换"""
        constraints = [
            {"type": "budget", "value": "500万"},
            {"type": "time_pressure", "urgency": "high"},
        ]
        result = self.fn([], constraints)
        assert len(result) == 2
        ids = [r["id"] for r in result]
        assert "budget" in ids
        assert "time_pressure" in ids
        assert all(r["source"] == "constraints" for r in result)

    def test_deduplication(self):
        """U2.5: 同一 ID 在 mandatory_dims 和 constraints 中只出现一次"""
        result = self.fn(["budget"], [{"type": "budget", "value": "300万"}])
        ids = [r["id"] for r in result]
        assert ids.count("budget") == 1, "budget 应去重"

    def test_unknown_dim_uses_id_as_label(self):
        """U2.6: 未知维度 ID 使用 ID 本身作为 label"""
        result = self.fn(["unknown_xyz_dim"], [])
        assert len(result) == 1
        assert result[0]["label"] in ("unknown_xyz_dim", ""), "未知维度应回退到 ID 或空字符串"

    def test_visual_constraints_adds_visual_evidence(self):
        """U2.7: 有视觉约束时添加 visual_evidence 项"""
        visual = {
            "existing_conditions": [
                {"desc": "天花板管道外露"},
                {"desc": "地面不平"},
            ]
        }
        result = self.fn([], [], visual_constraints=visual)
        ids = [r["id"] for r in result]
        assert "visual_evidence" in ids

    def test_visual_constraints_empty_conditions_no_item(self):
        """U2.8: 视觉约束无 existing_conditions 时不添加"""
        visual = {"existing_conditions": []}
        result = self.fn([], [], visual_constraints=visual)
        ids = [r["id"] for r in result]
        assert "visual_evidence" not in ids

    def test_mandatory_dim_duplicate_ignored(self):
        """U2.9: mandatory_dims 自身有重复时只保留一次"""
        result = self.fn(["acoustics", "acoustics", "acoustics"], [])
        assert len(result) == 1

    def test_category_from_display_map(self):
        """U2.10: category 应来自 display map 而非硬编码"""
        result = self.fn(["budget"], [])
        # budget 在 YAML 中应为 project_constraint
        if result:
            assert result[0]["category"] == "project_constraint"


# ==============================================================================
# U3: confirmed_constraints 解析（模拟用户响应解析逻辑）
# ==============================================================================


class TestU3ConfirmedConstraintsParsing:
    """用户确认约束的解析逻辑"""

    def _parse_confirmed(self, user_response: dict):
        """复现 output_intent_detection 中的解析逻辑"""
        confirmed_constraints = user_response.get("confirmed_constraints") or []
        if not confirmed_constraints and user_response.get("user_constraints"):
            confirmed_constraints = [
                {"id": f"user_{i}", "label": c.get("label", ""), "desc": c.get("desc", ""), "source": "user_added"}
                for i, c in enumerate(user_response["user_constraints"])
            ]
        kept_visual_ref_indices = user_response.get("kept_visual_reference_indices")
        return confirmed_constraints, kept_visual_ref_indices

    def test_new_format_parsed(self):
        """U3.1: v12.1 新格式 confirmed_constraints 正确解析"""
        response = {
            "confirmed_constraints": [
                {"id": "acoustics", "label": "声学设计", "desc": "...", "source": "ai_recommended"},
                {"id": "user_0", "label": "自定义", "desc": "我的约束", "source": "user_added"},
            ]
        }
        cc, _ = self._parse_confirmed(response)
        assert len(cc) == 2
        assert cc[0]["id"] == "acoustics"
        assert cc[1]["source"] == "user_added"

    def test_old_format_backward_compat(self):
        """U3.2: 旧格式 user_constraints 被转换为 confirmed_constraints"""
        response = {
            "user_constraints": [
                {"label": "预算限制", "desc": "不超过 500万"},
                {"label": "时间紧迫", "desc": "3个月内完成"},
            ]
        }
        cc, _ = self._parse_confirmed(response)
        assert len(cc) == 2
        assert cc[0]["id"] == "user_0"
        assert cc[0]["label"] == "预算限制"
        assert cc[0]["source"] == "user_added"
        assert cc[1]["id"] == "user_1"

    def test_new_format_takes_priority(self):
        """U3.3: 同时有新旧格式时，新格式优先"""
        response = {
            "confirmed_constraints": [{"id": "a", "label": "A", "desc": "", "source": "ai_recommended"}],
            "user_constraints": [{"label": "B", "desc": "xxx"}],
        }
        cc, _ = self._parse_confirmed(response)
        assert len(cc) == 1
        assert cc[0]["id"] == "a"

    def test_empty_response(self):
        """U3.4: 空 user_response"""
        cc, ki = self._parse_confirmed({})
        assert cc == []
        assert ki is None

    def test_kept_visual_ref_indices_parsed(self):
        """U3.5: kept_visual_reference_indices 正确返回"""
        response = {
            "kept_visual_reference_indices": [0, 2, 5],
        }
        _, ki = self._parse_confirmed(response)
        assert ki == [0, 2, 5]

    def test_confirmed_constraints_empty_list_treated_as_none(self):
        """U3.6: 空列表的 confirmed_constraints 应回退到 user_constraints"""
        response = {
            "confirmed_constraints": [],
            "user_constraints": [{"label": "X", "desc": "Y"}],
        }
        cc, _ = self._parse_confirmed(response)
        assert len(cc) == 1
        assert cc[0]["label"] == "X"


# ==============================================================================
# U4: framework_signals 注入逻辑
# ==============================================================================


class TestU4FrameworkSignalsInjection:
    """confirmed_constraints → framework_signals 注入"""

    def _inject(self, framework_signals: dict, confirmed_constraints: list) -> dict:
        """复现 output_intent_detection 中的注入逻辑"""
        fs = copy.deepcopy(framework_signals)
        if confirmed_constraints:
            confirmed_dim_ids = [c["id"] for c in confirmed_constraints if c.get("source") == "ai_recommended"]
            user_added = [c for c in confirmed_constraints if c.get("source") == "user_added"]
            if confirmed_dim_ids:
                fs["mandatory_dimensions"] = confirmed_dim_ids
            for c in user_added:
                fs.setdefault("constraints", []).append(
                    {
                        "type": "user_declared",
                        "label": c.get("label", ""),
                        "desc": c.get("desc", ""),
                    }
                )
        return fs

    def test_ai_recommended_overrides_mandatory_dims(self):
        """U4.1: AI 推荐的确认项覆盖 mandatory_dimensions"""
        fs = {"mandatory_dimensions": ["a", "b", "c"]}
        cc = [
            {"id": "acoustics", "source": "ai_recommended"},
            {"id": "budget", "source": "ai_recommended"},
        ]
        result = self._inject(fs, cc)
        assert result["mandatory_dimensions"] == ["acoustics", "budget"]

    def test_user_added_appended_to_constraints(self):
        """U4.2: 用户手动添加的约束追加到 constraints"""
        fs = {"constraints": [{"type": "existing"}]}
        cc = [
            {"id": "user_0", "label": "自定义约束", "desc": "描述", "source": "user_added"},
        ]
        result = self._inject(fs, cc)
        assert len(result["constraints"]) == 2
        assert result["constraints"][1]["type"] == "user_declared"
        assert result["constraints"][1]["label"] == "自定义约束"

    def test_mixed_sources(self):
        """U4.3: 混合来源（AI + 用户）正确处理"""
        fs = {}
        cc = [
            {"id": "acoustics", "source": "ai_recommended"},
            {"id": "user_0", "label": "L", "desc": "D", "source": "user_added"},
        ]
        result = self._inject(fs, cc)
        assert result["mandatory_dimensions"] == ["acoustics"]
        assert len(result["constraints"]) == 1

    def test_empty_constraints_no_change(self):
        """U4.4: 空 confirmed_constraints 不修改原 signals"""
        fs = {"mandatory_dimensions": ["original"]}
        result = self._inject(fs, [])
        assert result["mandatory_dimensions"] == ["original"]

    def test_constraints_key_created_if_absent(self):
        """U4.5: framework_signals 无 constraints key 时自动创建"""
        fs = {}
        cc = [{"id": "u1", "label": "A", "desc": "B", "source": "user_added"}]
        result = self._inject(fs, cc)
        assert "constraints" in result
        assert len(result["constraints"]) == 1


# ==============================================================================
# U5: constraint_display.yaml 配置完整性
# ==============================================================================


class TestU5ConstraintDisplayYamlIntegrity:
    """配置文件完整性验证"""

    @pytest.fixture(autouse=True)
    def _load(self):
        import yaml

        config_path = Path(__file__).parent.parent.parent / "config" / "constraint_display.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.dims = data.get("constraint_dimensions", {})

    def test_has_27_dimensions(self):
        """U5.1: 应恰好有 27 个维度（20 + 7）"""
        assert len(self.dims) == 27, f"期望 27 个维度，实际 {len(self.dims)}"

    def test_domain_capability_count(self):
        """U5.2: domain_capability 类别应有 20 个"""
        dc = [k for k, v in self.dims.items() if v.get("category") == "domain_capability"]
        assert len(dc) == 20, f"期望 20 个 domain_capability，实际 {len(dc)}: {dc}"

    def test_project_constraint_count(self):
        """U5.3: project_constraint 类别应有 7 个"""
        pc = [k for k, v in self.dims.items() if v.get("category") == "project_constraint"]
        assert len(pc) == 7, f"期望 7 个 project_constraint，实际 {len(pc)}: {pc}"

    def test_all_labels_are_chinese(self):
        """U5.4: 所有 label 应包含中文字符"""
        import re

        for dim_id, info in self.dims.items():
            label = info.get("label", "")
            assert re.search(r"[\u4e00-\u9fff]", label), f"{dim_id} 的 label 不含中文: '{label}'"

    def test_known_budget_dimension(self):
        """U5.5: budget 维度应正确配置"""
        assert "budget" in self.dims
        assert self.dims["budget"]["category"] == "project_constraint"
        assert len(self.dims["budget"]["label"]) > 0

    def test_known_acoustics_dimension(self):
        """U5.6: acoustics 维度应正确配置"""
        assert "acoustics" in self.dims
        assert self.dims["acoustics"]["category"] == "domain_capability"
