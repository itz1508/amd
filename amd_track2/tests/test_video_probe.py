"""Tests for video_probe module."""

from amd_track2.video_probe import ProbeResult, VideoProbe


def test_probe_result_defaults():
    """ProbeResult should have sensible defaults."""
    result = ProbeResult(success=False)
    assert result.success is False
    assert result.duration_seconds is None
    assert result.has_video_stream is False


def test_probe_missing_file():
    """Should handle missing file gracefully."""
    prober = VideoProbe()
    result = prober.probe("/nonexistent/path.mp4")
    assert result.success is False
    assert result.error_message is not None


def test_probe_parse_duration_from_format():
    """Should parse duration from format section."""
    prober = VideoProbe()
    data = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
            }
        ],
        "format": {"duration": "120.5", "format_name": "mp4"},
    }
    result = prober._parse(data)
    assert result.success is True
    assert result.duration_seconds == 120.5
    assert result.width == 1920
    assert result.height == 1080
    assert result.fps == 30.0
    assert result.container_format == "mp4"
    assert result.video_codec == "h264"
    assert result.has_video_stream is True


def test_probe_parse_no_video_stream():
    """Should fail when no video stream present."""
    prober = VideoProbe()
    data = {
        "streams": [{"codec_type": "audio", "codec_name": "aac"}],
        "format": {"duration": "60.0"},
    }
    result = prober._parse(data)
    assert result.success is False
    assert "No video stream" in (result.error_message or "")


def test_probe_parse_fps_fraction():
    """Should parse fractional frame rates."""
    prober = VideoProbe()
    data = {
        "streams": [
            {
                "codec_type": "video",
                "r_frame_rate": "30000/1001",
            }
        ],
        "format": {},
    }
    result = prober._parse(data)
    assert result.success is True
    assert abs(result.fps - 29.97) < 0.01


def test_probe_parse_duration_fallback_nb_frames():
    """Should compute duration from nb_frames when format duration missing."""
    prober = VideoProbe()
    data = {
        "streams": [
            {
                "codec_type": "video",
                "r_frame_rate": "25/1",
                "nb_frames": "250",
            }
        ],
        "format": {},
    }
    result = prober._parse(data)
    assert result.success is True
    assert result.duration_seconds == 10.0  # 250 frames / 25 fps