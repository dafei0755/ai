"""
v7.138 Phase 2: LLM维度推荐器 - 单元测试

测试LLM维度推荐器的核心功能：
1. LLM推荐器初始化和环境变量控制
2. Prompt构建（system_prompt和user_prompt）
3. JSON解析（支持Markdown代码块）
4. 必选维度验证和自动补充
5. 降级策略（配置缺失、LLM失败）
6. 集成测试（DimensionSelector调用LLM推荐器）
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
import yaml

# 设置环境变量（必须在导入LLMDimensionRecommender之前）
os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "true"

from intelligent_project_analyzer.services.dimension_selector import DimensionSelector
from intelligent_project_analyzer.services.llm_dimension_recommender import LLMDimensionRecommender


class TestLLMDimensionRecommenderInitialization:
    """测试LLM维度推荐器的初始化和配置加载"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        recommender1 = LLMDimensionRecommender()
        recommender2 = LLMDimensionRecommender()
        assert recommender1 is recommender2, "LLMDimensionRecommender应该是单例"

    def test_environment_variable_enabled(self):
        """测试环境变量控制 - 启用"""
        os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "true"
        recommender = LLMDimensionRecommender()
        assert recommender.enabled is True, "环境变量为true时应启用"

    def test_environment_variable_disabled(self):
        """测试环境变量控制 - 禁用"""
        os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "false"
        # 重置单例
        LLMDimensionRecommender._instance = None
        recommender = LLMDimensionRecommender()
        assert recommender.enabled is False, "环境变量为false时应禁用"
        # 恢复环境变量
        os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "true"

    def test_config_loading_success(self):
        """测试配置文件加载成功"""
        recommender = LLMDimensionRecommender()
        assert recommender._prompt_config is not None, "Prompt配置应加载成功"
        assert "system_prompt" in recommender._prompt_config, "配置应包含system_prompt"
        assert "user_prompt" in recommender._prompt_config, "配置应包含user_prompt"
        assert "config" in recommender._prompt_config, "配置应包含config"

    def test_config_loading_failure_degradation(self):
        """测试配置文件加载失败时的降级策略"""
        # 保存当前状态
        original_instance = LLMDimensionRecommender._instance
        original_prompt_config = LLMDimensionRecommender._prompt_config

        try:
            with patch("pathlib.Path.exists", return_value=False):
                LLMDimensionRecommender._instance = None
                LLMDimensionRecommender._prompt_config = None
                recommender = LLMDimensionRecommender()
                # 配置缺失时，recommend_dimensions应返回None
                result = recommender.recommend_dimensions(
                    project_type="personal_residential",
                    user_input="新中式住宅",
                    all_dimensions={"budget_priority": {"name": "预算优先级", "default_value": 50}},
                    required_dimensions=["budget_priority"],
                    confirmed_tasks=[],
                    gap_filling_answers={},
                )
                assert result is None, "配置缺失时应返回None（降级）"
        finally:
            # 恢复原状态
            LLMDimensionRecommender._instance = original_instance
            LLMDimensionRecommender._prompt_config = original_prompt_config


class TestPromptConstruction:
    """测试Prompt构建功能"""

    def setup_method(self):
        """测试前初始化"""
        self.recommender = LLMDimensionRecommender()
        self.dimensions_config = self._load_dimensions_config()

    def _load_dimensions_config(self) -> Dict[str, Any]:
        """加载维度配置"""
        config_path = (
            Path(__file__).parent.parent
            / "intelligent_project_analyzer"
            / "config"
            / "prompts"
            / "radar_dimensions.yaml"
        )
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_build_system_prompt(self):
        """测试system_prompt构建"""
        dimensions = self.dimensions_config.get("dimensions", {})
        assert len(dimensions) > 0, "维度库不应为空"

        system_prompt = self.recommender._build_system_prompt(dimensions)
        assert system_prompt is not None, "system_prompt不应为None"
        assert len(system_prompt) > 0, "system_prompt不应为空"
        # 检查至少包含部分维度ID
        assert "budget_priority" in system_prompt, "system_prompt应包含维度库说明"

    def test_build_user_prompt(self):
        """测试user_prompt构建"""
        user_prompt = self.recommender._build_user_prompt(
            project_type="personal_residential",
            user_input="新中式住宅，注重文化传承和现代舒适",
            required_dimensions=["budget_priority", "space_flexibility"],
            confirmed_tasks=[
                {"task_id": "cultural_depth", "name": "文化深度设计", "priority": "high"},
                {"task_id": "storage_optimization", "name": "收纳优化", "priority": "medium"},
            ],
            gap_filling_answers={
                "question_1": "预算适中，约150万",
                "question_2": "家庭成员4人，三代同堂",
            },
            min_dimensions=9,
            max_dimensions=12,
        )
        assert user_prompt is not None, "user_prompt不应为None"
        assert "personal_residential" in user_prompt, "user_prompt应包含项目类型"
        assert "新中式住宅" in user_prompt, "user_prompt应包含用户输入"
        assert "budget_priority" in user_prompt, "user_prompt应包含必选维度"
        assert "文化深度设计" in user_prompt, "user_prompt应包含任务列表"
        assert "预算适中" in user_prompt, "user_prompt应包含问卷答案"

    def test_build_tasks_summary(self):
        """测试任务列表摘要构建"""
        tasks = [
            {"task_id": "storage_optimization", "name": "收纳优化", "priority": "high"},
            {"task_id": "smart_home", "name": "智能家居集成", "priority": "medium"},
        ]
        summary = self.recommender._build_tasks_summary(tasks)
        assert summary is not None, "任务摘要不应为None"
        assert "收纳优化" in summary, "任务摘要应包含任务名称"
        assert "high" in summary, "任务摘要应包含优先级"

    def test_build_answers_summary(self):
        """测试答案摘要构建"""
        answers = {
            "question_1": "预算约200万",
            "question_2": "家庭成员5人",
        }
        summary = self.recommender._build_answers_summary(answers)
        assert summary is not None, "答案摘要不应为None"
        assert "预算约200万" in summary, "答案摘要应包含答案内容"
        assert "question_1" in summary, "答案摘要应包含问题ID"


