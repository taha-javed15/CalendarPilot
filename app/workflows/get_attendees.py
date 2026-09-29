from app.services.event_service import find_single_event
from app.agent.memory.workflow_result import WorkflowStatus


def get_attendees_workflow(event_query=None, event=None, start_time=None, end_time=None):
    if event is None:
        result = find_single_event(event_query, start_time, end_time)

        if result["status"] == WorkflowStatus.AMBIGUOUS:
            return {
                "status": WorkflowStatus.AMBIGUOUS,
                "tool": "get_attendees",
                "arguments": {
                    "event_query": event_query,
                    "start_time": start_time,
                    "end_time": end_time
                },
                "context": {
                    "events": result["events"]
                }
            }

        if result["status"] != WorkflowStatus.SUCCESS:
            return result

        event = result["event"]

    attendees = event.get("attendees", [])

    if len(attendees) == 0:
        return {
            "status": WorkflowStatus.NOT_FOUND,
            "message": "This event has no attendees."
        }

    return {
        "status": WorkflowStatus.SUCCESS,
        "event": event,
        "event_summary": event.get("summary"),
        "attendees": attendees
    }