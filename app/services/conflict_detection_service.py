from app.calendar_api import find_events
from app.agent.memory.workflow_result import WorkflowStatus


def find_conflicts(start_time, end_time):
    result = find_events(start_time, end_time)

    if result["status"] == WorkflowStatus.SUCCESS:
        return {
            "conflict": True,
            "events": result["events"],
        }

    if result["status"] == WorkflowStatus.ERROR:
        # Propagate calendar errors instead of silently treating them as
        # "no conflict" - we'd rather ask again than double-book someone.
        raise RuntimeError(
            result.get("message", "Failed to check for conflicts.")
        )

    return {
        "conflict": False,
        "events": None,
    }