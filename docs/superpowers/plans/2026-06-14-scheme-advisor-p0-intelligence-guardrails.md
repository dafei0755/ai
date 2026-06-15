# 方案高参 P0 智能底座整改 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把方案高参入口从“固定追问和局部关键词补丁”升级为“空间分类稳定、主矛盾排序、覆盖封顶、人话展示”的通用智能底座。

**Architecture:** 保持现有链路不推翻：`SpaceClassificationService -> scheme_advisor_semantic_axes -> MissingSlotService -> SpaceContextPacketService -> SchemeAdvisorContextIntelligence`。新增或调整的能力必须优先落在 Registry / 配置 / 通用排序函数中，不为单个题目写专用分支。

**Tech Stack:** Python service layer, YAML registries, pytest, existing pressure runner over `sf\2026.3.22\模拟问题集合.txt`.

---

## Implementation Status

Last refreshed: 2026-06-15.

Current evidence shows the P0 guardrails are implemented and under test:

- `tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`: 13 passed.
- `tests/services/test_scheme_advisor_pressure_semantic_axes.py`: 26 passed.
- Combined pressure/backlog/drift/user-copy guardrail tests: 40 passed.
- `scripts/check_terminal_user_copy_guardrails.py`: `violation_count = 0`.
- 190-question pressure run: `total = 190`, `passed = 190`, `failed = 0`.
- Pressure report now includes `output_depth_counts` and `coverage_ceiling_counts`.
- Baseline drift policy remains report-only: golden baselines are not auto-updated.

This plan remains open because P0 is a continuing guardrail track. Future edits should keep adding evidence here instead of replacing systemic mechanisms with single-prompt exceptions.

---

## Scope

本计划只覆盖 P0：防跑偏、防装懂、防露内部字段。茶饮、咖啡或其他空间激活包补充不在本计划内。

## File Structure

- Modify: `intelligent_project_analyzer/config/registries/scheme_advisor_semantic_axes.yaml`
  - 维护通用语义轴、主矛盾权重、面向用户显示标签、错误领域引用 guardrails。
- Create: `intelligent_project_analyzer/config/registries/scheme_advisor_public_labels.yaml`
  - 维护 snake_case / 英文 token 到中文显示词的通用翻译，不放在业务代码里。
- Modify: `intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py`
  - 增加主矛盾排序函数，返回用户问题当前最重要的 1-3 个判断轴。
- Modify: `intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py`
  - 消费主矛盾排序，生成动态追问标题和选项；所有显示文本走 public label。
- Modify: `intelligent_project_analyzer/services/space_context_packet_service.py`
  - 保留并扩展 `coverage_ceiling`，把低置信分类与知识覆盖不足明确传给入口体验层。
- Modify: `intelligent_project_analyzer/services/scheme_advisor_pressure_runner.py`
  - 在 190 题压测中输出主矛盾遗漏、错误领域引用、英文字段泄露等质量指标。
- Modify: `intelligent_project_analyzer/services/scheme_advisor_pressure_backlog.py`
  - 把低置信和覆盖缺口转成候选治理清单，不自动写入正式 Registry。
- Test: `tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`
  - P0 端到端防跑偏测试。
- Test: `tests/fixtures/scheme_advisor_semantic_axes_test.yaml`
  - 轻量 fixture，保证测试不依赖完整生产词库。

---

### Task 1: Add P0 Regression Tests Before Changing Logic

**Files:**
- Create: `tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`

- [ ] **Step 1: Write failing tests for the known P0 problems**

Create tests that encode the system-wide behavior, not one-off answer wording.

```python
from intelligent_project_analyzer.services.scheme_advisor_context_intelligence import (
    SchemeAdvisorContextIntelligence,
)
from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
    evaluate_semantic_alignment,
)


FOUNDER_SEASIDE_VILLA = (
    "项目位于深圳湾一线海景别墅区，业主为第一代创业者，"
    "从草根奋斗至资本成功，对空间的期待既包含成就象征，"
    "也包含家族传承与内心回归。请从一代创业者的精神结构出发，"
    "提出完整室内设计概念。"
)


def _visible_text(packet: dict) -> str:
    parts = []
    for key in ("opening", "summary", "stage_conclusion"):
        value = packet.get(key)
        if isinstance(value, str):
            parts.append(value)
    for round_item in packet.get("question_rounds") or []:
        for page in round_item.get("pages") or []:
            parts.append(str(page.get("title") or ""))
            parts.append(str(page.get("prompt") or ""))
            for option in page.get("options") or []:
                parts.append(str(option.get("label") or ""))
                parts.append(str(option.get("description") or ""))
    return "\n".join(parts)


def test_founder_seaside_villa_prioritizes_identity_and_family_not_urban_renewal():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    visible = _visible_text(packet)

    assert "创业" in visible or "第一代" in visible
    assert "家族" in visible or "传承" in visible
    assert "城市更新" not in visible
    assert "历史建筑" not in visible

    issues = evaluate_semantic_alignment(FOUNDER_SEASIDE_VILLA, visible)
    assert "wrong_domain_reference" not in {issue["code"] for issue in issues}


def test_entry_guidance_does_not_expose_internal_english_keys():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    visible = _visible_text(packet)

    forbidden = [
        "preservation grade",
        "structural condition",
        "heritage value",
        "context_packet",
        "missing_slot",
        "activation_pack",
    ]
    assert not any(item in visible for item in forbidden)


def test_question_titles_are_dynamic_not_fixed_workflow_words():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    visible = _visible_text(packet)

    fixed_titles = ["成立路径", "硬约束", "取舍边界", "选择判断路径"]
    assert not any(title in visible for title in fixed_titles)
```

