from app.calendar_api import get_calendar_service
from app.services.event_service import find_single_event
from app.agent.memory.workflow_result import WorkflowStatus
from app.utils.retry import with_retry


def delete_event_workflow(
    event_query=None,
    event=None,
    force=False,
    start_time=None,
    end_time=None,
):
    if event is None:
        result = find_single_event(
            event_query,
            start_time,
            end_time,
        )

        if result["status"] == WorkflowStatus.AMBIGUOUS:
            return {
                "status": WorkflowStatus.AMBIGUOUS,
                "tool": "delete_event",
                "arguments": {
                    "event_query": event_query,
                    "start_time": start_time,
                    "end_time": end_time,
                },
                "context": {
                    "events": result["events"],
                },
            }

        if result["status"] != WorkflowStatus.SUCCESS:
            return result

        event = result["event"]

    if not force:
        # Store the already-resolved `event` object directly in
        # `arguments` rather than re-passing `event_query`/`start_time`/
        # `end_time`. Two bugs this fixes:
        #  1. This previously used the key "start_query" instead of
        #     "start_time", which doesn't match delete_event_workflow's
        #     actual parameter name - confirming a delete would crash
        #     with a TypeError ("unexpected keyword argument
        #     'start_query'") since that dict is passed straight back in
        #     via **arguments on confirm.
        #  2. Re-searching by event_query on confirm could, in principle,
        #     resolve to a different event than the one the user was
        #     actually shown and asked to confirm (e.g. if the calendar
        #     changed in between). Passing the exact resolved event
        #     avoids re-resolving it at all.
        return {
            "status": WorkflowStatus.CONFIRMATION_REQUIRED,
            "tool": "delete_event",
            "arguments": {
                "event": event,
            },
            "context": {
                "event": event,
            },
        }

    delete_event(event)

    return {
        "status": WorkflowStatus.SUCCESS,
        "message": "Event deleted successfully.",
        "deleted_event_id": event.get("id"),
    }


@with_retry()
def delete_event(event):
    service = get_calendar_service()

    service.events().delete(
        calendarId="primary",
        eventId=event["id"],
    ).execute()