from app.agent.memory.workflow_result import WorkflowStatus
from app.workflows.configure_reminders import configure_reminders_workflow


def test_configure_reminders_ambiguous_uses_events_key(mock_calendar_service, sample_events_list):
    """
    Regression test: this used to store ambiguous events under
    "ambiguous_events" while everything else (and the disambiguation
    resolver) reads "events" - reminders could never be disambiguated.
    """
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": sample_events_list
    }

    result = configure_reminders_workflow(event_query="team sync", use_default=False, reminders=[{"method": "popup", "minutes": 10}])

    assert result["status"] == WorkflowStatus.AMBIGUOUS
    assert "events" in result["context"]
    assert result["context"]["events"] == sample_events_list


def test_configure_reminders_with_preresolved_event(mock_calendar_service, sample_event):
    import copy
    updated = copy.deepcopy(sample_event)
    updated["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}
    mock_calendar_service.events.return_value.update.return_value.execute.return_value = updated

    result = configure_reminders_workflow(event=sample_event, reminders=[{"method": "popup", "minutes": 10}])

    assert result["status"] == WorkflowStatus.SUCCESS
    assert result["reminders"]["overrides"][0]["minutes"] == 10


def test_configure_reminders_no_settings_is_invalid():
    result = configure_reminders_workflow(event_query="team sync")
    assert result["status"] == WorkflowStatus.INVALID_REQUEST
