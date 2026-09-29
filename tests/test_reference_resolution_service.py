from app.services.reference_resolution_service import resolve_reference


def make_event(id_, summary):
    return {"id": id_, "summary": summary, "start": {}, "end": {}}


def test_no_recent_events_is_no_match():
    outcome, payload = resolve_reference("Gym", [])
    assert outcome == "no_match"
    assert payload is None


def test_empty_query_is_no_match():
    outcome, payload = resolve_reference("", [make_event("1", "Gym")])
    assert outcome == "no_match"


def test_pronoun_with_single_recent_event_resolves():
    events = [make_event("1", "Gym")]
    outcome, payload = resolve_reference("it", events)
    assert outcome == "resolved"
    assert payload["id"] == "1"


def test_pronoun_with_multiple_recent_events_is_ambiguous():
    events = [make_event("1", "Gym"), make_event("2", "Dentist")]
    outcome, payload = resolve_reference("that", events)
    assert outcome == "ambiguous"
    assert len(payload) == 2


def test_short_pronoun_phrase_resolves():
    events = [make_event("1", "Gym")]
    outcome, payload = resolve_reference("move it", events)
    assert outcome == "resolved"
    assert payload["id"] == "1"


def test_exact_title_match_resolves():
    events = [make_event("1", "Gym")]
    outcome, payload = resolve_reference("Gym", events)
    assert outcome == "resolved"
    assert payload["id"] == "1"


def test_title_substring_match_resolves():
    events = [make_event("1", "Gym Session")]
    outcome, payload = resolve_reference("gym", events)
    assert outcome == "resolved"
    assert payload["id"] == "1"


def test_ambiguous_title_among_recent_events():
    events = [make_event("1", "Gym"), make_event("2", "Gym (recurring)")]
    outcome, payload = resolve_reference("gym", events)
    assert outcome == "ambiguous"
    assert len(payload) == 2


def test_no_title_match_falls_back():
    events = [make_event("1", "Dentist")]
    outcome, payload = resolve_reference("Gym", events)
    assert outcome == "no_match"


def test_duplicate_ids_are_deduped():
    same_event = make_event("1", "Gym")
    outcome, payload = resolve_reference("it", [same_event, dict(same_event)])
    assert outcome == "resolved"
    assert payload["id"] == "1"