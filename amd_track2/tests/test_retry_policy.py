"""Tests for retry_policy module."""

import pytest
from amd_track2.retry_policy import RetryPolicy, with_retry


def test_retry_success_on_first_attempt():
    """Should return result immediately on success."""
    policy = RetryPolicy(max_attempts=3)

    def succeed():
        return 42

    result = policy.call(succeed)
    assert result == 42


def test_retry_eventually_succeeds():
    """Should retry and eventually succeed."""
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=0.01)
    attempts = 0

    def fail_twice():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("fail")
        return "success"

    result = policy.call(fail_twice)
    assert result == "success"
    assert attempts == 3


def test_retry_exhaustion_raises():
    """Should raise last exception when all attempts exhausted."""
    policy = RetryPolicy(max_attempts=2, base_delay_seconds=0.01)

    def always_fail():
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        policy.call(always_fail)


def test_retry_deadline():
    """Should raise TimeoutError when deadline exceeded."""
    policy = RetryPolicy(max_attempts=10, base_delay_seconds=0.1, deadline_seconds=0.05)

    def slow_fail():
        raise ValueError("fail")

    with pytest.raises(TimeoutError):
        policy.call(slow_fail)


def test_retry_non_retryable_exception():
    """Should not retry non-retryable exceptions."""
    policy = RetryPolicy(
        max_attempts=3,
        base_delay_seconds=0.01,
        retryable_exceptions=(ValueError,),
    )

    def raise_type_error():
        raise TypeError("not retryable")

    with pytest.raises(TypeError):
        policy.call(raise_type_error)


def test_with_retry_decorator():
    """Decorator should apply retry policy."""

    @with_retry(max_attempts=2, base_delay_seconds=0.01)
    def flaky():
        flaky.calls += 1
        if flaky.calls < 2:
            raise ValueError("fail")
        return "ok"

    flaky.calls = 0
    result = flaky()
    assert result == "ok"
    assert flaky.calls == 2