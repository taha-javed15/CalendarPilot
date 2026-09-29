from tests.conftest import make_llm_response, make_tool_call
from app.agent.memory.conversation import Conversation
from app.workflows.normal_request_workflow import handle_normal_request


def test_plain_reply_with_no_tool_call(mock_primary_llm):
    conversation = Conversation(session_id="s1")
    mock_primary_llm.return_value = make_llm_response(content="Hi! How can I help with your calendar?")

    reply = handle_normal_request(conversation, "hello")

    assert reply == "Hi! How can I help with your calendar?"


def test_tool_call_then_final_answer(mock_primary_llm, mock_calendar_service):
    conversation = Conversation(session_id="s2")
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": []}

    tool_call = make_tool_call(
        "call_1", "list_events",
        {"start_time": "2026-08-10T00:00:00+05:30", "end_time": "2026-08-11T00:00:00+05:30"}
    )

    mock_primary_llm.side_effect = [
        make_llm_response(content=None, tool_calls=[tool_call]),
        make_llm_response(content="You have nothing scheduled that day.")
    ]

    reply = handle_normal_request(conversation, "what's on my calendar tomorrow?")

    assert reply == "You have nothing scheduled that day."


def test_tool_call_requiring_confirmation_short_circuits(mock_primary_llm, mock_calendar_service, mock_small_llm, sample_event):
    conversation = Conversation(session_id="s3")
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": [sample_event]}

    tool_call = make_tool_call(
        "call_1", "create_event",
        {"start": "2026-08-10T10:00:00+05:30", "end": "2026-08-10T10:30:00+05:30", "summary": "Team Sync"}
    )
    mock_primary_llm.return_value = make_llm_response(content=None, tool_calls=[tool_call])
    mock_small_llm.queue("There's a conflicting event. Do you want to proceed anyway?")

    reply = handle_normal_request(conversation, "schedule team sync at 10am")

    assert "conflict" in reply.lower() or "proceed" in reply.lower()
    assert conversation.get_pending_action() is not None
    assert conversation.get_pending_action().tool == "create_event"


def test_malformed_tool_arguments_does_not_crash(mock_primary_llm):
    conversation = Conversation(session_id="s4")

    bad_tool_call = make_tool_call("call_1", "list_events", {})
    bad_tool_call.function.arguments = "{not valid json"

    mock_primary_llm.side_effect = [
        make_llm_response(content=None, tool_calls=[bad_tool_call]),
        make_llm_response(content="Something went wrong reading that request.")
    ]

    reply = handle_normal_request(conversation, "show my calendar")

    assert reply == "Something went wrong reading that request."
