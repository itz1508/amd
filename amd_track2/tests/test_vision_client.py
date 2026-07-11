"""Tests for vision_client module."""

from amd_track2.vision_client import VisionClient, VisionResponse


def test_vision_response_defaults():
    """VisionResponse should have sensible defaults."""
    resp = VisionResponse(success=False)
    assert resp.success is False
    assert resp.content is None
    assert resp.parsed_json is None


def test_encode_image_data_uri():
    """Should create valid data URI."""
    client = VisionClient()
    # Create a minimal valid JPEG (SOI + EOI markers)
    import tempfile
    import os

    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, b"\xff\xd8\xff\xd9")  # Minimal JPEG
    os.close(fd)

    try:
        uri = client._encode_image(path)
        assert uri.startswith("data:image/jpeg;base64,")
        # Should be decodable
        import base64
        b64_part = uri.split(",")[1]
        decoded = base64.b64decode(b64_part)
        assert decoded == b"\xff\xd8\xff\xd9"
    finally:
        os.unlink(path)


def test_extract_json_direct():
    """Should parse direct JSON."""
    client = VisionClient()
    parsed = client._extract_json('{"key": "value"}')
    assert parsed == {"key": "value"}


def test_extract_json_from_markdown():
    """Should extract JSON from markdown code block."""
    client = VisionClient()
    text = 'Some text\\n```json\\n{"a": 1}\\n```\\nMore text'
    parsed = client._extract_json(text)
    assert parsed == {"a": 1}


def test_extract_json_from_braces():
    """Should extract first JSON object from text."""
    client = VisionClient()
    text = 'prefix {"nested": {"key": "value"}} suffix'
    parsed = client._extract_json(text)
    assert parsed == {"nested": {"key": "value"}}


def test_extract_json_invalid():
    """Should return None for invalid JSON."""
    client = VisionClient()
    parsed = client._extract_json("not json at all")
    assert parsed is None


def test_build_content_with_missing_image():
    """Should skip missing image paths."""
    client = VisionClient()
    content = client._build_content("Describe this", ["/nonexistent/path.jpg"])
    # Should only have text entry
    assert len(content) == 1
    assert content[0]["type"] == "text"


def test_headers():
    """Should include Authorization header."""
    client = VisionClient(api_key="test-key")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"


def test_endpoint_with_base_url():
    """Should construct endpoint from base_url."""
    client = VisionClient(base_url="https://api.example.com/v1")
    assert client._endpoint() == "https://api.example.com/v1/chat/completions"


def test_endpoint_default():
    """Missing Fireworks base URL must not fall back to OpenAI."""
    client = VisionClient()
    assert client._endpoint() == ""
