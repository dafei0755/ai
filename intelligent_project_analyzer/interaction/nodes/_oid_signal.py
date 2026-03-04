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


def _load_config() -> Dict:
    """加载 output_projections.yaml 中的意图检测配置"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    cfg_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config",
        "output_projections.yaml",
    )
    try:
        with open(cfg_path, encoding="utf-8") as f:
            _CONFIG_CACHE = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"[输出意图] 加载 output_projections.yaml 失败: {e}")
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE


# ==================================================================================
# 交付类型检测：四源交叉算法
# ==================================================================================

ALL_PROJECTION_IDS = [
    "design_professional",
    "investor_operator",
    "government_policy",
    "construction_execution",
    "aesthetic_critique",
]

# 交付类型中文展示（按系统能力边界定义，而非受众分类）
PROJECTION_DISPLAY = {
    "design_professional": {"label": "空间策略报告", "desc": "含概念框架、功能策略、材料选配方向"},
    "investor_operator": {"label": "商业运营分析", "desc": "含业态模型、市场定位、运营架构建议"},
    "government_policy": {"label": "在地文化研究", "desc": "含地域文脉梳理、社区价值、人文影响分析"},
    "construction_execution": {"label": "落地实施指南", "desc": "含材料策略、工艺建议、实施优先级排序"},
    "aesthetic_critique": {"label": "叙事创意方案", "desc": "含空间命名、品牌故事、文化叙事表达"},
}


def _detect_explicit_signals(user_input: str) -> Dict[str, float]:
    """源1: 从用户原文中检测显式交付类型信号"""
    signals: Dict[str, float] = {}

    # 显式关键词 → 投射类型（高权重 1.0）
    explicit_rules = {
        "design_professional": [
            r"设计方案|整体规划|概念框架|设计报告|空间策略|建筑语言|材料策略|室内设计|选材方向",
        ],
        "investor_operator": [
            r"运营模型|商业模[型式]|投资[回报分析]|收入结构|盈利|投资方案|招商|股权|融资|业态",
        ],
        "government_policy": [
            r"在地文化|文脉[梳理研究]|地域[特色根性]|社区[价值贡献]|乡土|乡村[振兴文化]|历史[文化街区]",
        ],
        "construction_execution": [
            r"落地[实施方案]|材料[策略选型]|工艺[建议方向]|实施[路径优先级]|可建性|技术[可行性路径]",
        ],
        "aesthetic_critique": [
            r"命名[方案创意]|品牌[故事叙事]|空间[叙事故事]|文案[创作策划]|文化[表达叙事]|美学[表达文字]",
        ],
    }

    for pid, patterns in explicit_rules.items():
        for pattern in patterns:
            if re.search(pattern, user_input):
                signals[pid] = max(signals.get(pid, 0), 1.0)
                break

    # 弱信号（0.2-0.4）
    weak_rules = {
        "investor_operator": (r"商业成功|投资回报|运营收益|运营主体|租金回报", 0.55),
        "government_policy": (r"示范[意义项目]|文化示范|乡村振兴|公共", 0.2),
        "aesthetic_critique": (r"文化深度|大师|安藤|隈研吾|王澍|刘家琨|谢柯", 0.3),
        "construction_execution": (r"落地|建设|建造|施工", 0.2),
    }
    for pid, (pattern, weight) in weak_rules.items():
        if pid not in signals and re.search(pattern, user_input):
            signals[pid] = weight

    return signals


def _detect_stakeholder_signals(structured_requirements: Dict) -> Dict[str, float]:
    """源2: 从 stakeholder_system 检测角色证据"""
    signals: Dict[str, float] = {}

    stakeholder_system = structured_requirements.get("stakeholder_system")
    if not stakeholder_system:
        return signals

    identified = []
    if isinstance(stakeholder_system, dict):
        identified = stakeholder_system.get("identified_stakeholders", [])
    elif isinstance(stakeholder_system, list):
        identified = stakeholder_system

    # stakeholder role → projection mapping
    config = _load_config()
    role_mapping = config.get("stakeholder_projection_mapping", {})

    power_weights = {"high": 0.8, "medium": 0.6, "low": 0.3, "indirect": 0.1}

    for sh in identified:
        if not isinstance(sh, dict):
            continue
        role = sh.get("role", "")
        power = sh.get("decision_power", "medium")
        weight = power_weights.get(power, 0.3)

        # 匹配角色到投射
        for _mapping_key, mapping_val in role_mapping.items():
            if not isinstance(mapping_val, dict):
                continue
            maps_to = mapping_val.get("maps_to")
            if not maps_to:
                continue
            keywords = mapping_val.get("role_keywords", [])
            for kw in keywords:
                if kw in role:
                    signals[maps_to] = max(signals.get(maps_to, 0), weight)
                    break

    return signals


def _detect_spatial_attribute_signals(
    detected_modes: List[Dict], project_classification: Dict | None
) -> Tuple[List[str], List[str]]:
    """源3: 从 mode + project_type 检测空间属性必然/可能利益方"""
    mandatory: List[str] = []
    likely: List[str] = []

    config = _load_config()
    rules = config.get("spatial_attribute_rules", {})

    mode_ids = set()
    for m in detected_modes or []:
        mid = m.get("mode", "") if isinstance(m, dict) else str(m)
        mode_ids.add(mid)

    project_type = ""
    if project_classification:
        project_type = project_classification.get("project_type", "")

    for _rule_name, rule in rules.items():
        if not isinstance(rule, dict):
            continue
        trigger = rule.get("trigger", {})
        trigger_modes = set(trigger.get("modes", []))
        trigger_types = set(trigger.get("project_types", []))

        # 检查是否匹配
        mode_match = bool(mode_ids & trigger_modes)
        type_match = any(pt in project_type for pt in trigger_types) if trigger_types else False

        if mode_match or type_match:
            for sh in rule.get("mandatory_stakeholders", []):
                # 通过 stakeholder → projection 映射
                pid = _stakeholder_to_projection(sh)
                if pid and pid not in mandatory:
                    mandatory.append(pid)
            for sh in rule.get("likely_stakeholders", []):
                pid = _stakeholder_to_projection(sh)
                if pid and pid not in likely:
                    likely.append(pid)

    return mandatory, likely


def _stakeholder_to_projection(stakeholder_key: str) -> str | None:
    """将 stakeholder 键名映射到 projection ID"""
    config = _load_config()
    mapping = config.get("stakeholder_projection_mapping", {})
    entry = mapping.get(stakeholder_key, {})
    if isinstance(entry, dict):
        return entry.get("maps_to")
    return None


def _detect_motivation_signals(structured_requirements: Dict, user_input: str) -> Dict[str, float]:
    """源4: 从动机/情感/身份数据检测投射倾向"""
    signals: Dict[str, float] = {}
    config = _load_config()
    mot_mapping = config.get("motivation_projection_mapping", {})

    # 4a: 12种动机类型
    motivation_types = structured_requirements.get("motivation_types", {})
    if isinstance(motivation_types, dict):
        primary = motivation_types.get("primary", "")
        secondaries = motivation_types.get("secondary", [])
        if isinstance(secondaries, str):
            secondaries = [secondaries]

        for mot_key, mot_rule in mot_mapping.items():
            if not isinstance(mot_rule, dict) or mot_key in (
                "five_whys_signals",
                "brand_dna_signals",
                "competitor_signals",
                "symbolic_identity_signals",
            ):
                continue
            if primary == mot_key:
                pid = mot_rule.get("primary_projection")
                w = mot_rule.get("signal_weight", 0.3)
                if pid:
                    signals[pid] = signals.get(pid, 0) + w
                sec = mot_rule.get("secondary_projection")
                if sec:
                    signals[sec] = signals.get(sec, 0) + w * 0.3
            for s in secondaries:
                if s == mot_key:
                    pid = mot_rule.get("primary_projection")
                    w = mot_rule.get("signal_weight", 0.3)
                    if pid:
                        signals[pid] = signals.get(pid, 0) + w * 0.5

    # 4b: 五层追问深层信号
    five_whys = structured_requirements.get("five_whys_analysis", {})
    fws_config = mot_mapping.get("five_whys_signals", {})
    if isinstance(five_whys, dict) and fws_config:
        all_l4_text = ""
        all_l5_text = ""
        for _chain_key, chain_val in five_whys.items():
            if isinstance(chain_val, dict):
                all_l4_text += " " + str(chain_val.get("L4_why_emotion", ""))
                all_l5_text += " " + str(chain_val.get("L5_why_identity", ""))

        for rule in fws_config.get("L4_emotion_keywords", []):
            if isinstance(rule, dict):
                patterns = rule.get("pattern", [])
                maps_to = rule.get("maps_to")
                if maps_to and any(p in all_l4_text for p in patterns):
                    signals[maps_to] = signals.get(maps_to, 0) + 0.3

        for rule in fws_config.get("L5_identity_keywords", []):
            if isinstance(rule, dict):
                patterns = rule.get("pattern", [])
                maps_to = rule.get("maps_to")
                if maps_to and any(p in all_l5_text for p in patterns):
                    signals[maps_to] = signals.get(maps_to, 0) + 0.3

    # 4c: 品牌 DNA
    brand_dna = structured_requirements.get("brand_dna")
    brand_cfg = mot_mapping.get("brand_dna_signals", {})
    if brand_dna and isinstance(brand_cfg, dict) and brand_cfg.get("has_brand_dna"):
        pid = brand_cfg.get("maps_to")
        sec = brand_cfg.get("secondary")
        w = brand_cfg.get("signal_weight", 0.3)
        if pid:
            signals[pid] = signals.get(pid, 0) + w
        if sec:
            signals[sec] = signals.get(sec, 0) + w * 0.5

    # 4d: 竞争思想实验
    thought_experiments = structured_requirements.get("thought_experiments", {})
    comp_cfg = mot_mapping.get("competitor_signals", {})
    if isinstance(thought_experiments, dict) and thought_experiments.get("competitor_first"):
        if isinstance(comp_cfg, dict) and comp_cfg.get("has_competitor_analysis"):
            pid = comp_cfg.get("maps_to")
            w = comp_cfg.get("signal_weight", 0.5)
            if pid:
                signals[pid] = signals.get(pid, 0) + w

    # 4e: 符号身份信号
    char_narrative = structured_requirements.get("character_narrative", {})
    symbolic_id = ""
    if isinstance(char_narrative, dict):
        symbolic_id = str(char_narrative.get("symbolic_identity", ""))
    sym_rules = mot_mapping.get("symbolic_identity_signals", [])
    if isinstance(sym_rules, list):
        for rule in sym_rules:
            if isinstance(rule, dict):
                patterns = rule.get("pattern", [])
                maps_to = rule.get("maps_to")
                if maps_to and any(p in symbolic_id for p in patterns):
                    signals[maps_to] = signals.get(maps_to, 0) + 0.3

    # 动机分封顶 0.8
    return {k: min(v, 0.8) for k, v in signals.items()}


