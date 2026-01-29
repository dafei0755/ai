"""
单元测试: 需求洞察节点 (Questionnaire Summary Node)

测试范围:
1. 问卷数据提取
2. 需求重构引擎调用
3. 超时保护机制
4. 降级方案
5. 结构化需求文档生成
6. 边界条件处理

v7.142: 新增超时保护测试
"""

from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.interaction.nodes.questionnaire_summary import (
    QuestionnaireSummaryNode,
    questionnaire_summary_node,
)


class TestQuestionnaireDataExtraction:
    """测试问卷数据提取功能"""

    def test_extract_complete_questionnaire_data(self):
        """测试完整问卷数据提取"""
        state = {
            "confirmed_core_tasks": [
                {"id": "task_1", "title": "调研安藤忠雄的乡土建筑设计案例"},
                {"id": "task_2", "title": "四川广元农村气候与地形调研"},
            ],
            "gap_filling_answers": {
                "design_objectives": ["乡土情怀", "现代简约"],
                "budget_range": "100-200万",
                "timeline": "6个月",
            },
            "selected_dimensions": [
                {"dimension_id": "cultural_axis", "name": "文化认同"},
                {"dimension_id": "material_temperature", "name": "材料温度"},
            ],
            "dimension_weights": {"cultural_axis": 75, "material_temperature": 60},
            "progressive_questionnaire_step": 3,
        }

        result = QuestionnaireSummaryNode._extract_questionnaire_data(state)

        # 验证核心任务
        assert len(result["core_tasks"]) == 2
        assert result["core_tasks"][0]["title"] == "调研安藤忠雄的乡土建筑设计案例"

        # 验证信息补全
        assert len(result["gap_filling"]) == 3
        assert result["gap_filling"]["budget_range"] == "100-200万"

        # 验证雷达维度
        assert len(result["dimensions"]["selected"]) == 2
        assert result["dimensions"]["weights"]["cultural_axis"] == 75

        # 验证步骤
        assert result["questionnaire_step"] == 3

    def test_extract_partial_data(self):
        """测试部分数据缺失情况"""
        state = {
            "confirmed_core_tasks": [{"id": "task_1", "title": "任务1"}],
            # 缺少 gap_filling_answers
            "selected_dimensions": [],
            "dimension_weights": {},
        }

        result = QuestionnaireSummaryNode._extract_questionnaire_data(state)

        # 应该能处理缺失数据
        assert len(result["core_tasks"]) == 1
        assert len(result["gap_filling"]) == 0
        assert len(result["dimensions"]["selected"]) == 0

    def test_extract_empty_state(self):
        """测试空状态处理"""
        state = {}

        result = QuestionnaireSummaryNode._extract_questionnaire_data(state)

        # 应该返回空结构但不抛异常
        assert result["core_tasks"] == []
        assert result["gap_filling"] == {}
        assert result["dimensions"]["selected"] == []


