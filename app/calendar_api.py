from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.agent.memory.workflow_result import WorkflowStatus
from app.utils.retry import with_retry
from app.utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_PATH = BASE_DIR / "token.json"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"

_service = None  # cached calendar service, built lazily on first use


def get_calendar_service():
    """
    Returns a cached Google Calendar service client, refreshing or
    generating OAuth credentials as needed.
    """
    global _service

    if _service is not None:
        return _service

    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_PATH),
            SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("OAuth token refreshed")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH),
                SCOPES
            )
            creds = flow.run_local_server(
                port=8080,
                open_browser=True
            )
            logger.info("OAuth login completed")

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    _service = build("calendar", "v3", credentials=creds)
    return _service


def reset_calendar_service():
    """Clears the cached service. Mainly useful for tests."""
    global _service
    _service = None


@with_retry()
def find_events(start_time, end_time):
    service = get_calendar_service()

    try:
        event_result = service.events().list(
            calendarId="primary",
            timeMin=start_time,
            timeMax=end_time,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
    except Exception as e:
        logger.error(
            "find_events failed",
            extra={"error": str(e)}
        )
        return {
            "status": WorkflowStatus.ERROR,
            "message": f"Failed to list calendar events: {e}"
        }

    events = event_result.get("items", [])

    if not events:
        return {
            "status": WorkflowStatus.NOT_FOUND,
            "message": "No events were found in the given time duration."
        }

    return {
        "status": WorkflowStatus.SUCCESS,
        "events": events
    }


@with_retry()
def find_events_by_query(event_query, start_time=None, end_time=None, max_results=10):
    """
    `max_results` defaults to 10 to match the historical behavior of
    single-event lookups (update/delete/get_details etc., which only
    ever need to see "is there more than one match"). Batch operations
    that mean to act on *every* matching event (see
    batch_delete_events_workflow) pass a much higher value - capping at
    10 there would silently truncate a genuine "delete all" request
    without telling the user anything was left behind.
    """
    service = get_calendar_service()

    params = {
        "calendarId": "primary",
        "maxResults": max_results,
        "singleEvents": True
    }

    if event_query:
        params["q"] = event_query

    if start_time:
        params["timeMin"] = start_time

    if end_time:
        params["timeMax"] = end_time

    try:
        event_result = service.events().list(**params).execute()
    except Exception as e:
        logger.error(
            "find_events_by_query failed",
            extra={"error": str(e)}
        )
        raise

    return event_result.get("items", [])


@with_retry()
def get_event_by_id(event_id):
    """
    Fetch a single event by its ID, or return None if it no longer exists.

    Transient failures (network errors, 429/5xx) are retried by
    @with_retry. A 404/410 (event genuinely not found or deleted) is a
    normal outcome and returns None directly rather than being retried
    or raised.
    """
    service = get_calendar_service()

    try:
        return service.events().get(
            calendarId="primary",
            eventId=event_id
        ).execute()

    except Exception as e:
        status = getattr(getattr(e, "resp", None), "status", None)

        if status in (404, 410):
            return None

        raise