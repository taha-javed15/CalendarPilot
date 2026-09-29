import json

from app.llm import ask_llm
from app.dispatcher import execute_tools
from app.workflows.pending_action_helper import needs_pending_action, stash_pending_action_and_reply
from app.exceptions import LLMServiceError
from app.utils.logger import get_logger

logger = get_logger(__name__)

FRIENDLY_LLM_ERROR = (
    "I'm having trouble reaching the assistant service right now. "
    "Please try again in a moment."
)

# Some requests genuinely need more than one tool call in sequence
# (e.g. "find a free slot, then book it there") - the model is allowed
# to call tools() again after seeing a tool's result rather than being
# forced to produce a final text answer after exactly one round. This
# caps how many such rounds we'll follow in a single user turn, purely
# as a safety net against a model that keeps requesting tools
# indefinitely; ordinary single-tool requests only ever use one round.
MAX_TOOL_ROUNDS = 5

INCOMPLETE_REQUEST_MESSAGE = (
    "I wasn't able to finish that request in the time I had - could you "
    "tell me what's still left to do, or try again?"
)


def handle_normal_request(conversation, user_message):
    conversation.add_user_message(user_message)

    for round_number in range(1, MAX_TOOL_ROUNDS + 1):
        try:
            response = ask_llm(conversation.get_history())
        except LLMServiceError:
            return FRIENDLY_LLM_ERROR

        assistant_message = response.choices[0].message

        logger.info(
            "LLM response",
            extra={
                "round": round_number,
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                    for tc in (assistant_message.tool_calls or [])
                ]
            }
        )

        if not assistant_message.tool_calls:
            # No further tool calls requested - this is the model's
            # actual final answer, regardless of which round produced it.
            content = assistant_message.content
            if not content:
                content = "I'm not sure how to respond to that. Could you rephrase?"
            conversation.add_assistant_message(
                {"role": "assistant", "content": content}
            )
            return content

        conversation.add_assistant_message(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": assistant_message.tool_calls
            }
        )

        tool_calls = list(assistant_message.tool_calls)

        for i, tool_call in enumerate(tool_calls):
            tool_name = tool_call.function.name

            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                logger.error("Malformed tool arguments from LLM", extra={"tool": tool_name})
                conversation.add_tool_message(
                    tool_call,
                    {"status": "error", "message": "Malformed tool arguments."}
                )
                continue

            result = execute_tools(tool_name=tool_name, arguments=arguments, conversation=conversation)
            status = result["status"]

            # Every tool_call in this round needs a matching tool
            # response, or the next ask_llm call will be rejected for
            # having an assistant message with unanswered tool_calls.
            conversation.add_tool_message(tool_call, result)

            if needs_pending_action(status):
                # Anything the model queued after this call in the same
                # round never ran - the pending action has to be
                # resolved first. Close those out too instead of leaving
                # them dangling; the model can re-request them once the
                # conversation continues.
                for skipped_call in tool_calls[i + 1:]:
                    conversation.add_tool_message(
                        skipped_call,
                        {
                            "status": "skipped",
                            "message": (
                                "Not executed - a prior action in this "
                                "turn requires user confirmation first."
                            ),
                        },
                    )
                return stash_pending_action_and_reply(conversation, result)

        # All tool calls in this round completed. Loop back and ask the
        # model again - it may now have everything it needs to answer in
        # text, or it may need to call another tool based on what it
        # just learned (e.g. found a free slot, now book it).

    # Exhausted MAX_TOOL_ROUNDS without the model producing a final text
    # answer. This should be rare - it means the model kept requesting
    # tools well beyond what a normal calendar request needs - so it's
    # worth a distinct log signal rather than silently returning a
    # generic "I don't understand" that would misrepresent what actually
    # happened.
    logger.warning(
        "Exceeded max tool-calling rounds without a final answer",
        extra={"max_rounds": MAX_TOOL_ROUNDS}
    )
    conversation.add_assistant_message(
        {"role": "assistant", "content": INCOMPLETE_REQUEST_MESSAGE}
    )
    return INCOMPLETE_REQUEST_MESSAGE