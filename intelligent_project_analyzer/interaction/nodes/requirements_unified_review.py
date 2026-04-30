"""
需求侧统一审核节点（Requirements Unified Review）

定位：需求洞察后、项目总监规划前的人工确认关卡。
语义：以"角色-任务-交付物三合一"的统一审核口径进行确认，而非单一人物审批。
"""

import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from ...core.state import ProjectAnalysisState


def _slugify_category(text: str, idx: int) -> str:
    """将分类名转为安全的 role_id 片段"""
    safe = re.sub(r"[^\w]", "", text, flags=re.UNICODE)
    return safe[:10].upper() if safe else f"CAT{idx}"


def _make_expected_output(category: str, task_count: int) -> str:
    """根据类别名称生成语义化的预期输出描述"""
    suffix_map = {
        "调研": "调研报告与数据汇编",
        "研究": "研究分析报告",
        "分析": "分析报告与洞察",
        "设计": "设计方案草稿",
        "策略": "策略建议文档",
        "规划": "规划框架文档",
        "评估": "评估报告",
        "整合": "整合梳理报告",
        "定位": "定位分析报告",
        "用户": "用户需求洞察报告",
    }
    for keyword, output in suffix_map.items():
        if keyword in category:
            return f"{category}：{output}（共{task_count}项任务）"
    return f"{category}：阶段性研究报告（共{task_count}项任务）"


