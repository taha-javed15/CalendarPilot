from datetime import datetime

from app.calendar_api import get_calendar_service
from app.services.conflict_detection_service import find_conflicts
from app.agent.memory.workflow_result import WorkflowStatus
from app.utils.retry import with_retry
from app.workflows.settings import load_settings


def _parse_dt(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@with_retry()
def create_event(start, end, summary, description=None, location=None):
    service = get_calendar_service()
    settings = load_settings()
    tz = settings["time_zone"]

    event = {
        "start": {
            "dateTime": start,
            "timeZone": tz,
        },
        "end": {
            "dateTime": end,
            "timeZone": tz,
        },
        "summary": summary,
    }

    if description is not None:
        event["description"] = description

    if location is not None:
        event["location"] = location

    event_result = (
        service.events()
        .insert(
            calendarId="primary",
            body=event,
        )
        .execute()
    )

    return event_result


def create_event_workflow(
    start,
    end,
    summary,
    description=None,
    location=None,
    force=False,
):
    """
    `force=True` skips the conflict check. This is set when the user has
    already confirmed they want to create the event despite a known
    conflict - without it, re-running this workflow after confirmation
    would detect the same conflict again and ask forever.
    """
    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)

    if start_dt and end_dt and start_dt >= end_dt:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "The event's start time must be before its end time.",
        }

    if not force:
        conflicts = find_conflicts(start, end)

        if conflicts["conflict"]:
            return {
                "status": WorkflowStatus.CONFIRMATION_REQUIRED,
                "tool": "create_event",
                "arguments": {
                    "summary": summary,
                    "start": start,
                    "end": end,
                    "description": description,
                    "location": location,
                },
                "context": {
                    "events": conflicts["events"],
                },
            }

    event = create_event(
        start,
        end,
        summary,
        description=description,
        location=location,
    )

    return {
        "status": WorkflowStatus.SUCCESS,
        "event": event,
    }