from app.agent.groq_client import client

from app.exceptions import LLMServiceError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def ask_utility_llm(messages):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            reasoning_effort="low",
            temperature=0,
            messages=messages,
        )
    except Exception as e:
        logger.error(
            "Utility LLM call failed",
            extra={"error": str(e)},
        )
        raise LLMServiceError(
            f"Utility LLM call failed: {e}"
        ) from e

    return response