import copy
from app.agent.memory.conversation import Conversation
from app.agent.memory.pending_action import PendingAction, PendingActionType
from app.workflows.pending_action_workflow import handle_pending_action


def make_conversation_with_pending(action_type, tool, arguments, context=None):
    conversation = Conversation(session_id="test-session")
    conversation.set_pending_action(
        PendingAction(action_type=action_type, tool=tool, arguments=arguments, context=context)
    )
    return conversation


# ---------------------------------------------------------------------------
# Confirmation flow
# ---------------------------------------------------------------------------

def test_confirm_create_event_executes_with_force(mock_calendar_service, mock_small_llm, sample_event):
    conversation = make_conversation_with_pending(
        PendingActionType.CONFIRMATION,
        tool="create_event",
        arguments={"start": "2026-08-10T10:00:00+05:30", "end": "2026-08-10T10:30:00+05:30", "summary": "Team Sync"},
        context={"events": [sample_event]}
    )

    mock_small_llm.queue("CONFIRM")
    mock_small_llm.queue("Your event has been created.")
    mock_calendar_service.events.return_value.insert.return_value.execute.return_value = sample_event

    reply = handle_pending_action(conversation, "yes go ahead")

    assert reply == "Your event has been created."
    # conflict re-check must NOT happen on confirm
    mock_calendar_service.events.return_value.list.assert_not_called()
    mock_calendar_service.events.return_value.insert.assert_called_once()
    assert conversation.get_pending_action() is None


def test_cancel_pending_confirmation(mock_small_llm):
    conversation = make_conversation_with_pending(
        PendingActionType.CONFIRMATION,
        tool="create_event",
        arguments={"start": "x", "end": "y", "summary": "z"},
    )

    mock_small_llm.queue("CANCEL")

    reply = handle_pending_action(conversation, "no don't")

    assert "cancelled" in reply.lower()
    assert conversation.get_pending_action() is None


def test_unclear_response_keeps_pending_action(mock_small_llm):
    conversation = make_conversation_with_pending(
        PendingActionType.CONFIRMATION,
        tool="create_event",
        arguments={"start": "x", "end": "y", "summary": "z"},
    )

    mock_small_llm.queue("UNKNOWN")

    reply = handle_pending_action(conversation, "hmm what?")

    assert "yes or no" in reply.lower() or "not sure" in reply.lower()
    assert conversation.get_pending_action() is not None


def test_new_request_during_confirmation_drops_pending_and_routes_normally(mock_small_llm, mock_primary_llm):
    from tests.conftest import make_llm_response

    conversation = make_conversation_with_pending(
        PendingActionType.CONFIRMATION,
        tool="create_event",
        arguments={"start": "x", "end": "y", "summary": "z"},
    )

    mock_small_llm.queue("NEW_REQUEST")
    mock_primary_llm.return_value = make_llm_response(content="Sure, what time works?")

    reply = handle_pending_action(conversation, "actually cancel that, tell me about tomorrow instead")

    assert reply == "Sure, what time works?"
    assert conversation.get_pending_action() is None


# ---------------------------------------------------------------------------
# Ambiguity flow
# ---------------------------------------------------------------------------

def test_resolve_ambiguity_by_index_executes_tool_with_event(mock_calendar_service, mock_small_llm, sample_events_list):
    conversation = make_conversation_with_pending(
        PendingActionType.AMBIGUITY,
        tool="delete_event",
        arguments={"event_query": "team sync"},
        context={"events": sample_events_list}
    )

    mock_small_llm.queue("1")  # pick the second event
    mock_small_llm.queue("Deleted the event.")

    reply = handle_pending_action(conversation, "the second one")

    assert reply == "Deleted the event."
    mock_calendar_service.events.return_value.delete.assert_called_once_with(
        calendarId="primary", eventId=sample_events_list[1]["id"]
    )
    assert conversation.get_pending_action() is None


def test_resolve_ambiguity_unclear_keeps_pending_action(mock_small_llm, sample_events_list):
    conversation = make_conversation_with_pending(
        PendingActionType.AMBIGUITY,
        tool="delete_event",
        arguments={"event_query": "team sync"},
        context={"events": sample_events_list}
    )

    mock_small_llm.queue("NONE")

    reply = handle_pending_action(conversation, "I dunno")

    assert "couldn't tell" in reply.lower()
    assert conversation.get_pending_action() is not None


def test_resolve_ambiguity_new_request_routes_normally(mock_small_llm, mock_primary_llm, sample_events_list):
    from tests.conftest import make_llm_response

    conversation = make_conversation_with_pending(
        PendingActionType.AMBIGUITY,
        tool="delete_event",
        arguments={"event_query": "team sync"},
        context={"events": sample_events_list}
    )

    mock_small_llm.queue("NEW_REQUEST")
    mock_primary_llm.return_value = make_llm_response(content="Okay, what would you like instead?")

    reply = handle_pending_action(conversation, "never mind, what's free tomorrow?")

    assert reply == "Okay, what would you like instead?"
    assert conversation.get_pending_action() is None


def test_expired_pending_action_is_cleared():
    conversation = make_conversation_with_pending(
        PendingActionType.CONFIRMATION,
        tool="create_event",
        arguments={"start": "x", "end": "y", "summary": "z"},
    )
    conversation.get_pending_action().expires_at = conversation.get_pending_action().created_at

    reply = handle_pending_action(conversation, "yes")

    assert "expired" in reply.lower()
    assert conversation.get_pending_action() is None
