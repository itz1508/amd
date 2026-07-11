"""Tests for context_extractor module."""

from amd_track2.context_extractor import ContextExtractor, ContextResult
from amd_track2.evidence_packet import EvidencePacket, VideoMetadata
from amd_track2.frame_extractor import FrameInfo
from amd_track2.vision_client import VisionClient, VisionResponse


class FakeVisionClient:
    """Mock vision client for testing."""

    def __init__(self, response_data=None, success=True):
        self.response_data = response_data or {
            "scene_summary": "A person walking in a park",
            "main_subjects": ["person", "park"],
            "actions": ["walking"],
            "setting": "outdoor park",
            "important_objects": ["trees", "bench"],
            "scene_progression": ["person enters", "person walks"],
            "mood": "calm",
            "must_mention": ["person walking", "park setting"],
            "must_not_claim": ["specific identity"],
            "uncertainties": ["exact location unknown"],
            "confidence": 0.85,
        }
        self.success = success

    def complete(self, **kwargs):
        if self.success:
            return VisionResponse(
                success=True,
                content=str(self.response_data),
                parsed_json=self.response_data,
            )
        return VisionResponse(success=False, error_message="API error")


def test_extract_success():
    """Should extract context from vision response."""
    fake_vision = FakeVisionClient()
    extractor = ContextExtractor(fake_vision)

    packet = EvidencePacket(
        task_id="task1",
        video_url="http://example.com/v.mp4",
        video_metadata=VideoMetadata(
            duration_seconds=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            container_format="mp4",
            video_codec="h264",
        ),
        frames=[
            FrameInfo(timestamp=0.5, path="/tmp/f1.jpg", role="opening"),
        ],
        requested_styles=["formal"],
    )

    result = extractor.extract(packet)
    assert isinstance(result, ContextResult)
    assert result.scene_summary == "A person walking in a park"
    assert "person" in result.main_subjects
    assert result.confidence == 0.85


def test_extract_failure_fallback():
    """Should return weak fallback on vision failure."""
    fake_vision = FakeVisionClient(success=False)
    extractor = ContextExtractor(fake_vision)

    packet = EvidencePacket(
        task_id="task1",
        video_url="http://example.com/v.mp4",
        video_metadata=VideoMetadata(
            duration_seconds=60.0,
            width=None,
            height=None,
            fps=None,
            container_format=None,
            video_codec=None,
        ),
        frames=[
            FrameInfo(timestamp=0.5, path="/tmp/f1.jpg", role="opening"),
        ],
        requested_styles=["formal"],
    )

    result = extractor.extract(packet)
    assert isinstance(result, ContextResult)
    assert result.confidence == 0.3
    assert "context extraction failed" in result.uncertainties[0]


def test_validate_and_normalize():
    """Should normalize missing fields."""
    extractor = ContextExtractor(VisionClient())
    parsed = {
        "scene_summary": "Test scene",
        "main_subjects": ["subject1"],
        "confidence": 0.5,  # Below 0.7 threshold
    }
    result = extractor._validate_and_normalize(parsed)
    assert result.scene_summary == "Test scene"
    assert result.main_subjects == ["subject1"]
    assert result.confidence == 0.5
    # Should add uncertainties when confidence < 0.7
    assert len(result.uncertainties) > 0


def test_validate_empty_fields():
    """Should fill empty required fields with defaults."""
    extractor = ContextExtractor(VisionClient())
    parsed = {}
    result = extractor._validate_and_normalize(parsed)
    assert result.scene_summary == "A scene with visible subjects and actions."
    assert result.main_subjects == ["visible subjects in the scene"]
    assert result.must_mention == ["a scene is visible in the video"]
    assert result.confidence == 0.5