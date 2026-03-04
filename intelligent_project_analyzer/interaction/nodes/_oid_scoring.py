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


def _score_delivery_types(
    explicit: Dict[str, float],
    stakeholder: Dict[str, float],
    mandatory: List[str],
    likely: List[str],
    motivation: Dict[str, float],
) -> List[Dict[str, Any]]:
    """四源交叉评分，输出每个投射的分数、状态和证据链"""
    results = []

    for pid in ALL_PROJECTION_IDS:
        score = 0.0
        evidence: List[str] = []

        # 源1: 显式信号
        if pid in explicit:
            score += explicit[pid]
            if explicit[pid] >= 1.0:
                evidence.append("用户原文明确提及")
            else:
                evidence.append(f"用户原文弱信号(+{explicit[pid]:.1f})")

        # 源2: 利益相关方
        if pid in stakeholder:
            score += stakeholder[pid]
            evidence.append(f"利益相关方角色匹配(+{stakeholder[pid]:.1f})")

        # 源3: 空间属性
        if pid in mandatory:
            score += 0.7
            evidence.append("空间属性必然要求(+0.7)")
        elif pid in likely:
            score += 0.3
            evidence.append("空间属性可能涉及(+0.3)")

        # 源4: 动机
        if pid in motivation:
            score += motivation[pid]
            evidence.append(f"动机/情感/身份信号(+{motivation[pid]:.2f})")

        # design_professional 保底
        if pid == "design_professional":
            score = max(score, 1.0)
            if not evidence:
                evidence.append("默认必选")

        # 分类
        if score >= 1.0:
            status = "confirmed"
        elif score >= 0.3:
            status = "candidate"
        else:
            status = "excluded"

        results.append(
            {
                "id": pid,
                "label": PROJECTION_DISPLAY.get(pid, {}).get("label", pid),
                "desc": PROJECTION_DISPLAY.get(pid, {}).get("desc", ""),
                "score": round(score, 2),
                "status": status,
                "evidence": evidence,
            }
        )

    return results


# ==================================================================================
# 身份模式检测
# ==================================================================================

# 通用身份模式（跨项目类型）
UNIVERSAL_IDENTITY_MODES = [
    {
        "id": "as_family_intimate",
        "label": "作为家人（亲密关系）",
        "spatial_need": "放松、无防御、情感连接",
        "trigger_scenes": ["起居", "餐厅", "亲子", "家庭聚会"],
    },
    {
        "id": "as_professional",
        "label": "作为职业人（工作身份）",
        "spatial_need": "效率、专注、权威感、信息密度",
        "trigger_scenes": ["书房", "会议", "远程办公", "接待"],
    },
    {
        "id": "as_social_host",
        "label": "作为社交主人（待客身份）",
        "spatial_need": "展示、控场、慷慨表达、得体退场",
        "trigger_scenes": ["客厅", "餐厅", "酒吧", "花园"],
    },
    {
        "id": "as_business_partner",
        "label": "作为生意人（商务身份）",
        "spatial_need": "信任构建、权力暗示、谈判氛围、隐私",
        "trigger_scenes": ["茶室", "私宴", "雪茄间", "会客"],
    },
    {
        "id": "as_solitary_self",
        "label": "作为独处者（自我身份）",
        "spatial_need": "屏蔽干扰、内省、仪式感、自我犒赏",
        "trigger_scenes": ["浴室", "阅读角", "冥想", "阳台"],
    },
    {
        "id": "as_caregiver",
        "label": "作为照护者（责任身份）",
        "spatial_need": "监护视线、应急可达、安全冗余",
        "trigger_scenes": ["老人房", "儿童区", "无障碍"],
    },
    {
        "id": "as_learner_creator",
        "label": "作为学习者/创造者",
        "spatial_need": "灵感刺激、工具可达、专注-发散切换",
        "trigger_scenes": ["工作室", "画室", "手作间"],
    },
]

