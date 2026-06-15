"""
通用方法论检查器 (General Method Checker)

将 general_method_profile.active_checks 中的 check_id 字符串映射到实际 Python 检查函数。
每个检查函数接收 (state, structured_data) 并返回 CheckResult 字典：

    {
        "check_id": str,
        "passed": bool,
        "severity": "warning" | "error" | "blocker",
        "message": str,           # 人类可读的问题描述
        "action": "record" | "clarify" | "block",
        "clarification_hint": str | None,  # 建议追问方向
    }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------
CheckResult = Dict[str, Any]
StateDict = Dict[str, Any]
StructuredData = Dict[str, Any]


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _result(
    check_id: str,
    passed: bool,
    severity: str,
    message: str,
    action: str = "record",
    clarification_hint: Optional[str] = None,
) -> CheckResult:
    return {
        "check_id": check_id,
        "passed": passed,
        "severity": severity,
        "message": message,
        "action": action,
        "clarification_hint": clarification_hint,
    }


def _get_text(state: StateDict, structured_data: StructuredData) -> str:
    """合并用户输入与结构化数据文本，用于关键词检测。"""
    parts = [
        state.get("user_input", ""),
        str(structured_data.get("project_goal", "")),
        str(structured_data.get("target_users", "")),
        str(structured_data.get("constraints", "")),
        str(structured_data.get("budget", "")),
        str(structured_data.get("timeline", "")),
    ]
    return " ".join(p for p in parts if p).lower()


# ---------------------------------------------------------------------------
# 默认兜底检查 (general_gap_and_tension_check)
# ---------------------------------------------------------------------------

def check_missing_goal(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_goal"
    goal = str(structured_data.get("project_goal", "")).strip()
    if goal and len(goal) > 5:
        return _result(cid, True, "warning", "项目目标已存在")
    return _result(
        cid, False, "error",
        "项目目标未被明确或存在根本歧义",
        action="clarify",
        clarification_hint="请说明本项目最核心的设计目标是什么？希望实现什么效果？",
    )


def check_missing_user(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_user"
    users = str(structured_data.get("target_users", "") or structured_data.get("users", "")).strip()
    text = _get_text(state, structured_data)
    user_keywords = ["用户", "使用者", "客户", "访客", "业主", "学生", "患者", "员工", "居民", "访客"]
    has_user = bool(users) or any(kw in text for kw in user_keywords)
    if has_user:
        return _result(cid, True, "warning", "主要使用者已被提及")
    return _result(
        cid, False, "error",
        "主要使用者未被定义",
        action="clarify",
        clarification_hint="本项目主要面向哪些使用者？他们的核心需求是什么？",
    )


def check_missing_constraints(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_constraints"
    text = _get_text(state, structured_data)
    constraint_keywords = ["预算", "造价", "工期", "时间", "面积", "用地", "规范", "限高", "容积率"]
    has_constraints = any(kw in text for kw in constraint_keywords)
    if has_constraints:
        return _result(cid, True, "warning", "关键约束条件已被提及")
    return _result(
        cid, False, "warning",
        "关键约束（预算/用地/工期）均未被提及",
        action="clarify",
        clarification_hint="项目的预算范围、工期要求、面积限制大致是多少？",
    )


def check_goal_user_mismatch(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """目标与使用者之间的逻辑不一致检测（v2新增）。"""
    cid = "goal_user_mismatch"
    goal = str(structured_data.get("project_goal", "")).lower()
    users = str(structured_data.get("target_users", "") or structured_data.get("users", "")).lower()
    # 简单信号：两者都存在但明显矛盾（如目标提高端，用户是普通大众）
    high_end_signals = ["高端", "奢华", "顶级", "vip", "精品"]
    mass_signals = ["大众", "普通", "平价", "低价", "亲民"]
    goal_high = any(s in goal for s in high_end_signals)
    user_mass = any(s in users for s in mass_signals)
    if goal_high and user_mass:
        return _result(
            cid, False, "warning",
            "目标定位高端但使用者似乎以大众为主，存在逻辑矛盾",
            action="clarify",
            clarification_hint="高端定位与大众用户群之间如何平衡？目标受众和商业定位需要再确认。",
        )
    return _result(cid, True, "warning", "目标与使用者逻辑未发现明显矛盾")


def check_scope_overload(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """空间范围相对预算工期严重过载检测（v2新增）。"""
    cid = "scope_overload"
    text = _get_text(state, structured_data)
    # 检查是否同时出现大面积+紧工期+低预算信号
    large_area = any(kw in text for kw in ["万㎡", "万平", "大型", "超大"])
    tight_budget = any(kw in text for kw in ["低预算", "经费有限", "预算紧张", "成本控制"])
    tight_schedule = any(kw in text for kw in ["紧急", "一个月", "两个月", "赶工", "快速"])
    if (large_area and tight_budget) or (large_area and tight_schedule):
        return _result(
            cid, False, "warning",
            "空间规模与预算/工期之间存在潜在过载风险",
            action="clarify",
            clarification_hint="项目面积/规模与预算工期是否已做过可行性匹配？建议明确分期策略。",
        )
    return _result(cid, True, "warning", "未发现明显的范围过载信号")


def check_ambiguity_blocker(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """根本性歧义导致无法继续推进的检测（v2新增）。"""
    cid = "ambiguity_blocker"
    # 如果任务数为0且用户输入极短，认为存在阻断性歧义
    confirmed_tasks = state.get("confirmed_core_tasks", [])
    user_input = state.get("user_input", "")
    if not confirmed_tasks and len(user_input) < 20:
        return _result(
            cid, False, "blocker",
            "项目信息过于简单，无法形成有效分析起点",
            action="block",
            clarification_hint="请描述项目类型、场地条件、设计目标和预期使用者。",
        )
    return _result(cid, True, "warning", "未发现阻断性歧义")


# ---------------------------------------------------------------------------
# 民宿/酒店检查 (method.general.tension_check.v1)
# ---------------------------------------------------------------------------

def check_public_private_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "public_private_conflict"
    text = _get_text(state, structured_data)
    has_public = any(kw in text for kw in ["大堂", "公区", "公共区", "餐厅", "泳池", "共享"])
    has_private = any(kw in text for kw in ["客房", "套房", "卧室", "私密", "独立"])
    if has_public and has_private:
        # 检查是否有隔声/隔离处理的描述
        has_separation = any(kw in text for kw in ["隔声", "隔音", "视线", "边界", "分隔", "独立出入"])
        if not has_separation:
            return _result(
                cid, False, "error",
                "公共区域与客房私密性需求之间缺乏隔声/视线边界处理",
                action="clarify",
                clarification_hint="公共区域（大堂/餐厅/泳池）与客房之间的隔声和视线边界如何处理？",
            )
    return _result(cid, True, "warning", "公区与私密区冲突未发现明显问题")


def check_mixed_audience_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "mixed_audience_conflict"
    text = _get_text(state, structured_data)
    audience_types = []
    if any(kw in text for kw in ["亲子", "儿童", "家庭", "带孩子"]):
        audience_types.append("亲子")
    if any(kw in text for kw in ["商务", "会议", "出差", "工作"]):
        audience_types.append("商务")
    if any(kw in text for kw in ["情侣", "蜜月", "浪漫", "度假"]):
        audience_types.append("情侣")
    if len(audience_types) >= 2:
        return _result(
            cid, False, "warning",
            f"存在多类型访客（{'、'.join(audience_types)}），需求可能冲突",
            action="clarify",
            clarification_hint=f"项目同时面向{'/'.join(audience_types)}客群，如何在空间上区分服务各群体的差异需求？",
        )
    return _result(cid, True, "warning", "未发现混合受众冲突")


def check_seasonal_operation_gap(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "seasonal_operation_gap"
    text = _get_text(state, structured_data)
    has_seasonal = any(kw in text for kw in ["旺季", "淡季", "季节", "暑期", "节假日", "高峰", "低谷"])
    if not has_seasonal:
        return _result(
            cid, False, "warning",
            "淡旺季运营差异未被规划，可能导致设计不适配",
            action="record",
            clarification_hint="旺季最大客容量与淡季最低运营成本是否有对应的空间设计边界？",
        )
    return _result(cid, True, "warning", "淡旺季运营已被考虑")


def check_budget_schedule_overload(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "budget_schedule_overload"
    text = _get_text(state, structured_data)
    overload_signals = ["预算超出", "工期紧", "成本超标", "投资回报", "roi"]
    if any(s in text for s in overload_signals):
        return _result(
            cid, False, "warning",
            "预算与工期相对于方案目标存在结构性过载风险",
            action="clarify",
            clarification_hint="当前方案目标与预算工期是否经过可行性匹配？是否需要调整方案范围？",
        )
    return _result(cid, True, "warning", "未发现明显的预算工期过载")


# ---------------------------------------------------------------------------
# 医疗/康养检查 (method.general.safety_first_check.v1)
# ---------------------------------------------------------------------------

def check_missing_safety_process(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_safety_process"
    text = _get_text(state, structured_data)
    safety_keywords = ["洁污分流", "急救", "消防", "疏散", "安全通道", "无菌", "隔离"]
    has_safety = any(kw in text for kw in safety_keywords)
    if not has_safety:
        return _result(
            cid, False, "error",
            "流程安全（洁污分流/急救动线）未被明确设计",
            action="clarify",
            clarification_hint="医疗/康养空间的洁污分流、急救动线、消防疏散是否已纳入方案？",
        )
    return _result(cid, True, "warning", "安全流程已有所涉及")


def check_privacy_risk(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "privacy_risk"
    text = _get_text(state, structured_data)
    privacy_keywords = ["隐私", "保密", "私密", "病历", "患者信息"]
    has_privacy = any(kw in text for kw in privacy_keywords)
    if not has_privacy:
        return _result(
            cid, False, "warning",
            "患者隐私边界缺失或模糊",
            action="record",
            clarification_hint="患者诊疗区域的隐私保护（视线/声音/信息）是否有明确边界设计？",
        )
    return _result(cid, True, "warning", "隐私保护已被提及")


def check_accessibility_gap(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "accessibility_gap"
    text = _get_text(state, structured_data)
    a11y_keywords = ["无障碍", "轮椅", "残障", "老年人", "坡道", "电梯"]
    has_a11y = any(kw in text for kw in a11y_keywords)
    if not has_a11y:
        return _result(
            cid, False, "warning",
            "无障碍设计未被纳入空间推演",
            action="record",
            clarification_hint="本项目是否需要满足无障碍设计规范？老年人/残障人士如何使用该空间？",
        )
    return _result(cid, True, "warning", "无障碍设计已被提及")


# ---------------------------------------------------------------------------
# 品牌体验检查 (method.general.brand_route_check.v1)
# ---------------------------------------------------------------------------

def check_retail_vs_brand_experience_boundary(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "retail_vs_brand_experience_boundary"
    text = _get_text(state, structured_data)
    has_retail = any(kw in text for kw in ["销售", "零售", "购买", "转化", "成交"])
    has_brand = any(kw in text for kw in ["品牌", "体验", "沉浸", "故事", "传播"])
    if has_retail and has_brand:
        return _result(
            cid, False, "warning",
            "品牌体验与零售转化之间的逻辑边界混淆",
            action="clarify",
            clarification_hint="品牌体验区域与零售销售区域的比例和边界如何界定？两者的空间逻辑是否一致？",
        )
    return _result(cid, True, "warning", "品牌体验与零售边界未发现明显混淆")


def check_weak_memory_point(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "weak_memory_point"
    text = _get_text(state, structured_data)
    memory_keywords = ["记忆点", "高潮点", "情绪峰值", "打卡", "标志性", "核心场景"]
    has_memory = any(kw in text for kw in memory_keywords)
    if not has_memory:
        return _result(
            cid, False, "warning",
            "缺乏可记忆的空间高潮点或情绪峰值设计",
            action="record",
            clarification_hint="本项目是否有明确的「记忆点」或「打卡场景」设计？访客体验的情绪高潮在哪里？",
        )
    return _result(cid, True, "warning", "已有记忆点或情绪峰值设计描述")


def check_missing_business_metric(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_business_metric"
    text = _get_text(state, structured_data)
    metric_keywords = ["转化率", "kpi", "指标", "品牌认知", "roi", "曝光量", "到访量"]
    has_metric = any(kw in text for kw in metric_keywords)
    if not has_metric:
        return _result(
            cid, False, "warning",
            "未定义转化率、品牌认知等可量化业务目标",
            action="record",
            clarification_hint="本项目有哪些可量化的商业目标（如转化率、到访量、品牌曝光量）？",
        )
    return _result(cid, True, "warning", "已有可量化业务目标描述")


# ---------------------------------------------------------------------------
# 办公检查 (method.general.organization_check.v1)
# ---------------------------------------------------------------------------

def check_display_vs_work_efficiency(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "display_vs_work_efficiency"
    text = _get_text(state, structured_data)
    has_display = any(kw in text for kw in ["展示", "形象", "门面", "品牌墙", "接待区"])
    has_work = any(kw in text for kw in ["工位", "办公", "工作效率", "专注", "工作区"])
    if has_display and has_work:
        return _result(
            cid, False, "warning",
            "展示性设计与日常工作效率之间存在潜在冲突",
            action="clarify",
            clarification_hint="展示形象区域与日常工作区域如何在空间上隔离？形象展示是否会干扰日常办公效率？",
        )
    return _result(cid, True, "warning", "展示区与工作区冲突未发现明显问题")


def check_collaboration_focus_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "collaboration_focus_conflict"
    text = _get_text(state, structured_data)
    has_collab = any(kw in text for kw in ["协作", "开放", "交流区", "讨论", "团队"])
    has_focus = any(kw in text for kw in ["专注", "独立", "安静", "电话间", "专注舱"])
    if has_collab and has_focus:
        return _result(
            cid, False, "warning",
            "协作区与专注区之间存在声学/视线冲突风险",
            action="clarify",
            clarification_hint="协作讨论区与专注工作区之间如何做声学隔离？视线干扰如何控制？",
        )
    return _result(cid, True, "warning", "协作区与专注区冲突未发现明显问题")


# ---------------------------------------------------------------------------
# 居住检查 (method.general.life_pattern_check.v1)
# ---------------------------------------------------------------------------

def check_missing_household_member(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_household_member"
    text = _get_text(state, structured_data)
    member_keywords = ["家庭成员", "几口人", "老人", "孩子", "夫妻", "单身", "合租", "室友"]
    has_members = any(kw in text for kw in member_keywords)
    if not has_members:
        return _result(
            cid, False, "error",
            "家庭成员未完整定义，空间分配存在盲区",
            action="clarify",
            clarification_hint="家庭成员组成是什么？（如：夫妻+老人+孩子）各成员的生活习惯和空间需求有何不同？",
        )
    return _result(cid, True, "warning", "家庭成员信息已被提及")


def check_privacy_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "privacy_conflict"
    text = _get_text(state, structured_data)
    conflict_keywords = ["老人", "孩子", "青少年", "客房", "工作在家", "访客"]
    member_count = sum(1 for kw in conflict_keywords if kw in text)
    if member_count >= 2:
        has_privacy_design = any(kw in text for kw in ["隐私", "独立卫浴", "独立卧室", "套间"])
        if not has_privacy_design:
            return _result(
                cid, False, "warning",
                "家庭内部不同成员的隐私需求可能存在冲突",
                action="clarify",
                clarification_hint="不同家庭成员（如老人与青少年、访客与家人）之间如何保障各自的隐私空间？",
            )
    return _result(cid, True, "warning", "居住隐私冲突未发现明显问题")


def check_maintenance_gap(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "maintenance_gap"
    text = _get_text(state, structured_data)
    maintenance_keywords = ["维护", "保养", "清洁", "好打理", "耐用", "长期"]
    has_maintenance = any(kw in text for kw in maintenance_keywords)
    if not has_maintenance:
        return _result(
            cid, False, "warning",
            "方案未考虑长期维护可行性",
            action="record",
            clarification_hint="方案材料、设备、绿植等的长期维护成本和难度是否在可接受范围内？",
        )
    return _result(cid, True, "warning", "已有维护可行性考虑")


# ---------------------------------------------------------------------------
# 乡建检查 (method.general.public_value_check.v1)
# ---------------------------------------------------------------------------

def check_hospitality_vs_rural_construction_boundary(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "hospitality_vs_rural_construction_boundary"
    text = _get_text(state, structured_data)
    has_hospitality = any(kw in text for kw in ["民宿", "旅游", "民宿开发", "度假"])
    has_public = any(kw in text for kw in ["公共空间", "村民", "社区", "公共价值", "乡建"])
    if has_hospitality and has_public:
        return _result(
            cid, False, "warning",
            "民宿开发逻辑与乡建公共价值逻辑的边界混淆",
            action="clarify",
            clarification_hint="商业民宿部分与公共空间部分如何在权属、运营和空间上明确边界？",
        )
    return _result(cid, True, "warning", "民宿与公共价值边界未发现明显混淆")


def check_stakeholder_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "stakeholder_conflict"
    text = _get_text(state, structured_data)
    stakeholders = []
    if any(kw in text for kw in ["村集体", "村委", "村民"]):
        stakeholders.append("村集体")
    if any(kw in text for kw in ["运营方", "运营商", "投资方"]):
        stakeholders.append("运营方")
    if any(kw in text for kw in ["设计方", "设计师", "建筑师"]):
        stakeholders.append("设计方")
    if len(stakeholders) >= 2:
        return _result(
            cid, False, "warning",
            f"多方利益主体（{'、'.join(stakeholders)}）之间的冲突未被明确处理",
            action="clarify",
            clarification_hint=f"{'、'.join(stakeholders)}之间在决策权、利益分配、空间使用上是否有明确协议？",
        )
    return _result(cid, True, "warning", "利益主体冲突未发现明显问题")


def check_governance_gap(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "governance_gap"
    text = _get_text(state, structured_data)
    governance_keywords = ["运营治理", "管理方案", "后期运营", "可持续运营", "物业", "托管"]
    has_governance = any(kw in text for kw in governance_keywords)
    if not has_governance:
        return _result(
            cid, False, "warning",
            "运营治理方案缺失，建成后可能无法可持续运转",
            action="record",
            clarification_hint="项目建成后由谁运营管理？运营收益如何分配？是否有长期可持续的治理方案？",
        )
    return _result(cid, True, "warning", "已有运营治理相关描述")


# ---------------------------------------------------------------------------
# 精神/宗教检查 (method.general.boundary_and_taboo_check.v1)
# ---------------------------------------------------------------------------

def check_sacred_boundary_blur(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "sacred_boundary_blur"
    text = _get_text(state, structured_data)
    sacred_keywords = ["神圣", "圣殿", "祭坛", "圣堂", "圣域", "神龛"]
    secular_keywords = ["餐饮", "商店", "展览", "游客", "参观", "商业"]
    has_sacred = any(kw in text for kw in sacred_keywords)
    has_secular = any(kw in text for kw in secular_keywords)
    if has_sacred and has_secular:
        has_boundary = any(kw in text for kw in ["边界", "隔离", "缓冲", "过渡", "门槛"])
        if not has_boundary:
            return _result(
                cid, False, "error",
                "神圣边界未被明确，世俗与神圣空间混同",
                action="clarify",
                clarification_hint="神圣空间与世俗/商业空间之间如何设置明确的空间边界和过渡仪式？",
            )
    return _result(cid, True, "warning", "神圣边界未发现明显混同")


def check_surface_style_replacing_ritual_logic(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "surface_style_replacing_ritual_logic"
    text = _get_text(state, structured_data)
    style_keywords = ["禅意", "禅风", "静谧", "东方美学", "侘寂", "极简"]
    ritual_keywords = ["仪式", "礼仪", "流程", "序列", "进入方式", "祭祀"]
    has_style = any(kw in text for kw in style_keywords)
    has_ritual = any(kw in text for kw in ritual_keywords)
    if has_style and not has_ritual:
        return _result(
            cid, False, "warning",
            "风格化设计描述丰富但仪式逻辑缺失，存在以表面风格替代仪式深度的风险",
            action="clarify",
            clarification_hint="本项目的核心仪式序列是什么？空间如何引导使用者完成仪式性行为？",
        )
    return _result(cid, True, "warning", "仪式逻辑未发现被表面风格替代")


def check_access_taboo_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "access_taboo_conflict"
    text = _get_text(state, structured_data)
    taboo_keywords = ["禁区", "禁忌", "不可入", "限制进入", "禁止", "专属区"]
    access_keywords = ["参观路径", "访客动线", "游览路线", "开放"]
    has_taboo = any(kw in text for kw in taboo_keywords)
    has_open_access = any(kw in text for kw in access_keywords)
    if has_taboo and has_open_access:
        return _result(
            cid, False, "error",
            "访客路径与禁入禁忌边界可能发生冲突",
            action="clarify",
            clarification_hint="哪些区域对访客开放、哪些区域完全禁入？禁忌边界如何通过空间设计来实现？",
        )
    return _result(cid, True, "warning", "访客路径与禁忌边界未发现明显冲突")


def check_silence_gathering_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "silence_gathering_conflict"
    text = _get_text(state, structured_data)
    has_silence = any(kw in text for kw in ["静默", "冥想", "禅修", "安静", "独处"])
    has_gathering = any(kw in text for kw in ["聚集", "集会", "仪式", "祈祷", "群体活动"])
    if has_silence and has_gathering:
        has_separation = any(kw in text for kw in ["隔断", "分区", "声学", "隔音", "边界"])
        if not has_separation:
            return _result(
                cid, False, "warning",
                "静默区与聚集区之间缺乏适当隔断",
                action="clarify",
                clarification_hint="静默冥想区域与集体仪式聚集区之间如何做声学和视线隔离？",
            )
    return _result(cid, True, "warning", "静默区与聚集区冲突未发现明显问题")


# ---------------------------------------------------------------------------
# 商业零售检查 (method.general.retail_check.v1)
# ---------------------------------------------------------------------------

def check_missing_conversion_metric(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_conversion_metric"
    text = _get_text(state, structured_data)
    metric_keywords = ["转化率", "坪效", "销售额", "销售目标", "kpi"]
    has_metric = any(kw in text for kw in metric_keywords)
    if not has_metric:
        return _result(
            cid, False, "warning",
            "零售项目缺乏明确的转化率/坪效量化目标",
            action="record",
            clarification_hint="本项目的目标坪效或转化率是多少？关键的商业成功指标如何衡量？",
        )
    return _result(cid, True, "warning", "已有转化指标描述")


def check_display_vs_navigation_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "display_vs_navigation_conflict"
    text = _get_text(state, structured_data)
    has_rich_display = any(kw in text for kw in ["丰富陈列", "多品类", "高密度", "满铺"])
    has_navigation = any(kw in text for kw in ["导视", "导流", "动线清晰", "易找"])
    if has_rich_display and not has_navigation:
        return _result(
            cid, False, "warning",
            "陈列丰富但缺乏清晰导视设计，可能导致访客迷失",
            action="clarify",
            clarification_hint="高密度陈列环境中如何保证访客导向清晰？导视系统和主动线如何设计？",
        )
    return _result(cid, True, "warning", "陈列与导视未发现明显冲突")


def check_backstage_underestimated(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "backstage_underestimated"
    text = _get_text(state, structured_data)
    has_backstage = any(kw in text for kw in ["仓储", "后台", "库房", "补货", "后勤"])
    if not has_backstage:
        return _result(
            cid, False, "warning",
            "零售后台（仓储/补货/后勤）可能被低估或遗漏",
            action="record",
            clarification_hint="仓储空间面积比例是否合理？补货动线是否与顾客动线分离？",
        )
    return _result(cid, True, "warning", "后台空间已被提及")


# ---------------------------------------------------------------------------
# 教育设施检查 (method.general.educational_check.v1)
# ---------------------------------------------------------------------------

def check_missing_pedagogy_model(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_pedagogy_model"
    text = _get_text(state, structured_data)
    pedagogy_keywords = ["教学模式", "教法", "课程", "探究式", "互动式", "传统课堂", "工作坊"]
    has_pedagogy = any(kw in text for kw in pedagogy_keywords)
    if not has_pedagogy:
        return _result(
            cid, False, "error",
            "教学模式未被定义，空间设计缺乏依据",
            action="clarify",
            clarification_hint="本项目采用什么教学模式？（如传统讲授/探究式/工作坊/混合式）不同教学模式对空间的要求有本质差异。",
        )
    return _result(cid, True, "warning", "教学模式已被描述")


def check_safety_constraint_gap(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "safety_constraint_gap"
    text = _get_text(state, structured_data)
    safety_keywords = ["安全", "监管", "视线", "护栏", "紧急疏散", "儿童安全"]
    has_safety = any(kw in text for kw in safety_keywords)
    if not has_safety:
        return _result(
            cid, False, "error",
            "教育设施安全监管与儿童安全约束未被纳入方案",
            action="clarify",
            clarification_hint="教师对学生的视线监管如何保障？儿童活动区的安全护栏、疏散路径是否符合规范？",
        )
    return _result(cid, True, "warning", "安全约束已被提及")


def check_acoustic_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "acoustic_conflict"
    text = _get_text(state, structured_data)
    noisy_keywords = ["体育馆", "音乐室", "排练厅", "报告厅", "操场"]
    quiet_keywords = ["图书馆", "自习室", "专注学习", "安静"]
    has_noisy = any(kw in text for kw in noisy_keywords)
    has_quiet = any(kw in text for kw in quiet_keywords)
    if has_noisy and has_quiet:
        has_separation = any(kw in text for kw in ["隔声", "隔音", "分区", "声学"])
        if not has_separation:
            return _result(
                cid, False, "warning",
                "高噪声区域（体育/音乐）与安静学习区之间缺乏声学隔离设计",
                action="clarify",
                clarification_hint="体育馆/音乐室等高噪声区与图书馆/自习室等安静区之间如何做声学分区？",
            )
    return _result(cid, True, "warning", "声学冲突未发现明显问题")


# ---------------------------------------------------------------------------
# 文化展陈检查 (method.general.public_value_check.v1 for public_cultural)
# ---------------------------------------------------------------------------

def check_missing_public_mission(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "missing_public_mission"
    text = _get_text(state, structured_data)
    mission_keywords = ["公共使命", "公益", "公众服务", "文化传播", "教育使命"]
    has_mission = any(kw in text for kw in mission_keywords)
    if not has_mission:
        return _result(
            cid, False, "warning",
            "公共文化机构的公共使命未被明确定义",
            action="clarify",
            clarification_hint="本文化机构的核心公共使命是什么？服务的主要公众群体和社会价值目标是什么？",
        )
    return _result(cid, True, "warning", "公共使命已被描述")


def check_content_strategy_undefined(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "content_strategy_undefined"
    text = _get_text(state, structured_data)
    content_keywords = ["藏品", "展品", "内容策略", "策展", "主题", "叙事线"]
    has_content = any(kw in text for kw in content_keywords)
    if not has_content:
        return _result(
            cid, False, "error",
            "内容策略（藏品/展品/主题）未被定义，空间无从设计",
            action="clarify",
            clarification_hint="本场馆展示什么内容？藏品/展品的体量、性质和展示要求是什么？核心叙事主题是什么？",
        )
    return _result(cid, True, "warning", "内容策略已被描述")


# ---------------------------------------------------------------------------
# 工业改造检查 (method.general.retrofit_check.v1)
# ---------------------------------------------------------------------------

def check_structural_assessment_missing(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "structural_assessment_missing"
    text = _get_text(state, structured_data)
    struct_keywords = ["结构评估", "结构检测", "承重", "结构安全", "原有结构"]
    has_struct = any(kw in text for kw in struct_keywords)
    if not has_struct:
        return _result(
            cid, False, "error",
            "既有结构安全评估未被前置确认",
            action="clarify",
            clarification_hint="改造前是否已完成既有结构安全评估？承重墙、楼板荷载等是否满足新用途要求？",
        )
    return _result(cid, True, "warning", "结构评估已被提及")


def check_environmental_clearance_gap(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "environmental_clearance_gap"
    text = _get_text(state, structured_data)
    env_keywords = ["环保", "污染", "土壤检测", "环境修复", "危废", "石棉"]
    has_env = any(kw in text for kw in env_keywords)
    if not has_env:
        return _result(
            cid, False, "warning",
            "工业遗址环境合规清查可能未被确认",
            action="record",
            clarification_hint="原工业用地是否存在土壤污染或危废遗留？是否需要环境修复才能进行改造？",
        )
    return _result(cid, True, "warning", "环境合规已被提及")


def check_heritage_vs_program_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "heritage_vs_program_conflict"
    text = _get_text(state, structured_data)
    heritage_keywords = ["保留", "保护", "工业遗存", "历史风貌", "修旧如旧"]
    new_program_keywords = ["新功能", "改造为", "转变为", "新用途"]
    has_heritage = any(kw in text for kw in heritage_keywords)
    has_new = any(kw in text for kw in new_program_keywords)
    if has_heritage and has_new:
        return _result(
            cid, False, "warning",
            "历史风貌保护与新功能植入之间存在潜在冲突",
            action="clarify",
            clarification_hint="哪些历史元素必须保留？新功能的空间需求与保留要求之间如何取得平衡？",
        )
    return _result(cid, True, "warning", "历史保护与新程序冲突未发现明显问题")


# ---------------------------------------------------------------------------
# 居住改造检查 (method.general.renovation_check.v1)
# ---------------------------------------------------------------------------

def check_existing_structure_constraint(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "existing_structure_constraint"
    text = _get_text(state, structured_data)
    constraint_keywords = ["承重墙", "原有结构", "梁柱", "管线", "结构限制"]
    has_constraint = any(kw in text for kw in constraint_keywords)
    if not has_constraint:
        return _result(
            cid, False, "error",
            "既有建筑结构约束未被前置确认",
            action="clarify",
            clarification_hint="是否已确认哪些墙体/柱子不可拆改？原有管线位置是否已排查？",
        )
    return _result(cid, True, "warning", "结构约束已被提及")


def check_mep_relocation_gap(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "mep_relocation_gap"
    text = _get_text(state, structured_data)
    mep_keywords = ["水电", "管线", "暖通", "给排水", "强弱电", "改管"]
    has_mep = any(kw in text for kw in mep_keywords)
    if not has_mep:
        return _result(
            cid, False, "warning",
            "机电管线改造方案未被前置考虑",
            action="record",
            clarification_hint="水电管线是否需要大幅改动？机电改造的复杂度是否已纳入预算和工期？",
        )
    return _result(cid, True, "warning", "机电管线已被提及")


def check_no_interruption_construction(state: StateDict, structured_data: StructuredData) -> CheckResult:
    cid = "no_interruption_construction"
    text = _get_text(state, structured_data)
    living_keywords = ["边住边改", "不搬出", "继续居住", "不中断"]
    if any(kw in text for kw in living_keywords):
        return _result(
            cid, False, "warning",
            "居住不中断施工对噪声、粉尘和安全管控要求极高",
            action="clarify",
            clarification_hint="施工期间业主居住在内，如何分区隔离施工区域？噪声和粉尘如何控制？施工时段是否有限制？",
        )
    return _result(cid, True, "warning", "未发现居住不中断施工的高风险信号")


# ---------------------------------------------------------------------------
# commercial_dining 检查函数
# ---------------------------------------------------------------------------

def check_front_back_ratio_imbalance(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """前厅与后厨面积比例失衡检查"""
    cid = "front_back_ratio_imbalance"
    text = _get_text(state, structured_data)
    # 若明确只强调座位数但没提到厨房面积/规模，判定为高风险
    has_seating = any(kw in text for kw in ["座位", "餐位", "翻台", "容纳"])
    has_kitchen = any(kw in text for kw in ["厨房", "后厨", "备餐", "操作间", "洗碗"])
    if has_seating and not has_kitchen:
        return _result(
            cid, False, "error",
            "仅描述了座位/翻台目标，未提及后厨规模，存在前厅后厨比例严重失衡的风险",
            action="clarify",
            clarification_hint="当前方案的后厨面积与前厅座位数的比例是多少？厨房出菜能力是否能支撑设计容量？",
        )
    return _result(cid, True, "error", "未检测到明显的前厅后厨比例失衡信号")


def check_turnover_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """翻台率与空间体验目标冲突检查"""
    cid = "turnover_conflict"
    text = _get_text(state, structured_data)
    high_turnover = any(kw in text for kw in ["翻台", "快餐", "高翻台", "快速就餐"])
    high_experience = any(kw in text for kw in ["沉浸", "慢餐", "体验", "高端", "品质感", "仪式感"])
    if high_turnover and high_experience:
        return _result(
            cid, False, "error",
            "同时追求高翻台效率与高体验沉浸感，两者在空间逻辑和动线设计上存在根本冲突",
            action="clarify",
            clarification_hint="本项目的核心商业逻辑是效率优先（快餐/高翻台）还是体验优先（慢餐/品质感）？两者不能并重，请明确优先级。",
        )
    return _result(cid, True, "error", "未检测到翻台率与体验目标的明显冲突")


def check_kitchen_flow_vs_service_conflict(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """厨房出餐流线与服务流线冲突检查"""
    cid = "kitchen_flow_vs_service_conflict"
    text = _get_text(state, structured_data)
    open_kitchen = any(kw in text for kw in ["明厨", "开放厨房", "半开放"])
    service_conflict = any(kw in text for kw in ["穿越", "动线交叉", "上菜路线"])
    if open_kitchen or service_conflict:
        return _result(
            cid, False, "warning",
            "开放厨房或动线描述中存在出餐流线与服务流线交叉的潜在风险",
            action="clarify",
            clarification_hint="服务员上菜路线是否会穿越备餐/出餐区？高峰期出餐动线和服务动线如何隔离？",
        )
    return _result(cid, True, "warning", "未检测到厨房与服务流线冲突信号")


def check_noise_zone_missing(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """噪声分区设计缺失检查"""
    cid = "noise_zone_missing"
    text = _get_text(state, structured_data)
    noisy_context = any(kw in text for kw in ["包间", "包厢", "宴会", "大厅", "嘈杂", "热闹"])
    quiet_context = any(kw in text for kw in ["安静", "私密", "商务", "情侣", "独立空间"])
    has_acoustic = any(kw in text for kw in ["隔音", "吸声", "噪声", "声学"])
    if (noisy_context and quiet_context) and not has_acoustic:
        return _result(
            cid, False, "warning",
            "项目同时存在嘈杂区（大厅/宴会）和安静区（包间/商务）需求，但未提及噪声隔离方案",
            action="clarify",
            clarification_hint="包间与大厅之间的噪声隔离是否已在设计中考虑？是否需要隔声处理或物理分区？",
        )
    return _result(cid, True, "warning", "未检测到噪声分区缺失的明显信号")


# ---------------------------------------------------------------------------
# landscape_outdoor 检查函数
# ---------------------------------------------------------------------------

def check_seasonal_performance_gap(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """季节性表现缺口检查"""
    cid = "seasonal_performance_gap"
    text = _get_text(state, structured_data)
    outdoor_keywords = any(kw in text for kw in ["户外", "景观", "花园", "广场", "公园", "庭院"])
    seasonal_addressed = any(kw in text for kw in ["四季", "冬季", "夏季", "落叶", "常绿", "季节性"])
    if outdoor_keywords and not seasonal_addressed:
        return _result(
            cid, False, "error",
            "户外/景观项目未提及季节性适应策略，存在冬季或极端天气下空间体验崩溃的风险",
            action="clarify",
            clarification_hint="本项目在冬季/雨季/极端天气下的使用状态是什么？植物选型是否考虑了四季景观变化？",
        )
    return _result(cid, True, "error", "未检测到季节性表现缺口信号")


def check_maintenance_cost_underestimated(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """维护成本低估检查"""
    cid = "maintenance_cost_underestimated"
    text = _get_text(state, structured_data)
    complex_elements = any(kw in text for kw in ["水景", "喷泉", "种植屋面", "攀援植物", "特种植物"])
    maintenance_addressed = any(kw in text for kw in ["维护", "养护", "运维", "维修", "保洁"])
    if complex_elements and not maintenance_addressed:
        return _result(
            cid, False, "warning",
            "项目包含高维护复杂元素（水景/种植屋面/特种植物），但未提及长期养护方案和成本预估",
            action="clarify",
            clarification_hint="水景和复杂植被的年养护费用是否在预算内？业主方是否有专业园丁或养护团队？",
        )
    return _result(cid, True, "warning", "未检测到维护成本低估信号")


def check_safety_barrier_missing(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """安全护栏/安全边界缺失检查"""
    cid = "safety_barrier_missing"
    text = _get_text(state, structured_data)
    high_risk = any(kw in text for kw in ["儿童", "亲子", "老人", "水边", "高差", "台阶", "坡道", "崖"])
    barrier_addressed = any(kw in text for kw in ["护栏", "围栏", "安全边界", "防护", "扶手"])
    if high_risk and not barrier_addressed:
        return _result(
            cid, False, "error",
            "项目存在高风险使用场景（儿童/老人/水边/大高差），但未提及安全护栏或防护设计",
            action="clarify",
            clarification_hint="项目中的水边、高差区域是否已规划护栏或防护边界？儿童活动区的安全分级是否明确？",
        )
    return _result(cid, True, "error", "未检测到安全护栏缺失的高风险信号")


def check_climate_material_mismatch(state: StateDict, structured_data: StructuredData) -> CheckResult:
    """气候与材料适配性冲突检查"""
    cid = "climate_material_mismatch"
    text = _get_text(state, structured_data)
    cold_climate = any(kw in text for kw in ["北方", "寒冷", "东北", "内蒙", "西北", "冻融"])
    hot_humid = any(kw in text for kw in ["华南", "亚热带", "湿热", "广东", "广西", "海南"])
    problematic_material = any(kw in text for kw in ["木材", "实木", "防腐木", "钢结构", "铁艺"])
    climate_check = any(kw in text for kw in ["防冻", "防腐", "镀锌", "耐候", "户外级"])
    if (cold_climate or hot_humid) and problematic_material and not climate_check:
        return _result(
            cid, False, "warning",
            "项目在特定气候条件下使用了对气候敏感的材料，但未提及相应的防护处理",
            action="clarify",
            clarification_hint="所选户外材料是否经过防腐/防冻/耐候处理？在当地气候条件下的预期使用寿命是多少？",
        )
    return _result(cid, True, "warning", "未检测到气候与材料适配性的明显冲突")


# ---------------------------------------------------------------------------
# CHECK_REGISTRY：check_id → 检查函数
# ---------------------------------------------------------------------------

CHECK_REGISTRY: Dict[str, Any] = {
    # 默认兜底 (v2)
    "missing_goal": check_missing_goal,
    "missing_user": check_missing_user,
    "missing_constraints": check_missing_constraints,
    "goal_user_mismatch": check_goal_user_mismatch,
    "scope_overload": check_scope_overload,
    "ambiguity_blocker": check_ambiguity_blocker,
    # 民宿/酒店
    "public_private_conflict": check_public_private_conflict,
    "mixed_audience_conflict": check_mixed_audience_conflict,
    "seasonal_operation_gap": check_seasonal_operation_gap,
    "budget_schedule_overload": check_budget_schedule_overload,
    # 医疗/康养
    "missing_safety_process": check_missing_safety_process,
    "privacy_risk": check_privacy_risk,
    "accessibility_gap": check_accessibility_gap,
    # 品牌体验
    "retail_vs_brand_experience_boundary": check_retail_vs_brand_experience_boundary,
    "weak_memory_point": check_weak_memory_point,
    "missing_business_metric": check_missing_business_metric,
    # 办公
    "display_vs_work_efficiency": check_display_vs_work_efficiency,
    "collaboration_focus_conflict": check_collaboration_focus_conflict,
    # 居住
    "missing_household_member": check_missing_household_member,
    "privacy_conflict": check_privacy_conflict,
    "maintenance_gap": check_maintenance_gap,
    # 乡建
    "hospitality_vs_rural_construction_boundary": check_hospitality_vs_rural_construction_boundary,
    "stakeholder_conflict": check_stakeholder_conflict,
    "governance_gap": check_governance_gap,
    # 精神/宗教
    "sacred_boundary_blur": check_sacred_boundary_blur,
    "surface_style_replacing_ritual_logic": check_surface_style_replacing_ritual_logic,
    "access_taboo_conflict": check_access_taboo_conflict,
    "silence_gathering_conflict": check_silence_gathering_conflict,
    # 商业零售
    "missing_conversion_metric": check_missing_conversion_metric,
    "display_vs_navigation_conflict": check_display_vs_navigation_conflict,
    "backstage_underestimated": check_backstage_underestimated,
    # 教育设施
    "missing_pedagogy_model": check_missing_pedagogy_model,
    "safety_constraint_gap": check_safety_constraint_gap,
    "acoustic_conflict": check_acoustic_conflict,
    # 文化展陈
    "missing_public_mission": check_missing_public_mission,
    "content_strategy_undefined": check_content_strategy_undefined,
    # 工业改造
    "structural_assessment_missing": check_structural_assessment_missing,
    "environmental_clearance_gap": check_environmental_clearance_gap,
    "heritage_vs_program_conflict": check_heritage_vs_program_conflict,
    # 居住改造
    "existing_structure_constraint": check_existing_structure_constraint,
    "mep_relocation_gap": check_mep_relocation_gap,
    "no_interruption_construction": check_no_interruption_construction,
    # 餐饮空间
    "front_back_ratio_imbalance": check_front_back_ratio_imbalance,
    "turnover_conflict": check_turnover_conflict,
    "kitchen_flow_vs_service_conflict": check_kitchen_flow_vs_service_conflict,
    "noise_zone_missing": check_noise_zone_missing,
    # 景观/户外
    "seasonal_performance_gap": check_seasonal_performance_gap,
    "maintenance_cost_underestimated": check_maintenance_cost_underestimated,
    "safety_barrier_missing": check_safety_barrier_missing,
    "climate_material_mismatch": check_climate_material_mismatch,
}


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def run_general_method_checks(
    state: StateDict,
    general_method_profile: Dict[str, Any],
    structured_data: Optional[StructuredData] = None,
) -> Dict[str, Any]:
    """
    执行通用方法论检查。

    Args:
        state: 当前工作流状态
        general_method_profile: 从 project_definition_activation_pack 中取出的 profile
        structured_data: 结构化需求数据（可选，优先使用）

    Returns:
        {
            "profile_id": str,
            "results": List[CheckResult],
            "errors": List[CheckResult],      # severity in (error, blocker)
            "warnings": List[CheckResult],    # severity == warning
            "blockers": List[CheckResult],    # severity == blocker
            "has_blocker": bool,
            "has_error": bool,
            "clarification_hints": List[str],  # 所有建议追问方向
        }
    """
    if structured_data is None:
        agent_results = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst", {})
        structured_data = requirements_result.get("structured_data", {}) or {}

    profile_id = general_method_profile.get("profile_id", "unknown")
    active_checks = general_method_profile.get("active_checks", [])

    results: List[CheckResult] = []
    for check_item in active_checks:
        # active_checks 支持两种格式：
        #   旧格式（v1）：字符串 "check_id"
        #   新格式（v2）：{"check_id": str, "severity": str}
        if isinstance(check_item, dict):
            check_id = check_item.get("check_id", "")
            yaml_severity = check_item.get("severity")  # YAML 中配置的 severity，可覆盖函数默认值
        else:
            check_id = str(check_item)
            yaml_severity = None

        fn = CHECK_REGISTRY.get(check_id)
        if fn is None:
            logger.warning(f"[GeneralMethodChecker] 未找到 check_id={check_id!r} 对应的检查函数，跳过")
            continue
        try:
            result = fn(state, structured_data)
            # 若 YAML 明确配置了 severity，用其覆盖函数返回的默认值
            if yaml_severity and not result["passed"]:
                result["severity"] = yaml_severity
            results.append(result)
            status = "✅ passed" if result["passed"] else f"❌ {result['severity']}"
            logger.debug(f"[GeneralMethodChecker] {check_id}: {status} — {result['message']}")
        except Exception as exc:
            logger.error(f"[GeneralMethodChecker] check_id={check_id} 执行异常: {exc}")

    errors = [r for r in results if not r["passed"] and r["severity"] in ("error", "blocker")]
    warnings = [r for r in results if not r["passed"] and r["severity"] == "warning"]
    blockers = [r for r in results if not r["passed"] and r["severity"] == "blocker"]
    clarification_hints = [
        r["clarification_hint"]
        for r in results
        if not r["passed"] and r.get("clarification_hint")
    ]

    summary = {
        "profile_id": profile_id,
        "results": results,
        "errors": errors,
        "warnings": warnings,
        "blockers": blockers,
        "has_blocker": bool(blockers),
        "has_error": bool(errors),
        "clarification_hints": clarification_hints,
    }

    logger.info(
        f"[GeneralMethodChecker] profile={profile_id} | "
        f"checks={len(results)} | errors={len(errors)} | "
        f"warnings={len(warnings)} | blockers={len(blockers)}"
    )
    return summary
