from datetime import datetime
from app.workflows.find_free_time import find_free_time_workflow
from app.workflows.settings import load_settings
from app.agent.memory.workflow_result import WorkflowStatus


def suggest_alternative_times_workflow(start_time, end_time, event_duration=None, max_suggestions=None):
    if event_duration is None:
        settings = load_settings()
        event_duration = settings["event"]["default_duration"]

    result = find_free_time_workflow(start_time, end_time)

    if result["status"] != WorkflowStatus.SUCCESS:
        return result

    free_slots = result["free_slots"]
    suggestions = []

    for slot in free_slots:
        slot_start = datetime.fromisoformat(slot["start"])
        slot_end = datetime.fromisoformat(slot["end"])

        duration = (slot_end - slot_start).total_seconds() / 60

        if duration >= event_duration:
            suggestions.append(slot)

    if max_suggestions is not None:
        suggestions = suggestions[:max_suggestions]

    if not suggestions:
        return {
            "status": WorkflowStatus.NOT_FOUND,
            "message": "Either no available time was found or no slots are long enough for the requested event."
        }

    return {
        "status": WorkflowStatus.SUCCESS,
        "suggestions": suggestions
    }