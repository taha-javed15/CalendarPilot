from datetime import datetime

from app.calendar_api import get_calendar_service
from app.services.event_service import find_single_event
from app.agent.memory.workflow_result import WorkflowStatus
from app.utils.retry import with_retry


def _parse_dt(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def update_event_workflow(
    event_query=None,
    summary=None,
    description=None,
    start=None,
    end=None,
    location=None,
    event=None,
    search_start=None,
    search_end=None,
):
    if all(value is None for value in [summary, description, start, end, location]):
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "No updates were provided.",
        }

    if event is None:
        result = find_single_event(
            event_query,
            search_start,
            search_end,
        )

        if result["status"] == WorkflowStatus.AMBIGUOUS:
            return {
                "status": WorkflowStatus.AMBIGUOUS,
                "tool": "update_event",
                "arguments": {
                    "event_query": event_query,
                    "summary": summary,
                    "description": description,
                    "start": start,
                    "end": end,
                    "location": location,
                    "search_start": search_start,
                    "search_end": search_end,
                },
                "context": {
                    "events": result["events"],
                },
            }

        if result["status"] != WorkflowStatus.SUCCESS:
            return result

        event = result["event"]

    if summary is not None:
        event["summary"] = summary

    if description is not None:
        event["description"] = description

    if location is not None:
        event["location"] = location

    if start is not None:
        event.setdefault("start", {})["dateTime"] = start

    if end is not None:
        event.setdefault("end", {})["dateTime"] = end

    # Validate the resulting start/end are sane before hitting the API -
    # previously a partial update (e.g. only moving the start time past
    # the existing end time) would be sent straight to Google Calendar
    # and come back as an opaque 400 error, surfaced to the user as a
    # generic "something went wrong" message.
    new_start = _parse_dt((event.get("start") or {}).get("dateTime"))
    new_end = _parse_dt((event.get("end") or {}).get("dateTime"))

    if new_start and new_end and new_start >= new_end:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "The event's start time must be before its end time.",
        }

    updated_event = update_event(event)

    return {
        "status": WorkflowStatus.SUCCESS,
        "event": updated_event,
    }


@with_retry()
def update_event(event):
    service = get_calendar_service()

    updated_event = (
        service.events()
        .update(
            calendarId="primary",
            eventId=event["id"],
            body=event,
        )
        .execute()
    )

    return updated_event