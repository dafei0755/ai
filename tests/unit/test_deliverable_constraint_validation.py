"""
v8.2 交付物约束实时验证 - 单元测试

测试 DynamicProjectDirector._validate_deliverable_constraints() 方法
验证 constraint_loader 的 must_include/must_exclude 规则在角色选择流程中被正确执行。
"""

from unittest.mock import MagicMock, patch

from intelligent_project_analyzer.agents.dynamic_project_director import (
    DynamicProjectDirector,
    RoleSelection,
    RoleObject,
)
from intelligent_project_analyzer.core.task_oriented_models import (
    TaskInstruction,
    DeliverableSpec,
)


def _make_role(role_id: str, role_name: str = "测试角色") -> RoleObject:
    """辅助函数：创建最小 RoleObject"""
    return RoleObject(
        role_id=role_id,
        role_name=role_name,
        dynamic_role_name=f"测试动态名称_{role_id}",
        task_instruction=TaskInstruction(
            objective=f"{role_name}的任务目标",
            deliverables=[
                DeliverableSpec(
                    name=f"交付物_{role_id}",
                    description=f"由{role_name}完成的交付物",
                    format="analysis",
                    success_criteria=["完成分析", "质量达标"],
                )
            ],
            success_criteria=["整体任务完成", "质量符合预期"],
        ),
    )


def _make_selection(*role_ids: str) -> RoleSelection:
    """辅助函数：创建包含指定角色的 RoleSelection"""
    roles = [_make_role(rid) for rid in role_ids]
    return RoleSelection(
        selected_roles=roles,
        reasoning="测试用的角色选择理由，包含足够长度以通过 min_length=50 的验证要求，这里补充一些额外文字确保通过。",
    )


def _make_dpd() -> DynamicProjectDirector:
    """辅助函数：创建带 mock LLM 的 DPD 实例"""
    mock_llm = MagicMock()
    from intelligent_project_analyzer.core.role_manager import RoleManager

    rm = RoleManager()
    dpd = DynamicProjectDirector(llm_model=mock_llm, role_manager=rm)
    return dpd


class TestDeliverableConstraintValidation:
    """交付物约束验证测试"""

    def test_no_deliverables_skip_validation(self):
        """无 primary_deliverables 时跳过验证"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = None
        selection = _make_selection("4-1", "3-1", "5-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is None, "无交付物时应跳过验证返回 None"

    def test_empty_deliverables_skip_validation(self):
        """空 primary_deliverables 列表跳过验证"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = []
        selection = _make_selection("4-1", "3-1", "5-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is None, "空列表应跳过验证返回 None"

    def test_naming_must_include_v3_pass(self):
        """命名类交付物 + V3 角色 → 验证通过"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [{"type": "naming_list", "description": "为8间包房命名"}]
        # 包含 V3 角色（3-1），满足 must_include: ["V3"]
        selection = _make_selection("3-1", "4-1", "5-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is None, "包含 V3 时命名类交付物应通过验证"

    def test_naming_missing_v3_fail(self):
        """命名类交付物缺少 V3 → 验证失败"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [{"type": "naming_list", "description": "品牌命名"}]
        # 不含 V3 角色
        selection = _make_selection("2-1", "4-1", "5-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is not None, "缺少 V3 时命名类交付物应失败"
        assert "V3" in result, "错误信息应指出缺少 V3"

    def test_naming_must_exclude_v2_v6_fail(self):
        """命名类交付物包含 V2/V6 → 验证失败"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [{"type": "naming_list", "description": "产品命名"}]
        # 包含 V3（满足 must_include）但也包含被禁止的 V2
        selection = _make_selection("3-1", "2-1", "4-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is not None, "包含 V2 时命名类交付物应失败"
        assert "V2" in result, "错误信息应指出 V2 被禁止"

    def test_research_must_include_v4_pass(self):
        """研究报告类交付物 + V4 → 验证通过"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [{"type": "analysis_report", "description": "市场分析报告"}]
        selection = _make_selection("4-1", "3-1", "5-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is None, "包含 V4 时研究类交付物应通过"

    def test_design_strategy_must_include_v2_pass(self):
        """设计策略类交付物 + V2 → 验证通过"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [{"type": "design_strategy", "description": "空间设计策略"}]
        selection = _make_selection("2-1", "4-1", "3-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is None, "包含 V2 时设计策略类交付物应通过"

    def test_synthesized_role_decomposed_for_validation(self):
        """合成角色 (2-1+5-1) 应被拆分为 V2 和 V5 分别验证"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [{"type": "design_strategy", "description": "空间设计策略"}]  # must_include: V2
        # 合成角色包含 V2（2-1+5-1 拆分为 2-1 和 5-1）
        selection = _make_selection("SYNTHESIZED_2-1+5-1", "4-1", "3-1")
        # 修改 role_id 格式模拟真实合成角色
        selection.selected_roles[0].role_id = "SYNTHESIZED_2-1+5-1"
        result = dpd._validate_deliverable_constraints(selection)
        assert result is None, "合成角色 2-1+5-1 应被拆分识别为包含 V2"

    def test_custom_type_always_passes(self):
        """自定义类型交付物无强制约束 → 始终通过"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [{"type": "custom", "description": "自定义交付物"}]
        selection = _make_selection("2-1", "4-1", "6-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is None, "自定义类型应始终通过"

    def test_multiple_deliverables_all_checked(self):
        """多个交付物全部验证"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [
            {"type": "selection_framework", "description": "技术选型框架"},  # must_include: V6, must_exclude: []
            {"type": "design_strategy", "description": "设计策略"},  # must_include: V2, must_exclude: V6? No — ["V6"]
        ]
        # design_strategy excludes V6 but selection_framework requires V6 → conflict
        # 换一个真正兼容的组合：implementation_guide (V6, no exclude) + selection_framework (V6, no exclude)
        dpd._current_primary_deliverables = [
            {"type": "selection_framework", "description": "技术选型框架"},  # must_include: V6, must_exclude: []
            {"type": "implementation_guide", "description": "实施指南"},  # must_include: V6, must_exclude: []
        ]
        selection = _make_selection("6-1", "4-1", "5-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is None, "同时满足所有交付物约束应通过"

    def test_multiple_deliverables_partial_fail(self):
        """多个交付物其中一个不满足 → 失败"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [
            {"type": "naming_list", "description": "命名"},  # must_include: V3
            {"type": "design_strategy", "description": "设计"},  # must_include: V2
        ]
        # 缺少 V3 → naming_list 约束失败
        selection = _make_selection("2-1", "4-1", "5-1")
        result = dpd._validate_deliverable_constraints(selection)
        assert result is not None, "缺少 V3 时 naming_list 约束应触发失败"

    def test_constraint_exception_degrades_gracefully(self):
        """约束验证异常时降级跳过，不阻断流程"""
        dpd = _make_dpd()
        dpd._current_primary_deliverables = [{"type": "naming_list", "description": "命名"}]
        selection = _make_selection("3-1", "4-1", "5-1")

        with patch(
            "intelligent_project_analyzer.utils.constraint_loader.validate_allocation",
            side_effect=RuntimeError("模拟异常"),
        ):
            # 异常时应返回 None（降级跳过），不抛出
            result = dpd._validate_deliverable_constraints(selection)
            assert result is None, "验证异常时应降级返回 None"
