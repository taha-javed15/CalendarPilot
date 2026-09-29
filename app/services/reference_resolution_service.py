"""
Resolves event references ("it", "that", "Gym") against events the
conversation has recently shown the user, so a follow-up like
"move it to 8pm" doesn't trigger a fresh full-calendar search that
turns up every event with a similar title.

This is intentionally a cheap, deterministic heuristic rather than
another LLM round-trip - it only needs to be right often enough to
avoid *unnecessary* ambiguity. When it can't confidently resolve or
narrow the reference, it says so and the caller falls back to the
existing full-calendar search, which is still the ultimate source of
truth.
"""

PRONOUN_REFERENCES = {
    "it",
    "that",
    "this",
    "this one",
    "that one",
    "same one",
    "same event",
    "this event",
    "that event",
    "the event",
    "the meeting",
    "this meeting",
    "that meeting",
    "it instead",
    "that instead",
}


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _is_pronoun_reference(event_query: str) -> bool:
    normalized = _normalize(event_query)

    if normalized in PRONOUN_REFERENCES:
        return True

    # Catches short trailing phrasing like "move it" being passed whole,
    # or "delete that meeting" - a pronoun word with nothing else
    # specific.
    words = normalized.split()
    return len(words) <= 3 and any(
        w in {"it", "that", "this"} for w in words
    )


def _dedupe(events: list) -> list:
    seen_ids = set()
    deduped = []

    for event in events:
        event_id = event.get("id")

        if event_id in seen_ids:
            continue

        seen_ids.add(event_id)
        deduped.append(event)

    return deduped


def resolve_reference(event_query: str, last_referenced_events: list):
    """
    Returns a tuple of (outcome, payload):

        ("resolved", event)    - exactly one event matched, use it directly
        ("ambiguous", events)  - more than one recently-shown event matched
        ("no_match", None)     - no confident match; fall back to a full search
    """

    if not event_query or not last_referenced_events:
        return ("no_match", None)

    if _is_pronoun_reference(event_query):
        deduped = _dedupe(last_referenced_events)

        if len(deduped) == 1:
            return ("resolved", deduped[0])

        return ("ambiguous", deduped)

    normalized_query = _normalize(event_query)
    matches = []

    for event in last_referenced_events:
        summary = _normalize(event.get("summary"))

        if not summary:
            continue

        if normalized_query in summary or summary in normalized_query:
            matches.append(event)

    matches = _dedupe(matches)

    if len(matches) == 1:
        return ("resolved", matches[0])

    if len(matches) > 1:
        return ("ambiguous", matches)

    return ("no_match", None)