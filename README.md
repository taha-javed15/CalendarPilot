# CalendarPilot

**CalendarPilot is a conversational AI calendar assistant that lets users manage Google Calendar using natural language.**

Instead of forcing users to navigate calendar interfaces or remember specific commands, CalendarPilot interprets conversational requests, selects the appropriate calendar operation, validates the request, and executes it through structured workflows.

## What it can do

- Create calendar events
- Search and view events
- Update existing events
- Delete individual events
- Batch-delete multiple events
- Find available time
- Suggest alternative meeting times
- Find the best meeting time for a specific event
- Invite attendees
- Add or remove attendees
- Check attendee RSVP status
- View attendee comments
- Configure event reminders
- Read and update user settings
- Maintain multi-turn conversational context
- Resolve references such as "it", "that meeting", or "Gym"
- Detect scheduling conflicts
- Ask for confirmation before consequential actions
- Stream responses to the web interface
- Recover gracefully from API and LLM failures

---

# Architecture

```text
                              CalendarPilot
                                    │
                                    ▼
                              FastAPI Server
                         ┌──────────┴──────────┐
                         │                     │
                       /chat             /chat/stream
                         │                     │
                         └──────────┬──────────┘
                                    ▼
                              Agent Service
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                  Normal Request       Pending Action
                     Workflow              Workflow
                         │                     │
                         ▼                     ▼
                   Primary LLM          Confirmation /
                  Groq gpt-oss-120b      Disambiguation
                         │                     │
                         ▼                     ▼
                     Tool Calls          Secondary LLM
                         │                  Ollama
                         ▼
                    Dispatcher
                         │
                         ▼
                     Workflows
                         │
                         ▼
               Google Calendar API
```

The application separates **LLM reasoning, orchestration, business logic, external API access, and response generation** rather than allowing the model to directly control the calendar API.

---

# Agent Architecture

## 1. Agent Service

`app/agent/agent_service.py`

The agent service is the main entry point for conversational requests.

For each `session_id`, CalendarPilot retrieves or creates a conversation and determines whether the user is:

- making a normal request, or
- responding to an existing pending action.

Conversation turns for the same session are serialized with a lock so that shared conversation state cannot be mutated concurrently.

---

## 2. Primary LLM

The primary model is:

```text
openai/gpt-oss-120b
```

accessed through Groq.

It is responsible for the main reasoning loop:

- Understanding the user's intent
- Determining which calendar operation is required
- Selecting the appropriate tool
- Producing structured tool arguments
- Reviewing tool results
- Requesting additional tool calls when a task genuinely requires multiple steps
- Producing the final conversational response

The normal request workflow supports multiple tool-calling rounds, with a maximum of five rounds per user request as a safety limit.

---

## 3. Tool Calling

Calendar capabilities are exposed to the primary LLM through structured function definitions in:

```text
app/tools.py
```

The dispatcher maps those tool calls to individual workflows.

This keeps the LLM responsible for **deciding what should happen**, while application code remains responsible for **how the operation is actually performed**.

---

# Workflow Architecture

Calendar operations are separated into individual workflows under:

```text
app/workflows/
```

Examples include:

```text
create_event.py
update_event.py
delete_event.py
batch_delete_events.py
find_free_time.py
find_best_event_time.py
suggest_alternative_times.py
invite_attendees.py
update_attendees.py
get_attendees.py
get_attendee_status.py
view_attendee_comments.py
configure_reminders.py
get_event_details.py
settings.py
```

Workflows do not directly generate conversational responses.

Instead, they return structured results using statuses such as:

```text
success
confirmation_required
ambiguous
error
not_found
invalid_request
```

This creates a clean boundary between calendar business logic and conversational behavior.

---

# Dispatcher

`app/dispatcher.py`

The dispatcher is the central orchestration layer between the LLM and calendar workflows.

It is responsible for:

- Mapping tool names to workflows
- Validating tool requests
- Normalizing datetime arguments
- Resolving conversational event references
- Validating previously referenced events against the live calendar
- Localizing event timestamps
- Remembering recently referenced events
- Invalidating deleted events from conversational context
- Catching unexpected workflow failures
- Returning structured error results

This gives the agent a single controlled path for executing external calendar operations.

---

# Conversational Context & Reference Resolution

One of the core problems CalendarPilot solves is conversational event references.

For example:

