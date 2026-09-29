import copy
from app.agent.memory.workflow_result import WorkflowStatus
from app.workflows.update_attendees import update_attendees_workflow


def test_update_attendees_no_changes_is_invalid():
    result = update_attendees_workflow(event_query="team sync")
    assert result["status"] == WorkflowStatus.INVALID_REQUEST


def test_update_attendees_ambiguous(mock_calendar_service, sample_events_list):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": sample_events_list
    }

    result = update_attendees_workflow(event_query="team sync", add_attendees=["carol@example.com"])

    assert result["status"] == WorkflowStatus.AMBIGUOUS
    assert result["tool"] == "update_attendees"
    assert result["arguments"]["add_attendees"] == ["carol@example.com"]


def test_update_attendees_remove(mock_calendar_service, sample_event):
    updated = copy.deepcopy(sample_event)
    updated["attendees"] = [a for a in sample_event["attendees"] if a["email"] != "bob@example.com"]
    mock_calendar_service.events.return_value.update.return_value.execute.return_value = updated

    result = update_attendees_workflow(event=sample_event, remove_attendees=["bob@example.com"])

    assert result["status"] == WorkflowStatus.SUCCESS
    assert "bob@example.com" in result["attendees_removed"]


def test_update_attendees_already_up_to_date(sample_event):
    existing_email = sample_event["attendees"][0]["email"]

    result = update_attendees_workflow(event=sample_event, add_attendees=[existing_email])

    assert result["status"] == WorkflowStatus.INVALID_REQUEST
    assert "up to date" in result["message"].lower()
