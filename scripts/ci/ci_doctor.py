#!/usr/bin/env python3
"""Static sanity checks for GitHub Actions workflows."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root is not a mapping")
    return data


def _check(condition: bool, message: str, errors: list[str]) -> None:
    if condition:
        print(f"[OK] {message}")
    else:
        print(f"[FAIL] {message}")
        errors.append(message)


def _on_section(data: dict[str, Any]) -> dict[str, Any]:
    section = data.get("on")
    if isinstance(section, dict):
        return section
    section = data.get(True)
    if isinstance(section, dict):
        return section
    return {}


def main() -> int:
    errors: list[str] = []
    wf_dir = ROOT / ".github" / "workflows"
    ci_path = wf_dir / "ci.yml"
    tests_path = wf_dir / "tests.yml"
    trend_path = wf_dir / "quality-trend.yml"
    branch_audit_path = wf_dir / "branch-protection-audit.yml"
    allowlist_review_path = wf_dir / "security-allowlist-review.yml"
    incident_path = wf_dir / "ops-auto-incident.yml"

    for p in [ci_path, tests_path, trend_path, branch_audit_path, allowlist_review_path, incident_path]:
        _check(p.exists(), f"workflow exists: {p.name}", errors)
    if errors:
        return 1

    ci = _load_yaml(ci_path)
    tests = _load_yaml(tests_path)
    trend = _load_yaml(trend_path)
    branch_audit = _load_yaml(branch_audit_path)
    allowlist_review = _load_yaml(allowlist_review_path)
    incident = _load_yaml(incident_path)

    # CI workflow checks
    ci_on = _on_section(ci)
    ci_jobs = ci.get("jobs", {})
    ci_dispatch = (ci_on.get("workflow_dispatch") or {}).get("inputs", {})
    ci_run_scope = ci_dispatch.get("run_scope", {})
    ci_options = set(ci_run_scope.get("options", []))
    _check(ci_options == {"gate_only", "full_backend", "all"}, "ci run_scope options", errors)
    _check(
        "concurrency" in ci and ci["concurrency"].get("cancel-in-progress") is True, "ci concurrency enabled", errors
    )
    for name in ["changes", "backend-gate", "backend-tests-full", "frontend-tests"]:
        _check(name in ci_jobs, f"ci job exists: {name}", errors)

    ci_raw = ci_path.read_text(encoding="utf-8")
    for test_name in [
        "tests/unit/test_mode_config.py",
        "tests/unit/test_mode_detector.py",
        "tests/unit/test_deliverable_constraint_validation.py",
    ]:
        _check(test_name in ci_raw, f"ci fast gate includes {test_name}", errors)

    # Tests workflow checks
    tests_on = _on_section(tests)
    tests_jobs = tests.get("jobs", {})
    tests_env = tests.get("env", {})
    _check(str(tests_env.get("COVERAGE_MIN_FAST")) == "16", "tests COVERAGE_MIN_FAST=16", errors)
    _check(str(tests_env.get("COVERAGE_MIN_FULL")) == "16", "tests COVERAGE_MIN_FULL=16", errors)

    tests_inputs = (tests_on.get("workflow_dispatch") or {}).get("inputs", {})
    t_options = set((tests_inputs.get("run_scope") or {}).get("options", []))
    _check(t_options == {"fast_only", "full_matrix", "both"}, "tests run_scope options", errors)
    _check("run_flaky" in tests_inputs, "tests workflow has run_flaky input", errors)
    _check("flaky-isolated" in tests_jobs, "tests has flaky-isolated job", errors)
    _check(
        bool((tests_jobs.get("flaky-isolated") or {}).get("continue-on-error")),
        "flaky-isolated is non-blocking",
        errors,
    )

    tests_raw = tests_path.read_text(encoding="utf-8")
    _check("Enforce security baseline" in tests_raw, "tests enforces security baseline", errors)

    # Docs drift check: README_TESTING threshold values should match workflow env
    readme_testing = (ROOT / "README_TESTING.md").read_text(encoding="utf-8")
    fast_doc = re.search(r"COVERAGE_MIN_FAST=(\d+)", readme_testing)
    full_doc = re.search(r"COVERAGE_MIN_FULL=(\d+)", readme_testing)
    _check(fast_doc is not None, "README_TESTING has COVERAGE_MIN_FAST", errors)
    _check(full_doc is not None, "README_TESTING has COVERAGE_MIN_FULL", errors)
    if fast_doc:
        _check(
            fast_doc.group(1) == str(tests_env.get("COVERAGE_MIN_FAST")),
            "README_TESTING COVERAGE_MIN_FAST matches tests.yml",
            errors,
        )
    if full_doc:
        _check(
            full_doc.group(1) == str(tests_env.get("COVERAGE_MIN_FULL")),
            "README_TESTING COVERAGE_MIN_FULL matches tests.yml",
            errors,
        )

    # Docs consistency check: referenced workflow names/files
    _check("Actions > CI" in readme_testing, "README_TESTING references CI workflow name", errors)
    _check(
        "Actions > Automated Tests" in readme_testing,
        "README_TESTING references Automated Tests workflow name",
        errors,
    )
    _check(
        ".github/workflows/quality-trend.yml" in readme_testing,
        "README_TESTING references quality-trend workflow file",
        errors,
    )

    # README command presence check
    readme_main = (ROOT / "README.md").read_text(encoding="utf-8")
    _check(
        "python scripts/ci/ci_doctor.py" in readme_main,
        "README has cross-platform ci_doctor command",
        errors,
    )
    _check(
        "scripts\\ci\\ci_doctor.bat" in readme_main,
        "README has Windows ci_doctor command",
        errors,
    )

    # Trend workflow checks
    trend_on = _on_section(trend)
    _check("schedule" in trend_on, "quality-trend has schedule", errors)
    _check("workflow_dispatch" in trend_on, "quality-trend supports manual trigger", errors)

    # Branch protection audit workflow checks
    branch_on = _on_section(branch_audit)
    _check("schedule" in branch_on, "branch-protection-audit has schedule", errors)
    _check("workflow_dispatch" in branch_on, "branch-protection-audit supports manual trigger", errors)

    # Security allowlist review workflow checks
    allowlist_on = _on_section(allowlist_review)
    _check("schedule" in allowlist_on, "security-allowlist-review has schedule", errors)
    _check("workflow_dispatch" in allowlist_on, "security-allowlist-review supports manual trigger", errors)

    # Ops incident workflow checks
    incident_on = _on_section(incident)
    _check("workflow_run" in incident_on, "ops-auto-incident listens workflow_run", errors)

    report = {
        "ok": len(errors) == 0,
        "errors": errors,
    }
    out = ROOT / "reports" / "ci-doctor-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report written: {out}")

    if errors:
        print(f"CI doctor failed with {len(errors)} issue(s).")
        return 1
    print("CI doctor passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
