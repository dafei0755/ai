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

DEMAND_RECONSTRUCTION_RURAL_HOME_PROMPT = (
    "\u0035\u0030\u5c81\u7537\u6027\u5ba4\u5185\u8bbe\u8ba1\u5e08"
    "\uff0c\u80cc\u4e95\u79bb\u4e61"
    "\uff0c\u60f3\u5728\u8001\u5bb6\u5efa\u4e00\u680b\u6c11\u5c45"
    "\uff0c\u7ed9\u51fa\u5efa\u8bae"
)

FORMAL_RURAL_HOME_PROMPT = (
    "\u56db\u5ddd\u5e7f\u5143\u519c\u6751\u0033\u0030\u0030\u33a1\u7530\u56ed\u6c11\u5c45"
    "\uff0c\u4e1a\u4e3b\u4e3a\u0035\u0030\u5c81\u7537\u6027\u5ba4\u5185\u8bbe\u8ba1\u5e08"
    "\uff0c\u957f\u671f\u79bb\u5bb6\u5728\u5916\u53d1\u5c55"
    "\uff0c\u5185\u5fc3\u5b58\u5728\u5bf9\u4e61\u571f\u7684\u590d\u6742\u60c5\u611f\u3002"
    "\u8bf7\u4ee5\u201c\u5b89\u85e4\u5fe0\u96c4\u4e3a\u5176\u8bbe\u8ba1\u201d\u4e3a\u5047\u8bbe\u524d\u63d0"
    "\uff0c\u63d0\u51fa\u5b8c\u6574\u5ba4\u5185\u8bbe\u8ba1\u6982\u5ff5\u6846\u67b6"
    "\uff0c\u56f4\u7ed5\u5149\u7684\u63a7\u5236\u3001\u6df7\u51dd\u571f\u4e0e\u5728\u5730\u6750\u6599\u7684\u5f20\u529b"
    "\uff0c\u7a7a\u95f4\u7684\u6c89\u9ed8\u611f\u3001\u4e0e\u81ea\u7136\u5bf9\u8bdd\u7684\u754c\u9762\u5173\u7cfb"
    "\uff0c\u4ee5\u53ca\u5982\u4f55\u5728\u6734\u7d20\u4e61\u6751\u73af\u5883\u4e2d\u5b9e\u73b0\u7cbe\u795e\u6027\u7a7a\u95f4\u7684\u5efa\u6784"
    "\uff0c\u907f\u514d\u5f62\u5f0f\u5316\u6a21\u4eff\u3002"
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


@pytest.mark.asyncio
async def test_demand_reconstruction_prompt_returns_blueprint_without_formal_round(monkeypatch):
    manager = FakeSessionManager()

    async def fake_get_sm():
        return manager

    async def noop_archive(*args, **kwargs):
        return None

    monkeypatch.setenv("SCHEME_ADVISOR_ENTRY_V2_ENABLED", "1")
    monkeypatch.setenv("SCHEME_ADVISOR_ENTRY_V2_USE_LLM", "0")
    monkeypatch.setattr(dual_mode_routes, "_get_sm", fake_get_sm)
    monkeypatch.setattr(dual_mode_routes, "_archive_conversation_snapshot", noop_archive)
    monkeypatch.setattr(dual_mode_routes, "_get_conv_llm", lambda: None)

    response = await post_conversation_message(
        ConversationMessageRequest(message=DEMAND_RECONSTRUCTION_RURAL_HOME_PROMPT),
        current_user=None,
    )

    assert response.intent == "demand_reconstruction_blueprint"
    assert response.dialogue_layer == "demand_reconstruction"
    assert response.handoff_available is True
    assert response.reconstruction_type == "demand_reconstruction"
    assert response.artifact_name == "action_blueprint"
    assert response.guidance_card is not None
    assert response.guidance_card["card_type"] == "demand_reconstruction_blueprint"
    assert response.guidance_card["title"] == "需求重构"
    assert response.guidance_card["artifact_name"] == "行动蓝图"
    assert "需求重构" in response.reply
    assert "行动蓝图" not in response.reply
    assert "提交首轮判断" not in response.reply
    assert manager.sessions[response.session_id]["demand_reconstruction_context"]["blueprint"]["task_reframe"]


@pytest.mark.asyncio
async def test_formal_brief_prompt_enters_scheme_round_with_brief_layer(monkeypatch):
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
        ConversationMessageRequest(message=FORMAL_RURAL_HOME_PROMPT),
        current_user=None,
    )

    assert response.intent == "scheme_advisor_entry"
    assert response.dialogue_layer == "brief_intake"
    assert response.handoff_available is False
    assert response.guidance_card is not None
    assert response.guidance_card["card_type"] == "scheme_round_1"


