"""
投射调度器 (Projection Dispatcher)

功能：
- 从 state 中提取五轴坐标分数（identity/power/operation/emotion/civilization）
- 加载 output_projections.yaml 配置
- 根据激活规则确定需要生成的视角投射列表
- 为每个激活的投射生成上下文包（analysis_pool + discourse_register + case_template）
- 并行调度 perspective_writer 生成多视角输出

架构位置：
  result_aggregator → 【projection_dispatcher】→ report_guard → pdf_generator

版本：v1.0 (首版实现)
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# 配置路径
CONFIG_DIR = Path(__file__).parent.parent / "config"
PROJECTIONS_FILE = CONFIG_DIR / "output_projections.yaml"

# 手动缓存（替代 @lru_cache，支持加载失败后重试）
_projections_config_cache: Optional[Dict[str, Any]] = None


# ==============================================================================
# 1. 配置加载（带手动缓存 + 失败重试）
# ==============================================================================


def load_projections_config() -> Dict[str, Any]:
    """
    加载 output_projections.yaml 配置。

    使用手动缓存替代 @lru_cache — 仅缓存成功加载的结果。
    如果加载失败（文件不存在或解析错误），不会缓存空结果，
    下次调用时会重新尝试加载。
    """
    global _projections_config_cache
    if _projections_config_cache is not None:
        return _projections_config_cache

    if not PROJECTIONS_FILE.exists():
        logger.warning(f"[projection_dispatcher] 投射配置不存在: {PROJECTIONS_FILE}")
        return {}
    try:
        content = PROJECTIONS_FILE.read_text(encoding="utf-8")
        config = yaml.safe_load(content) or {}
        logger.info(f"[projection_dispatcher] 已加载投射配置 v{config.get('metadata', {}).get('version', '?')}")
        # 仅在成功加载时缓存
        _projections_config_cache = config
        return config
    except Exception as e:
        logger.error(f"[projection_dispatcher] 加载投射配置失败: {e}")
        return {}


def invalidate_projections_cache():
    """手动清除投射配置缓存（用于热更新或测试）"""
    global _projections_config_cache
    _projections_config_cache = None
    logger.info("[projection_dispatcher] 投射配置缓存已清除")


def _get_nested(data: dict, dotted_key: str, default=None):
    """安全读取嵌套字典（支持 'a.b.c' 点号路径）"""
    keys = dotted_key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


# ==============================================================================
# 2. 五轴坐标评分
# ==============================================================================


def calculate_axis_scores(state: Dict[str, Any]) -> Dict[str, float]:
    """
    从 state 中提取五轴坐标分数。

    评分逻辑：
    1. 如果 state 中已有 meta_axis_scores，直接复用
    2. 否则根据 axis_scoring 配置从 state 字段映射
    3. 缺失字段使用默认值

    Returns:
        dict: {"identity": 0.5, "power": 0.3, "operation": 0.5, "emotion": 0.4, "civilization": 0.3}
    """
    # 如果已有评分（如 project_director 已计算），直接复用
    existing = state.get("meta_axis_scores")
    if existing and isinstance(existing, dict) and len(existing) >= 5:
        logger.info(f"[projection_dispatcher] 复用已有五轴评分: {existing}")
        return existing

    config = load_projections_config()
    scoring_rules = config.get("axis_scoring", {})

    scores: Dict[str, float] = {}
    yaml_hit_axes: set = set()  # 记录真正命中了 YAML 字段（非默认值）的轴
    for axis_name in ["identity", "power", "operation", "emotion", "civilization"]:
        rule = scoring_rules.get(axis_name, {})
        default_score = rule.get("default_score", 0.5)
        sources = rule.get("sources", [])

        if not sources:
            scores[axis_name] = default_score
            continue

        # 加权求和
        total_weight = 0.0
        weighted_sum = 0.0
        has_any_source = False

        for source in sources:
            field_path = source.get("field", "")
            weight = source.get("weight", 0.0)
            mode_mapping = source.get("mode_mapping")
            value = _get_nested(state, field_path)

            if value is not None:
                # 尝试将值转为分数（支持 mode_mapping 字典映射）
                score = _value_to_score(value, mode_mapping=mode_mapping)
                if score is not None:
                    weighted_sum += score * weight
                    total_weight += weight
                    has_any_source = True

        if has_any_source and total_weight > 0:
            scores[axis_name] = round(weighted_sum / total_weight, 3)
            yaml_hit_axes.add(axis_name)
        else:
            scores[axis_name] = default_score

    # ===========================================================================
    # 动态维度贡献层 (v9.0)
    # 修复：LLM 生成的项目专属维度（id 自由字符串）无法命中 YAML 硬编码字段名，
    # 导致 emotion/civilization 轴长期使用 default_score(0.4/0.3) 的断链问题。
    # 方案：根据每个维度的 category/source 将用户滑块值聚合到对应元轴。
    # ===========================================================================
    CATEGORY_TO_AXIS = {
        "aesthetic": "civilization",
        "experience": "emotion",
        "functional": "operation",
        "technology": "operation",
        "resource": "power",
        "special": "identity",
    }
    SOURCE_BONUS_AXIS = {
        "insight": "identity",
        "decision": "power",
    }

    selected_dims = state.get("selected_radar_dimensions", [])
    radar_values = state.get("radar_dimension_values", {})

    if selected_dims and radar_values:
        dynamic_vals: Dict[str, List[float]] = {ax: [] for ax in scores}

        for dim in selected_dims:
            dim_id = dim.get("id") or dim.get("dimension_id", "")
            raw_val = radar_values.get(dim_id)
            if raw_val is None:
                continue
            # 归一化到 0-1
            normalized = max(0.0, min(1.0, float(raw_val) / 100.0))

            # category → primary axis
            target_axis = CATEGORY_TO_AXIS.get(dim.get("category", ""))
            if target_axis:
                dynamic_vals[target_axis].append(normalized)

            # source → bonus axis（避免重复累加同一轴）
            bonus_axis = SOURCE_BONUS_AXIS.get(dim.get("source", ""))
            if bonus_axis and bonus_axis != target_axis:
                dynamic_vals[bonus_axis].append(normalized)

        # 将动态聚合值与静态 YAML 评分混合
        provenance: Dict[str, str] = {}
        for axis in list(scores.keys()):
            dyn = dynamic_vals.get(axis, [])
            if not dyn:
                provenance[axis] = "yaml_only"
                continue
            dyn_avg = sum(dyn) / len(dyn)
            if axis in yaml_hit_axes:
                # 该轴有真实 YAML 字段命中：保留 70% 静态 + 30% 动态
                scores[axis] = round(scores[axis] * 0.7 + dyn_avg * 0.3, 3)
                provenance[axis] = "blended"
            else:
                # 该轴仅有默认值（YAML 字段全部缺失）：100% 使用动态值
                scores[axis] = round(dyn_avg, 3)
                provenance[axis] = "dynamic_only"

        logger.info(f"[projection_dispatcher] 动态维度贡献层: {provenance}")

    # ── v8.0: 设计师行为动机轴值修正层（置信度 >= 0.5，幅度 ±0.08~0.12）──
    _dbm_ax = state.get("designer_behavioral_motivation")
    if isinstance(_dbm_ax, dict) and _dbm_ax.get("confidence", 0) >= 0.5:
        _pri = _dbm_ax.get("primary", "")
        _orig = scores.copy()
        if _pri == "D1_survival_securing":
            scores["operation"]     = min(1.0, scores.get("operation", 0.5)     + 0.10)
            scores["civilization"]  = max(0.1, scores.get("civilization", 0.3)  - 0.10)
        elif _pri == "D2_competitive_winning":
            scores["power"]         = min(1.0, scores.get("power", 0.3)         + 0.12)
        elif _pri == "D3_breakthrough_innovation":
            scores["identity"]      = min(1.0, scores.get("identity", 0.5)      + 0.10)
            scores["emotion"]       = min(1.0, scores.get("emotion", 0.4)       + 0.08)
        elif _pri == "D4_capability_learning":
            scores["operation"]     = min(1.0, scores.get("operation", 0.5)     + 0.12)
            scores["civilization"]  = max(0.1, scores.get("civilization", 0.3)  - 0.08)
        elif _pri == "D5_structural_clarification":
            scores["operation"]     = min(1.0, scores.get("operation", 0.5)     + 0.08)
            scores["emotion"]       = max(0.1, scores.get("emotion", 0.4)       - 0.06)
        elif _pri == "D6_strategic_construction":
            scores["civilization"]  = min(1.0, scores.get("civilization", 0.3)  + 0.12)
        if scores != _orig:
            logger.info(f"[projection_dispatcher] v8.0动机轴修正 {_pri}: {_orig} → {scores}")

    logger.info(f"[projection_dispatcher] 五轴评分: {scores}")
    return scores


def _value_to_score(value: Any, mode_mapping: Optional[Dict[str, float]] = None) -> Optional[float]:
    """将各种类型的值映射为 0-1 分数

    Args:
        value: 需要转化的值
        mode_mapping: 可选的字符串→分数映射表（用于模式ID等枚举值）
    """
    if isinstance(value, (int, float)):
        # 如果已经是 0-1 范围内的数
        if 0 <= value <= 1:
            return float(value)
        # 如果是 0-100 范围
        if 0 <= value <= 100:
            return value / 100.0
        # 如果是 0-10 范围（如雷达分数）
        if 0 <= value <= 10:
            return value / 10.0
        return 0.5

    if isinstance(value, str):
        # 空字符串 → 低分
        if not value.strip():
            return 0.2
        # 优先查找 mode_mapping 精确匹配
        if mode_mapping and isinstance(mode_mapping, dict):
            stripped = value.strip()
            if stripped in mode_mapping:
                return float(mode_mapping[stripped])
            # 模糊匹配：mode_mapping key 在 value 中 或 value 在 key 中
            for mk, mv in mode_mapping.items():
                if mk in stripped or stripped in mk:
                    return float(mv)
        # 有内容 → 根据长度给分（粗略启发式）
        length = len(value.strip())
        if length < 20:
            return 0.3
        if length < 100:
            return 0.5
        if length < 500:
            return 0.7
        return 0.9

    if isinstance(value, dict):
        # 字典非空 → 高分
        return 0.8 if value else 0.2

    if isinstance(value, list):
        # 列表长度越长分越高
        if not value:
            return 0.2
        return min(0.9, 0.3 + len(value) * 0.1)

    return None


# ==============================================================================
# 3. 投射激活判定
# ==============================================================================


def determine_active_projections(
    axis_scores: Dict[str, float],
    state: Dict[str, Any],
    user_selected: Optional[List[str]] = None,
) -> List[str]:
    """
    确定需要激活的投射视角列表。

    激活优先级：
    1. 用户手动选择 > 自动规则
    2. always: true → 总是激活
    3. when_modes → 匹配当前模式
    4. when_axis_above → 超过阈值
    5. when_task_contains → 原始需求包含关键词

    Args:
        axis_scores: 五轴坐标
        state: 完整工作流状态
        user_selected: 用户手动选择的视角列表（可选）

    Returns:
        list: 激活的投射ID列表
    """
    config = load_projections_config()
    projections = config.get("projections", {})
    dispatch_rules = config.get("dispatch_rules", {})
    max_parallel = dispatch_rules.get("max_parallel_projections", 3)
    threshold = dispatch_rules.get("activation_threshold", 0.5)

    # 用户手动选择优先
    if user_selected:
        valid = [p for p in user_selected if p in projections]
        logger.info(f"[projection_dispatcher] 用户手动选择投射: {valid}")
        return valid[:max_parallel]

    # 如果 state 中已有 active_projections，复用
    existing_projections = state.get("active_projections")
    if existing_projections and isinstance(existing_projections, list):
        logger.info(f"[projection_dispatcher] 复用已有投射列表: {existing_projections}")
        return existing_projections

    activated = []
    activation_scores = {}  # 用于优先级排序

    # 获取当前模式
    detected_modes = state.get("detected_design_modes", [])
    if isinstance(detected_modes, str):
        detected_modes = [detected_modes]
    # 提取模式ID（如 "M5_rural_context" → "M5"）
    mode_ids = []
    for m in detected_modes:
        if isinstance(m, str):
            mode_ids.append(m.split("_")[0].upper() if "_" in m else m.upper())

    user_input = state.get("user_input", "")

    # ── v8.0: 动机激活偏置前置数据 ──
    _pm = state.get("project_motivation")
    _pm_primary = _pm.get("primary", "") if isinstance(_pm, dict) else ""
    _pm_conf = _pm.get("confidence", 0) if isinstance(_pm, dict) else 0
    _mot_mapping = config.get("motivation_projection_mapping", {})

    _dbm = state.get("designer_behavioral_motivation")
    _dbm_primary = _dbm.get("primary", "") if isinstance(_dbm, dict) else ""
    _dbm_conf = _dbm.get("confidence", 0) if isinstance(_dbm, dict) else 0
    # D-type → 优先激活的投射ID
    _D_PROJ_BOOST: Dict[str, str] = {
        "D1_survival_securing":       "construction_execution",
        "D2_competitive_winning":      "investor_operator",
        "D3_breakthrough_innovation":  "aesthetic_critique",
        "D4_capability_learning":      "design_professional",
        "D5_structural_clarification": "design_professional",
        "D6_strategic_construction":   "government_policy",
    }

    for proj_id, proj_config in projections.items():
        auto_rules = proj_config.get("auto_activate", {})

        # always: true — 必须激活
        if auto_rules.get("always", False):
            activated.append(proj_id)
            activation_scores[proj_id] = 1.0
            continue

        score = 0.0

        # when_modes 匹配
        when_modes = auto_rules.get("when_modes", [])
        if when_modes and mode_ids:
            for wm in when_modes:
                if str(wm).upper() in mode_ids:
                    score += 0.5
                    break

        # when_axis_above 匹配
        when_axis = auto_rules.get("when_axis_above", {})
        for axis_name, min_val in when_axis.items():
            current_val = axis_scores.get(axis_name, 0)
            if current_val >= min_val:
                score += 0.3 * (current_val / max(min_val, 0.01))

        # when_task_contains 匹配
        when_keywords = auto_rules.get("when_task_contains", [])
        if when_keywords and user_input:
            for kw in when_keywords:
                if kw in user_input:
                    score += 0.4
                    break

        # ── v8.0: 项目动机激活偏置（来自 Phase1 LLM 识别的12类项目动机）──
        if _pm_primary and _pm_conf >= 0.3:
            _mot_entry = _mot_mapping.get(_pm_primary, {})
            if isinstance(_mot_entry, dict):
                if _mot_entry.get("primary_projection") == proj_id:
                    score += _mot_entry.get("signal_weight", 0.3) * 0.5  # 最多 +0.3
                elif _mot_entry.get("secondary_projection") == proj_id:
                    score += _mot_entry.get("signal_weight", 0.2) * 0.25  # 最多 +0.15

        # ── v8.0: D-type 行为动机激活偏置（置信度 >= 0.5 时生效）──
        if _dbm_primary and _dbm_conf >= 0.5:
            if _D_PROJ_BOOST.get(_dbm_primary) == proj_id:
                score += 0.15

        if score >= threshold:
            activated.append(proj_id)
            activation_scores[proj_id] = score

    # 按激活分数排序，限制最大并行数
    activated.sort(key=lambda x: activation_scores.get(x, 0), reverse=True)
    activated = activated[:max_parallel]

    # 确保默认投射在列表中
    defaults = dispatch_rules.get("default_projections", [])
    for d in defaults:
        if d not in activated and d in projections:
            activated.insert(0, d)

    # 再次限制
    activated = activated[:max_parallel]

    logger.info(f"[projection_dispatcher] 激活投射: {activated} (scores: {activation_scores})")
    return activated


# ==============================================================================
# 4. 投射上下文包组装
# ==============================================================================


def build_projection_context(
    projection_id: str,
    projection_config: Dict[str, Any],
    analysis_pool: Dict[str, Any],
    axis_scores: Dict[str, float],
    case_templates: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    为单个投射视角组装完整上下文包。

    上下文包结构：
    {
        "projection_id": "design_professional",
        "projection_name": "设计专业报告",
        "discourse_register": {...},
        "axis_weights": {...},
        "section_priority": [...],
        "value_anchor": "...",
        "risk_focus": "...",
        "analysis_pool": {...},  # 专家分析结果池
        "axis_scores": {...},    # 五轴坐标
        "case_template": "..."   # CASE 示范文本
    }
    """
    # 加载 CASE 模板
    case_template_key = projection_config.get("case_template_key", "")
    case_text = ""
    if case_templates and case_template_key:
        case_text = case_templates.get(case_template_key, "")

    context = {
        "projection_id": projection_id,
        "projection_name": projection_config.get("name", projection_id),
        "target_audience": projection_config.get("target_audience", []),
        "discourse_register": projection_config.get("discourse_register", {}),
        "axis_weights": projection_config.get("axis_weights", {}),
        "section_priority": projection_config.get("section_priority", []),
        "value_anchor": projection_config.get("value_anchor", ""),
        "risk_focus": projection_config.get("risk_focus", ""),
        "analysis_pool": analysis_pool,
        "axis_scores": axis_scores,
        "case_template": case_text,
    }

    return context


