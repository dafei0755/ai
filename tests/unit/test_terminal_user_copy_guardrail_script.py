import json
import subprocess
import sys
from pathlib import Path


def _write_guardrail(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "module": "FrontendHumanLanguageMapping",
                        "ui_guardrail": {
                            "scope": "terminal_user_visible_copy",
                            "violation_policy": "fail_review",
                            "forbidden_terms": [
                            "heritage value",
                            "preservation grade",
                            "context_packet",
                            "missing_slots",
                            "core_tension",
                            ],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_terminal_user_copy_guardrail_flags_visible_internal_terms(tmp_path):
    guardrail = tmp_path / "guardrail.json"
    frontend = tmp_path / "frontend-nextjs"
    page = frontend / "app" / "entry" / "page.tsx"
    page.parent.mkdir(parents=True)
    page.write_text("export default function Page(){ return <p>heritage value</p>; }", encoding="utf-8")
    _write_guardrail(guardrail)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_terminal_user_copy_guardrails.py",
            "--guardrail",
            str(guardrail),
            "--frontend-root",
            str(frontend),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["summary"]["violation_count"] == 1
    assert report["violations"][0]["term"] == "heritage value"
    assert report["violations"][0]["path"].endswith("app/entry/page.tsx")


def test_terminal_user_copy_guardrail_scans_user_facing_components_by_default(tmp_path):
    guardrail = tmp_path / "guardrail.json"
    frontend = tmp_path / "frontend-nextjs"
    component = frontend / "components" / "ConversationMode" / "GuidanceCard.tsx"
    component.parent.mkdir(parents=True)
    component.write_text(
        "export default function GuidanceCard(){ return <span>preservation grade</span>; }",
        encoding="utf-8",
    )
    _write_guardrail(guardrail)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_terminal_user_copy_guardrails.py",
            "--guardrail",
            str(guardrail),
            "--frontend-root",
            str(frontend),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["summary"]["violation_count"] == 1
    assert report["violations"][0]["path"].endswith("components/ConversationMode/GuidanceCard.tsx")


def test_terminal_user_copy_guardrail_ignores_internal_machine_token_strings(tmp_path):
    guardrail = tmp_path / "guardrail.json"
    frontend = tmp_path / "frontend-nextjs"
    component = frontend / "components" / "ConversationMode" / "GuidanceCard.tsx"
    component.parent.mkdir(parents=True)
    component.write_text(
        "export default function GuidanceCard({page}){"
        " const isMissing = page.source === 'context_packet.missing_slots';"
        " return <span>请先补齐关键条件</span>;"
        "}",
        encoding="utf-8",
    )
    _write_guardrail(guardrail)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_terminal_user_copy_guardrails.py",
            "--guardrail",
            str(guardrail),
            "--frontend-root",
            str(frontend),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["summary"]["violation_count"] == 0


def test_terminal_user_copy_guardrail_ignores_code_identifiers_and_admin_files(tmp_path):
    guardrail = tmp_path / "guardrail.json"
    frontend = tmp_path / "frontend-nextjs"
    user_page = frontend / "app" / "entry" / "page.tsx"
    admin_page = frontend / "app" / "admin" / "space-classification" / "page.tsx"
    user_page.parent.mkdir(parents=True)
    admin_page.parent.mkdir(parents=True)
    user_page.write_text("const core_tension = value; export default function Page(){ return <p>主矛盾</p>; }", encoding="utf-8")
    admin_page.write_text("export default function Page(){ return <p>preservation grade</p>; }", encoding="utf-8")
    _write_guardrail(guardrail)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_terminal_user_copy_guardrails.py",
            "--guardrail",
            str(guardrail),
            "--frontend-root",
            str(frontend),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["summary"]["violation_count"] == 0
