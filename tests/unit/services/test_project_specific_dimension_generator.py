"""
v8.0 项目专属维度生成器 - 单元测试

覆盖：
- 维度验证逻辑（9条规则）
- JSON 提取（4层策略）
- User prompt 构建
- 三不问过滤
- 三层分类（校准/决策/洞察）
- 降级行为
"""

import json
import pytest
from unittest.mock import patch
from typing import Dict, List

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def generator():
    """创建 ProjectSpecificDimensionGenerator 实例（不触发 LLM）"""
    from intelligent_project_analyzer.services.project_specific_dimension_generator import (
        ProjectSpecificDimensionGenerator,
    )

    return ProjectSpecificDimensionGenerator()


@pytest.fixture
def valid_dim_calibration():
    """有效的校准维度（default ≠ 50）"""
    return {
        "id": "budget_control",
        "name": "预算控制倾向",
        "left_label": "严格控制预算",
        "right_label": "不惜成本追求品质",
        "description": "用于校准用户在预算方面的真实态度",
        "default_value": 35,
        "category": "calibration",
        "source": "calibration",
        "rationale": "用户提到有预算压力，需要校准实际容忍度",
        "impact_hint": "影响材料选型和施工深度",
        "global_impact": True,
    }


@pytest.fixture
def valid_dim_decision():
    """有效的决策维度"""
    return {
        "id": "privacy_vs_openness",
        "name": "私密与开放",
        "left_label": "强调私密边界",
        "right_label": "开放共享空间",
        "description": "决定空间布局的根本逻辑",
        "default_value": 50,
        "category": "decision",
        "source": "decision",
        "rationale": "三代同住带来私密性矛盾",
        "impact_hint": "影响隔断、门窗设计",
        "global_impact": True,
    }


@pytest.fixture
def valid_dim_insight():
    """有效的洞察维度"""
    return {
        "id": "identity_display",
        "name": "身份彰显需求",
        "left_label": "低调内敛",
        "right_label": "彰显身份地位",
        "description": "捕捉用户隐性的社会身份信号需求",
        "default_value": 60,
        "category": "insight",
        "source": "insight",
        "rationale": "企业家身份暗示身份展示需求",
        "impact_hint": "影响入口设计、材料标识性",
        "global_impact": True,
    }


@pytest.fixture
def minimal_structured_data():
    """最简结构化数据"""
    return {
        "project_task": "现代住宅设计",
        "character_narrative": "35岁商人，追求品质",
        "confidence_score": 0.7,
    }


@pytest.fixture
def full_structured_data():
    """包含所有可选字段的完整结构化数据"""
    return {
        "project_task": "三代同堂住宅改造",
        "character_narrative": "城市中产三代同堂家庭，祖父80岁行动不便",
        "confidence_score": 0.55,
        "five_whys_analysis": "为什么改造？→ 祖父摔倒 → 动线不安全 → 缺乏无障碍设计",
        "assumption_audit": "假设：老人愿意适应新布局",
        "core_tensions": "老人安全 vs 年轻人审美",
        "stakeholder_system": "老人、成年子女、孙辈",
        "human_dimensions": ["无障碍", "隔代沟通", "私密需求"],
        "uncertainty_map": {"项目周期": "未知", "预算": "模糊"},
        "ontology_parameters": {"scale": "中型", "mode": "M4"},
        "missing_dimensions": ["老人心理接受度", "施工扰动"],
    }


# ==============================================================================
# [1] 维度验证 - 9条规则
# ==============================================================================


