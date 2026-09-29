from app.calendar_api import find_events, get_event_by_id
from app.workflows.create_event import create_event_workflow
from app.workflows.update_event import update_event_workflow
from app.workflows.delete_event import delete_event_workflow
from app.workflows.batch_delete_events import batch_delete_events_workflow
from app.workflows.find_free_time import find_free_time_workflow
from app.workflows.settings import get_settings_workflow, update_settings_workflow
from app.workflows.find_best_event_time import find_best_time_workflow
from app.workflows.invite_attendees import invite_attendees_workflow
from app.workflows.suggest_alternative_times import suggest_alternative_times_workflow
from app.workflows.update_attendees import update_attendees_workflow
from app.workflows.get_attendee_status import get_attendee_status_workflow
from app.workflows.get_attendees import get_attendees_workflow
from app.workflows.view_attendee_comments import view_attendee_comments_workflow
from app.workflows.configure_reminders import configure_reminders_workflow
from app.workflows.get_event_details import get_event_details_workflow
from app.agent.memory.workflow_result import WorkflowStatus
from app.services.reference_resolution_service import resolve_reference
from app.utils.timezone import get_current_offset, get_user_timezone, localize_events_in_result
from app.utils.logger import get_logger

logger = get_logger(__name__)

tool_map = {
    "create_event": create_event_workflow,
    "update_event": update_event_workflow,
    "list_events": find_events,
    "delete_event": delete_event_workflow,
    "batch_delete_events": batch_delete_events_workflow,
    "find_free_time": find_free_time_workflow,
    "get_settings": get_settings_workflow,
    "update_settings": update_settings_workflow,
    "find_best_event_time": find_best_time_workflow,
    "invite_attendees": invite_attendees_workflow,
    "suggest_alternative_times": suggest_alternative_times_workflow,
    "update_attendees": update_attendees_workflow,
    "get_attendee_status": get_attendee_status_workflow,
    "get_attendees": get_attendees_workflow,
    "view_attendee_comments": view_attendee_comments_workflow,
    "configure_reminders": configure_reminders_workflow,
    "get_event_details": get_event_details_workflow
}

# Tools that can benefit from conversational reference resolution
REFERENCE_RESOLVABLE_TOOLS = {
    "update_event", "delete_event", "invite_attendees", "update_attendees",
    "get_attendee_status", "get_attendees", "view_attendee_comments",
    "configure_reminders", "get_event_details",
}

# Datetime fields that need timezone offset validation
_DATETIME_FIELDS = {"start", "end", "start_time", "end_time", "search_start", "search_end"}

_DATE_ONLY_LENGTH = 10


def _validate_cached_events(events: list) -> list:
    """
    Filter out events that no longer exist in the live calendar, and
    replace each entry with its current server state (rather than the
    stale cached copy) so downstream workflows always mutate fresh data.
    """
    valid = []
    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        try:
            fresh_event = get_event_by_id(event_id)
        except Exception as e:
            logger.warning(
                "Could not verify cached event, dropping it from context",
                extra={"event_id": event_id, "error": str(e)}
            )
            continue
        if fresh_event is not None:
            valid.append(fresh_event)
    return valid


def _resolve_against_conversation(tool_name, arguments, conversation=None):
    if conversation is None or tool_name not in REFERENCE_RESOLVABLE_TOOLS:
        return None, arguments

    event_query = arguments.get("event_query")
    if not event_query or arguments.get("event") is not None:
        return None, arguments

    recent_events = conversation.get_last_referenced_events()
    if not recent_events:
        return None, arguments

    recent_events = _validate_cached_events(recent_events)
    if not recent_events:
        conversation.set_last_referenced_events([])
        return None, arguments

    outcome, payload = resolve_reference(event_query, recent_events)

    if outcome == "resolved":
        logger.info(
            "Resolved event reference from conversation context",
            extra={"tool": tool_name, "event_query": event_query, "resolved_event_id": payload.get("id")}
        )
        new_arguments = dict(arguments)
        new_arguments.pop("event_query", None)
        new_arguments["event"] = payload
        return None, new_arguments

    if outcome == "ambiguous":
        logger.info(
            "Event reference ambiguous among recently-shown events",
            extra={"tool": tool_name, "event_query": event_query, "candidate_count": len(payload)}
        )
        return {
            "status": WorkflowStatus.AMBIGUOUS,
            "tool": tool_name,
            "arguments": arguments,
            "context": {"events": payload}
        }, arguments

    return None, arguments


