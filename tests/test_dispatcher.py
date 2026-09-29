from app.agent.memory.workflow_result import WorkflowStatus
from app.dispatcher import execute_tools


def test_unknown_tool_returns_invalid_request():
    result = execute_tools("not_a_real_tool", {})
    assert result["status"] == WorkflowStatus.INVALID_REQUEST


def test_tool_exception_is_caught_and_returns_error(monkeypatch):
    def boom(**kwargs):
        raise ConnectionError("simulated network failure")

    monkeypatch.setitem(__import__("app.dispatcher", fromlist=["tool_map"]).tool_map, "list_events", boom)

    result = execute_tools("list_events", {"start_time": "x", "end_time": "y"})

    assert result["status"] == WorkflowStatus.ERROR
    assert "went wrong" in result["message"].lower()


def test_successful_tool_call_passes_through(mock_calendar_service):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {"items": []}

    result = execute_tools("list_events", {"start_time": "2026-08-10T00:00:00+05:30", "end_time": "2026-08-11T00:00:00+05:30"})

    assert result["status"] == WorkflowStatus.NOT_FOUND
