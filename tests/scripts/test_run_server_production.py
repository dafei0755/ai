import importlib
from types import SimpleNamespace
from pathlib import Path

import pytest


startup = importlib.import_module("scripts.run_server_production")


def test_occupied_port_with_healthy_backend_is_reused(monkeypatch):
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": True,
            "status": "healthy",
            "url": "http://127.0.0.1:8001/health",
        },
    )

    result = startup.handle_backend_port_conflict()

    assert result["action"] == "adopted"
    assert "8001" in result["message"]


def test_available_port_starts_normally(monkeypatch):
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: False)

    result = startup.handle_backend_port_conflict()

    assert result["action"] == "start"


def test_unhealthy_occupied_port_reports_owner_and_policy(monkeypatch):
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": False,
            "url": "http://127.0.0.1:8001/health",
            "error": "timed out",
        },
    )
    monkeypatch.setattr(
        startup,
        "find_port_owners",
        lambda port: [{"pid": 1234, "name": "python.exe", "command_line": "old server"}],
    )

    with pytest.raises(SystemExit) as exc:
        startup.handle_backend_port_conflict()

    message = str(exc.value)
    assert "PID 1234" in message
    assert "BACKEND_PORT_CONFLICT_POLICY" in message
    assert "http://127.0.0.1:8001/health" in message


def test_unhealthy_repo_backend_restarts_by_default(monkeypatch):
    stopped = []
    owner = {
        "pid": 12032,
        "name": "python.exe",
        "command_line": (
            '"C:\\ProgramData\\anaconda3\\python.exe" -m uvicorn '
            "intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8001"
        ),
    }
    monkeypatch.delenv("BACKEND_PORT_CONFLICT_POLICY", raising=False)
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": False,
            "url": "http://127.0.0.1:8001/health",
            "error": "timed out",
        },
    )
    monkeypatch.setattr(startup, "find_port_owners", lambda port: [owner])
    monkeypatch.setattr(startup, "stop_process", lambda pid: stopped.append(pid))
    monkeypatch.setattr(startup, "wait_until_port_released", lambda host, port: True)

    result = startup.handle_backend_port_conflict()

    assert result["action"] == "restart-owned"
    assert stopped == [12032]


def test_unhealthy_relative_startup_script_restarts_by_default(monkeypatch):
    stopped = []
    owner = {
        "pid": 37968,
        "name": "python.exe",
        "command_line": '"C:\\ProgramData\\anaconda3\\python.exe" -B scripts/run_server_production.py',
    }
    monkeypatch.delenv("BACKEND_PORT_CONFLICT_POLICY", raising=False)
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": False,
            "url": "http://127.0.0.1:8001/health",
            "error": "timed out",
        },
    )
    monkeypatch.setattr(startup, "find_port_owners", lambda port: [owner])
    monkeypatch.setattr(startup, "stop_process", lambda pid: stopped.append(pid))
    monkeypatch.setattr(startup, "wait_until_port_released", lambda host, port: True)

    result = startup.handle_backend_port_conflict()

    assert result["action"] == "restart-owned"
    assert stopped == [37968]


def test_force_restart_owned_restarts_even_when_health_probe_passes(monkeypatch):
    stopped = []
    owner = {
        "pid": 37968,
        "name": "python.exe",
        "command_line": '"C:\\ProgramData\\anaconda3\\python.exe" -B scripts/run_server_production.py',
    }
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": True,
            "url": "http://127.0.0.1:8001/health",
            "status": 200,
        },
    )
    monkeypatch.setattr(startup, "find_port_owners", lambda port: [owner])
    monkeypatch.setattr(startup, "stop_process", lambda pid: stopped.append(pid))
    monkeypatch.setattr(startup, "wait_until_port_released", lambda host, port: True)

    result = startup.handle_backend_port_conflict(force_restart_owned=True)

    assert result["action"] == "restart-owned"
    assert stopped == [37968]


def test_unknown_unhealthy_port_owner_is_never_stopped_by_default(monkeypatch):
    stopped = []
    owner = {
        "pid": 9100,
        "name": "node.exe",
        "command_line": "node other-server.js --port 8001",
    }
    monkeypatch.delenv("BACKEND_PORT_CONFLICT_POLICY", raising=False)
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": False,
            "url": "http://127.0.0.1:8001/health",
            "error": "timed out",
        },
    )
    monkeypatch.setattr(startup, "find_port_owners", lambda port: [owner])
    monkeypatch.setattr(startup, "stop_process", lambda pid: stopped.append(pid))

    with pytest.raises(SystemExit) as exc:
        startup.handle_backend_port_conflict()

    assert stopped == []
    assert "PID 9100" in str(exc.value)