class TestRestructuringEngine:
    """测试需求重构引擎"""

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt")
    @patch(
        "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
    )
    def test_successful_restructuring(self, mock_restructure, mock_interrupt):
        """测试成功的需求重构 - v7.151 更新"""
        # 🆕 v7.151: mock interrupt 返回确认
        mock_interrupt.return_value = {"intent": "confirm"}

        # Mock返回值
        mock_restructure.return_value = {
            "metadata": {
                "document_version": "2.0",
                "generated_at": datetime.now().isoformat(),
                "generation_method": "questionnaire_based_with_ai_insights",
                "llm_enhanced": True,  # 🆕 v7.151
            },
            "project_objectives": {"primary_goal": "为50岁男士打造田园民居", "primary_goal_source": "L4_JTBD_insight"},
            "constraints": {"budget": {"total": "100-200万"}, "timeline": {"duration": "6个月"}},
            "design_priorities": [{"label": "文化认同", "weight": 0.75}, {"label": "材料温度", "weight": 0.60}],
            "identified_risks": [],
            "insight_summary": {"L5_sharpness_score": 85},
            # 🆕 v7.151: 新增深度洞察字段
            "project_essence": "打造融合乡土情怀与现代舒适的归隐空间",
            "implicit_requirements": [],
            "key_conflicts": [],
            "core_tension": {"description": "传统与现代的平衡"},
        }

        state = {
            "user_input": "让安藤忠雄为50岁男士设计田园民居",
            "confirmed_core_tasks": [{"id": "task_1", "title": "调研案例"}],
            "gap_filling_answers": {"budget_range": "100-200万"},
            "selected_dimensions": [{"dimension_id": "cultural_axis", "name": "文化认同"}],
            "dimension_weights": {"cultural_axis": 75},
            "requirement_analysis": {},
            "agent_results": {"requirements_analyst": {"analysis_layers": {"L4_project_task": "打造乡土情感复归空间"}}},
        }

        result = QuestionnaireSummaryNode.execute(state)

        # 验证调用
        assert mock_restructure.called
        assert mock_restructure.call_count == 1
        assert mock_interrupt.called  # 🆕 v7.151: 验证 interrupt 被调用

        # 🆕 v7.151: 返回 Command 对象，验证 update 字典
        from langgraph.types import Command

        assert isinstance(result, Command)
        assert result.goto == "project_director"  # 确认后应该直接到 project_director
        assert result.update["questionnaire_summary_completed"] is True
        assert result.update["requirements_confirmed"] is True
        assert "restructured_requirements" in result.update
        assert result.update["restructured_requirements"]["project_objectives"]["primary_goal"] == "为50岁男士打造田园民居"

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt")
    @patch(
        "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
    )
    def test_restructuring_failure_uses_fallback(self, mock_restructure, mock_interrupt):
        """测试重构失败时使用降级方案 - v7.151 更新"""
        # Mock抛出异常
        mock_restructure.side_effect = Exception("LLM服务不可用")
        mock_interrupt.return_value = {"intent": "confirm"}

        state = {
            "user_input": "设计田园民居",
            "confirmed_core_tasks": [{"id": "task_1", "title": "主任务"}],
            "gap_filling_answers": {},
            "selected_dimensions": [],
            "dimension_weights": {},
            "requirement_analysis": {},
            "agent_results": {},
        }

        result = QuestionnaireSummaryNode.execute(state)

        # 🆕 v7.151: 返回 Command 对象
        from langgraph.types import Command

        assert isinstance(result, Command)

        # 验证使用了降级方案
        assert result.update["questionnaire_summary_completed"] is True
        assert result.update["restructured_requirements"]["metadata"]["generation_method"] == "fallback_restructure"
        assert result.update["restructured_requirements"]["project_objectives"]["primary_goal"] == "主任务"


class TestTimeoutProtection:
    """测试超时保护机制 (v7.142)"""

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt")
    @patch(
        "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
    )
    def test_restructuring_exception_triggers_fallback(self, mock_restructure, mock_interrupt):
        """测试重构异常触发降级方案（模拟超时异常）- v7.151 更新"""

        # Mock抛出超时异常
        mock_restructure.side_effect = TimeoutError("LLM调用超时")
        mock_interrupt.return_value = {"intent": "confirm"}

        state = {
            "user_input": "设计需求",
            "confirmed_core_tasks": [{"id": "task_1", "title": "核心任务"}],
            "gap_filling_answers": {},
            "selected_dimensions": [],
            "dimension_weights": {},
            "requirement_analysis": {},
            "agent_results": {},
        }

        # 执行测试
        result = QuestionnaireSummaryNode.execute(state)

        # 🆕 v7.151: 返回 Command 对象
        from langgraph.types import Command

        assert isinstance(result, Command)

        # 验证使用了降级方案
        assert result.update["questionnaire_summary_completed"] is True
        assert result.update["restructured_requirements"]["metadata"]["generation_method"] == "fallback_restructure"

        print(f"✅ 异常触发降级方案")

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt")
    @patch(
        "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
    )
    def test_fast_restructuring_completes_normally(self, mock_restructure, mock_interrupt):
        """测试快速重构正常完成 - v7.151 更新"""
        import time

        mock_interrupt.return_value = {"intent": "confirm"}

        # Mock一个快速操作（0.1秒）
        def fast_restructure(*args, **kwargs):
            time.sleep(0.1)
            return {
                "metadata": {
                    "document_version": "2.0",
                    "generated_at": datetime.now().isoformat(),
                    "generation_method": "questionnaire_based_with_ai_insights",
                    "llm_enhanced": True,
                },
                "project_objectives": {"primary_goal": "快速完成的目标"},
                "constraints": {},
                "design_priorities": [],
                "identified_risks": [],
                "insight_summary": {"L5_sharpness_score": 75},
                "project_essence": "",
                "implicit_requirements": [],
                "key_conflicts": [],
                "core_tension": {"description": ""},
            }

        mock_restructure.side_effect = fast_restructure

        state = {
            "user_input": "设计需求",
            "confirmed_core_tasks": [{"id": "task_1", "title": "核心任务"}],
            "gap_filling_answers": {},
            "selected_dimensions": [],
            "dimension_weights": {},
            "requirement_analysis": {},
            "agent_results": {},
        }

        # 执行测试
        start_time = time.time()
        result = QuestionnaireSummaryNode.execute(state)
        elapsed_time = time.time() - start_time

        # 验证快速完成
        assert elapsed_time < 1, f"应该快速完成，实际耗时 {elapsed_time:.2f}秒"

        # 🆕 v7.151: 返回 Command 对象
        from langgraph.types import Command

        assert isinstance(result, Command)

        # 验证使用了正常方案
        assert (
            result.update["restructured_requirements"]["metadata"]["generation_method"]
            == "questionnaire_based_with_ai_insights"
        )

        print(f"✅ 正常完成，耗时 {elapsed_time:.2f}秒")


