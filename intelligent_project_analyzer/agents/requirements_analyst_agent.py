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

# ============================================================
# 🔧 Emoji Encoding 深度修复（必须在最前面）
# ============================================================
try:
    import os
    import sys

    # 添加项目根目录到path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from fix_emoji_encoding import apply_all_patches

    apply_all_patches()
    print("[RequirementsAnalystAgent] ✅ Emoji编码修复已应用")
except Exception as e:
    print(f"[RequirementsAnalystAgent] ⚠️ Emoji修复加载失败: {e}")
# ============================================================

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from loguru import logger

from ..core.prompt_manager import PromptManager
from ..core.state import AgentType
from ..core.types import AnalysisResult
from ..services.capability_boundary_service import CapabilityBoundaryService
from ..utils.capability_detector import check_capability
from ..utils.jtbd_parser import transform_jtbd_to_natural_language
from ..services.mode_detector import HybridModeDetector
from ..services.mode_info_adjuster import adjust_info_status_by_mode
from .requirements_analyst_schema import RequirementsAnalystOutput

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
    # 注意: _llm_model / _prompt_manager 不存入 state，通过闭包注入节点
    # （msgpack checkpointer 无法序列化这两个对象）
    # ─────────────────────────────────────────────────────────────────────────

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
    # 中间状态 - Mode Detection & Vote
    # ─────────────────────────────────────────────────────────────────────────
    phase1_info_status_vote: Dict[str, Any]   # 三源投票结果详情
    detected_design_modes: List[Dict[str, Any]]  # 检测到的设计模式列表
    mode_detection_elapsed_ms: float           # 模式检测耗时
    phase2_mode: str                           # "Phase2-Full" | "Phase2-Lite"

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
    project_type: str | None  # 项目类型

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

    logger.info("[Precheck] [Precheck] 程序化能力边界预检测...")

    # 调用程序化检测器
    precheck_result = check_capability(user_input)

    elapsed_ms = (time.time() - start_time) * 1000

    # 提取关键指标
    info_suff = precheck_result.get("info_sufficiency", {})
    deliv_cap = precheck_result.get("deliverable_capability", {})

    logger.info(f"[OK] [Precheck] 完成，耗时 {elapsed_ms:.1f}ms")
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