# ==============================================================================
# 5. 投射调度器主函数
# ==============================================================================


async def dispatch_projections(
    state: Dict[str, Any],
    llm_model: Any = None,
    user_selected: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    投射调度器主入口（异步）。

    流程：
    1. 计算五轴坐标
    2. 确定激活投射列表
    3. 加载 CASE 模板
    4. 并行调度 perspective_writer 生成各视角输出
    5. 返回更新的 state 字段

    Args:
        state: 完整工作流状态
        llm_model: LLM 实例（用于 perspective writer）
        user_selected: 用户手动选择的投射视角

    Returns:
        dict: 需要更新的 state 字段
            - meta_axis_scores: 五轴坐标
            - active_projections: 激活的投射列表
            - perspective_outputs: 各视角输出内容
    """
    logger.info("[projection_dispatcher] === 投射调度开始 ===")

    # 1. 计算五轴坐标
    axis_scores = calculate_axis_scores(state)

    # 2. 确定激活投射
    active_projections = determine_active_projections(axis_scores, state, user_selected)

    if not active_projections:
        logger.warning("[projection_dispatcher] 无激活投射，跳过")
        return {
            "meta_axis_scores": axis_scores,
            "active_projections": [],
            "perspective_outputs": {},
        }

    # 3. 加载配置和 CASE 模板
    config = load_projections_config()
    projections_config = config.get("projections", {})

    # 加载 CASE 模板（延迟导入避免循环依赖）
    case_templates = {}
    try:
        from .sf_knowledge_loader import load_perspective_case_templates

        case_templates = load_perspective_case_templates()
    except Exception as e:
        logger.warning(f"[projection_dispatcher] 加载 CASE 模板失败: {e}")

    # 4. 组装分析池（从 state 中提取专家分析结果）
    analysis_pool = _extract_analysis_pool(state)

    # 5. 并行生成各视角输出
    perspective_outputs = {}
    tasks = []

    for proj_id in active_projections:
        proj_config = projections_config.get(proj_id, {})
        if not proj_config:
            logger.warning(f"[projection_dispatcher] 投射 {proj_id} 无配置，跳过")
            continue

        context = build_projection_context(proj_id, proj_config, analysis_pool, axis_scores, case_templates)

        if llm_model:
            tasks.append(_generate_perspective_output(proj_id, context, llm_model))
        else:
            # 无 LLM 时，返回结构化上下文（用于调试/测试）
            perspective_outputs[proj_id] = {
                "status": "pending_llm",
                "context": context,
                "message": "LLM not available, returning structured context for manual generation",
            }

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for proj_id, result in zip(active_projections, results):
            if isinstance(result, Exception):
                logger.error(f"[projection_dispatcher] 投射 {proj_id} 生成失败: {result}")
                perspective_outputs[proj_id] = {
                    "status": "error",
                    "error": str(result),
                }
            else:
                perspective_outputs[proj_id] = result

    logger.info(f"[projection_dispatcher] === 投射调度完成 === 生成 {len(perspective_outputs)} 个视角")

    return {
        "meta_axis_scores": axis_scores,
        "active_projections": active_projections,
        "perspective_outputs": perspective_outputs,
    }


def dispatch_projections_sync(
    state: Dict[str, Any],
    llm_model: Any = None,
    user_selected: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """投射调度器同步版本（供 LangGraph 节点直接调用）"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果事件循环已在运行（如在 LangGraph async 环境中），
            # 创建新线程执行
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, dispatch_projections(state, llm_model, user_selected))
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(dispatch_projections(state, llm_model, user_selected))
    except RuntimeError:
        return asyncio.run(dispatch_projections(state, llm_model, user_selected))


