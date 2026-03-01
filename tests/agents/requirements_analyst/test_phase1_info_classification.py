# -*- coding: utf-8 -*-
"""
需求分析师 Phase1 信息分类测试
测试Phase1的信息充足性判断逻辑

创建日期: 2026-02-11
"""

import pytest
from intelligent_project_analyzer.agents.requirements_analyst_schema import (
    Phase1Output,
    Phase1Deliverable,
    DeliverableTypeEnum,
    DeliverablePriorityEnum,
)


class TestPhase1InfoClassification:
    """测试Phase1信息充足性判断"""

    def test_sufficient_info_standard_case(self):
        """标准充足信息输入"""
        # 模拟Phase1输出：信息充足的标准案例
        output = Phase1Output(
            phase=1,
            info_status="sufficient",
            info_status_reason="包含项目类型、用户画像、空间约束、预算、功能需求，信息完整",
            info_gaps=[],
            project_type_preliminary="personal_residential",
            project_summary="75平米现代简约风格住宅设计项目，业主为单身职场女性，需兼顾日常居住与内容创作功能需求",
            primary_deliverables=[
                Phase1Deliverable(
                    deliverable_id="D1",
                    type=DeliverableTypeEnum.DESIGN_STRATEGY,
                    description="75平米住宅空间规划策略方案",
                    priority=DeliverablePriorityEnum.MUST_HAVE,
                    acceptance_criteria=["必须包含功能分区", "必须考虑采光"],
                    deliverable_owner_suggestion={
                        "primary_owner": "V2_设计总监",
                        "owner_rationale": "空间规划是设计总监的核心能力",
                        "anti_pattern": ["V3_叙事专家"],
                    },
                    capability_check={"within_capability": True},
                )
            ],
            recommended_next_step="phase2_analysis",
            next_step_reason="信息充足，可直接进行深度分析，包含项目类型和用户画像",
        )

        # 验证
        assert output.info_status == "sufficient"
        assert output.recommended_next_step == "phase2_analysis"
        assert len(output.primary_deliverables) >= 1

    def test_insufficient_info_vague_case(self):
        """模糊输入案例"""
        output = Phase1Output(
            phase=1,
            info_status="insufficient",
            info_status_reason="用户需求过于模糊，缺乏具体场景约束条件和项目详细信息",
            info_gaps=["缺失用户身份和角色", "缺失空间约束（面积、户型）", "缺失预算范围"],
            project_type_preliminary="residential",
            project_summary="用户希望装修房子，但未提供具体的空间面积、户型、预算等关键信息，需进一步收集",
            primary_deliverables=[
                Phase1Deliverable(
                    deliverable_id="D1",
                    type=DeliverableTypeEnum.DESIGN_STRATEGY,
                    description="住宅设计策略（待用户补充信息后细化）",
                    priority=DeliverablePriorityEnum.MUST_HAVE,
                    acceptance_criteria=["必须基于补充信息制定具体方案"],
                    deliverable_owner_suggestion={
                        "primary_owner": "V2_设计总监",
                        "owner_rationale": "空间设计策略制定是核心能力",
                        "anti_pattern": [],
                    },
                    capability_check={"within_capability": True},
                )
            ],
            recommended_next_step="questionnaire_first",
            next_step_reason="信息不足，需要通过问卷收集关键项目信息和用户偏好",
        )

        # 验证
        assert output.info_status == "insufficient"
        assert len(output.info_gaps) >= 3
        assert output.recommended_next_step == "questionnaire_first"

    def test_logic_validation_sufficient_with_too_many_gaps(self):
        """测试逻辑验证：信息充足但缺失项过多"""
        with pytest.raises(ValueError, match="信息充足时不应有过多缺失项"):
            Phase1Output(
                phase=1,
                info_status="sufficient",
                info_status_reason="信息基本充足，包含了项目类型和基本需求信息",
                info_gaps=["gap1", "gap2", "gap3"],  # 超过2个
                project_type_preliminary="residential",
                project_summary="测试项目概要，包含住宅设计类型、用户画像和空间约束条件信息。",
                primary_deliverables=[
                    Phase1Deliverable(
                        deliverable_id="D1",
                        type=DeliverableTypeEnum.DESIGN_STRATEGY,
                        description="整体设计策略方案（含空间规划）",
                        priority=DeliverablePriorityEnum.MUST_HAVE,
                        acceptance_criteria=["必须完整"],
                        deliverable_owner_suggestion={
                            "primary_owner": "V2_设计总监",
                            "owner_rationale": "负责设计策略规划与方案制定",
                            "anti_pattern": [],
                        },
                        capability_check={"within_capability": True},
                    )
                ],
                recommended_next_step="phase2_analysis",
                next_step_reason="进入深度分析，制定详细设计方案和任务规划",
            )

    def test_logic_validation_insufficient_recommends_phase2(self):
        """测试逻辑验证：信息不足却推荐Phase2"""
        with pytest.raises(ValueError, match="信息不足时应推荐问卷"):
            Phase1Output(
                phase=1,
                info_status="insufficient",
                info_status_reason="用户提供的信息不足，缺少关键项目约束条件",
                info_gaps=["缺失用户画像", "缺失预算"],
                project_type_preliminary="residential",
                project_summary="测试项目概要，包含住宅设计类型、用户画像和空间约束条件信息。",
                primary_deliverables=[
                    Phase1Deliverable(
                        deliverable_id="D1",
                        type=DeliverableTypeEnum.DESIGN_STRATEGY,
                        description="整体设计策略方案（含空间规划）",
                        priority=DeliverablePriorityEnum.MUST_HAVE,
                        acceptance_criteria=["必须完整"],
                        deliverable_owner_suggestion={
                            "primary_owner": "V2_设计总监",
                            "owner_rationale": "负责设计策略规划与方案制定",
                            "anti_pattern": [],
                        },
                        capability_check={"within_capability": True},
                    )
                ],
                recommended_next_step="phase2_analysis",  # 错误：应该是questionnaire_first
                next_step_reason="不合理的推荐，信息不足时不应直接进入分析",
            )

    def test_logic_validation_no_must_have_deliverable(self):
        """测试逻辑验证：缺少MUST_HAVE交付物"""
        with pytest.raises(ValueError, match="至少需要一个MUST_HAVE优先级的交付物"):
            Phase1Output(
                phase=1,
                info_status="sufficient",
                info_status_reason="信息充足，包含项目类型和基本需求，可进入深度分析阶段",
                info_gaps=[],
                project_type_preliminary="residential",
                project_summary="测试项目概要，包含住宅设计类型、用户画像和空间约束条件信息。",
                primary_deliverables=[
                    Phase1Deliverable(
                        deliverable_id="D1",
                        type=DeliverableTypeEnum.DESIGN_STRATEGY,
                        description="整体设计策略方案（含空间规划）",
                        priority=DeliverablePriorityEnum.NICE_TO_HAVE,  # 全是NICE_TO_HAVE
                        acceptance_criteria=["必须完整"],
                        deliverable_owner_suggestion={
                            "primary_owner": "V2_设计总监",
                            "owner_rationale": "负责设计策略规划与方案制定",
                            "anti_pattern": [],
                        },
                        capability_check={"within_capability": True},
                    )
                ],
                recommended_next_step="phase2_analysis",
                next_step_reason="进入深度分析，制定详细设计方案和任务规划",
            )


