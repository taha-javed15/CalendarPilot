import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.agent.memory.workflow_result import WorkflowStatus


BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "data" / "settings.json"

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def load_settings():
    with open(SETTINGS_PATH, "r") as file:
        return json.load(file)


def save_settings(settings):
    with open(SETTINGS_PATH, "w") as file:
        json.dump(settings, file, indent=4)


def get_settings_workflow():
    settings = load_settings()

    return {
        "status": WorkflowStatus.SUCCESS,
        "settings": settings,
    }


def _is_valid_time(value: str) -> bool:
    return bool(_TIME_RE.match(value))


def _is_valid_timezone(value: str) -> bool:
    try:
        ZoneInfo(value)
        return True
    except ZoneInfoNotFoundError:
        return False


def update_settings_workflow(
    working_hours_start: str | None = None,
    working_hours_end: str | None = None,
    event_default_duration: int | None = None,
    event_default_reminder: int | None = None,
    daily_briefing_enabled: bool | None = None,
    daily_briefing_time: str | None = None,
    time_zone: str | None = None,
):
    if all(
        value is None
        for value in [
            working_hours_start,
            working_hours_end,
            event_default_duration,
            event_default_reminder,
            daily_briefing_enabled,
            daily_briefing_time,
            time_zone,
        ]
    ):
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "No settings were provided.",
        }

    # Validate inputs up front so a bad value (typo'd time zone, malformed
    # HH:MM string, negative duration) can't get written to settings.json
    # and then silently break something else later (e.g. get_current_offset
    # raising on every subsequent request because of a bad time_zone).
    for label, value in (
        ("working_hours_start", working_hours_start),
        ("working_hours_end", working_hours_end),
        ("daily_briefing_time", daily_briefing_time),
    ):
        if value is not None and not _is_valid_time(value):
            return {
                "status": WorkflowStatus.INVALID_REQUEST,
                "message": (
                    f"'{value}' is not a valid time for "
                    f"{label.replace('_', ' ')}. Please use 24-hour HH:MM format."
                ),
            }

    if event_default_duration is not None and event_default_duration <= 0:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "Default event duration must be a positive number of minutes.",
        }

    if event_default_reminder is not None and event_default_reminder < 0:
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "Default reminder time can't be negative.",
        }

    if time_zone is not None and not _is_valid_timezone(time_zone):
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": (
                f"'{time_zone}' is not a recognized time zone. "
                "Please use an IANA time zone name, e.g. 'Asia/Kolkata'."
            ),
        }

    if (
        working_hours_start is not None
        and working_hours_end is not None
        and working_hours_start >= working_hours_end
    ):
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "Working hours start must be earlier than working hours end.",
        }

    settings = load_settings()

    if working_hours_start is not None:
        settings["working_hours"]["start"] = working_hours_start

    if working_hours_end is not None:
        settings["working_hours"]["end"] = working_hours_end

    if event_default_duration is not None:
        settings["event"]["default_duration"] = event_default_duration

    if event_default_reminder is not None:
        settings["event"]["default_reminder"] = event_default_reminder

    if daily_briefing_enabled is not None:
        settings["daily_briefing"]["enabled"] = daily_briefing_enabled

    if daily_briefing_time is not None:
        settings["daily_briefing"]["time"] = daily_briefing_time

    if time_zone is not None:
        settings["time_zone"] = time_zone

    save_settings(settings)

    return {
        "status": WorkflowStatus.SUCCESS,
        "message": "Settings updated successfully.",
        "settings": settings,
    }