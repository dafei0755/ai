import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock the session manager
mock_session_manager = AsyncMock()
mock_archive_manager = AsyncMock()

# Mock data
MOCK_SESSION_ID = "test-session-123"
MOCK_SESSION_DATA = {
    "session_id": MOCK_SESSION_ID,
    "status": "completed",
    "progress": 1.0,
    "final_report": "This is a mock final report.",
    "history": [],
    "created_at": datetime.now().isoformat(),
}


@pytest.fixture
def client():
    # Import lazily to avoid heavy initialization during test collection.
    from intelligent_project_analyzer.api import server as server_module

    # Patch the dependencies
    with patch.object(server_module, "session_manager", mock_session_manager), patch.object(
        server_module, "archive_manager", mock_archive_manager
    ):
        # Setup mock return values
        mock_session_manager.get.return_value = MOCK_SESSION_DATA.copy()
        mock_session_manager.update.return_value = None

        with TestClient(server_module.app) as c:
            yield c


def test_system_followup_flow(client):
    """
    System Test: Follow-up Question Flow
    1. Verify Recommendations (Suggestions)
    2. Verify Dialogue (Question/Answer)
    3. Verify Persistence (History)
    """

    # --- Step 1: Send Follow-up Question ---
    print("\n[Step 1] Sending Follow-up Question...")

    question_payload = {
        "session_id": MOCK_SESSION_ID,
        "question": "Can you explain the cost?",
        "requires_analysis": False,  # Important: Chat Mode
    }

    # Mock the session update to simulate saving history
    async def mock_update(session_id, update_data):
        if "history" in update_data:
            MOCK_SESSION_DATA["history"] = update_data["history"]
        return None

    mock_session_manager.update.side_effect = mock_update

    response = client.post("/api/analysis/followup", json=question_payload)

    assert response.status_code == 200
    data = response.json()

    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

    # Verify Response Structure
    assert "answer" in data
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)

    # Verify Suggestions (Step 1 Requirement)
    print(f"\n[Check] Suggestions generated: {data['suggestions']}")
    assert len(data["suggestions"]) > 0

    # --- Step 2: Verify Dialogue ---
    print("\n[Step 2] Verifying Dialogue Content...")
    assert len(data["answer"]) > 0
    # Since we are using a real LLM (or mock if configured), we just check we got a string back.
    # Note: In a real CI environment, we might mock the LLM too, but here we want to test the flow.

    # --- Step 3: Verify Persistence ---
    print("\n[Step 3] Verifying Persistence...")

    # Simulate getting status
    mock_session_manager.get.return_value = MOCK_SESSION_DATA

    status_response = client.get(f"/api/analysis/status/{MOCK_SESSION_ID}")
    assert status_response.status_code == 200
    status_data = status_response.json()

    print(f"Session History: {json.dumps(status_data.get('history'), indent=2, ensure_ascii=False)}")

    history = status_data.get("history", [])
    assert len(history) > 0
    last_turn = history[-1]

    assert last_turn["question"] == "Can you explain the cost?"
    assert "answer" in last_turn
    assert last_turn["answer"] == data["answer"]

    print("\n✅ System Test Passed: Follow-up flow is working correctly.")


if __name__ == "__main__":
    # Allow running directly
    pytest.main([__file__])