class TestPhase1DeliverableIdentification:
    """测试Phase1交付物识别"""

    def test_naming_task_identification(self):
        """命名任务识别"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.NAMING_LIST,
            description="中餐包房命名方案（8个）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            quantity=8,
            scope="中餐包房",
            format_requirements={"length": "4个汉字", "source": "苏东坡诗词", "style": "传递生活态度"},
            acceptance_criteria=["必须提供正好8个命名（不多不少）", "每个命名必须正好4个汉字", "必须标注每个命名的苏东坡诗词出处"],
            deliverable_owner_suggestion={
                "primary_owner": "V3_叙事专家",
                "owner_rationale": "命名任务核心是创意文案产出",
                "anti_pattern": ["V2_设计总监", "V6_工程师"],
            },
            capability_check={"within_capability": True},
        )

        # 验证
        assert deliverable.type == DeliverableTypeEnum.NAMING_LIST
        assert deliverable.quantity == 8
        assert len(deliverable.acceptance_criteria) >= 3
        assert "V3" in deliverable.deliverable_owner_suggestion.primary_owner

    def test_capability_boundary_transformation(self):
        """能力边界转化测试"""
        deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.DESIGN_STRATEGY,
            description="空间规划策略（转化自CAD图纸需求）",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须包含空间分区思路", "必须说明功能布局原则"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "空间策略是设计总监核心能力",
                "anti_pattern": [],
            },
            capability_check={
                "within_capability": True,
                "original_request": "精确的CAD平面图",
                "transformed_to": "design_strategy",
                "transformation_reason": "系统输出设计思路和策略，而非执行图纸",
            },
        )

        # 验证
        assert deliverable.capability_check.within_capability is True
        assert deliverable.capability_check.original_request is not None
        assert deliverable.capability_check.transformed_to == "design_strategy"

    def test_deliverable_id_format(self):
        """交付物ID格式验证"""
        # 正确格式
        valid_deliverable = Phase1Deliverable(
            deliverable_id="D1",
            type=DeliverableTypeEnum.DESIGN_STRATEGY,
            description="75平米住宅空间规划策略方案",
            priority=DeliverablePriorityEnum.MUST_HAVE,
            acceptance_criteria=["必须包含完整的空间规划思路"],
            deliverable_owner_suggestion={
                "primary_owner": "V2_设计总监",
                "owner_rationale": "空间设计策略制定是核心能力",
                "anti_pattern": [],
            },
            capability_check={"within_capability": True},
        )
        assert valid_deliverable.deliverable_id == "D1"

        # 错误格式
        with pytest.raises(ValueError):
            Phase1Deliverable(
                deliverable_id="Deliverable1",  # 错误格式
                type=DeliverableTypeEnum.DESIGN_STRATEGY,
                description="空间规划策略方案",
                priority=DeliverablePriorityEnum.MUST_HAVE,
                acceptance_criteria=["必须完整"],
                deliverable_owner_suggestion={
                    "primary_owner": "V2_设计总监",
                    "owner_rationale": "设计策略",
                    "anti_pattern": [],
                },
                capability_check={"within_capability": True},
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
