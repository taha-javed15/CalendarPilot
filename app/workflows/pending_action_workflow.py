from app.dispatcher import execute_tools, _validate_cached_events
from app.agent.memory.pending_action import PendingActionType
from app.services.confirmation_service import confirm_user_intent, UserIntent
from app.services.disambiguation_service import resolve_ambiguity
from app.services.response_generation_service import generate_response
from app.workflows.pending_action_helper import (
    needs_pending_action,
    stash_pending_action_and_reply,
)
from app.exceptions import LLMServiceError
from app.utils.logger import get_logger

logger = get_logger(__name__)

FRIENDLY_LLM_ERROR = (
    "I'm having trouble reaching the assistant service right now. "
    "Please try again in a moment."
)


def handle_pending_action(conversation, user_message):
    pending_action = conversation.get_pending_action()

    if pending_action.is_expired():
        pending_action.mark_expired()
        conversation.clear_pending_action()
        return (
            "Your previous request has expired. "
            "Please tell me what you'd like to do again."
        )

    try:
        if pending_action.action_type == PendingActionType.CONFIRMATION:
            return _handle_confirmation(conversation, pending_action, user_message)

        return _handle_ambiguity(conversation, pending_action, user_message)

    except LLMServiceError:
        return FRIENDLY_LLM_ERROR

    except Exception as e:
        logger.error(
            "Unexpected error in pending action handler",
            extra={"error": str(e)},
            exc_info=True,
        )
        conversation.clear_pending_action()
        return (
            "Something went wrong with that request. "
            "I had to delete that request - please try again."
        )


def _handle_confirmation(conversation, pending_action, user_message):
    intent = confirm_user_intent(user_message)

    if intent == UserIntent.CONFIRM:
        pending_action.mark_completed()
        conversation.clear_pending_action()

        arguments = dict(pending_action.arguments)

        if pending_action.tool in (
            "create_event",
            "delete_event",
            "batch_delete_events",
        ):
            # Without this, re-running the workflow would detect the same
            # conflict / ask for confirmation again and loop forever.
            arguments["force"] = True

        return _execute_and_respond(
            conversation,
            pending_action.tool,
            arguments,
        )

    if intent == UserIntent.CANCEL:
        pending_action.mark_cancelled()
        conversation.clear_pending_action()
        return "Okay, I've cancelled that request."

    if intent == UserIntent.NEW_REQUEST:
        pending_action.mark_cancelled()
        conversation.clear_pending_action()

        from app.workflows.normal_request_workflow import handle_normal_request

        return handle_normal_request(conversation, user_message)

    return (
        "I'm not sure whether you want to continue or cancel the previous "
        "request - could you confirm with a yes or no?"
    )


def _handle_ambiguity(conversation, pending_action, user_message):
    events = pending_action.context.get("events", [])
    valid_events = _validate_cached_events(events)

    if not valid_events:
        pending_action.mark_cancelled()
        conversation.clear_pending_action()
        return (
            "The events I showed you earlier are no longer available."
            "please tell me what you'd like to do again."
        )

    if len(valid_events) != len(events):
        pending_action.context["events"] = valid_events

    resolution = resolve_ambiguity(user_message, valid_events)

    if resolution == "NEW_REQUEST":
        pending_action.mark_cancelled()
        conversation.clear_pending_action()

        from app.workflows.normal_request_workflow import handle_normal_request

        return handle_normal_request(conversation, user_message)

    if resolution is None:
        return (
            "I couldn't tell which event you meant. Could you describe it "
            "more specifically - by date, time, or title?"
        )

    chosen_event = valid_events[resolution]

    pending_action.mark_completed()
    conversation.clear_pending_action()

    arguments = dict(pending_action.arguments)
    arguments.pop("event_query", None)
    arguments["event"] = chosen_event

    # If the user just picked a specific event from an ambiguous list,
    # don't ask for confirmation again — execute destructive ops directly.
    if pending_action.tool in ("delete_event", "batch_delete_events"):
        arguments["force"] = True

    return _execute_and_respond(
        conversation,
        pending_action.tool,
        arguments,
    )


def _execute_and_respond(conversation, tool, arguments):
    try:
        result = execute_tools(
            tool_name=tool,
            arguments=arguments,
            conversation=conversation,
        )

    except Exception as e:
        logger.error(
            "Tool execution failed in pending action",
            extra={"error": str(e)},
        )
        conversation.clear_pending_action()
        return (
            "Something went wrong while completing that request. "
            "Please try again."
        )

    status = result["status"]

    if needs_pending_action(status):
        return stash_pending_action_and_reply(conversation, result)

    try:
        reply = generate_response(result)
    except LLMServiceError:
        reply = FRIENDLY_LLM_ERROR

    if not reply:
        reply = "Done. Let me know if you need anything else."

    conversation.add_assistant_message(
        {"role": "assistant", "content": reply}
    )
    return reply