def phase1_node(state: RequirementsAnalystState, llm_model, prompt_manager) -> Dict[str, Any]:
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

    logger.info("[Phase1] [Phase1] 开始快速定性 + 交付物识别...")

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

        #  强制清理emoji (防止Windows GBK编码错误)
        import re

        emoji_pattern = re.compile(
            r"[\U0001F000-\U0001F9FF\U00002300-\U000023FF\U00002600-\U000027BF\U00002700-\U000027BF\U0001F900-\U0001F9FF]+",
            flags=re.UNICODE,
        )
        for msg in messages:
            msg["content"] = emoji_pattern.sub("", msg["content"])

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

    logger.info(f"[OK] [Phase1] 完成，耗时 {elapsed_ms:.0f}ms")
    logger.info(f"   - info_status: {info_status}")
    logger.info(f"   - deliverables: {len(deliverables)}个")
    logger.info(f"   - next_step: {recommended_next}")

    # NEW 能力边界检查：验证Phase1输出的交付物
    if deliverables:
        logger.info("[Precheck] [CapabilityBoundary] 验证Phase1输出的交付物能力")
        boundary_check = CapabilityBoundaryService.check_deliverable_list(
            deliverables=deliverables,
            context={
                "node": "requirements_analyst_phase1",
                "user_input": state.get("user_input", ""),
                "session_id": state.get("session_id", ""),
            },
        )

        logger.info("[Data] 交付物能力边界检查结果:")
        logger.info(f"   在能力范围内: {boundary_check.within_capability}")
        logger.info(f"   能力匹配度: {boundary_check.capability_score:.2f}")

        # 如果有超出能力的交付物，应用转化
        if not boundary_check.within_capability:
            logger.warning("[Warning] Phase1输出包含超出能力的交付物")
            logger.info(f"   转化建议: {len(boundary_check.transformations_needed)} 项")

            # 更新交付物清单（应用转化）
            transformed_deliverables = []
            for i, deliv in enumerate(deliverables):
                deliv_type = deliv.get("type", "")

                # 查找是否需要转化
                for check in boundary_check.deliverable_checks:
                    if not check.within_capability and check.original_type == deliv_type:
                        # 应用转化
                        deliv["type"] = check.transformed_type or "design_strategy"
                        deliv["capability_transformed"] = True
                        deliv["original_type"] = check.original_type
                        deliv["transformation_reason"] = check.transformation_reason
                        logger.info(f"     - D{i+1}: '{check.original_type}' → '{check.transformed_type}'")
                        break

                transformed_deliverables.append(deliv)

            deliverables = transformed_deliverables
        else:
            logger.info("[OK] 所有交付物在能力范围内")

    # ── Step 4: Mode Engine (同步，轻量) ──────────────────────────────────────
    _mode_t0 = time.time()
    try:
        detected_modes = HybridModeDetector.detect_sync(
            user_input=user_input,
            structured_requirements={"primary_deliverables": deliverables},
        )
    except Exception as _mode_err:
        logger.warning(f"[Phase1] Mode Engine 失败，使用空列表: {_mode_err}")
        detected_modes = []
    mode_detection_elapsed_ms = (time.time() - _mode_t0) * 1000

    # ── Step 5: Mode-aware info status adjustment ─────────────────────────────
    if detected_modes:
        try:
            mode_adjustment = adjust_info_status_by_mode(
                original_status=info_status,
                user_input=user_input,
                detected_modes=detected_modes,
                phase1_result=phase1_result,
            )
            logger.info(f"[Phase1] ModeAdjustment: {mode_adjustment.get('adjustment_summary', '')}")
        except Exception as _adj_err:
            logger.warning(f"[Phase1] adjust_info_status_by_mode 失败: {_adj_err}")
            mode_adjustment = {"adjusted_status": None}
    else:
        mode_adjustment = {"adjusted_status": None}

    # ── Step 6: 三源加权投票 ───────────────────────────────────────────────────
    vote_precheck = state.get("precheck_result", {})
    final_info_status, vote_details = _weighted_info_status_vote(
        precheck=vote_precheck,
        phase1=phase1_result,
        mode=mode_adjustment,
    )
    logger.info(
        f"[Phase1] 三源投票 -> {final_info_status} "
        f"(score={vote_details['final_score']:.2f}, consensus={vote_details['consensus']})"
    )

    return {
        "phase1_result": phase1_result,
        "phase1_elapsed_ms": elapsed_ms,
        "phase1_info_status": final_info_status,
        "recommended_next_step": recommended_next,
        "primary_deliverables": deliverables,
        # 三源投票新字段
        "phase1_info_status_vote": vote_details,
        "detected_design_modes": detected_modes,
        "mode_detection_elapsed_ms": mode_detection_elapsed_ms,
        # 动机字段直通（置信度不足时 LLM 会返回 null）
        "phase1_motivation_preliminary": phase1_result.get("motivation_preliminary"),
        "phase1_designer_behavioral_motivation": phase1_result.get("designer_behavioral_motivation"),
        "processing_log": state.get("processing_log", [])
        + [
            f"[Phase1] 完成 ({elapsed_ms:.0f}ms) - {final_info_status}, "
            f"{len(deliverables)}个交付物, modes={len(detected_modes)}"
        ],
        "node_path": state.get("node_path", []) + ["phase1"],
    }


