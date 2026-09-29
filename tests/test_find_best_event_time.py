from app.agent.memory.workflow_result import WorkflowStatus
from app.workflows.find_best_event_time import find_best_time_workflow


def test_find_best_time_returns_best_slot(mock_calendar_service, mock_small_llm):
    mock_calendar_service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {"primary": {"busy": []}}
    }
    mock_small_llm.queue('{"best_slot": {"start": "2026-08-10T09:00:00", "end": "2026-08-10T10:00:00"}}')

    result = find_best_time_workflow(
        start_time="2026-08-10T09:00:00",
        end_time="2026-08-10T18:00:00",
        event_summary="Team planning"
    )

    assert result["status"] == WorkflowStatus.SUCCESS
    assert result["best_slot"]["best_slot"]["start"] == "2026-08-10T09:00:00"


def test_find_best_time_no_free_slots_propagates_not_found(mock_calendar_service):
    mock_calendar_service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {"primary": {"busy": [{"start": "2026-08-10T09:00:00", "end": "2026-08-10T18:00:00"}]}}
    }

    result = find_best_time_workflow(
        start_time="2026-08-10T09:00:00",
        end_time="2026-08-10T18:00:00",
        event_summary="Team planning"
    )

    assert result["status"] == WorkflowStatus.NOT_FOUND


def test_find_best_time_invalid_llm_json_returns_invalid_request(mock_calendar_service, mock_small_llm):
    mock_calendar_service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {"primary": {"busy": []}}
    }
    mock_small_llm.queue("not valid json")

    result = find_best_time_workflow(
        start_time="2026-08-10T09:00:00",
        end_time="2026-08-10T18:00:00",
        event_summary="Team planning"
    )

    assert result["status"] == WorkflowStatus.INVALID_REQUEST
