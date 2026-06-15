"""Build systemic remediation backlog for Scheme Advisor pressure tests."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_GOLDEN = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-190-golden-annotation-base-2026-03-22.json"
)
_DEFAULT_SUGGESTIONS = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-golden-review-batch-01-p0-suggestions-2026-03-22.json"
)
_DEFAULT_PRESSURE_RESULT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-pressure-test-2026-03-22.json"
)
_DEFAULT_JSON_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-systemic-remediation-backlog-2026-03-22.json"
)
_DEFAULT_CSV_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-systemic-remediation-backlog-2026-03-22.csv"
)
_DEFAULT_MD_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-systemic-remediation-backlog-2026-03-22.md"
)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_systemic_remediation_backlog(
    golden_annotation: Mapping[str, Any],
    review_suggestions: Mapping[str, Any] | None = None,
    pressure_result: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    items = [item for item in golden_annotation.get("items", []) or [] if isinstance(item, Mapping)]
    summary = golden_annotation.get("summary") or {}
    family_counts = dict(summary.get("remediation_family_counts") or _count_by(items, "remediation_family"))
    warning_counts = _warning_counts(items)
    governance_signal_counts = _governance_signal_counts(items)
    latest_pressure_summary = _latest_pressure_summary(pressure_result)
    governance_signal_routing = _governance_signal_routing(
        (latest_pressure_summary.get("governance_signal_counts") or governance_signal_counts)
    )
    baseline_drift = _baseline_drift(
        golden_total=int(summary.get("total") or len(items)),
        golden_warning_counts=warning_counts,
        golden_governance_signal_counts=governance_signal_counts,
        pressure_summary=latest_pressure_summary,
    )
    suggestions_summary = (review_suggestions or {}).get("summary") or {}

    backlog_items = [
        _classification_action(family_counts, items, warning_counts),
        _core_tension_action(family_counts, items),
        _ceiling_action(family_counts, items),
        _frontend_language_action(items),
        _registry_governance_action(family_counts, items),
        _knowledge_coverage_action(family_counts, items, warning_counts),
        _activation_lens_action(items, governance_signal_counts),
        _review_workflow_action(suggestions_summary, items),
    ]

    return {
        "schema_version": "scheme_advisor_systemic_remediation_backlog.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_pressure_items": int(summary.get("total") or len(items)),
            "needs_human_review": int(summary.get("needs_human_review") or _count_needs_review(items)),
            "systemic_actions": len(backlog_items),
            "must_not_hardcode_cases": True,
            "family_counts": family_counts,
            "warning_counts": warning_counts,
            "governance_signal_counts": governance_signal_counts,
            "governance_signal_routing": governance_signal_routing,
            "latest_pressure_summary": latest_pressure_summary,
            "baseline_drift": baseline_drift,
            "review_suggestion_summary": suggestions_summary,
        },
        "principles": [
            "不把单个案例写成固定规则；只沉淀跨样本成立的机制。",
            "先识别空间主轴、项目阶段、核心矛盾，再决定输出深度。",
            "专科知识和激活包不能全覆盖时，先走基础空间推理框架；只有专业覆盖不足会影响判断可靠性时才封顶。",
            "模型推断只能进入候选和复核，不得自动进入正式 Registry 或知识库。",
            "前端只展示人话标签，不暴露内部英文枚举和字段名。",
        ],
        "items": backlog_items,
    }


def write_backlog_json(backlog: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(backlog, ensure_ascii=False, indent=2), encoding="utf-8")


def write_backlog_csv(backlog: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(backlog.get("items", []) or [])
    fieldnames = [
        "id",
        "priority",
        "module",
        "governance_mode",
        "decision_inputs",
        "generalization_method",
        "anti_hardcoding_policy",
        "algorithm_verification",
        "risk",
        "mechanism",
        "verification_gate",
        "evidence_count",
        "ui_guardrail",
        "sample_ids",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flattened = dict(row)
            flattened["sample_ids"] = ",".join(str(item) for item in row.get("sample_ids", []) or [])
            flattened["decision_inputs"] = "；".join(str(item) for item in row.get("decision_inputs", []) or [])
            writer.writerow({field: flattened.get(field, "") for field in fieldnames})


def write_backlog_markdown(backlog: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = backlog.get("summary") or {}
    lines = [
        "# 方案高参系统性整改清单",
        "",
        f"- 生成时间：`{backlog.get('generated_at')}`",
        f"- 压测样本：{summary.get('total_pressure_items', 0)}",
        f"- 需人工复核：{summary.get('needs_human_review', 0)}",
        f"- 系统性整改项：{summary.get('systemic_actions', 0)}",
        f"- 禁止个案硬编码：{summary.get('must_not_hardcode_cases')}",
        "",
        "## 原则",
        "",
    ]
    for principle in backlog.get("principles", []) or []:
        lines.append(f"- {principle}")
    drift = summary.get("baseline_drift") or {}
    if drift.get("has_drift"):
        lines.extend(
            [
                "",
                "## 基线差异",
                "",
                f"- 处理策略：`{drift.get('policy')}`",
                f"- 需要人工复核：{drift.get('requires_human_review')}",
                "",
                "| 字段 | Golden 批注 | 最新压测 |",
                "|---|---:|---:|",
            ]
        )
        for item in drift.get("items", []) or []:
            lines.append(
                "| {field} | {golden} | {pressure} |".format(
                    field=_md(item.get("field")),
                    golden=item.get("golden", 0),
                    pressure=item.get("pressure", 0),
                )
            )
    routing = summary.get("governance_signal_routing") or {}
    if routing:
        lines.extend(
            [
                "",
                "## 治理信号路由",
                "",
                "| 信号 | 数量 | 候选类型 | 治理队列 | 允许动作 | 晋级规则 | 验证门槛 |",
                "|---|---:|---|---|---|---|---|",
            ]
        )
        for code, route in sorted(routing.items()):
            lines.append(
                "| {code} | {count} | {kind} | {queue} | {action} | {rule} | {gate} |".format(
                    code=_md(code),
                    count=route.get("count", 0),
                    kind=_md(route.get("candidate_kind")),
                    queue=_md(route.get("review_queue")),
                    action=_md(route.get("allowed_action")),
                    rule=_md(route.get("promotion_rule")),
                    gate=_md(route.get("verification_gate")),
                )
            )
    lines.extend(
        [
            "",
            "## 整改项",
            "",
            "| 优先级 | 模块 | 治理方式 | 风险 | 机制 | 验证方式 | 守门规则 | 证据量 |",
            "|---|---|---|---|---|---|---|---:|",
        ]
    )
    for item in backlog.get("items", []) or []:
        lines.append(
            "| {priority} | {module} | {mode} | {risk} | {mechanism} | {gate} | {guardrail} | {count} |".format(
                priority=_md(item.get("priority")),
                module=_md(item.get("module")),
                mode=_md(item.get("governance_mode")),
                risk=_md(item.get("risk")),
                mechanism=_md(item.get("mechanism")),
                gate=_md(item.get("verification_gate")),
                guardrail=_md(_summarize_guardrail(item.get("ui_guardrail"))),
                count=item.get("evidence_count", 0),
            )
        )
    lines.extend(
        [
            "",
            "## 方法论字段",
            "",
            "| 模块 | 通用输入 | 泛化方法 | 反硬编码策略 | 算法验证 |",
            "|---|---|---|---|---|",
        ]
    )
    for item in backlog.get("items", []) or []:
        lines.append(
            "| {module} | {inputs} | {method} | {policy} | {verification} |".format(
                module=_md(item.get("module")),
                inputs=_md("；".join(str(value) for value in item.get("decision_inputs", []) or [])),
                method=_md(item.get("generalization_method")),
                policy=_md(item.get("anti_hardcoding_policy")),
                verification=_md(item.get("algorithm_verification")),
            )
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_systemic_remediation_artifacts(
    *,
    golden_path: Path = _DEFAULT_GOLDEN,
    suggestions_path: Path = _DEFAULT_SUGGESTIONS,
    pressure_result_path: Path = _DEFAULT_PRESSURE_RESULT,
    json_output: Path = _DEFAULT_JSON_OUTPUT,
    csv_output: Path = _DEFAULT_CSV_OUTPUT,
    markdown_output: Path = _DEFAULT_MD_OUTPUT,
) -> Dict[str, Any]:
    suggestions = load_json(suggestions_path) if suggestions_path.exists() else {}
    pressure_result = load_json(pressure_result_path) if pressure_result_path.exists() else {}
    backlog = build_systemic_remediation_backlog(
        load_json(golden_path),
        suggestions,
        pressure_result=pressure_result,
    )
    write_backlog_json(backlog, json_output)
    write_backlog_csv(backlog, csv_output)
    write_backlog_markdown(backlog, markdown_output)
    return backlog


def _classification_action(
    family_counts: Mapping[str, int],
    items: Iterable[Mapping[str, Any]],
    warning_counts: Mapping[str, int],
) -> Dict[str, Any]:
    evidence_count = (
        int(family_counts.get("住宅身份/家庭关系/情绪修复", 0))
        + int(family_counts.get("类型边界低置信", 0))
        + int(warning_counts.get("low_classification_confidence", 0))
    )
    return _action(
        id="R01",
        priority="P0",
        module="SpaceClassificationService",
        governance_mode="algorithmic_rule",
        risk="空间主轴识别偏移会把用户问题导向错误专题。",
        mechanism="建立空间主轴判定算法：空间载体、使用者身份、经营/家庭/公共目标、阶段和约束分层打分，再输出主类、次类和不确定原因。",
        verification_gate="用 190 条 golden baseline 回归，住宅身份、复合空间、非空间入口不得误入无关类型；低置信必须进入人工复核。",
        evidence_count=evidence_count,
        sample_ids=_sample_ids(items, ["住宅身份/家庭关系/情绪修复", "类型边界低置信"], limit=12),
    )


def _core_tension_action(family_counts: Mapping[str, int], items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    evidence_count = (
        int(family_counts.get("住宅身份/家庭关系/情绪修复", 0))
        + int(family_counts.get("商业运营闭环/效率与体验", 0))
        + int(family_counts.get("文化产业/非遗/农业复合空间", 0))
    )
    return _action(
        id="R02",
        priority="P0",
        module="SchemeAdvisorEntryService",
        governance_mode="algorithmic_rule",
        risk="第一轮响应没有抓住主矛盾，会导致后续追问和方案方向答非所问。",
        mechanism="先抽取核心矛盾：身份表达、家庭关系、商业效率、文化转译、阶段不确定、硬约束冲突；再生成首轮回应和追问。",
        verification_gate="190 条回归中 core_tension 必须优先反映用户真实目标，不得只按类型模板套话。",
        evidence_count=evidence_count,
        sample_ids=_sample_ids(items, ["住宅身份/家庭关系/情绪修复", "商业运营闭环/效率与体验"], limit=12),
    )


def _ceiling_action(family_counts: Mapping[str, int], items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    evidence_count = (
        int(family_counts.get("空间尺度与阶段封顶", 0))
        + int(family_counts.get("非空间类型入口/设计决策论证", 0))
    )
    return _action(
        id="R03",
        priority="P0",
        module="OutputCeilingPolicy",
        governance_mode="algorithmic_rule",
        risk="信息不足或题目不是空间方案时，系统仍可能输出过深、过确定的方案。",
        mechanism="按信息完整度、空间尺度、项目阶段、知识覆盖和风险约束计算输出封顶等级：完整方案、条件方案、策略框架、决策论证、风险提示。",
        verification_gate="190 条回归中缺面积/图纸/阶段/专业覆盖的样本必须降级输出，不得承诺施工级或确定性方案。",
        evidence_count=evidence_count,
        sample_ids=_sample_ids(items, ["空间尺度与阶段封顶", "非空间类型入口/设计决策论证"], limit=12),
    )


def _frontend_language_action(items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    return _action(
        id="R04",
        priority="P0",
        module="FrontendHumanLanguageMapping",
        governance_mode="ui_mapping",
        risk="英文内部字段和工程术语暴露给终端用户，降低可信度和理解效率。",
        mechanism="建立内部枚举到人话标签的映射层：追问标题、选项、风险、空间类型、输出深度都用中文业务语言展示。",
        verification_gate="前端截图和 DOM 文本检查不得出现 heritage value、preservation grade、core_tension 等内部英文字段。",
        evidence_count=len(list(items)),
        ui_guardrail={
            "scope": "terminal_user_visible_copy",
            "violation_policy": "fail_review",
            "forbidden_terms": [
                "heritage value",
                "preservation grade",
                "structural condition",
                "adaptive reuse program",
                "core_tension",
                "project_type",
                "space_type",
                "ontology",
                "context_packet",
                "missing_slots",
                "activation pack",
                "knowledge package",
                "选择判断路径",
                "成立路径",
                "硬约束",
                "取舍边界",
                "风险阈值",
                "预算押注",
                "决策级变量",
            ],
            "required_action": "用中文业务标签替换内部字段名；必要时只在管理后台技术详情中保留原始枚举。",
        },
        sample_ids=[],
    )


def _registry_governance_action(family_counts: Mapping[str, int], items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    evidence_count = int(family_counts.get("常规空间分类复核", 0)) + int(family_counts.get("类型边界低置信", 0))
    return _action(
        id="R05",
        priority="P1",
        module="ProjectTypeRegistry",
        governance_mode="registry_governed",
        risk="空间分类相对稳定，但新增别名、子类和复合类型不能靠代码里临时补词。",
        mechanism="把类型别名、父桶、复合规则和反例样本纳入 Registry 候选池；人工审核后才进入正式分类源。",
        verification_gate="新增类型候选只能改变候选池；批准前 190 条回归不得读取未审核 Registry 事实。",
        evidence_count=evidence_count,
        sample_ids=_sample_ids(items, ["常规空间分类复核", "类型边界低置信"], limit=12),
    )


def _knowledge_coverage_action(
    family_counts: Mapping[str, int],
    items: Iterable[Mapping[str, Any]],
    warning_counts: Mapping[str, int],
) -> Dict[str, Any]:
    evidence_count = int(warning_counts.get("knowledge_gap_ticket", 0)) or sum(int(v) for v in family_counts.values())
    return _action(
        id="R06",
        priority="P1",
        module="KnowledgeCoverageAndRecall",
        governance_mode="review_workflow",
        risk="知识包无法覆盖所有空间时，系统可能把通用推断当专业结论。",
        mechanism="按空间主类、核心矛盾和输出深度先走基础空间推理框架；缺专业知识时输出通用方法论、边界声明和候选知识缺口。",
        verification_gate="专业覆盖不足会影响判断可靠性时才给出封顶原因；不得引用未批准卡片，也不得把通用推断包装成专科结论。",
        evidence_count=evidence_count,
        sample_ids=_sample_ids(items, list(family_counts.keys()), limit=12),
    )


def _activation_lens_action(items: Iterable[Mapping[str, Any]], governance_signal_counts: Mapping[str, int]) -> Dict[str, Any]:
    evidence_count = int(governance_signal_counts.get("activation_pack_candidate", 0)) or len(list(items))
    return _action(
        id="R07",
        priority="P1",
        module="ContextPacketLensActivation",
        governance_mode="algorithmic_rule",
        risk="激活包不能全覆盖所有空间，错误激活会把问题推向错误专业路径。",
        mechanism="用空间主轴、项目阶段、核心矛盾、硬约束和知识覆盖计算 lens 激活分档，而不是按空间名称硬匹配。",
        verification_gate="复合空间样本必须产生多 lens context_packet；低覆盖样本必须 active_light 或 dormant，不得强行专科化。",
        evidence_count=evidence_count,
        sample_ids=[],
    )


def _review_workflow_action(suggestions_summary: Mapping[str, Any], items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    needs_decision = int(suggestions_summary.get("needs_human_decision") or 0)
    total_suggestions = int(suggestions_summary.get("total") or 0)
    return _action(
        id="R08",
        priority="P1",
        module="GoldenReviewWorkflow",
        governance_mode="review_workflow",
        risk="模型建议若直接写入 gold，会把低置信推断固化成系统事实。",
        mechanism="保留 suggested_* 与 gold_expected_* 双轨：机器只给建议，人工确认后 verifier 才能写入 golden 副本。",
        verification_gate="suggestions 中 needs_human_decision 必须保留为空 gold；apply 工具不得覆盖原始 golden 基线。",
        evidence_count=needs_decision or total_suggestions or len(list(items)),
        sample_ids=[],
    )


def _action(**kwargs: Any) -> Dict[str, Any]:
    methodology = _methodology_for_action(str(kwargs.get("id") or ""))
    return {
        **kwargs,
        "decision_inputs": methodology["decision_inputs"],
        "generalization_method": methodology["generalization_method"],
        "anti_hardcoding_policy": "样本编号只作为证据，不得作为运行时分支条件。",
        "algorithm_verification": methodology["algorithm_verification"],
    }


def _methodology_for_action(action_id: str) -> Dict[str, Any]:
    catalog: Dict[str, Dict[str, Any]] = {
        "R01": {
            "decision_inputs": ["空间载体", "使用者身份", "经营/家庭/公共目标", "项目阶段", "硬约束", "知识覆盖等级"],
            "generalization_method": "对输入先做空间主轴分层评分，再输出主类、次类、置信度和不确定原因；新样本只能影响权重和候选池，不能形成单题分支。",
            "algorithm_verification": "190 条模拟问题回归中，空间主轴、复合空间和低置信降级必须稳定；新增候选批准前不得改变正式分类事实。",
        },
        "R02": {
            "decision_inputs": ["用户真实目标", "身份叙事", "经营闭环", "家庭关系", "文化表达", "约束冲突"],
            "generalization_method": "先抽取核心矛盾，再按目标、约束、场景和情绪权重组织首轮回应；追问围绕当前矛盾，而不是固定套用四个标签。",
            "algorithm_verification": "golden baseline 中首轮回应必须覆盖真实目标和主矛盾；不得把商业、住宅、文化项目统一套成模板话术。",
        },
        "R03": {
            "decision_inputs": ["信息完整度", "空间尺度", "项目阶段", "知识覆盖等级", "风险约束"],
            "generalization_method": "按可判断程度计算输出封顶等级，缺面积、图纸、阶段或专业覆盖时只给条件方案或策略框架。",
            "algorithm_verification": "缺关键参数的样本不得输出施工级结论；风险冲突样本必须先声明前提和边界。",
        },
        "R04": {
            "decision_inputs": ["内部字段名", "终端用户界面位置", "业务语义", "管理后台可见范围"],
            "generalization_method": "建立内部枚举到人话标签的统一映射层，终端界面只显示中文业务语义，技术字段只允许在管理后台详情中出现。",
            "algorithm_verification": "用户可见文本守卫脚本必须阻断英文内部字段和工程术语；新增字段必须先登记中文标签。",
        },
        "R05": {
            "decision_inputs": ["类型别名", "父类", "复合类型线索", "反例样本", "审核状态"],
            "generalization_method": "把空间分类作为相对稳定 Registry 治理对象，别名和边界进入候选池，经人工复核后才进入正式分类源。",
            "algorithm_verification": "未审核候选不得参与运行时分类；批准新增类型后必须跑 190 条回归，确认没有挤压既有类型。",
        },
        "R06": {
            "decision_inputs": ["空间主类", "核心矛盾", "知识覆盖等级", "输出深度", "已批准知识卡成熟度"],
            "generalization_method": "知识覆盖不足时先走基础空间推理框架，只输出通用方法论、边界声明和候选缺口；不得把通用推理包装成专科结论。",
            "algorithm_verification": "没有 approved card 或专科包时不得召回未审知识；覆盖不足必须生成知识缺口候选或观察信号。",
        },
        "R07": {
            "decision_inputs": ["空间主轴", "项目阶段", "核心矛盾", "硬约束", "知识覆盖等级", "可用卡片成熟度"],
            "generalization_method": "按输入特征计算 lens 激活分档，复合空间允许多 lens 协同，低覆盖场景降为 active_light 或 dormant。",
            "algorithm_verification": "复合空间样本必须产生多 lens context_packet；低覆盖样本不得强行专科化。",
        },
        "R08": {
            "decision_inputs": ["模型建议", "golden 原值", "置信度", "人工裁决状态", "漂移差异"],
            "generalization_method": "保持 suggested 与 gold 双轨，模型只生成建议；人工批准后才写入 golden 副本和后续回归基线。",
            "algorithm_verification": "apply 工具不得覆盖原始 golden；baseline drift 只报告差异，不自动同步。",
        },
    }
    return catalog.get(
        action_id,
        {
            "decision_inputs": ["输入事实", "风险信号", "审核状态"],
            "generalization_method": "按模块边界抽象为可复用机制，不使用样本编号作为运行时条件。",
            "algorithm_verification": "通过对应模块回归和人工复核验证。",
        },
    )


def _count_by(items: Iterable[Mapping[str, Any]], field: str) -> Counter:
    return Counter(str(item.get(field) or "-") for item in items)


def _warning_counts(items: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        codes = str(item.get("warning_codes") or "")
        for code in ["low_classification_confidence", "coverage_gap", "knowledge_gap_ticket"]:
            if code in codes:
                counts[code] += 1
    return dict(counts)


def _governance_signal_counts(items: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        codes = str(item.get("warning_codes") or "")
        for code in ["activation_pack_candidate"]:
            if code in codes:
                counts[code] += 1
    return dict(counts)


def _latest_pressure_summary(pressure_result: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not pressure_result:
        return {}

    summary = pressure_result.get("summary") or {}
    warning_counts = _pressure_issue_counts(pressure_result, bucket="warning_issues")
    governance_signal_counts = _pressure_issue_counts(pressure_result, bucket="governance_signals")
    if not warning_counts and isinstance(summary.get("warning_counts"), Mapping):
        warning_counts = dict(summary.get("warning_counts") or {})
    if not governance_signal_counts and isinstance(summary.get("governance_signal_counts"), Mapping):
        governance_signal_counts = dict(summary.get("governance_signal_counts") or {})

    return {
        "total": int(summary.get("total") or 0),
        "passed": int(summary.get("passed") or 0),
        "failed": int(summary.get("failed") or 0),
        "with_warnings": int(summary.get("with_warnings") or 0),
        "with_governance_signals": int(summary.get("with_governance_signals") or 0),
        "warning_counts": warning_counts,
        "governance_signal_counts": governance_signal_counts,
    }


def _governance_signal_routing(counts: Mapping[str, int]) -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {
        "coverage_gap": {
            "candidate_kind": "registry_boundary_candidate",
            "review_queue": "space_registry_review",
            "allowed_action": "生成空间分类、别名或边界规则候选，不得直接改正式 Registry。",
            "promotion_rule": "候选聚合 + 人工复核 + 190 条回归通过",
            "verification_gate": "批准前只能影响候选池；批准后必须确认没有挤压既有空间主轴。",
        },
        "knowledge_gap_ticket": {
            "candidate_kind": "knowledge_card_candidate",
            "review_queue": "knowledge_asset_review",
            "allowed_action": "生成候选知识卡或知识包缺口，不得进入 runtime recall。",
            "promotion_rule": "证据链完整 + 适用边界明确 + 人工审核批准",
            "verification_gate": "审核通过前不得被消费链召回；通过后必须登记来源、边界和成熟度。",
        },
        "activation_pack_candidate": {
            "candidate_kind": "activation_pack_candidate",
            "review_queue": "activation_pack_review",
            "allowed_action": "进入激活包候选池，按频次、商业价值和知识成熟度排期。",
            "promotion_rule": "高频聚类 + 范围定义 + 人工批准",
            "verification_gate": "正式上线前必须定义适用/不适用边界、最小知识卡和回归样本。",
        },
        "knowledge_coverage_watch": {
            "candidate_kind": "coverage_watch_signal",
            "review_queue": "coverage_watch_pool",
            "allowed_action": "只进入观察池，累计样本和风险，不直接立项建设专科包。",
            "promotion_rule": "达到频次、风险或商业价值阈值后再转候选",
            "verification_gate": "观察阶段只能影响报告和建设优先级，不得改变运行时事实。",
        },
    }

    routed: Dict[str, Dict[str, Any]] = {}
    for code, count in sorted((counts or {}).items()):
        count_value = int(count or 0)
        if count_value <= 0:
            continue
        metadata = catalog.get(
            str(code),
            {
                "candidate_kind": "governance_signal_candidate",
                "review_queue": "manual_governance_triage",
                "allowed_action": "进入人工治理分诊，不得自动写入正式事实。",
                "promotion_rule": "人工确认信号含义后再选择治理路径",
                "verification_gate": "未知信号必须先定义治理语义和回归验证方式。",
            },
        )
        routed[str(code)] = {
            "count": count_value,
            "must_not_auto_promote": True,
            **metadata,
        }
    return routed


def _pressure_issue_counts(pressure_result: Mapping[str, Any], *, bucket: str) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for item in pressure_result.get("items", []) or []:
        if not isinstance(item, Mapping):
            continue
        for issue in item.get(bucket) or []:
            if isinstance(issue, Mapping) and issue.get("code"):
                counts[str(issue["code"])] += 1
    return dict(counts)


def _baseline_drift(
    *,
    golden_total: int,
    golden_warning_counts: Mapping[str, int],
    golden_governance_signal_counts: Mapping[str, int],
    pressure_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    if not pressure_summary:
        return {
            "has_drift": False,
            "policy": "report_only_never_auto_sync",
            "requires_human_review": False,
            "items": [],
        }

    rows: List[Dict[str, Any]] = []
    _append_drift(rows, "total", golden_total, int(pressure_summary.get("total") or 0))

    pressure_warning_counts = pressure_summary.get("warning_counts") or {}
    for code in sorted(set(golden_warning_counts) | set(pressure_warning_counts)):
        _append_drift(
            rows,
            f"warning_counts.{code}",
            int(golden_warning_counts.get(code) or 0),
            int(pressure_warning_counts.get(code) or 0),
        )

    pressure_governance_counts = pressure_summary.get("governance_signal_counts") or {}
    for code in sorted(set(golden_governance_signal_counts) | set(pressure_governance_counts)):
        _append_drift(
            rows,
            f"governance_signal_counts.{code}",
            int(golden_governance_signal_counts.get(code) or 0),
            int(pressure_governance_counts.get(code) or 0),
        )

    return {
        "has_drift": bool(rows),
        "policy": "report_only_never_auto_sync",
        "requires_human_review": bool(rows),
        "items": rows,
    }


def _append_drift(rows: List[Dict[str, Any]], field: str, golden_value: int, pressure_value: int) -> None:
    if golden_value == pressure_value:
        return
    rows.append({"field": field, "golden": golden_value, "pressure": pressure_value})


def _count_needs_review(items: Iterable[Mapping[str, Any]]) -> int:
    return sum(1 for item in items if str(item.get("needs_human_review") or "").lower() == "yes")


def _sample_ids(items: Iterable[Mapping[str, Any]], families: List[str], *, limit: int) -> List[int]:
    ids: List[int] = []
    family_set = set(families)
    for item in items:
        if item.get("remediation_family") in family_set and item.get("id") is not None:
            ids.append(int(item["id"]))
        if len(ids) >= limit:
            break
    return ids


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _summarize_guardrail(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    terms = value.get("forbidden_terms") or []
    if isinstance(terms, list):
        term_text = "、".join(str(item) for item in terms[:4])
    else:
        term_text = str(terms)
    policy = value.get("violation_policy") or ""
    return f"{policy}: {term_text}" if term_text else str(policy)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Scheme Advisor systemic remediation backlog.")
    parser.add_argument("--golden", type=Path, default=_DEFAULT_GOLDEN)
    parser.add_argument("--suggestions", type=Path, default=_DEFAULT_SUGGESTIONS)
    parser.add_argument("--pressure-result", type=Path, default=_DEFAULT_PRESSURE_RESULT)
    parser.add_argument("--json-output", type=Path, default=_DEFAULT_JSON_OUTPUT)
    parser.add_argument("--csv-output", type=Path, default=_DEFAULT_CSV_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=_DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    backlog = write_systemic_remediation_artifacts(
        golden_path=args.golden,
        suggestions_path=args.suggestions,
        pressure_result_path=args.pressure_result,
        json_output=args.json_output,
        csv_output=args.csv_output,
        markdown_output=args.markdown_output,
    )
    print(json.dumps(backlog["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
