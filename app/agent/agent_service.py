from app.agent.memory.conversation_manager import conversation_manager
from app.workflows.pending_action_workflow import handle_pending_action
from app.workflows.normal_request_workflow import handle_normal_request
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_agent(user_message: str, session_id: str):
    if not user_message or not user_message.strip():
        return "I didn't receive any message - could you try sending that again?"

    conversation = conversation_manager.get_conversation(session_id)

    # Serialize turns for a single session - the request/response cycle
    # mutates shared conversation state (messages, pending_actions) and
    # is not safe to run concurrently for the same session_id.
    with conversation.lock:
        logger.info(
            "User message received",
            extra={
                "session_id": session_id,
                "has_pending_action": bool(conversation.get_pending_action()),
            },
        )

        if conversation.get_pending_action():
            return handle_pending_action(
                conversation=conversation,
                user_message=user_message,
            )

        return handle_normal_request(
            conversation=conversation,
            user_message=user_message,
        )