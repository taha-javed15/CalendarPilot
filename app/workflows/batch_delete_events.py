from app.calendar_api import find_events_by_query
from app.workflows.delete_event import delete_event
from app.agent.memory.workflow_result import WorkflowStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

# "Delete all" should not be silently capped at the same limit used for
# single-event disambiguation lookups (see find_events_by_query) - a
# user asking to clear their whole day shouldn't have some events left
# behind with no indication anything was skipped. 250 is Calendar's
# per-request maximum.
BATCH_DELETE_SEARCH_LIMIT = 250


def batch_delete_events_workflow(event_query=None, start_time=None, end_time=None, events=None, force=False):
    """
    Find all events matching the query (optionally within a time window)
    and delete them. Requires confirmation unless force=True.

    `events`, when provided, is the exact, already-resolved list from a
    prior confirmation step - it's used as-is instead of re-searching, so
    what gets deleted on confirm is exactly what the user was shown, even
    if the calendar changed in the meantime.

    `event_query` is intentionally optional. For a broad "delete all
    events [in this time range]" request, the caller (the LLM, per its
    tool description) should omit it entirely - Google's `q` search
    parameter is a fuzzy text match, not an "everything" wildcard, so
    passing any generic placeholder term here would narrow the search to
    only events whose text happens to contain that word instead of
    matching every event in the window.
    """
    if events is None:
        events = find_events_by_query(
            event_query,
            start_time,
            end_time,
            max_results=BATCH_DELETE_SEARCH_LIMIT,
        )

    if not events:
        message = (
            f"No events matching '{event_query}' were found."
            if event_query
            else "No events were found in that time range."
        )
        return {
            "status": WorkflowStatus.NOT_FOUND,
            "message": message
        }

    if not force:
        return {
            "status": WorkflowStatus.CONFIRMATION_REQUIRED,
            "tool": "batch_delete_events",
            "arguments": {
                "events": events
            },
            "context": {
                "events": events,
                "count": len(events)
            }
        }

    deleted = []
    failed = []

    for event in events:
        try:
            delete_event(event)
            deleted.append(event)
        except Exception as e:
            logger.error(
                "Batch delete failed for event",
                extra={"event_id": event.get("id"), "error": str(e)}
            )
            failed.append({"event": event, "error": str(e)})

    return {
        "status": WorkflowStatus.SUCCESS,
        "message": f"Deleted {len(deleted)} event(s).",
        "deleted_count": len(deleted),
        "failed_count": len(failed),
        "deleted_event_ids": [e["id"] for e in deleted],
        "deleted_events": deleted,
        "failed_events": failed
    }