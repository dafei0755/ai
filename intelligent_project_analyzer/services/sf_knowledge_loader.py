"""
sf/ 知识文件运行时加载器 (P2-T8)

功能：
- 加载 sf/ 目录下的知识文件（10_Mode_Engine, 12_Ability_Core, 13_Evaluation_Matrix, 14_Output_Standards）
- 解析机器可读的 YAML-like 段落（如 mode_evaluation_weights）
- 提供按模式/维度提取知识片段的接口
- 使用 lru_cache 缓存，避免重复磁盘 I/O
- v9.0: 框架感知知识注入 — 支持 analysis_frameworks.yaml / layer_models.yaml / ability_core_essentials.yaml

版本：v9.000 (Framework-Aware Knowledge Injection)
"""

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# sf/ 目录路径
SF_DIR = Path(__file__).parent.parent.parent / "sf"

# 配置目录路径
CONFIG_DIR = Path(__file__).parent.parent / "config"

# 知识文件名映射
SF_FILES = {
    "10_Mode_Engine": "10_Mode_Engine",
    "12_Ability_Core": "12_Ability_Core",
    "13_Evaluation_Matrix": "13_Evaluation_Matrix",
    "14_Output_Standards": "14_Output_Standards",
}


# ============================================================
# 1. 基础加载（带缓存）
# ============================================================


@lru_cache(maxsize=8)
def _load_sf_file(filename: str) -> str:
    """加载单个 sf/ 文件内容（缓存）"""
    filepath = SF_DIR / filename
    if not filepath.exists():
        logger.warning(f"[sf_knowledge] 文件不存在: {filepath}")
        return ""
    try:
        content = filepath.read_text(encoding="utf-8")
        logger.info(f"[sf_knowledge] 已加载 {filename} ({len(content)} chars)")
        return content
    except Exception as e:
        logger.error(f"[sf_knowledge] 读取 {filename} 失败: {e}")
        return ""


def load_evaluation_matrix() -> str:
    """加载 13_Evaluation_Matrix 全文"""
    return _load_sf_file("13_Evaluation_Matrix")


def load_output_standards() -> str:
    """加载 14_Output_Standards 全文"""
    return _load_sf_file("14_Output_Standards")


def load_mode_engine() -> str:
    """加载 10_Mode_Engine 全文"""
    return _load_sf_file("10_Mode_Engine")


def load_ability_core() -> str:
    """加载 12_Ability_Core 全文"""
    return _load_sf_file("12_Ability_Core")


# ============================================================
# 1b. CASE 示范文件加载（v9.1: 多维投射模板支持）
# ============================================================


@lru_cache(maxsize=16)
def _load_case_file(filepath_relative: str) -> str:
    """加载单个 CASE 示范文件（缓存）"""
    # 支持 sf/ 前缀或直接文件名
    if filepath_relative.startswith("sf/"):
        filepath = SF_DIR.parent / filepath_relative
    else:
        filepath = SF_DIR / filepath_relative
    if not filepath.exists():
        logger.warning(f"[sf_knowledge] CASE文件不存在: {filepath}")
        return ""
    try:
        content = filepath.read_text(encoding="utf-8")
        logger.info(f"[sf_knowledge] 已加载 CASE: {filepath.name} ({len(content)} chars)")
        return content
    except Exception as e:
        logger.error(f"[sf_knowledge] 读取 CASE 文件失败: {e}")
        return ""


def load_case_examples(framework_id: str) -> List[Dict[str, str]]:
    """
    从 analysis_frameworks.yaml 加载指定框架的 CASE 示范文件

    v9.1: 接通 case_examples 消费管线 — 将声明式配置转为可用的 few-shot 模板

    Args:
        framework_id: 框架ID（如 "ability_core"）

    Returns:
        [{"filename": "CASE_狮岭村_...", "content": "...全文..."}, ...]
    """
    fw_config = get_framework_config(framework_id)
    if not fw_config:
        return []

    case_paths = fw_config.get("case_examples", [])
    if not case_paths:
        return []

    results = []
    for path in case_paths:
        content = _load_case_file(path)
        if content:
            filename = Path(path).stem
            results.append({"filename": filename, "content": content})

    logger.info(f"[sf_knowledge] 框架 {framework_id} 加载了 {len(results)} 个 CASE 示范")
    return results