```text
User: What are my events tomorrow?

CalendarPilot: You have Gym tomorrow at 7 PM.

User: Move it to 8 PM.
```

A naive implementation could perform another calendar-wide search for "Gym", potentially finding many unrelated events.

CalendarPilot instead stores recently referenced events in the conversation.

The reference resolution layer first checks those recent events before falling back to a normal calendar search.

### Supported references

Examples include:

```text
"it"
"that"
"this meeting"
"the event"
"Gym"
"Gym session"
```

### Reference behavior

- A single matching recent event is resolved directly.
- Multiple matching recent events produce a scoped ambiguity.
- No recent match falls back to the normal calendar search.
- Recently referenced events expire after 15 minutes.
- Cached events are revalidated against the live Google Calendar before being used.

This prevents stale conversational context from silently modifying the wrong event.

---

# Pending Actions

Calendar operations sometimes cannot safely execute immediately.

For example:

```text
User: Schedule Team Sync at 10 AM.
```

If another event already occupies that time, CalendarPilot does not immediately create the event.

Instead:

```text
Workflow
   ↓
Conflict detected
   ↓
confirmation_required
   ↓
PendingAction stored
   ↓
User asked for confirmation
```

Similarly, if multiple events match a request:

```text
ambiguous
   ↓
PendingAction stored
   ↓
User chooses the intended event
```

Pending actions have their own lifecycle:

```text
PENDING
COMPLETED
CANCELLED
EXPIRED
```

Pending actions expire after 10 minutes.

---

# Confirmation & Disambiguation

The secondary LLM is used for conversational tasks that do not require the full primary reasoning loop.

It runs locally through Ollama using:

```text
llama3.2
```

It handles tasks such as:

- Classifying confirmation responses
- Detecting cancellation
- Detecting when the user has started a new request
- Resolving which event the user selected from an ambiguous list
- Ranking available meeting slots

For example, a confirmation response can be classified as:

```text
CONFIRM
CANCEL
NEW_REQUEST
UNKNOWN
```

This keeps smaller conversational decisions separate from the main tool-selection model.

---

# Scheduling Intelligence

CalendarPilot includes dedicated scheduling workflows rather than relying entirely on the LLM to reason about calendar availability.

## Free time

The application queries Google Calendar's FreeBusy API and calculates available intervals inside a requested time window.

## Alternative times

Available intervals are converted into candidate meeting slots according to the requested duration.

## Best meeting time

For requests such as:

```text
Find the best time for a team planning meeting tomorrow.
```

CalendarPilot:

```text
Calendar availability
        ↓
Available time slots
        ↓
Secondary LLM ranking
        ↓
Best candidate slot
```

The ranking considers factors such as:

- Event type
- Working hours
- Normal scheduling patterns
- Appropriate times for personal vs. work activities

---

# Conflict Detection

Creating an event first checks for overlapping calendar events.

If a conflict exists, the workflow returns:

```text
confirmation_required
```

rather than silently creating an overlapping event.

The user can then explicitly choose whether to proceed.

After confirmation, the workflow uses the resolved action directly instead of repeating the same confirmation check.

---

# Timezone Handling

CalendarPilot stores the user's timezone in:

```text
app/data/settings.json
```

The default configuration currently uses:

```text
Asia/Kolkata
```

The timezone system:

- Generates ISO-8601 timestamps with the correct offset
- Converts Google Calendar event timestamps into the configured user timezone
- Handles timezone-aware scheduling
- Validates configured IANA timezone names
- Applies localization centrally through the dispatcher

This avoids duplicating timezone conversion logic across individual workflows.

---

# User Settings

CalendarPilot supports configurable settings including:

```json
{
    "working_hours": {
        "start": "09:00",
        "end": "17:00"
    },
    "event": {
        "default_duration": 60,
        "default_reminder": 15
    },
    "daily_briefing": {
        "enabled": false,
        "time": "08:00"
    },
    "time_zone": "Asia/Kolkata"
}
```

Settings can be read and updated through natural-language requests.

The settings workflow validates:

- Time formats
- Working-hour ranges
- Event duration
- Reminder values
- IANA timezone names

before writing changes to `settings.json`.

---

# API

CalendarPilot is built with FastAPI.

## Web interface

```text
GET /
```

Serves the CalendarPilot chat interface.

## Health check

```text
GET /health
```

Returns:

```json
{
    "status": "ok"
}
```

## Chat API

```text
POST /chat
```

Request:

