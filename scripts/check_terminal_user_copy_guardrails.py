"""Check terminal-user visible frontend copy against governance guardrails."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GUARDRAIL = (
    ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-systemic-remediation-backlog-2026-03-22.json"
)
DEFAULT_FRONTEND_ROOT = ROOT / "frontend-nextjs"
DEFAULT_SCAN_SUBDIRS = ("app", "components")
SOURCE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}
EXCLUDED_PARTS = {"admin", "__tests__", "node_modules", ".next"}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_frontend_guardrail(data: Mapping[str, Any]) -> Dict[str, Any]:
    for item in data.get("items", []) or []:
        if not isinstance(item, Mapping):
            continue
        if item.get("module") != "FrontendHumanLanguageMapping":
            continue
        guardrail = item.get("ui_guardrail")
        if isinstance(guardrail, Mapping):
            return dict(guardrail)
    return {}


def should_scan(path: Path, frontend_root: Path) -> bool:
    try:
        relative = path.relative_to(frontend_root)
    except ValueError:
        relative = path
    parts = set(relative.parts)
    if parts.intersection(EXCLUDED_PARTS):
        return False
    name = path.name
    if ".test." in name or ".spec." in name or ".bak" in name:
        return False
    return path.suffix in SOURCE_EXTENSIONS


def iter_scan_files(frontend_root: Path, scan_subdirs: Iterable[str]) -> Iterable[Path]:
    for subdir in scan_subdirs:
        root = frontend_root / subdir
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and should_scan(path, frontend_root):
                yield path


def iter_visible_segments(text: str) -> Iterable[tuple[int, str]]:
    # JSX text nodes such as <p>visible copy</p>.
    for match in re.finditer(r">([^<>{}]+)<", text, flags=re.MULTILINE):
        segment = match.group(1).strip()
        if segment:
            yield match.start(1), segment

    # String literals often carry button labels, placeholders, and option text.
    for match in re.finditer(r"(['\"])(.*?)\1", text, flags=re.DOTALL):
        segment = match.group(2).strip()
        if _is_nonvisible_machine_literal(text, match.start(2), segment):
            continue
        if segment:
            yield match.start(2), segment


def _is_nonvisible_machine_literal(text: str, start_index: int, segment: str) -> bool:
    """Skip string literals that are clearly internal tokens, not user copy."""

    value = str(segment or "").strip()
    if not re.fullmatch(r"[a-z0-9_.:-]+", value):
        return False
    prefix = text[max(0, start_index - 80):start_index]
    compact_prefix = prefix.rstrip().rstrip("'\"").rstrip()
    if compact_prefix.endswith(("===", "!==", "==", "!=")):
        return True
    if re.search(
        r"\b(id|key|type|source|status|module|card_type|response_mode|missing_slot_action|evidenceStatus)\s*:\s*$",
        compact_prefix,
    ):
        return True
    return False


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def check_frontend_copy(
    *,
    guardrail_path: Path = DEFAULT_GUARDRAIL,
    frontend_root: Path = DEFAULT_FRONTEND_ROOT,
    scan_subdirs: Iterable[str] = DEFAULT_SCAN_SUBDIRS,
) -> Dict[str, Any]:
    guardrail = extract_frontend_guardrail(load_json(guardrail_path))
    forbidden_terms = [str(term) for term in guardrail.get("forbidden_terms", []) or [] if str(term).strip()]
    violations: List[Dict[str, Any]] = []

    for path in iter_scan_files(frontend_root, scan_subdirs):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for offset, segment in iter_visible_segments(text):
            lowered_segment = segment.lower()
            for term in forbidden_terms:
                if term.lower() not in lowered_segment:
                    continue
                relative = path.relative_to(frontend_root).as_posix()
                violations.append(
                    {
                        "path": relative,
                        "line": line_number(text, offset),
                        "term": term,
                        "excerpt": segment[:160],
                    }
                )

    return {
        "schema_version": "terminal_user_copy_guardrail_report.v1",
        "guardrail_scope": guardrail.get("scope", ""),
        "violation_policy": guardrail.get("violation_policy", ""),
        "summary": {
            "forbidden_term_count": len(forbidden_terms),
            "violation_count": len(violations),
        },
        "violations": violations,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check terminal-user visible frontend copy.")
    parser.add_argument("--guardrail", type=Path, default=DEFAULT_GUARDRAIL)
    parser.add_argument("--frontend-root", type=Path, default=DEFAULT_FRONTEND_ROOT)
    parser.add_argument("--scan-subdir", action="append", dest="scan_subdirs")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = check_frontend_copy(
        guardrail_path=args.guardrail,
        frontend_root=args.frontend_root,
        scan_subdirs=args.scan_subdirs or list(DEFAULT_SCAN_SUBDIRS),
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["summary"]["violation_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
