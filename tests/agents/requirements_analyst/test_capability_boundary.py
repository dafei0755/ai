# -*- coding: utf-8 -*-
"""
需求分析师能力边界检测测试
测试系统识别超出能力的需求并正确转化

创建日期: 2026-02-11
"""

import pytest
from intelligent_project_analyzer.agents.requirements_analyst_schema import (
    Phase1Deliverable,
    DeliverableTypeEnum,
    DeliverablePriorityEnum,
    CapabilityCheck,
)


class TestCapabilityBoundaryDetection:
    """测试能力边界检测"""

    def test_cad_drawing_transformation(self):
        """CAD图纸 → 设计策略转化"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.DESIGN_STRATEGY,
            description="空间规划策略（转化自CAD图纸需求）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须包含空间分区思路"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "负责空间规划与设计策略制定",
                "anti_pattern": [],
            },
            capability_check={
                "within_capability": True,
                "original_request": "精确的CAD平面图和立面图",
                "transformed_to": "design_strategy",
                "transformation_reason": "系统输出设计思路和策略，而非执行图纸",
            },
        )

        assert deliverable.capability_check.within_capability is True
        assert deliverable.capability_check.original_request is not None
        assert "CAD" in deliverable.capability_check.original_request
        assert deliverable.type == DeliverableTypeEnum.DESIGN_STRATEGY

    def test_material_list_transformation(self):
        """精确材料清单 → 材料指导转化"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.MATERIAL_GUIDANCE,
            description="材料选择指导原则（转化自精确清单需求）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须提供选择原则和标准"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "负责材料选型指导与评估",
                "anti_pattern": [],
            },
            capability_check={
                "within_capability": True,
                "original_request": "精确材料清单（含型号、规格、数量）",
                "transformed_to": "material_guidance",
                "transformation_reason": "系统提供材料选择原则和指导，而非精确清单",
            },
        )

        assert deliverable.type == DeliverableTypeEnum.MATERIAL_GUIDANCE
        assert "material_guidance" in deliverable.capability_check.transformed_to

    def test_cost_estimate_transformation(self):
        """精确成本估算 → 预算框架转化"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.BUDGET_FRAMEWORK,
            description="预算分配框架（转化自精确成本估算需求）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须提供预算分配原则"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "负责整体预算框架与分配策略",
                "anti_pattern": [],
            },
            capability_check={
                "within_capability": True,
                "original_request": "精确到元的成本估算表",
                "transformed_to": "budget_framework",
                "transformation_reason": "系统提供预算分配框架和原则，而非精确估算",
            },
        )

        assert deliverable.type == DeliverableTypeEnum.BUDGET_FRAMEWORK
        assert "budget_framework" in deliverable.capability_check.transformed_to

    def test_procurement_list_transformation(self):
        """采购清单 → 采购指导转化"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.PROCUREMENT_GUIDANCE,
            description="采购决策指导（转化自精确采购清单需求）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须提供采购决策原则"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "负责采购策略指导与供应商评估",
                "anti_pattern": [],
            },
            capability_check={
                "within_capability": True,
                "original_request": "可执行的采购清单（含供应商、价格）",
                "transformed_to": "procurement_guidance",
                "transformation_reason": "系统提供采购决策指导，而非可执行清单",
            },
        )

        assert deliverable.type == DeliverableTypeEnum.PROCUREMENT_GUIDANCE
        assert "procurement_guidance" in deliverable.capability_check.transformed_to

    def test_technical_spec_transformation(self):
        """技术规范 → 选型框架转化"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.SELECTION_FRAMEWORK,
            description="设备选型决策框架（转化自技术规范需求）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须提供选型决策标准"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "负责设备选型框架与技术评估",
                "anti_pattern": [],
            },
            capability_check={
                "within_capability": True,
                "original_request": "详细技术规范书（含参数、标准）",
                "transformed_to": "selection_framework",
                "transformation_reason": "系统提供选型决策框架，而非技术规范",
            },
        )

        assert deliverable.type == DeliverableTypeEnum.SELECTION_FRAMEWORK
        assert "selection_framework" in deliverable.capability_check.transformed_to


class TestWithinCapabilityRequests:
    """测试在能力范围内的需求"""

    def test_naming_within_capability(self):
        """命名任务在能力范围内"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.NAMING_LIST,
            description="品牌命名方案（创意命名与品牌塑造）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须提供创意命名"],
            deliverable_owner_suggestion={
                "primary_owner": "V3_叙事专家",
                "owner_rationale": "命名创意是叙事专家的核心能力",
                "anti_pattern": [],
            },
            capability_check={"within_capability": True},  # 无需转化
        )

        assert deliverable.capability_check.within_capability is True
        assert deliverable.capability_check.original_request is None

    def test_strategy_within_capability(self):
        """策略制定在能力范围内"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.DESIGN_STRATEGY,
            description="设计策略方案（整体设计思路与策略）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须包含设计思路"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "负责整体设计策略的制定与把控",
                "anti_pattern": [],
            },
            capability_check={"within_capability": True},  # 无需转化
        )

        assert deliverable.capability_check.within_capability is True

    def test_analysis_within_capability(self):
        """分析报告在能力范围内"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.ANALYSIS_REPORT,
            description="用户行为分析报告（深度洞察与策略建议）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须包含深度洞察"],
            deliverable_owner_suggestion={
                "primary_owner": "V4_设计研究员",
                "owner_rationale": "设计研究分析是核心专业能力",
                "anti_pattern": [],
            },
            capability_check={"within_capability": True},  # 无需转化
        )

        assert deliverable.capability_check.within_capability is True


class TestCapabilityCheckModel:
    """测试CapabilityCheck模型"""

    def test_capability_check_full_transformation(self):
        """完整转化信息"""
        check = CapabilityCheck(
            within_capability=True,
            original_request="用户要求的精确CAD图纸",
            transformed_to="design_strategy",
            transformation_reason="系统能力是策略层而非执行层",
        )

        assert check.within_capability is True
        assert check.original_request is not None
        assert check.transformed_to is not None
        assert check.transformation_reason is not None

    def test_capability_check_no_transformation(self):
        """无需转化"""
        check = CapabilityCheck(within_capability=True)

        assert check.within_capability is True
        assert check.original_request is None
        assert check.transformed_to is None
        assert check.transformation_reason is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
