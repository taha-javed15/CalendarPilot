class CalendarServiceError(Exception):
    """Raised when the Google Calendar API fails after retries are exhausted."""


class LLMServiceError(Exception):
    """Raised when a call to the primary or secondary LLM fails."""
