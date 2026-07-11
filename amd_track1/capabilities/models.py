from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class CapabilityAdapter:
    provider_id: str
    model_id: str
    execution_class: str
    supported_capabilities: List[str]

    def invoke(self, prompt: str) -> Dict[str, Any]:
        return {"prompt": prompt, "provider_id": self.provider_id, "model_id": self.model_id}

    def normalize_usage(self) -> Dict[str, Any]:
        return {"provider_id": self.provider_id, "model_id": self.model_id}

    def classify_error(self, error: Exception) -> str:
        return type(error).__name__

    def health_check(self) -> bool:
        return True
