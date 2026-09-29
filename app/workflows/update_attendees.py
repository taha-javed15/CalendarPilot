from app.services.event_service import find_single_event
from app.workflows.update_event import update_event
from app.agent.memory.workflow_result import WorkflowStatus


def update_attendees_workflow(
    event_query=None,
    add_attendees=None,
    remove_attendees=None,
    event=None,
    start_time=None,
    end_time=None,
):
    if not add_attendees and not remove_attendees:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "No attendee updates were provided.",
        }

    if event is None:
        result = find_single_event(
            event_query,
            start_time,
            end_time,
        )

        if result["status"] == WorkflowStatus.AMBIGUOUS:
            return {
                "status": WorkflowStatus.AMBIGUOUS,
                "tool": "update_attendees",
                "arguments": {
                    "event_query": event_query,
                    "add_attendees": add_attendees,
                    "remove_attendees": remove_attendees,
                    "start_time": start_time,
                    "end_time": end_time,
                },
                "context": {
                    "events": result["events"],
                },
            }

        if result["status"] != WorkflowStatus.SUCCESS:
            return result

        event = result["event"]

    if "attendees" not in event:
        event["attendees"] = []

    # Some attendees (e.g. calendar resources) may lack an "email" key -
    # using .get() instead of ["email"] avoids a KeyError crash on those.
    existing = {
        attendee.get("email")
        for attendee in event["attendees"]
        if attendee.get("email")
    }

    removed = []

    if remove_attendees:
        remove_set = set(remove_attendees)

        for email in remove_attendees:
            if email in existing:
                removed.append(email)

        event["attendees"] = [
            attendee
            for attendee in event["attendees"]
            if attendee.get("email") not in remove_set
        ]

        existing = {
            attendee.get("email")
            for attendee in event["attendees"]
            if attendee.get("email")
        }

    added = []

    if add_attendees:
        for email in add_attendees:
            if email not in existing:
                event["attendees"].append({"email": email})
                existing.add(email)
                added.append(email)

    if not added and not removed:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "The attendee list is already up to date.",
            "attendees": event["attendees"],
        }

    updated_event = update_event(event)

    return {
        "status": WorkflowStatus.SUCCESS,
        "attendees_added": added,
        "attendees_removed": removed,
        "event": updated_event,
        "attendees": updated_event.get("attendees", []),
    }