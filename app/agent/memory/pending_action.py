from datetime import datetime, timedelta
from uuid import uuid4
from enum import Enum
from typing import Any


class PendingActionStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PendingActionType(str, Enum):
    CONFIRMATION = "confirmation"
    AMBIGUITY = "ambiguity"


class PendingAction:
    def __init__(
        self,
        action_type: PendingActionType,
        tool: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ):
        self.action_id = uuid4()

        self.action_type = action_type
        self.tool = tool
        self.arguments = arguments
        self.context = context or {}

        self.status = PendingActionStatus.PENDING

        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(minutes=10)

    def is_expired(self):
        return datetime.now() >= self.expires_at

    def mark_completed(self):
        self.status = PendingActionStatus.COMPLETED

    def mark_expired(self):
        self.status = PendingActionStatus.EXPIRED

    def mark_cancelled(self):
        self.status = PendingActionStatus.CANCELLED