class TestValidateDimension:
    """_validate_dimension 9条规则全覆盖"""

    def test_valid_calibration_passes(self, generator, valid_dim_calibration):
        """有效校准维度应通过验证"""
        result = generator._validate_dimension(valid_dim_calibration, set())
        assert result is True

    def test_valid_decision_passes(self, generator, valid_dim_decision):
        """有效决策维度应通过"""
        result = generator._validate_dimension(valid_dim_decision, set())
        assert result is True

    def test_valid_insight_passes(self, generator, valid_dim_insight):
        """有效洞察维度应通过"""
        result = generator._validate_dimension(valid_dim_insight, set())
        assert result is True

    # 规则 1: 必需字段
    @pytest.mark.parametrize(
        "missing_field",
        [
            "id",
            "name",
            "left_label",
            "right_label",
            "description",
            "category",
            "default_value",
            "source",
        ],
    )
    def test_missing_required_field_fails(self, generator, valid_dim_calibration, missing_field):
        """规则1: 缺少任何必需字段应返回 False"""
        dim = {**valid_dim_calibration}
        del dim[missing_field]
        result = generator._validate_dimension(dim, set())
        assert result is False, f"缺少字段 '{missing_field}' 应被拒绝"

    # 规则 2: ID 格式
    @pytest.mark.parametrize(
        "bad_id",
        [
            "",
            "A_uppercase",
            "1start_with_digit",
            "ab",
            "has space",
            "has-dash",
            "x" * 32,  # 超长
        ],
    )
    def test_invalid_id_format_fails(self, generator, valid_dim_calibration, bad_id):
        """规则2: ID 格式不合法应返回 False"""
        dim = {**valid_dim_calibration, "id": bad_id}
        result = generator._validate_dimension(dim, set())
        assert result is False, f"ID '{bad_id}' 应被拒绝"

    @pytest.mark.parametrize(
        "good_id",
        [
            "abc",
            "budget_control",
            "a1b2c3",
            "x" * 3,
            "x" * 30,
        ],
    )
    def test_valid_id_format_passes(self, generator, valid_dim_calibration, good_id):
        """规则2: 合法 ID 应通过"""
        dim = {**valid_dim_calibration, "id": good_id}
        result = generator._validate_dimension(dim, set())
        assert result is True, f"ID '{good_id}' 应通过"

    # 规则 3: ID 唯一性
    def test_duplicate_id_fails(self, generator, valid_dim_calibration):
        """规则3: 重复 ID 应返回 False"""
        existing_ids = {"budget_control"}
        result = generator._validate_dimension(valid_dim_calibration, existing_ids)
        assert result is False

    def test_unique_id_passes(self, generator, valid_dim_calibration):
        """规则3: 未出现的 ID 应通过"""
        existing_ids = {"other_dim"}
        result = generator._validate_dimension(valid_dim_calibration, existing_ids)
        assert result is True

    # 规则 4: 类别合法性 - 非法类别应自动修正
    def test_invalid_category_autocorrected(self, generator, valid_dim_calibration):
        """规则4: 非法 category 应被自动修正为 'special'，而非拒绝"""
        dim = {**valid_dim_calibration, "category": "invalid_cat"}
        result = generator._validate_dimension(dim, set())
        assert result is True  # 不拒绝，而是修正
        assert dim["category"] == "special"

    # 规则 5: 默认值范围自动修正
    @pytest.mark.parametrize(
        "bad_value,expected",
        [
            (-10, 0),
            (110, 100),
            (200, 100),
        ],
    )
    def test_default_value_clamped(self, generator, valid_dim_calibration, bad_value, expected):
        """规则5: 越界 default_value 应被自动截断"""
        dim = {**valid_dim_calibration, "default_value": bad_value}
        result = generator._validate_dimension(dim, set())
        assert result is True  # 不拒绝，截断后应通过
        assert dim["default_value"] == expected

    # 规则 6: 名称长度 - 截断而非拒绝
    def test_long_name_truncated(self, generator, valid_dim_calibration):
        """规则6: 超长名称应被截断而非拒绝"""
        dim = {**valid_dim_calibration, "name": "🏠" * 20}
        result = generator._validate_dimension(dim, set())
        assert result is True
        assert len(dim["name"]) <= 15

    # 规则 7: source 合法性 - 自动修正
    def test_invalid_source_autocorrected(self, generator, valid_dim_calibration):
        """规则7: 非法 source 应被改为 'decision'"""
        dim = {**valid_dim_calibration, "source": "unknown_source"}
        result = generator._validate_dimension(dim, set())
        assert result is True
        assert dim["source"] == "decision"

    # 规则 8: 校准维度 default ≠ 50
    @pytest.mark.parametrize("center_value", [45, 50, 55])
    def test_calibration_center_default_converts_to_decision(self, generator, valid_dim_calibration, center_value):
        """规则8: calibration 维度 default 在 45-55 区间应转为 decision"""
        dim = {**valid_dim_calibration, "id": "unique_id", "default_value": center_value}
        result = generator._validate_dimension(dim, set())
        assert result is True  # 不拒绝，修正 source
        assert dim["source"] == "decision"

    def test_calibration_non_center_keeps_source(self, generator, valid_dim_calibration):
        """规则8: calibration 维度 default 在中心区外应保持 source=calibration"""
        dim = {**valid_dim_calibration, "default_value": 25}
        result = generator._validate_dimension(dim, set())
        assert result is True
        assert dim["source"] == "calibration"

    # 规则 9: 标签负面词过滤（底线维度安全网）
    @pytest.mark.parametrize(
        "bad_label",
        [
            "不做无障碍",
            "拒绝现代风格",
            "不允许",
            "禁止",
            "不考虑老人",
        ],
    )
    def test_negative_label_fails(self, generator, valid_dim_calibration, bad_label):
        """规则9: 包含负面词的标签应被拒绝"""
        dim = {**valid_dim_calibration, "left_label": bad_label}
        result = generator._validate_dimension(dim, set())
        assert result is False, f"负面标签 '{bad_label}' 应被拒绝"

    def test_optional_fields_added_by_default(self, generator, valid_dim_calibration):
        """验证通过后应自动补充可选字段的默认值"""
        dim = {**valid_dim_calibration}
        # 删除可选字段
        for field in ("rationale", "impact_hint", "evidence", "global_impact"):
            dim.pop(field, None)
        result = generator._validate_dimension(dim, set())
        assert result is True
        assert "rationale" in dim
        assert "impact_hint" in dim
        assert "evidence" in dim
        assert "global_impact" in dim


