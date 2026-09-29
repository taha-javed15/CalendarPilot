from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.workflows.settings import load_settings


def get_user_timezone() -> ZoneInfo:
    settings = load_settings()

    tz_name = settings.get("time_zone")

    if not tz_name:
        raise RuntimeError(
            "time_zone not set in settings.json"
        )

    try:
        return ZoneInfo(tz_name)

    except ZoneInfoNotFoundError as e:
        raise RuntimeError(
            f"Configured time_zone '{tz_name}' is not a valid IANA time zone."
        ) from e


def get_current_offset() -> str:
    tz = get_user_timezone()
    now = datetime.now(tz)

    offset = now.strftime("%z")  # e.g. '+0530'

    return f"{offset[:3]}:{offset[3:]}"


def _convert_datetime_field(field, tz: ZoneInfo):
    """
    Convert a Calendar API start/end field's `dateTime` into `tz`.
    All-day events use `date` instead of `dateTime` and have no time
    component - those (and anything not shaped like a Calendar
    start/end object) are returned unchanged.
    """
    if not isinstance(field, dict) or "dateTime" not in field:
        return field

    raw = field.get("dateTime")

    try:
        dt = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return field

    if dt.tzinfo is None:
        # The Calendar API always returns an offset or "Z", but if a
        # bare value ever shows up, treat it as UTC (Calendar's own
        # default) rather than silently leaving it unconverted.
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    localized = dt.astimezone(tz)

    converted = dict(field)
    converted["dateTime"] = localized.isoformat()
    converted["timeZone"] = str(tz)
    return converted


def localize_event(event: dict, tz: ZoneInfo) -> dict:
    """
    Returns a copy of a Calendar API event dict with `start`/`end`
    converted into `tz`. Only those two fields are touched - id,
    summary, attendees, etc. pass through unchanged. Returning a copy
    (rather than mutating in place) matters because the same event
    object flows through dispatcher into conversation.last_referenced_events;
    mutating it here would mean the cached copy and whatever gets sent
    back to Google on a later update share timestamps that no longer
    match the workflow's internal, non-localized working copy.
    """
    if not isinstance(event, dict):
        return event

    localized = dict(event)

    if "start" in event:
        localized["start"] = _convert_datetime_field(event["start"], tz)

    if "end" in event:
        localized["end"] = _convert_datetime_field(event["end"], tz)

    return localized


def localize_events_in_result(data, tz: ZoneInfo | None = None):
    """
    Recursively walks a workflow result (arbitrarily nested dicts/lists)
    and converts every Calendar-event-shaped dict's start/end into the
    user's configured timezone.

    Event data shows up in many different result shapes across the
    workflows - a single "event", a list under "events", nested lists
    like "deleted_events"/"failed_events", an ambiguity's
    "context.events", a conflict's "context.events", etc. Doing the
    conversion once, generically, at the single point every tool result
    already passes through (dispatcher.execute_tools) means every one of
    those shapes is covered automatically, and any workflow added later
    gets correct behavior for free instead of needing to remember to
    call a helper.

    An "event" is recognized structurally - any dict containing both a
    "start" and an "end" key, which is the shape every Calendar API
    event has. Plain strings (e.g. a create_event confirmation's
    "start"/"end" *arguments*, which are already-offset ISO strings, not
    nested {"dateTime": ...} objects) are left untouched by
    _convert_datetime_field's isinstance check, so this is safe to run
    over any tool result without needing to know its exact shape ahead
    of time.
    """
    if tz is None:
        tz = get_user_timezone()

    if isinstance(data, dict):
        if "start" in data and "end" in data:
            data = localize_event(data, tz)

        return {
            key: localize_events_in_result(value, tz)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [localize_events_in_result(item, tz) for item in data]

    return data