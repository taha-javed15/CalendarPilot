import copy
from app.agent.memory.workflow_result import WorkflowStatus
from app.workflows.update_event import update_event_workflow


def test_update_event_no_fields_is_invalid():
    result = update_event_workflow(event_query="team sync")
    assert result["status"] == WorkflowStatus.INVALID_REQUEST


def test_update_event_via_lookup_applies_fields(mock_calendar_service, sample_event):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": [sample_event]
    }
    updated = copy.deepcopy(sample_event)
    updated["summary"] = "Renamed Sync"
    mock_calendar_service.events.return_value.update.return_value.execute.return_value = updated

    result = update_event_workflow(event_query="team sync", summary="Renamed Sync")

    assert result["status"] == WorkflowStatus.SUCCESS
    call_body = mock_calendar_service.events.return_value.update.call_args.kwargs["body"]
    assert call_body["summary"] == "Renamed Sync"


def test_update_event_with_preresolved_event_applies_fields(mock_calendar_service, sample_event):
    """
    Regression test: when `event` is passed directly (as happens after
    disambiguation resolves which event the user meant), the requested
    field changes must still be applied - previously this branch silently
    no-op'd and just re-saved the event unchanged.
    """
    updated = copy.deepcopy(sample_event)
    updated["location"] = "Room 4B"
    mock_calendar_service.events.return_value.update.return_value.execute.return_value = updated

    result = update_event_workflow(event=sample_event, location="Room 4B")

    assert result["status"] == WorkflowStatus.SUCCESS
    call_body = mock_calendar_service.events.return_value.update.call_args.kwargs["body"]
    assert call_body["location"] == "Room 4B"
    # find_single_event / list() must never be called when event is pre-resolved
    mock_calendar_service.events.return_value.list.assert_not_called()


def test_update_event_ambiguous_events_returns_ambiguous_status(mock_calendar_service, sample_events_list):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": sample_events_list
    }

    result = update_event_workflow(event_query="team sync", summary="Renamed")

    assert result["status"] == WorkflowStatus.AMBIGUOUS
    assert result["tool"] == "update_event"
    assert result["context"]["events"] == sample_events_list
