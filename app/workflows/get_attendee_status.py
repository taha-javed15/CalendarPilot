from app.workflows.get_attendees import get_attendees_workflow
from app.agent.memory.workflow_result import WorkflowStatus


def get_attendee_status_workflow(event_query=None, event=None, start_time=None, end_time=None):
    result = get_attendees_workflow(
        event_query=event_query,
        event=event,
        start_time=start_time,
        end_time=end_time
    )

    if result["status"] == WorkflowStatus.AMBIGUOUS:
        return {
            "status": WorkflowStatus.AMBIGUOUS,
            "tool": "get_attendee_status",
            "arguments": {
                "event_query": event_query,
                "start_time": start_time,
                "end_time": end_time
            },
            "context": result["context"]
        }

    if result["status"] != WorkflowStatus.SUCCESS:
        return result

    attendees = result["attendees"]
    statuses = []

    for attendee in attendees:
        statuses.append(
            {
                "email": attendee.get("email"),
                "name": attendee.get("displayName"),
                "response_status": attendee.get("responseStatus")
            }
        )

    return {
        "status": WorkflowStatus.SUCCESS,
        "event": result["event"],
        "event_summary": result["event_summary"],
        "attendees": statuses
    }