def phase2_node(state: RequirementsAnalystState, llm_model, prompt_manager) -> Dict[str, Any]:
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

    # ── 双模式提示词选择 ──────────────────────────────────────────────────────
    phase1_info_status = state.get("phase1_info_status", "insufficient")
    is_full_mode = phase1_info_status == "sufficient"
    phase2_mode = "Phase2-Full" if is_full_mode else "Phase2-Lite"
    prompt_key = "requirements_analyst_phase2" if is_full_mode else "requirements_analyst_phase2_lite"

    logger.info(f"[Phase2] [Phase2] 开始深度分析，模式={phase2_mode} (info_status={phase1_info_status})")

    # 加载提示词配置
    phase2_config = prompt_manager.get_prompt(prompt_key, return_full_config=True)
    if not phase2_config:
        logger.warning(f"[Phase2] 未找到配置 '{prompt_key}'，使用 fallback")
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

    # emoji 清理（防 Windows GBK 编码错误）
    import re
    _emoji_re = re.compile(
        r"[\U0001F000-\U0001F9FF\U00002300-\U000023FF\U00002600-\U000027BF"
        r"\U00002700-\U000027BF\U0001F900-\U0001F9FF]+",
        flags=re.UNICODE,
    )
    system_prompt = _emoji_re.sub("", system_prompt)
    task_description = _emoji_re.sub("", task_description)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_description},
    ]

    phase2_result: Dict[str, Any] = {}

    # ── 第一层: with_structured_output ────────────────────────────────────────
    try:
        _structured_llm = llm_model.with_structured_output(RequirementsAnalystOutput, method="function_calling")
        _output_obj = _structured_llm.invoke(messages)
        if _output_obj is not None:
            phase2_result = _output_obj.model_dump() if hasattr(_output_obj, "model_dump") else dict(_output_obj)
            phase2_result["phase"] = 2
            phase2_result["_parse_method"] = "structured_output"
            logger.info("[Phase2][T1] with_structured_output 解析成功")
    except Exception as _e1:
        logger.warning(f"[Phase2][T1] with_structured_output 失败: {_e1}")

    # ── 第二层: 加入 schema hint 重试 ─────────────────────────────────────────
    if not phase2_result:
        try:
            _hint = (
                "\n\n[系统提示] 请严格按照 RequirementsAnalystOutput JSON schema 输出，"
                "确保所有必填字段存在，analysis_layers 包含 L1-L9。"
            )
            _messages_r2 = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task_description + _hint},
            ]
            _structured_llm = llm_model.with_structured_output(RequirementsAnalystOutput, method="function_calling")
            _output_obj = _structured_llm.invoke(_messages_r2)
            if _output_obj is not None:
                phase2_result = _output_obj.model_dump() if hasattr(_output_obj, "model_dump") else dict(_output_obj)
                phase2_result["phase"] = 2
                phase2_result["_parse_method"] = "structured_output_retry"
                logger.info("[Phase2][T2] 重试 structured_output 成功")
        except Exception as _e2:
            logger.warning(f"[Phase2][T2] 重试 structured_output 失败: {_e2}")

    # ── 第三层: raw invoke + _parse_json_response ────────────────────────────
    if not phase2_result:
        try:
            _response = llm_model.invoke(messages)
            _content = _response.content if hasattr(_response, "content") else str(_response)
            phase2_result = _parse_json_response(_content)
            phase2_result["phase"] = 2
            phase2_result["_parse_method"] = "raw_json_fallback"
            # stakeholder_system None 守护
            if "stakeholder_system" not in phase2_result:
                phase2_result["stakeholder_system"] = None
            logger.info("[Phase2][T3] raw invoke + JSON parse 成功")
        except Exception as _e3:
            logger.error(f"[Phase2][T3] 全部策略失败: {_e3}")
            return _phase2_fallback(state, start_time)

    elapsed_ms = (time.time() - start_time) * 1000
    _parse_method = phase2_result.get("_parse_method", "unknown")
    logger.info(f"[OK] [Phase2] 完成，耗时 {elapsed_ms:.0f}ms, 模式={phase2_mode}, 解析={_parse_method}")

    return {
        "phase2_result": phase2_result,
        "phase2_elapsed_ms": elapsed_ms,
        "phase2_mode": phase2_mode,
        "analysis_layers": phase2_result.get("analysis_layers", {}),
        "expert_handoff": phase2_result.get("expert_handoff", {}),
        "processing_log": state.get("processing_log", [])
        + [f"[Phase2] 完成 ({elapsed_ms:.0f}ms) - {phase2_mode}, 解析={_parse_method}"],
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

    logger.info(f" [Output] 构建输出 ({analysis_mode})...")

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

    # 动机字段直通（来自 phase1_result，置信度不足时为 None）
    structured_data["motivation_preliminary"] = phase1_result.get("motivation_preliminary")
    structured_data["designer_behavioral_motivation"] = phase1_result.get("designer_behavioral_motivation")

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

    logger.info(f"[OK] [Output] 完成，总耗时 {total_elapsed:.0f}ms")

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
    条件路由: 始终执行 Phase2（深度分析）

    设计决策 (V-Default, TestRoutingRegression):
    - Phase2 **绝不跳过**，无论 info_status 为何值
    - 保留 "output" 作为图声明中的备用路径，但当前策略始终走 phase2
    """
    logger.info("[Route] [路由] 进入 Phase2（始终执行）")
    return "phase2"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════


def _format_precheck_hints(precheck_result: Dict[str, Any]) -> str:
    """格式化预检测结果为 LLM 提示"""
    hints = ["### [Precheck] 程序化预检测结果（已完成，请参考）"]

    info_suff = precheck_result.get("info_sufficiency", {})
    if info_suff.get("is_sufficient"):
        hints.append(f"[OK] **信息充足性**: 充足（得分 {info_suff.get('score', 0):.2f}）")
        hints.append(f"   - 已识别: {', '.join(info_suff.get('present_elements', []))}")
    else:
        hints.append(f"[Warning] **信息充足性**: 不足（得分 {info_suff.get('score', 0):.2f}）")
        hints.append(f"   - 缺少: {', '.join(info_suff.get('missing_elements', [])[:5])}")

    deliv_cap = precheck_result.get("deliverable_capability", {})
    hints.append(f"[OK] **能力匹配度**: {deliv_cap.get('capability_score', 1.0):.0%}")

    capable = precheck_result.get("capable_deliverables", [])
    if capable:
        deliverable_types = [d.get("type", "") for d in capable[:3]]
        hints.append(f"   - 可交付: {', '.join(deliverable_types)}")

    transformations = precheck_result.get("transformations", [])
    if transformations:
        hints.append("[Warning] **需要转化的需求**:")
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


def _build_problem_solving_approach(phase1: Dict[str, Any], phase2: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    从 Phase2 结果中构建 problem_solving_approach 结构（A-01 止血修复）

    Returns:
        dict with keys: source, method, task_type, core_challenge,
                        design_task, complexity_level, depth_reached
        None if no core fields available
    """
    # 支持 analysis_layers 包装
    layers = phase2.get("analysis_layers", phase2)

    # 提取核心张力（L3），支持备用键名
    core_tension = (
        layers.get("L3_core_tension")
        or layers.get("core_tensions")
        or phase2.get("L3_core_tension")
        or phase2.get("core_tensions")
    )

    # 提取项目任务（L4），支持备用键名
    project_task = (
        layers.get("L4_project_task")
        or layers.get("project_task")
        or phase2.get("L4_project_task")
        or phase2.get("project_task")
    )

    # 无核心字段则返回 None
    if not core_tension and not project_task:
        return None

    # 计算复杂度
    l5_sharpness = layers.get("L5_sharpness") or phase2.get("L5_sharpness", {})
    sharpness_score = l5_sharpness.get("score", 0) if isinstance(l5_sharpness, dict) else 0
    complexity_level = "high" if sharpness_score >= 70 else "medium"

    # 判断分析深度
    has_five_whys = bool(layers.get("L5_1_five_whys") or phase2.get("L5_1_five_whys"))
    depth_reached = "L5" if has_five_whys else "L4"

    # 截断 core_challenge 至 200 字符
    core_challenge = str(core_tension or "")[:200]

    return {
        "source": "phase2_output",
        "method": "programmatic_extraction",
        "task_type": "design_strategy",
        "core_challenge": core_challenge,
        "design_task": str(project_task or "")[:200],
        "complexity_level": complexity_level,
        "depth_reached": depth_reached,
    }


def _build_decision_reason(
    is_sufficient: bool,
    precheck_status: str,
    phase1_status: str,
    mode_status: str,
) -> str:
    """
    构建加权投票的决策理由说明文本

    Args:
        is_sufficient: 最终判决是否充足
        precheck_status: precheck 投票结果（"sufficient"/"insufficient"）
        phase1_status:   phase1  投票结果
        mode_status:     mode    投票结果

    Returns:
        人类可读的决策理由字符串
    """
    statuses = [precheck_status, phase1_status, mode_status]
    all_same = len(set(statuses)) == 1

    if all_same:
        label = "充足" if is_sufficient else "不足"
        return f"三方一致：信息{label}（precheck={precheck_status}, phase1={phase1_status}, mode={mode_status}）"

    if is_sufficient:
        return f"加权多数判定充足（precheck={precheck_status}, phase1={phase1_status}, mode={mode_status}）"
    else:
        return f"加权多数判定不足（precheck={precheck_status}, phase1={phase1_status}, mode={mode_status}）"


def _weighted_info_status_vote(
    precheck: Dict[str, Any],
    phase1: Dict[str, Any],
    mode: Dict[str, Any],
) -> tuple:
    """
    三方加权投票决定最终 info_status

    投票权重:
    - precheck = 0.4  (程序化预检测)
    - phase1   = 0.4  (LLM 定性判断)
    - mode     = 0.2  (模式检测调整，无 adjusted_status 时默认贡献 sufficient 权重)

    阈值: final_score >= 0.5 → "sufficient"

    Returns:
        (status: str, details: dict)
        details keys: final_score, consensus, votes, decision_reason
    """
    # precheck 贡献
    precheck_suff = precheck.get("info_sufficiency", {}).get("is_sufficient", False)
    precheck_score = 0.4 if precheck_suff else 0.0
    precheck_status_str = "sufficient" if precheck_suff else "insufficient"

    # phase1 贡献
    phase1_suff = phase1.get("info_status", "insufficient") == "sufficient"
    phase1_score = 0.4 if phase1_suff else 0.0
    phase1_status_str = "sufficient" if phase1_suff else "insufficient"

    # mode 贡献：有 adjusted_status 则按值判断，否则默认 sufficient（贡献 0.2）
    adjusted = mode.get("adjusted_status")
    if adjusted is None:
        mode_score = 0.2  # 默认 sufficient 方向
        mode_status_str = "sufficient"
    elif adjusted == "sufficient":
        mode_score = 0.2
        mode_status_str = "sufficient"
    else:
        mode_score = 0.0
        mode_status_str = "insufficient"

    final_score = precheck_score + phase1_score + mode_score
    is_sufficient = final_score >= 0.5

    # consensus：三方一致时为 True
    consensus = len({precheck_status_str, phase1_status_str, mode_status_str}) == 1

    decision_reason = _build_decision_reason(is_sufficient, precheck_status_str, phase1_status_str, mode_status_str)

    details = {
        "final_score": final_score,
        "consensus": consensus,
        "votes": {
            "precheck": precheck_status_str,
            "phase1": phase1_status_str,
            "mode": mode_status_str,
        },
        "decision_reason": decision_reason,
    }

    status = "sufficient" if is_sufficient else "insufficient"
    return status, details


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
        "motivation_preliminary": phase1_result.get("motivation_preliminary"),
        "designer_behavioral_motivation": phase1_result.get("designer_behavioral_motivation"),
    }


