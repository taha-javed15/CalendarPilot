from app.services.event_service import find_single_event
from app.workflows.update_event import update_event
from app.agent.memory.workflow_result import WorkflowStatus


def configure_reminders_workflow(event_query=None, event=None, use_default: bool | None = None, reminders: list | None = None, start_time=None, end_time=None):
    if use_default is None and reminders is None:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "No reminder settings were provided."
        }

    if use_default is False and reminders is None:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "Custom reminders must be provided when use_default is False."
        }

    if event is None:
        result = find_single_event(event_query, start_time, end_time)

        if result["status"] == WorkflowStatus.AMBIGUOUS:
            return {
                "status": WorkflowStatus.AMBIGUOUS,
                "tool": "configure_reminders",
                "arguments": {
                    "event_query": event_query,
                    "use_default": use_default,
                    "reminders": reminders,
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

    if use_default is not None:
        event["reminders"] = {
            "useDefault": use_default
        }

    if reminders is not None:
        event["reminders"] = {
            "useDefault": False,
            "overrides": reminders
        }

    updated_event = update_event(event)

    return {
        "status": WorkflowStatus.SUCCESS,
        "event": updated_event,
        "reminders": updated_event.get("reminders")
    }