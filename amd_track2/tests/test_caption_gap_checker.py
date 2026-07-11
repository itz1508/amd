"""Tests for caption_gap_checker module."""

from amd_track2.caption_gap_checker import CaptionGapChecker
from amd_track2.context_extractor import ContextResult


def test_valid_captions():
    """Should report valid when all checks pass."""
    checker = CaptionGapChecker()
    context = ContextResult(
        scene_summary="A person walking in a park",
        main_subjects=["person", "park"],
        actions=["walking"],
        setting="outdoor",
        important_objects=["trees"],
        scene_progression=["person walks"],
        mood="calm",
        must_mention=["person walking"],
        must_not_claim=["specific identity"],
        uncertainties=[],
        confidence=0.85,
    )
    captions = {
        "formal": "A person is walking in a park with trees.",
        "sarcastic": "Oh look, another exciting park walk.",
        "humorous_tech": "This park walk has O(n) scenic complexity.",
        "humorous_non_tech": "Walking in the park like a normal human being.",
    }

    report = checker.check(captions, context, list(captions.keys()))
    assert report.valid is True
    assert len(report.gaps) == 0


def test_missing_style():
    """Should detect missing style."""
    checker = CaptionGapChecker()
    context = ContextResult(
        scene_summary="A scene",
        main_subjects=["subject"],
        actions=["action"],
        setting="unknown",
        important_objects=[],
        scene_progression=[],
        mood="neutral",
        must_mention=["scene"],
        must_not_claim=[],
        uncertainties=[],
        confidence=0.5,
    )
    captions = {"formal": "A scene is visible."}

    report = checker.check(captions, context, ["formal", "sarcastic"])
    assert report.valid is False
    gap = report.gaps[0]
    assert gap.gap_code == "CAP-001-MISSING-STYLE"
    assert gap.style == "sarcastic"


def test_empty_caption():
    """Should detect empty caption."""
    checker = CaptionGapChecker()
    context = ContextResult(
        scene_summary="A scene",
        main_subjects=["subject"],
        actions=["action"],
        setting="unknown",
        important_objects=[],
        scene_progression=[],
        mood="neutral",
        must_mention=["scene"],
        must_not_claim=[],
        uncertainties=[],
        confidence=0.5,
    )
    captions = {"formal": "   "}

    report = checker.check(captions, context, ["formal"])
    assert report.valid is False
    assert any(g.gap_code == "CAP-002-EMPTY-CAPTION" for g in report.gaps)


def test_tech_jargon_in_non_tech():
    """Should detect tech jargon in humorous_non_tech."""
    checker = CaptionGapChecker()
    context = ContextResult(
        scene_summary="A scene",
        main_subjects=["subject"],
        actions=["action"],
        setting="unknown",
        important_objects=[],
        scene_progression=[],
        mood="neutral",
        must_mention=["scene"],
        must_not_claim=[],
        uncertainties=[],
        confidence=0.5,
    )
    captions = {
        "humorous_non_tech": "This video is like debugging your life.",
    }

    report = checker.check(captions, context, ["humorous_non_tech"])
    assert report.valid is False
    assert any(g.gap_code == "CAP-003-TECH-JARGON" for g in report.gaps)


def test_identical_captions():
    """Should detect identical captions across styles."""
    checker = CaptionGapChecker()
    context = ContextResult(
        scene_summary="A scene",
        main_subjects=["subject"],
        actions=["action"],
        setting="unknown",
        important_objects=[],
        scene_progression=[],
        mood="neutral",
        must_mention=["scene"],
        must_not_claim=[],
        uncertainties=[],
        confidence=0.5,
    )
    captions = {
        "formal": "Same caption.",
        "sarcastic": "Same caption.",
    }

    report = checker.check(captions, context, ["formal", "sarcastic"])
    assert report.valid is False
    assert any(g.gap_code == "CAP-004-IDENTICAL-CAPTIONS" for g in report.gaps)


def test_not_grounded():
    """Should detect captions not grounded in context."""
    checker = CaptionGapChecker()
    context = ContextResult(
        scene_summary="A person walking in a park",
        main_subjects=["person", "park"],
        actions=["walking"],
        setting="outdoor",
        important_objects=["trees"],
        scene_progression=["person walks"],
        mood="calm",
        must_mention=["person walking"],
        must_not_claim=[],
        uncertainties=[],
        confidence=0.85,
    )
    captions = {
        "formal": "The quantum mechanics of black holes is fascinating.",
    }

    report = checker.check(captions, context, ["formal"])
    assert report.valid is False
    assert any(g.gap_code == "CAP-005-NOT-GROUNDED" for g in report.gaps)


def test_contradiction():
    """Should detect contradictions with must_not_claim."""
    checker = CaptionGapChecker()
    context = ContextResult(
        scene_summary="A person walking",
        main_subjects=["person"],
        actions=["walking"],
        setting="park",
        important_objects=[],
        scene_progression=[],
        mood="calm",
        must_mention=["walking"],
        must_not_claim=["specific identity"],
        uncertainties=[],
        confidence=0.8,
    )
    captions = {
        "formal": "The specific identity of this person is John Smith.",
    }

    report = checker.check(captions, context, ["formal"])
    assert report.valid is False
    assert any(g.gap_code == "CAP-006-CONTRADICTION" for g in report.gaps)