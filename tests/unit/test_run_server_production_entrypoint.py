import importlib.util
from pathlib import Path


def _load_entrypoint_module():
    script_path = Path("scripts/run_server_production.py")
    spec = importlib.util.spec_from_file_location("run_server_production", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_backend_startup_entrypoint_normalizes_invalid_debug_env(monkeypatch):
    module = _load_entrypoint_module()

    monkeypatch.setenv("DEBUG", "release")

    module.normalize_debug_env()

    assert module.os.environ["DEBUG"] == "false"


def test_backend_startup_entrypoint_keeps_boolean_debug_env(monkeypatch):
    module = _load_entrypoint_module()

    monkeypatch.setenv("DEBUG", "true")

    module.normalize_debug_env()

    assert module.os.environ["DEBUG"] == "true"


def test_backend_startup_entrypoint_reads_backend_port(monkeypatch):
    module = _load_entrypoint_module()

    monkeypatch.setenv("BACKEND_PORT", "8001")

    assert module.get_backend_port() == 8001


def test_backend_startup_entrypoint_loads_backend_port_from_env_file(monkeypatch):
    module = _load_entrypoint_module()
    env_path = Path("tmp/test_run_server_production.env")

    monkeypatch.delenv("BACKEND_PORT", raising=False)
    env_path.parent.mkdir(exist_ok=True)
    env_path.write_text("BACKEND_PORT=8123\n", encoding="utf-8")

    try:
        module.load_runtime_env(env_path)

        assert module.get_backend_port() == 8123
    finally:
        env_path.unlink(missing_ok=True)


def test_backend_startup_entrypoint_rejects_invalid_backend_port(monkeypatch):
    module = _load_entrypoint_module()

    monkeypatch.setenv("BACKEND_PORT", "not-a-port")

    try:
        module.get_backend_port()
    except SystemExit as exc:
        assert "BACKEND_PORT" in str(exc)
        assert "not-a-port" in str(exc)
    else:
        raise AssertionError("Expected SystemExit for invalid BACKEND_PORT")


def test_backend_startup_entrypoint_fails_fast_when_port_is_in_use(monkeypatch):
    module = _load_entrypoint_module()

    monkeypatch.setenv("BACKEND_PORT", "8000")
    monkeypatch.setattr(module, "is_port_in_use", lambda host, port: True)

    try:
        module.fail_fast_if_backend_port_in_use()
    except SystemExit as exc:
        message = str(exc)
        assert "8000" in message
        assert "已被占用" in message
        assert "BACKEND_PORT" in message
    else:
        raise AssertionError("Expected SystemExit when backend port is already in use")


def test_backend_startup_entrypoint_pins_resolved_backend_address(monkeypatch):
    module = _load_entrypoint_module()

    monkeypatch.setenv("BACKEND_HOST", "127.0.0.1")
    monkeypatch.setenv("BACKEND_PORT", "8002")

    module.pin_resolved_backend_address()
    monkeypatch.setenv("BACKEND_PORT", "8001")

    assert module.os.environ["SERVER_STARTUP_BACKEND_HOST"] == "127.0.0.1"
    assert module.os.environ["SERVER_STARTUP_BACKEND_PORT"] == "8002"