- [ ] **Step 2: Run tests and verify at least one fails**

Run:

```powershell
pytest tests/services/test_scheme_advisor_p0_intelligence_guardrails.py -q
```

Expected: at least one test fails before implementation if the current runtime still exposes fixed titles, wrong-domain references, or internal keys.

---

### Task 2: Move Public Label Translation Out Of Service Code

**Files:**
- Create: `intelligent_project_analyzer/config/registries/scheme_advisor_public_labels.yaml`
- Modify: `intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py`
- Test: `tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`

- [ ] **Step 1: Add public label registry**

Create the YAML file with token-level labels and exact key labels. This is not a project-specific answer template; it is a display-layer dictionary.

```yaml
version: "v1.0"
description: >
  方案高参用户侧显示标签注册表。内部 key 可以保留英文或 snake_case，
  但进入前端前必须转成中文表达；找不到标签时显示“待确认项”，不暴露原 key。

exact_labels:
  fire_egress_clearance: 消防疏散净距
  kitchen_ventilation_and_exhaust: 厨房排风排烟
  acoustic_comfort_threshold: 声环境舒适底线
  zoning_and_flow_diagram: 分区与动线图示
  queue_pickup_strategy_note: 排队取餐策略说明
  structural_condition: 结构现状
  preservation_grade: 保护等级
  heritage_value: 历史价值

token_labels:
  fire: 消防
  egress: 疏散
  clearance: 净距
  kitchen: 厨房
  ventilation: 排风
  exhaust: 排烟
  acoustic: 声环境
  comfort: 舒适
  threshold: 底线
  zoning: 分区
  flow: 动线
  diagram: 图示
  queue: 排队
  pickup: 取餐
  strategy: 策略
  note: 说明
  structural: 结构
  condition: 现状
  preservation: 保护
  grade: 等级
  heritage: 历史
  value: 价值

fallback_label: 待确认项
```

- [ ] **Step 2: Add failing test for external registry override**

Append to `tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`:

```python
from intelligent_project_analyzer.services.scheme_advisor_context_intelligence import (
    public_label,
)


def test_public_label_translates_known_keys_without_leaking_raw_key():
    assert public_label("fire_egress_clearance") == "消防疏散净距"
    assert public_label("structural_condition") == "结构现状"
    assert public_label("unknown_internal_key") == "待确认项"
```

- [ ] **Step 3: Implement minimal loader**

Add a small loader in `scheme_advisor_context_intelligence.py` or a focused helper file if the service is already too large. The public API should be:

```python
def public_label(value: str) -> str:
    ...
```

Implementation rules:
- exact label wins.
- `_vs_` splits into `A / B`.
- token label can compose Chinese.
- unknown English key returns fallback label.
- existing Chinese text returns itself.

- [ ] **Step 4: Run label tests**

Run:

```powershell
pytest tests/services/test_scheme_advisor_p0_intelligence_guardrails.py::test_public_label_translates_known_keys_without_leaking_raw_key -q
```

Expected: PASS.

---

### Task 3: Add Main-Tension Ranking As A Generic Semantic Function

**Files:**
- Modify: `intelligent_project_analyzer/config/registries/scheme_advisor_semantic_axes.yaml`
- Modify: `intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py`
- Test: `tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`

- [ ] **Step 1: Extend registry with tension weights**

Add a `tension_priority` section:

