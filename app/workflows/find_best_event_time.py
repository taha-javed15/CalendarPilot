from app.workflows.suggest_alternative_times import suggest_alternative_times_workflow
from app.workflows.settings import load_settings
from app.services.ranking_service import rank_slots
from app.agent.memory.workflow_result import WorkflowStatus


def find_best_time_workflow(start_time, end_time, event_summary, working_hours=None, event_duration=None):
    if event_duration is None or working_hours is None:
        settings = load_settings()

    if event_duration is None:
        event_duration = settings["event"]["default_duration"]

    if working_hours is None:
        working_hours = settings["working_hours"]

    result = suggest_alternative_times_workflow(start_time, end_time, event_duration)

    if result["status"] != WorkflowStatus.SUCCESS:
        return result

    best_slot = rank_slots(event_summary, result["suggestions"], working_hours)

    if not best_slot:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "Could not determine the best time slot."
        }

    return {
        "status": WorkflowStatus.SUCCESS,
        "best_slot": best_slot
    }