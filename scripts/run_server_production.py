"""Backend startup entrypoint used by QUICKSTART and Windows terminals."""

from __future__ import annotations

import os
import runpy
import socket
import sys
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
    raw_value = os.environ.get("BACKEND_PORT", "8000").strip()
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


def fail_fast_if_backend_port_in_use() -> None:
    host = get_backend_host()
    port = get_backend_port()
    if not is_port_in_use(host, port):
        return
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
    fail_fast_if_backend_port_in_use()
    pin_resolved_backend_address()
    runpy.run_module("intelligent_project_analyzer.api.server", run_name="__main__")


if __name__ == "__main__":
    main()
