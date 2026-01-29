"""
UCPPT v7.270 单元测试

测试范围：
1. ProblemSolvingApproach 数据结构
2. Step2 Prompt 生成
3. 辅助方法功能
"""

import json
from dataclasses import asdict

import pytest

from intelligent_project_analyzer.services.ucppt_search_engine import (
    ProblemSolvingApproach,
    SearchFramework,
    SearchTarget,
    UcpptSearchEngine,
)


class TestProblemSolvingApproach:
    """测试 ProblemSolvingApproach 数据结构"""

    def test_create_instance(self):
        """测试创建实例"""
        approach = ProblemSolvingApproach(
            task_type="design",
            task_type_description="这是一个设计任务",
            complexity_level="complex",
            required_expertise=["室内设计", "品牌美学"],
            solution_steps=[{"step_id": "S1", "action": "解析品牌设计语言", "purpose": "建立美学参照系", "expected_output": "品牌设计哲学"}],
            breakthrough_points=[{"point": "核心张力", "why_key": "定义设计挑战", "how_to_leverage": "用作设计框架"}],
            expected_deliverable={
                "format": "report",
                "sections": ["设计理念", "色彩方案"],
                "key_elements": ["视觉参考"],
                "quality_criteria": ["可执行性"],
            },
            original_requirement="原始需求",
            refined_requirement="结构化需求",
            confidence_score=0.85,
            alternative_approaches=["备选方案1"],
        )

        assert approach.task_type == "design"
        assert approach.complexity_level == "complex"
        assert len(approach.solution_steps) == 1
        assert len(approach.breakthrough_points) == 1
        assert approach.confidence_score == 0.85

    def test_to_dict(self):
        """测试转换为字典"""
        approach = ProblemSolvingApproach(
            task_type="research",
            task_type_description="研究任务",
            complexity_level="moderate",
            required_expertise=["领域知识"],
            solution_steps=[{"step_id": "S1", "action": "收集信息", "purpose": "建立认知", "expected_output": "信息清单"}],
            breakthrough_points=[],
            expected_deliverable={},
            original_requirement="测试",
            refined_requirement="测试",
            confidence_score=0.7,
            alternative_approaches=[],
        )

        data = approach.to_dict()

        assert isinstance(data, dict)
        assert data["task_type"] == "research"
        assert data["complexity_level"] == "moderate"
        assert len(data["solution_steps"]) == 1
        assert data["confidence_score"] == 0.7

    def test_from_dict(self):
        """测试从字典创建实例"""
        data = {
            "task_type": "exploration",
            "task_type_description": "探索任务",
            "complexity_level": "simple",
            "required_expertise": ["基础知识"],
            "solution_steps": [{"step_id": "S1", "action": "探索领域", "purpose": "理解问题", "expected_output": "领域概览"}],
            "breakthrough_points": [{"point": "关键洞察", "why_key": "解锁问题", "how_to_leverage": "应用策略"}],
            "expected_deliverable": {
                "format": "list",
                "sections": ["概述"],
                "key_elements": ["要点"],
                "quality_criteria": ["准确性"],
            },
            "original_requirement": "原始",
            "refined_requirement": "精炼",
            "confidence_score": 0.6,
            "alternative_approaches": ["方案A"],
        }

        approach = ProblemSolvingApproach.from_dict(data)

        assert approach.task_type == "exploration"
        assert approach.complexity_level == "simple"
        assert len(approach.solution_steps) == 1
        assert approach.solution_steps[0]["step_id"] == "S1"
        assert len(approach.breakthrough_points) == 1
        assert approach.confidence_score == 0.6

    def test_to_plain_text(self):
        """测试生成纯文本格式"""
        approach = ProblemSolvingApproach(
            task_type="design",
            task_type_description="设计融合任务",
            complexity_level="complex",
            required_expertise=["室内设计", "品牌美学", "地域文化"],
            solution_steps=[
                {"step_id": "S1", "action": "解析HAY品牌核心设计语言", "purpose": "建立源美学参照系", "expected_output": "HAY设计哲学、核心设计师"},
                {"step_id": "S2", "action": "提取HAY色彩系统与材质特征", "purpose": "获取可应用的视觉元素", "expected_output": "标志性色彩、材质偏好"},
            ],
            breakthrough_points=[
                {"point": "HAY几何工业感 vs 峨眉山有机自然感", "why_key": "这是定义设计挑战的核心张力", "how_to_leverage": "用HAY的几何框架作为骨架"}
            ],
            expected_deliverable={
                "format": "report",
                "sections": ["设计理念", "色彩方案", "材质选择"],
                "key_elements": ["视觉参考图", "产品推荐"],
                "quality_criteria": ["可执行性强", "视觉协调统一"],
            },
            original_requirement="以HAY气质为基础，为峨眉山七里坪民宿提供概念设计",
            refined_requirement="融合HAY北欧极简与峨眉山地域特色的民宿设计方案",
            confidence_score=0.85,
            alternative_approaches=["先从成功案例入手", "从用户体验场景出发"],
        )

        text = approach.to_plain_text()

        # 验证文本包含关键信息
        assert "## 任务本质" in text
        assert "设计融合任务" in text
        assert "complex" in text
        assert "室内设计" in text

        assert "## 解题路径（2步）" in text
        assert "**S1**: 解析HAY品牌核心设计语言" in text
        assert "**S2**: 提取HAY色彩系统与材质特征" in text

        assert "## 关键突破口" in text
        assert "HAY几何工业感 vs 峨眉山有机自然感" in text

        assert "## 预期产出" in text
        assert "格式：report" in text
        assert "设计理念, 色彩方案, 材质选择" in text

        assert "## 任务描述" in text
        assert "以HAY气质为基础" in text

    def test_serialization_roundtrip(self):
        """测试序列化往返（to_dict -> from_dict）"""
        original = ProblemSolvingApproach(
            task_type="verification",
            task_type_description="验证型任务",
            complexity_level="moderate",
            required_expertise=["数据分析", "统计学"],
            solution_steps=[
                {"step_id": "S1", "action": "收集数据", "purpose": "建立基线", "expected_output": "数据集"},
                {"step_id": "S2", "action": "分析数据", "purpose": "验证假设", "expected_output": "分析报告"},
            ],
            breakthrough_points=[{"point": "数据质量", "why_key": "决定结论可信度", "how_to_leverage": "严格筛选数据源"}],
            expected_deliverable={
                "format": "comparison",
                "sections": ["数据概览", "分析结果", "结论"],
                "key_elements": ["图表", "统计数据"],
                "quality_criteria": ["准确性", "可重复性"],
            },
            original_requirement="验证假设X",
            refined_requirement="通过数据分析验证假设X的有效性",
            confidence_score=0.75,
            alternative_approaches=["使用不同数据集", "采用其他分析方法"],
        )

        # 序列化
        data = original.to_dict()

        # 反序列化
        restored = ProblemSolvingApproach.from_dict(data)

        # 验证所有字段
        assert restored.task_type == original.task_type
        assert restored.task_type_description == original.task_type_description
        assert restored.complexity_level == original.complexity_level
        assert restored.required_expertise == original.required_expertise
        assert len(restored.solution_steps) == len(original.solution_steps)
        assert restored.solution_steps[0]["step_id"] == original.solution_steps[0]["step_id"]
        assert len(restored.breakthrough_points) == len(original.breakthrough_points)
        assert restored.expected_deliverable == original.expected_deliverable
        assert restored.original_requirement == original.original_requirement
        assert restored.refined_requirement == original.refined_requirement
        assert restored.confidence_score == original.confidence_score
        assert restored.alternative_approaches == original.alternative_approaches

    def test_empty_optional_fields(self):
        """测试可选字段为空的情况"""
        approach = ProblemSolvingApproach(
            task_type="exploration",
            task_type_description="",
            complexity_level="simple",
            required_expertise=[],
            solution_steps=[],
            breakthrough_points=[],
            expected_deliverable={},
            original_requirement="",
            refined_requirement="",
            confidence_score=0.0,
            alternative_approaches=[],
        )

        # 应该能正常创建
        assert approach.task_type == "exploration"
        assert len(approach.solution_steps) == 0
        assert len(approach.breakthrough_points) == 0

        # 应该能正常序列化
        data = approach.to_dict()
        assert isinstance(data, dict)

        # 应该能正常反序列化
        restored = ProblemSolvingApproach.from_dict(data)
        assert restored.task_type == "exploration"