@pytest.mark.asyncio
async def test_demand_reconstruction_handoff_enters_formal_round_and_preserves_context(monkeypatch):
    manager = FakeSessionManager()

    async def fake_get_sm():
        return manager

    async def noop_archive(*args, **kwargs):
        return None

    monkeypatch.setenv("SCHEME_ADVISOR_ENTRY_V2_ENABLED", "1")
    monkeypatch.setenv("SCHEME_ADVISOR_ENTRY_V2_USE_LLM", "0")
    monkeypatch.setattr(dual_mode_routes, "_get_sm", fake_get_sm)
    monkeypatch.setattr(dual_mode_routes, "_archive_conversation_snapshot", noop_archive)
    monkeypatch.setattr(dual_mode_routes, "_get_conv_llm", lambda: None)

    demand_reconstruction_response = await post_conversation_message(
        ConversationMessageRequest(message=DEMAND_RECONSTRUCTION_RURAL_HOME_PROMPT),
        current_user=None,
    )
    demand_reconstruction_card = demand_reconstruction_response.guidance_card
    assert demand_reconstruction_card is not None

    formal_response = await post_conversation_message(
        ConversationMessageRequest(
            session_id=demand_reconstruction_response.session_id,
            message="\u6574\u7406\u6210\u8bbe\u8ba1\u4efb\u52a1\u4e66\u8349\u7a3f",
            in_response_to_card_id=demand_reconstruction_card["card_id"],
            selected_option_id="handoff_to_brief",
        ),
        current_user=None,
    )

    stored = manager.sessions[demand_reconstruction_response.session_id]
    assert formal_response.intent == "scheme_advisor_entry"
    assert formal_response.dialogue_layer == "brief_intake"
    assert formal_response.guidance_card is not None
    assert formal_response.guidance_card["card_type"] == "scheme_round_1"
    assert "\u5df2\u7ee7\u627f\u9700\u6c42\u91cd\u6784\u884c\u52a8\u84dd\u56fe" in formal_response.guidance_card["prompt_text"]
    assert stored["demand_reconstruction_context"]["blueprint"]["brief_handoff_slots"]["owner_profile"]


@pytest.mark.asyncio
async def test_legacy_shallow_pending_card_is_migrated_to_demand_reconstruction(monkeypatch):
    manager = FakeSessionManager()
    session_id = "conv-legacy-shallow"
    await manager.create(
        session_id,
        {
            "session_id": session_id,
            "user_id": "dev_user",
            "user_input": DEMAND_RECONSTRUCTION_RURAL_HOME_PROMPT,
            "system_mode": "conversation",
            "status": "conversation_active",
            "conversation_drafts": [],
            "conversation_history_v2": [],
            "pending_guidance_card": {
                "card_id": "legacy-shallow-1",
                "card_type": "shallow_battle_plan",
                "title": "\u65e7\u5165\u53e3\u5361\u7247",
                "prompt_text": DEMAND_RECONSTRUCTION_RURAL_HOME_PROMPT,
                "options": [],
            },
        },
    )

    async def fake_get_sm():
        return manager

    async def noop_archive(*args, **kwargs):
        return None

    monkeypatch.setenv("SCHEME_ADVISOR_ENTRY_V2_ENABLED", "1")
    monkeypatch.setenv("SCHEME_ADVISOR_ENTRY_V2_USE_LLM", "0")
    monkeypatch.setattr(dual_mode_routes, "_get_sm", fake_get_sm)
    monkeypatch.setattr(dual_mode_routes, "_archive_conversation_snapshot", noop_archive)
    monkeypatch.setattr(dual_mode_routes, "_get_conv_llm", lambda: None)

    response = await post_conversation_message(
        ConversationMessageRequest(
            session_id=session_id,
            message="\u7ee7\u7eed\u628a\u8fd9\u4e2a\u95ee\u9898\u60f3\u6e05\u695a",
            in_response_to_card_id="legacy-shallow-1",
            selected_option_id="continue_shallow",
        ),
        current_user=None,
    )

    assert response.intent == "demand_reconstruction_blueprint"
    assert response.guidance_card is not None
    assert response.guidance_card["card_type"] == "demand_reconstruction_blueprint"
    assert manager.sessions[session_id]["pending_guidance_card"]["card_type"] == "demand_reconstruction_blueprint"
