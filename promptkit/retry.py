from __future__ import annotations

import random
from dataclasses import dataclass

from promptkit.errors import EngineError, ProviderError, RateLimitError

RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 3
    initial_backoff: float = 0.5
    max_backoff: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True

    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self.attempts:
            return False

        return is_retryable(error)

    def backoff(self, attempt: int, retry_after: float | None = None) -> float:
        if retry_after is not None:
            return min(retry_after, self.max_backoff)

        delay = min(
            self.initial_backoff * self.multiplier ** (attempt - 1), self.max_backoff
        )

        if self.jitter:
            return random.uniform(0.0, delay)

        return delay


NO_RETRY = RetryPolicy(attempts=1)


def is_retryable(error: Exception) -> bool:
    if isinstance(error, RateLimitError):
        return True

    if isinstance(error, ProviderError):
        if error.status_code is None:
            return True

        return error.status_code in RETRYABLE_STATUS

    return False


def retry_after_of(error: Exception) -> float | None:
    if isinstance(error, RateLimitError):
        return error.retry_after

    return None


def describe(error: Exception) -> str:
    if isinstance(error, EngineError):
        return type(error).__name__

    return type(error).__name__


__all__ = [
    "NO_RETRY",
    "RETRYABLE_STATUS",
    "RetryPolicy",
    "is_retryable",
    "retry_after_of",
]