```yaml
tension_priority:
  identity_expression:
    base_weight: 90
    title: 先确认空间真正要表达什么
    prompt: 这个项目的关键不是先选风格，而是先确认空间要承载的身份、精神和分寸。
  family_legacy:
    base_weight: 86
    title: 先确认家人和来客的关系
    prompt: 需要先判断家庭传承、日常生活和待客场景之间如何分层。
  business_roi:
    base_weight: 88
    title: 先确认生意是否成立
    prompt: 需要先判断租金、客流、投入和回本目标能否支撑空间策略。
  operational_efficiency:
    base_weight: 84
    title: 先确认高峰期怎么运转
    prompt: 需要先判断点单、制作、取餐、排队和后场是否互相打架。
  fire_structure:
    base_weight: 95
    title: 先确认不能突破的条件
    prompt: 消防、结构、机电这类条件不清楚时，只能做条件级判断。
```

- [ ] **Step 2: Add failing test for ranking**

```python
from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
    rank_main_tensions,
)


def test_rank_main_tensions_prefers_founder_identity_and_family_for_villa():
    tensions = rank_main_tensions(FOUNDER_SEASIDE_VILLA)
    ids = [item["id"] for item in tensions[:3]]

    assert "identity_expression" in ids
    assert "family_legacy" in ids
    assert "urban_renewal" not in ids
```

- [ ] **Step 3: Implement `rank_main_tensions`**

Rules:
- derive semantic axes once.
- score matched `founding_drivers`, `critical_constraints`, `subject_profiles`, and `site_resources`.
- use registry weights.
- return sorted objects with `id`, `label`, `title`, `prompt`, `score`, `source_axes`.
- do not create project-specific branches.

- [ ] **Step 4: Run ranking test**

Run:

```powershell
pytest tests/services/test_scheme_advisor_p0_intelligence_guardrails.py::test_rank_main_tensions_prefers_founder_identity_and_family_for_villa -q
```

Expected: PASS.

---

### Task 4: Use Main Tensions To Generate Dynamic Question Pages

**Files:**
- Modify: `intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py`
- Test: `tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`

- [ ] **Step 1: Add failing test for dynamic page titles**

```python
def test_entry_question_pages_use_ranked_tension_titles():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    visible = _visible_text(packet)

    assert "先确认空间真正要表达什么" in visible or "先确认家人和来客的关系" in visible
    assert "城市更新/历史建筑活化最先要证明哪几件事成立" not in visible
```

- [ ] **Step 2: Integrate `rank_main_tensions`**

Inside context intelligence:
- call `rank_main_tensions(user_input)`.
- if ranked tensions exist, first question pages come from tension titles/prompts.
- missing slots still matter, but they should attach under the relevant tension rather than drive a fixed workflow name.
- if no tension is detected, fall back to current missing-slot page logic.

- [ ] **Step 3: Run dynamic page tests**

Run:

```powershell
pytest tests/services/test_scheme_advisor_p0_intelligence_guardrails.py -q
```

Expected: all tests in this file PASS.

---

### Task 5: Make Low-Confidence Classification A Governed Candidate, Not A Silent Path

**Files:**
- Modify: `intelligent_project_analyzer/services/space_context_packet_service.py`
- Modify: `intelligent_project_analyzer/services/scheme_advisor_pressure_backlog.py`
- Test: `tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`
- Test: `tests/services/test_scheme_advisor_pressure_backlog.py`

- [ ] **Step 1: Add test for low-confidence governance field**

Use a synthetic activation packet or monkeypatch classification output so the test is deterministic.

```python
def test_low_confidence_classification_creates_governance_candidate():
    # Build from an activation-shaped dict so the test does not rely on fragile keyword matching.
    activation = {
        "space_classification": {
            "project_type": None,
            "project_type_name": None,
            "confidence": 0.22,
            "confidence_level": "low",
            "status": "low_confidence",
            "secondary_types": ["personal_residential", "commercial_hospitality"],
            "ambiguity": {"reason": "multi_domain_or_abstract_prompt"},
        },
        "project_definition_activation_pack": {"_v18_extensions": {}},
    }

    from intelligent_project_analyzer.services.space_context_packet_service import (
        SpaceContextPacketService,
    )

    packet = SpaceContextPacketService().build_from_activation("复合空间设计", activation)
    candidate = packet["classification"]["ambiguity"].get("governance_candidate")

    assert candidate["requires_human_review"] is True
    assert candidate["candidate_type"] == "project_type_boundary"
    assert candidate["must_not_update_registry_automatically"] is True
```

- [ ] **Step 2: Implement governance candidate field**

Rules:
- if confidence is missing, below threshold, or project_type is missing, attach candidate metadata.
- do not write to `PROJECT_TYPE_REGISTRY`.
- include nearby type IDs and reason.
- make it available to backlog/admin review later.

- [ ] **Step 3: Update pressure backlog aggregation**

Backlog should separate:
- `type_alias_candidates`
- `project_type_boundary_candidates`
- `activation_pack_candidates`
- `knowledge_gap_candidates`

