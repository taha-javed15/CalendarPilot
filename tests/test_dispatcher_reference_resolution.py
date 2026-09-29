import copy
import pytest
from app.agent.memory.conversation import Conversation
from app.agent.memory.workflow_result import WorkflowStatus
from app.dispatcher import execute_tools


def make_event(id_, summary, start="2026-08-11T07:00:00+05:30", end="2026-08-11T08:00:00+05:30"):
    return {"id": id_, "summary": summary, "start": {"dateTime": start}, "end": {"dateTime": end}}


@pytest.fixture(autouse=True)
def mock_get_event_by_id(monkeypatch):
    """
    The dispatcher now validates cached events against the live calendar
    before using them for reference resolution. Mock this so cached events
    appear valid unless a test explicitly overrides the mock.
    """
    def fake_get_event_by_id(event_id):
        return {"id": event_id, "summary": "Cached Event", "start": {}, "end": {}}
    monkeypatch.setattr("app.dispatcher.get_event_by_id", fake_get_event_by_id)


def test_list_events_populates_conversation_reference(mock_calendar_service):
    conversation = Conversation(session_id="s1")
    gym_event = make_event("gym-1", "Gym")
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": [gym_event]}

    execute_tools("list_events", {"start_time": "2026-08-11T00:00:00+05:30", "end_time": "2026-08-12T00:00:00+05:30"}, conversation=conversation)

    assert conversation.get_last_referenced_events() == [gym_event]


def test_update_event_resolves_against_conversation_without_full_search(mock_calendar_service):
    """
    Regression test for the reported bug: after list_events surfaces a
    single "Gym" event, a follow-up update_event(event_query="Gym") must
    resolve directly to that event WITHOUT calling find_single_event
    (i.e. without a fresh calendar-wide search), even though the calendar
    has many other events also titled "Gym".
    """
    conversation = Conversation(session_id="s2")
    todays_gym = make_event("gym-today", "Gym")
    conversation.set_last_referenced_events([todays_gym])

    updated = copy.deepcopy(todays_gym)
    updated["start"]["dateTime"] = "2026-08-11T20:00:00+05:30"
    mock_calendar_service.events.return_value.update.return_value.execute.return_value = updated

    result = execute_tools(
        "update_event",
        {"event_query": "Gym", "start": "2026-08-11T20:00:00+05:30"},
        conversation=conversation
    )

    assert result["status"] == WorkflowStatus.SUCCESS
    # The full-calendar search must never have happened - only .update()
    # should have been called, not .list()
    mock_calendar_service.events.return_value.list.assert_not_called()
    mock_calendar_service.events.return_value.update.assert_called_once()
    call_body = mock_calendar_service.events.return_value.update.call_args.kwargs["body"]
    assert call_body["id"] == "gym-today"
    assert call_body["start"]["dateTime"] == "2026-08-11T20:00:00+05:30"


def test_pronoun_reference_resolves_without_full_search(mock_calendar_service):
    conversation = Conversation(session_id="s3")
    dentist = make_event("dentist-1", "Dentist")
    conversation.set_last_referenced_events([dentist])
    mock_calendar_service.events.return_value.delete.return_value.execute.return_value = {}

    result = execute_tools("delete_event", {"event_query": "it", "force": True}, conversation=conversation)

    assert result["status"] == WorkflowStatus.SUCCESS
    mock_calendar_service.events.return_value.list.assert_not_called()
    mock_calendar_service.events.return_value.delete.assert_called_once_with(
        calendarId="primary", eventId="dentist-1"
    )


def test_ambiguous_among_recent_events_scopes_to_just_those(mock_calendar_service):
    """
    If the reference matches more than one recently-shown event, the
    resulting ambiguity must be scoped to just those candidates, not a
    fresh full-calendar search.
    """
    conversation = Conversation(session_id="s4")
    gym_am = make_event("gym-am", "Gym")
    gym_pm = make_event("gym-pm", "Gym")
    conversation.set_last_referenced_events([gym_am, gym_pm])

    result = execute_tools("delete_event", {"event_query": "Gym"}, conversation=conversation)

    assert result["status"] == WorkflowStatus.AMBIGUOUS
    assert result["tool"] == "delete_event"
    assert {e["id"] for e in result["context"]["events"]} == {"gym-am", "gym-pm"}
    mock_calendar_service.events.return_value.list.assert_not_called()


def test_no_match_falls_back_to_full_calendar_search(mock_calendar_service):
    conversation = Conversation(session_id="s5")
    conversation.set_last_referenced_events([make_event("dentist-1", "Dentist")])

    lunch_event = make_event("lunch-1", "Lunch with Sarah")
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": [lunch_event]}
    mock_calendar_service.events.return_value.delete.return_value.execute.return_value = {}

    result = execute_tools("delete_event", {"event_query": "Lunch with Sarah", "force": True}, conversation=conversation)

    assert result["status"] == WorkflowStatus.SUCCESS
    # No match against recent context ("Dentist" vs "Lunch with Sarah") -
    # so it must fall back to the normal full-calendar search.
    mock_calendar_service.events.return_value.list.assert_called_once()


def test_stale_reference_is_ignored(mock_calendar_service):
    from datetime import timedelta

    conversation = Conversation(session_id="s6")
    conversation.set_last_referenced_events([make_event("gym-old", "Gym")])
    conversation.last_referenced_at -= timedelta(minutes=30)

    fresh_gym = make_event("gym-new", "Gym")
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": [fresh_gym]}
    mock_calendar_service.events.return_value.delete.return_value.execute.return_value = {}

    result = execute_tools("delete_event", {"event_query": "Gym", "force": True}, conversation=conversation)

    assert result["status"] == WorkflowStatus.SUCCESS
    mock_calendar_service.events.return_value.list.assert_called_once()


def test_explicit_event_argument_skips_resolution_entirely(mock_calendar_service):
    """If `event` is already provided (e.g. from disambiguation resolution),
    reference resolution must not run at all, regardless of event_query."""
    conversation = Conversation(session_id="s7")
    conversation.set_last_referenced_events([{"id": "wrong-one", "summary": "Gym"}])

    correct_event = {"id": "correct-one", "summary": "Gym", "start": {}, "end": {}}
    mock_calendar_service.events.return_value.delete.return_value.execute.return_value = {}

    result = execute_tools("delete_event", {"event": correct_event, "force": True}, conversation=conversation)

    assert result["status"] == WorkflowStatus.SUCCESS
    mock_calendar_service.events.return_value.delete.assert_called_once_with(
        calendarId="primary", eventId="correct-one"
    )


def test_get_event_details_reference_preserves_id_for_later_use(mock_calendar_service):
    """
    Regression test: get_event_details_workflow used to strip `id` from
    its returned event, which would have crashed a later delete/update
    call resolved against that reference.
    """
    conversation = Conversation(session_id="s8")
    gym = make_event("gym-1", "Gym")
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": [gym]}

    details_result = execute_tools("get_event_details", {"event_query": "Gym"}, conversation=conversation)
    assert details_result["status"] == WorkflowStatus.SUCCESS
    assert details_result["event"]["id"] == "gym-1"

    mock_calendar_service.events.return_value.delete.return_value.execute.return_value = {}
    delete_result = execute_tools("delete_event", {"event_query": "it", "force": True}, conversation=conversation)

    assert delete_result["status"] == WorkflowStatus.SUCCESS
    mock_calendar_service.events.return_value.delete.assert_called_once_with(
        calendarId="primary", eventId="gym-1"
    )