```json
{
    "message": "Schedule lunch with Sarah tomorrow at 1pm",
    "session_id": "demo"
}
```

Response:

```json
{
    "response": "..."
}
```

## Streaming Chat API

```text
POST /chat/stream
```

The streaming endpoint uses **Server-Sent Events (SSE)** to progressively send the assistant's final response to the frontend.

The agent's orchestration still completes before the response is streamed, but the frontend receives the final response progressively rather than displaying it all at once.

---

# Frontend

CalendarPilot includes a custom web interface under:

```text
app/templates/index.html
app/static/script.js
app/static/style.css
```

The interface includes:

- Conversational chat UI
- Typing indicator
- Markdown rendering
- Streaming responses
- Responsive layout
- Keyboard shortcuts
- Mobile-friendly styling
- Sanitized rendered Markdown using DOMPurify

The browser generates a unique session ID for each conversation.

---

# Error Handling & Resilience

CalendarPilot treats external services as failure points rather than assuming they will always respond successfully.

## API retries

Transient failures are retried with exponential backoff.

Retryable failures include:

- Connection errors
- Timeouts
- OS-level connection failures
- HTTP 429
- HTTP 5xx

The retry system uses a maximum attempt count and increasing delays between attempts.

## LLM errors

Failures from the primary or secondary LLM are wrapped in application-level exceptions and converted into user-friendly responses.

## Workflow errors

Unexpected workflow exceptions are caught centrally by the dispatcher and converted into structured error results.

## Global API protection

FastAPI has a global exception handler that:

- Logs the actual server-side exception
- Returns a generic response to the client
- Prevents internal stack traces from being exposed

---

# Structured Logging

CalendarPilot uses structured JSON logging through:

```text
app/utils/logger.py
```

Logs can include:

- Incoming requests
- Session information
- Selected tools
- Tool arguments
- Workflow results
- LLM failures
- Retry attempts
- Exceptions
- Slow requests

Requests taking longer than the configured 5-second response target are specifically logged.

---

# Testing

The project includes a dedicated pytest suite covering:

- Agent routing
- Conversation management
- Pending actions
- Confirmation flows
- Ambiguity resolution
- Event creation
- Event deletion
- Event updates
- Attendee management
- Reminder configuration
- Settings validation
- Dispatcher behavior
- Conversational reference resolution
- Scheduling and slot ranking
- API endpoints
- Error handling
- Retry behavior
- LLM failures

External services are mocked during testing.

The test suite therefore does not require:

- Real Google Calendar credentials
- A real Google Calendar
- A running Ollama instance
- Live LLM calls

Run the tests with:

```bash
pip install -r requirements-dev.txt
pytest
```

For coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

---

# Project Structure

```text
calendarpilot/
│
├── app/
│   ├── agent/
│   │   ├── memory/
│   │   │   ├── conversation.py
│   │   │   ├── conversation_manager.py
│   │   │   ├── pending_action.py
│   │   │   └── workflow_result.py
│   │   │
│   │   ├── agent_service.py
│   │   └── groq_client.py
│   │
│   ├── data/
│   │   └── settings.json
│   │
│   ├── services/
│   │   ├── confirmation_service.py
│   │   ├── conflict_detection_service.py
│   │   ├── disambiguation_service.py
│   │   ├── event_service.py
│   │   ├── ranking_service.py
│   │   ├── reference_resolution_service.py
│   │   ├── response_generation_service.py
│   │   └── secondary_llm_service.py
│   │
│   ├── static/
│   │   ├── script.js
│   │   └── style.css
│   │
│   ├── templates/
│   │   └── index.html
│   │
│   ├── utils/
│   │   ├── logger.py
│   │   ├── retry.py
│   │   └── timezone.py
│   │
│   ├── workflows/
│   │   ├── batch_delete_events.py
│   │   ├── configure_reminders.py
│   │   ├── create_event.py
│   │   ├── delete_event.py
│   │   ├── find_best_event_time.py
│   │   ├── find_free_time.py
│   │   ├── get_attendee_status.py
│   │   ├── get_attendees.py
│   │   ├── get_event_details.py
│   │   ├── invite_attendees.py
│   │   ├── normal_request_workflow.py
│   │   ├── pending_action_workflow.py
│   │   ├── settings.py
│   │   ├── suggest_alternative_times.py
│   │   ├── update_attendees.py
│   │   └── update_event.py
│   │
│   ├── calendar_api.py
│   ├── dispatcher.py
│   ├── exceptions.py
│   ├── llm.py
│   ├── main.py
│   ├── prompts.py
│   ├── tools.py
│   └── utility_llm.py
│
├── tests/
│   ├── test_agent_service.py
│   ├── test_attendees.py
│   ├── test_configure_reminders.py
│   ├── test_conversation_references.py
│   ├── test_create_event.py
│   ├── test_delete_details_settings.py
│   ├── test_dispatcher.py
│   ├── test_dispatcher_reference_resolution.py
│   ├── test_find_best_event_time.py
│   ├── test_main.py
│   ├── test_normal_request_workflow.py
│   ├── test_pending_action_flow.py
│   ├── test_ranking_and_suggestions.py
│   ├── test_reference_resolution_service.py
│   ├── test_resilience.py
│   └── test_update_event.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

# Setup

## 1. Clone the repository

```bash
git clone https://github.com/taha-javed15/CalendarPilot.git
cd CalendarPilot
```

## 2. Install Python dependencies

Python 3.13 is used for the project.

```bash
pip install -r requirements.txt
```

For development:

```bash
pip install -r requirements-dev.txt
```

---

## 3. Configure Groq

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
```

