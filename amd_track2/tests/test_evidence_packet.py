"""Tests for evidence_packet module."""

from amd_track2.evidence_packet import EvidencePacketBuilder, VideoMetadata
from amd_track2.frame_extractor import FrameInfo
from amd_track2.video_probe import ProbeResult


def test_build_packet():
    """Should build complete evidence packet."""
    builder = EvidencePacketBuilder()
    probe = ProbeResult(
        success=True,
        duration_seconds=60.0,
        width=1920,
        height=1080,
        fps=30.0,
        container_format="mp4",
        video_codec="h264",
        has_video_stream=True,
    )
    frames = [
        FrameInfo(timestamp=0.5, path="/tmp/frame1.jpg", role="opening"),
        FrameInfo(timestamp=12.0, path="/tmp/frame2.jpg", role="mid_20"),
    ]
    packet = builder.build(
        task_id="task1",
        video_url="http://example.com/video.mp4",
        probe=probe,
        frames=frames,
        requested_styles=["formal", "sarcastic"],
    )

    assert packet.task_id == "task1"
    assert packet.video_url == "http://example.com/video.mp4"
    assert len(packet.frames) == 2
    assert packet.requested_styles == ["formal", "sarcastic"]
    assert packet.video_metadata.duration_seconds == 60.0


def test_packet_to_dict():
    """Should serialize to dict."""
    builder = EvidencePacketBuilder()
    probe = ProbeResult(
        success=True,
        duration_seconds=30.0,
        has_video_stream=True,
    )
    packet = builder.build(
        task_id="task2",
        video_url="http://example.com/v.mp4",
        probe=probe,
        frames=[FrameInfo(timestamp=1.0, path="/tmp/f.jpg", role="opening")],
        requested_styles=["formal"],
    )
    d = packet.to_dict()
    assert d["task_id"] == "task2"
    assert "video_metadata" in d
    assert "frames" in d
    assert len(d["frames"]) == 1