"""AdvisorAgent LangGraph 子图。

独立于 main_workflow.py，不修改现有节点。
LangGraph Command 只用于节点路由，不承担对象写入。
所有对象读取必须经 ObjectGateway，禁止节点直接查 DB。
"""
from typing import Any, Optional, TypedDict
import uuid
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.skill_registry import SkillRegistry
from intelligent_project_analyzer.advisor.skills.requirement_structuring import (
    RequirementStructuringSkill, SkillInput,
)
from intelligent_project_analyzer.advisor.gate import MVPGate
from intelligent_project_analyzer.advisor.command_handler import CommandHandler
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService
from intelligent_project_analyzer.advisor.models import AdvisorActionDraft


class AdvisorState(TypedDict):
    project_id: str
    trace_id: str
    session_id: str
    user_message: str
    module: str
    view: Optional[str]
    object_id: Optional[str]
    user_action: str
    dispatch_level: str
    # 节点输出
    skill_output: Optional[dict]
    action_draft: Optional[dict]
    confirmed: bool
    ticket_id: Optional[str]
    error: Optional[str]
    # 最终 ViewModel 字段
    bound_object_id: Optional[str]
    object_state: Optional[str]
    object_version: Optional[str]
    evidence_status: Optional[str]
    judgment_content: Optional[str]
    judgment_confidence: Optional[str]
    action_chips: Optional[list]
    activated_capabilities: Optional[list]


def _make_advisor_graph(db_url: str = "sqlite:///advisor_objects.db"):
    engine = init_db(db_url)
    registry = SkillRegistry()
    skill = RequirementStructuringSkill(registry)

    def read_context_node(state: AdvisorState) -> dict:
        with get_session(engine) as session:
            gw = ObjectGateway(session)
            project = gw.get_project(state["project_id"])
        return {
            "bound_object_id": state["project_id"],
            "object_state": project.object_state if project else "draft",
            "object_version": project.object_version if project else "0.1.0",
        }

    def run_skill_node(state: AdvisorState) -> dict:
        inp = SkillInput(
            project_id=state["project_id"],
            raw_description=state["user_message"],
        )
        output = skill.run(inp)
        return {
            "skill_output": output.model_dump(),
            "evidence_status": output.evidence_status,
            "judgment_content": _build_judgment(output),
            "judgment_confidence": output.confidence,
        }

    def generate_draft_node(state: AdvisorState) -> dict:
        chips = _build_chips(state)
        capabilities = [
            {"type": "ontology", "name": "本体论", "status": "placeholder",
             "summary": "Phase A2 接入后生效"},
            {"type": "methodology", "name": "方法论", "status": "placeholder",
             "summary": "Phase A2 接入后生效"},
            {"type": "knowledge", "name": "知识库", "status": "placeholder",
             "summary": "Phase A2 接入后生效"},
        ]
        return {
            "action_chips": chips,
            "activated_capabilities": capabilities,
        }

    def build_advisor_graph() -> StateGraph:
        graph = StateGraph(AdvisorState)
        graph.add_node("read_context", read_context_node)
        graph.add_node("run_skill", run_skill_node)
        graph.add_node("generate_draft", generate_draft_node)
        graph.set_entry_point("read_context")
        graph.add_edge("read_context", "run_skill")
        graph.add_edge("run_skill", "generate_draft")
        graph.add_edge("generate_draft", END)
        return graph

    return build_advisor_graph().compile(checkpointer=MemorySaver())


def _build_judgment(output) -> str:
    if output.confidence == "low":
        return "输入信息不足，无法生成有效判断。请补充关键信息后重试。"
    parts = []
    sd = output.structured_data
    if sd.get("project_type"):
        parts.append(f"项目类型：{sd['project_type']}")
    if sd.get("location"):
        parts.append(f"地点：{sd['location']}")
    if output.missing_fields:
        parts.append(f"缺失信息：{', '.join(output.missing_fields)}")
    return "；".join(parts) if parts else "需求已初步结构化，请查看建议行动。"


_VIEW_CHIP_MAP: dict[str, list[dict]] = {
    "portfolio": [
        {"type": "navigate", "label": "查看作品详情", "isPrimary": True,
         "payload": {"target": "scheme_canvas"}},
        {"type": "ask", "label": "这个作品的核心亮点是什么？", "isPrimary": False,
         "payload": {"question": "这个作品的核心亮点是什么？"}},
    ],
    "sediment": [
        {"type": "ask", "label": "哪些沉淀值得复用？", "isPrimary": True,
         "payload": {"question": "哪些沉淀可以直接复用到新项目？"}},
        {"type": "navigate", "label": "关联到方案画布", "isPrimary": False,
         "payload": {"target": "scheme_canvas"}},
    ],
    "profile": [
        {"type": "ask", "label": "如何提升个人影响力？", "isPrimary": True,
         "payload": {"question": "基于当前档案，如何进一步提升个人影响力？"}},
    ],
}


def _build_chips(state: AdvisorState) -> list:
    skill_out = state.get("skill_output", {})
    missing = skill_out.get("missing_fields", [])
    view = state.get("view")

    if view and view in _VIEW_CHIP_MAP:
        return _VIEW_CHIP_MAP[view]

    chips = []
    if missing:
        chips.append({
            "type": "ask",
            "label": f"补充 {len(missing)} 个关键信息",
            "isPrimary": True,
            "payload": {"question": f"请补充以下信息：{', '.join(missing)}"},
        })
    chips.append({
        "type": "fill",
        "label": "保存项目方向草案",
        "isPrimary": not chips,
        "payload": {"formId": "project-base-draft"},
    })
    return chips


# 全局单例（生产使用）
_advisor_app = None


def get_advisor_app(db_url: str = "sqlite:///advisor_objects.db"):
    global _advisor_app
    if _advisor_app is None:
        _advisor_app = _make_advisor_graph(db_url)
    return _advisor_app


def run_advisor(project_id: str, trace_id: str, session_id: str,
                user_message: str, module: str = "project_base",
                view: Optional[str] = None, object_id: Optional[str] = None,
                db_url: str = "sqlite:///advisor_objects.db") -> dict:
    app = get_advisor_app(db_url)
    initial_state = AdvisorState(
        project_id=project_id, trace_id=trace_id, session_id=session_id,
        user_message=user_message, module=module,
        view=view, object_id=object_id,
        user_action="ask", dispatch_level="L1" if not view else "L2",
        skill_output=None, action_draft=None, confirmed=False,
        ticket_id=None, error=None,
        bound_object_id=None, object_state=None, object_version=None,
        evidence_status=None, judgment_content=None, judgment_confidence=None,
        action_chips=None, activated_capabilities=None,
    )
    config = {"configurable": {"thread_id": session_id}}
    result = app.invoke(initial_state, config=config)
    return result
