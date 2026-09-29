import json
import threading
from datetime import datetime, timedelta

from app.prompts import get_tool_llm_prompt
from app.agent.memory.pending_action import PendingAction


class Conversation:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.pending_actions: PendingAction | None = None

        # Computed fresh per-conversation (not at module import time) so
        # the "current date/time" the model sees is always accurate, even
        # on a long-running server process.
        self.messages = [
            {
                "role": "system",
                "content": get_tool_llm_prompt(),
            }
        ]

        # Events recently shown to the user (via list_events,
        # get_event_details, or as the result of a create/update/delete),
        # used to resolve follow-up references like
        # "move it to 8pm" without re-searching the whole calendar.
        # See reference_resolution_service.
        self.last_referenced_events: list = []
        self.last_referenced_at: datetime | None = None

        # Tracked by ConversationManager to allow evicting idle sessions.
        self.last_active: datetime = datetime.now()

        self.lock = threading.Lock()

    def add_user_message(self, message: str):
        self.messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

    def add_assistant_message(self, message: dict):
        self.messages.append(message)

    def add_tool_message(self, tool_call, result):
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str),
            }
        )

    def get_history(self):
        return self.messages

    def set_pending_action(self, pending_action: PendingAction):
        self.pending_actions = pending_action

    def get_pending_action(self):
        return self.pending_actions

    def clear_pending_action(self):
        self.pending_actions = None

    def set_last_referenced_events(self, events: list):
        """Records events just shown to or acted on for the user."""
        self.last_referenced_events = events or []
        self.last_referenced_at = datetime.now()

    def get_last_referenced_events(self, max_age_minutes: int = 15) -> list:
        """
        Returns the recently-referenced events, or [] if none were set or
        they're older than `max_age_minutes`. The recency window exists so
        a follow-up hours later doesn't silently resolve against a stale
        reference from an earlier, unrelated part of the conversation.
        """
        if (
            not self.last_referenced_events
            or self.last_referenced_at is None
        ):
            return []

        if (
            datetime.now() - self.last_referenced_at
            > timedelta(minutes=max_age_minutes)
        ):
            return []

        return self.last_referenced_events