def _merge_phase_results(phase1: Dict, phase2: Dict, user_input: str) -> Dict[str, Any]:
    """合并 Phase1 和 Phase2 结果"""
    structured_output = phase2.get("structured_output", {})

    # Bug① fix v9.3: project_task 可能是 dict（LLM 返回结构化对象），直接对 dict 切片会导致 KeyError
    _pt_raw = structured_output.get("project_task")
    if isinstance(_pt_raw, dict):
        _pt_str = _pt_raw.get("full_statement") or _pt_raw.get("i_want_to") or str(_pt_raw)
    elif _pt_raw:
        _pt_str = str(_pt_raw)
    else:
        _pt_str = ""

    result = {
        "project_task": _pt_str,
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
        "project_overview": _pt_str,
        "core_objectives": [_pt_str[:100]] if _pt_str else [],
        "project_tasks": [_pt_str] if _pt_str else [],
        "motivation_preliminary": phase1.get("motivation_preliminary"),
        "designer_behavioral_motivation": phase1.get("designer_behavioral_motivation"),
        "problem_types": phase1.get("problem_types", []),
    }

    # v10.0.0 三阶段键名支持：phase_a_reality / phase_b_excavation
    phase_a = phase2.get("phase_a_reality", {})
    phase_b = phase2.get("phase_b_excavation", {})
    if phase_a:
        stakeholders = phase_a.get("A2_stakeholders")
        if stakeholders is not None:
            result["stakeholder_system"] = stakeholders
    if phase_b:
        five_whys = phase_b.get("B3_five_whys_analysis")
        if five_whys is not None:
            result["five_whys_analysis"] = five_whys

    # A-01: 补充 problem_solving_approach（两阶段必须字段）
    psa = _build_problem_solving_approach(phase1, phase2)
    if psa is not None:
        result["problem_solving_approach"] = psa

    return result


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


