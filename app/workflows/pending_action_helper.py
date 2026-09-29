from app.agent.memory.pending_action import PendingAction, PendingActionType
from app.agent.memory.workflow_result import WorkflowStatus
from app.services.response_generation_service import generate_response
from app.exceptions import LLMServiceError

FRIENDLY_LLM_ERROR = (
    "I'm having trouble reaching the assistant service right now. "
    "Please try again in a moment."
)


def needs_pending_action(status) -> bool:
    return status in (WorkflowStatus.CONFIRMATION_REQUIRED, WorkflowStatus.AMBIGUOUS)


def stash_pending_action_and_reply(conversation, result):
    status = result["status"]

    action_type = (
        PendingActionType.CONFIRMATION
        if status == WorkflowStatus.CONFIRMATION_REQUIRED
        else PendingActionType.AMBIGUITY
    )

    conversation.set_pending_action(
        PendingAction(
            action_type=action_type,
            tool=result["tool"],
            arguments=result["arguments"],
            context=result.get("context")
        )
    )

    # generate_response makes its own LLM call and can fail independently
    # of the tool call that produced `result` - previously this wasn't
    # guarded, so a transient failure here would surface as a raw 500
    # instead of the same friendly message used elsewhere.
    try:
        reply = generate_response(result)
    except LLMServiceError:
        reply = FRIENDLY_LLM_ERROR

    if not reply:
        reply = "I've noted that. What would you like to do next?"
        
    conversation.add_assistant_message({"role": "assistant", "content": reply})
    return reply