def load_perspective_case_templates() -> Dict[str, str]:
    """
    加载多维投射示范模板（v9.1: 输出投射层基础设施）

    扫描 sf/ 目录下的 CASE 变体文件，按投射视角分类：
    - 基础版（无后缀）→ "ability_core_full"
    - " - 2" → "industry_strategy"（产业穿透+治理）
    - " - 3" → "construction_detail"（施工级深化）
    - " - 4" → "policy_report"（政策汇报）
    - " - 5" → "aesthetic_critique"（美学锋化）

    Returns:
        {"perspective_id": "CASE全文", ...}
    """
    perspective_map = {
        "ability_core_full": [],
        "industry_strategy": [" - 2"],
        "construction_detail": [" - 3"],
        "policy_report": [" - 4"],
        "aesthetic_critique": [" - 5"],
    }

    results = {}
    for perspective_id, suffixes in perspective_map.items():
        for case_file in SF_DIR.glob("CASE_*"):
            if not case_file.is_file():
                continue
            stem = case_file.stem
            if not suffixes:
                # 基础版：匹配不含 " - N" 后缀的文件
                if " - " not in stem:
                    content = _load_case_file(case_file.name)
                    if content:
                        results[perspective_id] = content
                        break
            else:
                for suffix in suffixes:
                    if stem.endswith(suffix):
                        content = _load_case_file(case_file.name)
                        if content:
                            results[perspective_id] = content
                            break

    logger.info(f"[sf_knowledge] 加载了 {len(results)} 个投射视角模板: {list(results.keys())}")
    return results


# ============================================================
# 2. 结构化解析
# ============================================================


@lru_cache(maxsize=1)
def get_mode_evaluation_weights() -> Dict[str, Dict[str, float]]:
    """
    解析 13_Evaluation_Matrix 中的 mode_evaluation_weights YAML 段落

    Returns:
        {
            "M1_concept_driven": {"concept_integrity": 0.40, ...},
            "M2_functional_efficiency": {...},
            ...
        }
    """
    content = load_evaluation_matrix()
    if not content:
        return {}

    # 提取 mode_evaluation_weights: 开始到文件结尾的 YAML 块
    match = re.search(r"mode_evaluation_weights:\s*\n(.*)", content, re.DOTALL)
    if not match:
        logger.warning("[sf_knowledge] 未找到 mode_evaluation_weights 段落")
        return {}

    yaml_block = "mode_evaluation_weights:\n" + match.group(1)
    try:
        parsed = yaml.safe_load(yaml_block)
        weights = parsed.get("mode_evaluation_weights", {})
        logger.info(f"[sf_knowledge] 解析到 {len(weights)} 个模式的评估权重")
        return weights
    except Exception as e:
        logger.error(f"[sf_knowledge] 解析 mode_evaluation_weights 失败: {e}")
        return {}


@lru_cache(maxsize=1)
def get_mode_deliverable_mapping() -> Dict[str, Dict[str, Any]]:
    """
    解析 14_Output_Standards 中的模式-交付物映射

    Returns:
        {
            "M1_concept_driven": {
                "核心交付物": [...],
                "辅助交付物": [...],
                "禁止交付物": [...]
            },
            ...
        }
    """
    content = load_output_standards()
    if not content:
        return {}

    result = {}
    # 用正则匹配每个模式块：M{n}_{name}: 后跟缩进内容
    pattern = r"(M\d+_\w+):\s*\n((?:  .+\n)+)"
    for m in re.finditer(pattern, content):
        mode_id = m.group(1)
        block = m.group(2)

        mapping: Dict[str, list] = {}
        current_key = None

        for line in block.split("\n"):
            line = line.rstrip()
            if not line.strip():
                continue
            # 检测子标题行（如 "  核心交付物:"）
            key_match = re.match(r"  (\S.*?):", line)
            if key_match:
                current_key = key_match.group(1).strip()
                mapping[current_key] = []
            elif current_key and line.strip().startswith("- "):
                item = line.strip()[2:].strip()
                mapping[current_key].append(item)

        if mapping:
            result[mode_id] = mapping

    logger.info(f"[sf_knowledge] 解析到 {len(result)} 个模式的交付物映射")
    return result


