"""
需求分析师 StateGraph Agent (v7.17 P3)

将需求分析师升级为完整的 LangGraph StateGraph Agent，
支持程序化预检测、两阶段分析、条件路由等能力。

架构设计：
┌─────────────────┐
│   precheck      │ ← 程序化能力边界预检测
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    phase1       │ ← 快速定性 + 交付物识别
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
 [info       [info
 sufficient]  insufficient]
    │              │
    ▼              ▼
┌─────────┐   ┌──────────┐
│ phase2  │   │ output   │ ← 跳过 Phase2
└────┬────┘   └────┬─────┘
     │             │
     ▼             │
┌─────────┐        │
│ output  │ ◄──────┘
└────┬────┘
     │
     ▼
   [END]
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from loguru import logger

from ..core.prompt_manager import PromptManager
from ..core.state import AgentType
from ..core.types import AnalysisResult
from ..services.capability_boundary_service import CapabilityBoundaryService, CheckType
from ..utils.capability_detector import CapabilityDetector, check_capability
from ..utils.jtbd_parser import transform_jtbd_to_natural_language

# ═══════════════════════════════════════════════════════════════════════════════
# 1. 状态定义
# ═══════════════════════════════════════════════════════════════════════════════


class RequirementsAnalystState(TypedDict):
    """需求分析师 StateGraph 状态定义"""

    # ─────────────────────────────────────────────────────────────────────────
    # 输入
    # ─────────────────────────────────────────────────────────────────────────
    user_input: str  # 用户原始输入
    session_id: str  # 会话 ID

    # ─────────────────────────────────────────────────────────────────────────
    # 配置
    # ─────────────────────────────────────────────────────────────────────────
    _llm_model: Any  # LLM 模型实例
    _prompt_manager: Any  # 提示词管理器

    # ─────────────────────────────────────────────────────────────────────────
    # 中间状态 - Precheck 阶段
    # ─────────────────────────────────────────────────────────────────────────
    precheck_result: Dict[str, Any]  # 程序化预检测结果
    precheck_elapsed_ms: float  # 预检测耗时
    info_sufficient: bool  # 信息是否充足（程序化判断）
    capability_score: float  # 能力匹配度

    # ─────────────────────────────────────────────────────────────────────────
    # 中间状态 - Phase1 阶段
    # ─────────────────────────────────────────────────────────────────────────
    phase1_result: Dict[str, Any]  # Phase1 LLM 输出
    phase1_elapsed_ms: float  # Phase1 耗时
    phase1_info_status: str  # Phase1 判定的信息状态
    recommended_next_step: str  # 推荐的下一步
    primary_deliverables: List[Dict]  # 主要交付物列表

    # ─────────────────────────────────────────────────────────────────────────
    # 中间状态 - Phase2 阶段
    # ─────────────────────────────────────────────────────────────────────────
    phase2_result: Dict[str, Any]  # Phase2 LLM 输出
    phase2_elapsed_ms: float  # Phase2 耗时
    analysis_layers: Dict[str, Any]  # L1-L5 分析层
    expert_handoff: Dict[str, Any]  # 专家接口

    # ─────────────────────────────────────────────────────────────────────────
    # 输出
    # ─────────────────────────────────────────────────────────────────────────
    structured_data: Dict[str, Any]  # 结构化输出
    confidence: float  # 置信度
    analysis_mode: str  # "phase1_only" | "two_phase"
    project_type: Optional[str]  # 项目类型

    # ─────────────────────────────────────────────────────────────────────────
    # 元数据
    # ─────────────────────────────────────────────────────────────────────────
    processing_log: List[str]  # 处理日志
    total_elapsed_ms: float  # 总耗时
    node_path: List[str]  # 经过的节点路径


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 节点函数
# ═══════════════════════════════════════════════════════════════════════════════


def precheck_node(state: RequirementsAnalystState) -> Dict[str, Any]:
    """
    节点1: 程序化能力边界预检测

    不调用 LLM，纯程序化检测：
    - 信息充足性检测（7个维度）
    - 交付物能力匹配检测
    - 能力转化建议生成
    """
    start_time = time.time()
    user_input = state.get("user_input", "")

    logger.info("🔍 [Precheck] 程序化能力边界预检测...")

    # 调用程序化检测器
    precheck_result = check_capability(user_input)

    elapsed_ms = (time.time() - start_time) * 1000

    # 提取关键指标
    info_suff = precheck_result.get("info_sufficiency", {})
    deliv_cap = precheck_result.get("deliverable_capability", {})

    logger.info(f"✅ [Precheck] 完成，耗时 {elapsed_ms:.1f}ms")
    logger.info(f"   - 信息充足: {info_suff.get('is_sufficient')}")
    logger.info(f"   - 能力匹配: {deliv_cap.get('capability_score', 1.0):.0%}")

    return {
        "precheck_result": precheck_result,
        "precheck_elapsed_ms": elapsed_ms,
        "info_sufficient": info_suff.get("is_sufficient", False),
        "capability_score": deliv_cap.get("capability_score", 1.0),
        "processing_log": state.get("processing_log", [])
        + [f"[Precheck] 完成 ({elapsed_ms:.1f}ms) - 信息{'充足' if info_suff.get('is_sufficient') else '不足'}"],
        "node_path": state.get("node_path", []) + ["precheck"],
    }


def phase1_node(state: RequirementsAnalystState) -> Dict[str, Any]:
    """
    节点2: Phase1 - 快速定性 + 交付物识别

    LLM 调用（~1.5s）：
    - L0 项目定性
    - 交付物识别 + 能力边界判断
    - 输出: info_status, primary_deliverables, recommended_next_step
    """
    start_time = time.time()
    user_input = state.get("user_input", "")
    precheck_result = state.get("precheck_result", {})
    llm_model = state.get("_llm_model")
    prompt_manager = state.get("_prompt_manager")

    logger.info("📋 [Phase1] 开始快速定性 + 交付物识别...")

    # 加载 Phase1 提示词
    phase1_config = prompt_manager.get_prompt("requirements_analyst_phase1", return_full_config=True)

    if not phase1_config:
        logger.warning("[Phase1] 未找到专用配置，使用 fallback")
        return _phase1_fallback(state, start_time)

    system_prompt = phase1_config.get("system_prompt", "")
    task_template = phase1_config.get("task_description_template", "")

    # 构建任务描述
    datetime_info = f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}。"
    task_description = task_template.replace("{datetime_info}", datetime_info).replace("{user_input}", user_input)

    # 注入预检测结果
    if precheck_result:
        precheck_hints = _format_precheck_hints(precheck_result)
        task_description = f"{precheck_hints}\n\n{task_description}"

    # 调用 LLM
    try:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": task_description}]
        response = llm_model.invoke(messages)
        response_content = response.content if hasattr(response, "content") else str(response)

        # 解析 JSON
        phase1_result = _parse_json_response(response_content)
        phase1_result["phase"] = 1

    except Exception as e:
        logger.error(f"[Phase1] LLM 调用失败: {e}")
        return _phase1_fallback(state, start_time)

    elapsed_ms = (time.time() - start_time) * 1000

    # 提取关键信息
    info_status = phase1_result.get("info_status", "insufficient")
    recommended_next = phase1_result.get("recommended_next_step", "questionnaire_first")
    deliverables = phase1_result.get("primary_deliverables", [])

    logger.info(f"✅ [Phase1] 完成，耗时 {elapsed_ms:.0f}ms")
    logger.info(f"   - info_status: {info_status}")
    logger.info(f"   - deliverables: {len(deliverables)}个")
    logger.info(f"   - next_step: {recommended_next}")

    # 🆕 能力边界检查：验证Phase1输出的交付物
    if deliverables:
        logger.info("🔍 [CapabilityBoundary] 验证Phase1输出的交付物能力")
        boundary_check = CapabilityBoundaryService.check_deliverable_list(
            deliverables=deliverables,
            context={
                "node": "requirements_analyst_phase1",
                "user_input": state.get("user_input", ""),
                "session_id": state.get("session_id", ""),
            },
        )

        logger.info(f"📊 交付物能力边界检查结果:")
        logger.info(f"   在能力范围内: {boundary_check.within_capability}")
        logger.info(f"   能力匹配度: {boundary_check.capability_score:.2f}")

        # 如果有超出能力的交付物，应用转化
        if not boundary_check.within_capability:
            logger.warning(f"⚠️ Phase1输出包含超出能力的交付物")
            logger.info(f"   转化建议: {len(boundary_check.transformations_needed)} 项")

            # 更新交付物清单（应用转化）
            transformed_deliverables = []
            for i, deliv in enumerate(deliverables):
                deliv_type = deliv.get("type", "")

                # 查找是否需要转化
                needs_transform = False
                for check in boundary_check.deliverable_checks:
                    if not check.within_capability and check.original_type == deliv_type:
                        # 应用转化
                        deliv["type"] = check.transformed_type or "design_strategy"
                        deliv["capability_transformed"] = True
                        deliv["original_type"] = check.original_type
                        deliv["transformation_reason"] = check.transformation_reason
                        needs_transform = True
                        logger.info(f"     - D{i+1}: '{check.original_type}' → '{check.transformed_type}'")
                        break

                transformed_deliverables.append(deliv)

            deliverables = transformed_deliverables
        else:
            logger.info("✅ 所有交付物在能力范围内")

    return {
        "phase1_result": phase1_result,
        "phase1_elapsed_ms": elapsed_ms,
        "phase1_info_status": info_status,
        "recommended_next_step": recommended_next,
        "primary_deliverables": deliverables,
        "processing_log": state.get("processing_log", [])
        + [f"[Phase1] 完成 ({elapsed_ms:.0f}ms) - {info_status}, {len(deliverables)}个交付物"],
        "node_path": state.get("node_path", []) + ["phase1"],
    }


def phase2_node(state: RequirementsAnalystState) -> Dict[str, Any]:
    """
    节点3: Phase2 - 深度分析 + 专家接口构建

    LLM 调用（~3s）：
    - L1-L5 深度分析
    - 专家接口构建
    - 输出: analysis_layers, structured_output, expert_handoff
    """
    start_time = time.time()
    user_input = state.get("user_input", "")
    phase1_result = state.get("phase1_result", {})
    llm_model = state.get("_llm_model")
    prompt_manager = state.get("_prompt_manager")

    logger.info("🔬 [Phase2] 开始深度分析 + 专家接口构建...")

    # 加载 Phase2 提示词
    phase2_config = prompt_manager.get_prompt("requirements_analyst_phase2", return_full_config=True)

    if not phase2_config:
        logger.warning("[Phase2] 未找到专用配置，使用 fallback")
        return _phase2_fallback(state, start_time)

    system_prompt = phase2_config.get("system_prompt", "")
    task_template = phase2_config.get("task_description_template", "")

    # 构建任务描述
    datetime_info = f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}。"
    phase1_output_str = json.dumps(phase1_result, ensure_ascii=False, indent=2)

    task_description = (
        task_template.replace("{datetime_info}", datetime_info)
        .replace("{user_input}", user_input)
        .replace("{phase1_output}", phase1_output_str)
    )

    # 调用 LLM
    try:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": task_description}]
        response = llm_model.invoke(messages)
        response_content = response.content if hasattr(response, "content") else str(response)

        # 解析 JSON
        phase2_result = _parse_json_response(response_content)
        phase2_result["phase"] = 2

    except Exception as e:
        logger.error(f"[Phase2] LLM 调用失败: {e}")
        return _phase2_fallback(state, start_time)

    elapsed_ms = (time.time() - start_time) * 1000

    logger.info(f"✅ [Phase2] 完成，耗时 {elapsed_ms:.0f}ms")

    return {
        "phase2_result": phase2_result,
        "phase2_elapsed_ms": elapsed_ms,
        "analysis_layers": phase2_result.get("analysis_layers", {}),
        "expert_handoff": phase2_result.get("expert_handoff", {}),
        "processing_log": state.get("processing_log", []) + [f"[Phase2] 完成 ({elapsed_ms:.0f}ms)"],
        "node_path": state.get("node_path", []) + ["phase2"],
    }


def output_node(state: RequirementsAnalystState) -> Dict[str, Any]:
    """
    节点4: 输出构建

    根据执行路径，构建最终输出：
    - phase1_only: 仅 Phase1 完成
    - two_phase: Phase1 + Phase2 完成
    """
    start_time = time.time()
    user_input = state.get("user_input", "")
    phase1_result = state.get("phase1_result", {})
    phase2_result = state.get("phase2_result", {})

    # 判断执行模式
    has_phase2 = bool(phase2_result)
    analysis_mode = "two_phase" if has_phase2 else "phase1_only"

    logger.info(f"📦 [Output] 构建输出 ({analysis_mode})...")

    if has_phase2:
        # 合并 Phase1 和 Phase2 结果
        structured_data = _merge_phase_results(phase1_result, phase2_result, user_input)
        confidence = _calculate_two_phase_confidence(phase1_result, phase2_result)
    else:
        # 仅 Phase1 结果
        structured_data = _build_phase1_only_result(phase1_result, user_input)
        confidence = 0.5

    # 后处理
    _normalize_jtbd_fields(structured_data)
    project_type = _infer_project_type(structured_data)

    structured_data["analysis_mode"] = analysis_mode
    structured_data["project_type"] = project_type

    # 添加耗时信息
    structured_data["precheck_elapsed_ms"] = state.get("precheck_elapsed_ms", 0)
    structured_data["phase1_elapsed_ms"] = state.get("phase1_elapsed_ms", 0)
    if has_phase2:
        structured_data["phase2_elapsed_ms"] = state.get("phase2_elapsed_ms", 0)

    elapsed_ms = (time.time() - start_time) * 1000
    total_elapsed = (
        state.get("precheck_elapsed_ms", 0)
        + state.get("phase1_elapsed_ms", 0)
        + state.get("phase2_elapsed_ms", 0)
        + elapsed_ms
    )

    logger.info(f"✅ [Output] 完成，总耗时 {total_elapsed:.0f}ms")

    return {
        "structured_data": structured_data,
        "confidence": confidence,
        "analysis_mode": analysis_mode,
        "project_type": project_type,
        "total_elapsed_ms": total_elapsed,
        "processing_log": state.get("processing_log", [])
        + [f"[Output] 完成 ({elapsed_ms:.0f}ms) - 模式: {analysis_mode}, 置信度: {confidence:.2f}"],
        "node_path": state.get("node_path", []) + ["output"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 条件路由
# ═══════════════════════════════════════════════════════════════════════════════


def should_execute_phase2(state: RequirementsAnalystState) -> Literal["phase2", "output"]:
    """
    条件路由: 判断是否执行 Phase2

    条件:
    - info_status == "sufficient" AND
    - recommended_next_step != "questionnaire_first"
    → 执行 Phase2

    否则:
    → 跳过 Phase2，直接输出
    """
    info_status = state.get("phase1_info_status", "insufficient")
    recommended_next = state.get("recommended_next_step", "questionnaire_first")

    if info_status == "sufficient" and recommended_next != "questionnaire_first":
        logger.info("🔀 [路由] 信息充足，进入 Phase2")
        return "phase2"
    else:
        logger.info(f"🔀 [路由] 跳过 Phase2 (info_status={info_status}, next={recommended_next})")
        return "output"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════


def _format_precheck_hints(precheck_result: Dict[str, Any]) -> str:
    """格式化预检测结果为 LLM 提示"""
    hints = ["### 🔍 程序化预检测结果（已完成，请参考）"]

    info_suff = precheck_result.get("info_sufficiency", {})
    if info_suff.get("is_sufficient"):
        hints.append(f"✅ **信息充足性**: 充足（得分 {info_suff.get('score', 0):.2f}）")
        hints.append(f"   - 已识别: {', '.join(info_suff.get('present_elements', []))}")
    else:
        hints.append(f"⚠️ **信息充足性**: 不足（得分 {info_suff.get('score', 0):.2f}）")
        hints.append(f"   - 缺少: {', '.join(info_suff.get('missing_elements', [])[:5])}")

    deliv_cap = precheck_result.get("deliverable_capability", {})
    hints.append(f"✅ **能力匹配度**: {deliv_cap.get('capability_score', 1.0):.0%}")

    capable = precheck_result.get("capable_deliverables", [])
    if capable:
        deliverable_types = [d.get("type", "") for d in capable[:3]]
        hints.append(f"   - 可交付: {', '.join(deliverable_types)}")

    transformations = precheck_result.get("transformations", [])
    if transformations:
        hints.append("⚠️ **需要转化的需求**:")
        for t in transformations[:3]:
            hints.append(f"   - '{t.get('original')}' → '{t.get('transformed_to')}'")

    hints.append("")
    return "\n".join(hints)


def _parse_json_response(response: str) -> Dict[str, Any]:
    """解析 JSON 响应"""
    # 尝试代码块提取
    import re

    json_pattern = r"```(?:json)?\s*\n(.*?)\n```"
    match = re.search(json_pattern, response, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # 尝试平衡括号提取
    start_idx = response.find("{")
    if start_idx == -1:
        raise ValueError("无法找到 JSON 开始")

    stack = []
    in_string = False
    escape = False

    for i in range(start_idx, len(response)):
        ch = response[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{":
                stack.append(ch)
            elif ch == "}":
                if stack:
                    stack.pop()
                if not stack:
                    return json.loads(response[start_idx : i + 1])

    raise ValueError("无法找到完整 JSON")


def _phase1_fallback(state: RequirementsAnalystState, start_time: float) -> Dict[str, Any]:
    """Phase1 降级逻辑"""
    user_input = state.get("user_input", "")
    precheck_result = state.get("precheck_result", {})

    info_suff = precheck_result.get("info_sufficiency", {})
    capable = precheck_result.get("capable_deliverables", [])

    phase1_result = {
        "phase": 1,
        "info_status": "sufficient" if info_suff.get("is_sufficient") else "insufficient",
        "info_status_reason": "基于程序化预检测",
        "project_summary": user_input[:100] + "...",
        "primary_deliverables": [
            {"deliverable_id": f"D{i+1}", "type": d.get("type", "design_strategy"), "priority": "MUST_HAVE"}
            for i, d in enumerate(capable[:3])
        ]
        or [{"deliverable_id": "D1", "type": "design_strategy", "priority": "MUST_HAVE"}],
        "recommended_next_step": precheck_result.get("recommended_action", "questionnaire_first"),
        "fallback": True,
    }

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        "phase1_result": phase1_result,
        "phase1_elapsed_ms": elapsed_ms,
        "phase1_info_status": phase1_result["info_status"],
        "recommended_next_step": phase1_result["recommended_next_step"],
        "primary_deliverables": phase1_result["primary_deliverables"],
        "processing_log": state.get("processing_log", []) + [f"[Phase1] Fallback ({elapsed_ms:.0f}ms)"],
        "node_path": state.get("node_path", []) + ["phase1"],
    }


def _phase2_fallback(state: RequirementsAnalystState, start_time: float) -> Dict[str, Any]:
    """Phase2 降级逻辑"""
    user_input = state.get("user_input", "")

    phase2_result = {
        "phase": 2,
        "analysis_layers": {
            "L1_facts": [f"用户输入: {user_input[:100]}..."],
            "L2_user_model": {},
            "L3_core_tension": "待识别",
            "L4_project_task": user_input[:200],
            "L5_sharpness": {"score": 50},
        },
        "structured_output": {
            "project_task": user_input[:200],
            "character_narrative": "待分析",
            "physical_context": "待明确",
            "resource_constraints": "待明确",
        },
        "expert_handoff": {},
        "fallback": True,
    }

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        "phase2_result": phase2_result,
        "phase2_elapsed_ms": elapsed_ms,
        "analysis_layers": phase2_result["analysis_layers"],
        "expert_handoff": phase2_result["expert_handoff"],
        "processing_log": state.get("processing_log", []) + [f"[Phase2] Fallback ({elapsed_ms:.0f}ms)"],
        "node_path": state.get("node_path", []) + ["phase2"],
    }


def _build_phase1_only_result(phase1_result: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    """构建仅 Phase1 的结果"""
    return {
        "project_task": phase1_result.get("project_summary", user_input[:200]),
        "character_narrative": "待问卷补充后分析",
        "physical_context": "待明确",
        "resource_constraints": "待明确",
        "regulatory_requirements": "待明确",
        "inspiration_references": "待补齐",
        "experience_behavior": "待补齐",
        "design_challenge": "待识别",
        "primary_deliverables": phase1_result.get("primary_deliverables", []),
        "info_status": phase1_result.get("info_status"),
        "info_gaps": phase1_result.get("info_gaps", []),
        "skip_phase2_reason": phase1_result.get("info_status_reason", "信息不足"),
        "project_overview": phase1_result.get("project_summary", user_input[:200]),
        "core_objectives": [],
        "project_tasks": [],
    }


def _merge_phase_results(phase1: Dict, phase2: Dict, user_input: str) -> Dict[str, Any]:
    """合并 Phase1 和 Phase2 结果"""
    structured_output = phase2.get("structured_output", {})

    return {
        "project_task": structured_output.get("project_task", ""),
        "character_narrative": structured_output.get("character_narrative", ""),
        "physical_context": structured_output.get("physical_context", ""),
        "resource_constraints": structured_output.get("resource_constraints", ""),
        "regulatory_requirements": structured_output.get("regulatory_requirements", ""),
        "inspiration_references": structured_output.get("inspiration_references", ""),
        "experience_behavior": structured_output.get("experience_behavior", ""),
        "design_challenge": structured_output.get("design_challenge", ""),
        "primary_deliverables": phase1.get("primary_deliverables", []),
        "info_status": phase1.get("info_status"),
        "project_type_preliminary": phase1.get("project_type_preliminary"),
        "analysis_layers": phase2.get("analysis_layers", {}),
        "expert_handoff": phase2.get("expert_handoff", {}),
        "project_overview": structured_output.get("project_task", ""),
        "core_objectives": [structured_output.get("project_task", "")[:100]]
        if structured_output.get("project_task")
        else [],
        "project_tasks": [structured_output.get("project_task", "")] if structured_output.get("project_task") else [],
    }


def _calculate_two_phase_confidence(phase1: Dict, phase2: Dict) -> float:
    """计算两阶段置信度"""
    confidence = 0.5

    if phase1.get("info_status") == "sufficient":
        confidence += 0.1
    if len(phase1.get("primary_deliverables", [])) > 0:
        confidence += 0.1

    sharpness = phase2.get("analysis_layers", {}).get("L5_sharpness", {})
    if isinstance(sharpness, dict):
        score = sharpness.get("score", 0)
        confidence += min(score / 200, 0.2)

    if phase2.get("expert_handoff", {}).get("critical_questions_for_experts"):
        confidence += 0.1

    return min(confidence, 1.0)


def _normalize_jtbd_fields(structured_data: Dict[str, Any]) -> None:
    """JTBD 字段规范化"""
    for field in ["project_task", "project_overview"]:
        value = structured_data.get(field)
        if isinstance(value, str):
            structured_data[field] = transform_jtbd_to_natural_language(value)


def _infer_project_type(structured_data: Dict[str, Any]) -> Optional[str]:
    """推断项目类型"""
    all_text = " ".join(
        [
            str(structured_data.get("project_task", "")),
            str(structured_data.get("character_narrative", "")),
            str(structured_data.get("project_overview", "")),
        ]
    ).lower()

    personal_keywords = ["住宅", "家", "公寓", "别墅", "房子", "居住", "卧室", "客厅", "家庭"]
    commercial_keywords = ["办公", "商业", "企业", "餐厅", "酒店", "店铺", "展厅", "菜市场"]

    personal_score = sum(1 for kw in personal_keywords if kw in all_text)
    commercial_score = sum(1 for kw in commercial_keywords if kw in all_text)

    if personal_score > 0 and commercial_score > 0:
        return "hybrid_residential_commercial"
    elif personal_score > commercial_score:
        return "personal_residential"
    elif commercial_score > personal_score:
        return "commercial_enterprise"
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 5. StateGraph 构建
# ═══════════════════════════════════════════════════════════════════════════════


def build_requirements_analyst_graph() -> StateGraph:
    """
    构建需求分析师 StateGraph

    节点流转:
    START → precheck → phase1 → [条件] → phase2 → output → END
                                    ↓
                                  output → END
    """
    workflow = StateGraph(RequirementsAnalystState)

    # 添加节点
    workflow.add_node("precheck", precheck_node)
    workflow.add_node("phase1", phase1_node)
    workflow.add_node("phase2", phase2_node)
    workflow.add_node("output", output_node)

    # 添加边
    workflow.add_edge(START, "precheck")
    workflow.add_edge("precheck", "phase1")

    # 条件边: Phase1 → Phase2 或 Output
    workflow.add_conditional_edges("phase1", should_execute_phase2, {"phase2": "phase2", "output": "output"})

    workflow.add_edge("phase2", "output")
    workflow.add_edge("output", END)

    return workflow


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Agent 封装类
# ═══════════════════════════════════════════════════════════════════════════════


class RequirementsAnalystAgentV2:
    """
    需求分析师 StateGraph Agent (v7.17 P3)

    封装 StateGraph，提供统一的执行接口
    """

    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Agent

        Args:
            llm_model: LLM 模型实例
            config: 可选配置
        """
        self.llm_model = llm_model
        self.config = config or {}
        self.prompt_manager = PromptManager()

        # 构建并编译图
        self._graph = build_requirements_analyst_graph().compile()

        logger.info("✅ [RequirementsAnalystAgentV2] StateGraph Agent 初始化完成")

    def execute(self, user_input: str, session_id: str = "unknown") -> AnalysisResult:
        """
        执行需求分析

        Args:
            user_input: 用户输入
            session_id: 会话 ID

        Returns:
            AnalysisResult 分析结果
        """
        logger.info(f"🚀 [RequirementsAnalystAgentV2] 启动分析 (session: {session_id})")

        # 构建初始状态
        initial_state: RequirementsAnalystState = {
            "user_input": user_input,
            "session_id": session_id,
            "_llm_model": self.llm_model,
            "_prompt_manager": self.prompt_manager,
            "processing_log": [],
            "node_path": [],
        }

        # 执行图
        final_state = self._graph.invoke(initial_state)

        # 构建 AnalysisResult
        result = AnalysisResult(
            agent_type=AgentType.REQUIREMENTS_ANALYST,
            content=json.dumps(final_state.get("structured_data", {}), ensure_ascii=False, indent=2),
            structured_data=final_state.get("structured_data", {}),
            confidence=final_state.get("confidence", 0.5),
            sources=["user_input", "stategraph_analysis"],
            metadata={
                "analysis_mode": final_state.get("analysis_mode"),
                "project_type": final_state.get("project_type"),
                "total_elapsed_ms": final_state.get("total_elapsed_ms"),
                "node_path": final_state.get("node_path"),
                "processing_log": final_state.get("processing_log"),
            },
        )

        logger.info(f"🏁 [RequirementsAnalystAgentV2] 分析完成，耗时 {final_state.get('total_elapsed_ms', 0):.0f}ms")

        return result

    def get_graph(self):
        """返回编译后的图（用于调试）"""
        return self._graph


# ═══════════════════════════════════════════════════════════════════════════════
# 7. 向后兼容层
# ═══════════════════════════════════════════════════════════════════════════════


class RequirementsAnalystCompat:
    """
    向后兼容层

    保持与原 RequirementsAnalystAgent 相同的接口，
    内部使用 StateGraph Agent 执行
    """

    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        self._agent = RequirementsAnalystAgentV2(llm_model, config)
        self.llm_model = llm_model
        self.config = config

    def execute(
        self, state: Dict[str, Any], config=None, store=None, use_two_phase: bool = True  # 默认使用 StateGraph 模式
    ) -> AnalysisResult:
        """
        兼容原接口的 execute 方法
        """
        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "unknown")

        return self._agent.execute(user_input, session_id)
