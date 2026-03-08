"""
输出意图检测节点 (v10.1)

独立节点，位于 requirements_analyst 之后、feasibility_analyst 之前。

v10.1 重构原则：
  - 不针对任何具体项目硬编码（适配 190+ 问题类型的多元性）
  - 输出 output_framework_signals：通用的范围/约束/维度信号
  - 信号是抽象的描述，不是具体的章节模板
  - 下游任务梳理器（LLM）根据信号动态推理框架结构

检测内容：
  1. 交付类型（文件给谁看）：四源交叉验证
  2. 身份模式（空间为谁设计）：多源匹配
  3. 范围信号（多大/多深/多长）：从输入推断
  4. 约束信号（什么限制最紧）：从输入提取
  5. 必须覆盖维度（哪些特殊领域不可缺）：从需求推断

设计原则：
  - 不猜不漏不臆造：三源中任意两源命中才 confirmed，单源仅作 candidate
  - 用户明确说了直接用，不追问
  - 高置信时不追问，有 candidate 时一次 interrupt 解决
  - design_professional 保底（always）
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from langgraph.types import Command, interrupt

# v8.2: 动态步骤追踪装饰器
from ...utils.node_tracker import track_active_step

logger = logging.getLogger(__name__)


# ==================================================================================
# 🆕 v12.0: 空间区域提取 + 约束信封组装
# ==================================================================================


def _extract_spatial_zones(structured_requirements: Dict, user_input: str) -> List[Dict[str, Any]]:
    """
    🆕 v12.0: 从结构化需求和用户输入中提取空间区域列表。

    返回: [{"id": "overall", "label": "整体", "source": "preset"}, ...]
    """
    zones = [{"id": "overall", "label": "整体", "source": "preset"}]
    seen_ids = {"overall"}

    # 从 user_input 正则提取楼层和功能区
    floor_patterns = [
        (r"(\d+)\s*[楼层Ff]", lambda m: (f"{m.group(1)}f", f"{m.group(1)}F")),
        (r"地下室", lambda m: ("basement", "地下室")),
        (r"阁楼", lambda m: ("attic", "阁楼")),
        (r"露台", lambda m: ("terrace", "露台")),
        (r"庭院|花园|院子", lambda m: ("garden", "庭院")),
        (r"车库", lambda m: ("garage", "车库")),
        (r"屋顶", lambda m: ("rooftop", "屋顶")),
    ]

    for pattern, id_label_fn in floor_patterns:
        for match in re.finditer(pattern, user_input):
            zone_id, zone_label = id_label_fn(match)
            if zone_id not in seen_ids:
                zones.append({"id": zone_id, "label": zone_label, "source": "extracted"})
                seen_ids.add(zone_id)

    # 从 structured_requirements 提取功能区
    spatial_desc = structured_requirements.get("spatial_description", {})
    if isinstance(spatial_desc, dict):
        for zone_name in spatial_desc.get("zones", []):
            zone_id = re.sub(r"\s+", "_", zone_name.lower().strip())
            if zone_id and zone_id not in seen_ids:
                zones.append({"id": zone_id, "label": zone_name, "source": "extracted"})
                seen_ids.add(zone_id)

    # 从 user_input 提取常见功能区名称
    room_patterns = [
        (r"客厅", "living_room", "客厅"),
        (r"餐厅", "dining_room", "餐厅"),
        (r"厨房", "kitchen", "厨房"),
        (r"主卧|主卧室", "master_bedroom", "主卧"),
        (r"书房", "study", "书房"),
        (r"卫生间|洗手间|浴室", "bathroom", "卫生间"),
        (r"儿童房", "kids_room", "儿童房"),
        (r"玄关", "entrance", "玄关"),
    ]
    for pattern, zone_id, zone_label in room_patterns:
        if re.search(pattern, user_input) and zone_id not in seen_ids:
            zones.append({"id": zone_id, "label": zone_label, "source": "extracted"})
            seen_ids.add(zone_id)

    logger.info(f"🗺️ [v12.0] 提取到 {len(zones)} 个空间区域: {[z['label'] for z in zones]}")
    return zones


# ─── v12.1: 约束维度映射加载 + 推荐构建 ───

_constraint_display_cache: Dict[str, Any] | None = None


def _load_constraint_display() -> Dict[str, Any]:
    """加载 config/constraint_display.yaml 的约束维度映射表"""
    global _constraint_display_cache
    if _constraint_display_cache is not None:
        return _constraint_display_cache

    config_path = Path(__file__).parent.parent.parent.parent / "config" / "constraint_display.yaml"
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            _constraint_display_cache = data.get("constraint_dimensions", {})
        except Exception as e:
            logger.warning(f"⚠️ [v12.1] 加载 constraint_display.yaml 失败: {e}")
            _constraint_display_cache = {}
    else:
        logger.warning(f"⚠️ [v12.1] constraint_display.yaml 不存在: {config_path}")
        _constraint_display_cache = {}
    return _constraint_display_cache


def _build_recommended_constraints(
    mandatory_dims: List[str],
    constraints: List[Dict[str, Any]],
    visual_constraints: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    🆕 v12.1: 将后端检测到的 mandatory_dimensions 和 constraints
    转换为前端可展示的推荐约束列表。

    Returns:
        [{id, label, desc, category, recommended, source, evidence}]
    """
    display_map = _load_constraint_display()
    result = []
    seen_ids = set()

    # A. mandatory_dimensions → 领域能力推荐
    for dim_id in mandatory_dims:
        if dim_id in seen_ids:
            continue
        seen_ids.add(dim_id)
        info = display_map.get(dim_id, {})
        result.append(
            {
                "id": dim_id,
                "label": info.get("label", dim_id),
                "desc": info.get("desc", ""),
                "category": info.get("category", "domain_capability"),
                "recommended": True,
                "source": "mandatory_dimensions",
                "evidence": [f"从项目需求中检测到 {info.get('label', dim_id)} 相关信号"],
            }
        )

    # B. constraints → 项目约束推荐
    for c in constraints:
        c_type = c.get("type", "")
        if c_type in seen_ids:
            continue
        seen_ids.add(c_type)
        info = display_map.get(c_type, {})
        result.append(
            {
                "id": c_type,
                "label": info.get("label", c_type),
                "desc": info.get("desc", ""),
                "category": info.get("category", "project_constraint"),
                "recommended": True,
                "source": "constraints",
                "evidence": [f"检测到 {info.get('label', c_type)} 约束信号"],
            }
        )

    # C. 如果有视觉约束中的额外信号，也包含
    if visual_constraints:
        existing_conditions = visual_constraints.get("existing_conditions", [])
        if existing_conditions and "visual_evidence" not in seen_ids:
            result.append(
                {
                    "id": "visual_evidence",
                    "label": "现场实况",
                    "desc": f"从上传图片中检测到 {len(existing_conditions)} 项现场条件",
                    "category": "project_constraint",
                    "recommended": True,
                    "source": "visual_analysis",
                    "evidence": [str(ec)[:80] for ec in existing_conditions[:3]],
                }
            )

    logger.info(f"🎯 [v12.1] 构建推荐约束: {len(result)} 项 ({[r['id'] for r in result]})")
    return result


