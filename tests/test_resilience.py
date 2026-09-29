import pytest
from unittest.mock import MagicMock
from app.utils.retry import with_retry
from app.exceptions import LLMServiceError


def test_retry_succeeds_after_transient_failures():
    attempts = {"count": 0}

    @with_retry(max_attempts=3, base_delay=0)
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ConnectionError("temporary blip")
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 3


def test_retry_gives_up_after_max_attempts():
    attempts = {"count": 0}

    @with_retry(max_attempts=2, base_delay=0)
    def always_fails():
        attempts["count"] += 1
        raise ConnectionError("still broken")

    with pytest.raises(ConnectionError):
        always_fails()

    assert attempts["count"] == 2


def test_retry_does_not_retry_non_transient_errors():
    attempts = {"count": 0}

    @with_retry(max_attempts=3, base_delay=0)
    def bad_value():
        attempts["count"] += 1
        raise ValueError("not a transient error")

    with pytest.raises(ValueError):
        bad_value()

    assert attempts["count"] == 1


def test_ask_llm_wraps_failures_in_llm_service_error(monkeypatch):
    from app import llm as llm_module

    def boom(*args, **kwargs):
        raise RuntimeError("groq is down")

    monkeypatch.setattr(llm_module.client.chat.completions, "create", boom)

    with pytest.raises(LLMServiceError):
        llm_module.ask_llm([{"role": "user", "content": "hi"}])


def test_ask_small_llm_wraps_failures_in_llm_service_error(monkeypatch):
    from app.services import secondary_llm_service

    def boom(*args, **kwargs):
        raise RuntimeError("ollama is down")

    monkeypatch.setattr(secondary_llm_service.client.chat.completions, "create", boom)

    with pytest.raises(LLMServiceError):
        secondary_llm_service.ask_small_llm([{"role": "user", "content": "hi"}])