# 项目类型专属身份模式
PROJECT_SPECIFIC_IDENTITY_MODES = {
    "rural_village": {
        "trigger_modes": ["M5", "M5_rural_context"],
        "trigger_type_keywords": ["rural", "village", "乡村", "农村", "民宿", "乡建"],
        "modes": [
            {
                "id": "as_rooted_villager",
                "label": "作为在地村民（日常身份）",
                "spatial_need": "生计不受干扰、公共空间可达、被尊重",
                "trigger_scenes": ["晒场", "集市", "祠堂", "村口"],
            },
            {
                "id": "as_returning_child",
                "label": "作为归乡游子（记忆身份）",
                "spatial_need": "乡愁锚点、现代生活标准、身份弥合",
                "trigger_scenes": ["老宅", "村口", "记忆场所"],
            },
            {
                "id": "as_cultural_witness",
                "label": "作为文化见证者（游客身份）",
                "spatial_need": "真实性体验、非冒犯地参与、带走记忆",
                "trigger_scenes": ["展览", "工坊体验", "民宿"],
            },
            {
                "id": "as_elder_guardian",
                "label": "作为留守老人（守望身份）",
                "spatial_need": "尊严、不被边缘化、医疗可达、习惯保留",
                "trigger_scenes": ["日常起居", "公共活动", "医疗点"],
            },
            {
                "id": "as_young_pioneer",
                "label": "作为驻村创业者（开拓身份）",
                "spatial_need": "工作空间、网络基建、属于感、展示机会",
                "trigger_scenes": ["共享办公", "市集", "社交"],
            },
        ],
    },
    "commercial_hospitality": {
        "trigger_modes": ["M4", "M4_capital_asset"],
        "trigger_type_keywords": ["commercial", "hospitality", "酒店", "民宿", "商业", "度假"],
        "modes": [
            {
                "id": "as_escapist",
                "label": "作为逃离者（度假身份）",
                "spatial_need": "日常断裂感、节奏放慢、感官放大",
                "trigger_scenes": ["入住仪式", "SPA", "景观"],
            },
            {
                "id": "as_explorer",
                "label": "作为探索者（发现身份）",
                "spatial_need": "惊喜、隐藏动线、可讲述的发现",
                "trigger_scenes": ["公共区域", "在地体验", "隐秘角落"],
            },
            {
                "id": "as_status_performer",
                "label": "作为身份展演者（阶层身份）",
                "spatial_need": "可拍摄、品味暗示、排他性空间",
                "trigger_scenes": ["大堂", "餐厅", "顶层"],
            },
            {
                "id": "as_service_provider",
                "label": "作为服务者（职业身份）",
                "spatial_need": "后勤效率、职业尊严、疲劳管理",
                "trigger_scenes": ["后厨", "员工通道", "休息区"],
            },
        ],
    },
    "urban_renewal": {
        "trigger_modes": ["M6", "M6_urban_regeneration"],
        "trigger_type_keywords": ["urban", "城市更新", "旧改", "改造"],
        "modes": [
            {
                "id": "as_original_inhabitant",
                "label": "作为原住民（归属身份）",
                "spatial_need": "不被驱逐、社区网络保留、参与权",
                "trigger_scenes": ["历史街区", "菜场", "邻里空间"],
            },
            {
                "id": "as_newcomer",
                "label": "作为新来者（融入身份）",
                "spatial_need": "接纳感、配套便利、文化入口",
                "trigger_scenes": ["共享空间", "社区活动", "商业配套"],
            },
            {
                "id": "as_passerby",
                "label": "作为城市过客（公共身份）",
                "spatial_need": "可达性、安全感、短暂停留的品质",
                "trigger_scenes": ["街道", "广场", "临街商铺"],
            },
        ],
    },
    "healthcare": {
        "trigger_modes": ["M11", "M11_healthcare_healing"],
        "trigger_type_keywords": ["healthcare", "医疗", "疗愈", "康复", "养老"],
        "modes": [
            {
                "id": "as_vulnerable_patient",
                "label": "作为脆弱者（患者身份）",
                "spatial_need": "心理安全、控制感、尊严、隐私",
                "trigger_scenes": ["病房", "诊疗室", "等候区"],
            },
            {
                "id": "as_anxious_companion",
                "label": "作为焦虑陪伴者（家属身份）",
                "spatial_need": "信息可获取、等候不崩溃、与患者连接",
                "trigger_scenes": ["等候区", "探视通道", "家属休息"],
            },
        ],
    },
    "public_cultural": {
        "trigger_modes": ["M1", "M9", "M1_concept_driven", "M9_social_structure"],
        "trigger_type_keywords": ["public", "cultural", "展览", "博物馆", "文化", "公共"],
        "modes": [
            {
                "id": "as_casual_visitor",
                "label": "作为普通访客",
                "spatial_need": "可理解性、停留舒适度、社交可能",
                "trigger_scenes": ["展厅", "大厅", "休息区"],
            },
            {
                "id": "as_professional_user",
                "label": "作为专业使用者",
                "spatial_need": "功能满足、设备品质、声学光学温控",
                "trigger_scenes": ["工作室", "排练厅", "实验室"],
            },
            {
                "id": "as_event_organizer",
                "label": "作为活动组织方",
                "spatial_need": "灵活性、容量、后勤支持",
                "trigger_scenes": ["多功能厅", "户外广场", "后台"],
            },
        ],
    },
}

# universal 前 5 个有更低的 confirmed 门槛
UNIVERSAL_TOP5 = {"as_family_intimate", "as_professional", "as_social_host", "as_business_partner", "as_solitary_self"}