class TestFallbackRestructure:
    """测试降级重构逻辑"""

    def test_fallback_with_complete_data(self):
        """测试完整数据的降级重构"""
        questionnaire_data = {
            "core_tasks": [
                {"id": "task_1", "title": "主要任务", "description": "详细描述"},
                {"id": "task_2", "title": "次要任务1"},
                {"id": "task_3", "title": "次要任务2"},
            ],
            "gap_filling": {"budget": "100万"},
            "dimensions": {"selected": [{"dimension_id": "dim1", "name": "维度1"}], "weights": {"dim1": 80}},
        }

        ai_analysis = {}
        user_input = "用户原始输入"

        result = QuestionnaireSummaryNode._fallback_restructure(questionnaire_data, ai_analysis, user_input)

        # 验证基本结构
        assert result["metadata"]["generation_method"] == "fallback_restructure"
        assert result["project_objectives"]["primary_goal"] == "主要任务"
        assert len(result["project_objectives"]["secondary_goals"]) == 2
        assert result["project_objectives"]["secondary_goals"][0] == "次要任务1"

    def test_fallback_with_empty_tasks(self):
        """测试空任务列表的降级重构"""
        questionnaire_data = {"core_tasks": [], "gap_filling": {}, "dimensions": {"selected": [], "weights": {}}}

        result = QuestionnaireSummaryNode._fallback_restructure(questionnaire_data, {}, "用户输入")

        # 验证默认值
        assert result["project_objectives"]["primary_goal"] == "待明确核心目标"
        assert result["project_objectives"]["secondary_goals"] == []


class TestSummaryTextGeneration:
    """测试摘要文本生成"""

    def test_generate_full_summary(self):
        """测试完整摘要生成"""
        doc = {
            "project_objectives": {"primary_goal": "为50岁男士打造融合乡土情感与现代美学的田园民居"},
            "constraints": {
                "budget": {"total": "100-200万"},
                "timeline": {"duration": "6个月"},
                "space": {"area": "300平米"},
            },
            "design_priorities": [
                {"label": "文化认同", "weight": 0.75},
                {"label": "材料温度", "weight": 0.60},
                {"label": "空间灵活性", "weight": 0.55},
            ],
        }

        summary = QuestionnaireSummaryNode._generate_summary_text(doc)

        # 验证包含关键信息
        assert "项目目标" in summary
        assert "田园民居" in summary
        assert "核心约束" in summary
        assert "100-200万" in summary
        assert "6个月" in summary
        assert "300平米" in summary
        assert "设计重点" in summary
        assert "文化认同" in summary

    def test_generate_minimal_summary(self):
        """测试最小摘要生成"""
        doc = {"project_objectives": {"primary_goal": "简单目标"}, "constraints": {}, "design_priorities": []}

        summary = QuestionnaireSummaryNode._generate_summary_text(doc)

        # 验证基本结构
        assert "项目目标" in summary
        assert "简单目标" in summary


