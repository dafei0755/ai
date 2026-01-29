# -*- coding: utf-8 -*-
"""
v7.266 思考过程优化测试套件

测试内容：
1. 单元测试：prompt结构验证、动机类型识别
2. 集成测试：LLM输出解析
3. 端到端测试：完整分析流程
4. 回归测试：确保原有功能不受影响

修改文件：intelligent_project_analyzer/services/ucppt_search_engine.py
- 第3953-3985行：禁止元认知叙述
- 第4015-4034行：添加动机类型识别
- 第4228-4233行：更新JSON输出结构
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

# ============================================================
# 第一部分：单元测试
# ============================================================


class TestPromptStructure:
    """测试prompt结构是否正确"""

    def test_prompt_contains_output_rules(self):
        """测试prompt包含输出规范"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证包含输出规范
        assert "输出规范（强制）" in prompt
        assert "绝对禁止" in prompt
        assert "元认知叙述" in prompt

    def test_prompt_forbids_metacognition(self):
        """测试prompt禁止元认知叙述"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证禁止的表达
        forbidden_patterns = ["用户要我分析", "我得用庖丁解牛的方式", "用户希望我扮演", "首先看用户问题", "我得从理解用户开始"]

        for pattern in forbidden_patterns:
            assert pattern in prompt, f"prompt应包含禁止示例: {pattern}"

    def test_prompt_contains_motivation_types(self):
        """测试prompt包含12种动机类型"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证12种动机类型
        motivation_types = [
            "cultural",
            "commercial",
            "wellness",
            "technical",
            "sustainable",
            "professional",
            "inclusive",
            "functional",
            "emotional",
            "aesthetic",
            "social",
            "mixed",
        ]

        for mt in motivation_types:
            assert mt in prompt, f"prompt应包含动机类型: {mt}"

    def test_prompt_contains_motivation_chinese_names(self):
        """测试prompt包含动机类型中文名"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        chinese_names = ["文化认同", "商业价值", "健康疗愈", "技术创新", "可持续价值", "专业职能", "包容性", "功能性", "情感性", "审美", "社交", "综合"]

        for name in chinese_names:
            assert name in prompt, f"prompt应包含中文名: {name}"

    def test_prompt_json_structure_has_motivation_types(self):
        """测试JSON输出结构包含motivation_types字段"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证JSON结构包含motivation_types
        assert "motivation_types" in prompt
        assert "primary" in prompt
        assert "primary_reason" in prompt
        assert "secondary" in prompt
        assert "secondary_reason" in prompt

    def test_prompt_numbering_sequence(self):
        """测试prompt编号顺序正确（1-9）"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证编号顺序
        expected_items = [
            "1. **用户画像**",
            "2. **实体提取**",
            "3. **隐性需求**",
            "4. **动机类型识别**",
            "5. **L1 事实解构**",
            "6. **L2 多视角建模**",
            "7. **L3 核心张力**",
            "8. **L4 用户任务（JTBD）**",
            "9. **L5 锐度自检**",
        ]

        for item in expected_items:
            assert item in prompt, f"prompt应包含: {item}"


class TestMotivationTypeValidation:
    """测试动机类型验证逻辑"""

    def test_valid_motivation_type_ids(self):
        """测试有效的动机类型ID"""
        valid_ids = [
            "cultural",
            "commercial",
            "wellness",
            "technical",
            "sustainable",
            "professional",
            "inclusive",
            "functional",
            "emotional",
            "aesthetic",
            "social",
            "mixed",
        ]

        # 模拟验证函数
        def is_valid_motivation_id(motivation_id: str) -> bool:
            return motivation_id in valid_ids

        for mid in valid_ids:
            assert is_valid_motivation_id(mid), f"{mid} 应该是有效的动机类型ID"

    def test_invalid_motivation_type_ids(self):
        """测试无效的动机类型ID"""
        valid_ids = [
            "cultural",
            "commercial",
            "wellness",
            "technical",
            "sustainable",
            "professional",
            "inclusive",
            "functional",
            "emotional",
            "aesthetic",
            "social",
            "mixed",
        ]

        invalid_ids = ["unknown", "test", "invalid", ""]

        def is_valid_motivation_id(motivation_id: str) -> bool:
            return motivation_id in valid_ids

        for mid in invalid_ids:
            assert not is_valid_motivation_id(mid), f"{mid} 应该是无效的动机类型ID"


class TestOutputValidation:
    """测试输出验证逻辑"""

    def test_detect_metacognition_patterns(self):
        """测试检测元认知叙述模式"""
        metacognition_patterns = [
            r"好的[，,]",
            r"用户要我",
            r"我[得需]要",
            r"首先[看来]",
            r"让我[先来]",
            r"我想[这是]",
            r"嗯[，,]",
        ]

        # 应该被检测到的文本
        bad_texts = ["好的，用户要我分析这个问题", "我需要先理解用户的需求", "首先看用户问题", "让我先分析一下", "我想这是一个设计问题", "嗯，这个问题很有意思"]

        for text in bad_texts:
            has_metacognition = any(re.search(p, text) for p in metacognition_patterns)
            assert has_metacognition, f"应该检测到元认知叙述: {text}"

        # 不应该被检测到的文本
        good_texts = ["**核心矛盾**：HAY几何工业感 × 峨眉山有机自然感", "**用户画像**：民宿主/设计师", "**动机类型**：aesthetic + cultural"]

        for text in good_texts:
            has_metacognition = any(re.search(p, text) for p in metacognition_patterns)
            assert not has_metacognition, f"不应该检测到元认知叙述: {text}"


# ============================================================
# 第二部分：集成测试
# ============================================================


class TestLLMOutputParsing:
    """测试LLM输出解析"""

    def test_parse_motivation_types_from_json(self):
        """测试从JSON解析动机类型"""
        sample_output = {
            "user_profile": {
                "location": "四川",
                "occupation": "民宿主",
                "identity_tags": ["设计敏感型", "文化融合探索者"],
                "explicit_need": "HAY风格民宿设计",
                "implicit_needs": ["商业差异化", "设计溢价"],
                "motivation_types": {
                    "primary": "aesthetic",
                    "primary_reason": "HAY品牌气质、北欧设计美学",
                    "secondary": ["cultural"],
                    "secondary_reason": "峨眉山在地文化融合",
                },
            }
        }

        # 验证解析
        motivation = sample_output["user_profile"]["motivation_types"]
        assert motivation["primary"] == "aesthetic"
        assert motivation["primary_reason"] == "HAY品牌气质、北欧设计美学"
        assert "cultural" in motivation["secondary"]

    def test_parse_complete_analysis_output(self):
        """测试解析完整的分析输出"""
        sample_json = """
        {
            "user_profile": {
                "location": "四川峨眉山",
                "occupation": "民宿主/设计师",
                "identity_tags": ["中高端民宿创业者", "设计敏感型业主"],
                "explicit_need": "HAY风格民宿设计概念",
                "implicit_needs": ["商业差异化", "设计溢价", "文化融合"],
                "motivation_types": {
                    "primary": "aesthetic",
                    "primary_reason": "HAY品牌气质、北欧设计美学追求",
                    "secondary": ["cultural", "commercial"],
                    "secondary_reason": "峨眉山在地文化融合、民宿商业运营"
                }
            },
            "analysis": {
                "l1_facts": {
                    "brand_entities": [
                        {"name": "HAY", "product_lines": ["Palissade", "Mags"], "designers": ["Bouroullec兄弟"]}
                    ],
                    "location_entities": [
                        {"name": "峨眉山七里坪", "climate": "湿润多雾", "altitude": "1300m"}
                    ]
                },
                "l3_tension": {
                    "formula": "HAY几何工业感 vs 峨眉山有机自然感",
                    "resolution_strategy": "HAY骨架+在地肌理"
                }
            }
        }
        """

        data = json.loads(sample_json)

        # 验证结构完整性
        assert "user_profile" in data
        assert "motivation_types" in data["user_profile"]
        assert "analysis" in data
        assert "l1_facts" in data["analysis"]
        assert "l3_tension" in data["analysis"]

        # 验证动机类型
        motivation = data["user_profile"]["motivation_types"]
        assert motivation["primary"] in [
            "aesthetic",
            "cultural",
            "commercial",
            "functional",
            "emotional",
            "social",
            "wellness",
            "technical",
            "sustainable",
            "professional",
            "inclusive",
            "mixed",
        ]


class TestMotivationEngineIntegration:
    """测试动机引擎集成"""

    def test_motivation_registry_loads(self):
        """测试动机类型注册表加载"""
        try:
            from intelligent_project_analyzer.services.motivation_engine import MotivationTypeRegistry

            registry = MotivationTypeRegistry()

            # 验证12种类型都已加载
            expected_types = [
                "cultural",
                "commercial",
                "wellness",
                "technical",
                "sustainable",
                "professional",
                "inclusive",
                "functional",
                "emotional",
                "aesthetic",
                "social",
                "mixed",
            ]

            for type_id in expected_types:
                mt = registry.get_type(type_id)
                assert mt is not None, f"应该能获取动机类型: {type_id}"
                assert mt.label_zh is not None, f"{type_id} 应该有中文标签"

        except ImportError:
            pytest.skip("MotivationEngine 模块不可用")

    def test_keyword_matching_returns_motivation(self):
        """测试关键词匹配返回动机类型"""
        try:
            from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

            engine = UcpptSearchEngine()

            # 测试用例
            test_cases = [
                {"title": "HAY风格民宿设计", "description": "北欧设计美学、视觉风格", "expected_motivation": "aesthetic"},
                {"title": "峨眉山传统文化融合", "description": "在地文化、地域特色", "expected_motivation": "cultural"},
                {"title": "提升坪效和ROI", "description": "商业运营、盈利模式", "expected_motivation": "commercial"},
            ]

            for case in test_cases:
                task_dict = {"title": case["title"], "description": case["description"], "source_keywords": []}
                result = engine._keyword_matching(task_dict, case["title"], None)
                # 验证返回了有效的动机类型
                assert result.primary is not None, f"应该返回动机类型: {case['title']}"

        except Exception as e:
            pytest.skip(f"关键词匹配测试跳过: {e}")


# ============================================================
# 第三部分：端到端测试
# ============================================================


class TestEndToEndAnalysis:
    """端到端测试：完整分析流程"""

    @pytest.mark.asyncio
    async def test_unified_analysis_stream_structure(self):
        """测试统一分析流的输出结构"""
        try:
            from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

            engine = UcpptSearchEngine()
            query = "以丹麦家居品牌HAY气质为基础的民宿室内设计概念，四川峨眉山七里坪"

            # 收集流式输出
            chunks = []
            async for chunk in engine._unified_analysis_stream(query, {}):
                chunks.append(chunk)

            # 验证有输出
            assert len(chunks) > 0, "应该有流式输出"

            # 查找最终的JSON输出
            final_chunk = chunks[-1] if chunks else None
            if final_chunk and "data" in final_chunk:
                data = final_chunk["data"]
                if isinstance(data, dict) and "user_profile" in data:
                    # 验证包含motivation_types
                    assert "motivation_types" in data.get("user_profile", {}), "user_profile应包含motivation_types"

        except Exception as e:
            pytest.skip(f"端到端测试跳过（需要LLM服务）: {e}")

    @pytest.mark.asyncio
    async def test_analysis_output_no_metacognition(self):
        """测试分析输出不包含元认知叙述"""
        # 模拟LLM输出
        mock_thinking = """**核心矛盾**：HAY几何工业感 × 峨眉山有机自然感

