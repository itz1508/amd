"""Track 2 video captioning entrypoint."""

import json
import os
import sys
import tempfile
from pathlib import Path

from amd_track2.video_fetcher import VideoFetcher
from amd_track2.video_probe import VideoProbe
from amd_track2.frame_extractor import FrameExtractor
from amd_track2.evidence_packet import EvidencePacketBuilder
from amd_track2.vision_client import VisionClient
from amd_track2.context_extractor import ContextExtractor
from amd_track2.caption_writer import CaptionWriter
from amd_track2.caption_gap_checker import CaptionGapChecker
from amd_track2.output_validator import OutputValidator


def _fallback(styles):
    values = {
        "formal": "The video shows visible content in the scene.",
        "sarcastic": "Apparently, the scene decided to make an appearance.",
        "humorous_tech": "The scene has successfully loaded without errors.",
        "humorous_non_tech": "Well, something is certainly happening here.",
    }
    return {style: values.get(style, "The video shows visible content in the scene.") for style in styles}


class Track2Orchestrator:
    """Testable owner of the Track 2 fetch-to-caption pipeline."""

    def __init__(self, input_path: str = "/input/tasks.json", output_path: str = "/output/results.json"):
        self.input_path, self.output_path = input_path, output_path
        self.fetcher = VideoFetcher()
        self.prober = VideoProbe()
        self.extractor = FrameExtractor()
        self.vision = VisionClient()
        self.context_extractor = ContextExtractor(self.vision)
        self.caption_writer = CaptionWriter(self.vision)
        self.gap_checker = CaptionGapChecker()
        self.output_validator = OutputValidator()

    def _fallback_result(self, task_id, styles):
        return {"task_id": task_id, "captions": _fallback(styles)}

    def _read_input(self):
        try:
            with open(self.input_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, list) else data.get("tasks") if isinstance(data, dict) else None
        except (OSError, ValueError, TypeError):
            return None

    @staticmethod
    def _safe_unlink(path):
        try:
            if path:
                os.unlink(path)
        except OSError:
            pass

    def _emergency_write(self, results):
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as handle:
            json.dump(results, handle)


def main() -> int:
    input_path = os.environ.get("TRACK2_INPUT", "/input/tasks.json")
    output_path = os.environ.get("TRACK2_OUTPUT", "/output/results.json")
    required = ["FIREWORKS_API_KEY", "FIREWORKS_BASE_URL", "ALLOWED_MODELS"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        return 1

    with open(input_path, "r", encoding="utf-8") as handle:
        tasks = json.load(handle)
    if not isinstance(tasks, list):
        print("Input must be a JSON list", file=sys.stderr)
        return 1

    vision = VisionClient(
        api_key=os.environ["FIREWORKS_API_KEY"],
        base_url=os.environ["FIREWORKS_BASE_URL"],
        model=os.environ["ALLOWED_MODELS"].split(",")[0].strip(),
    )
    fetcher, probe, extractor = VideoFetcher(), VideoProbe(), FrameExtractor()
    packet_builder = EvidencePacketBuilder()
    context_extractor, caption_writer = ContextExtractor(vision), CaptionWriter(vision)
    results = []

    with tempfile.TemporaryDirectory(prefix="amd_track2_") as work:
        for task in tasks:
            task_id = str(task.get("task_id", ""))
            styles = task.get("styles", ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"])
            captions = _fallback(styles)
            try:
                fetched = fetcher.fetch(task.get("video_url", ""), task_id)
                if not fetched.success or not fetched.local_path:
                    raise RuntimeError(fetched.error_message or "video fetch failed")
                metadata = probe.probe(fetched.local_path)
                extracted = extractor.extract(fetched.local_path, metadata, str(Path(work) / task_id))
                if not extracted.success:
                    raise RuntimeError(extracted.error_message or "frame extraction failed")
                packet = packet_builder.build(task_id, task["video_url"], metadata, extracted.frames, styles)
                context = context_extractor.extract(packet)
                captions = caption_writer.write(context, styles).to_dict()
                if not self_gap_check(captions, context, styles):
                    captions = _fallback(styles)
            except Exception as exc:
                print(f"Task {task_id} degraded to fallback: {exc}", file=sys.stderr)
            results.append({"task_id": task_id, "captions": captions})

    OutputValidator().validate_and_write(results, tasks, output_path)
    return 0


def self_gap_check(captions, context, styles):
    """Return whether generated captions satisfy the local gap checks."""
    from amd_track2.caption_gap_checker import CaptionGapChecker
    return CaptionGapChecker().check(captions, context, styles).valid


if __name__ == "__main__":
    raise SystemExit(main())