def _detect_identity_modes(
    user_input: str,
    structured_requirements: Dict,
    detected_modes: List[Dict],
    project_classification: Dict | None,
) -> List[Dict[str, Any]]:
    """检测身份模式：多源交叉"""

    # 获取 mode_ids 和 project_type
    mode_ids = set()
    for m in detected_modes or []:
        mid = m.get("mode", "") if isinstance(m, dict) else str(m)
        mode_ids.add(mid)

    project_type = ""
    if project_classification:
        project_type = project_classification.get("project_type", "")

    # C1: 收集候选身份模式全集
    candidates = list(UNIVERSAL_IDENTITY_MODES)  # 深拷贝
    candidates = [dict(m) for m in candidates]

    for _cat_key, cat_val in PROJECT_SPECIFIC_IDENTITY_MODES.items():
        trigger_modes = set(cat_val.get("trigger_modes", []))
        trigger_kws = cat_val.get("trigger_type_keywords", [])

        mode_match = bool(mode_ids & trigger_modes)
        type_match = any(kw in project_type or kw in user_input for kw in trigger_kws)

        if mode_match or type_match:
            for m in cat_val.get("modes", []):
                candidates.append(dict(m))

    # 为每个候选打分
    results = []
    for mode in candidates:
        evidence_count = 0
        evidence_sources: List[str] = []
        mid = mode["id"]
        scenes = mode.get("trigger_scenes", [])

        # C2: user_input 场景关键词
        for scene in scenes:
            if scene in user_input:
                evidence_count += 1
                evidence_sources.append(f"用户提及场景: {scene}")
                break

        # 额外关键词匹配
        label_kw = mode.get("label", "")
        # 提取括号中的关键词
        import re as _re

        paren_match = _re.search(r"[（(](.+?)[）)]", label_kw)
        if paren_match:
            kw_in_label = paren_match.group(1)
            if kw_in_label in user_input:
                evidence_count += 1
                evidence_sources.append(f"用户提及: {kw_in_label}")

        # C3: character_narrative
        char_narrative = structured_requirements.get("character_narrative", {})
        if isinstance(char_narrative, dict):
            who = str(char_narrative.get("who", ""))
            conflict = str(char_narrative.get("internal_conflict", ""))
            combined = who + " " + conflict
            for scene in scenes:
                if scene in combined:
                    evidence_count += 1
                    evidence_sources.append(f"角色叙事匹配: {scene}")
                    break

        # C4: five_whys L4/L5
        five_whys = structured_requirements.get("five_whys_analysis", {})
        if isinstance(five_whys, dict):
            all_text = ""
            for chain in five_whys.values():
                if isinstance(chain, dict):
                    all_text += " " + str(chain.get("L4_why_emotion", ""))
                    all_text += " " + str(chain.get("L5_why_identity", ""))
            for scene in scenes:
                if scene in all_text:
                    evidence_count += 1
                    evidence_sources.append(f"五层追问匹配: {scene}")
                    break

        # C5: emotional_landscape / ritual_behaviors
        emo = str(structured_requirements.get("emotional_landscape", ""))
        rituals = str(structured_requirements.get("ritual_behaviors", ""))
        combined_emo = emo + " " + rituals
        for scene in scenes:
            if scene in combined_emo:
                evidence_count += 1
                evidence_sources.append(f"情感/仪式匹配: {scene}")
                break

        # 分类
        if evidence_count >= 2:
            status = "confirmed"
        elif evidence_count == 1 and mid in UNIVERSAL_TOP5:
            status = "confirmed"  # universal 前5 降低门槛
        elif evidence_count >= 1:
            status = "candidate"
        else:
            status = "excluded"

        if status != "excluded":
            results.append(
                {
                    **mode,
                    "evidence_count": evidence_count,
                    "evidence_sources": evidence_sources,
                    "status": status,
                }
            )

    return results


# ==================================================================================
# v10.1: 通用输出框架信号提取（不硬编码任何项目类型）
# ==================================================================================


