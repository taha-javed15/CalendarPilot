import threading
from datetime import datetime, timedelta

from app.agent.memory.conversation import Conversation


class ConversationManager:
    def __init__(self, ttl_minutes: int = 120):
        self.conversations = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self._manager_lock = threading.Lock()

    def get_conversation(self, session_id):
        with self._manager_lock:
            self._evict_expired()

            conversation = self.conversations.get(session_id)
            if conversation is None:
                conversation = self.create_new_conversation(session_id)

            conversation.last_active = datetime.now()
            return conversation

    def create_new_conversation(self, session_id):
        new_conversation = Conversation(session_id)
        self.conversations[session_id] = new_conversation
        return new_conversation

    def _evict_expired(self):
        now = datetime.now()

        expired_ids = [
            sid
            for sid, conv in self.conversations.items()
            if now - getattr(conv, "last_active", now) > self.ttl
        ]

        for sid in expired_ids:
            self.conversations.pop(sid, None)


conversation_manager = ConversationManager()