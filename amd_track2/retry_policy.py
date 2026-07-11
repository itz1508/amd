"""Bounded retry and timeout policies for Track 2 runtime reliability."""

import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RetryPolicy:
    """Configurable retry with exponential backoff and hard deadline."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        deadline_seconds: Optional[float] = None,
        retryable_exceptions: tuple = (Exception,),
    ):
        self.max_attempts = max(max_attempts, 1)
        self.base_delay = base_delay_seconds
        self.max_delay = max_delay_seconds
        self.deadline = deadline_seconds
        self.retryable = retryable_exceptions

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute fn with retries. Returns result or raises last exception."""
        start = time.monotonic()
        last_exception: Exception = RuntimeError("Unexpected retry exhaustion")

        for attempt in range(1, self.max_attempts + 1):
            try:
                if self.deadline is not None:
                    elapsed = time.monotonic() - start
                    if elapsed >= self.deadline:
                        raise TimeoutError(
                            f"Retry deadline exceeded after {elapsed:.1f}s"
                        )
                return fn(*args, **kwargs)
            except self.retryable as exc:
                last_exception = exc
                if attempt < self.max_attempts:
                    delay = min(
                        self.base_delay * (2 ** (attempt - 1)), self.max_delay
                    )
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                        attempt,
                        self.max_attempts,
                        fn.__name__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "All %d attempts failed for %s: %s",
                        self.max_attempts,
                        fn.__name__,
                        exc,
                    )
        raise last_exception


def with_retry(
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 30.0,
    deadline_seconds: Optional[float] = None,
    retryable_exceptions: tuple = (Exception,),
) -> Callable[[F], F]:
    """Decorator factory applying RetryPolicy."""

    policy = RetryPolicy(
        max_attempts=max_attempts,
        base_delay_seconds=base_delay_seconds,
        max_delay_seconds=max_delay_seconds,
        deadline_seconds=deadline_seconds,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return policy.call(fn, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator