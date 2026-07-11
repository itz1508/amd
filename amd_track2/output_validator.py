"""Guarantee Track 2 output contract: valid JSON with correct schema."""

import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OutputValidationFailure(Exception):
    """Raised when output validation fails."""
    pass


class OutputValidator:
    """Validate and atomically write Track 2 results."""

    def validate_and_write(
        self,
        results: List[Dict[str, Any]],
        input_tasks: List[Dict[str, Any]],
        output_path: str,
    ) -> bool:
        """Validate results against input contract and write atomically.

        Returns True on success, False on failure.
        Raises OutputValidationFailure if validation fails after repair attempt.
        """
        errors = self._validate(results, input_tasks)
        if errors:
            for err in errors:
                logger.error("Output validation error: %s", err)
            # Attempt repair: fill missing with safe fallbacks
            repaired = self._repair(results, input_tasks)
            # Revalidate after repair
            repair_errors = self._validate(repaired, input_tasks)
            if repair_errors:
                logger.error("Output repair failed: %d errors remain", len(repair_errors))
                raise OutputValidationFailure(
                    f"Output validation failed after repair: {repair_errors}"
                )
            results = repaired

        # Atomic write with read-back validation
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            suffix=".json", prefix="results_", dir=dir_name or "."
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, output_path)

            # Read-back validation
            read_back = self._read_back_validate(output_path, results)
            if read_back is not True:
                logger.error("Read-back validation failed: %s", read_back)
                raise OutputValidationFailure(f"Read-back validation failed: {read_back}")

            logger.info("Wrote %d results to %s", len(results), output_path)
            return True
        except OutputValidationFailure:
            raise
        except Exception as exc:
            logger.exception("Failed to write output")
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return False

    def _read_back_validate(
        self, output_path: str, expected: List[Dict[str, Any]]
    ) -> bool:
        """Validate written file matches expected content. Returns True on success, raises on failure."""
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                actual = json.load(f)

            if not isinstance(actual, list):
                raise OutputValidationFailure("Output is not a list after read-back")

            if len(actual) != len(expected):
                raise OutputValidationFailure(
                    f"Output count {len(actual)} != expected {len(expected)}"
                )

            # Verify each task ID is present
            actual_ids = {r.get("task_id") for r in actual if isinstance(r, dict)}
            expected_ids = {r.get("task_id") for r in expected}
            missing = expected_ids - actual_ids
            if missing:
                raise OutputValidationFailure(f"Missing task IDs after read-back: {missing}")

            # Verify no duplicate IDs
            seen: set = set()
            for r in actual:
                tid = r.get("task_id")
                if tid and tid in seen:
                    raise OutputValidationFailure(f"Duplicate task_id in output: {tid}")
                if tid:
                    seen.add(tid)

            return True
        except json.JSONDecodeError as exc:
            raise OutputValidationFailure(f"Invalid JSON in output file: {exc}")
        except OutputValidationFailure:
            raise
        except Exception as exc:
            raise OutputValidationFailure(f"Read-back validation error: {exc}")

    def _validate(
        self, results: List[Dict[str, Any]], input_tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """Return list of validation error strings."""
        errors: List[str] = []

        if not isinstance(results, list):
            errors.append("Output is not a list")
            return errors

        if len(results) != len(input_tasks):
            errors.append(
                f"Output count {len(results)} != input count {len(input_tasks)}"
            )

        input_ids = {t.get("task_id") for t in input_tasks}
        output_ids = set()
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                errors.append(f"Result[{i}] is not a dict")
                continue

            task_id = result.get("task_id")
            if not task_id:
                errors.append(f"Result[{i}] missing task_id")
            elif task_id in output_ids:
                errors.append(f"Duplicate task_id: {task_id}")
            elif task_id not in input_ids:
                errors.append(f"Unknown task_id: {task_id}")
            output_ids.add(task_id)

            captions = result.get("captions")
            if not isinstance(captions, dict):
                errors.append(f"Result[{i}] missing or invalid captions object")
                continue

            # Find matching input task for style requirements
            matching_input = next(
                (t for t in input_tasks if t.get("task_id") == task_id), None
            )
            required_styles = (
                matching_input.get("styles", []) if matching_input else []
            )

            for style in required_styles:
                if style not in captions:
                    errors.append(
                        f"Result[{i}] missing required style '{style}'"
                    )
                else:
                    val = captions[style]
                    if not isinstance(val, str):
                        errors.append(
                            f"Result[{i}] style '{style}' is not a string"
                        )
                    elif not val.strip():
                        errors.append(
                            f"Result[{i}] style '{style}' is empty"
                        )

        return errors

    def _repair(
        self, results: List[Dict[str, Any]], input_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fill missing results with safe fallback captions."""
        # Build lookup
        by_id: Dict[str, Dict[str, Any]] = {}
        for r in results:
            tid = r.get("task_id")
            if tid:
                by_id[tid] = r

        repaired: List[Dict[str, Any]] = []
        for task in input_tasks:
            tid = task.get("task_id")
            styles = task.get("styles", [])
            existing = by_id.get(tid, {})

            existing_captions = existing.get("captions")
            captions = existing_captions if isinstance(existing_captions, dict) else {}
            # Ensure all styles exist
            for style in styles:
                if style not in captions or not isinstance(captions.get(style), str) or not captions[style].strip():
                    captions[style] = "A video showing visible content."

            repaired.append({"task_id": tid, "captions": captions})

        return repaired