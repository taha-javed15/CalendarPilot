from app.utility_llm import ask_utility_llm
from app.services.llm_response_utils import extract_content


SYSTEM_PROMPT = """
You determine which calendar event the user selected from a previously shown numbered list.

The list below is numbered starting at 1, matching exactly how it was shown to the user.

Return exactly one of:

- A single integer representing the selected event number (as shown in the numbered list, starting at 1).
- NEW_REQUEST if the user has abandoned the selection and started a different calendar request.
- NONE if the selection is ambiguous or cannot be determined.

The user may refer to an event by:
- its number
- its title
- its date or time
- an ordinal (first, second, last)
- another unique identifying detail

Never guess.

Return only the integer, NEW_REQUEST, or NONE.
"""


def _format_events(events):
    # NOTE: numbered starting at 1 - this must match the numbering the
    # user actually sees. The user-facing list (built separately by
    # response_generation_service from this same `events` list) is also
    # 1-indexed. These two used to disagree (this list used to start at
    # 0), so a user replying "2" to mean the second item they saw could
    # get silently mapped to the *third* item here.
    lines = []

    for i, event in enumerate(events, start=1):
        summary = event.get("summary", "Untitled event")
        start = (
            (event.get("start") or {}).get("dateTime")
            or (event.get("start") or {}).get("date")
        )
        lines.append(f"{i}. {summary} - {start}")

    return "\n".join(lines)


def _clean(response: str) -> str:
    return response.strip().strip("`").strip()


def resolve_ambiguity(user_message: str, events: list):
    """
    Returns:
        int            -> index into `events` the user selected
        "NEW_REQUEST"  -> the user abandoned the disambiguation
        None           -> still unclear
    """

    if not events:
        return None

    user_prompt = f"""
Events:
{_format_events(events)}

User reply:
{user_message}
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    response_obj = ask_utility_llm(messages)
    response = _clean(extract_content(response_obj))

    if response == "NEW_REQUEST":
        return "NEW_REQUEST"

    if response == "NONE":
        return None

    try:
        # The model returns a 1-based number (matching what the user was
        # shown); convert to a 0-based index into `events`.
        number = int(response)
    except ValueError:
        return None

    index = number - 1

    if 0 <= index < len(events):
        return index

    return None