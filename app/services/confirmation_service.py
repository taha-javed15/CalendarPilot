from enum import Enum

from app.utility_llm import ask_utility_llm
from app.services.llm_response_utils import extract_content
from app.utils.logger import get_logger


class UserIntent(str, Enum):
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    NEW_REQUEST = "NEW_REQUEST"
    UNKNOWN = "UNKNOWN"


SYSTEM_PROMPT = """
You classify a user's reply to a pending calendar confirmation.

Return exactly one of these labels:

CONFIRM
The user wants to proceed.

CANCEL
The user wants to stop the action.

NEW_REQUEST
The user is no longer answering the confirmation and has started a new or modified calendar request.

UNKNOWN
The reply is ambiguous or does not clearly fit the above categories.

Rules:
- Return only one label.
- No explanations.
- No punctuation.
- Valid outputs are:
CONFIRM
CANCEL
NEW_REQUEST
UNKNOWN
"""

logger = get_logger(__name__)


def _clean(response: str) -> str:
    return response.strip().strip("`").strip()


def confirm_user_intent(message: str) -> UserIntent:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    response_obj = ask_utility_llm(messages)

    logger.info(
        "Confirmation LLM response",
        extra={
            "response": (
                response_obj.model_dump()
                if hasattr(response_obj, "model_dump")
                else response_obj
            )
        },
    )

    response = _clean(extract_content(response_obj))

    try:
        return UserIntent(response)
    except ValueError:
        return UserIntent.UNKNOWN