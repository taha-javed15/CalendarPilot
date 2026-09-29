from app.calendar_api import find_events_by_query
from app.agent.memory.workflow_result import WorkflowStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


def find_single_event(event_query, start_time=None, end_time=None):
    events = find_events_by_query(
        event_query,
        start_time,
        end_time,
    )

    logger.info(
        "Found events",
        extra={
            "event_query": event_query,
            "start_time": start_time,
            "end_time": end_time,
            "count": len(events),
            "events": events,
        },
    )

    if len(events) == 0:
        return {
            "status": WorkflowStatus.NOT_FOUND,
            "message": f"No event matching '{event_query}' was found.",
        }

    if len(events) > 1:
        return {
            "status": WorkflowStatus.AMBIGUOUS,
            "events": events,
        }

    event = events[0]

    return {
        "status": WorkflowStatus.SUCCESS,
        "event": event,
    }