class TestStructuredRequirementsUpdate:
    """测试结构化需求更新"""

    def test_update_with_full_restructured_doc(self):
        """测试完整重构文档的更新"""
        existing = {"project_type": "residential", "old_field": "保留的旧字段"}

        restructured_doc = {
            "metadata": {"generated_at": "2026-01-06T15:00:00"},
            "project_objectives": {"primary_goal": "新的核心目标"},
            "constraints": {
                "budget": {"total": "100-200万", "breakdown": {"设计费": "20万", "施工费": "150万"}},
                "timeline": {"duration": "6个月"},
                "space": {"area": "300平米", "layout": "2层独栋"},
            },
            "design_priorities": [
                {"label": "文化认同", "weight": 0.75},
                {"label": "材料温度", "weight": 0.60},
                {"label": "空间灵活性", "weight": 0.55},
            ],
        }

        result = QuestionnaireSummaryNode._update_structured_requirements(existing, restructured_doc)

        # 验证旧字段保留
        assert result["old_field"] == "保留的旧字段"

        # 验证新字段更新
        assert result["project_task"] == "新的核心目标"
        assert result["budget_range"] == "100-200万"
        assert "budget_breakdown" in result
        assert result["budget_breakdown"]["设计费"] == "20万"
        assert result["timeline"] == "6个月"
        assert result["space_area"] == "300平米"
        assert result["space_layout"] == "2层独栋"

        # 验证设计重点
        assert "design_focus" in result
        assert result["design_focus"] == ["文化认同", "材料温度", "空间灵活性"]

        # 验证元数据
        assert result["_source"] == "questionnaire_restructured"
        assert result["_questionnaire_enhanced"] is True

    def test_update_preserves_existing_when_no_new_data(self):
        """测试没有新数据时保留现有数据"""
        existing = {"project_task": "原有任务", "budget_range": "50万"}

        restructured_doc = {
            "metadata": {},
            "project_objectives": {},  # 空目标
            "constraints": {},  # 空约束
            "design_priorities": [],
        }

        result = QuestionnaireSummaryNode._update_structured_requirements(existing, restructured_doc)

        # 验证原有数据保留
        assert result["project_task"] == "原有任务"
        assert result["budget_range"] == "50万"


class TestConvenienceFunction:
    """测试便捷函数"""

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.QuestionnaireSummaryNode.execute")
    def test_questionnaire_summary_node_function(self, mock_execute):
        """测试 questionnaire_summary_node 便捷函数"""
        mock_execute.return_value = {"result": "success"}

        state = {"user_input": "测试"}
        result = questionnaire_summary_node(state)

        # 验证调用
        assert mock_execute.called
        assert result == {"result": "success"}


# ============================================================================
# 集成测试
# ============================================================================


