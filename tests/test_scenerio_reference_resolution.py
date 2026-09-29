from tests.conftest import make_llm_response, make_tool_call
from app.agent.memory.conversation import Conversation
from app.workflows.normal_request_workflow import handle_normal_request


def test_followup_reference_does_not_trigger_calendar_wide_ambiguity(mock_primary_llm, mock_calendar_service, mock_small_llm, monkeypatch):
    """
    Reproduces the reported scenario end-to-end:

    1. "What are my events tomorrow?" -> list_events surfaces one Gym event.
    2. "Move it to 8 PM" -> the LLM calls update_event(event_query="Gym").
       Even though the calendar has many other events also called "Gym",
       this must resolve directly to the one just discussed instead of
       becoming AMBIGUOUS over the whole calendar.
    """
    # Ensure cached events pass the new live-calendar validation step
    monkeypatch.setattr(
        "app.dispatcher.get_event_by_id",
        lambda eid: {"id": eid, "summary": "Gym", "start": {}, "end": {}}
    )

    conversation = Conversation(session_id="scenario")

    # Turn 1: "What are my events tomorrow?"
    tomorrows_gym = {
        "id": "gym-tomorrow",
        "summary": "Gym",
        "start": {"dateTime": "2026-08-11T07:00:00+05:30"},
        "end": {"dateTime": "2026-08-11T08:00:00+05:30"},
    }
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": [tomorrows_gym]
    }

    list_call = make_tool_call(
        "call_1", "list_events",
        {"start_time": "2026-08-11T00:00:00+05:30", "end_time": "2026-08-12T00:00:00+05:30"}
    )
    mock_primary_llm.side_effect = [
        make_llm_response(content=None, tool_calls=[list_call]),
        make_llm_response(content="You have Gym tomorrow at 7 AM."),
    ]

    reply_1 = handle_normal_request(conversation, "What are my events tomorrow?")
    assert reply_1 == "You have Gym tomorrow at 7 AM."
    assert conversation.get_last_referenced_events() == [tomorrows_gym]

    # Turn 2: "Move it to 8 PM" - the primary LLM would naturally call
    # update_event with a query like "Gym" (or "it") derived from context.
    update_call = make_tool_call(
        "call_2", "update_event",
        {"event_query": "Gym", "start": "2026-08-11T20:00:00+05:30"}
    )
    mock_primary_llm.side_effect = [
        make_llm_response(content=None, tool_calls=[update_call]),
        make_llm_response(content="Moved Gym to 8 PM."),
    ]

    updated_event = dict(tomorrows_gym)
    updated_event["start"] = {"dateTime": "2026-08-11T20:00:00+05:30"}
    mock_calendar_service.events.return_value.update.return_value.execute.return_value = updated_event

    reply_2 = handle_normal_request(conversation, "Move it to 8 PM")

    # The critical assertion: this must succeed directly, NOT come back as
    # a request for clarification among every "Gym" event ever created.
    assert reply_2 == "Moved Gym to 8 PM."
    assert conversation.get_pending_action() is None

    # And it must have resolved without a second full-calendar search -
    # list() should only have been called once, during turn 1.
    assert mock_calendar_service.events.return_value.list.call_count == 1
    mock_calendar_service.events.return_value.update.assert_called_once()
    updated_body = mock_calendar_service.events.return_value.update.call_args.kwargs["body"]
    assert updated_body["id"] == "gym-tomorrow"