"""Backend startup entrypoint used by QUICKSTART and Windows terminals."""

from __future__ import annotations

import os
import runpy
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import csv
import json
from pathlib import Path


VALID_BOOLEAN_ENV_VALUES = {
    "1",
    "0",
    "true",
    "false",
    "yes",
    "no",
    "on",
    "off",
}
SERVER_STARTUP_BACKEND_HOST = "SERVER_STARTUP_BACKEND_HOST"
SERVER_STARTUP_BACKEND_PORT = "SERVER_STARTUP_BACKEND_PORT"
BACKEND_PORT_CONFLICT_POLICY = "BACKEND_PORT_CONFLICT_POLICY"
DEFAULT_HEALTH_TIMEOUT_SECONDS = 1.5


def ensure_repo_on_pythonpath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_text = str(repo_root)
    if repo_root_text not in sys.path:
        sys.path.insert(0, repo_root_text)


def normalize_debug_env() -> None:
    value = os.environ.get("DEBUG")
    if value is None:
        return
    if value.strip().lower() in VALID_BOOLEAN_ENV_VALUES:
        return
    os.environ["DEBUG"] = "false"


def load_runtime_env(env_path: Path | None = None) -> None:
    resolved_env_path = env_path or Path(__file__).resolve().parents[1] / ".env"
    if not resolved_env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(resolved_env_path, override=False)
        return
    except ImportError:
        pass
    for raw_line in resolved_env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def get_backend_host() -> str:
    return os.environ.get("BACKEND_HOST", "0.0.0.0").strip() or "0.0.0.0"


def get_backend_port() -> int:
    raw_value = os.environ.get("BACKEND_PORT", "8001").strip()
    try:
        port = int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"BACKEND_PORT 必须是 1-65535 的整数，当前值为 {raw_value!r}") from exc
    if port < 1 or port > 65535:
        raise SystemExit(f"BACKEND_PORT 必须是 1-65535 的整数，当前值为 {raw_value!r}")
    return port


def is_port_in_use(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
            return False
    except OSError:
        return True


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_probe_host(host: str) -> str:
    if host in {"", "0.0.0.0", "::", "[::]"}:
        return "127.0.0.1"
    return host.strip("[]")


def get_backend_health_url(host: str, port: int) -> str:
    return f"http://{get_probe_host(host)}:{port}/health"


def probe_existing_backend_health(host: str, port: int) -> dict:
    url = get_backend_health_url(host, port)
    try:
        with urllib.request.urlopen(url, timeout=DEFAULT_HEALTH_TIMEOUT_SECONDS) as response:
            status_code = getattr(response, "status", 200)
            body: dict = {}
            try:
                raw_body = response.read().decode("utf-8", errors="replace")
                body = json.loads(raw_body) if raw_body.strip() else {}
            except (ValueError, OSError):
                body = {}
            return {"ok": 200 <= status_code < 300, "status": status_code, "url": url, "body": body}
    except (OSError, urllib.error.URLError) as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def _pid_from_local_address(line: str, port: int) -> str | None:
    parts = line.split()
    if len(parts) < 5 or parts[-2].upper() != "LISTENING":
        return None
    local_address = parts[1]
    if not local_address.endswith(f":{port}"):
        return None
    return parts[-1]


def _get_windows_process_info(pid: str) -> dict:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" | "
            "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
        ),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError):
        return _get_windows_process_name_from_tasklist(pid)
    output = result.stdout.strip()
    if not output:
        return _get_windows_process_name_from_tasklist(pid)
    try:
        import json

        data = json.loads(output)
        if isinstance(data, list):
            data = data[0] if data else {}
        return {
            "pid": int(data.get("ProcessId") or pid),
            "name": data.get("Name") or "",
            "command_line": data.get("CommandLine") or "",
        }
    except (ValueError, TypeError, AttributeError):
        return _get_windows_process_name_from_tasklist(pid)


