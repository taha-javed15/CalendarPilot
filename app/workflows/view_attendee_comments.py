from app.workflows.get_attendees import get_attendees_workflow
from app.agent.memory.workflow_result import WorkflowStatus


def view_attendee_comments_workflow(event_query=None, event=None, start_time=None, end_time=None):
    result = get_attendees_workflow(
        event_query=event_query,
        event=event,
        start_time=start_time,
        end_time=end_time
    )

    if result["status"] == WorkflowStatus.AMBIGUOUS:
        return {
            "status": WorkflowStatus.AMBIGUOUS,
            "tool": "view_attendee_comments",
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
    comments = []

    for attendee in attendees:
        comment = attendee.get("comment")
        if comment:
            comments.append({
                "email": attendee.get("email"),
                "name": attendee.get("displayName"),
                "comment": comment
            })

    if len(comments) == 0:
        return {
            "status": WorkflowStatus.NOT_FOUND,
            "message": "No attendee comments were found."
        }

    return {
        "status": WorkflowStatus.SUCCESS,
        "event": result["event"],
        "event_summary": result["event_summary"],
        "comments": comments
    }