- [ ] **Step 4: Run governance tests**

Run:

```powershell
pytest tests/services/test_scheme_advisor_p0_intelligence_guardrails.py tests/services/test_scheme_advisor_pressure_backlog.py -q
```

Expected: PASS.

---

### Task 6: Upgrade 190-Question Pressure Gate From Pass/Fail To Quality Metrics

**Files:**
- Modify: `intelligent_project_analyzer/services/scheme_advisor_pressure_runner.py`
- Modify: `docs/system-completeness-audit/scheme-advisor-pressure-optimization-backlog-2026-03-22.md`
- Test: `tests/services/test_scheme_advisor_pressure_semantic_axes.py`

- [ ] **Step 1: Add quality metrics to runner output**

Each item should keep:
- `semantic_alignment_issues`
- `question_quality_issues`
- `display_safety_issues`
- `coverage_ceiling_level`
- `governance_candidate_emitted`

- [ ] **Step 2: Add summary counters**

Summary should include:

```json
{
  "wrong_domain_reference": 0,
  "english_key_visible": 0,
  "generic_step_title_visible": 0,
  "core_subject_missing": 0,
  "low_classification_confidence": 0,
  "knowledge_coverage_gap": 0
}
```

Counters may be non-zero during transition, but the report must expose them explicitly.

- [ ] **Step 3: Run 190-question pressure test**

Run:

```powershell
python -m intelligent_project_analyzer.services.scheme_advisor_pressure_runner --input "sf\2026.3.22\模拟问题集合.txt" --output "docs\system-completeness-audit\scheme-advisor-pressure-test-2026-03-22.md" --json-output "docs\system-completeness-audit\scheme-advisor-pressure-test-2026-03-22.json"
```

Expected:
- command exits 0.
- `total` remains 190.
- no item fails schema validation.
- report shows quality counters.

- [ ] **Step 4: Refresh backlog**

Run:

```powershell
python -m intelligent_project_analyzer.services.scheme_advisor_pressure_backlog --input "docs\system-completeness-audit\scheme-advisor-pressure-test-2026-03-22.json" --output "docs\system-completeness-audit\scheme-advisor-pressure-optimization-backlog-2026-03-22.md" --json-output "docs\system-completeness-audit\scheme-advisor-pressure-optimization-backlog-2026-03-22.json"
```

Expected:
- low-confidence candidates are visible as candidates.
- coverage gaps are visible as knowledge/activation-pack candidates.
- no candidate is described as automatically approved.

---

### Task 7: Final Verification

**Files:**
- All files touched in Tasks 1-6.

- [ ] **Step 1: Run focused tests**

```powershell
pytest tests/services/test_scheme_advisor_p0_intelligence_guardrails.py tests/services/test_scheme_advisor_pressure_semantic_axes.py tests/services/test_scheme_advisor_context_intelligence_humanization.py tests/services/test_knowledge_coverage_ceiling.py tests/services/test_scheme_advisor_pressure_backlog.py -q
```

Expected: PASS.

- [ ] **Step 2: Run entry API smoke**

```powershell
pytest tests/api/test_scheme_advisor_entry_route.py -q
```

Expected: PASS.

- [ ] **Step 3: Run 190-question pressure gate**

Use the pressure command from Task 6. Expected summary:
- `total = 190`
- no schema failure
- quality metrics present
- no user-visible internal English key in generated guidance text

- [ ] **Step 4: Inspect git changes**

```powershell
git status --short
git diff -- intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py intelligent_project_analyzer/services/space_context_packet_service.py intelligent_project_analyzer/services/scheme_advisor_pressure_runner.py intelligent_project_analyzer/services/scheme_advisor_pressure_backlog.py
```

Expected:
- changes are limited to P0 guardrails, tests, registries, and generated pressure reports.
- no unrelated frontend layout, crawler, membership, or admin cleanup changes are introduced by this plan.

---

## Acceptance Criteria

- 用户侧不再出现内部英文 key、snake_case、activation pack、context packet 等词。
- 复合项目先按主矛盾排序，不因局部关键词误跳到不相关空间语境。
- 低置信分类进入候选治理，不自动写入正式 Registry。
- 知识覆盖不足时触发封顶，不装作专科覆盖。
- 190 题压力测试保留，并升级为质量指标门槛。
- 所有新增能力通过 Registry / 通用算法实现，不为单个问题写专用分支。

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-06-14-scheme-advisor-p0-intelligence-guardrails.md`. Two execution options:

1. **Subagent-Driven (recommended)** - 每个任务单独执行和复核，适合当前工作树已经较脏的状态。
2. **Inline Execution** - 在当前会话按任务顺序执行，每个任务后跑对应测试。
