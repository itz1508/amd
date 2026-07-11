"""Tests for frame_extractor module."""

from amd_track2.frame_extractor import FrameExtractor
from amd_track2.video_probe import ProbeResult


def test_extraction_no_video_stream():
    """Should fail when probe reports no video stream."""
    extractor = FrameExtractor()
    probe = ProbeResult(success=False, has_video_stream=False)
    result = extractor.extract("/fake/path.mp4", probe)
    assert result.success is False
    assert len(result.frames) == 0


def test_compute_timestamps_normal_duration():
    """Should compute 6 timestamps for a 100s video."""
    extractor = FrameExtractor()
    timestamps = extractor._compute_timestamps(100.0)
    assert len(timestamps) == 6
    # Check roles
    roles = [t[1] for t in timestamps]
    assert "opening" in roles
    assert "mid_20" in roles
    assert "mid_40" in roles
    assert "mid_60" in roles
    assert "mid_80" in roles
    assert "closing" in roles


def test_compute_timestamps_clamps_to_duration():
    """Should clamp timestamps within video duration."""
    extractor = FrameExtractor()
    timestamps = extractor._compute_timestamps(1.0)
    # For 1s video, opening at 0.5s, closing at min(0.95, 0.5) = 0.5
    # Should deduplicate
    assert len(timestamps) >= 1
    for ts, _ in timestamps:
        assert 0.0 <= ts <= 1.0


def test_compute_timestamps_zero_duration():
    """Should return empty for zero duration."""
    extractor = FrameExtractor()
    timestamps = extractor._compute_timestamps(0.0)
    assert len(timestamps) == 0


def test_compute_timestamps_negative_duration():
    """Should return empty for negative duration."""
    extractor = FrameExtractor()
    timestamps = extractor._compute_timestamps(-5.0)
    assert len(timestamps) == 0


def test_fallback_timestamps():
    """Should return fallback timestamps when duration unknown."""
    extractor = FrameExtractor()
    timestamps = extractor._fallback_timestamps("/fake/path.mp4")
    assert len(timestamps) == 6
    # All should be fallback roles
    for _, role in timestamps:
        assert role.startswith("fallback_")