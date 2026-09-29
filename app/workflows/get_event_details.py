from app.services.event_service import find_single_event
from app.agent.memory.workflow_result import WorkflowStatus


def get_event_details_workflow(event_query=None, event=None, start_time=None, end_time=None):
    if event is None:
        result = find_single_event(event_query, start_time, end_time)

        if result["status"] == WorkflowStatus.AMBIGUOUS:
            return {
                "status": WorkflowStatus.AMBIGUOUS,
                "tool": "get_event_details",
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

    return {
        "status": WorkflowStatus.SUCCESS,
        "event": {
            "id": event.get("id"),
            "summary": event.get("summary"),
            "description": event.get("description"),
            "location": event.get("location"),
            "start": event.get("start"),
            "end": event.get("end"),
            "attendees": event.get("attendees", []),
            "reminders": event.get("reminders"),
            "creator": event.get("creator"),
            "organizer": event.get("organizer"),
            "conferenceData": event.get("conferenceData"),
            "status": event.get("status")
        }
    }