def _build_constraint_envelope(
    constraints_by_zone: Dict[str, List[Dict]],
    spatial_zones: List[Dict[str, Any]],
    style_tendencies: Dict | None = None,
) -> str:
    """
    🆕 v12.0: 组装三层约束信封文本。

    按区域分组输出，单区域项目不分组。
    总长度软上限 800 字符，超出时按 L3→L2→L1 优先级截断。
    """
    zone_id_to_label = {z["id"]: z["label"] for z in spatial_zones}
    sections = []

    # 判断是否为多区域
    effective_zones = [zid for zid in constraints_by_zone if constraints_by_zone[zid]]
    is_multi_zone = len(effective_zones) > 1 or (len(effective_zones) == 1 and effective_zones[0] != "overall")

    level_icons = {"immutable": "🔒", "baseline": "📐", "opportunity": "✨"}
    level_labels = {"immutable": "L1 不可变", "baseline": "L2 基准", "opportunity": "L3 机会"}

    for zone_id in ["overall"] + [z for z in effective_zones if z != "overall"]:
        zone_constraints = constraints_by_zone.get(zone_id, [])
        if not zone_constraints:
            continue

        zone_label = zone_id_to_label.get(zone_id, zone_id)

        # 按级别分组
        by_level: Dict[str, List[str]] = {"immutable": [], "baseline": [], "opportunity": []}
        for c in zone_constraints:
            level = c.get("level", "baseline")
            desc = c.get("description", "")
            if desc:
                by_level.setdefault(level, []).append(desc)

        lines = []
        if is_multi_zone:
            lines.append(f"\n## {zone_label}")

        for level in ("immutable", "baseline", "opportunity"):
            items = by_level.get(level, [])
            if items:
                icon = level_icons.get(level, "")
                label = level_labels.get(level, level)
                lines.append(f"### {icon} {label}")
                for item in items[:5]:  # 每级别最多5条
                    lines.append(f"- {item}")

        if lines:
            sections.append("\n".join(lines))

    # 风格倾向（全局）
    if style_tendencies:
        style_lines = []
        prefer = style_tendencies.get("prefer", [])
        avoid = style_tendencies.get("avoid", [])
        if prefer:
            style_lines.append(f"### 风格偏好: {', '.join(prefer[:5])}")
        if avoid:
            style_lines.append(f"### 倾向避免: {', '.join(avoid[:5])}")
        if style_lines:
            sections.append("\n".join(style_lines))

    if not sections:
        return ""

    envelope = "=== 设计参照系（系统自动识别）===\n" + "\n".join(sections) + "\n=== END ==="

    # 软上限截断
    if len(envelope) > 800:
        logger.warning(f"⚠️ [v12.0] 约束信封超长 ({len(envelope)} 字符)，将截断")
        envelope = envelope[:797] + "..."

    return envelope


