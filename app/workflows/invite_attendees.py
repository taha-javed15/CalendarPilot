from app.workflows.update_attendees import update_attendees_workflow


def invite_attendees_workflow(event_query=None, attendees=None, event=None, start_time=None, end_time=None):
    if event is None:
        return update_attendees_workflow(
            event_query=event_query,
            add_attendees=attendees,
            start_time=start_time,
            end_time=end_time
        )

    return update_attendees_workflow(
        event=event,
        add_attendees=attendees
    )