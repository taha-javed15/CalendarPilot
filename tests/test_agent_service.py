from tests.conftest import make_llm_response
from app.agent.agent_service import run_agent
from app.agent.memory.conversation_manager import conversation_manager
from app.agent.memory.pending_action import PendingAction, PendingActionType


def test_run_agent_routes_to_normal_request_when_no_pending_action(monkeypatch):
    monkeypatch.setattr(
        "app.workflows.normal_request_workflow.ask_llm",
        lambda messages: make_llm_response(content="Hello there!")
    )

    reply = run_agent("hi", session_id="session-normal")

    assert reply == "Hello there!"


def test_run_agent_routes_to_pending_action_when_one_exists(monkeypatch, mock_small_llm):
    conversation = conversation_manager.get_conversation("session-pending")
    conversation.set_pending_action(
        PendingAction(
            action_type=PendingActionType.CONFIRMATION,
            tool="create_event",
            arguments={"start": "x", "end": "y", "summary": "z"}
        )
    )
    mock_small_llm.queue("CANCEL")

    reply = run_agent("no thanks", session_id="session-pending")

    assert "cancelled" in reply.lower()


def test_conversation_manager_reuses_same_session():
    first = conversation_manager.get_conversation("reuse-test")
    second = conversation_manager.get_conversation("reuse-test")
    assert first is second


def test_conversation_manager_creates_distinct_sessions():
    a = conversation_manager.get_conversation("session-a")
    b = conversation_manager.get_conversation("session-b")
    assert a is not b
