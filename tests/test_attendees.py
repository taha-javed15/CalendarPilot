from app.agent.memory.workflow_result import WorkflowStatus
from app.workflows.get_attendees import get_attendees_workflow
from app.workflows.get_attendee_status import get_attendee_status_workflow
from app.workflows.view_attendee_comments import view_attendee_comments_workflow
from app.workflows.update_attendees import update_attendees_workflow
from app.workflows.invite_attendees import invite_attendees_workflow


def test_get_attendees_with_preresolved_event(sample_event):
    """Regression test: get_attendees_workflow must accept event= directly."""
    result = get_attendees_workflow(event=sample_event)
    assert result["status"] == WorkflowStatus.SUCCESS
    assert len(result["attendees"]) == 2


def test_get_attendee_status_ambiguous_retags_tool_name(mock_calendar_service, sample_events_list):
    """
    Regression test: previously this leaked "get_attendees" as the tool
    name, so resolving the ambiguity would call the wrong workflow and
    return raw attendee objects instead of RSVP statuses.
    """
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": sample_events_list
    }

    result = get_attendee_status_workflow(event_query="team sync")

    assert result["status"] == WorkflowStatus.AMBIGUOUS
    assert result["tool"] == "get_attendee_status"
    assert result["context"]["events"] == sample_events_list


def test_get_attendee_status_with_preresolved_event(sample_event):
    result = get_attendee_status_workflow(event=sample_event)
    assert result["status"] == WorkflowStatus.SUCCESS
    assert result["attendees"][0]["response_status"] == "accepted"


def test_view_attendee_comments_ambiguous_retags_tool_name(mock_calendar_service, sample_events_list):
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": sample_events_list
    }

    result = view_attendee_comments_workflow(event_query="team sync")

    assert result["status"] == WorkflowStatus.AMBIGUOUS
    assert result["tool"] == "view_attendee_comments"


def test_view_attendee_comments_with_preresolved_event(sample_event):
    result = view_attendee_comments_workflow(event=sample_event)
    assert result["status"] == WorkflowStatus.SUCCESS
    assert result["comments"][0]["email"] == "bob@example.com"


def test_update_attendees_with_preresolved_event(mock_calendar_service, sample_event):
    """Regression test: update_attendees_workflow must accept event= directly."""
    import copy
    updated = copy.deepcopy(sample_event)
    mock_calendar_service.events.return_value.update.return_value.execute.return_value = updated

    result = update_attendees_workflow(event=sample_event, add_attendees=["carol@example.com"])

    assert result["status"] == WorkflowStatus.SUCCESS
    assert "carol@example.com" in result["attendees_added"]
    mock_calendar_service.events.return_value.list.assert_not_called()


def test_invite_attendees_with_preresolved_event_does_not_crash(mock_calendar_service, sample_event):
    """
    Regression test: invite_attendees_workflow always called
    update_attendees_workflow(event=...), which previously had no `event`
    parameter and would raise TypeError.
    """
    import copy
    updated = copy.deepcopy(sample_event)
    mock_calendar_service.events.return_value.update.return_value.execute.return_value = updated

    result = invite_attendees_workflow(attendees=["dave@example.com"], event=sample_event)

    assert result["status"] == WorkflowStatus.SUCCESS
    assert "dave@example.com" in result["attendees_added"]
