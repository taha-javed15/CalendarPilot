from datetime import datetime
from app.calendar_api import get_calendar_service
from app.agent.memory.workflow_result import WorkflowStatus
from app.utils.retry import with_retry


def find_free_time_workflow(start_time, end_time):
    busy_periods = get_busy_times(start_time, end_time)

    free_slots = calculate_free_slots(
        busy_periods=busy_periods,
        start_time=start_time,
        end_time=end_time
    )

    if not free_slots:
        return {
            "status": WorkflowStatus.NOT_FOUND,
            "message": "No free slots were found in the given timeline."
        }

    return {
        "status": WorkflowStatus.SUCCESS,
        "free_slots": free_slots
    }


@with_retry()
def get_busy_times(start_time, end_time):
    service = get_calendar_service()

    result = service.freebusy().query(
        body={
            "timeMin": start_time,
            "timeMax": end_time,
            "items": [
                {"id": "primary"}
            ]
        }
    ).execute()

    return result["calendars"]["primary"]["busy"]


def calculate_free_slots(busy_periods, start_time, end_time):
    start_time = datetime.fromisoformat(start_time)
    end_time = datetime.fromisoformat(end_time)

    free_slots = []
    current = start_time

    for busy in busy_periods:
        busy_start = datetime.fromisoformat(busy["start"])
        busy_end = datetime.fromisoformat(busy["end"])

        if current < busy_start:
            free_slots.append({
                "start": current.isoformat(),
                "end": busy_start.isoformat()
            })

        if busy_end > current:
            current = busy_end

    if current < end_time:
        free_slots.append({
            "start": current.isoformat(),
            "end": end_time.isoformat()
        })

    return free_slots