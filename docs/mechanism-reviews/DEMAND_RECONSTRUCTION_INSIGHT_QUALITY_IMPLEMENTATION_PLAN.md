# Demand Reconstruction Insight Quality Implementation Plan

Version: v1.2 implementation status
Updated: 2026-06-20
Scope: demand reconstruction first-screen insight quality

## 1. Problem Statement

The previous demand reconstruction path could read the Q16-style input as a project plus construction-risk problem, while the user expected a human-centered insight:

- `50岁` means life stage, childhood memory, career achievement, hardship, and later-life settlement may matter.
- `背井离乡` means hometown longing, return, recognition, and unresolved relation to place may matter.
- `民居` is not only dwelling and engineering; it may be a container for return and body-mind settlement.
- `室内设计师` means professional identity changes the old/new fusion, control boundary, and lifestyle assumptions.

The implementation goal is not generic empathy. It is evidence-bound insight: the system should notice high-value human signals, preserve them into the first response, and reject shallow capture by style, hard constraints, or generic warmth.

## 2. Implemented Artifacts

- `intelligent_project_analyzer/services/demand_reconstruction_insight_quality.py`
  - detects expected high-value signals from source text and latent model.
  - reports missing signal ids.
  - checks style-over-capture and hard-constraint-over-capture.
  - grades `semantic_pass`, `insight_pass`, `trust_pass`.

- `intelligent_project_analyzer/services/demand_reconstruction_service.py`
  - builds latent model before blueprint generation.
  - evaluates final visible reply and blueprint.
  - attaches `blueprint.insight_quality` and `governance_signals[type=insight_quality_watch]`.
  - expands demand reconstruction entry coverage for the 190-question set.

- `intelligent_project_analyzer/services/demand_reconstruction_insight_protocol.py`
  - LLM prompt now carries `latent_model`.
  - prompt distinguishes empty cliche from evidence-bound emotional/identity judgment.
  - prompt explicitly protects `person_profile`, `evidence_bound_affect`, and `forbidden_capture_paths`.

- `scripts/audit_demand_reconstruction_insight_quality.py`
  - parses numbered question sets.
  - runs local demand reconstruction without external LLM dependency.
  - emits handled rate, quality levels, missing signals, and warning issues.

## 3. Acceptance Checklist

| Requirement | Status | Evidence |
| --- | --- | --- |
| Q16 sample preserves life stage, professional identity, returning-home relation, and dwelling-as-settlement | Done | `tests/services/test_demand_reconstruction_insight_quality_gate.py`; manual Q16 output check |
| Empty style/construction capture is flagged | Done | `tests/unit/test_demand_reconstruction_insight_quality.py` |
| Evidence-bound affect can pass quality gate | Done | `tests/unit/test_demand_reconstruction_insight_quality.py` |
| LLM prompt includes latent model and anti-capture instructions | Done | `tests/unit/test_demand_reconstruction_insight_protocol_prompt.py` |
| Demand reconstruction context exposes latent model | Done | service gate test |
| Blueprint exposes insight quality and governance watch signal | Done | service gate test |
| 190-question simulation set is batch-auditable | Done | audit script test and local audit run |
| 190-question entrance coverage reaches full handled rate | Done | audit result: `190/190 handled`, `unhandled_count=0` |

## 4. Current Q16 Expected Behavior

For input:

`50岁男性室内设计师，背井离乡，想在老家建一栋民居，给出建议`

The first response should not primarily discuss standardized rural construction, style labels, or engineering feasibility. It should reframe the task around:

- career/life stage and professional self-positioning.
- return to hometown and relation to place.
- rural home as a body-mind/family settlement container.
- the tension between designer control and local construction/living reality.
- one high-impact follow-up question about actual residence pattern and role of the house.

Latest manual verification produced `trust_pass`, score `1.0`, and no missing high-value signals.

## 5. Verification Commands

Run before final completion:

```powershell
.\.conda\python.exe -m pytest tests/unit/test_latent_model_contract.py tests/services/test_latent_model_adapter.py tests/unit/test_demand_reconstruction_insight_quality.py tests/services/test_demand_reconstruction_insight_quality_gate.py tests/unit/test_audit_demand_reconstruction_insight_quality_script.py tests/unit/test_demand_reconstruction_insight_protocol_prompt.py tests/services/test_demand_reconstruction_service.py -q
$env:LOGURU_LEVEL='ERROR'
.\.conda\python.exe scripts/audit_demand_reconstruction_insight_quality.py "sf/2026.3.22/模拟问题集合.txt" --output tmp/demand_reconstruction_insight_quality_audit.json
```

## 6. Remaining Risks

- Quality scoring is still a lightweight evaluator. It catches known collapse modes but is not yet a comprehensive semantic judge.
- The 190-question audit proves entrance coverage and mechanical quality fields; it does not prove every response has expert-level depth.
- Existing frontend rendering has not been separately smoke-tested in this step; backend context is present, but UI presentation of internal quality fields is intentionally hidden from card summary.

## 7. Next Step

Verification completed on 2026-06-20: focused latent model, insight quality, prompt, audit, and service tests returned `21 passed`; the 190-question audit returned `190/190 handled`, handled rate `1.0`, unhandled count `0`, with level distribution `insight_pass=187`, `semantic_pass=1`, `trust_pass=2`.

