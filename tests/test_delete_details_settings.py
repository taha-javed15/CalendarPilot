from app.agent.memory.workflow_result import WorkflowStatus
from app.workflows.delete_event import delete_event_workflow
from app.workflows.get_event_details import get_event_details_workflow
from app.workflows.settings import get_settings_workflow, update_settings_workflow, load_settings


def test_delete_event_by_query_requires_confirmation(mock_calendar_service, sample_event):
    """Delete now requires confirmation before executing."""
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": [sample_event]
    }

    result = delete_event_workflow(event_query="team sync")

    assert result["status"] == WorkflowStatus.CONFIRMATION_REQUIRED
    assert result["tool"] == "delete_event"
    mock_calendar_service.events.return_value.delete.assert_not_called()


def test_delete_event_by_query_success(mock_calendar_service, sample_event):
    """force=True bypasses confirmation (used after user confirms)."""
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": [sample_event]
    }

    result = delete_event_workflow(event_query="team sync", force=True)

    assert result["status"] == WorkflowStatus.SUCCESS
    mock_calendar_service.events.return_value.delete.assert_called_once_with(
        calendarId="primary", eventId=sample_event["id"]
    )


def test_delete_event_ambiguous(mock_calendar_service, sample_events_list):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": sample_events_list
    }

    result = delete_event_workflow(event_query="team sync")

    assert result["status"] == WorkflowStatus.AMBIGUOUS
    assert result["tool"] == "delete_event"


def test_delete_event_not_found(mock_calendar_service):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": []}

    result = delete_event_workflow(event_query="nonexistent meeting")

    assert result["status"] == WorkflowStatus.NOT_FOUND
    mock_calendar_service.events.return_value.delete.assert_not_called()


def test_delete_event_with_preresolved_event(mock_calendar_service, sample_event):
    result = delete_event_workflow(event=sample_event, force=True)

    assert result["status"] == WorkflowStatus.SUCCESS
    mock_calendar_service.events.return_value.list.assert_not_called()


def test_get_event_details_by_query(mock_calendar_service, sample_event):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": [sample_event]
    }

    result = get_event_details_workflow(event_query="team sync")

    assert result["status"] == WorkflowStatus.SUCCESS
    assert result["event"]["summary"] == "Team Sync"
    assert len(result["event"]["attendees"]) == 2


def test_get_event_details_ambiguous(mock_calendar_service, sample_events_list):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": sample_events_list
    }

    result = get_event_details_workflow(event_query="team sync")

    assert result["status"] == WorkflowStatus.AMBIGUOUS
    assert result["tool"] == "get_event_details"


def test_get_event_details_with_preresolved_event(sample_event):
    result = get_event_details_workflow(event=sample_event)
    assert result["status"] == WorkflowStatus.SUCCESS
    assert result["event"]["location"] is None


def test_get_settings_returns_current_settings():
    result = get_settings_workflow()
    assert result["status"] == WorkflowStatus.SUCCESS
    assert "working_hours" in result["settings"]


def test_update_settings_no_fields_is_invalid():
    result = update_settings_workflow()
    assert result["status"] == WorkflowStatus.INVALID_REQUEST


def test_update_settings_persists_changes(tmp_path, monkeypatch):
    import app.workflows.settings as settings_module
    import json

    fake_settings_path = tmp_path / "settings.json"
    fake_settings_path.write_text(json.dumps({
        "working_hours": {"start": "09:00", "end": "17:00"},
        "event": {"default_duration": 60, "default_reminder": 15},
        "daily_briefing": {"enabled": False, "time": "08:00"},
        "time_zone": "Asia/Kolkata"
    }))
    monkeypatch.setattr(settings_module, "SETTINGS_PATH", fake_settings_path)

    result = update_settings_workflow(working_hours_start="10:00", time_zone="America/New_York")

    assert result["status"] == WorkflowStatus.SUCCESS
    assert result["settings"]["working_hours"]["start"] == "10:00"
    assert result["settings"]["time_zone"] == "America/New_York"

    reloaded = json.loads(fake_settings_path.read_text())
    assert reloaded["working_hours"]["start"] == "10:00"