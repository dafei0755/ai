"""Audit demand-reconstruction insight quality over a numbered question set."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from intelligent_project_analyzer.services.demand_reconstruction_service import DemandReconstructionService


_NUMBERED_RE = re.compile(r"(?ms)^\s*(\d+)\.\s*(.*?)(?=^\s*\d+\.\s*|\Z)")


def parse_numbered_questions(text: str) -> List[Tuple[int, str]]:
    """Parse numbered Chinese prompt collections such as `1. ...` blocks."""
    questions: List[Tuple[int, str]] = []
    for match in _NUMBERED_RE.finditer(str(text or "")):
        number = int(match.group(1))
        body = " ".join(line.strip() for line in match.group(2).splitlines() if line.strip())
        if body:
            questions.append((number, body))
    return questions


def audit_questions(questions: List[Tuple[int, str]]) -> Dict[str, Any]:
    service = DemandReconstructionService(require_llm=False)
    items: List[Dict[str, Any]] = []
    handled = 0
    levels: Dict[str, int] = {}
    for number, question in questions:
        result = service.handle_message(
            session={},
            user_message=question,
            in_response_to_card_id=None,
            selected_option_id=None,
        )
        if not result:
            items.append({"number": number, "handled": False, "question": question})
            continue
        handled += 1
        blueprint = result["demand_reconstruction_context"]["blueprint"]
        quality = blueprint.get("insight_quality") or {}
        level = str(quality.get("level") or "unknown")
        levels[level] = levels.get(level, 0) + 1
        items.append(
            {
                "number": number,
                "handled": True,
                "question": question,
                "level": level,
                "score": quality.get("score"),
                "missing_high_value_signals": quality.get("missing_high_value_signals") or [],
                "warning_issues": quality.get("warning_issues") or [],
            }
        )
    total = len(questions)
    return {
        "schema_version": "demand_reconstruction_insight_quality_audit.v1",
        "total": total,
        "handled": handled,
        "handled_rate": handled / total if total else 0,
        "levels": levels,
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    questions = parse_numbered_questions(args.question_file.read_text(encoding="utf-8"))
    report = audit_questions(questions)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
