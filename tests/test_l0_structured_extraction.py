"""
L0 结构化信息提取单元测试 - v7.205

测试 StructuredUserInfo 数据类和 L0 提取功能
"""
import json

import pytest


class TestStructuredUserInfo:
    """测试 StructuredUserInfo 数据类"""

    def test_import_structured_user_info(self):
        """验证 StructuredUserInfo 可以导入"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        assert StructuredUserInfo is not None

    def test_default_values(self):
        """测试默认值初始化"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        info = StructuredUserInfo()

        # 验证默认结构
        assert info.demographics["location"] == ""
        assert info.demographics["location_context"] == ""
        assert info.identity_tags == []
        assert info.lifestyle["hobbies"] == []
        assert info.project_context["type"] == ""
        assert info.preferences["style_references"] == []
        assert info.core_request["explicit_need"] == ""
        assert info.core_request["implicit_needs"] == []
        assert info.completeness["confidence_score"] == 0.0

    def test_to_dict(self):
        """测试 to_dict 方法"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        info = StructuredUserInfo()
        info.demographics["location"] = "深圳南山"
        info.identity_tags = ["独立女性", "程序员"]
        info.completeness["confidence_score"] = 0.85

        result = info.to_dict()

        assert isinstance(result, dict)
        assert result["demographics"]["location"] == "深圳南山"
        assert result["identity_tags"] == ["独立女性", "程序员"]
        assert result["completeness"]["confidence_score"] == 0.85
        # 确保 raw_extraction 不在输出中
        assert "raw_extraction" not in result

    def test_has_user_profile_true(self):
        """测试 has_user_profile 返回 True"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        info = StructuredUserInfo()
        info.demographics["location"] = "北京"

        assert info.has_user_profile() is True

    def test_has_user_profile_with_tags(self):
        """测试有身份标签时 has_user_profile 返回 True"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        info = StructuredUserInfo()
        info.identity_tags = ["创业者"]

        assert info.has_user_profile() is True

    def test_has_user_profile_false(self):
        """测试 has_user_profile 返回 False"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        info = StructuredUserInfo()

        assert info.has_user_profile() is False

    def test_has_preferences_true(self):
        """测试 has_preferences 返回 True"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        info = StructuredUserInfo()
        info.preferences["style_references"] = ["Audrey Hepburn"]

        assert info.has_preferences() is True

    def test_has_preferences_false(self):
        """测试 has_preferences 返回 False"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        info = StructuredUserInfo()

        assert info.has_preferences() is False


class TestL0ExtractionPrompt:
    """测试 L0 Prompt 构建"""

    def test_build_l0_extraction_prompt(self):
        """测试 _build_l0_extraction_prompt 方法"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        query = "我是深圳南山的程序员，想装修一套100平的房子"

        prompt = engine._build_l0_extraction_prompt(query)

        # 验证 prompt 包含关键内容
        assert query in prompt
        assert "demographics" in prompt
        assert "identity_tags" in prompt
        assert "lifestyle" in prompt
        assert "project_context" in prompt
        assert "preferences" in prompt
        assert "core_request" in prompt
        assert "location_considerations" in prompt
        assert "completeness" in prompt
        assert "JSON" in prompt

    def test_prompt_contains_inference_rules(self):
        """测试 prompt 包含推断规则"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_l0_extraction_prompt("测试查询")

        # 验证包含推断规则示例
        assert "英国海归" in prompt or "不婚主义" in prompt or "程序员" in prompt


