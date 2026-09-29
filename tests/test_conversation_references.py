from datetime import timedelta
from app.agent.memory.conversation import Conversation


def test_no_referenced_events_by_default():
    conversation = Conversation(session_id="s1")
    assert conversation.get_last_referenced_events() == []


def test_set_and_get_referenced_events():
    conversation = Conversation(session_id="s2")
    events = [{"id": "1", "summary": "Gym"}]

    conversation.set_last_referenced_events(events)

    assert conversation.get_last_referenced_events() == events


def test_stale_referenced_events_are_dropped():
    conversation = Conversation(session_id="s3")
    conversation.set_last_referenced_events([{"id": "1", "summary": "Gym"}])

    # simulate the reference having been set 20 minutes ago
    conversation.last_referenced_at -= timedelta(minutes=20)

    assert conversation.get_last_referenced_events(max_age_minutes=15) == []


def test_recent_referenced_events_within_window_are_kept():
    conversation = Conversation(session_id="s4")
    conversation.set_last_referenced_events([{"id": "1", "summary": "Gym"}])

    conversation.last_referenced_at -= timedelta(minutes=5)

    assert len(conversation.get_last_referenced_events(max_age_minutes=15)) == 1