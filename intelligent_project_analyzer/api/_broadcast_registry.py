# api/_broadcast_registry.py
# Broadcast function registry - decouples workflow layer from api.server.
#
# api.server registers broadcast_to_websockets at module load via register_broadcast().
# workflow nodes retrieve the callable via get_broadcast() and invoke it without
# importing api.server directly (avoiding the workflow->api layer violation).
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

__all__ = ['register_broadcast', 'get_broadcast']

_broadcast_fn: Callable[[str, Any], Awaitable[None]] | None = None


def register_broadcast(fn: Callable[[str, Any], Awaitable[None]]) -> None:
    '''Register the broadcast function (called by api.server at module load).'''
    global _broadcast_fn
    _broadcast_fn = fn


def get_broadcast() -> Callable[[str, Any], Awaitable[None]] | None:
    '''Return the registered broadcast function, or None if not yet registered.'''
    return _broadcast_fn
