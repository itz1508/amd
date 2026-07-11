"""Tests for video_fetcher module."""

from amd_track2.video_fetcher import FetchResult, VideoFetcher


def test_fetch_result_defaults():
    """FetchResult should have sensible defaults."""
    result = FetchResult(success=True)
    assert result.success is True
    assert result.local_path is None
    assert result.error_code is None


def test_fetcher_rejects_invalid_url():
    """Should reject non-http URLs."""
    fetcher = VideoFetcher()
    result = fetcher.fetch("ftp://example.com/video.mp4", "task1")
    assert result.success is False
    assert result.error_code == "invalid_url"


def test_fetcher_rejects_empty_url():
    """Should reject empty URL."""
    fetcher = VideoFetcher()
    result = fetcher.fetch("", "task1")
    assert result.success is False
    assert result.error_code == "invalid_url"


def test_fetcher_rejects_url_without_host():
    """Should reject URL missing host."""
    fetcher = VideoFetcher()
    result = fetcher.fetch("http:///path", "task1")
    assert result.success is False
    assert result.error_code == "invalid_url"