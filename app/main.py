import asyncio
import json
import time
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.agent.agent_service import run_agent
from app.utils.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).parent

app = FastAPI(title="CalendarPilot")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

SLOW_REQUEST_THRESHOLD_SECONDS = 5.0

# Small pacing delay between streamed chunks so text visibly "types out"
# on the frontend instead of appearing all at once.
STREAM_CHUNK_DELAY_SECONDS = 0.02


class ChatRequest(BaseModel):
    message: str
    session_id: str


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start

    log_extra = {
        "path": request.url.path,
        "method": request.method,
        "status_code": response.status_code,
        "duration_seconds": round(duration, 3)
    }

    if duration > SLOW_REQUEST_THRESHOLD_SECONDS:
        logger.warning("Request exceeded response time target", extra=log_extra)
    else:
        logger.info("Request completed", extra=log_extra)

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        extra={"path": request.url.path, "error": str(exc)},
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"response": "Something went wrong on our end. Please try again."}
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest):
    response = run_agent(request.message, request.session_id)
    return {"response": response}


def _sse(data: dict, event: str | None = None) -> str:
    payload = f"data: {json.dumps(data)}\n"
    if event:
        payload = f"event: {event}\n" + payload
    return payload + "\n"


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streams the assistant's reply back to the client as Server-Sent
    Events so the frontend can render it progressively instead of
    waiting for the entire response.

    The agent's own tool-calling/orchestration logic runs to completion
    first (it's inherently a multi-step, blocking process - tool
    execution has to finish before there's a final answer to show), off
    the event loop via a threadpool so it doesn't block other requests.
    Once the final text is ready, it's streamed out chunk by chunk so
    the UI still gets a live "typing" experience rather than a single
    blocking wait followed by an instant full response.
    """

    async def event_generator():
        try:
            full_response = await run_in_threadpool(
                run_agent, request.message, request.session_id
            )
        except Exception as e:
            logger.error(
                "Streaming chat failed",
                extra={"path": "/chat/stream", "error": str(e)},
                exc_info=True
            )
            yield _sse({"error": "Something went wrong on our end. Please try again."})
            yield _sse({}, event="done")
            return

        full_response = full_response or ""

        # Chunk by word so punctuation/markdown stays intact within a chunk.
        words = full_response.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            yield _sse({"delta": chunk})
            await asyncio.sleep(STREAM_CHUNK_DELAY_SECONDS)

        yield _sse({}, event="done")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )