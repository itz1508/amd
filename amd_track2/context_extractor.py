"""Agent B: Extract visual context from evidence frames before captioning."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from amd_track2.evidence_packet import EvidencePacket
from amd_track2.frame_extractor import ExtractionResult, FrameInfo
from amd_track2.video_probe import ProbeResult
from amd_track2.vision_client import VisionClient, VisionResponse

logger = logging.getLogger(__name__)

CONTEXT_SYSTEM_PROMPT = """\
You are a visual evidence analyst. Your job is to describe what is VISIBLE in the provided video frames.
Do NOT caption. Do NOT infer identity, brand, location, or intent unless visually obvious.
Be explicit about uncertainty. Extract visible facts only.
Respond in valid JSON matching the requested schema exactly.
"""

CONTEXT_USER_PROMPT_TEMPLATE = """\
I have sampled frames from a video. Please analyze what is visible.

Video metadata:
- Duration: {duration}s
- Resolution: {width}x{height}
- Requested caption styles: {styles}

For each frame, describe what you see. Then synthesize into a structured context object.

Respond with valid JSON only, no markdown, no extra text. Use this exact schema:
{{
  "scene_summary": "brief overall description",
  "main_subjects": ["subject1", "subject2"],
  "actions": ["action1", "action2"],
  "setting": "indoor/outdoor/unknown and description",
  "important_objects": ["object1"],
  "scene_progression": ["frame 1 shows...", "frame 2 shows..."],
  "mood": "calm/energetic/tense/etc",
  "must_mention": ["visually obvious fact 1", "fact 2"],
  "must_not_claim": ["do not say X because not visible"],
  "uncertainties": ["unsure about Y"],
  "confidence": 0.85
}}

Rules:
- scene_summary must be non-empty
- main_subjects or actions must have at least one entry
- must_mention must be non-empty
- confidence is 0.0 to 1.0
- uncertainties must be present if confidence < 0.7
- Do not infer identity, brand, location, or intent unless visually obvious
"""


@dataclass
class ContextResult:
    """Structured visual context extracted from frames."""

    scene_summary: str
    main_subjects: List[str]
    actions: List[str]
    setting: str
    important_objects: List[str]
    scene_progression: List[str]
    mood: str
    must_mention: List[str]
    must_not_claim: List[str]
    uncertainties: List[str]
    confidence: float
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_summary": self.scene_summary,
            "main_subjects": self.main_subjects,
            "actions": self.actions,
            "setting": self.setting,
            "important_objects": self.important_objects,
            "scene_progression": self.scene_progression,
            "mood": self.mood,
            "must_mention": self.must_mention,
            "must_not_claim": self.must_not_claim,
            "uncertainties": self.uncertainties,
            "confidence": self.confidence,
        }


class ContextExtractor:
    """Agent B: turns visual evidence into source-of-truth context."""

    def __init__(self, vision_client: VisionClient):
        self.vision = vision_client

    def extract(self, packet: EvidencePacket) -> ContextResult:
        """One vision call per video to extract grounded context."""
        image_paths = [f.path for f in packet.frames]

        meta = packet.video_metadata
        duration = meta.duration_seconds or "unknown"
        width = meta.width or "unknown"
        height = meta.height or "unknown"
        styles = ", ".join(packet.requested_styles)

        user_prompt = CONTEXT_USER_PROMPT_TEMPLATE.format(
            duration=duration,
            width=width,
            height=height,
            styles=styles,
        )

        response = self.vision.complete(
            system_prompt=CONTEXT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            image_paths=image_paths,
            response_format={"type": "json_object"},
        )

        if not response.success or not response.parsed_json:
            logger.error("Context extraction failed: %s", response.error_message)
            return self._weak_fallback(packet, response.content)

        parsed = response.parsed_json
        validated = self._validate_and_normalize(parsed)
        validated.raw_response = response.content
        return validated

    def _validate_and_normalize(self, parsed: Dict[str, Any]) -> ContextResult:
        """Ensure required fields exist and types are correct."""
        scene_summary = self._str_or_default(parsed.get("scene_summary"), "A scene with visible subjects and actions.")
        main_subjects = self._list_of_str(parsed.get("main_subjects"))
        actions = self._list_of_str(parsed.get("actions"))
        setting = self._str_or_default(parsed.get("setting"), "unknown")
        important_objects = self._list_of_str(parsed.get("important_objects"))
        scene_progression = self._list_of_str(parsed.get("scene_progression"))
        mood = self._str_or_default(parsed.get("mood"), "neutral")
        must_mention = self._list_of_str(parsed.get("must_mention"))
        must_not_claim = self._list_of_str(parsed.get("must_not_claim"))
        uncertainties = self._list_of_str(parsed.get("uncertainties"))
        confidence = self._clamp_float(parsed.get("confidence"), 0.0, 1.0, 0.5)

        # Enforce validation rules
        if not scene_summary:
            scene_summary = "A scene with visible subjects and actions."
        if not main_subjects and not actions:
            main_subjects = ["visible subjects in the scene"]
        if not must_mention:
            must_mention = ["a scene is visible in the video"]
        if confidence < 0.7 and not uncertainties:
            uncertainties = ["some details may be unclear from the sampled frames"]

        return ContextResult(
            scene_summary=scene_summary,
            main_subjects=main_subjects,
            actions=actions,
            setting=setting,
            important_objects=important_objects,
            scene_progression=scene_progression,
            mood=mood,
            must_mention=must_mention,
            must_not_claim=must_not_claim,
            uncertainties=uncertainties,
            confidence=confidence,
        )

    @staticmethod
    def _str_or_default(value: Any, default: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    @staticmethod
    def _list_of_str(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if v is not None]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _clamp_float(value: Any, lo: float, hi: float, default: float) -> float:
        try:
            f = float(value)
            return max(lo, min(f, hi))
        except (TypeError, ValueError):
            return default

    def _weak_fallback(self, packet: EvidencePacket, raw_response: Optional[str]) -> ContextResult:
        """Return safe weak context when vision call fails completely."""
        logger.warning("Using weak fallback context for %s", packet.task_id)
        return ContextResult(
            scene_summary="A video scene with visible content.",
            main_subjects=["subjects visible in the video"],
            actions=["actions occurring in the video"],
            setting="unknown",
            important_objects=[],
            scene_progression=[f"Frame at {f.timestamp}s shows visible content" for f in packet.frames],
            mood="neutral",
            must_mention=["a video scene is visible"],
            must_not_claim=["do not claim specific identities or brands"],
            uncertainties=["context extraction failed; details are uncertain"],
            confidence=0.3,
            raw_response=raw_response,
        )