async def _run_constraint_pipeline(state: dict) -> Dict[str, Any]:
    """
    🆕 v12.0: 约束识别管线主函数。

    从 state 中读取 uploaded_visual_references，
    对约束源图片执行结构化提取，汇总并生成约束信封。

    Returns:
        visual_constraints dict（写入 state），若无图片则返回 None
    """
    import asyncio
    from pathlib import Path

    from ...services.file_processor import MAX_CONSTRAINT_EXTRACTIONS, ConstraintSourceExtractor
    from ...services.file_processor import file_processor as _fp

    uploaded_refs = state.get("uploaded_visual_references") or []
    if not uploaded_refs:
        logger.info("📷 [v12.0] 无上传图片，跳过约束管线")
        return None

    # 筛选约束源图片
    constraint_sources = []
    style_refs = []
    for ref in uploaded_refs:
        features = ref.get("structured_features", {})
        img_type = features.get("image_type", "style_reference")
        if img_type == "constraint_source":
            constraint_sources.append(ref)
        elif img_type == "style_reference":
            style_refs.append(ref)

    if not constraint_sources and not style_refs:
        logger.info("📷 [v12.0] 无约束源/风格参考图片，跳过约束管线")
        return None

    # 构建提取器（复用现有 file_processor 的 vision_llm）
    extractor = ConstraintSourceExtractor(
        vision_llm=_fp.vision_llm if hasattr(_fp, "vision_llm") else None,
        enable_vision_api=_fp.enable_vision_api if hasattr(_fp, "enable_vision_api") else False,
    )

    # 并行提取约束源图片（上限 MAX_CONSTRAINT_EXTRACTIONS）
    constraints_by_zone: Dict[str, List[Dict]] = {}
    spatial_topologies: Dict[str, Dict] = {}
    existing_conditions: Dict[str, Dict] = {}

    if constraint_sources:
        tasks = []
        for ref in constraint_sources[:MAX_CONSTRAINT_EXTRACTIONS]:
            features = ref.get("structured_features", {})
            subtype = features.get("image_subtype", "site_photo")
            zone = features.get("spatial_zone_guess", "整体")
            # 用户标注 > AI 猜测
            user_zone = ref.get("spatial_zone")
            effective_zone = user_zone if user_zone else zone

            tasks.append(
                extractor.extract_constraint_source_details(
                    file_path=Path(ref["file_path"]),
                    image_subtype=subtype,
                    spatial_zone=effective_zone,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"⚠️ [v12.0] 约束提取异常: {result}")
                continue

            zone = result.get("spatial_zone", "整体")

            # 按区域汇总约束
            for c in result.get("constraints", []):
                constraints_by_zone.setdefault(zone, []).append(c)

            # 汇总空间拓扑
            topo = result.get("spatial_topology")
            if topo:
                spatial_topologies[zone] = topo

            # 汇总现有条件
            cond = result.get("existing_conditions")
            if cond:
                existing_conditions[zone] = cond

    # 汇总风格倾向（来自风格参考图）
    style_tendencies: Dict[str, List[str]] = {"prefer": [], "avoid": []}
    for ref in style_refs:
        features = ref.get("structured_features", {})
        for kw in features.get("style_keywords", []):
            if kw and kw not in style_tendencies["prefer"]:
                style_tendencies["prefer"].append(kw)

    # 从 site_photo 的 style_tendency 中也汇总
    for _ref in constraint_sources:
        # 如果提取结果中有 style_tendency
        pass  # 已在 constraints 中，此处后续可扩展

    # 获取空间区域列表（用于信封格式化）
    extracted_zones = state.get("extracted_spatial_zones") or [{"id": "overall", "label": "整体", "source": "preset"}]

    # 组装约束信封
    constraint_envelope = _build_constraint_envelope(
        constraints_by_zone, extracted_zones, style_tendencies if any(style_tendencies.values()) else None
    )

    visual_constraints = {
        "constraints_by_zone": constraints_by_zone,
        "spatial_topologies": spatial_topologies,
        "existing_conditions": existing_conditions,
        "style_tendencies": style_tendencies,
        "constraint_envelope": constraint_envelope,
    }

    total_constraints = sum(len(v) for v in constraints_by_zone.values())
    logger.info(
        f"🎯 [v12.0] 约束管线完成: {total_constraints} 条约束, "
        f"{len(spatial_topologies)} 个拓扑, {len(existing_conditions)} 个现状条件"
    )

    return visual_constraints


# ==================================================================================
# 配置加载
# ==================================================================================

_CONFIG_CACHE: Dict | None = None