def _infer_project_type(structured_data: Dict[str, Any]) -> str:
    """推断项目类型（v7.200+: 无匹配返回 'other' 而非 None）

    优先级: commercial_dining > commercial_office > personal_residential > commercial_enterprise > other
    """
    all_text = " ".join(
        [
            str(structured_data.get("project_task", "")),
            str(structured_data.get("character_narrative", "")),
            str(structured_data.get("project_overview", "")),
        ]
    ).lower()

    # 餐饮类型（最高优先级，包括复合场景）
    dining_keywords = ["餐厅", "餐饮", "饮食", "咖啡厅", "小吃", "饮食空间"]
    if any(kw in all_text for kw in dining_keywords):
        return "commercial_dining"

    # 办公类型
    office_keywords = ["办公", "工作空间", "办公室", "办公楼", "企业台", "办公设计"]
    if any(kw in all_text for kw in office_keywords):
        return "commercial_office"

    # 个人住宅类型
    personal_keywords = ["住宅", "家", "公寓", "别墅", "房子", "居住", "卧室", "客厅", "家庭"]
    commercial_keywords = ["商业", "企业", "酒店", "展厅", "店铺", "菜市场"]
    personal_score = sum(1 for kw in personal_keywords if kw in all_text)
    commercial_score = sum(1 for kw in commercial_keywords if kw in all_text)

    if personal_score > 0 and commercial_score == 0:
        return "personal_residential"
    elif commercial_score > 0:
        return "commercial_enterprise"
    elif personal_score > 0:
        return "personal_residential"

    return "other"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. StateGraph 构建
