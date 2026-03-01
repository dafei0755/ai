# -*- coding: utf-8 -*-
"""
workflow/nodes — LT-1 Mixin 子包

包含从 main_workflow.py 拆分出来的 5 个 Mixin 模块：
- security_nodes:      输入验证、拒绝、报告审核
- requirements_nodes:  需求分析师、可行性、问卷流程
- planning_nodes:      项目总监、角色选择、任务分派、质量预检
- execution_nodes:     动态批次执行、Agent 并发调度
- aggregation_nodes:   批次路由、挑战检测、结果聚合、输出生成

由 _lt1_split_workflow.py 自动生成 — 请勿在此直接修改节点逻辑。
"""
from .security_nodes import SecurityNodesMixin
from .requirements_nodes import RequirementsNodesMixin
from .planning_nodes import PlanningNodesMixin
from .execution_nodes import ExecutionNodesMixin
from .aggregation_nodes import AggregationNodesMixin

__all__ = [
    "SecurityNodesMixin",
    "RequirementsNodesMixin",
    "PlanningNodesMixin",
    "ExecutionNodesMixin",
    "AggregationNodesMixin",
]
