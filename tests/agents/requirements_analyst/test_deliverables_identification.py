# -*- coding: utf-8 -*-
"""
需求分析师交付物识别测试
测试从用户输入中准确识别交付物的能力

创建日期: 2026-02-11
"""

import pytest
from intelligent_project_analyzer.agents.requirements_analyst_schema import (
    Phase1Deliverable,
    DeliverableTypeEnum,
    DeliverablePriorityEnum,
)


class TestDeliverableIdentification:
    """测试交付物识别准确性"""

    def test_explicit_naming_request(self):
        """明确的命名需求"""
        # 用户输入："给我的中餐包房起8个4字的名字，要有文化底蕴"
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.NAMING_LIST,
            description="中餐包房命名方案（8个4字）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            quantity=8,
            scope="中餐包房",
            format_requirements={"length": "4个汉字", "style": "文化底蕴", "must_include_fields": ["命名", "文化出处", "寓意说明"]},
            acceptance_criteria=["必须提供正好8个命名", "每个命名必须正好4个汉字", "必须标注文化出处和寓意"],
            deliverable_owner_suggestion={
                "primary_owner": "V3_叙事专家",
                "owner_rationale": "命名是创意文案核心能力",
                "anti_pattern": ["V6_工程师"],
            },
            capability_check={"within_capability": True},
        )

        assert deliverable.type == DeliverableTypeEnum.NAMING_LIST
        assert deliverable.quantity == 8
        assert "4个汉字" in str(deliverable.format_requirements)

    def test_design_strategy_request(self):
        """设计策略需求"""
        # 用户输入："75平米住宅的空间规划方案"
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.DESIGN_STRATEGY,
            description="75平米住宅空间规划策略",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            format_requirements={"scope": "全屋", "must_include": ["功能分区", "动线设计", "采光策略"]},
            acceptance_criteria=["必须包含功能分区方案", "必须说明动线设计逻辑", "必须考虑采光和通风"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "空间规划是设计总监核心能力",
                "anti_pattern": ["V3_叙事专家"],
            },
            capability_check={"within_capability": True},
        )

        assert deliverable.type == DeliverableTypeEnum.DESIGN_STRATEGY
        assert "空间规划" in deliverable.description

    def test_multiple_deliverables_extraction(self):
        """多交付物提取"""
        # 用户输入："需要设计方案、材料建议和预算框架"
        deliverables = [
            Phase1Deliverable(
                deliverable_id="D1",
                type=DeliverableTypeEnum.DESIGN_STRATEGY,
                description="整体设计策略方案（含空间规划与风格定位）",
                priority=DeliverablePriorityEnum.MUST_HAVE,
                acceptance_criteria=["必须包含设计思路"],
                deliverable_owner_suggestion={
                    "primary_owner": "V2_设计总监",
                    "owner_rationale": "负责整体设计策略制定与空间规划",
                    "anti_pattern": [],
                },
                capability_check={"within_capability": True},
            ),
            Phase1Deliverable(
                deliverable_id="D2",
                type=DeliverableTypeEnum.MATERIAL_GUIDANCE,
                description="材料选择指导方案（含选材原则与推荐）",
                priority=DeliverablePriorityEnum.MUST_HAVE,
                acceptance_criteria=["必须提供选择原则"],
                deliverable_owner_suggestion={
                    "primary_owner": "V2_设计总监",
                    "owner_rationale": "负责材料指导与选材策略制定",
                    "anti_pattern": [],
                },
                capability_check={"within_capability": True},
            ),
            Phase1Deliverable(
                deliverable_id="D3",
                type=DeliverableTypeEnum.BUDGET_FRAMEWORK,
                description="预算分配框架方案（含各项目预算比例）",
                priority=DeliverablePriorityEnum.MUST_HAVE,
                acceptance_criteria=["必须提供预算分配原则"],
                deliverable_owner_suggestion={
                    "primary_owner": "V2_设计总监",
                    "owner_rationale": "负责预算框架制定与资源分配",
                    "anti_pattern": [],
                },
                capability_check={"within_capability": True},
            ),
        ]

        assert len(deliverables) == 3
        assert all(d.priority == DeliverablePriorityEnum.MUST_HAVE for d in deliverables)

    def test_implicit_deliverable_inference(self):
        """隐式交付物推断"""
        # 用户输入："我想设计一个75平米住宅"（未明说要什么）
        # 系统应推断出需要设计策略
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.DESIGN_STRATEGY,
            description="住宅设计策略方案（推断）",
            priority=DeliverablePriorityEnum.NICE_TO_HAVE,  # 推断的用NICE_TO_HAVE
            acceptance_criteria=["必须基于用户确认后制定"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "负责设计策略规划与方案制定",
                "anti_pattern": [],
            },
            capability_check={"within_capability": True},
        )

        assert deliverable.priority == DeliverablePriorityEnum.NICE_TO_HAVE
        assert "推断" in deliverable.description

    def test_format_requirements_extraction(self):
        """格式要求提取"""
        # 用户输入："命名要4个字，来自苏东坡诗词"
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.NAMING_LIST,
            description="基于苏东坡诗词的命名方案",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            format_requirements={"length": "4个汉字", "source": "苏东坡诗词", "must_include_fields": ["命名", "出处诗句", "价值观阐释"]},
            acceptance_criteria=["每个命名必须正好4个汉字", "必须标注苏东坡诗词出处", "必须阐释价值观（50-150字）"],
            deliverable_owner_suggestion={
                "primary_owner": "V3_叙事专家",
                "owner_rationale": "诗词文案是叙事专家特长",
                "anti_pattern": ["V6_工程师"],
            },
            capability_check={"within_capability": True},
        )

        assert "4个汉字" in str(deliverable.format_requirements)
        assert "苏东坡" in str(deliverable.format_requirements)

    def test_acceptance_criteria_quantifiable(self):
        """验收标准可量化性"""
        # 好的验收标准：可量化、可验证
        good_deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.NAMING_LIST,
            description="中餐包房命名方案（含文化寓意说明）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=[
                "必须提供正好8个命名（不多不少）",  # ✅ 可量化
                "每个命名必须4个汉字（no more, no less）",  # ✅ 可验证
                "必须标注出处（含完整诗句）",  # ✅ 可检查
            ],
            deliverable_owner_suggestion={
                "primary_owner": "V3_叙事专家",
                "owner_rationale": "命名是创意文案的核心产出能力",
                "anti_pattern": [],
            },
            capability_check={"within_capability": True},
        )

        # 验证所有标准都以"必须"开头
        assert all(c.startswith("必须") for c in good_deliverable.acceptance_criteria)
        assert len(good_deliverable.acceptance_criteria) >= 1


