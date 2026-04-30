# DEPRECATED: 已被 v2.0 双态架构 S1-S5 链（requirements_analysis/ 节点）取代。
# 当 ENABLE_DUAL_MODE_V2=true 时本模块不再被主工作流调用，仅保留以供回退兼容。
"""
需求分析师 StateGraph Agent (v7.17 P3)

将需求分析师升级为完整的 LangGraph StateGraph Agent，
支持程序化预检测、两阶段分析、条件路由等能力。

架构设计（v7.621+ 更新）：
┌─────────────────┐
│   precheck      │ ← 程序化能力边界预检测
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    phase1       │ ← 快速定性 + 交付物识别
└────────┬────────┘
         │
         ▼          （v7.621: Phase2 总是执行，不可跳过）
┌─────────────────┐
│    phase2       │ ← info_sufficient → Full 模式
│                 │   info_insufficient → Lite 模式
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    output       │ ← 合并 Phase1 + Phase2 结果
└────────┬────────┘
         │
         ▼
       [END]
"""

# ============================================================
# 🔧 Emoji Encoding 深度修复（必须在最前面）
# ============================================================
try:
    import sys
    import os

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
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from langgraph.graph import END, START, StateGraph
from loguru import logger

from ..core.prompt_manager import PromptManager
from ..core.state import AgentType
from ..core.types import AnalysisResult
from ..services.capability_boundary_service import CapabilityBoundaryService
from ..services.mode_detector import HybridModeDetector
from ..utils.capability_detector import check_capability
from ..utils.jtbd_parser import transform_jtbd_to_natural_language

# 🆕 v7.501 P1-A: 结构化输出Schema（防止幻觉）
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
    detected_design_modes: List[Dict[str, Any]]  # NEW: 10 Mode Engine检测结果
    mode_detection_elapsed_ms: float  # NEW: 模式检测耗时

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
            (
                r"[\U0001F000-\U0001F9FF\U00002300-\U000023FF"
                r"\U00002600-\U000027BF\U00002700-\U000027BF\U0001F900-\U0001F9FF]+"
            ),
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
                        logger.info(f"     - D{i + 1}: '{check.original_type}' → '{check.transformed_type}'")
                        break

                transformed_deliverables.append(deliv)

            deliverables = transformed_deliverables
        else:
            logger.info("[OK] 所有交付物在能力范围内")

    # ═══════════════════════════════════════════════════════════
    # NEW: 设计模式检测（10 Mode Engine）- 移至Phase1确保总是执行
    # ═══════════════════════════════════════════════════════════
    logger.info("[ModeDetection] 开始10 Mode Engine检测（Phase1集成）...")
    mode_detection_start = time.time()

    try:
        # 提取结构化需求
        structured_reqs = None
        if phase1_result:
            structured_reqs = {
                "project_type": phase1_result.get("project_type", {}),
                "deliverables": deliverables,  # 使用已转化的deliverables
            }

        # 执行同步模式检测（关键词快速检测）
        detected_modes = HybridModeDetector.detect_sync(user_input=user_input, structured_requirements=structured_reqs)

        mode_detection_elapsed = (time.time() - mode_detection_start) * 1000

        logger.info(
            f"[OK] [ModeDetection] 检测完成，耗时 {mode_detection_elapsed:.1f}ms, 识别{len(detected_modes)}个模式"
        )

        if detected_modes:
            top_mode = detected_modes[0]
            from ..services.mode_detector import get_mode_name

            logger.info(f"   主模式: {get_mode_name(top_mode['mode'])} ({top_mode['confidence']:.2f})")

    except Exception as e:
        logger.error(f"[Error] [ModeDetection] 模式检测失败: {e}")
        detected_modes = []
        mode_detection_elapsed = 0
    # ═══════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════
    # NEW v7.750 P1: 模式感知信息质量调整
    # ═══════════════════════════════════════════════════════════
    original_info_status = info_status
    mode_adjustment_result = {}

    if detected_modes:
        try:
            from ..services.mode_info_adjuster import adjust_info_status_by_mode

            logger.info("[ModeAdjustment] 基于检测模式调整info_status...")
            mode_adjustment_result = adjust_info_status_by_mode(
                original_status=info_status,
                user_input=user_input,
                detected_modes=detected_modes,
                phase1_result=phase1_result,
            )

            # 应用调整后的status
            info_status = mode_adjustment_result["adjusted_status"]

            # 记录调整日志
            if info_status != original_info_status:
                logger.warning(f"[ModeAdjustment] info_status调整: '{original_info_status}' -> '{info_status}'")
                logger.info(f"   原因: {mode_adjustment_result.get('adjustment_summary', '')}")

                # 如果有缺失信息提示，记录
                missing_hints = mode_adjustment_result.get("mode_adjustments", [])
                for adj in missing_hints:
                    if adj.get("penalty_applied", 0) > 0:
                        logger.info(f"   - {adj['mode_name']}: 关键信息覆盖率 {adj['keyword_coverage'] * 100:.0f}%")
            else:
                logger.info(
                    f"[OK] [ModeAdjustment] info_status保持不变: '{info_status}' (根据{len(detected_modes)}个模式验证)"
                )

        except Exception as e:
            logger.error(f"[Error] [ModeAdjustment] 模式调整失败: {e}")
            # 保持原始status
    # ═══════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════
    # 🆕 v7.623: 加权投票决定最终info_status
    # ═══════════════════════════════════════════════════════════
    final_info_status, decision_details = _weighted_info_status_vote(
        precheck_result=precheck_result, phase1_result=phase1_result, mode_adjustment_result=mode_adjustment_result
    )

    # 记录决策日志
    if final_info_status != info_status:
        logger.warning(f"[WeightedVote] info_status调整: '{info_status}' -> '{final_info_status}'")
        logger.info(f"   原因: {decision_details['decision_reason']}")
        logger.info(f"   投票分数: {decision_details['final_score']:.2f}")
    else:
        logger.info(
            f"[OK] [WeightedVote] info_status保持: '{final_info_status}' "
            f"(投票分数: {decision_details['final_score']:.2f})"
        )
    # ═══════════════════════════════════════════════════════════

    return {
        "phase1_result": phase1_result,
        "phase1_elapsed_ms": elapsed_ms,
        "phase1_info_status": final_info_status,  # 🆕 v7.623: 使用加权投票结果
        "phase1_original_info_status": original_info_status,  # NEW: 记录原始status
        "phase1_llm_info_status": info_status,  # 🆕 v7.623: 记录LLM原始判定
        "weighted_vote_decision": decision_details,  # 🆕 v7.623: 记录投票详情
        "mode_adjustment_result": mode_adjustment_result,  # NEW: 调整详情
        "recommended_next_step": recommended_next,
        "primary_deliverables": deliverables,
        "detected_design_modes": detected_modes,  # NEW: Phase1提供Mode Detection结果
        "mode_detection_elapsed_ms": mode_detection_elapsed,  # NEW: 记录检测耗时
        "processing_log": state.get("processing_log", [])
        + [
            f"[Phase1] 完成 ({elapsed_ms:.0f}ms) - {final_info_status}, {len(deliverables)}个交付物, {len(detected_modes)}个模式"
        ],
        "node_path": state.get("node_path", []) + ["phase1"],
    }


