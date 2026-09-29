import json

from app.prompts import ranking_prompt
from app.services.secondary_llm_service import ask_small_llm


def _strip_fences(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]

    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]

    return text.strip()


def rank_slots(event_summary, suggestions, working_hours, context=None):
    user_prompt = f"""
Event:
{event_summary}

Working hours:
{working_hours}

Available slots:
{json.dumps(suggestions, indent=2)}

Choose the single best slot.

Return ONLY valid JSON.

Do not explain your reasoning.
"""

    messages = [
        {"role": "system", "content": ranking_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = ask_small_llm(messages)
    cleaned = _strip_fences(response)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None