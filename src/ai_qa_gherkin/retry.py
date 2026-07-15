from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential, before_sleep_log
from loguru import logger
from ai_qa_gherkin.config import settings

TRANSIENT_HTTP_STATUS = (429, 502, 503, 504)

class TransientError(Exception):
    """Retryable error (timeouts, throttling, temporary upstream failures)."""

class PermanentError(Exception):
    """Non-retryable error (auth, permissions, invalid requests)."""

def retry_policy():
    return retry(
        reraise=True,
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=settings.retry_min_seconds,
            max=settings.retry_max_seconds
        ),
        retry=retry_if_exception_type(TransientError),
        before_sleep=before_sleep_log(logger, logger.level("WARNING").no),
    )