def phase2_node(state: RequirementsAnalystState, llm_model, prompt_manager) -> Dict[str, Any]:
    """
    节点3: Phase2 - 深度分析 + 专家接口构建

    🆕 v7.622: 双模式策略
    - info_status="sufficient" → Phase2-Full（完整L1-L7分析，~3000ms）
    - info_status="insufficient" → Phase2-Lite（轻量L1-L4分析，~1200ms）
    """
    start_time = time.time()
    user_input = state.get("user_input", "")
    phase1_result = state.get("phase1_result", {})
    phase1_info_status = state.get("phase1_info_status", "insufficient")

    # ═══════════════════════════════════════════════════════════
    # 🆕 v7.622: 根据info_status选择配置
    # ═══════════════════════════════════════════════════════════
    if phase1_info_status == "sufficient":
        config_name = "requirements_analyst_phase2"
        mode_label = "Phase2-Full"
        logger.info(f"[Phase2] 信息充足，使用完整分析模式（{mode_label}）")
    else:
        config_name = "requirements_analyst_phase2_lite"
        mode_label = "Phase2-Lite"
        logger.info(f"[Phase2] 信息不足，使用轻量级模式（{mode_label}）")

    logger.info(f"[Phase2] 开始深度分析 + 专家接口构建（{mode_label}）...")

    # ═══════════════════════════════════════════════════════════
    # NEW: 使用Phase1提供的Mode Detection结果（无需重复检测）
    # ═══════════════════════════════════════════════════════════
    detected_modes = state.get("detected_design_modes", [])
    mode_detection_elapsed = state.get("mode_detection_elapsed_ms", 0)

    if detected_modes:
        logger.info(
            f"[ModeDetection] 使用Phase1检测结果: {len(detected_modes)}个模式, 耗时 {mode_detection_elapsed:.1f}ms"
        )
        top_mode = detected_modes[0]
        from ..services.mode_detector import get_mode_name

        logger.info(f"   主模式: {get_mode_name(top_mode['mode'])} ({top_mode['confidence']:.2f})")
    else:
        logger.warning("[ModeDetection] Phase1未检测到模式，继续执行Phase2")
    # ═══════════════════════════════════════════════════════════

    # 🆕 v7.622: 加载对应模式的配置
    phase2_config = prompt_manager.get_prompt(config_name, return_full_config=True)

    if not phase2_config:
        logger.warning("[Phase2] 未找到专用配置，使用 fallback")
        return _phase2_fallback(state, start_time)

    system_prompt = phase2_config.get("system_prompt", "")
    task_template = phase2_config.get("task_description_template", "")

    # ═══════════════════════════════════════════════════════════
    # v9.2-Layer2: sf知识体系注入（模式感知）
    # ═══════════════════════════════════════════════════════════
    sf_knowledge_text = ""
    if detected_modes:
        try:
            from ..services.sf_knowledge_loader import (
                get_activated_abilities_for_mode,
                get_ability_injection,
            )

            top_mode_id = detected_modes[0].get("mode", "")
            activated_abilities = get_activated_abilities_for_mode(top_mode_id)
            if activated_abilities:
                ability_sections = []
                for ability_tag in activated_abilities[:4]:  # 限制注入数量，避免prompt过长
                    injection = get_ability_injection(ability_tag)
                    if injection:
                        ability_sections.append(injection)
                if ability_sections:
                    sf_knowledge_text = (
                        "### 当前项目关联的设计能力维度（来自sf知识体系）\n\n"
                        "以下能力维度与检测到的设计模式最相关，请在分析中优先考虑这些维度的洞察深度：\n\n"
                        + "\n\n".join(ability_sections)
                    )
                    logger.info(
                        f"[Phase2-v9.2] sf知识注入: {len(ability_sections)}个能力维度, "
                        f"mode={top_mode_id}, abilities={activated_abilities[:4]}"
                    )
        except Exception as sf_err:
            logger.warning(f"[Phase2-v9.2] sf知识注入失败（降级跳过）: {sf_err}")

    # ═══════════════════════════════════════════════════════════
    # v9.2-Layer3a: 结果导向前置锚定（交付物驱动分析深度）
    # ═══════════════════════════════════════════════════════════
    deliverable_anchoring_text = ""
    primary_deliverables = phase1_result.get("primary_deliverables", [])
    if primary_deliverables:
        # 交付物类型 → 必须洞察的维度映射
        deliverable_insight_map = {
            "design_strategy": ["L3杠杆点（核心矛盾）", "L4.5五层为什么（身份层需求）", "L6假设审计（方向性假设）"],
            "naming_list": ["L2建模（符号身份）", "L4.5五层为什么（品牌认同层）", "L8反套路化"],
            "brand_narrative": ["L2.6品牌DNA解码", "L5锐度测试（独特性验证）", "L4.5五层为什么（情感层）"],
            "material_guidance": ["L1事实解构（物理约束）", "L6假设审计（材料适用性）", "L7系统性影响（环境维度）"],
            "analysis_report": ["L2.5利益相关者系统", "L6假设审计（全面性）", "L7系统性影响（全维度）"],
            "strategy_plan": ["L2.5利益相关者系统", "L3杠杆点", "L7系统性影响", "L6假设审计"],
            "implementation_guide": ["L1事实解构（MECE验证）", "L2.5利益相关者系统（权力动态）", "L6假设审计"],
        }
        anchoring_lines = []
        for d in primary_deliverables:
            d_type = d.get("type", "") if isinstance(d, dict) else str(d)
            d_desc = d.get("description", d_type) if isinstance(d, dict) else str(d)
            required_dims = deliverable_insight_map.get(d_type, ["L1-L5全面分析"])
            anchoring_lines.append(f"- 交付物「{d_desc}」→ 必须深度洞察: {', '.join(required_dims)}")

        if anchoring_lines:
            deliverable_anchoring_text = (
                "### 结果导向分析锚定\n\n"
                "Phase1已识别以下交付物，你的深度分析必须直接服务于这些交付物的生产：\n"
                + "\n".join(anchoring_lines)
                + "\n\n请确保上述维度的分析具有足够的深度和可操作性，而非泛泛而谈。"
            )
            logger.info(f"[Phase2-v9.2] 结果导向锚定: {len(primary_deliverables)}个交付物")

    # ═══════════════════════════════════════════════════════════
    # v9.2-Layer3b: 不确定性地图驱动分析（优先探索不确定领域）
    # ═══════════════════════════════════════════════════════════
    uncertainty_guidance_text = ""
    uncertainty_map = state.get("uncertainty_map") or phase1_result.get("uncertainty_map")
    if uncertainty_map and isinstance(uncertainty_map, dict):
        high_uncertainty_dims = []
        for dim, info in uncertainty_map.items():
            level = info.get("level", "") if isinstance(info, dict) else str(info)
            if level in ("high", "critical") or (isinstance(info, (int, float)) and info >= 0.7):
                reason = info.get("reason", "") if isinstance(info, dict) else ""
                high_uncertainty_dims.append(f"- {dim}: {reason}" if reason else f"- {dim}")

        if high_uncertainty_dims:
            uncertainty_guidance_text = (
                "### 不确定性引导\n\n"
                "以下维度的信息不确定性较高，请在分析中重点探索、提出假设并在L6中审计这些假设：\n"
                + "\n".join(high_uncertainty_dims)
                + "\n\n对于高不确定性维度，请：\n"
                "1. 在L1中标注信息缺口\n"
                "2. 在L4.5中对该维度执行五层追问\n"
                "3. 在L6中将其作为核心假设进行审计\n"
                "4. 在expert_handoff中标记为需要专家优先解决的问题"
            )
            logger.info(f"[Phase2-v9.2] 不确定性引导: {len(high_uncertainty_dims)}个高不确定维度")

    # 构建任务描述
    datetime_info = f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}。"
    phase1_output_str = json.dumps(phase1_result, ensure_ascii=False, indent=2)

    task_description = (
        task_template.replace("{datetime_info}", datetime_info)
        .replace("{user_input}", user_input)
        .replace("{phase1_output}", phase1_output_str)
        .replace("{sf_knowledge_injection}", sf_knowledge_text)
        .replace("{deliverable_anchoring}", deliverable_anchoring_text)
        .replace("{uncertainty_guidance}", uncertainty_guidance_text)
    )

    # 调用 LLM
    try:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": task_description}]

        #  强制清理emoji (防止Windows GBK编码错误)
        import re

        emoji_pattern = re.compile(
            (
                r"[\U0001F000-\U0001F9FF\U00002300-\U000023FF"
                r"\U00002600-\U000027BF\U00002700-\U000027BF\U0001F900-\U0001F9FF]+"
            ),
            flags=re.UNICODE,
        )
        for msg in messages:
            msg["content"] = emoji_pattern.sub("", msg["content"])

        # 🆕 v7.501 P1-A / v9.3: 使用结构化输出（防止幻觉），失败后重试1次再降级
        structured_llm = llm_model.with_structured_output(RequirementsAnalystOutput, method="function_calling")
        phase2_result = None

        def _build_structured_output_dict(result):
            """将结构化输出结果统一转换为含 structured_output 键的字典"""
            d = result.model_dump()
            d["phase"] = 2
            if "structured_output" not in d:
                d["structured_output"] = {
                    k: v
                    for k, v in d.items()
                    if k not in ("phase", "analysis_layers", "expert_handoff", "structured_output", "processing_log")
                }
            return d

        def _build_json_fallback_dict(raw_content):
            """JSON 降级路径：解析原始内容并写入 structured_output 键"""
            d = _parse_json_response(raw_content)
            d["phase"] = 2
            if "structured_output" not in d:
                d["structured_output"] = {
                    k: v
                    for k, v in d.items()
                    if k not in ("phase", "analysis_layers", "expert_handoff", "structured_output", "processing_log")
                }
            return d

        # --- 第1次结构化尝试 ---
        try:
            structured_result = structured_llm.invoke(messages)
            phase2_result = _build_structured_output_dict(structured_result)
            logger.info("[Phase2] ✅ 结构化输出验证通过（理论约束生效）[structured_attempt=1]")
        except Exception as e1:
            err_str = str(e1)
            if "Field required" in err_str:
                failure_bucket = "missing_required"
            elif "type=" in err_str or "Input should be" in err_str:
                failure_bucket = "type_mismatch"
            else:
                failure_bucket = "parse_error"
            logger.warning(
                f"[Phase2] 结构化输出第1次失败 [structured_attempt=1, failure_bucket={failure_bucket}]: {e1}"
            )

            # --- 第2次结构化重试：附加错误上下文提示 LLM 修正 ---
            retry_hint = (
                f"\n\n[系统提示] 上次JSON输出校验失败，错误分类={failure_bucket}。"
                f"请严格按schema补全缺失字段（尤其是 stakeholder_system.power_dynamics），"
                f"确保所有列表元素为合法对象（不得为null）。错误摘要：{err_str[:300]}"
            )
            retry_messages = messages + [{"role": "user", "content": retry_hint}]
            try:
                structured_result = structured_llm.invoke(retry_messages)
                phase2_result = _build_structured_output_dict(structured_result)
                logger.info(f"[Phase2] ✅ 结构化输出重试成功 [structured_attempt=2, failure_bucket={failure_bucket}]")
            except Exception as e2:
                logger.warning(
                    f"[Phase2] 结构化输出失败，降级到JSON解析 "
                    f"[structured_attempt=2, failure_bucket={failure_bucket}]: {e2}"
                )
                # --- 降级：JSON解析 ---
                response = llm_model.invoke(messages)
                response_content = response.content if hasattr(response, "content") else str(response)
                phase2_result = _build_json_fallback_dict(response_content)

                # 二次 schema 校验：失败则字段级清洗，不丢弃整体结果
                try:
                    RequirementsAnalystOutput.model_validate(phase2_result.get("structured_output", phase2_result))
                    logger.info("[Phase2] 降级JSON二次校验通过 [fallback_sanitized=false]")
                except Exception as validate_err:
                    logger.warning(
                        f"[Phase2] 降级JSON二次校验失败，清洗 stakeholder_system "
                        f"[fallback_sanitized=true]: {validate_err}"
                    )
                    so = phase2_result.get("structured_output", {})
                    ss = so.get("stakeholder_system")
                    if ss is not None and not isinstance(ss, dict):
                        so["stakeholder_system"] = None
                    phase2_result["structured_output"] = so

    except Exception as e:
        logger.error(f"[Phase2] LLM 调用失败: {e}")
        return _phase2_fallback(state, start_time)

    elapsed_ms = (time.time() - start_time) * 1000

    logger.info(f"[OK] [Phase2] 完成（{mode_label}），耗时 {elapsed_ms:.0f}ms")

    return {
        "phase2_result": phase2_result,
        "phase2_elapsed_ms": elapsed_ms,
        "phase2_mode": mode_label,  # 🆕 v7.622: 记录使用的模式
        "analysis_layers": phase2_result.get("analysis_layers", {}),
        "expert_handoff": phase2_result.get("expert_handoff", {}),
        "detected_design_modes": detected_modes,  # NEW: 10 Mode Engine检测结果
        "mode_detection_elapsed_ms": mode_detection_elapsed,  # NEW: 检测耗时
        "processing_log": state.get("processing_log", [])
        + [
            f"[Phase2] 完成（{mode_label}，{elapsed_ms:.0f}ms）",
            f"[ModeDetection] 识别{len(detected_modes)}个模式 ({mode_detection_elapsed:.1f}ms)",
        ],
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
    # C-A01: 补全 problem_solving_approach（UCPPT 搜索引擎依赖此字段，V2此前未生成）
    if has_phase2 and not structured_data.get("problem_solving_approach"):
        psa = _build_problem_solving_approach(structured_data, phase2_result)
        if psa:
            structured_data["problem_solving_approach"] = psa
    project_type = _infer_project_type(structured_data) or "other"  # 双保险：永不写入 None

    # Phase 2 双写：调用旁路分类服务生成 SpaceClassificationResult
    _space_classification_dict = None
    try:
        from intelligent_project_analyzer.services.space_classification_service import (
            SpaceClassificationService,
        )
        _combined_text = " ".join([
            str(structured_data.get("project_task", "")),
            str(structured_data.get("character_narrative", "")),
            str(structured_data.get("project_overview", "")),
            str(structured_data.get("target_users", "")),
        ])
        _spatial_zone_refs = [
            z.get("zone_id", "") for z in (state.get("extracted_spatial_zones") or [])
            if z.get("zone_id")
        ]
        _sc_result = SpaceClassificationService.get_instance().classify(
            _combined_text,
            confirmed_tasks=None,
            spatial_zone_refs=_spatial_zone_refs,
        )
        _space_classification_dict = _sc_result.model_dump()
        logger.info(
            f"[Phase2] space_classification: {_sc_result.project_type} "
            f"({_sc_result.confidence_level}, bucket={_sc_result.primary_bucket})"
        )
    except Exception as _sc_exc:
        logger.warning(f"[Phase2] SpaceClassificationService 调用失败（忽略）: {_sc_exc}")

    structured_data["analysis_mode"] = analysis_mode
    structured_data["project_type"] = project_type

    # v8.0 P0-T1: 注入 detected_design_modes 到 structured_data，打通模式检测管道
    detected_modes = state.get("detected_design_modes", [])
    if detected_modes:
        structured_data["detected_design_modes"] = detected_modes
        # 提取主模式名称供快速访问
        primary_mode = max(detected_modes, key=lambda m: m.get("confidence", 0)) if detected_modes else None
        if primary_mode:
            structured_data["primary_design_mode"] = primary_mode.get("mode", "")
            structured_data["primary_mode_confidence"] = primary_mode.get("confidence", 0)
        logger.info(f"[v8.0 P0] 已注入 {len(detected_modes)} 个设计模式到 structured_data")

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
        "space_classification": _space_classification_dict,   # 新增
        "total_elapsed_ms": total_elapsed,
        "processing_log": state.get("processing_log", [])
        + [f"[Output] 完成 ({elapsed_ms:.0f}ms) - 模式: {analysis_mode}, 置信度: {confidence:.2f}"],
        "node_path": state.get("node_path", []) + ["output"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 条件路由
# ═══════════════════════════════════════════════════════════════════════════════


def _build_problem_solving_approach(
    structured_data: Dict[str, Any],
    phase2_result: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    C-A01: 程序化构建 problem_solving_approach。
    从Phase2输出提取关键字段，替代V1的额外LLM调用（零成本）。
    UCPPT搜索引擎依赖此字段（ucppt_search_engine.py L7417, L10121）。
    """
    analysis = phase2_result.get("analysis_layers", phase2_result)
    core_tension = analysis.get("L3_core_tension") or analysis.get("core_tensions")
    project_task = analysis.get("L4_project_task") or analysis.get("project_task")
    five_whys = analysis.get("L5_1_five_whys") or analysis.get("five_whys_analysis")
    sharpness = analysis.get("L5_sharpness", {})
    score = sharpness.get("score", 0) if isinstance(sharpness, dict) else 0

    if not (core_tension or project_task):
        return None

    return {
        "task_type": "design_strategy",
        "complexity_level": "high" if score >= 70 else "medium",
        "core_challenge": str(core_tension)[:200] if core_tension else "",
        "primary_jtbd": str(project_task)[:200] if project_task else "",
        "depth_reached": "L5" if five_whys else "L4",
        "method": "programmatic_extraction",
        "source": "phase2_output",
    }


def should_execute_phase2(state: RequirementsAnalystState) -> Literal["phase2", "output"]:
    """
    条件路由: 判断是否执行 Phase2

    ✅ v7.621更新：Phase2总是执行（不可跳过）

    策略：
    - 所有场景都执行Phase2深度分析（L1-L7）
    - Insufficient场景虽信息不足，但仍可产生基础分析
    - 确保expert_handoff、JTBD等关键输出总是可用
    - 性能影响：66%场景增加~3s（1.7s → 4.7s）
    """
    info_status = state.get("phase1_info_status", "insufficient")

    logger.info(f"[Route] [路由] Phase2总是执行 (info_status={info_status})")
    return "phase2"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════


def _weighted_info_status_vote(
    precheck_result: Dict[str, Any], phase1_result: Dict[str, Any], mode_adjustment_result: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    🆕 v7.623: 加权投票决定最终info_status

    投票权重：
    - Precheck: 0.4（程序化检测，准确率82%）
    - Phase1: 0.4（LLM判定，准确率78%）
    - Mode调整: 0.2（模式特定要求）

    Args:
        precheck_result: Precheck检测结果
        phase1_result: Phase1 LLM判定结果
        mode_adjustment_result: 模式调整结果

    Returns:
        (final_status, decision_details)
    """
    # 提取各方判定
    precheck_sufficient = precheck_result.get("info_sufficiency", {}).get("is_sufficient", False)
    phase1_status = phase1_result.get("info_status", "insufficient")
    mode_adjusted_status = mode_adjustment_result.get("adjusted_status", phase1_status)

    # 转换为分数（sufficient=1, insufficient=0）
    precheck_score = 1.0 if precheck_sufficient else 0.0
    phase1_score = 1.0 if phase1_status == "sufficient" else 0.0
    mode_score = 1.0 if mode_adjusted_status == "sufficient" else 0.0

    # 加权投票
    weights = {"precheck": 0.4, "phase1": 0.4, "mode": 0.2}

    final_score = precheck_score * weights["precheck"] + phase1_score * weights["phase1"] + mode_score * weights["mode"]

    # 决策阈值：0.5
    final_status = "sufficient" if final_score >= 0.5 else "insufficient"

    # 构建决策详情
    decision_details = {
        "final_status": final_status,
        "final_score": final_score,
        "votes": {
            "precheck": {
                "status": "sufficient" if precheck_sufficient else "insufficient",
                "weight": weights["precheck"],
                "score": precheck_score,
            },
            "phase1": {"status": phase1_status, "weight": weights["phase1"], "score": phase1_score},
            "mode": {"status": mode_adjusted_status, "weight": weights["mode"], "score": mode_score},
        },
        "consensus": precheck_sufficient == (phase1_status == "sufficient"),
        "decision_reason": _build_decision_reason(
            precheck_sufficient, phase1_status, mode_adjusted_status, final_status
        ),
    }

    return final_status, decision_details


def _build_decision_reason(precheck_sufficient: bool, phase1_status: str, mode_status: str, final_status: str) -> str:
    """构建决策理由"""
    if precheck_sufficient and phase1_status == "sufficient" and mode_status == "sufficient":
        return "三方一致判定：信息充足"
    elif not precheck_sufficient and phase1_status == "insufficient" and mode_status == "insufficient":
        return "三方一致判定：信息不足"
    elif final_status == "sufficient":
        supporters = []
        if precheck_sufficient:
            supporters.append("Precheck")
        if phase1_status == "sufficient":
            supporters.append("Phase1")
        if mode_status == "sufficient":
            supporters.append("Mode调整")
        return f"加权投票判定信息充足（支持方：{', '.join(supporters)}）"
    else:
        supporters = []
        if not precheck_sufficient:
            supporters.append("Precheck")
        if phase1_status == "insufficient":
            supporters.append("Phase1")
        if mode_status == "insufficient":
            supporters.append("Mode调整")
        return f"加权投票判定信息不足（支持方：{', '.join(supporters)}）"


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
                    return json.loads(response[start_idx:i + 1])

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
            {"deliverable_id": f"D{i + 1}", "type": d.get("type", "design_strategy"), "priority": "MUST_HAVE"}
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
    """合并 Phase1 和 Phase2 结果

    v9.1: 新增 core_tensions / breakthrough_insight / design_principles / l2_disciplinary_lenses
    v9.2: 新增 L2.5利益相关者 / L4.5五层为什么 / L6假设审计 / L7系统影响 / L8反套路化 / 人性维度
    v9.3: 新增 first_principles / thought_experiments / razor_check / multi_perspective_synthesis
    v10.0.0: 新增 phase_a/b/c 三阶段键回退读取 + constraints_map(A4)
             新键名优先: phase_a_reality → A1/A2/A3/A4; phase_b_excavation → B1-B5; phase_c_validation → C1-C6
    v7.621: structured_output 兜底回退 → 若缺失 structured_output 键则直接用 phase2 扁平结构，
            消除结构化输出成功但数据丢失的静默 Bug
    """
    # ✅ v7.621 Step1: 兜底回退 —— 结构化成功路径返回扁平 dict 时，phase2 本身即等价于 structured_output
    structured_output = phase2.get("structured_output") or phase2
    analysis_layers = phase2.get("analysis_layers", {})
    # v10: 三阶段分组键（新架构输出）
    phase_a = phase2.get("phase_a_reality", {})
    phase_b = phase2.get("phase_b_excavation", {})
    phase_c = phase2.get("phase_c_validation", {})

    # v9.3 fix: project_task 经 model_dump() 后可能为 ProjectTask dict，
    # dict[:100] 会抛出 KeyError: slice(None,100,None)，统一在此归一化为 str
    _pt_raw = structured_output.get("project_task", "")
    if isinstance(_pt_raw, dict):
        _project_task_str = _pt_raw.get("full_statement") or _pt_raw.get("i_want_to") or str(_pt_raw)
    else:
        _project_task_str = str(_pt_raw or "")

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
        "analysis_layers": analysis_layers,
        "expert_handoff": phase2.get("expert_handoff", {}),
        "project_overview": _project_task_str,
        "core_objectives": [_project_task_str[:100]] if _project_task_str else [],
        "project_tasks": [_project_task_str] if _project_task_str else [],
        # v8.0: 传递 problem_types（此前被丢弃）
        "problem_types": (structured_output.get("problem_types") or phase1.get("problem_types") or []),
        # v9.1: Phase2 深度分析字段 → 供 core_task_decomposer 消费
        "core_tensions": structured_output.get("core_tensions", []),
        "breakthrough_insight": structured_output.get("breakthrough_insight", ""),
        "design_principles": structured_output.get("design_principles", []),
        "l2_disciplinary_lenses": structured_output.get("l2_disciplinary_lenses", []),
        "ontology_parameters": structured_output.get("ontology_parameters", []),
        "confidence_score": structured_output.get("confidence_score", 0.0),
        "ontology_suggestions": structured_output.get("ontology_suggestions"),
        # ═══════════════════════════════════════════════════════════
        # v9.2: 深度分析层提取（L2.5 / L4.5 / L6 / L7 / L8 / 人性维度）
        # 来源优先级: structured_output > analysis_layers（兼容两种输出格式）
        # ═══════════════════════════════════════════════════════════
        "stakeholder_system": (lambda ss: ss if isinstance(ss, dict) else None)(
            structured_output.get("stakeholder_system")
            or phase_a.get("A2_stakeholders")
            or analysis_layers.get("L2_5_stakeholder_system")
        ),
        "five_whys_analysis": (
            structured_output.get("five_whys_analysis")
            or phase_b.get("B3_five_whys_analysis")
            or analysis_layers.get("L4_5_five_whys_analysis")
        ),
        "assumption_audit": (
            structured_output.get("assumption_audit")
            or phase_b.get("B5_assumption_audit", {}).get("identified_assumptions")
            or analysis_layers.get("L6_assumption_audit", {}).get("identified_assumptions")
        ),
        "systemic_impact": (
            structured_output.get("systemic_impact")
            or phase_c.get("C4_systemic_impact")
            or analysis_layers.get("L7_systemic_impact")
        ),
        "anti_cliche_check": (
            structured_output.get("anti_cliche_check")
            or phase_c.get("C5_anti_cliche_check")
            or analysis_layers.get("L8_anti_cliche_check")
        ),
        "brand_dna": (phase_a.get("A3_brand_dna") or analysis_layers.get("L2_6_brand_dna")),
        # v10: A4 约束地图
        "constraints_map": (structured_output.get("constraints_map") or phase_a.get("A4_constraints")),
        # 人性维度（从 structured_output 提取）
        "human_dimensions": structured_output.get("human_dimensions"),
        "emotional_landscape": structured_output.get("emotional_landscape", ""),
        "spiritual_aspirations": structured_output.get("spiritual_aspirations", ""),
        "psychological_safety_needs": structured_output.get("psychological_safety_needs", ""),
        "ritual_behaviors": structured_output.get("ritual_behaviors", ""),
        "memory_anchors": structured_output.get("memory_anchors", ""),
        # ─────────────────────────────────────────────────────────
        # v9.3: 多视角对抗 + 思维模型层
        # ─────────────────────────────────────────────────────────
        "first_principles": (
            structured_output.get("first_principles")
            or phase_b.get("B4_first_principles")
            or analysis_layers.get("L1_5_first_principles")
        ),
        "thought_experiments": (
            structured_output.get("thought_experiments")
            or phase_c.get("C3_thought_experiments")
            or analysis_layers.get("L4_6_thought_experiments")
        ),
        "razor_check": (
            structured_output.get("razor_check")
            or analysis_layers.get("L5_razor_check")
            or analysis_layers.get("L5_sharpness", {}).get("razor_check")
        ),
        "multi_perspective_synthesis": (
            structured_output.get("multi_perspective_synthesis")
            or phase_c.get("C6_multi_perspective_synthesis")
            or analysis_layers.get("L9_multi_perspective_synthesis")
        ),
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


def _infer_project_type(structured_data: Dict[str, Any]) -> str:
    """
    推断项目类型 — 委托给 ProjectTypeDetector（SSOT 权威注册表）。

    v7.200+: 不再维护本地关键词硬编码，所有分类定义统一在
    services/project_type_detector.py 的 PROJECT_TYPE_REGISTRY 中维护。
    新增/修改类型只需修改注册表，此函数无需改动。

    Returns:
        project_type ID 字符串，永不返回 None（无匹配时返回 "other"）
    """
    from intelligent_project_analyzer.services.project_type_detector import ProjectTypeDetector

    combined_text = " ".join(
        [
            str(structured_data.get("project_task", "")),
            str(structured_data.get("character_narrative", "")),
            str(structured_data.get("project_overview", "")),
            str(structured_data.get("target_users", "")),
        ]
    )

    detector = ProjectTypeDetector()
    project_type, confidence, reason = detector.detect(combined_text)

    # ── Step 2 + Step 8: 低置信度时触发候选收集 + LLM 回退（后台异步，不阻塞返回） ──
    if project_type is None or confidence < 0.6:
        try:
            from intelligent_project_analyzer.services.project_type_expansion import (
                ProjectTypeCandidateCollector,
            )
            session_id = structured_data.get("session_id", "unknown")
            collector = ProjectTypeCandidateCollector()
            # Step 2: 规则候选收集
            collector.collect_from_session(
                session_id=str(session_id),
                user_text=combined_text,
                structured_data=structured_data,
            )
            # Step 8: LLM 异步回退推理（fire-and-forget）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(
                        collector.async_infer_type_with_llm(
                            combined_text, str(session_id)
                        )
                    )
            except RuntimeError:
                pass  # 无事件循环时静默忽略
        except Exception as _exc:
            logger.debug(f"[项目类型推断] 候选收集异常（忽略）: {_exc}")

    if project_type is None:
        logger.debug("[项目类型推断] 无关键词命中，使用兜底类型 'other'")
        return "other"  # 永不返回 None，避免下游 AttributeError

    logger.debug(f"[项目类型推断] {project_type} (置信度 {confidence:.0%}): {reason}")
    return project_type


# ═══════════════════════════════════════════════════════════════════════════════
# 5. StateGraph 构建
# ═══════════════════════════════════════════════════════════════════════════════

from functools import partial  # noqa: E402


def build_requirements_analyst_graph(llm_model, prompt_manager) -> StateGraph:
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
    workflow.add_node("phase1", partial(phase1_node, llm_model=llm_model, prompt_manager=prompt_manager))
    workflow.add_node("phase2", partial(phase2_node, llm_model=llm_model, prompt_manager=prompt_manager))
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
        self._graph = build_requirements_analyst_graph(self.llm_model, self.prompt_manager).compile()

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

        # 构建初始状态
        initial_state: Dict[str, Any] = {
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
                "space_classification": final_state.get("space_classification"),
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

    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        self._agent = RequirementsAnalystAgentV2(llm_model, config)
        self.llm_model = llm_model
        self.config = config

    def execute(
        self,
        state: Dict[str, Any],
        config=None,
        store=None,
        use_two_phase: bool = True,  # 默认使用 StateGraph 模式
    ) -> AnalysisResult:
        """
        兼容原接口的 execute 方法
        """
        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "unknown")

        return self._agent.execute(user_input, session_id)