def _extract_framework_signals(
    user_input: str,
    structured_requirements: Dict,
    active_projections: List[str],
    identity_modes: List[Dict],
) -> Dict[str, Any]:
    """
    从用户输入和结构化需求中提取通用的输出框架信号。

    这些信号是抽象描述（不是具体章节模板），下游 LLM 根据信号动态推理框架结构。
    覆盖 190+ 问题类型的多元性：15㎡电竞卧室到50000㎡酒店，8000元到无上限预算。

    返回 dict 包含:
      - scope: 项目范围信号
      - constraints: 约束信号（什么限制最紧）
      - mandatory_dimensions: 必须覆盖的特殊领域
      - output_calibration: 输出深度/广度校准
      - audience_needs: 受众决策需求
      - reasoning: 推理依据文本
    """
    signals: Dict[str, Any] = {}

    # ─── A. 范围信号 ───
    scope = {
        "scale_markers": [],  # 面积/体量/预算等量化标记
        "object_count": "unknown",  # 单一空间 / 单体建筑 / 建筑群 / 片区
        "temporal_hint": None,  # 永久 / 临时 / 可迭代
    }

    # A1: 面积/体量提取
    area_patterns = [
        (r"(\d+[\.,]?\d*)\s*㎡", "area_sqm"),
        (r"(\d+[\.,]?\d*)\s*平方米", "area_sqm"),
        (r"(\d+[\.,]?\d*)\s*(?:平米|平方)", "area_sqm"),
        (r"(\d+[\.,]?\d*)\s*[亩]", "area_mu"),
        (r"(\d+)\s*[间房套层栋]", "unit_count"),
        (r"(\d+)\s*[万]?\s*[㎡平方米]", "area_sqm"),
    ]
    for pat, marker_type in area_patterns:
        matches = re.findall(pat, user_input)
        for m in matches:
            scope["scale_markers"].append({"type": marker_type, "value": m})

    # A2: 对象粒度判断
    if re.search(r"单间|卧室|书房|厨房|浴室|茶室|包房|一间|一个空间", user_input):
        scope["object_count"] = "single_space"
    elif re.search(r"社区|片区|街区|园区|聚落|小镇|村庄|村(?=[整更改])|新区|综合体|村$", user_input):
        scope["object_count"] = "district_cluster"
    elif re.search(r"整栋|单体建筑|一栋|别墅|公寓|住宅|办公室|工作室|店铺|诊所", user_input):
        scope["object_count"] = "single_building"
    elif re.search(r"方法论|体系.*研究|系统分析|课题|理论", user_input):
        scope["object_count"] = "theoretical"

    # A3: 时间属性
    if re.search(r"临时|快闪|快速搭建|可拆卸|三个月|pop.?up", user_input, re.IGNORECASE):
        scope["temporal_hint"] = "temporary"
    elif re.search(r"可迭代|可升级|可成长|模块化|预留", user_input):
        scope["temporal_hint"] = "iterative"
    else:
        scope["temporal_hint"] = "permanent"

    signals["scope"] = scope

    # ─── B. 约束信号（什么限制最紧）───
    constraints = []

    # B1: 预算约束
    budget_patterns = [
        (r"预算[^，。,\n]{0,6}(\d+[\.,]?\d*)\s*[万元]", "tight_budget"),
        (r"(\d+)\s*[万]?\s*元[的]?预算", "tight_budget"),
        (r"(\d+)\s*元[\/每]\s*[㎡平]", "unit_cost_limit"),
        (r"低成本|极低预算|有限预算|预算有限|预算[仅只]", "budget_pressure"),
        (r"成本控制|造价控制|资金[链有限]", "budget_pressure"),
        (r"预算|经费|费用|造价", "budget_mentioned"),
    ]
    for pat, constraint_type in budget_patterns:
        if re.search(pat, user_input):
            constraints.append({"type": "budget", "sub_type": constraint_type})
            break

    # B2: 法规/安全约束
    if re.search(r"消防|规范|审批|合规|历史建筑|保护|文物|安全等级|洁净|无菌", user_input):
        constraints.append({"type": "regulatory"})

    # B3: 物理/环境极端约束
    if re.search(r"极寒|高原|海拔|台风|盐雾|潮湿|地震|防洪|极端|沙漠|极地|火山", user_input):
        constraints.append({"type": "extreme_environment"})

    # B4: 心理/特殊人群约束
    if re.search(r"自闭症|无障碍|轮椅|过敏|失眠|恐惧|焦虑|创伤|临终|患者|老人|儿童|留守", user_input):
        constraints.append({"type": "special_population"})

    # B5: 时间约束
    if re.search(r"夜间施工|不闭店|快速|紧急|三个月|短期|限时", user_input):
        constraints.append({"type": "time_pressure"})

    # B6: 空间极限约束（仅匹配 ≤30㎡ 的数字）
    if re.search(r"(?<!\d)[1-2]\d㎡|极限空间|极小|微型|房车|(?<!\d)[3-9]㎡", user_input):
        constraints.append({"type": "extreme_compact"})

    # B7: 多方冲突约束
    if re.search(r"冲突|矛盾|不同[风格偏好需求]|平衡|调和|兼顾.*兼顾|既.*又.*又|合租|再婚|复杂家庭", user_input):
        constraints.append({"type": "stakeholder_conflict"})

    signals["constraints"] = constraints

    # ─── C. 必须覆盖的特殊领域（从用户原文提取，不预设清单）───
    mandatory_dimensions = []

    # 领域检测组：每组是 (regex, dimension_label)
    # 注意：这些不是硬编码的"类型"，而是"领域信号"——任何项目都可能触发任意组合
    dimension_detectors = [
        (r"声学|隔音|吸音|扩散|混音|杜比|音响", "acoustics"),
        (r"无障碍|轮椅|感统|适老|儿童尺度|安全防护", "accessibility_safety"),
        (r"消防|疏散|耐火|防火|安全出口", "fire_safety"),
        (r"品牌[转译表达定位辨识]|IP|品牌.*融合|视觉.*系统", "brand_translation"),
        (r"智能|智慧|传感|物联|鸿蒙|自动化|AI|VR|AR|投影|沉浸|RGB|灯光系统|灯带|LED[控系]", "smart_technology"),
        (r"声环境|气味|香氛|嗅觉|触感|五感|感官", "multi_sensory"),
        (r"恒温恒湿|防潮|防腐|防氧化|保温|隔热", "environmental_control"),
        (r"拍摄|直播|录制|录音棚|录影|背景.*替换", "media_production"),
        (r"展陈|展示|博物馆|展厅|策展|陈列", "exhibition_curation"),
        (r"供暖|地暖|空调|新风|供氧|净化|散热", "hvac_MEP"),
        (r"材料.*[循环回收可追溯]|零碳|碳足迹|环保|可持续", "sustainability"),
        (r"运营|坪效|翻台|客单价|收入.*模型|商业.*模式", "operation_model"),
        (r"竞标|竞争|差异化|对标|竞品", "competitive_strategy"),
        (r"文化.*[转译融合表达抽象]|在地|乡土|民族|非遗|传统.*现代", "cultural_translation"),
        (r"心理[安全支持恢复]|情绪[缓冲支持管理]|创伤|疗愈|正念|冥想", "psychological_wellbeing"),
        (r"结构[加固改造]|防水|基础|承重|抗震|抗风", "structural_engineering"),
        (r"收纳|储物|隐藏|隐形|模块[化]|折叠|可变", "modularity_storage"),
        (r"安防|监控|门禁|隐蔽|保密|安全等级", "security"),
        (r"宠物|猫|狗|动物", "pet_integration"),
        (r"数据[驱动可视化监控]|热力图|传感器|反馈", "data_driven_design"),
    ]

    for pattern, dim_label in dimension_detectors:
        if re.search(pattern, user_input):
            mandatory_dimensions.append(dim_label)

    # 从 structured_requirements 补充（需求分析师可能识别出更多领域）
    sr_features = structured_requirements.get("project_features", {})
    if isinstance(sr_features, dict):
        special = sr_features.get("special_requirements", [])
        if isinstance(special, list):
            for req in special:
                req_str = str(req).lower()
                for pattern, dim_label in dimension_detectors:
                    if re.search(pattern, req_str) and dim_label not in mandatory_dimensions:
                        mandatory_dimensions.append(dim_label)

    signals["mandatory_dimensions"] = mandatory_dimensions

    # ─── D. 输出校准信号 ───
    calibration = {
        "depth_hint": "standard",  # exhaustive / strategic / executive / compressed
        "visual_expectation": False,  # 是否期待图片/参考图/效果图
        "quantitative_expectation": False,  # 是否期待数据/测算/表格
    }

    # D1: 深度提示
    if re.search(r"完整.*框架|系统.*[分析梳理]|全维度|深度[解析分析]|方法论", user_input):
        calibration["depth_hint"] = "exhaustive"
    elif re.search(r"策略|定位|概念|方向|思路", user_input):
        calibration["depth_hint"] = "strategic"
    elif re.search(r"快速|简要|概述|摘要", user_input):
        calibration["depth_hint"] = "compressed"

    # D2: 视觉期待
    if re.search(r"效果[图参考]|参考[图片案例]|视觉|样板|呈现", user_input):
        calibration["visual_expectation"] = True

    # D3: 量化期待
    if re.search(r"测算|预算|造价|费用|回报|收入|坪效|数据|面积.*配比", user_input):
        calibration["quantitative_expectation"] = True

    signals["output_calibration"] = calibration

    # ─── E. 受众决策需求 ───
    audience_needs = []
    for proj_id in active_projections:
        display = PROJECTION_DISPLAY.get(proj_id, {})
        audience_needs.append(
            {
                "projection_id": proj_id,
                "audience_label": display.get("label", proj_id),
                "audience_desc": display.get("desc", ""),
            }
        )
    signals["audience_needs"] = audience_needs

    # ─── F. 推理依据 ───
    reasoning_parts = []
    if scope["object_count"] != "unknown":
        reasoning_parts.append(f"范围={scope['object_count']}")
    if scope["scale_markers"]:
        markers_str = ", ".join(f"{m['type']}={m['value']}" for m in scope["scale_markers"][:3])
        reasoning_parts.append(f"规模=[{markers_str}]")
    if constraints:
        c_types = [c["type"] for c in constraints]
        reasoning_parts.append(f"约束=[{', '.join(c_types)}]")
    if mandatory_dimensions:
        reasoning_parts.append(
            f"特殊领域=[{', '.join(mandatory_dimensions[:5])}{'...' if len(mandatory_dimensions) > 5 else ''}]"
        )
    reasoning_parts.append(f"交付类型={active_projections}")
    reasoning_parts.append(f"身份模式={len(identity_modes)}种")
    signals["reasoning"] = " | ".join(reasoning_parts)

    return signals