# ═══════════════════════════════════════════════════════════════════════════════


def build_requirements_analyst_graph(llm_model, prompt_manager) -> StateGraph:
    """
    构建需求分析师 StateGraph

    使用闭包将 llm_model / prompt_manager 注入节点，
    避免存入 state 导致 msgpack 无法序列化。

    节点流转:
    START → precheck → phase1 → [条件] → phase2 → output → END
                                    ↓
                                  output → END
    """

    # 闭包: 将非序列化对象注入节点，而非存入 state
    def _phase1(state: RequirementsAnalystState) -> Dict[str, Any]:
        return phase1_node(state, llm_model, prompt_manager)

    def _phase2(state: RequirementsAnalystState) -> Dict[str, Any]:
        return phase2_node(state, llm_model, prompt_manager)

    workflow = StateGraph(RequirementsAnalystState)

    # 添加节点
    workflow.add_node("precheck", precheck_node)
    workflow.add_node("phase1", _phase1)
    workflow.add_node("phase2", _phase2)
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

    def __init__(self, llm_model, config: Dict[str, Any] | None = None):
        """
        初始化 Agent

        Args:
            llm_model: LLM 模型实例
            config: 可选配置
        """
        self.llm_model = llm_model
        self.config = config or {}
        self.prompt_manager = PromptManager()

        # 构建并编译图（不使用 checkpointer，避免 AsyncSqliteSaver 同步调用冲突）
        self._graph = build_requirements_analyst_graph(self.llm_model, self.prompt_manager).compile(checkpointer=None)

        # runtime source fingerprint — 诊断用：确认运行时加载的是当前工作树源码
        import inspect as _inspect
        import sys as _sys

        logger.info(
            "[RequirementsAnalystAgentV2] runtime source fingerprint | "
            f"module_file={__file__} | "
            f"build_graph_sig={_inspect.signature(build_requirements_analyst_graph)} | "
            f"sys_path_0={_sys.path[0]}"
        )
        logger.info("[OK] [RequirementsAnalystAgentV2] StateGraph Agent 初始化完成")

    def execute(self, user_input: str, session_id: str = "unknown") -> AnalysisResult:
        """
        执行需求分析

        Args:
            user_input: 用户输入
            session_id: 会话 ID

        Returns:
            AnalysisResult 分析结果
        """
        logger.info(f" [RequirementsAnalystAgentV2] 启动分析 (session: {session_id})")

        # 构建初始状态（llm_model/prompt_manager 已通过闭包注入节点，不存入 state 避免 msgpack 错误）
        initial_state: RequirementsAnalystState = {
            "user_input": user_input,
            "session_id": session_id,
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

        logger.info(f" [RequirementsAnalystAgentV2] 分析完成，耗时 {final_state.get('total_elapsed_ms', 0):.0f}ms")

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

    def __init__(self, llm_model, config: Dict[str, Any] | None = None):
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