class RequirementsUnifiedReviewNode:
    """需求侧统一审核节点"""

    @staticmethod
    def execute(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["project_director", "requirements_analyst"]]:
        logger.info("=" * 80)
        logger.info(" [Requirements Unified Review] 需求侧统一审核节点")
        logger.info("=" * 80)

        restructured = state.get("restructured_requirements") or {}
        confirmed_tasks = state.get("confirmed_core_tasks") or []
        selected_dimensions = state.get("selected_dimensions") or []
        deliverable_work_packages = state.get("deliverable_work_packages") or []

        draft_deliverables = restructured.get("deliverable_expectations", [])
        suggested_role_hints = [
            dim.get("label", "")
            for dim in selected_dimensions
            if isinstance(dim, dict) and dim.get("label")
        ][:5]

        #  按 category 字段分组任务 
        # 使用 list 跟踪插入顺序
        category_order: list = []
        task_groups: Dict[str, list] = defaultdict(list)
        for task in confirmed_tasks:
            if isinstance(task, dict):
                cat = task.get("category") or task.get("task_type") or "通用分析"
            else:
                cat = "通用分析"
            if cat not in task_groups:
                category_order.append(cat)
            task_groups[cat].append(task if isinstance(task, dict) else {"title": str(task)})

        # 若分类数量不足（全在same category且任务多），尝试按 task_type 二次分组
        if len(category_order) <= 1 and len(confirmed_tasks) > 8:
            type_label_map = {
                "research": "基础调研",
                "analysis": "深度分析",
                "design": "设计策略",
                "planning": "规划策略",
                "evaluation": "评估反馈",
            }
            alt_groups: Dict[str, list] = defaultdict(list)
            alt_order: list = []
            for task in confirmed_tasks:
                if isinstance(task, dict):
                    raw_type = task.get("task_type") or "research"
                    alt_cat = type_label_map.get(raw_type, raw_type)
                else:
                    alt_cat = "基础调研"
                if alt_cat not in alt_groups:
                    alt_order.append(alt_cat)
                alt_groups[alt_cat].append(task if isinstance(task, dict) else {"title": str(task)})
            if len(alt_order) > len(category_order):
                category_order = alt_order
                task_groups = alt_groups

        logger.info(
            f" [Requirements Unified Review] 任务分类: {len(category_order)} 个分类，"
            f"{len(confirmed_tasks)} 个任务: {category_order[:5]}"
        )

        #  构建角色列表与任务列表 
        role_selection_roles = []
        task_list = []

        for i, cat in enumerate(category_order):
            tasks_in_cat = task_groups[cat]
            task_texts: list = []
            for task in tasks_in_cat:
                title = task.get("title") or task.get("name") or task.get("id") or "未命名任务"
                desc = task.get("description") or ""
                task_texts.append(f"{title}：{desc}" if desc else str(title))

            role_id = f"REQ-{_slugify_category(cat, i)}-{i+1}"
            expected_output = _make_expected_output(cat, len(task_texts))
            focus = suggested_role_hints if i == 0 else []

            role_selection_roles.append(
                {
                    "role_id": role_id,
                    "role_name": cat,
                    "dynamic_role_name": cat,
                    "tasks": task_texts,
                    "focus_areas": focus,
                    "expected_output": expected_output,
                    "dependencies": [],
                }
            )

            task_list.append(
                {
                    "role_id": role_id,
                    "static_role_name": role_id,
                    "dynamic_role_name": cat,
                    "tasks": [{"description": t} for t in task_texts],
                    "task_count": len(task_texts),
                    "focus_areas": focus,
                    "expected_output": expected_output,
                    "dependencies": [],
                }
            )

        total_task_count = len(confirmed_tasks)
        role_count = len(role_selection_roles)

        payload = {
            "interaction_type": "role_and_task_unified_review",
            "title": "统一审核（角色-任务-交付物）",
            "message": "请确认当前需求理解是否可作为三合一统一审核输入，随后进入专家规划。",
            "close_previous_modal": True,
            "review_scope": "requirements_pre_director",
            "role_selection": {
                "decision_explanation": f"已按任务类别预分组为 {role_count} 个分析方向，供参考（项目总监将进行最终角色分配）。",
                "selected_roles": role_selection_roles,
                "validation": {"is_valid": True, "issues": [], "warnings": []},
                "recommendations": [],
                "strategy_info": {"current_strategy": "requirements_pre_director", "available_strategies": []},
            },
            "task_assignment": {
                "task_list": task_list,
                "validation": {"is_valid": True, "issues": [], "warnings": []},
                "assignment_principles": ["先确认需求边界，再进入角色选型与任务深化"],
                "summary": {
                    "total_roles": role_count,
                    "total_tasks": total_task_count,
                    "roles_with_tasks": role_count,
                },
            },
            "plan_view": {
                "work_packages": deliverable_work_packages,
                "coverage": state.get("dwp_coverage_report"),
                "confirmed_tasks": confirmed_tasks,
                "view_mode": "task_first",
            },
            "unified_review": {
                "project_essence": restructured.get("project_essence", ""),
                "primary_goal": restructured.get("project_objectives", {}).get("primary_goal", ""),
                "tasks": confirmed_tasks,
                "deliverables": draft_deliverables,
                "role_hints": suggested_role_hints,
            },
            "options": {
                "approve": "确认并进入专家规划",
                "modify_roles": "调整角色建议",
                "modify_tasks": "调整任务拆解",
                "edit_deliverables": "调整交付物工作包",
                "change_strategy": "切换规划策略",
                "modify": "需要调整后重分析",
                "reject": "驳回并重新分析",
            },
        }

        user_response = interrupt(payload)
        logger.info(f" [Requirements Unified Review] 收到用户响应: {type(user_response)}")

        action = "approve"
        note = ""
        if isinstance(user_response, str):
            action = user_response.strip().lower() or "approve"
        elif isinstance(user_response, dict):
            action = (user_response.get("action") or user_response.get("intent") or "approve").strip().lower()
            note = str(user_response.get("note") or user_response.get("comment") or user_response.get("reason") or "")

        change_log = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "note": note,
            "scope": "requirements_pre_director",
        }

        if action in {"approve", "confirm"}:
            logger.info(" [Requirements Unified Review] 审核通过，进入 project_director")
            return Command(
                update={
                    "requirements_unified_review_status": "approved",
                    "role_selection_approved": True,
                    "task_assignment_approved": True,
                    "unified_review_result": {
                        "approved": True,
                        "timestamp": change_log["timestamp"],
                        "scope": "requirements_pre_director",
                    },
                    "requirements_unified_review_result": {
                        "approved": True,
                        "timestamp": change_log["timestamp"],
                        "has_user_modifications": False,
                    },
                    "requirements_unified_review_change_log": [change_log],
                    "detail": "统一审核通过，进入专家规划",
                },
                goto="project_director",
            )

        if action == "modify_roles":
            return Command(
                update={
                    "requirements_unified_review_status": "approved",
                    "role_modification_request": user_response.get("modifications", {}) if isinstance(user_response, dict) else {},
                    "retry_reason": note or "需求侧统一审核：用户要求调整角色建议",
                    "requirements_unified_review_change_log": [change_log],
                    "detail": "已记录角色调整请求，进入专家规划",
                },
                goto="project_director",
            )

        if action == "modify_tasks":
            return Command(
                update={
                    "requirements_unified_review_status": "approved",
                    "task_modification_request": user_response.get("modifications", {}) if isinstance(user_response, dict) else {},
                    "retry_reason": note or "需求侧统一审核：用户要求调整任务拆解",
                    "requirements_unified_review_change_log": [change_log],
                    "detail": "已记录任务调整请求，进入专家规划",
                },
                goto="project_director",
            )

        if action == "edit_deliverables":
            edited_dwps = []
            if isinstance(user_response, dict):
                raw = user_response.get("modifications") or user_response.get("work_packages") or []
                if isinstance(raw, list):
                    edited_dwps = raw
            return Command(
                update={
                    "requirements_unified_review_status": "approved",
                    "deliverable_work_packages": edited_dwps or deliverable_work_packages,
                    "retry_reason": note or "需求侧统一审核：用户要求调整交付物工作包",
                    "requirements_unified_review_change_log": [change_log],
                    "detail": "已记录交付物工作包调整，进入专家规划",
                },
                goto="project_director",
            )

        if action == "change_strategy":
            new_strategy = ""
            if isinstance(user_response, dict):
                new_strategy = str(user_response.get("new_strategy") or "")
            return Command(
                update={
                    "requirements_unified_review_status": "approved",
                    "requested_strategy": new_strategy,
                    "retry_reason": note or f"需求侧统一审核：请求策略切换 {new_strategy or '(未指定)'}",
                    "requirements_unified_review_change_log": [change_log],
                    "detail": "已记录策略切换请求，进入专家规划",
                },
                goto="project_director",
            )

        logger.info(" [Requirements Unified Review] 审核未通过，回到 requirements_analyst")
        original_input = state.get("user_input", "")
        revised_input = original_input
        if note:
            revised_input = f"{original_input}\n\n【统一审核反馈】\n{note}"

        return Command(
            update={
                "requirements_unified_review_status": "rejected",
                "role_selection_approved": False,
                "task_assignment_approved": False,
                "rejection_reason": note or "需求侧统一审核未通过",
                "retry_reason": note or "需求侧统一审核要求重分析",
                "requirements_unified_review_result": {
                    "approved": False,
                    "timestamp": change_log["timestamp"],
                    "has_user_modifications": True,
                },
                "requirements_unified_review_change_log": [change_log],
                "requirements_confirmed": False,
                "user_input": revised_input,
                "detail": "统一审核未通过，返回需求分析",
            },
            goto="requirements_analyst",
        )


def requirements_unified_review_node(
    state: ProjectAnalysisState, store: Optional[BaseStore] = None
) -> Command:
    """导出节点函数（用于 workflow 注册）"""
    return RequirementsUnifiedReviewNode.execute(state, store)