The `.env` file is intentionally excluded from Git.

---

## 4. Configure Google Calendar

CalendarPilot uses Google OAuth 2.0.

1. Create an OAuth 2.0 Desktop application in Google Cloud.
2. Enable the Google Calendar API.
3. Download the OAuth client credentials.
4. Save the file in the project root as:

```text
credentials.json
```

On first authentication, CalendarPilot opens a browser for Google login and creates:

```text
token.json
```

Both files are excluded from Git through `.gitignore`.

**Never commit either file to the repository.**

---

## 5. Install Ollama

Install Ollama and pull the secondary model:

```bash
ollama pull llama3.2
```

Start Ollama:

```bash
ollama serve
```

CalendarPilot expects the local Ollama OpenAI-compatible API at:

```text
http://localhost:11434/v1
```

---

## 6. Run the application

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://localhost:8000
```

---

# Docker

The project includes:

```text
Dockerfile
docker-compose.yml
```

Build and start the application with:

```bash
docker compose up --build
```

The container exposes:

```text
8000
```

Google OAuth credentials are mounted from the host rather than copied into the image.

The Ollama service is **not included in the Docker Compose file**, so a containerized deployment requires appropriate networking/configuration to reach the Ollama instance running outside the container.

---

# Security

The following files contain credentials or local authentication state and are intentionally excluded from Git:

```text
.env
credentials.json
token.json
```

Do not commit them to the repository.

If credentials are accidentally exposed, revoke or rotate them through the relevant provider before continuing to use the project.

---

# Known Limitations

### In-memory conversation storage

Conversation state is stored in memory through `ConversationManager`.

Idle sessions are automatically evicted after the configured TTL, but the state is lost when the application restarts.

A production deployment could replace this with persistent session storage such as Redis.

### Local secondary LLM

The secondary reasoning layer depends on a locally running Ollama instance and the `llama3.2` model.

### Model availability

The primary model is configured in:

```text
app/llm.py
```

and currently uses:

```text
openai/gpt-oss-120b
```

through Groq.

Model availability can change, so deployments should verify that the configured model remains available through the provider.

---

# Tech Stack

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### AI / LLM

- Groq
- `openai/gpt-oss-120b`
- Ollama
- `llama3.2`
- Function/tool calling

### Integrations

- Google Calendar API
- Google OAuth 2.0

### Frontend

- HTML
- CSS
- JavaScript
- Server-Sent Events
- Marked
- DOMPurify

### Testing

- Pytest
- pytest-mock
- HTTPX

### Deployment

- Docker
- Docker Compose

---

# Engineering Focus

CalendarPilot was built around several core engineering principles:

- **LLM reasoning is separated from application logic.**
- **External APIs are accessed through controlled workflows rather than directly by the model.**
- **Consequential actions require explicit confirmation.**
- **Ambiguous requests are resolved before modifying the calendar.**
- **Conversational references are handled using recent context instead of unnecessary calendar-wide searches.**
- **External API failures are retried when they are plausibly transient.**
- **Unexpected failures are contained and converted into safe user-facing responses.**
- **Calendar data is normalized and localized centrally.**
- **Core behavior is covered by automated tests with external services mocked.**