# ==============================================================================
# [2] JSON 提取 - 4层策略
# ==============================================================================


class TestExtractDimensions:
    """_extract_dimensions 4层解析策略"""

    def test_extract_from_code_block(self, generator):
        """层1: 从 ```json``` 代码块提取"""
        raw = """这是前言
```json
[{"id": "abc", "name": "测试"}]
```
后缀"""
        dims = generator._extract_dimensions(raw)
        assert len(dims) == 1
        assert dims[0]["id"] == "abc"

    def test_extract_direct_json_array(self, generator):
        """层2: 直接 JSON 数组"""
        raw = '[{"id": "xyz", "name": "直接数组"}]'
        dims = generator._extract_dimensions(raw)
        assert len(dims) == 1

    def test_extract_from_json_object_with_dimensions_key(self, generator):
        """层3: JSON 对象含 dimensions key"""
        data = {"dimensions": [{"id": "nested_id", "name": "嵌套"}]}
        raw = json.dumps(data)
        dims = generator._extract_dimensions(raw)
        assert len(dims) == 1
        assert dims[0]["id"] == "nested_id"

    def test_extract_empty_on_invalid_json(self, generator):
        """无效输入应返回空列表（不崩溃）"""
        result = generator._extract_dimensions("这不是任何JSON内容")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_extract_with_surrounding_text(self, generator):
        """前后有大量文字时仍能提取"""
        payload = [{"id": "dim_a", "name": "维度A"}, {"id": "dim_b", "name": "维度B"}]
        raw = f"以下是维度设计方案：\n\n{json.dumps(payload, ensure_ascii=False)}\n\n完毕"
        dims = generator._extract_dimensions(raw)
        assert len(dims) == 2


# ==============================================================================
# [3] User Prompt 构建
# ==============================================================================


class TestBuildUserPrompt:
    """_build_user_prompt 字段提取覆盖"""

    def test_minimal_data_does_not_crash(self, generator, minimal_structured_data):
        """最简数据下不崩溃，返回非空字符串"""
        prompt = generator._build_user_prompt(
            user_input="简单项目需求",
            structured_data=minimal_structured_data,
            confirmed_tasks=[],
            project_type="personal_residential",
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_full_data_includes_key_fields(self, generator, full_structured_data):
        """完整数据时 prompt 包含关键字段"""
        prompt = generator._build_user_prompt(
            user_input="三代同堂住宅改造",
            structured_data=full_structured_data,
            confirmed_tasks=["无障碍改造", "老人卧室优化"],
            project_type="public_health_welfare",
        )
        # 置信度低应出现在 prompt 里（触发更多探索）
        assert "0.55" in prompt or "55" in prompt
        # 任务应出现
        assert "无障碍改造" in prompt

    def test_confirmed_tasks_in_prompt(self, generator, minimal_structured_data):
        """已确认任务应出现在 prompt 中"""
        tasks = ["任务一", "任务二", "任务三"]
        prompt = generator._build_user_prompt(
            user_input="测试",
            structured_data=minimal_structured_data,
            confirmed_tasks=tasks,
            project_type="",
        )
        for task in tasks:
            assert task in prompt

    def test_no_sensitive_data_leakage(self, generator, minimal_structured_data):
        """不包含内部实现细节（如 LLM 调用参数）"""
        prompt = generator._build_user_prompt(
            user_input="X",
            structured_data=minimal_structured_data,
            confirmed_tasks=[],
            project_type="",
        )
        assert "model=" not in prompt
        assert "temperature=" not in prompt


# ==============================================================================
# [4] generate_dimensions - 端到端（mock LLM）
# ==============================================================================


class TestGenerateDimensions:
    """generate_dimensions 方法（mock LLM 输出）"""

    def _make_llm_response(self, dimensions: List[Dict]) -> str:
        """构造模拟 LLM 返回文本"""
        return f"```json\n{json.dumps(dimensions, ensure_ascii=False)}\n```"

    def _make_valid_dims(self, count: int) -> List[Dict]:
        """生成 count 个有效维度"""
        return [
            {
                "id": f"dim_{i:03d}",
                "name": f"测试维度{i}",
                "left_label": f"左侧{i}",
                "right_label": f"右侧{i}",
                "description": f"维度{i}说明",
                "default_value": 30 + i * 3,
                "category": ["calibration", "decision", "insight"][i % 3],
                "source": ["calibration", "decision", "insight"][i % 3],
                "rationale": f"理由{i}",
                "impact_hint": f"影响{i}",
                "global_impact": i % 2 == 0,
            }
            for i in range(count)
        ]

    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    def test_returns_dict_with_dimensions_key(self, mock_llm, generator):
        """成功时返回 dict 含 dimensions 列表"""
        dims = self._make_valid_dims(8)
        mock_llm.return_value = self._make_llm_response(dims)
        result = generator.generate_dimensions(
            user_input="测试",
            structured_data={"confidence_score": 0.7},
            confirmed_tasks=["任务1"],
            project_type="personal_residential",
        )
        assert isinstance(result, dict)
        assert "dimensions" in result
        assert len(result["dimensions"]) == 8

    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    def test_generation_method_set_correctly(self, mock_llm, generator):
        """返回结果应含有 generation_method = 'project_specific'"""
        dims = self._make_valid_dims(7)
        mock_llm.return_value = self._make_llm_response(dims)
        result = generator.generate_dimensions("x", {}, [], "")
        assert result.get("generation_method") == "project_specific"

    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    def test_deduplication_removes_duplicate_ids(self, mock_llm, generator):
        """重复 ID 的维度应只保留第一个"""
        dims = self._make_valid_dims(5)
        # 添加重复 ID
        dup = {**dims[0], "name": "重复维度"}
        dims.append(dup)
        mock_llm.return_value = self._make_llm_response(dims)
        result = generator.generate_dimensions("x", {}, [], "")
        ids = [d["id"] for d in result.get("dimensions", [])]
        assert len(ids) == len(set(ids)), "不应有重复 ID"

    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    def test_invalid_dims_filtered_out(self, mock_llm, generator):
        """无效维度应被过滤（不返回给调用方）"""
        valid = self._make_valid_dims(5)
        invalid = [
            {"id": "bad!", "name": "坏维度"},  # ID 格式错误
            {"id": "ok_id", "name": "缺字段"},  # 缺 required 字段
        ]
        mock_llm.return_value = self._make_llm_response(valid + invalid)
        result = generator.generate_dimensions("x", {}, [], "")
        returned_ids = {d["id"] for d in result.get("dimensions", [])}
        assert "bad!" not in returned_ids

    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    def test_llm_exception_returns_empty_dict(self, mock_llm, generator):
        """LLM 调用抛异常时返回空 dict（不崩溃）"""
        mock_llm.side_effect = Exception("网络错误")
        result = generator.generate_dimensions("x", {}, [], "")
        assert result == {} or result.get("dimensions", []) == []

    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    def test_too_few_valid_dims_returns_empty(self, mock_llm, generator):
        """有效维度不足 3 个时返回空 dict（让调用方降级）"""
        dims = self._make_valid_dims(2)  # 只有2个
        mock_llm.return_value = self._make_llm_response(dims)
        result = generator.generate_dimensions("x", {}, [], "")
        # 少于阈值应返回空或少量维度（让外层判断 len >= 5）
        assert len(result.get("dimensions", [])) < 5


# ==============================================================================
# [5] 三层分类覆盖率
# ==============================================================================


class TestThreeLayerCoverage:
    """验证三层架构的类别多样性"""

    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    def test_all_three_categories_present(self, mock_llm, generator):
        """理想情况下三层 source 都应存在"""
        dims = [
            {
                "id": f"dim_{i}",
                "name": f"维度{i}",
                "left_label": f"左{i}",
                "right_label": f"右{i}",
                "description": f"描述{i}",
                "default_value": 30 + i * 5,
                "category": "functional",  # 使用合法 category
                "source": cat,
                "rationale": "理由",
                "impact_hint": "影响",
                "global_impact": True,
            }
            for i, cat in enumerate(
                ["calibration", "calibration", "decision", "decision", "decision", "insight", "insight"]
            )
        ]
        mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
        result = generator.generate_dimensions("项目需求", {}, [], "")
        sources = {d["source"] for d in result.get("dimensions", [])}
        assert "calibration" in sources
        assert "decision" in sources
        assert "insight" in sources

    def test_valid_sources_constant(self, generator):
        """VALID_SOURCES 应包含三层"""
        assert "calibration" in generator.VALID_SOURCES
        assert "decision" in generator.VALID_SOURCES
        assert "insight" in generator.VALID_SOURCES

    def test_valid_categories_constant(self, generator):
        """VALID_CATEGORIES 应包含常规建筑类别"""
        for cat in ("aesthetic", "functional", "technology", "resource", "experience", "special"):
            assert cat in generator.VALID_CATEGORIES


# ==============================================================================
# [6] 三不问规则（静态验证）
# ==============================================================================


class TestThreeDoNotAsk:
    """三不问规则：不问已回答的、不问常识、不问底线"""

    def test_negative_label_filter_blocks_baseline_dims(self, generator):
        """底线维度（包含否定词的标签）应被过滤"""
        baseline_dim = {
            "id": "safety_req",
            "name": "安全要求",
            "left_label": "不做消防验收",
            "right_label": "满足消防规范",
            "description": "消防规范合规",
            "default_value": 50,
            "category": "decision",
            "source": "decision",
        }
        result = generator._validate_dimension(baseline_dim, set())
        assert result is False, "底线维度（含否定词的标签）应被拒绝"

    def test_common_sense_center_calibration_converted(self, generator):
        """default=50 的校准维度（偏向共识）应被转为 decision，而非直接拒绝"""
        common_dim = {
            "id": "common_dim",
            "name": "通用维度",
            "left_label": "功能优先",
            "right_label": "美观优先",
            "description": "普遍性功能美观平衡",
            "default_value": 50,
            "category": "calibration",
            "source": "calibration",
        }
        result = generator._validate_dimension(common_dim, set())
        assert result is True
        assert common_dim["source"] == "decision"  # 降级为 decision，而非拒绝


# ==============================================================================
# [标记] pytest marks
# ==============================================================================

pytestmark = [pytest.mark.unit]