def _get_windows_process_name_from_tasklist(pid: str) -> dict:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"pid": int(pid), "name": "", "command_line": ""}
    output = result.stdout.strip()
    if not output or "INFO:" in output.upper():
        return {"pid": int(pid), "name": "", "command_line": ""}
    try:
        row = next(csv.reader(output.splitlines()))
    except (StopIteration, csv.Error):
        return {"pid": int(pid), "name": "", "command_line": ""}
    return {"pid": int(pid), "name": row[0] if row else "", "command_line": ""}


def find_port_owners(port: int) -> list[dict]:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    pids = sorted(
        {
            pid
            for line in result.stdout.splitlines()
            if (pid := _pid_from_local_address(line, port)) and pid.isdigit()
        }
    )
    return [_get_windows_process_info(pid) for pid in pids]


def is_owned_backend_process(process: dict, repo_root: Path) -> bool:
    command_line = (process.get("command_line") or "").lower()
    name = (process.get("name") or "").lower()
    repo_text = str(repo_root).lower()
    if "python" not in name:
        return False
    is_project_server = (
        "run_server_production.py" in command_line
        or "intelligent_project_analyzer.api.server" in command_line
    )
    if not is_project_server:
        return False
    if "intelligent_project_analyzer.api.server" in command_line:
        return True
    if repo_text in command_line:
        return True
    return "scripts/run_server_production.py" in command_line or "scripts\\run_server_production.py" in command_line


def stop_process(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True, text=True)
        return
    try:
        os.kill(pid, 15)
    except OSError:
        return


