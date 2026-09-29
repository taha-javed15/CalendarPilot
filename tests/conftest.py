import sys
import copy
import pytest
from unittest.mock import MagicMock

# GROQ_API_KEY must exist before app.llm is imported (Groq client reads it at import time)
import os
os.environ.setdefault("GROQ_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def reset_calendar_service_cache():
    """Ensure the cached calendar service singleton doesn't leak between tests."""
    from app import calendar_api
    calendar_api.reset_calendar_service()
    yield
    calendar_api.reset_calendar_service()


@pytest.fixture
def mock_calendar_service(monkeypatch):
    """
    Patches get_calendar_service to return a MagicMock, and returns that
    mock so tests can configure .events(), .freebusy(), etc.

    Several workflow modules do `from app.calendar_api import
    get_calendar_service`, which binds their own local reference at import
    time - patching app.calendar_api.get_calendar_service alone does NOT
    affect those already-bound references. Every module holding one of
    those local references needs to be patched individually.
    """
    mock_service = MagicMock()
    fake_get_service = lambda: mock_service

    monkeypatch.setattr("app.calendar_api.get_calendar_service", fake_get_service)
    monkeypatch.setattr("app.workflows.create_event.get_calendar_service", fake_get_service)
    monkeypatch.setattr("app.workflows.update_event.get_calendar_service", fake_get_service)
    monkeypatch.setattr("app.workflows.delete_event.get_calendar_service", fake_get_service)
    monkeypatch.setattr("app.workflows.find_free_time.get_calendar_service", fake_get_service)

    return mock_service


@pytest.fixture
def sample_event():
    return {
        "id": "evt_123",
        "summary": "Team Sync",
        "start": {"dateTime": "2026-08-10T10:00:00+05:30"},
        "end": {"dateTime": "2026-08-10T10:30:00+05:30"},
        "attendees": [
            {"email": "alice@example.com", "displayName": "Alice", "responseStatus": "accepted"},
            {"email": "bob@example.com", "displayName": "Bob", "responseStatus": "needsAction", "comment": "Might be late"}
        ]
    }


@pytest.fixture
def sample_events_list(sample_event):
    second = copy.deepcopy(sample_event)
    second["id"] = "evt_456"
    second["summary"] = "Team Sync (recurring)"
    second["start"] = {"dateTime": "2026-08-11T10:00:00+05:30"}
    second["end"] = {"dateTime": "2026-08-11T10:30:00+05:30"}
    return [sample_event, second]


@pytest.fixture
def mock_small_llm(monkeypatch):
    """
    Patches ask_small_llm everywhere it's imported (each service does
    `from app.services.secondary_llm_service import ask_small_llm`, which
    binds its own local reference, so we patch each module's copy).
    """
    responses = []

    def _ask(messages):
        if not responses:
            raise AssertionError("mock_small_llm called with no queued response")
        return responses.pop(0)

    mock_fn = MagicMock(side_effect=_ask)

    targets = [
        "app.services.confirmation_service.ask_llm",
        "app.services.disambiguation_service.ask_llm",
        "app.services.ranking_service.ask_small_llm",
        "app.services.response_generation_service.ask_llm",
    ]
    for target in targets:
        monkeypatch.setattr(target, mock_fn)

    def queue(response_text):
        responses.append(response_text)

    mock_fn.queue = queue
    return mock_fn


@pytest.fixture
def mock_primary_llm(monkeypatch):
    """Patches app.llm.ask_llm used by normal_request_workflow."""
    mock_fn = MagicMock()
    monkeypatch.setattr("app.workflows.normal_request_workflow.ask_llm", mock_fn)
    return mock_fn


def make_llm_response(content=None, tool_calls=None):
    """Builds an object shaped like a Groq/OpenAI chat completion response."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def make_tool_call(call_id, name, arguments_dict):
    import json
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function.name = name
    tool_call.function.arguments = json.dumps(arguments_dict)
    return tool_call
