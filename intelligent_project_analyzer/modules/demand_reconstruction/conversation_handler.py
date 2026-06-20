"""Conversation entry handling for demand reconstruction."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


ResultBuilder = Callable[..., Dict[str, Any]]


class DemandReconstructionConversationHandler:
    """Handle pending-card and new-message entry decisions."""

    def __init__(
        self,
        *,
        card_type: str,
        entry_classifier: Any,
        result_builder: ResultBuilder,
    ) -> None:
        self._card_type = card_type
        self._entry_classifier = entry_classifier
        self._result_builder = result_builder

    def handle_message(
        self,
        *,
        session: Dict[str, Any],
        user_message: str,
        in_response_to_card_id: Optional[str],
        selected_option_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        pending_card = session.get("pending_guidance_card") or {}
        if pending_card.get("card_type") == self._card_type:
            context = dict(session.get("demand_reconstruction_context") or {})
            if selected_option_id == "handoff_to_brief":
                context["handoff_requested"] = True
                return {
                    "handoff_requested": True,
                    "demand_reconstruction_context": context,
                }
            if (
                selected_option_id == "continue_demand_reconstruction"
                or self._entry_classifier.is_demand_reconstruction_followup(user_message)
            ):
                return self._result_builder(
                    user_message,
                    previous_context=context,
                    session=session,
                )
            return None

        if not self._entry_classifier.should_handle(user_message):
            return None
        return self._result_builder(user_message, session=session)
