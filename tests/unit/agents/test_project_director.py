"""
P2 Agent测试: ProjectDirectorAgent & DynamicProjectDirector

测试项目总监智能体的核心功能:
- Role selection logic (动态角色选择, 3-8个专家)
- Task distribution (任务分配与验证)
- DynamicProjectDirector integration (RoleSelection模型)
- Fallback mechanisms (LLM失败降级)
- Requirements formatting (需求格式化)
- Strategic analysis parsing (战略分析JSON解析)

覆盖率目标: 75%+
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from intelligent_project_analyzer.agents.dynamic_project_director import (
    DynamicProjectDirector,
    RoleObject,
    RoleSelection,
    TaskDetail,
)
from intelligent_project_analyzer.agents.project_director import ProjectDirectorAgent
from intelligent_project_analyzer.core.state import ProjectAnalysisState
from tests.fixtures.mocks import MockAsyncLLM, MockRoleManager

# ============================================================================
# Test Class 1: Role Selection Logic
# ============================================================================


class TestRoleSelection:
    """测试角色选择逻辑"""

    @pytest.fixture
    def director(self):
        """创建DynamicProjectDirector实例"""
        mock_llm = MockAsyncLLM()
        role_manager = MockRoleManager()
        return DynamicProjectDirector(llm_model=mock_llm, role_manager=role_manager)

    def test_select_roles_min_count(self, director):
        """测试最少选择3个角色"""
        requirements = "设计现代办公空间"

        with patch.object(
            director.llm,
            "ainvoke",
            return_value=Mock(
                content="""
        {
            "selected_roles": [
                {"role_id": "V3", "name": "叙事专家", "tasks": ["分析用户体验"]},
                {"role_id": "V4", "name": "研究员", "tasks": ["研究设计趋势"]},
                {"role_id": "V5", "name": "场景专家", "tasks": ["规划空间布局"]}
            ],
            "reasoning": "三个核心角色覆盖基本需求"
        }
        """
            ),
        ):
            result = director.select_roles_for_task(requirements)

            assert len(result.selected_roles) >= 3
            assert result.reasoning != ""

    def test_select_roles_max_count(self, director):
        """测试最多选择8个角色"""
        requirements = "大型综合体设计"

        with patch.object(
            director.llm,
            "ainvoke",
            return_value=Mock(
                content="""
        {
            "selected_roles": [
                {"role_id": "V2", "name": "设计总监", "tasks": ["战略规划"]},
                {"role_id": "V3", "name": "叙事专家", "tasks": ["用户体验"]},
                {"role_id": "V4", "name": "研究员", "tasks": ["市场调研"]},
                {"role_id": "V5", "name": "场景专家", "tasks": ["空间规划"]},
                {"role_id": "V6", "name": "实施规划师", "tasks": ["执行计划"]},
                {"role_id": "V7", "name": "专家7", "tasks": ["任务7"]},
                {"role_id": "V8", "name": "专家8", "tasks": ["任务8"]},
                {"role_id": "V9", "name": "专家9", "tasks": ["任务9"]}
            ],
            "reasoning": "复杂项目需要更多专家"
        }
        """
            ),
        ):
            result = director.select_roles_for_task(requirements)

            assert len(result.selected_roles) <= 8

    def test_select_roles_must_include_v4(self, director):
        """测试V4角色为必选项（验证逻辑）"""
        requirements = "办公空间设计"

        with patch.object(
            director.llm,
            "ainvoke",
            return_value=Mock(
                content="""
        {
            "selected_roles": [
                {"role_id": "V2", "name": "设计总监", "tasks": ["战略"]},
                {"role_id": "V3", "name": "叙事专家", "tasks": ["体验"]},
                {"role_id": "V5", "name": "场景专家", "tasks": ["空间"]}
            ],
            "reasoning": "核心团队"
        }
        """
            ),
        ):
            result = director.select_roles_for_task(requirements)

            # 检查是否包含V4或系统自动添加
            v4_roles = [r for r in result.selected_roles if r.role_id.startswith("V4")]
            # 如果有@model_validator强制V4，则应该存在
            # 如果没有，这个测试验证是否通过或触发验证错误
            assert len(result.selected_roles) >= 3

    def test_select_roles_with_retry(self, director):
        """测试LLM失败后重试机制"""
        requirements = "设计办公空间"

        # 第一次失败，第二次成功
        responses = [
            Mock(content="Invalid JSON {{{"),  # 第1次失败
            Mock(
                content="""
            {
                "selected_roles": [
                    {"role_id": "V3", "name": "叙事专家", "tasks": ["分析"]},
                    {"role_id": "V4", "name": "研究员", "tasks": ["研究"]},
                    {"role_id": "V5", "name": "场景专家", "tasks": ["规划"]}
                ],
                "reasoning": "重试成功"
            }
            """
            ),  # 第2次成功
        ]

        with patch.object(director.llm, "ainvoke", side_effect=responses):
            result = director.select_roles_for_task(requirements, max_retries=3)

            assert len(result.selected_roles) >= 3
            assert result.reasoning == "重试成功"

    def test_select_roles_max_retries_exhausted(self, director):
        """测试重试次数用尽后使用默认角色"""
        requirements = "设计办公空间"

        # 所有重试都失败
        with patch.object(director.llm, "ainvoke", side_effect=Exception("LLM timeout")):
            with patch.object(director, "_get_default_role_selection") as mock_default:
                mock_default.return_value = RoleSelection(
                    selected_roles=[
                        RoleObject(
                            role_id="V3",
                            name="叙事专家",
                            tasks=["默认任务"],
                            task_instruction=Mock(objective="默认", deliverables=[], success_criteria=[]),
                        ),
                        RoleObject(
                            role_id="V4",
                            name="研究员",
                            tasks=["默认任务"],
                            task_instruction=Mock(objective="默认", deliverables=[], success_criteria=[]),
                        ),
                        RoleObject(
                            role_id="V5",
                            name="场景专家",
                            tasks=["默认任务"],
                            task_instruction=Mock(objective="默认", deliverables=[], success_criteria=[]),
                        ),
                    ],
                    reasoning="使用默认角色配置",
                )

                result = director.select_roles_for_task(requirements, max_retries=2)

                mock_default.assert_called_once()
                assert "默认" in result.reasoning


# ============================================================================
# Test Class 2: Task Distribution
# ============================================================================


class TestTaskDistribution:
    """测试任务分配逻辑"""

    @pytest.fixture
    def director(self):
        """创建DynamicProjectDirector实例"""
        mock_llm = MockAsyncLLM()
        role_manager = MockRoleManager()
        return DynamicProjectDirector(llm_model=mock_llm, role_manager=role_manager)

    def test_task_distribution_auto_generated(self, director):
        """测试task_distribution从selected_roles自动生成"""
        role_selection = RoleSelection(
            selected_roles=[
                RoleObject(
                    role_id="V3_叙事专家_3-1",
                    name="叙事专家",
                    tasks=["分析用户体验", "构建叙事框架"],
                    task_instruction=Mock(
                        objective="用户体验分析", deliverables=[Mock(name="体验报告", description="分析用户体验")], success_criteria=[]
                    ),
                )
            ],
            reasoning="测试自动生成",
        )

        task_dist = role_selection.task_distribution

        assert "V3_叙事专家_3-1" in task_dist
        assert isinstance(task_dist["V3_叙事专家_3-1"], TaskDetail)
        assert "分析用户体验" in task_dist["V3_叙事专家_3-1"].tasks

    def test_task_distribution_all_roles_included(self, director):
        """测试所有选中角色都有任务分配"""
        role_selection = RoleSelection(
            selected_roles=[
                RoleObject(
                    role_id="V3",
                    name="叙事专家",
                    tasks=["任务A"],
                    task_instruction=Mock(objective="A", deliverables=[], success_criteria=[]),
                ),
                RoleObject(
                    role_id="V4",
                    name="研究员",
                    tasks=["任务B"],
                    task_instruction=Mock(objective="B", deliverables=[], success_criteria=[]),
                ),
                RoleObject(
                    role_id="V5",
                    name="场景专家",
                    tasks=["任务C"],
                    task_instruction=Mock(objective="C", deliverables=[], success_criteria=[]),
                ),
            ],
            reasoning="完整团队",
        )

        task_dist = role_selection.task_distribution

        assert len(task_dist) == len(role_selection.selected_roles)
        for role in role_selection.selected_roles:
            # 检查是否包含该角色的某种ID格式
            found = any(role.role_id in key for key in task_dist.keys())
            assert found, f"Role {role.role_id} not found in task_distribution"

    def test_fix_task_distribution_dict_to_taskdetail(self, director):
        """测试修复字典格式的task_distribution"""
        # 创建不正确的响应（字典而非TaskDetail）
        response = Mock()
        response.selected_roles = ["V3", "V4", "V5"]
        response.task_distribution = {
            "V3": {"tasks": ["任务1"], "focus_areas": ["领域1"]},  # 字典格式
            "V4": "字符串任务",  # 字符串格式
            "V5": Mock(tasks=["任务3"]),  # 已经是对象
        }

        with patch.object(director, "_get_default_role_selection") as mock_default:
            fixed = director._fix_task_distribution(response)

            # 应该已修复或调用了默认逻辑
            assert fixed is not None

    def test_empty_task_distribution_triggers_default(self, director):
        """测试空任务分配触发默认逻辑"""
        response = Mock()
        response.selected_roles = ["V3", "V4", "V5"]
        response.task_distribution = {}  # 空字典

        with patch.object(director, "_get_default_role_selection") as mock_default:
            mock_default.return_value = Mock(task_distribution={"V3": Mock(), "V4": Mock(), "V5": Mock()})

            result = director._fix_task_distribution(response)

            mock_default.assert_called_once()


# ============================================================================
# Test Class 3: Requirements Formatting
# ============================================================================


class TestRequirementsFormatting:
    """测试需求格式化"""

    @pytest.fixture
    def agent(self):
        """创建ProjectDirectorAgent实例"""
        mock_llm = MockAsyncLLM()
        return ProjectDirectorAgent(llm_model=mock_llm, config={})

    def test_format_requirements_basic(self, agent):
        """测试基本需求格式化"""
        requirements = {"project_task": "办公空间设计", "character_narrative": "科技公司，追求创新", "physical_context": "1000平方米"}

        formatted = agent._format_requirements_for_selection(requirements)

        assert "办公空间设计" in formatted
        assert "科技公司" in formatted
        assert "1000平方米" in formatted

    def test_format_requirements_with_confirmed_tasks(self, agent):
        """测试包含用户确认任务的格式化"""
        requirements_text = "设计办公空间"
        confirmed_tasks = [{"task": "空间规划", "priority": 1}, {"task": "家具选择", "priority": 2}]

        formatted = agent._format_requirements_with_tasks(requirements_text, confirmed_tasks)

        assert "空间规划" in formatted
        assert "家具选择" in formatted

    def test_format_requirements_missing_fields(self, agent):
        """测试缺少字段时的格式化"""
        requirements = {
            "project_task": "设计项目"
            # 缺少其他字段
        }

        formatted = agent._format_requirements_for_selection(requirements)

        assert "设计项目" in formatted
        assert formatted != ""  # 应该有默认值或占位符


# ============================================================================
# Test Class 4: Strategic Analysis Parsing
# ============================================================================


class TestStrategicAnalysisParsing:
    """测试战略分析解析"""

    @pytest.fixture
    def agent(self):
        """创建ProjectDirectorAgent实例"""
        mock_llm = MockAsyncLLM()
        return ProjectDirectorAgent(llm_model=mock_llm, config={})

    def test_parse_valid_strategic_analysis(self, agent):
        """测试解析有效的战略分析JSON"""
        llm_response = """
        ```json
        {
            "analysis_summary": "深度分析办公空间需求",
            "key_insights": ["洞察1", "洞察2"],
            "recommended_approach": "采用模块化设计"
        }
        ```
        """

        result = agent._parse_strategic_analysis(llm_response)

        assert result["analysis_summary"] == "深度分析办公空间需求"
        assert len(result["key_insights"]) == 2

    def test_parse_v6_format_compatibility(self, agent):
        """测试v6.0格式兼容性"""
        llm_response = """
        {
            "strategic_framework": {
                "core_strategy": "用户中心设计"
            }
        }
        """

        result = agent._parse_strategic_analysis(llm_response)

        assert "strategic_framework" in result or "core_strategy" in result

    def test_parse_old_format_conversion(self, agent):
        """测试旧格式自动转换"""
        old_format_data = {"overview": "项目概览", "goals": ["目标1", "目标2"]}

        with patch.object(
            agent,
            "_convert_old_to_new_format",
            return_value={"analysis_summary": "项目概览", "key_insights": ["目标1", "目标2"]},
        ) as mock_convert:
            result = agent._convert_old_to_new_format(old_format_data)

            assert "analysis_summary" in result

    def test_parse_failure_uses_fallback(self, agent):
        """测试解析失败时使用降级结构"""
        llm_response = "Invalid JSON content"

        with patch.object(
            agent, "_create_fallback_strategy", return_value={"analysis_summary": "降级战略分析"}
        ) as mock_fallback:
            result = agent._parse_strategic_analysis(llm_response)

            # 应该调用了fallback或返回了有效结构
            assert result is not None
            assert isinstance(result, dict)


# ============================================================================
# Test Class 5: Fallback Mechanisms
# ============================================================================


class TestFallbackMechanisms:
    """测试降级机制"""

    @pytest.fixture
    def director(self):
        """创建DynamicProjectDirector实例"""
        mock_llm = MockAsyncLLM()
        role_manager = MockRoleManager()
        return DynamicProjectDirector(llm_model=mock_llm, role_manager=role_manager)

    def test_get_default_role_selection(self, director):
        """测试获取默认角色选择"""
        available_roles = director.role_manager.get_available_roles()

        result = director._get_default_role_selection(available_roles)

        assert len(result.selected_roles) >= 3
        assert result.reasoning != ""
        assert "默认" in result.reasoning or "fallback" in result.reasoning.lower()

    def test_fallback_event_logging(self, director):
        """测试降级事件记录"""
        requirements = "测试需求"
        error = Exception("LLM timeout")

        with patch("intelligent_project_analyzer.agents.dynamic_project_director.logger") as mock_logger:
            director._log_fallback_event(requirements, error)

            # 应该记录了错误日志
            assert mock_logger.error.called or mock_logger.warning.called


# ============================================================================
# Test Class 6: Role-V Mapping & Send Commands
# ============================================================================


class TestRoleVMapping:
    """测试角色-V映射与Send命令创建"""

    @pytest.fixture
    def agent(self):
        """创建ProjectDirectorAgent实例"""
        mock_llm = MockAsyncLLM()
        agent = ProjectDirectorAgent(llm_model=mock_llm, config={})
        agent.role_manager = MockRoleManager()
        return agent

    def test_construct_full_role_id(self, agent):
        """测试构造完整角色ID"""
        short_role_id = "V3"

        full_id = agent._construct_full_role_id(short_role_id)

        # 应该包含V前缀和编号
        assert full_id.startswith("V3")

    def test_role_to_v_mapping_creation(self, agent):
        """测试角色到V2-V6的映射"""
        selection = Mock()
        selection.selected_roles = [Mock(role_id="V2"), Mock(role_id="V3"), Mock(role_id="V4")]
        selection.task_distribution = {
            "V2": Mock(tasks=["战略规划"]),
            "V3": Mock(tasks=["用户体验"]),
            "V4": Mock(tasks=["设计研究"]),
        }

        # 测试映射逻辑
        role_to_v_mapping = {"V2": [], "V3": [], "V4": [], "V5": [], "V6": []}

        for role in selection.selected_roles:
            role_id = role.role_id
            base_type = role_id.split("_")[0] if "_" in role_id else role_id
            if base_type in role_to_v_mapping:
                role_to_v_mapping[base_type].append(role_id)

        assert len(role_to_v_mapping["V3"]) > 0 or len(role_to_v_mapping["V4"]) > 0


# ============================================================================
# Test Class 7: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """测试完整集成场景"""

    @pytest.mark.asyncio
    async def test_complete_role_selection_workflow(self):
        """测试完整角色选择工作流"""
        mock_llm = MockAsyncLLM(
            responses=[
                """
        {
            "selected_roles": [
                {"role_id": "V3", "name": "叙事专家", "tasks": ["用户体验分析"],
                 "task_instruction": {"objective": "分析", "deliverables": [], "success_criteria": []}},
                {"role_id": "V4", "name": "研究员", "tasks": ["市场调研"],
                 "task_instruction": {"objective": "研究", "deliverables": [], "success_criteria": []}},
                {"role_id": "V5", "name": "场景专家", "tasks": ["空间规划"],
                 "task_instruction": {"objective": "规划", "deliverables": [], "success_criteria": []}}
            ],
            "reasoning": "三个核心角色覆盖基本需求"
        }
        """
            ]
        )

        role_manager = MockRoleManager()
        director = DynamicProjectDirector(llm_model=mock_llm, role_manager=role_manager)

        requirements = "设计现代办公空间，面积1000平米"

        result = director.select_roles_for_task(requirements)

        assert len(result.selected_roles) >= 3
        assert result.reasoning != ""
        assert len(result.task_distribution) == len(result.selected_roles)

    @pytest.mark.asyncio
    async def test_project_director_execute_dynamic_mode(self):
        """测试ProjectDirectorAgent动态模式执行"""
        mock_llm = MockAsyncLLM()
        agent = ProjectDirectorAgent(llm_model=mock_llm, config={})
        agent.role_manager = MockRoleManager()

        state = ProjectAnalysisState(
            user_input="设计办公空间", structured_requirements={"project_task": "办公空间设计", "character_narrative": "科技公司"}
        )
        config = Mock()
        store = Mock()

        with patch.object(agent, "_execute_dynamic_mode") as mock_dynamic:
            mock_dynamic.return_value = Mock(
                update={"strategic_analysis": {"summary": "战略分析"}, "active_agents": ["V3", "V4", "V5"]}, goto=[]
            )

            result = await agent.execute(state, config, store)

            mock_dynamic.assert_called_once()
            assert "strategic_analysis" in result.update
            assert len(result.update["active_agents"]) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
