from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List


def _definitions_dir() -> Path:
    return Path(__file__).resolve().parent / "definitions"


@lru_cache(maxsize=1)
def load_capability_definitions() -> List[Dict[str, Any]]:
    definitions: List[Dict[str, Any]] = []
    for path in sorted(_definitions_dir().glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        definitions.append(data)
    return definitions
