import json

from app.utility_llm import ask_utility_llm
from app.prompts import response_generation_prompt
from app.utils.logger import get_logger
from app.services.llm_response_utils import extract_content

logger = get_logger(__name__)


def generate_response(tool_result: dict):
    json_tool_result = json.dumps(
        tool_result,
        indent=2,
        default=str,
    )

    messages = [
        {
            "role": "system",
            "content": response_generation_prompt,
        },
        {
            "role": "user",
            "content": json.dumps(
                tool_result,
                indent=2,
                default=str,
            ),
        },
    ]

    logger.info(
        "Response generation input",
        extra={"tool_result": json_tool_result},
    )

    response = ask_utility_llm(messages)

    return extract_content(response)