class TestJSONParsing:
    """测试JSON解析功能"""

    def setup_method(self):
        """测试前初始化"""
        self.recommender = LLMDimensionRecommender()

    def test_extract_json_from_plain_json(self):
        """测试从纯JSON文本中提取JSON"""
        json_text = '{"key": "value"}'
        extracted = self.recommender._extract_json(json_text)
        assert extracted == '{"key": "value"}', "应正确提取纯JSON（返回字符串）"
        # 验证可以被json.loads解析
        parsed = json.loads(extracted)
        assert parsed == {"key": "value"}, "提取的JSON应可解析"

    def test_extract_json_from_markdown_code_block(self):
        """测试从Markdown代码块中提取JSON"""
        json_text = """```json
{
    "recommended_dimensions": [
        {"dimension_id": "budget_priority", "default_value": 70}
    ]
}
```"""
        extracted = self.recommender._extract_json(json_text)
        assert extracted is not None, "应成功提取JSON"
        # _extract_json返回字符串，需要json.loads解析
        parsed = json.loads(extracted)
        assert "recommended_dimensions" in parsed, "应包含推荐维度"
        assert parsed["recommended_dimensions"][0]["dimension_id"] == "budget_priority"

    def test_extract_json_from_plain_markdown_code_block(self):
        """测试从无语言标记的Markdown代码块中提取JSON"""
        json_text = """```
{
    "recommended_dimensions": []
}
```"""
        extracted = self.recommender._extract_json(json_text)
        assert extracted is not None, "应成功提取JSON"
        assert "recommended_dimensions" in extracted

    def test_extract_json_invalid_format(self):
        """测试无效JSON格式"""
        json_text = "This is not JSON"
        extracted = self.recommender._extract_json(json_text)
        # _extract_json会返回原文本，由_parse_llm_response处理JSON解析错误
        assert extracted == "This is not JSON", "无效JSON返回原文本"

    def test_parse_llm_response_valid(self):
        """测试解析有效的LLM响应"""
        llm_response = {
            "recommended_dimensions": [
                {"dimension_id": "cultural_axis", "default_value": 80},
                {"dimension_id": "budget_priority", "default_value": 60},
            ],
            "reasoning": "新中式设计强调文化传承",
            "confidence": "high",
        }
        all_dimensions = {
            "cultural_axis": {"name": "文化轴", "default_value": 50},
            "budget_priority": {"name": "预算优先级", "default_value": 50},
        }
        result = self.recommender._parse_llm_response(
            json.dumps(llm_response),
            all_dimensions=all_dimensions,
            required_dimensions=["budget_priority"],
        )
        assert result is not None, "应成功解析响应"
        assert len(result["recommended_dimensions"]) == 2, "应包含2个推荐维度"
        assert result["confidence"] == "high"

    def test_parse_llm_response_missing_required_dimensions(self):
        """测试自动补充遗漏的必选维度"""
        llm_response = {
            "recommended_dimensions": [
                {"dimension_id": "cultural_axis", "default_value": 80},
            ],
            "reasoning": "Test",
            "confidence": "medium",
        }
        all_dimensions = {
            "cultural_axis": {"name": "文化轴", "default_value": 50},
            "budget_priority": {"name": "预算优先级", "default_value": 50},
            "space_flexibility": {"name": "空间灵活性", "default_value": 50},
        }
        result = self.recommender._parse_llm_response(
            json.dumps(llm_response),
            all_dimensions=all_dimensions,
            required_dimensions=["budget_priority", "space_flexibility"],
        )
        assert result is not None, "应成功解析响应"
        # 应自动补充2个遗漏的必选维度
        dimension_ids = [d["dimension_id"] for d in result["recommended_dimensions"]]
        assert "budget_priority" in dimension_ids, "应自动补充budget_priority"
        assert "space_flexibility" in dimension_ids, "应自动补充space_flexibility"

    def test_parse_llm_response_invalid_dimension_id(self):
        """测试过滤无效的维度ID"""
        llm_response = {
            "recommended_dimensions": [
                {"dimension_id": "cultural_axis", "default_value": 80},
                {"dimension_id": "invalid_dimension_xxx", "default_value": 50},
            ],
            "reasoning": "Test",
            "confidence": "low",
        }
        all_dimensions = {
            "cultural_axis": {"name": "文化轴", "default_value": 50},
        }
        result = self.recommender._parse_llm_response(
            json.dumps(llm_response),
            all_dimensions=all_dimensions,
            required_dimensions=[],
        )
        assert result is not None, "应成功解析响应"
        # 应过滤掉无效维度ID
        dimension_ids = [d["dimension_id"] for d in result["recommended_dimensions"]]
        assert "invalid_dimension_xxx" not in dimension_ids, "应过滤无效维度ID"