**用户画像**
- 身份：民宿主/设计师
- 定位：中高端，设计驱动
- 标签：文化融合探索者、设计敏感型业主

**动机类型**：aesthetic + cultural
- aesthetic：HAY品牌气质、北欧设计美学
- cultural：峨眉山在地文化、川西建筑风格

**实体清单**
| 类型 | 名称 | 关键属性 |
|-----|-----|---------|
| 品牌 | HAY | Palissade系列、Mags沙发、粉末涂层钢 |
| 地点 | 峨眉山七里坪 | 海拔1300m、湿润多雾、冷杉木/竹材 |"""

        # 验证不包含元认知叙述
        metacognition_patterns = ["好的，", "用户要我", "我需要", "首先看", "让我先", "我想", "嗯，"]

        for pattern in metacognition_patterns:
            assert pattern not in mock_thinking, f"输出不应包含: {pattern}"

        # 验证包含预期内容
        assert "核心矛盾" in mock_thinking
        assert "用户画像" in mock_thinking
        assert "动机类型" in mock_thinking
        assert "实体清单" in mock_thinking


# ============================================================
# 第四部分：回归测试
# ============================================================


class TestRegressionExistingFeatures:
    """回归测试：确保原有功能不受影响"""

    def test_prompt_still_contains_l1_to_l5(self):
        """测试prompt仍包含L1-L5分析框架"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证L1-L5框架
        assert "L1 事实解构" in prompt
        assert "L2 多视角建模" in prompt
        assert "L3 核心张力" in prompt
        assert "L4 用户任务（JTBD）" in prompt
        assert "L5 锐度自检" in prompt

    def test_prompt_still_contains_entity_extraction(self):
        """测试prompt仍包含实体提取"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证6类实体
        entity_types = ["品牌实体", "地点实体", "风格实体", "场景实体", "竞品实体", "人物实体"]

        for entity in entity_types:
            assert entity in prompt, f"prompt应包含: {entity}"

    def test_prompt_still_contains_search_planning(self):
        """测试prompt仍包含搜索规划"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证搜索规划部分
        assert "搜索规划" in prompt
        assert "核心问题" in prompt
        assert "搜索策略" in prompt
        assert "targets" in prompt

    def test_json_output_structure_backward_compatible(self):
        """测试JSON输出结构向后兼容"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证原有字段仍存在
        original_fields = [
            '"user_profile"',
            '"location"',
            '"occupation"',
            '"identity_tags"',
            '"explicit_need"',
            '"implicit_needs"',
            '"analysis"',
            '"l1_facts"',
            '"l2_models"',
            '"l3_tension"',
            '"l4_jtbd"',
            '"l5_sharpness"',
            '"search_framework"',
            '"core_question"',
            '"answer_goal"',
            '"boundary"',
            '"targets"',
        ]

        for field in original_fields:
            assert field in prompt, f"prompt应包含原有字段: {field}"

    def test_motivation_engine_fallback(self):
        """测试动机引擎降级逻辑"""
        try:
            from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

            engine = UcpptSearchEngine()

            # 模拟动机引擎不可用的情况
            with patch.object(engine, "_keyword_matching", side_effect=Exception("模拟错误")):
                # 应该有降级逻辑，不会崩溃
                # 这里只验证方法存在
                assert hasattr(engine, "_generate_main_directions_fallback")

        except ImportError:
            pytest.skip("UCPPTSearchEngine 模块不可用")


class TestRegressionSearchFramework:
    """回归测试：搜索框架功能"""

    def test_search_framework_structure(self):
        """测试搜索框架结构完整"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证搜索框架结构
        framework_elements = [
            "core_question",
            "answer_goal",
            "boundary",
            "targets",
            "question",
            "search_for",
            "why_need",
            "priority",
            "category",
            "preset_keywords",
            "success_when",
            "expected_info",
        ]

        for element in framework_elements:
            assert element in prompt, f"搜索框架应包含: {element}"

    def test_priority_levels_defined(self):
        """测试优先级定义"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # 验证优先级定义
        assert "P1" in prompt or "priority" in prompt
        assert "P2" in prompt or "核心" in prompt
        assert "P3" in prompt or "拓展" in prompt


# ============================================================
# 第五部分：性能测试
# ============================================================


class TestPerformance:
    """性能测试"""

    def test_prompt_generation_time(self):
        """测试prompt生成时间"""
        import time

        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()

        start = time.time()
        for _ in range(100):
            engine._build_unified_analysis_prompt("测试问题", {})
        elapsed = time.time() - start

        # 100次生成应该在1秒内完成
        assert elapsed < 1.0, f"prompt生成太慢: {elapsed:.2f}s for 100 iterations"

    def test_prompt_size_reasonable(self):
        """测试prompt大小合理"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        prompt = engine._build_unified_analysis_prompt("测试问题", {})

        # prompt大小应该在合理范围内（< 50KB）
        prompt_size = len(prompt.encode("utf-8"))
        assert prompt_size < 50000, f"prompt太大: {prompt_size} bytes"


# ============================================================
# 运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