class TestStep2PromptGeneration:
    """测试 Step2 Prompt 生成"""

    @pytest.fixture
    def engine(self):
        """创建测试用的搜索引擎实例"""
        return UcpptSearchEngine()

    @pytest.fixture
    def sample_problem_solving_approach(self):
        """示例解题思路"""
        return ProblemSolvingApproach(
            task_type="design",
            task_type_description="设计融合任务",
            complexity_level="complex",
            required_expertise=["室内设计", "品牌美学", "地域文化"],
            solution_steps=[
                {"step_id": "S1", "action": "解析HAY品牌核心设计语言", "purpose": "建立源美学参照系", "expected_output": "HAY设计哲学、核心设计师"},
                {"step_id": "S2", "action": "提取HAY色彩系统与材质特征", "purpose": "获取可应用的视觉元素", "expected_output": "标志性色彩、材质偏好"},
                {"step_id": "S3", "action": "研究峨眉山七里坪气候与环境", "purpose": "理解物理约束", "expected_output": "海拔、气候、光线特点"},
            ],
            breakthrough_points=[
                {"point": "HAY几何工业感 vs 峨眉山有机自然感", "why_key": "定义设计挑战的核心张力", "how_to_leverage": "用HAY的几何框架作为骨架"}
            ],
            expected_deliverable={
                "format": "report",
                "sections": ["设计理念", "色彩方案", "材质选择"],
                "key_elements": ["视觉参考图"],
                "quality_criteria": ["可执行性强"],
            },
            original_requirement="以HAY气质为基础，为峨眉山七里坪民宿提供概念设计",
            refined_requirement="融合HAY北欧极简与峨眉山地域特色的民宿设计方案",
            confidence_score=0.85,
            alternative_approaches=[],
        )

    @pytest.fixture
    def sample_step2_context(self):
        """示例 step2_context"""
        return {
            "core_question": "如何在民宿设计中融合HAY的北欧极简与峨眉山的在地特色",
            "answer_goal": "一份完整的概念设计方案，包含具体建议",
            "solution_steps_summary": ["S1:HAY设计语言", "S2:HAY色彩材质", "S3:峨眉山环境"],
            "breakthrough_tensions": ["几何工业感 vs 有机自然感"],
        }

    @pytest.fixture
    def sample_analysis_data(self):
        """示例分析数据"""
        return {
            "user_profile": {"location": "四川", "occupation": "民宿主", "identity_tags": ["设计敏感型业主"]},
            "analysis": {
                "l1_facts": {
                    "brand_entities": [
                        {
                            "name": "HAY",
                            "product_lines": ["Palissade系列", "Mags沙发"],
                            "designers": ["Ronan Bouroullec"],
                            "color_system": ["柔和灰", "暖黄"],
                            "materials": ["粉末涂层钢", "实木"],
                        }
                    ],
                    "location_entities": [
                        {
                            "name": "峨眉山七里坪",
                            "climate": "湿润多雾",
                            "altitude": "1300m",
                            "local_materials": ["冷杉木", "竹材", "青石"],
                            "architecture_style": "川西山地",
                        }
                    ],
                },
                "l2_models": {},
                "l3_tension": "HAY几何工业感 vs 峨眉山有机自然感",
                "l4_jtbd": "当设计民宿时，我想要融合品牌美学与地域特色，以便创造独特体验",
                "l5_sharpness": {},
            },
        }

    def test_build_step2_prompt_structure(
        self, engine, sample_problem_solving_approach, sample_step2_context, sample_analysis_data
    ):
        """测试 Step2 Prompt 生成的结构"""
        query = "以丹麦家居品牌HAY气质为基础，为四川峨眉山七里坪民宿室内设计提供概念设计"

        prompt = engine._build_step2_search_framework_prompt(
            query, sample_step2_context, sample_problem_solving_approach, sample_analysis_data
        )

        # 验证 Prompt 包含关键部分
        assert "## 用户问题" in prompt
        assert query in prompt

        assert "## 第一步分析结果" in prompt
        assert "### 核心问题" in prompt
        assert "如何在民宿设计中融合HAY的北欧极简与峨眉山的在地特色" in prompt

        assert "### 解题路径" in prompt
        assert "S1: 解析HAY品牌核心设计语言" in prompt
        assert "S2: 提取HAY色彩系统与材质特征" in prompt
        assert "S3: 研究峨眉山七里坪气候与环境" in prompt

        assert "### 关键突破口" in prompt
        assert "HAY几何工业感 vs 峨眉山有机自然感" in prompt

        assert "### 提取的实体" in prompt
        assert "**品牌实体**" in prompt
        assert "HAY" in prompt
        assert "**地点实体**" in prompt
        assert "峨眉山七里坪" in prompt

        assert "## 任务要求" in prompt
        assert "### 搜索任务设计原则" in prompt
        assert "### 关键词生成要求" in prompt

    def test_build_step2_prompt_keyword_requirements(
        self, engine, sample_problem_solving_approach, sample_step2_context, sample_analysis_data
    ):
        """测试 Step2 Prompt 包含关键词生成要求"""
        query = "测试问题"

        prompt = engine._build_step2_search_framework_prompt(
            query, sample_step2_context, sample_problem_solving_approach, sample_analysis_data
        )

        # 验证关键词生成要求
        assert "预设关键词是搜索质量的关键" in prompt
        assert "具体化" in prompt
        assert "场景化" in prompt
        assert "多样化" in prompt
        assert "可搜索性" in prompt

        # 验证示例
        assert "HAY Palissade系列 户外家具" in prompt
        assert "峨眉山七里坪 民宿设计 在地材料" in prompt

    def test_build_step2_prompt_output_format(
        self, engine, sample_problem_solving_approach, sample_step2_context, sample_analysis_data
    ):
        """测试 Step2 Prompt 输出格式要求"""
        query = "测试问题"

        prompt = engine._build_step2_search_framework_prompt(
            query, sample_step2_context, sample_problem_solving_approach, sample_analysis_data
        )

        # 验证输出格式说明
        assert "## 输出要求" in prompt
        assert "core_question" in prompt
        assert "answer_goal" in prompt
        assert "boundary" in prompt
        assert "targets" in prompt
        assert "preset_keywords" in prompt

        # 验证 JSON 示例
        assert '"id": "T1"' in prompt
        assert '"question":' in prompt
        assert '"search_for":' in prompt
        assert '"why_need":' in prompt
        assert '"success_when":' in prompt
        assert '"priority":' in prompt
        assert '"category":' in prompt
        assert '"preset_keywords":' in prompt

    def test_build_step2_prompt_with_minimal_data(self, engine):
        """测试使用最小数据生成 Step2 Prompt"""
        query = "简单问题"
        step2_context = {"core_question": "核心问题", "answer_goal": "回答目标"}
        problem_solving_approach = ProblemSolvingApproach(
            task_type="exploration",
            task_type_description="探索任务",
            complexity_level="simple",
            required_expertise=["基础知识"],
            solution_steps=[{"step_id": "S1", "action": "探索", "purpose": "理解", "expected_output": "概览"}],
            breakthrough_points=[],
            expected_deliverable={},
            original_requirement=query,
            refined_requirement=query,
            confidence_score=0.5,
            alternative_approaches=[],
        )
        analysis_data = {
            "user_profile": {},
            "analysis": {"l1_facts": {}, "l2_models": {}, "l3_tension": "", "l4_jtbd": "", "l5_sharpness": {}},
        }

        # 应该能正常生成 Prompt
        prompt = engine._build_step2_search_framework_prompt(
            query, step2_context, problem_solving_approach, analysis_data
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "## 用户问题" in prompt
        assert "## 第一步分析结果" in prompt


class TestHelperMethods:
    """测试辅助方法"""

    @pytest.fixture
    def engine(self):
        """创建测试用的搜索引擎实例"""
        return UcpptSearchEngine()

    def test_build_default_problem_solving_approach(self, engine):
        """测试构建默认解题思路"""
        query = "测试问题"

        approach = engine._build_default_problem_solving_approach(query)

        # 验证基本字段
        assert approach.task_type == "exploration"
        assert approach.complexity_level == "moderate"
        assert len(approach.required_expertise) == 3
        assert "领域知识" in approach.required_expertise

        # 验证解题步骤
        assert len(approach.solution_steps) == 5
        assert approach.solution_steps[0]["step_id"] == "S1"
        assert "理解问题的核心诉求" in approach.solution_steps[0]["action"]

        # 验证突破口
        assert len(approach.breakthrough_points) == 1
        assert "问题的核心诉求" in approach.breakthrough_points[0]["point"]

        # 验证预期产出
        assert approach.expected_deliverable["format"] == "report"
        assert len(approach.expected_deliverable["sections"]) == 4

        # 验证任务描述
        assert approach.original_requirement == query
        assert query[:50] in approach.refined_requirement

        # 验证元数据
        assert approach.confidence_score == 0.5
        assert len(approach.alternative_approaches) == 2

    def test_generate_framework_checklist(self, engine):
        """测试生成框架清单"""
        # 创建测试用的 SearchFramework
        framework = SearchFramework(
            original_query="测试问题",
            core_question="核心问题",
            answer_goal="回答目标",
            boundary="不搜索价格信息",
            targets=[
                SearchTarget(
                    id="T1",
                    question="问题1",
                    search_for="搜索内容1",
                    why_need="原因1",
                    success_when=["标准1"],
                    priority=1,
                    category="品牌调研",
                ),
                SearchTarget(
                    id="T2",
                    question="问题2",
                    search_for="搜索内容2",
                    why_need="原因2",
                    success_when=["标准2"],
                    priority=2,
                    category="案例参考",
                ),
            ],
        )

        analysis_data = {"user_profile": {}, "analysis": {}}

        checklist = engine._generate_framework_checklist(framework, analysis_data)

        # 验证清单内容
        assert checklist.core_summary == "核心问题"
        assert checklist.answer_goal == "回答目标"
        assert len(checklist.main_directions) == 2
        assert checklist.main_directions[0]["id"] == "T1"
        assert checklist.main_directions[0]["name"] == "问题1"
        assert checklist.main_directions[0]["description"] == "搜索内容1"
        assert checklist.main_directions[0]["priority"] == 1
        assert len(checklist.boundaries) == 1
        assert checklist.boundaries[0] == "不搜索价格信息"
        assert checklist.generated_at != ""

    def test_generate_framework_checklist_with_many_targets(self, engine):
        """测试生成框架清单（超过5个目标）"""
        # 创建包含10个目标的框架
        targets = [
            SearchTarget(
                id=f"T{i}",
                question=f"问题{i}",
                search_for=f"搜索内容{i}",
                why_need=f"原因{i}",
                success_when=[f"标准{i}"],
                priority=1,
                category="品牌调研",
            )
            for i in range(1, 11)
        ]

        framework = SearchFramework(
            original_query="测试问题", core_question="核心问题", answer_goal="回答目标", boundary="", targets=targets
        )

        analysis_data = {}

        checklist = engine._generate_framework_checklist(framework, analysis_data)

        # 应该只包含前5个目标
        assert len(checklist.main_directions) == 5
        assert checklist.main_directions[0]["id"] == "T1"
        assert checklist.main_directions[4]["id"] == "T5"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