@lru_cache(maxsize=1)
def get_quality_floor_checklist() -> str:
    """
    提取 14_Output_Standards 中的质量底线清单 (Q1-Q5) 文本

    Returns:
        质量底线清单的原始文本
    """
    content = load_output_standards()
    if not content:
        return ""

    # 提取 "四、质量底线清单" 到 "五、" 之间的内容
    match = re.search(r"(四、质量底线清单.*?)(?=五、|$)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


# ============================================================
# 3. 按模式提取知识片段
# ============================================================


def get_evaluation_criteria_for_modes(detected_modes: List[Dict[str, Any]]) -> str:
    """
    根据检测到的设计模式，提取对应的评估维度权重和重点维度

    Args:
        detected_modes: [{"mode": "M5_rural_context", "confidence": 0.85}, ...]

    Returns:
        可直接注入 prompt 的评估标准文本
    """
    if not detected_modes:
        return ""

    weights = get_mode_evaluation_weights()
    if not weights:
        return ""

    # 维度中文名映射
    dim_names = {
        "concept_integrity": "概念完整度",
        "spatial_logic": "空间逻辑",
        "narrative_coherence": "叙事连贯度",
        "material_fitness": "材料适配",
        "functional_efficiency": "功能效率",
        "technical_feasibility": "技术可行",
        "commercial_closure": "商业闭环",
        "cultural_authenticity": "文化在地",
        "social_impact": "社会影响",
        "interdisciplinary_integration": "跨学科整合",
    }

    sections = []
    for mode_info in detected_modes:
        mode_id = mode_info.get("mode", "")
        confidence = mode_info.get("confidence", 0.0)

        if mode_id not in weights:
            continue

        mode_weights = weights[mode_id]
        # 按权重降序排列
        sorted_dims = sorted(mode_weights.items(), key=lambda x: x[1], reverse=True)

        # 构建文本
        mode_id.replace("_", " ").title()
        lines = [f"模式 {mode_id}（置信度 {confidence:.0%}）评估维度权重："]
        for dim_key, weight in sorted_dims:
            dim_cn = dim_names.get(dim_key, dim_key)
            bar = "█" * int(weight * 20)
            lines.append(f"  - {dim_cn}（{dim_key}）: {weight:.0%} {bar}")

        # 标注重点维度（权重 >= 20%）
        focus_dims = [dim_names.get(k, k) for k, v in sorted_dims if v >= 0.20]
        if focus_dims:
            lines.append(f"  重点评估维度: {', '.join(focus_dims)}")

        sections.append("\n".join(lines))

    if not sections:
        return ""

    return (
        "\n\n# 评估标准参考（基于 13 Evaluation Matrix）\n\n" + "\n\n".join(sections) + "\n\n注意：技术可行评估永远不低于 10%，概念完整度评估永远不低于 10%。"
    )


def get_output_standards_for_modes(detected_modes: List[Dict[str, Any]]) -> str:
    """
    根据检测到的设计模式，提取对应的输出标准（交付物要求 + 质量底线）

    Args:
        detected_modes: [{"mode": "M5_rural_context", "confidence": 0.85}, ...]

    Returns:
        可直接注入 prompt 的输出标准文本
    """
    if not detected_modes:
        return ""

    mapping = get_mode_deliverable_mapping()
    quality_floor = get_quality_floor_checklist()

    sections = []
    for mode_info in detected_modes:
        mode_id = mode_info.get("mode", "")
        if mode_id not in mapping:
            continue

        mode_map = mapping[mode_id]
        lines = [f"模式 {mode_id} 交付物要求："]

        for category, items in mode_map.items():
            if items:
                lines.append(f"  [{category}]")
                for item in items:
                    lines.append(f"    - {item}")

        sections.append("\n".join(lines))

    if not sections and not quality_floor:
        return ""

    result = ""
    if sections:
        result += "\n\n# 输出标准参考（基于 14 Output Standards）\n\n" + "\n\n".join(sections)

    if quality_floor:
        # 提取精简版质量底线（Q1-Q5标题+核心要求）
        result += "\n\n# 质量底线（Q1-Q5）\n"
        result += _extract_quality_floor_summary(quality_floor)

    return result


def _extract_quality_floor_summary(full_text: str) -> str:
    """从质量底线全文中提取精简摘要"""
    summary_lines = []
    for line in full_text.split("\n"):
        stripped = line.strip()
        # 提取 Q 编号行和违反后果行
        if stripped.startswith("Q") and "｜" in stripped:
            summary_lines.append(f"- {stripped}")
        elif stripped.startswith("违反后果"):
            summary_lines.append(f"  {stripped}")
    return "\n".join(summary_lines) if summary_lines else full_text[:500]


def get_full_knowledge_injection(detected_modes: List[Dict[str, Any]]) -> str:
    """
    获取完整的知识注入文本（评估标准 + 输出标准），用于注入专家/审核 prompt

    Args:
        detected_modes: [{"mode": "M5_rural_context", "confidence": 0.85}, ...]

    Returns:
        完整的知识注入文本
    """
    if not detected_modes:
        return ""

    eval_section = get_evaluation_criteria_for_modes(detected_modes)
    output_section = get_output_standards_for_modes(detected_modes)

    combined = ""
    if eval_section:
        combined += eval_section
    if output_section:
        combined += "\n" + output_section

    if combined:
        logger.info(f"[sf_knowledge] 生成知识注入文本 ({len(combined)} chars) " f"覆盖 {len(detected_modes)} 个模式")

    return combined


# ============================================================
# 3b. 框架注册表 & 层模型加载 (v9.0)
# ============================================================


@lru_cache(maxsize=1)
def load_analysis_frameworks() -> Dict[str, Any]:
    """
    加载 analysis_frameworks.yaml 框架注册表

    Returns:
        完整的框架注册表 dict
    """
    filepath = CONFIG_DIR / "analysis_frameworks.yaml"
    if not filepath.exists():
        logger.warning(f"[sf_knowledge] 框架注册表不存在: {filepath}")
        return {}
    try:
        data = yaml.safe_load(filepath.read_text(encoding="utf-8"))
        frameworks = data.get("frameworks", {})
        logger.info(f"[sf_knowledge] 已加载 {len(frameworks)} 个分析框架定义")
        return data
    except Exception as e:
        logger.error(f"[sf_knowledge] 加载框架注册表失败: {e}")
        return {}


@lru_cache(maxsize=1)
def load_layer_models() -> Dict[str, Any]:
    """
    加载 layer_models.yaml 层结构模型

    Returns:
        完整的层模型 dict
    """
    filepath = CONFIG_DIR / "layer_models.yaml"
    if not filepath.exists():
        logger.warning(f"[sf_knowledge] 层模型文件不存在: {filepath}")
        return {}
    try:
        data = yaml.safe_load(filepath.read_text(encoding="utf-8"))
        models = data.get("layer_models", {})
        logger.info(f"[sf_knowledge] 已加载 {len(models)} 个层结构模型")
        return data
    except Exception as e:
        logger.error(f"[sf_knowledge] 加载层模型失败: {e}")
        return {}


@lru_cache(maxsize=1)
def load_ability_core_essentials() -> Dict[str, Any]:
    """
    加载 ability_core_essentials.yaml（12个能力的精华）

    Returns:
        {
            "A1_concept_architecture": {
                "name": "概念建构能力",
                "essence": "...",
                "maturity_L4": "...",
                "highest_form": "...",
                "judgment_criteria": [...],
                "common_mistakes": [...]
            },
            ...
        }
    """
    filepath = CONFIG_DIR / "ability_core_essentials.yaml"
    if not filepath.exists():
        logger.warning(f"[sf_knowledge] ability_core_essentials 不存在: {filepath}")
        return {}
    try:
        data = yaml.safe_load(filepath.read_text(encoding="utf-8"))
        # 过滤掉非能力键（如注释块）
        abilities = {k: v for k, v in data.items() if k.startswith("A") and isinstance(v, dict)}
        logger.info(f"[sf_knowledge] 已加载 {len(abilities)} 个能力精华定义")
        return abilities
    except Exception as e:
        logger.error(f"[sf_knowledge] 加载 ability_core_essentials 失败: {e}")
        return {}


def get_framework_config(framework_id: str) -> Optional[Dict[str, Any]]:
    """
    获取指定框架的完整配置（从 analysis_frameworks.yaml）

    Args:
        framework_id: 框架ID（如 "ability_core"、"multi_scale_integration"）

    Returns:
        框架配置 dict，如不存在则返回 None
    """
    registry = load_analysis_frameworks()
    frameworks = registry.get("frameworks", {})
    return frameworks.get(framework_id)


def get_layer_model(model_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定层结构模型的完整配置

    Args:
        model_name: 层模型名称（如 "ability_core_5layer"）

    Returns:
        层模型配置 dict，如不存在则返回 None
    """
    all_models = load_layer_models()
    models = all_models.get("layer_models", {})
    return models.get(model_name)


def get_ability_injection(ability_tag: str) -> str:
    """
    获取单个能力维度的知识注入文本（用于专家 prompt）

    包含：
    - 能力本质 (essence)
    - L4 成熟度描述
    - 最高形态
    - 判断标准（前2条）
    - 常见误区（前2条）

    Args:
        ability_tag: 能力ID（如 "A1_concept_architecture"）

    Returns:
        注入文本字符串
    """
    essentials = load_ability_core_essentials()
    ability = essentials.get(ability_tag)
    if not ability:
        logger.warning(f"[sf_knowledge] 能力 {ability_tag} 不在 essentials 中")
        return ""

    name = ability.get("name", ability_tag)
    essence = ability.get("essence", "")
    maturity_l4 = ability.get("maturity_L4", "")
    highest_form = ability.get("highest_form", "")
    criteria = ability.get("judgment_criteria", [])
    mistakes = ability.get("common_mistakes", [])

    lines = [
        f"### 能力维度: {ability_tag}（{name}）",
        f"本质: {essence}",
        f"L4 成熟度标准: {maturity_l4}",
        f"最高形态: {highest_form}",
    ]

    if criteria:
        lines.append("判断标准:")
        for c in criteria[:3]:
            lines.append(f"  ✓ {c}")

    if mistakes:
        lines.append("常见误区:")
        for m in mistakes[:3]:
            lines.append(f"  ✗ {m}")

    return "\n".join(lines)


def get_layer_writing_instructions(framework_id: str) -> str:
    """
    获取框架对应的层写作指令文本（用于专家 prompt 或 result_aggregator）

    Args:
        framework_id: 框架ID（如 "ability_core"）

    Returns:
        层写作指令文本
    """
    fw_config = get_framework_config(framework_id)
    if not fw_config:
        return ""

    layer_model_name = fw_config.get("layer_model", "")
    if not layer_model_name:
        return ""

    layer_model = get_layer_model(layer_model_name)
    if not layer_model:
        return ""

    layers = layer_model.get("layers", [])
    if not layers:
        return ""

    lines = [f"## 分析层结构: {layer_model.get('name', layer_model_name)}"]
    lines.append(f"说明: {layer_model.get('description', '')}")
    lines.append("")

    for layer in layers:
        layer.get("id", "")
        lname = layer.get("name", "")
        instruction = layer.get("instruction", "").strip()
        quality_floor = layer.get("quality_floor", "")
        max_words = layer.get("max_words", "")

        lines.append(f"### {lname}")
        lines.append(f"写作指令: {instruction}")
        if quality_floor:
            lines.append(f"质量底线: {quality_floor}")
        if max_words:
            lines.append(f"字数上限: {max_words}字")
        lines.append("")

    return "\n".join(lines)


def get_activated_abilities_for_mode(mode_id: str) -> List[str]:
    """
    根据模式ID获取激活的能力列表（从 mode_ability_activation.yaml）

    Args:
        mode_id: 模式ID（如 "M5"、"M5_rural_context"）

    Returns:
        能力ID列表（如 ["A1_concept_architecture", "A5_lighting_architecture", ...]）
    """
    # 规范化 mode_id（只取 M 数字部分）
    m_match = re.match(r"(M\d+)", mode_id)
    if not m_match:
        return []
    m_key = m_match.group(1)

    activation_path = CONFIG_DIR / "mode_ability_activation.yaml"
    if not activation_path.exists():
        return []

    try:
        data = yaml.safe_load(activation_path.read_text(encoding="utf-8"))
        modes = data.get("modes", {})
        mode_entry = modes.get(m_key, {})
        if not mode_entry:
            return []

        abilities = []
        for ab in mode_entry.get("primary_abilities", []):
            ab_id = ab.get("id", "") if isinstance(ab, dict) else str(ab)
            if ab_id:
                abilities.append(ab_id)
        for ab in mode_entry.get("secondary_abilities", []):
            ab_id = ab.get("id", "") if isinstance(ab, dict) else str(ab)
            if ab_id:
                abilities.append(ab_id)

        return abilities
    except Exception as e:
        logger.warning(f"[sf_knowledge] 加载 mode_ability_activation 失败: {e}")
        return []


def get_framework_knowledge_injection(
    framework_id: str,
    ability_tags: Optional[List[str]] = None,
    detected_modes: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    获取框架感知的完整知识注入文本

    这是新的入口函数，统一了：
    1. 框架层写作指令（来自 layer_models.yaml）
    2. 能力维度精华注入（来自 ability_core_essentials.yaml）
    3. 评估标准 + 输出标准（来自 sf/13 + sf/14）

    Args:
        framework_id: 框架ID（如 "ability_core"）
        ability_tags: 当前任务关联的能力标签列表（可选）
        detected_modes: 检测到的设计模式列表（可选）

    Returns:
        完整的知识注入文本
    """
    sections = []

    # (1) 框架层写作指令
    layer_instructions = get_layer_writing_instructions(framework_id)
    if layer_instructions:
        sections.append(layer_instructions)

    # (2) 能力维度精华注入（仅当有 ability_tags 时）
    if ability_tags:
        ability_sections = []
        for tag in ability_tags:
            injection = get_ability_injection(tag)
            if injection:
                ability_sections.append(injection)
        if ability_sections:
            sections.append("## 当前任务关联能力维度\n\n" + "\n\n".join(ability_sections))

    # (3) 经典的评估标准 + 输出标准（sf/13 + sf/14）
    if detected_modes:
        classic_injection = get_full_knowledge_injection(detected_modes)
        if classic_injection:
            sections.append(classic_injection)

    if not sections:
        return ""

    combined = "\n\n---\n\n".join(sections)
    logger.info(
        f"[sf_knowledge] 框架知识注入 ({framework_id}) 生成 {len(combined)} chars, "
        f"ability_tags={ability_tags}, modes={len(detected_modes or [])}"
    )
    return combined


# ============================================================
# 4. 缓存管理
# ============================================================


def clear_sf_knowledge_cache():
    """清除所有 sf/ 知识缓存（用于测试或热重载）"""
    _load_sf_file.cache_clear()
    _load_case_file.cache_clear()
    get_mode_evaluation_weights.cache_clear()
    get_mode_deliverable_mapping.cache_clear()
    get_quality_floor_checklist.cache_clear()
    load_analysis_frameworks.cache_clear()
    load_layer_models.cache_clear()
    load_ability_core_essentials.cache_clear()
    logger.info("[sf_knowledge] 已清除所有知识缓存")
