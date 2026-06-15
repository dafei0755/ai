import os

os.environ["DEBUG"] = "false"

import pytest

from intelligent_project_analyzer.api import dual_mode_routes
from intelligent_project_analyzer.api.dual_mode_routes import (
    ConversationMessageRequest,
    post_conversation_message,
)


FORMAL_MILK_TEA_PROMPT = (
    "\u6df1\u5733\u5e02\u5357\u5c71\u533a\u6765\u798f\u58eb\u5e7f\u573a"
    "\uff0c\u8d1f\u4e00\u697c\uff0c30\u5e73\u7c73\u5546\u94fa"
    "\uff0c\u5730\u94c1\u901a\u9053\u4e0e\u5546\u573a\u7684\u8fde\u63a5\u5904"
    "\uff0c\u6253\u7b97\u505a\u4e00\u4e2a\u5976\u8336\u5e97"
    "\uff0c\u5e0c\u671b\u534a\u5e74\u80fd\u6536\u56de\u6210\u672c"
    "\uff0c\u6211\u9700\u8981\u4e00\u4efd\u5b8c\u6574\u7684\u8bbe\u8ba1\u5efa\u8bae\u3002"
)


class FakeSessionManager:
    def __init__(self) -> None:
        self.sessions = {}

    async def create(self, session_id: str, data: dict) -> None:
        self.sessions[session_id] = dict(data)

    async def get(self, session_id: str):
        return self.sessions.get(session_id)

    async def update(self, session_id: str, data: dict) -> None:
        self.sessions.setdefault(session_id, {}).update(data)


@pytest.mark.asyncio
async def test_conversation_route_prefers_scheme_advisor_entry_v2(monkeypatch):
    manager = FakeSessionManager()

    async def fake_get_sm():
        return manager

    async def noop_archive(*args, **kwargs):
        return None

    monkeypatch.setenv("SCHEME_ADVISOR_ENTRY_V2_ENABLED", "1")
    monkeypatch.setenv("SCHEME_ADVISOR_ENTRY_V2_USE_LLM", "0")
    monkeypatch.setattr(dual_mode_routes, "_get_sm", fake_get_sm)
    monkeypatch.setattr(dual_mode_routes, "_archive_conversation_snapshot", noop_archive)

    response = await post_conversation_message(
        ConversationMessageRequest(message=FORMAL_MILK_TEA_PROMPT),
        current_user=None,
    )

    assert response.intent == "scheme_advisor_entry"
    assert response.guidance_card is not None
    assert response.guidance_card["card_type"] == "scheme_round_1"
    assert response.session_id in manager.sessions
    assert manager.sessions[response.session_id]["pending_guidance_card"]["card_type"] == "scheme_round_1"