def wait_until_port_released(host: str, port: int, timeout_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not is_port_in_use(host, port):
            return True
        time.sleep(0.2)
    return not is_port_in_use(host, port)


def _format_port_owners(owners: list[dict]) -> str:
    if not owners:
        return "未能识别占用进程。"
    lines = []
    for owner in owners:
        command_line = owner.get("command_line") or ""
        command_hint = f" | {command_line}" if command_line else ""
        lines.append(f"- PID {owner.get('pid')} {owner.get('name') or ''}{command_hint}")
    return "\n".join(lines)


def restart_owned_backend_processes(host: str, port: int, owners: list[dict]) -> dict | None:
    repo_root = get_repo_root()
    owned_processes = [owner for owner in owners if is_owned_backend_process(owner, repo_root)]
    if not owned_processes:
        return None
    for owner in owned_processes:
        stop_process(int(owner["pid"]))
    if wait_until_port_released(host, port):
        message = f"已关闭旧后端进程，端口 {port} 已释放，准备重新启动。"
        print(message)
        return {"action": "restart-owned", "message": message, "owners": owned_processes}
    raise SystemExit(f"已尝试关闭旧后端进程，但端口 {port} 仍未释放。")


def collect_backend_status() -> dict:
    host = get_backend_host()
    port = get_backend_port()
    port_in_use = is_port_in_use(host, port)
    health = (
        probe_existing_backend_health(host, port)
        if port_in_use
        else {"ok": False, "url": get_backend_health_url(host, port), "error": "port free"}
    )
    owners = find_port_owners(port) if port_in_use else []
    repo_root = get_repo_root()
    annotated_owners = [
        {**owner, "is_owned_backend": is_owned_backend_process(owner, repo_root)}
        for owner in owners
    ]
    return {
        "host": host,
        "port": port,
        "port_in_use": port_in_use,
        "health": health,
        "owners": annotated_owners,
    }


def _extract_llm_status(health: dict) -> str:
    body = health.get("body") if isinstance(health.get("body"), dict) else {}
    components = body.get("components") if isinstance(body.get("components"), dict) else {}
    llm = components.get("llm") if isinstance(components.get("llm"), dict) else {}
    if not llm:
        return "未知"
    return f"{llm.get('provider') or 'unknown'}/{llm.get('status') or 'unknown'}"


def format_backend_status(status: dict) -> str:
    host = status.get("host") or get_backend_host()
    port = int(status.get("port") or get_backend_port())
    health = status.get("health") or {}
    lines = [
        "后端状态:",
        f"- 地址: {health.get('url') or get_backend_health_url(host, port)}",
        f"- 端口: {port}",
        f"- 端口占用: {'是' if status.get('port_in_use') else '否'}",
        f"- 健康检查: {'通过' if health.get('ok') else '未通过'}",
        f"- 可复用后端: {'是' if health.get('ok') else '否'}",
    ]
    if health.get("status"):
        lines.append(f"- HTTP状态: {health.get('status')}")
    if health.get("error"):
        lines.append(f"- 健康错误: {health.get('error')}")
    lines.append(f"- LLM: {_extract_llm_status(health)}")

    owners = status.get("owners") or []
    if not owners:
        lines.append("- 占用进程: 无")
        return "\n".join(lines)

    lines.append("- 占用进程:")
    for owner in owners:
        command_line = owner.get("command_line") or ""
        command_hint = f" | {command_line}" if command_line else ""
        if owner.get("is_owned_backend"):
            ownership = "是"
        elif health.get("ok") and not command_line:
            ownership = "未识别"
        else:
            ownership = "否"
        lines.append(f"  - PID {owner.get('pid')} {owner.get('name') or ''}{command_hint}")
        lines.append(f"    本项目后端: {ownership}")
    return "\n".join(lines)


def handle_backend_port_conflict(force_restart_owned: bool = False) -> dict:
    host = get_backend_host()
    port = get_backend_port()
    if not is_port_in_use(host, port):
        return {"action": "start", "message": f"后端端口 {port} 可用，准备启动。"}

    owners = find_port_owners(port)
    if force_restart_owned:
        restart_result = restart_owned_backend_processes(host, port, owners)
        if restart_result is not None:
            return restart_result
        raise SystemExit(
            f"已请求重启本项目后端，但未能识别端口 {port} 上的本项目进程。\n"
            f"占用进程：\n{_format_port_owners(owners)}\n"
            f"不会关闭未知进程。"
        )

    health = probe_existing_backend_health(host, port)
    if health.get("ok"):
        message = f"检测到已有健康后端正在运行：{health.get('url')}，本次不会重复启动。"
        print(message)
        return {"action": "adopted", "message": message, "health": health}

    policy = os.environ.get(BACKEND_PORT_CONFLICT_POLICY, "restart-owned").strip().lower()
    if policy in {"restart-owned", "restart"}:
        restart_result = restart_owned_backend_processes(host, port, owners)
        if restart_result is not None:
            return restart_result

    raise SystemExit(
        f"后端端口 {port} 已被占用，但健康检查未通过：{health.get('url')}\n"
        f"健康检查错误：{health.get('error') or health.get('status') or 'unknown'}\n"
        f"占用进程：\n{_format_port_owners(owners)}\n\n"
        f"处理方式：\n"
        f"- 如果这是健康后端，请直接使用前端，不要重复启动。\n"
        f"- 默认只会自动重启本项目的非健康后端，不会关闭未知进程。\n"
        f"- 可通过 {BACKEND_PORT_CONFLICT_POLICY}=adopt 禁用自动重启，只报告占用状态。\n"
        f"- 如果这是其他程序，请关闭该进程，或设置 BACKEND_PORT 为其他可用端口。"
    )


def fail_fast_if_backend_port_in_use() -> None:
    result = handle_backend_port_conflict()
    if result["action"] == "adopted":
        raise SystemExit(0)
    raise SystemExit(
        f"后端端口 {port} 已被占用，服务不会重复启动。\n"
        f"如果这是旧后端进程，请先关闭它；如果要临时换端口，请设置 BACKEND_PORT 为其他可用端口（例如 8002）后再启动。"
    )


def pin_resolved_backend_address() -> None:
    os.environ[SERVER_STARTUP_BACKEND_HOST] = get_backend_host()
    os.environ[SERVER_STARTUP_BACKEND_PORT] = str(get_backend_port())


def main() -> None:
    ensure_repo_on_pythonpath()
    load_runtime_env()
    normalize_debug_env()
    if "--status" in sys.argv:
        print(format_backend_status(collect_backend_status()))
        return
    startup_decision = handle_backend_port_conflict(force_restart_owned="--restart-owned" in sys.argv)
    if startup_decision["action"] == "adopted":
        return
    pin_resolved_backend_address()
    runpy.run_module("intelligent_project_analyzer.api.server", run_name="__main__")


if __name__ == "__main__":
    main()
