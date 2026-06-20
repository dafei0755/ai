# Latent Variable Unified Contract Implementation Plan

Version: v1.2 implementation status
Updated: 2026-06-20
Scope: demand reconstruction latent-variable substrate

## 1. Goal

Establish a shared latent-variable contract so demand reconstruction can preserve high-value human signals instead of collapsing user input into project type, style, construction, budget, or equipment constraints.

The contract must support:

- person profile: life stage, professional identity, relationship to place, family or role structure.
- evidence-bound affect: emotional or existential language allowed only when tied to source evidence.
- forbidden capture paths: explicit guards against style-over-capture, hard-constraint-over-capture, or other reduction errors.
- uncertainty ledger and decision frontier: what remains unknown and what question changes downstream direction.

## 2. Implemented Artifacts

- `intelligent_project_analyzer/core/latent_model.py`
  - `EvidenceItem`
  - `LatentVariableItem`
  - `LatentModel`
  - validator: inferred/derived/LLM variables must reference existing evidence ids.

- `intelligent_project_analyzer/services/latent_model_adapter.py`
  - builds `latent_model.v1` from source text and demand reconstruction adapter context.
  - preserves the Q16-style signals: `50岁`, `室内设计师`, `背井离乡`, `老家`, `民居`.
  - emits `person_profile`, `existential_job`, `evidence_bound_affect`, `forbidden_capture_paths`.

- `DemandReconstructionService`
  - attaches `adapter_context.latent_model` before blueprint construction.
  - exposes public latent model in `demand_reconstruction_context.adapter_context.latent_model`.

## 3. Acceptance Checklist

| Requirement | Status | Evidence |
| --- | --- | --- |
| Unified model has schema version and typed evidence index | Done | `tests/unit/test_latent_model_contract.py` |
| Inferred latent variables must be evidence-bound | Done | `LatentModel.validate_inferred_variables_are_evidence_bound` |
| Q16-style human signals are preserved as structured profile | Done | `tests/services/test_latent_model_adapter.py` |
| Returning-home / hometown relation is not reduced to construction risk | Done | `existential_job`, `forbidden_capture_paths` adapter output |
| Service carries latent model into demand reconstruction context | Done | `tests/services/test_demand_reconstruction_insight_quality_gate.py` |
| LLM insight prompt receives latent model | Done | `tests/unit/test_demand_reconstruction_insight_protocol_prompt.py` |
| Cross-domain 190-question audit can run against the new contract | Done | `scripts/audit_demand_reconstruction_insight_quality.py` |

## 4. Current Verification

Latest local verification on 2026-06-20:

- Focused latent model, insight quality, prompt, audit, and service tests: `21 passed`, `21 warnings`.
- 190-question audit after entrance expansion: `190/190 handled`, handled rate `1.0`, unhandled count `0`.
- Quality level distribution: `insight_pass=187`, `semantic_pass=1`, `trust_pass=2`.

## 5. Remaining Risks

- The current adapter is deterministic and keyword-assisted. It establishes the contract and prevents known collapse modes, but deeper cross-domain latent extraction still needs stronger semantic extraction rules or LLM-assisted extraction.
- Evidence-bound affect currently verifies presence of evidence references and visible terms; it does not yet grade subtle overreach in long-form LLM prose.
- The original v1.0/v1.1 planning files were absent from the current worktree when this status document was restored, so this file records the current implementable contract and acceptance state.

## 6. Next Step

Run the full focused verification command set after the prompt-layer update, then update this checklist with final results.

