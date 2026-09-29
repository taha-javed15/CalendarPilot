import functools
import time

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Kept broad on purpose: googleapiclient raises HttpError for API-side
# failures, but connection drops surface as plain socket/timeout errors.
# We only want to retry things that are plausibly transient.
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def _is_retryable_http_error(exc: Exception) -> bool:
    """
    googleapiclient.errors.HttpError exposes `resp.status`. We check for it
    duck-typed so this module doesn't hard-depend on the google client.
    """
    status = getattr(getattr(exc, "resp", None), "status", None)

    if status is None:
        return False

    return status == 429 or 500 <= status < 600


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
):
    """
    Retries a function on transient failures with exponential backoff.
    Re-raises the last exception if all attempts are exhausted.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0

            while True:
                attempt += 1

                try:
                    return func(*args, **kwargs)

                except Exception as exc:
                    retryable = (
                        isinstance(exc, RETRYABLE_EXCEPTIONS)
                        or _is_retryable_http_error(exc)
                    )

                    if not retryable or attempt >= max_attempts:
                        logger.warning(
                            "Giving up after failed attempt",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "error": str(exc),
                            },
                        )
                        raise

                    delay = base_delay * (2 ** (attempt - 1))

                    logger.warning(
                        "Transient error, retrying",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "delay": delay,
                            "error": str(exc),
                        },
                    )

                    time.sleep(delay)

        return wrapper

    return decorator