# ==============================================================================
# 6. 辅助函数
# ==============================================================================


def _extract_analysis_pool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 state 中提取完整分析结果池。

    分析池 = 所有专家分析结果的集合，是投射写手的原料。
    """
    pool = {}

    # 专家分析结果
    agent_results = state.get("agent_results", {})
    if agent_results:
        pool["expert_outputs"] = {}
        for agent_name, result in agent_results.items():
            if isinstance(result, dict):
                pool["expert_outputs"][agent_name] = {
                    "content": result.get("content", ""),
                    "structured_data": result.get("structured_data", {}),
                }

    # 最终报告（result_aggregator 的输出）
    final_report = state.get("final_report")
    if final_report:
        pool["final_report"] = final_report if isinstance(final_report, dict) else {}

    # 结构化需求
    structured_reqs = state.get("structured_requirements")
    if structured_reqs:
        pool["structured_requirements"] = structured_reqs

    # 项目分类与模式
    pool["project_info"] = {
        "project_type": state.get("project_type", ""),
        "detected_modes": state.get("detected_design_modes", []),
        "user_input": state.get("user_input", ""),
    }

    # 雷达分数
    radar = state.get("radar_scores")
    if radar:
        pool["radar_scores"] = radar

    return pool


async def _generate_perspective_output(
    projection_id: str,
    context: Dict[str, Any],
    llm_model: Any,
) -> Dict[str, Any]:
    """
    调用 LLM 生成单个视角的输出。

    Prompt 结构：
    1. 角色设定（基于 discourse_register）
    2. 分析原料（analysis_pool 摘要）
    3. 输出要求（section_priority + 话语层约束）
    4. CASE 示范（few-shot）
    """
    discourse = context.get("discourse_register", {})
    tone = discourse.get("tone", "专业写作")
    vocab_bias = discourse.get("vocabulary_bias", [])
    avoid = discourse.get("avoid", [])
    depth = discourse.get("depth", "")
    sections = context.get("section_priority", [])
    value_anchor = context.get("value_anchor", "")
    risk_focus = context.get("risk_focus", "")
    case_template = context.get("case_template", "")
    target_audience = context.get("target_audience", [])
    projection_name = context.get("projection_name", projection_id)

    # 组装分析摘要
    analysis_summary = _summarize_analysis_pool(context.get("analysis_pool", {}))

    # 构建 prompt
    prompt = f"""# 投射写手指令

