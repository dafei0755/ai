import types

from intelligent_project_analyzer.api.server import _ensure_aiosqlite_is_alive


class _DummyThread:
    def __init__(self, alive: bool = True) -> None:
        self._alive = alive

    def is_alive(self) -> bool:  # pragma: no cover - simple stub
        return self._alive


class _ConnWithoutIsAlive:
    def __init__(self, alive: bool = True) -> None:
        self._thread = _DummyThread(alive)
        self._running = alive


class _ConnWithIsAlive(_ConnWithoutIsAlive):
    def __init__(self, alive: bool = True) -> None:
        super().__init__(alive)
        self._patched = types.SimpleNamespace()

    def is_alive(self) -> bool:
        self._patched.called = True
        return False


def test_patch_injects_is_alive_when_missing() -> None:
    conn = _ConnWithoutIsAlive()
    patched = _ensure_aiosqlite_is_alive(conn)

    assert patched is conn
    assert hasattr(conn, "is_alive")
    assert callable(conn.is_alive)
    assert conn.is_alive() is True


def test_patch_preserves_existing_is_alive() -> None:
    conn = _ConnWithIsAlive()
    patched = _ensure_aiosqlite_is_alive(conn)

    assert patched is conn
    assert hasattr(conn, "is_alive")
    assert conn.is_alive() is False
    assert getattr(conn._patched, "called", False) is True