class TestL0Integration:
    """测试 L0 与 search_deep 的集成"""

    def test_search_deep_method_exists(self):
        """验证 search_deep 方法存在"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        assert hasattr(engine, "search_deep")
        assert callable(engine.search_deep)

    def test_build_analysis_prompt_exists(self):
        """验证 _build_analysis_prompt 方法存在"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        assert hasattr(engine, "_build_analysis_prompt")
        assert callable(engine._build_analysis_prompt)

    def test_extract_structured_info_stream_exists(self):
        """验证 _extract_structured_info_stream 方法存在"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        assert hasattr(engine, "_extract_structured_info_stream")
        assert callable(engine._extract_structured_info_stream)


class TestStructuredInfoParsing:
    """测试 JSON 解析逻辑"""

    def test_parse_valid_json(self):
        """测试解析有效的 JSON"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        json_str = """
        {
            "demographics": {"location": "上海"},
            "identity_tags": ["设计师"],
            "lifestyle": {"hobbies": ["摄影"]},
            "project_context": {"type": "办公室设计"},
            "preferences": {"style_keywords": ["简约"]},
            "core_request": {"explicit_need": "设计办公室"},
            "location_considerations": {"climate": "温带"},
            "completeness": {"confidence_score": 0.8}
        }
        """

        data = json.loads(json_str)
        info = StructuredUserInfo()

        # 手动填充数据
        info.demographics = data.get("demographics", info.demographics)
        info.identity_tags = data.get("identity_tags", info.identity_tags)
        info.completeness = data.get("completeness", info.completeness)

        assert info.demographics["location"] == "上海"
        assert "设计师" in info.identity_tags
        assert info.completeness["confidence_score"] == 0.8

    def test_parse_json_with_markdown_wrapper(self):
        """测试解析带有 markdown 代码块的 JSON"""
        json_str = """```json
        {
            "demographics": {"location": "北京"},
            "identity_tags": ["创业者"]
        }
        ```"""

        # 移除 markdown 包装
        cleaned = json_str.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # 移除首尾的 ``` 行
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)
        assert data["demographics"]["location"] == "北京"
        assert "创业者" in data["identity_tags"]

    def test_structured_info_full_data(self):
        """测试完整数据结构"""
        from intelligent_project_analyzer.services.ucppt_search_engine import StructuredUserInfo

        info = StructuredUserInfo()

        # 填充完整数据
        info.demographics = {
            "location": "深圳南山",
            "location_context": "科技创新中心",
            "age": "30-35",
            "age_context": "事业上升期",
            "gender": "女",
            "occupation": "程序员",
            "occupation_context": "需要良好的工作环境",
            "education": "硕士",
            "education_context": "注重品质",
        }
        info.identity_tags = ["独立女性", "科技从业者", "不婚主义"]
        info.lifestyle = {"living_situation": "独居", "family_status": "单身", "hobbies": ["阅读", "瑜伽"], "pets": ["猫"]}
        info.project_context = {
            "type": "室内装修",
            "scale": "100平",
            "scale_context": "中等户型",
            "constraints": ["预算有限"],
            "budget_range": "30-50万",
            "timeline": "3个月",
        }
        info.preferences = {
            "style_references": ["Audrey Hepburn"],
            "style_keywords": ["经典优雅", "简约"],
            "color_palette": ["黑", "白", "灰"],
            "material_preferences": ["实木", "大理石"],
            "cultural_influences": ["英式", "法式"],
        }
        info.core_request = {"explicit_need": "装修房子", "implicit_needs": ["人体工学办公区", "宠物友好设计", "独立衣帽间"]}
        info.location_considerations = {"climate": "亚热带气候，需要考虑遮阳隔热", "architecture": "现代高层建筑", "lifestyle": "快节奏都市生活"}
        info.completeness = {
            "provided_dimensions": ["location", "occupation", "project_type", "scale", "style"],
            "missing_dimensions": ["budget_details"],
            "confidence_score": 0.85,
        }

        # 验证 to_dict
        result = info.to_dict()
        assert result["demographics"]["location"] == "深圳南山"
        assert len(result["identity_tags"]) == 3
        assert result["lifestyle"]["pets"] == ["猫"]
        assert result["project_context"]["scale"] == "100平"
        assert "Audrey Hepburn" in result["preferences"]["style_references"]
        assert len(result["core_request"]["implicit_needs"]) == 3
        assert result["completeness"]["confidence_score"] == 0.85

        # 验证辅助方法
        assert info.has_user_profile() is True
        assert info.has_preferences() is True
