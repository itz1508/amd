"""Tests for AMD Track 1 model role helper.

Tests verify that SOLVER_MODEL and VERIFIER_MODEL are selected correctly
from environment variables or ALLOWED_MODELS fallback.
"""

import os
import pytest


class TestModelRoleHelper:
    """Test model role selection logic."""

    def test_solver_and_verifier_from_env_override(self, monkeypatch):
        """SOLVER_MODEL and VERIFIER_MODEL env vars take precedence over ALLOWED_MODELS."""
        monkeypatch.setenv("SOLVER_MODEL", "solver-env-model")
        monkeypatch.setenv("VERIFIER_MODEL", "verifier-env-model")
        monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b,model-c,solver-env-model,verifier-env-model")
        
        # Import after setting env vars
        from amd_track1.model_roles import get_solver_model, get_verifier_model, reset_model_cache
        reset_model_cache()
        
        assert get_solver_model() == "solver-env-model"
        assert get_verifier_model() == "verifier-env-model"

    def test_solver_fallback_to_first_allowed(self, monkeypatch):
        """When SOLVER_MODEL not set, fallback to first model in ALLOWED_MODELS."""
        monkeypatch.delenv("SOLVER_MODEL", raising=False)
        monkeypatch.delenv("VERIFIER_MODEL", raising=False)
        monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b,model-c")
        
        from amd_track1.model_roles import get_solver_model, reset_model_cache
        reset_model_cache()
        
        assert get_solver_model() == "model-a"

    def test_verifier_fallback_to_last_allowed(self, monkeypatch):
        """When VERIFIER_MODEL not set, fallback to last model in ALLOWED_MODELS."""
        monkeypatch.delenv("SOLVER_MODEL", raising=False)
        monkeypatch.delenv("VERIFIER_MODEL", raising=False)
        monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b,model-c")
        
        from amd_track1.model_roles import get_verifier_model, reset_model_cache
        reset_model_cache()
        
        assert get_verifier_model() == "model-c"

    def test_single_model_verifier_unavailable(self, monkeypatch):
        """When only one model in ALLOWED_MODELS, verifier unavailable unless explicitly set."""
        monkeypatch.delenv("SOLVER_MODEL", raising=False)
        monkeypatch.delenv("VERIFIER_MODEL", raising=False)
        monkeypatch.setenv("ALLOWED_MODELS", "only-model")
        
        from amd_track1.model_roles import get_solver_model, get_verifier_model, is_verifier_available, reset_model_cache
        reset_model_cache()
        
        assert get_solver_model() == "only-model"
        assert get_verifier_model() is None
        assert is_verifier_available() is False

    def test_single_model_with_explicit_verifier(self, monkeypatch):
        """Single model with explicit VERIFIER_MODEL set makes verifier available."""
        monkeypatch.delenv("SOLVER_MODEL", raising=False)
        monkeypatch.setenv("VERIFIER_MODEL", "explicit-verifier")
        monkeypatch.setenv("ALLOWED_MODELS", "only-model,explicit-verifier")
        
        from amd_track1.model_roles import get_verifier_model, is_verifier_available, reset_model_cache
        reset_model_cache()
        
        assert get_verifier_model() == "explicit-verifier"
        assert is_verifier_available() is True

    def test_empty_allowed_models_solver_fallback(self, monkeypatch):
        """Empty ALLOWED_MODELS with no env override returns None for solver."""
        monkeypatch.delenv("SOLVER_MODEL", raising=False)
        monkeypatch.delenv("VERIFIER_MODEL", raising=False)
        monkeypatch.setenv("ALLOWED_MODELS", "")
        
        from amd_track1.model_roles import get_solver_model, reset_model_cache
        reset_model_cache()
        
        assert get_solver_model() is None

    def test_no_hardcoded_model_ids(self, monkeypatch):
        """Model IDs must come from env or ALLOWED_MODELS, never hardcoded."""
        monkeypatch.delenv("SOLVER_MODEL", raising=False)
        monkeypatch.delenv("VERIFIER_MODEL", raising=False)
        monkeypatch.delenv("ALLOWED_MODELS", raising=False)
        
        from amd_track1.model_roles import get_solver_model, get_verifier_model, reset_model_cache
        reset_model_cache()
        
        assert get_solver_model() is None
        assert get_verifier_model() is None

    def test_model_ids_from_allowed_models_not_hardcoded(self, monkeypatch):
        """Verify model selection uses ALLOWED_MODELS config, not hardcoded strings."""
        monkeypatch.delenv("SOLVER_MODEL", raising=False)
        monkeypatch.delenv("VERIFIER_MODEL", raising=False)
        
        # Test with custom model names that wouldn't be hardcoded
        custom_models = "custom-solver-xyz,custom-verifier-abc,custom-fallback-pqr"
        monkeypatch.setenv("ALLOWED_MODELS", custom_models)
        
        from amd_track1.model_roles import get_solver_model, get_verifier_model, reset_model_cache
        reset_model_cache()
        
        assert get_solver_model() == "custom-solver-xyz"
        assert get_verifier_model() == "custom-fallback-pqr"