## 你的角色
你是「{projection_name}」视角的专业写手。
目标受众：{', '.join(target_audience)}

## 话语层约束
- 语调：{tone}
- 优先使用词汇：{', '.join(vocab_bias)}
- 禁用词汇：{', '.join(avoid)}
- 深度路径：{depth}

## 价值锚点
{value_anchor}

## 风险关注
{risk_focus}

## 分析原料（来自多专家并行分析的结果池）
{analysis_summary}

## 输出章节结构（按优先级排列）
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(sections))}

## 输出要求
1. 严格遵守话语层约束——使用指定词汇，避免禁用词汇
2. 每个章节 200-500 字，总输出 1500-4000 字
3. 以 {value_anchor} 为核心论点展开
4. 确保每个判断都有分析池中的证据支撑
5. 不要生成分析池中没有依据的内容（禁止幻觉）
"""

    if case_template:
        # 截取 CASE 模板的前 2000 字作为 few-shot
        case_excerpt = case_template[:2000] + ("\n...(截取)" if len(case_template) > 2000 else "")
        prompt += f"""
## 参考范例（CASE few-shot）
以下是该视角的示范文本风格和结构：
---
{case_excerpt}
---
请参考上述范例的语言风格和结构深度，但内容必须基于上方分析原料。
"""

    prompt += "\n## 开始输出\n请按照上述章节结构，生成完整的投射视角报告。"

    try:
        # 调用 LLM
        from langchain_core.messages import HumanMessage

        response = await llm_model.ainvoke([HumanMessage(content=prompt)])

        output_text = response.content if hasattr(response, "content") else str(response)

        return {
            "status": "completed",
            "projection_id": projection_id,
            "projection_name": projection_name,
            "content": output_text,
            "token_count": len(output_text),
            "sections": sections,
            "discourse_register": discourse,
        }

    except Exception as e:
        logger.error(f"[projection_dispatcher] LLM 调用失败 ({projection_id}): {e}")
        return {
            "status": "error",
            "projection_id": projection_id,
            "error": str(e),
        }


def _summarize_analysis_pool(pool: Dict[str, Any]) -> str:
    """将分析池压缩为适合 prompt 的摘要文本"""
    parts = []

    # 项目基本信息
    project_info = pool.get("project_info", {})
    if project_info:
        parts.append(f"### 项目信息\n- 类型: {project_info.get('project_type', '未知')}")
        parts.append(f"- 设计模式: {project_info.get('detected_modes', [])}")
        user_input = project_info.get("user_input", "")
        if user_input:
            parts.append(f"- 原始需求: {user_input[:500]}")

    # 专家输出摘要
    expert_outputs = pool.get("expert_outputs", {})
    if expert_outputs:
        parts.append("\n### 专家分析结果")
        for agent_name, output in expert_outputs.items():
            content = output.get("content", "")
            if content:
                # 截取关键部分
                excerpt = content[:800] + ("..." if len(content) > 800 else "")
                parts.append(f"\n**{agent_name}**:\n{excerpt}")

    # 最终报告摘要
    final_report = pool.get("final_report", {})
    if final_report and isinstance(final_report, dict):
        report_title = final_report.get("project_name", final_report.get("title", ""))
        if report_title:
            parts.append(f"\n### 综合报告标题: {report_title}")

        # 提取关键字段
        executive = final_report.get("executive_summary", "")
        if executive:
            parts.append(f"\n**执行摘要**: {executive[:500]}")

    # 雷达分数
    radar = pool.get("radar_scores", {})
    if radar:
        parts.append(f"\n### 雷达分数: {radar}")

    return "\n".join(parts) if parts else "(分析池为空)"