class TestQuestionnaireeSummaryIntegration:
    """需求洞察集成测试"""

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt")
    @patch(
        "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
    )
    def test_complete_flow_with_real_data(self, mock_restructure, mock_interrupt):
        """测试完整流程（使用真实数据结构）- v7.151 更新"""
        # 🆕 v7.151: mock interrupt 返回确认
        mock_interrupt.return_value = {"intent": "confirm"}

        # Mock重构引擎返回
        mock_restructure.return_value = {
            "metadata": {
                "document_version": "2.0",
                "generated_at": datetime.now().isoformat(),
                "generation_method": "questionnaire_based_with_ai_insights",
                "llm_enhanced": True,  # 🆕 v7.151
            },
            "project_objectives": {
                "primary_goal": "为离家多年的50岁男士打造乡土情感复归的田园民居",
                "primary_goal_source": "L4_JTBD_insight",
                "secondary_goals": ["融合职业展示空间", "体现四川广元地域特色"],
                "success_criteria": ["乡土情感复归达到预期", "职业展示功能完善"],
            },
            "constraints": {
                "budget": {"total": "100-200万", "flexibility": "中等"},
                "timeline": {"duration": "6个月"},
                "space": {"area": "300平米"},
            },
            "design_priorities": [
                {"label": "文化认同", "weight": 0.75, "dimension_id": "cultural_axis"},
                {"label": "材料温度", "weight": 0.60, "dimension_id": "material_temperature"},
            ],
            "core_tension": {"tension": "乡土情感复归 vs 职业创作展示", "description": "如何平衡私密的情感归属与开放的职业展示"},
            "special_requirements": ["安藤忠雄风格", "四川传统元素"],
            "identified_risks": [{"type": "功能冲突", "description": "居住私密性与展示开放性的矛盾"}],
            "insight_summary": {
                "L1_key_facts": ["50岁", "室内设计师", "离家多年"],
                "L2_user_profile": {"age": 50, "profession": "室内设计师"},
                "L3_core_tension": "乡土情感复归 vs 职业创作展示",
                "L4_project_task_jtbd": "打造情感归属与职业展示的双重空间",
                "L5_sharpness_score": 85,
                "L5_sharpness_note": "洞察深刻，张力明确",
            },
            "deliverable_expectations": ["设计策略文档", "空间概念描述"],
            "executive_summary": {
                "one_sentence": "通过融合乡土情感与现代美学，为50岁男士打造承载回忆与未来的田园民居",
                "what": "田园民居设计",
                "why": "满足情感归属需求",
                "how": "通过文化认同(75%) + 材料温度(60%)实现",
                "constraints_summary": "预算100-200万 | 时间6个月 | 面积300平米",
            },
            # 🆕 v7.151: 新增深度洞察字段
            "project_essence": "打造融合乡土情怀与现代舒适的归隐空间",
            "implicit_requirements": [],
            "key_conflicts": [],
        }

        # 准备真实数据结构
        state = {
            "user_input": "让安藤忠雄为一个离家多年的50岁男士设计一座田园民居，四川广元农村、300平米，室内设计师职业。",
            "confirmed_core_tasks": [
                {
                    "id": "task_1",
                    "title": "调研安藤忠雄的乡土建筑设计案例",
                    "description": "查找并分析安藤忠雄过往田园与乡土风格相关的设计案例",
                    "task_type": "research",
                },
                {
                    "id": "task_2",
                    "title": "四川广元农村气候与地形调研",
                    "description": "收集四川广元农村的地形、气候、建筑风格和乡土文化",
                    "task_type": "research",
                },
            ],
            "gap_filling_answers": {
                "design_objectives": ["乡土情怀", "现代简约", "传统中式", "融合自然"],
                "integration_professional_needs": "工作室氛围，童年情怀",
                "functional_zones": ["起居空间", "个人工作室", "家庭餐厅", "庭院景观"],
                "preferred_deliverables": ["设计策略文档", "空间概念描述", "材料选择指导"],
            },
            "selected_dimensions": [
                {"dimension_id": "cultural_axis", "name": "文化认同"},
                {"dimension_id": "material_temperature", "name": "材料温度"},
                {"dimension_id": "space_flexibility", "name": "空间灵活性"},
            ],
            "dimension_weights": {"cultural_axis": 75, "material_temperature": 60, "space_flexibility": 50},
            "progressive_questionnaire_step": 3,
            "requirement_analysis": {},
            "agent_results": {
                "requirements_analyst": {
                    "analysis_layers": {
                        "L1_key_facts": ["50岁", "室内设计师", "离家多年"],
                        "L2_user_model": {"age": 50, "profession": "室内设计师"},
                        "L3_core_tension": "乡土情感复归 vs 职业创作展示",
                        "L4_project_task": "打造情感归属与职业展示的双重空间",
                        "L5_sharpness_score": 85,
                    }
                }
            },
        }

        # 执行测试
        result = QuestionnaireSummaryNode.execute(state)

        # 🆕 v7.151: 返回 Command 对象
        from langgraph.types import Command

        assert isinstance(result, Command)
        assert result.goto == "project_director"  # 确认后直接到 project_director

        # 验证需求洞察完成
        assert result.update["questionnaire_summary_completed"] is True
        assert result.update["requirements_confirmed"] is True  # 🆕 v7.151: 合并确认逻辑

        # 验证重构文档结构
        doc = result.update["restructured_requirements"]
        assert doc["metadata"]["generation_method"] == "questionnaire_based_with_ai_insights"
        assert "50岁男士" in doc["project_objectives"]["primary_goal"]
        assert doc["constraints"]["budget"]["total"] == "100-200万"
        assert len(doc["design_priorities"]) == 2
        assert doc["design_priorities"][0]["label"] == "文化认同"
        assert doc["insight_summary"]["L5_sharpness_score"] == 85

        # 验证摘要文本
        assert (
            "project_objectives" in result.update["requirements_summary_text"]
            or "田园民居" in result.update["requirements_summary_text"]
        )

        # 验证结构化需求更新
        structured = result.update["structured_requirements"]
        assert structured["_source"] == "questionnaire_restructured"
        assert structured["_questionnaire_enhanced"] is True

        print("✅ 集成测试通过")
        print(f"📝 主要目标: {doc['project_objectives']['primary_goal']}")
        print(f"🎯 设计重点: {[p['label'] for p in doc['design_priorities']]}")
        print(f"📊 洞察评分: {doc['insight_summary']['L5_sharpness_score']}")


