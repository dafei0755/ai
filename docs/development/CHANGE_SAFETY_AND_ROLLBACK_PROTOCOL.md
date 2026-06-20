# Change Safety And Rollback Protocol

Version: v1.0
Date: 2026-06-20
Status: active guardrail

## Purpose

This protocol prevents verified mechanism work from being lost through branch switches, backup-only commits, broad restore commands, or mixed-lane edits. It is binding for high-risk runtime paths, including demand reconstruction, LLM routing, governance stores, API routes, registries, and shared tests.

## Required Boundary Before Editing

1. Run `git status --short`.
2. Record the active branch with `git branch --show-current`.
3. Identify whether target files already have user or prior-session changes.
4. For important or cross-module work, create a Git checkpoint before editing.
5. Important untracked files must be added to the checkpoint or recorded in a manifest before relying on rollback.
6. If a task touches a core shared file, do not mix unrelated docs, tests, frontend, backend, or cleanup changes in the same commit.

## Backup Branch Rule

A backup branch is only a safety copy. It is not considered implemented until its required changes are merged or cherry-picked into the active work branch and verified there.

Before leaving a backup branch or worktree, run:

```powershell
git branch --show-current
git status --short
git log --oneline -5
```

Then record whether the work is:

- `backup_only`: preserved but not active.
- `ready_to_merge`: verified and waiting to merge.
- `merged_active`: present in the active branch with tests passing.

Do not describe `backup_only` work as implemented.

## Restore And Rollback Discipline

Prefer file-level or hunk-level recovery. Do not use broad destructive commands unless the user explicitly approves and the protected state is known.

Forbidden without explicit approval:

```powershell
git reset --hard
git checkout -- .
git restore .
git clean -fd
git clean -fdx
git stash -u
git stash --all
```

When restoring from an older commit, use exact paths and then run the affected tests. Never restore a whole file over a high-risk runtime path without checking what newer work would be overwritten.

## High-Risk Contract Guard

For demand reconstruction, the current active contract is LLM-first:

```text
user input -> DemandReconstructionService -> LLM Semantic Router -> asset/rule scan -> LLM Final Synthesis -> quality/alignment gates
```

When `DEMAND_RECONSTRUCTION_USE_LLM=1`, missing understanding or synthesis must surface as typed unavailability (`UNDERSTANDING_UNAVAILABLE` / `SYNTHESIS_UNAVAILABLE`) and route-level HTTP 503. Rule fallback is only allowed when the LLM layer is disabled or explicitly in non-required mode.

Any change touching demand reconstruction must run the LLM-first guard tests before completion.

## Verification Minimums

For demand reconstruction runtime changes, run at least:

```powershell
.\.conda\python.exe -m pytest tests/services/test_demand_reconstruction_service.py tests/api/test_scheme_advisor_entry_route.py tests/unit/test_demand_reconstruction_llm_first_contract_guard.py -q
```

If that command is adjusted, record the replacement and why.

## Completion Report

Every high-risk task must end with:

```text
branch:
base_commit:
head_commit:
files_changed:
verification:
backup_or_checkpoint:
residual_risks:
```

A clean `git status --short` after commit is the preferred completion state.