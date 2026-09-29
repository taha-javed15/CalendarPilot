# CalendarPilot

An AI agent that manages your Google Calendar through natural language —
create, update, delete, and search events; find free time and the best
meeting slot; manage attendees and reminders; all via a `/chat` endpoint.

## Architecture

```
User -> FastAPI (/chat) -> Agent Service -> Normal Request Workflow -> Primary LLM (Groq, decides which tool to call)
                                          -> Dispatcher -> Workflow -> Google Calendar API
                                          -> Pending Action Workflow (confirmations / disambiguation)
                                             -> Secondary LLM (Ollama, classifies intent / generates replies)
```

- **Primary LLM (Groq)** — decides intent and which calendar tool to call.
- **Secondary LLM (local Ollama model)** — small, cheap model used for
  classifying yes/no/cancel responses, resolving "which event did you
  mean?", ranking candidate time slots, and turning structured workflow
  results into natural language. Keeps the expensive model out of the
  conversational glue.
- **Workflows** (`app/workflows/`) — one file per calendar capability.
  Each returns a structured result with a `status`
  (`success` / `confirmation_required` / `ambiguous` / `error` / `not_found`
  / `invalid_request`) rather than talking to the user directly.
- **Pending actions** — when a workflow can't proceed safely (a conflicting
  event, an ambiguous event reference), it returns `confirmation_required`
  or `ambiguous`. The agent stores that as a `PendingAction` on the
  conversation and asks the user to resolve it before doing anything else.
- **Dispatcher** — the single place that calls workflows, catches any
  unexpected exception, and turns it into a generic `error` status so a
  Calendar API hiccup never crashes the agent or leaks a stack trace. It's
  also where conversational reference resolution happens (see below).

## Conversational reference resolution

Follow-up requests like "move it to 8pm" or "delete that" don't trigger a
fresh full-calendar search. The dispatcher tracks whichever events were
most recently shown to or acted on for the user
(`Conversation.last_referenced_events`, `app/dispatcher.py`,
`app/services/reference_resolution_service.py`) and tries to resolve the
next `event_query` against those first:

- **Pronoun references** ("it", "that", "the meeting") resolve directly if
  exactly one event was recently shown, or ask for clarification scoped to
  just those recent candidates if there were several.
- **Title references** ("Gym") match against recently-shown event titles
  before ever touching `find_single_event`'s full-calendar search — so if
  you just asked about tomorrow's Gym session and say "move it", the agent
  won't ask you to disambiguate between every Gym event you've ever
  created.
- References expire after 15 minutes of inactivity, so a "delete it" long
  after the conversation moved on doesn't silently act on a stale event.
- If nothing recent matches, it falls back to the original full-calendar
  search unchanged — this only *removes* unnecessary ambiguity, it never
  suppresses a genuine one.

## Setup

### 1. Google Calendar credentials

1. Create an OAuth 2.0 **Desktop app** client ID in the
   [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   with the Calendar API enabled.
2. Download the client secret JSON and save it as `credentials.json` in the
   project root.
3. On first run, the app opens a browser for you to log in and generates
   `token.json` automatically (it refreshes itself after that).

**Never commit `credentials.json` or `token.json`.** Both are already in
`.gitignore`. If either has ever been committed or shared, rotate the
client secret in Google Cloud Console and delete `token.json` to force a
fresh login.

### 2. Environment variables

```bash
cp .env.example .env
# then edit .env and set GROQ_API_KEY
```

### 3. Local LLM (Ollama)

The secondary LLM calls run against a local Ollama instance:

```bash
ollama pull llama3.2
ollama serve
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
# for running tests:
pip install -r requirements-dev.txt
```

### 5. Run

```bash
uvicorn app.main:app --reload
```

Or with Docker:

```bash
docker compose up --build
```

(Docker Compose mounts `credentials.json` and `token.json` from the host,
so run the OAuth login locally at least once before containerizing, or be
ready to complete the login flow inside the container's exposed port 8080.)

### 6. Talk to it

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Schedule lunch with Sarah tomorrow at 1pm", "session_id": "demo"}'
```

`session_id` is any string you choose to keep a conversation's history and
pending actions isolated per user/session.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

All Google Calendar and LLM calls are mocked in tests — no network access,
no real credentials, no Ollama instance required to run the suite.

```bash
pytest --cov=app --cov-report=term-missing
```

## Logging

All logs are structured JSON on stdout (`app/utils/logger.py`), including:
- every user message received
- which tool was selected for each request and its outcome
- retried/failed Google Calendar API calls
- unhandled exceptions (server-side only — the client always gets a
  generic, non-leaking error message)
- requests that exceed the 5-second response time target

## Error resilience

- Google Calendar API calls that fail with a transient error (connection
  drop, timeout, 429, or 5xx) are retried automatically with exponential
  backoff (`app/utils/retry.py`).
- Any exception raised inside a workflow is caught centrally in the
  dispatcher and converted into a normal `error` status instead of
  crashing the request.
- OAuth tokens are refreshed automatically when expired.

## Known limitations

- The secondary LLM (`llama3.2` via Ollama) sometimes doesn't follow
  "JSON only" instructions perfectly. `rank_slots` strips markdown code
  fences defensively; if you see classification failures in the
  confirmation or disambiguation flow, check the logs for the raw model
  output first.
- Conversations are stored in memory only (`ConversationManager`) and are
  lost on restart. There's no session expiry/cleanup, so long-running
  deployments will accumulate conversation state in memory — fine for a
  personal/small-team deployment, worth revisiting (e.g. Redis-backed
  sessions with TTL) before scaling further.
- The primary model string in `app/llm.py`
  (`qwen/qwen3.6-27b` on Groq) should be double-checked against Groq's
  currently available models if you see completion errors — model
  availability changes over time and wasn't verified against a live API
  call as part of this build.