# ============================================================================
# v7.151 新增测试：需求洞察交互场景
# ============================================================================


class TestRequirementsInsightInteraction:
    """🆕 v7.151: 测试需求洞察交互场景"""

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt")
    @patch(
        "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
    )
    def test_minor_modification_updates_locally(self, mock_restructure, mock_interrupt):
        """测试微调(<50字符)本地更新，直接前进到 project_director"""
        # 用户提交微调修改
        mock_interrupt.return_value = {"intent": "confirm", "modifications": {"primary_goal": "为50岁男士设计归隐民居"}}  # 微小修改

        mock_restructure.return_value = {
            "metadata": {
                "document_version": "2.0",
                "generation_method": "questionnaire_based_with_ai_insights",
                "llm_enhanced": True,
            },
            "project_objectives": {"primary_goal": "为50岁男士打造田园民居"},
            "constraints": {},
            "design_priorities": [],
            "identified_risks": [],
            "insight_summary": {"L5_sharpness_score": 85},
            "core_tension": {"description": ""},
            "project_essence": "",
            "implicit_requirements": [],
            "key_conflicts": [],
        }

        state = {
            "user_input": "设计田园民居",
            "confirmed_core_tasks": [{"id": "task_1", "title": "核心任务"}],
            "gap_filling_answers": {},
            "selected_dimensions": [],
            "dimension_weights": {},
            "requirement_analysis": {},
            "agent_results": {},
        }

        result = QuestionnaireSummaryNode.execute(state)

        from langgraph.types import Command

        assert isinstance(result, Command)
        assert result.goto == "project_director"  # 微调应该直接前进
        assert result.update["requirements_confirmed"] is True
        assert result.update.get("user_requirement_adjustments") == {"primary_goal": "为50岁男士设计归隐民居"}
        # 验证本地更新了 primary_goal
        assert result.update["restructured_requirements"]["project_objectives"]["primary_goal"] == "为50岁男士设计归隐民居"
        print("✅ 微调测试通过：本地更新，直接到 project_director")

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt")
    @patch(
        "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
    )
    def test_major_modification_triggers_reanalysis(self, mock_restructure, mock_interrupt):
        """测试重大修改(>=50字符)触发重新分析，返回 requirements_analyst"""
        # 用户提交重大修改（超过50字符差异）
        mock_interrupt.return_value = {
            "intent": "confirm",
            "modifications": {
                "primary_goal": "我希望这个项目能够融合传统四合院的精髓与现代极简主义美学，打造一个既有文化底蕴又具有当代舒适性的归隐空间，同时需要考虑到四川地区的气候特点和地形条件"
            },
        }

        mock_restructure.return_value = {
            "metadata": {
                "document_version": "2.0",
                "generation_method": "questionnaire_based_with_ai_insights",
                "llm_enhanced": True,
            },
            "project_objectives": {"primary_goal": "为50岁男士打造田园民居"},
            "constraints": {},
            "design_priorities": [],
            "identified_risks": [],
            "insight_summary": {"L5_sharpness_score": 85},
            "core_tension": {"description": "传统与现代的平衡"},
            "project_essence": "",
            "implicit_requirements": [],
            "key_conflicts": [],
        }

        state = {
            "user_input": "设计田园民居",
            "confirmed_core_tasks": [{"id": "task_1", "title": "核心任务"}],
            "gap_filling_answers": {},
            "selected_dimensions": [],
            "dimension_weights": {},
            "requirement_analysis": {},
            "agent_results": {},
        }

        result = QuestionnaireSummaryNode.execute(state)

        from langgraph.types import Command

        assert isinstance(result, Command)
        assert result.goto == "requirements_analyst"  # 重大修改应该返回重新分析
        assert result.update["requirements_confirmed"] is False
        assert result.update["has_user_modifications"] is True
        assert "【用户修改补充 v7.151】" in result.update["user_input"]
        print("✅ 重大修改测试通过：返回 requirements_analyst 重新分析")

    @patch("intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt")
    @patch(
        "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
    )
    def test_rejection_triggers_reanalysis(self, mock_restructure, mock_interrupt):
        """测试用户拒绝触发重新分析"""
        mock_interrupt.return_value = {"intent": "reject"}  # 用户拒绝

        mock_restructure.return_value = {
            "metadata": {
                "document_version": "2.0",
                "generation_method": "questionnaire_based_with_ai_insights",
                "llm_enhanced": True,
            },
            "project_objectives": {"primary_goal": "为50岁男士打造田园民居"},
            "constraints": {},
            "design_priorities": [],
            "identified_risks": [],
            "insight_summary": {"L5_sharpness_score": 85},
            "core_tension": {"description": ""},
            "project_essence": "",
            "implicit_requirements": [],
            "key_conflicts": [],
        }

        state = {
            "user_input": "设计田园民居",
            "confirmed_core_tasks": [{"id": "task_1", "title": "核心任务"}],
            "gap_filling_answers": {},
            "selected_dimensions": [],
            "dimension_weights": {},
            "requirement_analysis": {},
            "agent_results": {},
        }

        result = QuestionnaireSummaryNode.execute(state)

        from langgraph.types import Command

        assert isinstance(result, Command)
        assert result.goto == "requirements_analyst"  # 拒绝应该返回重新分析
        assert result.update["requirements_confirmed"] is False
        print("✅ 拒绝测试通过：返回 requirements_analyst 重新分析")


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    """直接运行测试"""
    import sys

    print("=" * 80)
    print("需求洞察节点 - 单元测试套件")
    print("=" * 80)

    # 测试1: 数据提取
    print("\n[测试组 1] 问卷数据提取")
    print("-" * 80)
    test1 = TestQuestionnaireDataExtraction()
    try:
        test1.test_extract_complete_questionnaire_data()
        print("✅ 完整数据提取")
    except Exception as e:
        print(f"❌ 完整数据提取失败: {e}")

    try:
        test1.test_extract_partial_data()
        print("✅ 部分数据提取")
    except Exception as e:
        print(f"❌ 部分数据提取失败: {e}")

    # 测试2: 重构引擎
    print("\n[测试组 2] 需求重构引擎")
    print("-" * 80)
    test2 = TestRestructuringEngine()
    try:
        test2.test_successful_restructuring()
        print("✅ 成功重构")
    except Exception as e:
        print(f"❌ 成功重构失败: {e}")

    try:
        test2.test_restructuring_failure_uses_fallback()
        print("✅ 失败降级")
    except Exception as e:
        print(f"❌ 失败降级测试失败: {e}")

    # 测试3: 超时保护 (v7.142)
    print("\n[测试组 3] 异常保护机制 (v7.142)")
    print("-" * 80)
    test3 = TestTimeoutProtection()
    try:
        test3.test_restructuring_exception_triggers_fallback()
    except Exception as e:
        print(f"❌ 异常降级测试失败: {e}")

    try:
        test3.test_fast_restructuring_completes_normally()
        print("✅ 快速完成")
    except Exception as e:
        print(f"❌ 快速完成测试失败: {e}")

    # 测试4: 降级重构
    print("\n[测试组 4] 降级重构逻辑")
    print("-" * 80)
    test4 = TestFallbackRestructure()
    try:
        test4.test_fallback_with_complete_data()
        print("✅ 完整数据降级")
    except Exception as e:
        print(f"❌ 完整数据降级失败: {e}")

    # 测试5: 摘要生成
    print("\n[测试组 5] 摘要文本生成")
    print("-" * 80)
    test5 = TestSummaryTextGeneration()
    try:
        test5.test_generate_full_summary()
        print("✅ 完整摘要生成")
    except Exception as e:
        print(f"❌ 完整摘要生成失败: {e}")

    # 测试6: 集成测试
    print("\n[测试组 6] 集成测试")
    print("-" * 80)
    test6 = TestQuestionnaireeSummaryIntegration()
    try:
        test6.test_complete_flow_with_real_data()
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试完成！使用 pytest 运行完整测试:")
    print("  pytest tests/unit/test_questionnaire_summary.py -v")
    print("=" * 80)