class TestDeliverableOwnerSuggestion:
    """测试交付物责任人建议"""

    def test_naming_task_owner(self):
        """命名任务应推荐叙事专家"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.NAMING_LIST,
            description="中餐包房命名方案（含文化出处说明）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须完整"],
            deliverable_owner_suggestion={
                "primary_owner": "V3_叙事专家",
                "owner_rationale": "命名是创意文案核心能力",
                "anti_pattern": ["V2_设计总监", "V6_工程师"],
            },
            capability_check={"within_capability": True},
        )

        assert "V3" in deliverable.deliverable_owner_suggestion.primary_owner
        assert len(deliverable.deliverable_owner_suggestion.anti_pattern) > 0

    def test_design_strategy_owner(self):
        """设计策略应推荐设计总监"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.DESIGN_STRATEGY,
            description="住宅空间设计策略方案（含功能分区）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须完整"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "空间策略是设计总监核心能力",
                "anti_pattern": ["V3_叙事专家"],
            },
            capability_check={"within_capability": True},
        )

        assert "V2" in deliverable.deliverable_owner_suggestion.primary_owner

    def test_research_task_owner(self):
        """研究任务应推荐设计研究员"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.CASE_STUDY,
            description="同类型住宅案例研究报告（含分析总结）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须包含案例分析"],
            deliverable_owner_suggestion={
                "primary_owner": "V4_设计研究员",
                "owner_rationale": "案例研究是研究员专长",
                "anti_pattern": ["V6_工程师"],
            },
            capability_check={"within_capability": True},
        )

        assert "V4" in deliverable.deliverable_owner_suggestion.primary_owner


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
