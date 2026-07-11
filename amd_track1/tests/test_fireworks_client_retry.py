"""Tests for Fireworks transport retry behavior."""

import requests


class DummyResponse:
    def __init__(self, status_code, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self):
        return self._payload


def make_client():
    from amd_track1.executor import FireworksClient

    return FireworksClient(
        api_key="test-key",
        base_url="https://example.test",
        max_transport_retries=3,
        transport_retry_base_delay=0.0,
    )


def test_retries_transient_http_status_then_returns_success(monkeypatch):
    client = make_client()
    calls = []
    responses = [
        DummyResponse(500, "temporary failure"),
        DummyResponse(
            200,
            payload={
                "choices": [{"message": {"content": "answer"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        ),
    ]

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(requests, "post", fake_post)

    answer, error, input_tokens, output_tokens, latency = client.infer(
        "model", "prompt", timeout=30.0
    )

    assert answer == "answer"
    assert error is None
    assert input_tokens == 3
    assert output_tokens == 2
    assert latency is not None
    assert len(calls) == 2


def test_infer_uses_explicit_max_tokens(monkeypatch):
    client = make_client()
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return DummyResponse(
            200,
            payload={"choices": [{"message": {"content": "answer"}}]},
        )

    monkeypatch.setattr(requests, "post", fake_post)

    answer, error, *_ = client.infer("model", "prompt", timeout=30.0, max_tokens=96)

    assert answer == "answer"
    assert error is None
    assert calls[0][1]["json"]["max_tokens"] == 96


def test_does_not_retry_permanent_http_status(monkeypatch):
    client = make_client()
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return DummyResponse(400, "bad request")

    monkeypatch.setattr(requests, "post", fake_post)

    answer, error, *_ = client.infer("model", "prompt", timeout=30.0)

    assert answer is None
    assert error == "HTTP 400: bad request"
    assert len(calls) == 1


def test_retries_transport_exception_then_returns_success(monkeypatch):
    client = make_client()
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            raise requests.exceptions.ConnectionError("connection reset")
        return DummyResponse(
            200,
            payload={"choices": [{"message": {"content": "answer"}}]},
        )

    monkeypatch.setattr(requests, "post", fake_post)

    answer, error, *_ = client.infer("model", "prompt", timeout=30.0)

    assert answer == "answer"
    assert error is None
    assert len(calls) == 2


def test_transient_error_detection_matches_retry_statuses():
    from amd_track1.executor import FireworksClient

    for status_code in (429, 500, 502, 503, 504):
        assert FireworksClient.is_transient_error(f"HTTP {status_code}: temporary")

    for status_code in (400, 401, 404, 422):
        assert not FireworksClient.is_transient_error(f"HTTP {status_code}: permanent")
