"""Tests for caption_writer module."""

from amd_track2.caption_writer import CaptionWriter, CaptionResult
from amd_track2.context_extractor import ContextResult
from amd_track2.vision_client import VisionClient, VisionResponse


class FakeVisionClient:
    """Mock vision client for testing."""

    def __init__(self, response_data=None, success=True):
        self.response_data = response_data or {
            "captions": {
                "formal": "A person is walking in a park.",
                "sarcastic": "Oh great, another park walk video.",
                "humorous_tech": "This park walk has O(n) complexity.",
                "humorous_non_tech": "Walking in the park like a normal human.",
            }
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


def test_write_success():
    """Should generate captions from context."""
    fake_vision = FakeVisionClient()
    writer = CaptionWriter(fake_vision)

    context = ContextResult(
        scene_summary="A person walking in a park",
        main_subjects=["person"],
        actions=["walking"],
        setting="outdoor park",
        important_objects=["trees"],
        scene_progression=["person walks"],
        mood="calm",
        must_mention=["person walking"],
        must_not_claim=["specific identity"],
        uncertainties=[],
        confidence=0.85,
    )

    result = writer.write(context, ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"])
    assert isinstance(result, CaptionResult)
    assert "formal" in result.captions
    assert "sarcastic" in result.captions
    assert result.captions["formal"] == "A person is walking in a park."


def test_write_failure_fallback():
    """Should return fallback captions on vision failure."""
    fake_vision = FakeVisionClient(success=False)
    writer = CaptionWriter(fake_vision)

    context = ContextResult(
        scene_summary="A scene",
        main_subjects=["subject"],
        actions=["action"],
        setting="unknown",
        important_objects=[],
        scene_progression=[],
        mood="neutral",
        must_mention=["scene visible"],
        must_not_claim=[],
        uncertainties=[],
        confidence=0.5,
    )

    result = writer.write(context, ["formal", "sarcastic"])
    assert isinstance(result, CaptionResult)
    assert "formal" in result.captions
    assert "sarcastic" in result.captions
    assert "visible content" in result.captions["formal"]


def test_write_missing_styles_in_response():
    """Should fill missing styles with fallback."""
    fake_vision = FakeVisionClient(
        response_data={"captions": {"formal": "Only formal caption."}}
    )
    writer = CaptionWriter(fake_vision)

    context = ContextResult(
        scene_summary="A scene",
        main_subjects=["subject"],
        actions=["action"],
        setting="unknown",
        important_objects=[],
        scene_progression=[],
        mood="neutral",
        must_mention=["scene visible"],
        must_not_claim=[],
        uncertainties=[],
        confidence=0.5,
    )

    result = writer.write(context, ["formal", "sarcastic", "humorous_tech"])
    assert "formal" in result.captions
    assert "sarcastic" in result.captions
    assert "humorous_tech" in result.captions
    # Missing styles should have fallback values
    assert result.captions["sarcastic"] != ""
    assert result.captions["humorous_tech"] != ""


def test_safe_fallback_per_style():
    """Should generate style-specific fallback captions."""
    writer = CaptionWriter(VisionClient())
    context = ContextResult(
        scene_summary="A person walking",
        main_subjects=["person"],
        actions=["walking"],
        setting="park",
        important_objects=[],
        scene_progression=[],
        mood="calm",
        must_mention=["walking"],
        must_not_claim=[],
        uncertainties=[],
        confidence=0.8,
    )

    formal = writer._safe_fallback_for_style("formal", context)
    sarcastic = writer._safe_fallback_for_style("sarcastic", context)
    tech = writer._safe_fallback_for_style("humorous_tech", context)
    non_tech = writer._safe_fallback_for_style("humorous_non_tech", context)

    assert "person walking" in formal.lower()
    assert "oh, look" in sarcastic.lower()
    assert "404" in tech.lower()
    assert "every day" in non_tech.lower()