def _remember_referenced_events(conversation, result):
    """Store successfully retrieved events for conversational context."""
    if conversation is None:
        return
    if result.get("status") != WorkflowStatus.SUCCESS:
        return

    if "events" in result and result["events"]:
        conversation.set_last_referenced_events(result["events"])
    elif "event" in result and result["event"]:
        conversation.set_last_referenced_events([result["event"]])


def _invalidate_deleted_events(conversation, result):
    """Remove deleted event IDs from the conversation cache."""
    if conversation is None:
        return

    deleted_ids = set()
    if result.get("deleted_event_id"):
        deleted_ids.add(result["deleted_event_id"])
    for eid in result.get("deleted_event_ids", []):
        deleted_ids.add(eid)

    if deleted_ids and conversation.last_referenced_events:
        conversation.last_referenced_events = [
            e for e in conversation.last_referenced_events
            if e.get("id") not in deleted_ids
        ]


def _localize_result(result):
    """
    Convert every Calendar-event timestamp in a tool result into the
    user's configured timezone before it reaches any LLM or gets cached
    for conversational reference. See localize_events_in_result for why
    this lives here rather than in each individual workflow.

    Defensive by design: this touches the output of every single tool
    call, so a bad settings.json (invalid time_zone) or an unexpected
    result shape must never take down the whole response - fall back to
    the raw, unlocalized result and log it instead.
    """
    try:
        tz = get_user_timezone()
        return localize_events_in_result(result, tz)
    except Exception as e:
        logger.warning(
            "Could not localize event times, returning raw result",
            extra={"error": str(e)}
        )
        return result


# -------------------------------------------------------------------------
# Datetime normalization (for outgoing tool arguments, not display)
# -------------------------------------------------------------------------

def _ensure_offset(dt_string: str) -> str:
    if not dt_string or not isinstance(dt_string, str):
        return dt_string

    stripped = dt_string.strip()

    if len(stripped) == _DATE_ONLY_LENGTH and stripped.count("-") == 2 and "T" not in stripped:
        return stripped

    if stripped.endswith("Z"):
        return stripped

    if len(stripped) >= 6 and stripped[-3] == ":" and stripped[-6] in "+-":
        return stripped

    offset = get_current_offset()
    return f"{stripped}{offset}"


def _normalize_datetime_args(arguments: dict) -> dict:
    normalized = {}
    for key, value in arguments.items():
        if key in _DATETIME_FIELDS and isinstance(value, str):
            normalized[key] = _ensure_offset(value)
        else:
            normalized[key] = value
    return normalized


# -------------------------------------------------------------------------
# Main entry point
# -------------------------------------------------------------------------

def execute_tools(tool_name, arguments, conversation=None):
    tool = tool_map.get(tool_name)

    if tool is None:
        logger.warning("Unknown tool requested", extra={"tool": tool_name})
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": f"Unknown tool: {tool_name}"
        }

    # 1. Resolve event references against conversation context
    early_result, arguments = _resolve_against_conversation(
        tool_name, arguments, conversation
    )
    if early_result is not None:
        # This path (an ambiguous reference resolved from cached events)
        # previously returned straight past every step below it,
        # including timezone localization - an ambiguity list shown to
        # the user here would display raw, unconverted times. Route it
        # through the same finalize step as every other return.
        return _localize_result(early_result)

    # 2. Normalize datetime arguments (ensure timezone offsets)
    arguments = _normalize_datetime_args(arguments)

    logger.info("Tool selected", extra={"tool": tool_name, "arguments": arguments})

    # 3. Execute the tool
    try:
        result = tool(**arguments)
    except TypeError as e:
        logger.error("Tool called with invalid arguments", extra={"tool": tool_name, "error": str(e)})
        return {
            "status": WorkflowStatus.INVALID_REQUEST,
            "message": "That request couldn't be completed because some required information was missing or invalid."
        }
    except Exception as e:
        logger.error("Tool execution failed", extra={"tool": tool_name, "error": str(e)})
        return {
            "status": WorkflowStatus.ERROR,
            "message": (
                "Something went wrong while talking to Google Calendar or "
                "the scheduling service. Please try again in a moment."
            )
        }

    # 4. Localize event times to the user's configured timezone before
    #    anything downstream (caching, LLM response generation) sees them.
    result = _localize_result(result)

    # 5. Remember events for future conversational context
    _remember_referenced_events(conversation, result)

    # 6. Invalidate cache for deleted events
    if tool_name in ("delete_event", "batch_delete_events") and result.get("status") == WorkflowStatus.SUCCESS:
        _invalidate_deleted_events(conversation, result)

    logger.info("Tool completed", extra={"tool": tool_name, "status": str(result.get("status"))})
    return result