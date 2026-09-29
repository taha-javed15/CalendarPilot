from enum import Enum


class WorkflowStatus(str, Enum):
    SUCCESS = "success"
    CONFIRMATION_REQUIRED = "confirmation_required"
    AMBIGUOUS = "ambiguous"
    ERROR = "error"
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
