#!/usr/bin/env python3
"""Enforce security scan baseline against an allowlist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _load_allowlist(path: Path) -> set[str]:
    allowed: set[str] = set()
    if not path.exists():
        return allowed
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        allowed.add(line)
    return allowed


def _bandit_findings(payload: Any) -> list[dict[str, Any]]:
    results = payload.get("results", []) if isinstance(payload, dict) else []
    out: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("issue_severity", "")).upper()
        if severity not in {"HIGH", "MEDIUM"}:
            continue
        out.append(
            {
                "id": str(item.get("test_id", "UNKNOWN")),
                "file": str(item.get("filename", "UNKNOWN")),
                "severity": severity,
                "text": str(item.get("issue_text", "")),
            }
        )
    return out


def _safety_findings(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("vulnerabilities", [])
    else:
        items = []

    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        vuln_id = item.get("vulnerability_id", item.get("id", "UNKNOWN"))
        package = item.get("package_name", item.get("package", "UNKNOWN"))
        out.append(
            {
                "id": str(vuln_id),
                "package": str(package),
                "spec": str(item.get("affected_versions", "")),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bandit", type=Path, required=True)
    parser.add_argument("--safety", type=Path, required=True)
    parser.add_argument("--allowlist", type=Path, required=True)
    args = parser.parse_args()

    allowlist = _load_allowlist(args.allowlist)
    bandit_payload = _load_json(args.bandit)
    safety_payload = _load_json(args.safety)

    bandit = _bandit_findings(bandit_payload)
    safety = _safety_findings(safety_payload)

    new_bandit = []
    for item in bandit:
        key = f"bandit|{item['id']}|{item['file']}"
        if key not in allowlist:
            new_bandit.append({**item, "allow_key": key})

    new_safety = []
    for item in safety:
        key = f"safety|{item['id']}|{item['package']}"
        if key not in allowlist:
            new_safety.append({**item, "allow_key": key})

    report = {
        "bandit_total_medium_high": len(bandit),
        "safety_total": len(safety),
        "new_bandit": new_bandit,
        "new_safety": new_safety,
    }
    Path("security-baseline-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if new_bandit or new_safety:
        print("Security baseline check failed: new unallowlisted findings detected.")
        print(f"New bandit findings: {len(new_bandit)}")
        print(f"New safety findings: {len(new_safety)}")
        return 1

    print("Security baseline check passed: no new findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