def test_status_report_explains_backend_ownership_and_health(monkeypatch):
    owner = {
        "pid": 12032,
        "name": "python.exe",
        "command_line": "python -m uvicorn intelligent_project_analyzer.api.server:app --port 8001",
    }
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": True,
            "url": "http://127.0.0.1:8001/health",
            "status": 200,
            "body": {"components": {"llm": {"provider": "qwen", "status": "configured"}}},
        },
    )
    monkeypatch.setattr(startup, "find_port_owners", lambda port: [owner])

    report = startup.format_backend_status(startup.collect_backend_status())

    assert "端口: 8001" in report
    assert "健康检查: 通过" in report
    assert "LLM: qwen/configured" in report
    assert "本项目后端: 是" in report


def test_status_report_does_not_mislabel_healthy_backend_when_process_details_are_unavailable(monkeypatch):
    owner = {"pid": 37968, "name": "", "command_line": ""}
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": True,
            "url": "http://127.0.0.1:8001/health",
            "status": 200,
            "body": {"components": {"llm": {"provider": "qwen", "status": "configured"}}},
        },
    )
    monkeypatch.setattr(startup, "find_port_owners", lambda port: [owner])

    report = startup.format_backend_status(startup.collect_backend_status())

    assert "可复用后端: 是" in report
    assert "本项目后端: 未识别" in report


def test_restart_owned_policy_stops_repo_owned_backend(monkeypatch):
    stopped = []
    owner = {
        "pid": 1234,
        "name": "python.exe",
        "command_line": str(Path.cwd() / "scripts" / "run_server_production.py"),
    }
    monkeypatch.setenv("BACKEND_PORT_CONFLICT_POLICY", "restart-owned")
    monkeypatch.setattr(startup, "get_backend_host", lambda: "0.0.0.0")
    monkeypatch.setattr(startup, "get_backend_port", lambda: 8001)
    monkeypatch.setattr(startup, "is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(
        startup,
        "probe_existing_backend_health",
        lambda host, port: {
            "ok": False,
            "url": "http://127.0.0.1:8001/health",
            "error": "timed out",
        },
    )
    monkeypatch.setattr(startup, "find_port_owners", lambda port: [owner])
    monkeypatch.setattr(startup, "is_owned_backend_process", lambda process, repo_root: True)
    monkeypatch.setattr(startup, "stop_process", lambda pid: stopped.append(pid))
    monkeypatch.setattr(startup, "wait_until_port_released", lambda host, port: True)

    result = startup.handle_backend_port_conflict()

    assert result["action"] == "restart-owned"
    assert stopped == [1234]


def test_main_frontend_defaults_match_backend_port():
    api_ts = Path("frontend-nextjs/lib/api.ts").read_text(encoding="utf-8")
    analysis_page = Path("frontend-nextjs/app/analysis/[sessionId]/page.tsx").read_text(
        encoding="utf-8"
    )
    next_config = Path("frontend-nextjs/next.config.mjs").read_text(encoding="utf-8")

    assert "http://127.0.0.1:8000" not in api_ts
    assert "http://127.0.0.1:8000" not in analysis_page
    assert "http://127.0.0.1:8000" not in next_config
    assert "const API_BASE_URL = configuredApiUrl" in api_ts
    assert "http://127.0.0.1:8001" in analysis_page
    assert "http://127.0.0.1:8001" in next_config


def test_current_docs_and_backend_defaults_do_not_point_to_old_backend_port():
    current_paths = [
        Path("README.md"),
        Path("docs/API.md"),
        Path("frontend-nextjs/README.md"),
        Path("frontend-nextjs/STARTUP_GUIDE.md"),
        Path("frontend-nextjs/start.bat"),
        Path("intelligent_project_analyzer/api/client.py"),
        Path("intelligent_project_analyzer/settings.py"),
    ]

    for path in current_paths:
        content = path.read_text(encoding="utf-8")
        assert "localhost:8000" not in content, path
        assert "127.0.0.1:8000" not in content, path


def test_default_backend_port_matches_frontend_proxy(monkeypatch):
    monkeypatch.delenv("BACKEND_PORT", raising=False)

    assert startup.get_backend_port() == 8001


def test_windows_process_info_falls_back_to_tasklist_when_cim_is_denied(monkeypatch):
    def fake_run(command, **kwargs):
        if command[0] == "powershell":
            return SimpleNamespace(stdout="", returncode=1)
        if command[0] == "tasklist":
            return SimpleNamespace(
                stdout='"python.exe","37444","Console","1","100,000 K"\n',
                returncode=0,
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(startup.subprocess, "run", fake_run)

    info = startup._get_windows_process_info("37444")

    assert info["pid"] == 37444
    assert info["name"] == "python.exe"
