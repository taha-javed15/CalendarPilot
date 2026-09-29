from unittest.mock import MagicMock
from app.agent.memory.workflow_result import WorkflowStatus
from app.services.conflict_detection_service import find_conflicts
from app.workflows.create_event import create_event_workflow


def test_find_conflicts_no_events_means_no_conflict(mock_calendar_service):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": []}

    result = find_conflicts("2026-08-10T09:00:00+05:30", "2026-08-10T10:00:00+05:30")

    assert result["conflict"] is False


def test_find_conflicts_with_events_means_conflict(mock_calendar_service, sample_event):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": [sample_event]}

    result = find_conflicts("2026-08-10T09:00:00+05:30", "2026-08-10T10:00:00+05:30")

    assert result["conflict"] is True
    assert result["events"] == [sample_event]


def test_create_event_no_conflict_creates_directly(mock_calendar_service, sample_event):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": []}
    mock_calendar_service.events.return_value.insert.return_value.execute.return_value = sample_event

    result = create_event_workflow(
        start="2026-08-10T10:00:00+05:30",
        end="2026-08-10T10:30:00+05:30",
        summary="Team Sync"
    )

    assert result["status"] == WorkflowStatus.SUCCESS
    assert result["event"] == sample_event


def test_create_event_conflict_requires_confirmation(mock_calendar_service, sample_event):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": [sample_event]}

    result = create_event_workflow(
        start="2026-08-10T10:00:00+05:30",
        end="2026-08-10T10:30:00+05:30",
        summary="Team Sync"
    )

    assert result["status"] == WorkflowStatus.CONFIRMATION_REQUIRED
    assert result["tool"] == "create_event"
    assert result["context"]["events"] == [sample_event]
    # insert should never have been called
    mock_calendar_service.events.return_value.insert.assert_not_called()


def test_create_event_force_bypasses_conflict_check(mock_calendar_service, sample_event):
    """
    Regression test: confirming a conflicted create_event must not re-check
    for conflicts, or the user gets stuck in an infinite confirmation loop.
    """
    mock_calendar_service.events.return_value.insert.return_value.execute.return_value = sample_event

    result = create_event_workflow(
        start="2026-08-10T10:00:00+05:30",
        end="2026-08-10T10:30:00+05:30",
        summary="Team Sync",
        force=True
    )

    assert result["status"] == WorkflowStatus.SUCCESS
    # list() (conflict check) must never be called when forcing
    mock_calendar_service.events.return_value.list.assert_not_called()
    mock_calendar_service.events.return_value.insert.assert_called_once()
