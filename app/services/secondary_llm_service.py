from openai import OpenAI

from app.exceptions import LLMServiceError
from app.utils.logger import get_logger

logger = get_logger(__name__)

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


def ask_small_llm(messages):
    try:
        response = client.chat.completions.create(
            model="llama3.2",
            temperature=0,
            messages=messages,
        )
    except Exception as e:
        logger.error(
            "Secondary LLM call failed",
            extra={"error": str(e)},
        )
        raise LLMServiceError(
            f"Secondary LLM call failed: {e}"
        ) from e

    return response.choices[0].message.content