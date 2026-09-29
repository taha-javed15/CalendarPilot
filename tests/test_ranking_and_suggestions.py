from app.services.ranking_service import rank_slots
from app.workflows.suggest_alternative_times import suggest_alternative_times_workflow
from app.agent.memory.workflow_result import WorkflowStatus


def test_rank_slots_strips_markdown_fences(mock_small_llm):
    mock_small_llm.queue('```json\n{"best_slot": {"start": "a", "end": "b"}}\n```')

    result = rank_slots("Gym", [{"start": "a", "end": "b"}], {"start": "09:00", "end": "17:00"})

    assert result == {"best_slot": {"start": "a", "end": "b"}}


def test_rank_slots_handles_plain_json(mock_small_llm):
    mock_small_llm.queue('{"best_slot": {"start": "a", "end": "b"}}')

    result = rank_slots("Gym", [{"start": "a", "end": "b"}], {"start": "09:00", "end": "17:00"})

    assert result == {"best_slot": {"start": "a", "end": "b"}}


def test_rank_slots_invalid_json_returns_none(mock_small_llm):
    mock_small_llm.queue("not json at all")

    result = rank_slots("Gym", [], {"start": "09:00", "end": "17:00"})

    assert result is None


def test_suggest_alternative_times_respects_max_suggestions(mock_calendar_service):
    """Regression test: max_suggestions is in the tool schema but the
    workflow never accepted it as a parameter - this would previously
    raise TypeError if the LLM passed it."""
    mock_calendar_service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {"primary": {"busy": []}}
    }

    result = suggest_alternative_times_workflow(
        start_time="2026-08-10T09:00:00",
        end_time="2026-08-10T18:00:00",
        event_duration=30,
        max_suggestions=1
    )

    assert result["status"] == WorkflowStatus.SUCCESS
    assert len(result["suggestions"]) == 1