class TestDegradationStrategies:
    """测试降级策略"""

    def setup_method(self):
        """测试前初始化"""
        self.recommender = LLMDimensionRecommender()

    @patch("intelligent_project_analyzer.services.llm_dimension_recommender.get_llm")
    def test_llm_call_failure_returns_none(self, mock_get_llm):
        """测试LLM调用失败时返回None"""
        # Mock LLM抛出异常
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM调用失败")
        mock_get_llm.return_value = mock_llm

        result = self.recommender.recommend_dimensions(
            project_type="personal_residential",
            user_input="测试输入",
            all_dimensions={"budget_priority": {"name": "预算优先级", "default_value": 50}},
            required_dimensions=["budget_priority"],
            confirmed_tasks=[],
            gap_filling_answers={},
        )
        assert result is None, "LLM调用失败时应返回None（降级）"

    def test_disabled_recommender_returns_none(self):
        """测试禁用推荐器时返回None"""
        os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "false"
        LLMDimensionRecommender._instance = None
        recommender = LLMDimensionRecommender()

        result = recommender.recommend_dimensions(
            project_type="personal_residential",
            user_input="测试输入",
            all_dimensions={"budget_priority": {"name": "预算优先级", "default_value": 50}},
            required_dimensions=["budget_priority"],
            confirmed_tasks=[],
            gap_filling_answers={},
        )
        assert result is None, "禁用推荐器时应返回None"
        # 恢复环境变量
        os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "true"


class TestIntegrationWithDimensionSelector:
    """测试与DimensionSelector的集成"""

    def setup_method(self):
        """测试前初始化"""
        self.selector = DimensionSelector()

    @patch("intelligent_project_analyzer.services.llm_dimension_recommender.get_llm")
    def test_dimension_selector_calls_llm_recommender(self, mock_get_llm):
        """测试DimensionSelector调用LLM推荐器"""
        # Mock LLM返回有效推荐
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "recommended_dimensions": [
                    {"dimension_id": "cultural_axis", "default_value": 75},
                    {"dimension_id": "budget_priority", "default_value": 65},
                ],
                "reasoning": "新中式设计强调文化传承和成本控制",
                "confidence": "high",
            }
        )
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # 启用LLM推荐器
        os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "true"
        LLMDimensionRecommender._instance = None
        DimensionSelector._llm_recommender = None
        DimensionSelector._instance = None
        selector = DimensionSelector()

        result = selector.select_for_project(
            project_type="personal_residential",
            user_input="新中式住宅，注重文化传承",
            confirmed_tasks=[{"task_id": "cultural_depth", "name": "文化深度设计", "priority": "high"}],
            gap_filling_answers={"question_1": "预算150万"},
        )

        assert result is not None, "应返回结果"
        # v7.139返回格式：{dimensions, conflicts, adjustment_suggestions}
        assert "dimensions" in result, "应包含dimensions字段"
        dimensions = result["dimensions"]
        assert len(dimensions) >= 9, "维度数量应>=9"
        # 验证LLM推荐的维度是否包含在结果中
        dimension_ids = [d["dimension_id"] for d in dimensions]
        # 注意：cultural_axis可能已经包含在required/recommended中
        assert any(d["dimension_id"] == "budget_priority" for d in dimensions), "应包含LLM推荐的budget_priority"

    def test_dimension_selector_disabled_llm_recommender(self):
        """测试禁用LLM推荐器时的降级行为"""
        # 禁用LLM推荐器
        os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "false"
        LLMDimensionRecommender._instance = None
        DimensionSelector._llm_recommender = None
        DimensionSelector._instance = None
        selector = DimensionSelector()

        result = selector.select_for_project(
            project_type="personal_residential",
            user_input="新中式住宅",
            confirmed_tasks=[],
            gap_filling_answers={},
        )

        assert result is not None, "禁用LLM时应使用规则引擎"
        # v7.139返回格式：{dimensions, conflicts, adjustment_suggestions}
        assert "dimensions" in result, "应包含dimensions字段"
        dimensions = result["dimensions"]
        assert len(dimensions) >= 9, "维度数量应>=9"
        # 恢复环境变量
        os.environ["ENABLE_LLM_DIMENSION_RECOMMENDER"] = "true"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