# ==================================================================================
# 节点主函数
# ==================================================================================


@track_active_step("output_intent_detection")
def output_intent_detection_node(state: dict, store=None) -> Command:
    """
    输出意图检测节点

    位于 requirements_analyst 之后、feasibility_analyst 之前。
    四源交叉检测交付类型 + 身份模式，必要时 interrupt 确认。
    """
    logger.info("=" * 60)
    logger.info("🎯 [v10.x] 输出意图检测节点启动")
    logger.info("=" * 60)

    # -------------------------------------------------------
    # 0. 提取上下文
    # -------------------------------------------------------
    user_input = state.get("user_input", "")
    agent_results = state.get("agent_results", {})
    ra_result = agent_results.get("requirements_analyst", {})
    structured_requirements = ra_result.get("structured_data", {}) or {}
    detected_modes = state.get("detected_design_modes", []) or []

    # v10.1 fix: project_classification 已被 v9.1 移除（永远为 None），
    # 改为从 project_type (str) 构造兼容结构，供 _detect_spatial_attribute_signals 使用
    _project_type_str = state.get("project_type", "") or structured_requirements.get("project_type", "")
    project_classification = {"project_type": _project_type_str} if _project_type_str else None

    # 如果 requirements_analyst 没有产出结构化数据，尝试从 state 直接取
    if not structured_requirements:
        structured_requirements = state.get("structured_requirements", {}) or {}

    logger.info(f"  用户输入长度: {len(user_input)}")
    logger.info(f"  检测模式数: {len(detected_modes)}")
    logger.info(f"  结构化数据字段: {list(structured_requirements.keys())[:10]}")

    # -------------------------------------------------------
    # 🗑️ v8.3: 移除旧的幂等保护逻辑
    # 原因：v8.3流程中output_intent作为统一问卷Step 1，不需要幂等保护
    # 工作流路由已确保不会重复进入此节点（output_intent_confirmed后直接到Step 2）
    # -------------------------------------------------------

    # -------------------------------------------------------
    # 1. 四源交叉检测交付类型
    # -------------------------------------------------------
    explicit_signals = _detect_explicit_signals(user_input)
    stakeholder_signals = _detect_stakeholder_signals(structured_requirements)
    mandatory_proj, likely_proj = _detect_spatial_attribute_signals(detected_modes, project_classification)
    motivation_signals = _detect_motivation_signals(structured_requirements, user_input)

    logger.info(f"  源1 显式信号: {explicit_signals}")
    logger.info(f"  源2 角色信号: {stakeholder_signals}")
    logger.info(f"  源3 空间规则: mandatory={mandatory_proj}, likely={likely_proj}")
    logger.info(f"  源4 动机信号: {motivation_signals}")

    delivery_results = _score_delivery_types(
        explicit_signals, stakeholder_signals, mandatory_proj, likely_proj, motivation_signals
    )

    for r in delivery_results:
        logger.info(f"  📊 {r['id']}: score={r['score']}, status={r['status']}, evidence={r['evidence']}")

    # -------------------------------------------------------
    # 2. 身份模式检测
    # -------------------------------------------------------
    identity_results = _detect_identity_modes(
        user_input, structured_requirements, detected_modes, project_classification
    )

    confirmed_modes = [m for m in identity_results if m["status"] == "confirmed"]
    candidate_modes = [m for m in identity_results if m["status"] == "candidate"]
    logger.info(f"  身份模式: confirmed={len(confirmed_modes)}, candidate={len(candidate_modes)}")
    for m in confirmed_modes:
        logger.info(f"    ✅ {m['label']} ({m['evidence_count']}源: {m['evidence_sources']})")
    for m in candidate_modes:
        logger.info(f"    ❓ {m['label']} ({m['evidence_count']}源: {m['evidence_sources']})")

    # -------------------------------------------------------
    # 2.5 🆕 v12.0: 约束识别管线 — 空间区域 + 视觉约束提取
    # -------------------------------------------------------
    extracted_spatial_zones = _extract_spatial_zones(structured_requirements, user_input)
    visual_constraints = None

    try:
        import asyncio

        # 先将 extracted_spatial_zones 注入 state 以便管线读取
        _state_with_zones = {**state, "extracted_spatial_zones": extracted_spatial_zones}
        # 🔑 sync 节点中运行 async 管线：使用 asyncio.run()
        # LangGraph 允许在 sync 节点中使用 asyncio.run() 来等待异步结果
        try:
            loop = asyncio.get_running_loop()
            # 如果已有 event loop（如被 async 调用方调用），使用 nest_asyncio 或创建 task
            import nest_asyncio

            nest_asyncio.apply()
            visual_constraints = loop.run_until_complete(_run_constraint_pipeline(_state_with_zones))
        except RuntimeError:
            # 没有 running loop，可以安全地使用 asyncio.run()
            visual_constraints = asyncio.run(_run_constraint_pipeline(_state_with_zones))
    except Exception as e:
        logger.warning(f"⚠️ [v12.0] 约束管线执行异常（不影响主流程）: {e}")
        visual_constraints = None

    if visual_constraints:
        logger.info(f"  🎯 [v12.0] 约束信封长度: {len(visual_constraints.get('constraint_envelope', ''))}")
    else:
        logger.info("  📷 [v12.0] 无视觉约束（无上传图片或提取失败）")

    # -------------------------------------------------------
    # 3. 🆕 v11.0: 构建输出意图载荷并 interrupt 等待用户确认（Step 0）
    # -------------------------------------------------------
    confirmed_deliveries = [r for r in delivery_results if r["status"] == "confirmed"]
    candidate_deliveries = [r for r in delivery_results if r["status"] == "candidate"]

    # AI 推荐的默认值（confirmed 项）
    ai_projections = [r["id"] for r in confirmed_deliveries]
    if "design_professional" not in ai_projections:
        ai_projections.insert(0, "design_professional")
    ai_projections = ai_projections[:3]

    ai_modes = confirmed_modes

    # Bug④ fix v9.3: 幂等保护 — 如果 active_projections 已存在且 intent_changed=False，跳过 interrupt
    existing_projections = state.get("active_projections") or []
    if existing_projections and not state.get("intent_changed", False):
        logger.info(f"  ⏭️ [v9.3] 幂等保护: active_projections 已存在 ({existing_projections})，跳过 interrupt")
        return Command(
            update={
                "active_projections": existing_projections,
                "intent_changed": False,
            }
        )

    # 构建交付类型选项（显示全部，recommended=confirmed）
    delivery_options = []
    for r in delivery_results:
        if r["status"] == "excluded":
            continue
        delivery_options.append(
            {
                "id": r["id"],
                "label": r["label"],
                "desc": r["desc"],
                "recommended": r["status"] == "confirmed",
                "evidence": r["evidence"],
            }
        )

    # 构建身份模式选项
    mode_options = []
    for m in identity_results:
        if m["status"] == "excluded":
            continue
        mode_options.append(
            {
                "id": m["id"],
                "label": m["label"],
                "spatial_need": m.get("spatial_need", ""),
                "recommended": m["status"] == "confirmed",
                "evidence_sources": m.get("evidence_sources", []),
            }
        )

    # 🆕 v12.1: 构建推荐约束列表（从 framework_signals 预提取）
    _pre_signals = _extract_framework_signals(
        user_input=user_input,
        structured_requirements=structured_requirements,
        active_projections=ai_projections,
        identity_modes=[],
    )
    recommended_constraints_list = _build_recommended_constraints(
        mandatory_dims=_pre_signals.get("mandatory_dimensions", []),
        constraints=_pre_signals.get("constraints", []),
        visual_constraints=visual_constraints,
    )

    # 🆕 v13.1: 构建需求分析复盘卡片（纯字段提取，零 LLM 调用）
    _info_quality = structured_requirements.get("info_quality_metadata", {})
    if not _info_quality:
        _info_quality = ra_result.get("structured_data", {}).get("info_quality_metadata", {}) or {}
    _core_tensions_raw = structured_requirements.get("core_tensions") or []
    _deliverables_raw = structured_requirements.get("primary_deliverables") or []
    _design_modes_raw = detected_modes or []
    requirements_judgement = {
        "summary": structured_requirements.get("breakthrough_insight", ""),  # 前端字段名: summary
        "core_tensions": [
            {"name": t.get("name", ""), "implication": t.get("design_implication", t.get("implication", ""))}
            for t in _core_tensions_raw[:3]
        ],
        "info_quality": {
            "score": _info_quality.get("score", 0),
            "confidence_level": _info_quality.get("confidence_level", "medium"),
            "present_dimensions": _info_quality.get("present_dimensions", []),
            "missing_dimensions": _info_quality.get("missing_dimensions", []),
        },
        "primary_deliverables": [
            {"type": d.get("type", ""), "description": d.get("description", ""), "priority": d.get("priority", "")}
            for d in _deliverables_raw[:5]
        ],
        "design_mode": {
            "mode": _design_modes_raw[0].get("mode", "")
            if isinstance(_design_modes_raw[0], dict)
            else str(_design_modes_raw[0]),
            "confidence": _design_modes_raw[0].get("confidence", 0) if isinstance(_design_modes_raw[0], dict) else 0,
        }
        if _design_modes_raw
        else None,
    }
    logger.info(
        f"  📋 [v13.1] requirements_judgement: summary={bool(requirements_judgement['summary'])}, tensions={len(requirements_judgement['core_tensions'])}, quality_score={requirements_judgement['info_quality']['score']}"
    )

    output_intent_payload = {
        "interaction_type": "output_intent_confirmation",
        "title": "输出意图确认",
        "delivery_types": {
            "message": "交付类型：",
            "options": delivery_options,
            "max_select": 3,
        },
        "identity_modes": {
            "message": "身份视角：",
            "options": mode_options,
        } if mode_options else None,
        "recommended_constraints": {
            "message": "推荐约束维度：",
            "options": recommended_constraints_list,
        } if recommended_constraints_list else None,
        # 🆕 v12.0: 附加空间区域和自动检测的约束
        "spatial_zones": extracted_spatial_zones,
        "auto_detected_constraints": visual_constraints if visual_constraints else None,
        # 🆕 v13.1: 需求分析复盘卡片数据（向上验证需求分析的落地性）
        "requirements_judgement": requirements_judgement,
    }

    logger.info(f"  🛑 [v11.0] Step0 interrupt: {len(delivery_options)}个交付选项, {len(mode_options)}个身份选项")
    user_response = interrupt(output_intent_payload)
    logger.info(f"  ✅ [v11.0] Step0 用户响应: {type(user_response)}")

    # 解析用户确认结果
    if isinstance(user_response, dict):
        selected_deliveries = user_response.get("selected_deliveries", [])
        selected_modes_ids = user_response.get("selected_modes", [])
        # 🆕 v12.1: 用户确认的约束列表（替代旧 user_constraints）
        confirmed_constraints = user_response.get("confirmed_constraints") or []
        # 兼容旧前端: 如果只传了 user_constraints，转换为 confirmed_constraints 格式
        if not confirmed_constraints and user_response.get("user_constraints"):
            confirmed_constraints = [
                {"id": f"user_{i}", "label": c.get("label", ""), "desc": c.get("desc", ""), "source": "user_added"}
                for i, c in enumerate(user_response["user_constraints"])
            ]
        # 🆕 v12.1: 用户保留的视觉参考索引
        kept_visual_reference_indices = user_response.get("kept_visual_reference_indices") or []
    else:
        selected_deliveries = []
        selected_modes_ids = []
        confirmed_constraints = []
        kept_visual_reference_indices = []

    # 合并 AI 推荐 + 用户覆盖
    active_projections = selected_deliveries if selected_deliveries else ai_projections
    if "design_professional" not in active_projections:
        active_projections.insert(0, "design_professional")
    active_projections = active_projections[:3]

    # 身份模式：用户选中 → 过滤；否则使用 AI confirmed
    all_identity_results = identity_results
    if selected_modes_ids:
        final_modes = [m for m in all_identity_results if m.get("id") in selected_modes_ids]
    else:
        final_modes = ai_modes

    # 是否偏离 AI 推荐
    intent_changed = set(active_projections) != set(ai_projections)
    logger.info(f"  📊 [v11.0] intent_changed={intent_changed}, projections={active_projections}")

    # 清理 final_modes 以便序列化
    serializable_modes = []
    for m in final_modes:
        serializable_modes.append(
            {
                "id": m["id"],
                "label": m["label"],
                "spatial_need": m.get("spatial_need", ""),
                "trigger_scenes": m.get("trigger_scenes", []),
            }
        )

    # -------------------------------------------------------
    # 4. v10.1 通用框架信号提取
    # -------------------------------------------------------
    framework_signals = _extract_framework_signals(
        user_input=user_input,
        structured_requirements=structured_requirements,
        active_projections=active_projections,
        identity_modes=serializable_modes,
    )

    # 🆕 v12.1: 将用户确认的约束注入 framework_signals
    if confirmed_constraints:
        # 提取 AI 推荐中被用户确认的维度 ID
        confirmed_dim_ids = [c["id"] for c in confirmed_constraints if c.get("source") == "ai_recommended"]
        # 用户手动添加的约束转为文本描述注入
        user_added = [c for c in confirmed_constraints if c.get("source") == "user_added"]
        # 覆盖 mandatory_dimensions 为用户确认版本（AI推荐的维度ID）
        if confirmed_dim_ids:
            framework_signals["mandatory_dimensions"] = confirmed_dim_ids
        # 将用户手动添加的约束注入 constraints 列表
        for c in user_added:
            framework_signals.setdefault("constraints", []).append(
                {
                    "type": "user_declared",
                    "label": c.get("label", ""),
                    "desc": c.get("desc", ""),
                }
            )
        logger.info(
            f"  🎯 [v12.1] 用户确认约束: {len(confirmed_constraints)}项 (AI推荐{len(confirmed_dim_ids)}, 手动{len(user_added)})"
        )

    logger.info(f"  📐 框架信号: scope={framework_signals.get('scope', {}).get('object_count', '?')}")
    logger.info(f"  📐 约束数: {len(framework_signals.get('constraints', []))}")
    logger.info(f"  📐 特殊领域: {framework_signals.get('mandatory_dimensions', [])}")
    logger.info(f"  📐 推理: {framework_signals.get('reasoning', '')}")

    logger.info("=" * 60)
    logger.info("🎯 输出意图检测完成(v11.0):")
    logger.info(f"   交付类型: {active_projections}")
    logger.info(f"   身份模式: {[m['label'] for m in serializable_modes]}")
    logger.info(f"   intent_changed: {intent_changed}")
    logger.info(f"   框架信号: {framework_signals.get('reasoning', '')}")
    logger.info("=" * 60)

    return Command(
        update={
            "active_projections": active_projections,
            "detected_identity_modes": serializable_modes,
            "output_framework_signals": framework_signals,
            "intent_changed": intent_changed,
            # output_intent_payload 置 None（v11.0 已由 interrupt 处理）
            "output_intent_payload": None,
            # 🆕 v12.0: 视觉约束 + 空间区域
            "visual_constraints": visual_constraints,
            "extracted_spatial_zones": extracted_spatial_zones,
            # 🆕 v12.1: 用户确认的约束（替代旧 user_intent_constraints）
            "user_intent_constraints": confirmed_constraints if confirmed_constraints else None,
            # 🆕 v8.3: 标记输出意图已确认
            "output_intent_confirmed": True,
            # 🆕 v12.1: 用户保留的视觉参考索引
            "kept_visual_reference_indices": kept_visual_reference_indices if kept_visual_reference_indices else None,
            "detail": f"输出意图检测完成(v12.0): {len(active_projections)}种交付类型, {len(serializable_modes)}种身份模式",
        },
        # 🔧 v8.3: 输出意图确认后直接进入渐进式问卷Step 1（任务梳理）
        goto="progressive_step1_core_task",
    )
