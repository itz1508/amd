"""AMD Track 1 model role helper.

Provides SOLVER_MODEL and VERIFIER_MODEL selection from environment variables
or ALLOWED_MODELS fallback. Never hardcodes model IDs.

Selection rules:
- SOLVER_MODEL env override takes precedence
- VERIFIER_MODEL env override takes precedence
- Fallback solver = first model in ALLOWED_MODELS
- Fallback verifier = last model in ALLOWED_MODELS
- If only one model exists, verifier unavailable unless VERIFIER_MODEL explicitly set
"""

import os


# Module-level caches for performance
_solver_model = None
_verifier_model = None


def _get_allowed_models() -> list:
    """Get ALLOWED_MODELS from environment, split by comma."""
    allowed = os.environ.get("ALLOWED_MODELS", "")
    return [m.strip() for m in allowed.split(",") if m.strip()] if allowed else []


def get_solver_model() -> str | None:
    """Get solver model ID.
    
    Priority:
    1. SOLVER_MODEL environment variable (must be in ALLOWED_MODELS)
    2. First model in ALLOWED_MODELS
    3. None if no models configured
    
    Returns:
        str: Model ID, or None if not available.
        
    Raises:
        ValueError: If SOLVER_MODEL is set but not in ALLOWED_MODELS.
    """
    global _solver_model
    
    # Get allowed models first
    allowed = _get_allowed_models()
    if not allowed:
        return None
    
    # Check env override first - must be in ALLOWED_MODELS
    env_solver = os.environ.get("SOLVER_MODEL")
    if env_solver:
        if env_solver not in allowed:
            raise ValueError(
                f"SOLVER_MODEL '{env_solver}' is not in ALLOWED_MODELS: {allowed}. "
                f"Model must be explicitly listed in ALLOWED_MODELS."
            )
        _solver_model = env_solver
        return _solver_model
    
    # Fallback to cached value
    if _solver_model is not None:
        return _solver_model
    
    # Get from ALLOWED_MODELS
    _solver_model = allowed[0]
    return _solver_model


def get_verifier_model() -> str | None:
    """Get verifier model ID.
    
    Priority:
    1. VERIFIER_MODEL environment variable (must be in ALLOWED_MODELS)
    2. Last model in ALLOWED_MODELS (if different from solver)
    3. None if not available
    
    Returns:
        str: Model ID, or None if not available.
        
    Raises:
        ValueError: If VERIFIER_MODEL is set but not in ALLOWED_MODELS.
    """
    global _verifier_model
    
    # Get allowed models first
    allowed = _get_allowed_models()
    if not allowed:
        return None
    
    # Check env override first - must be in ALLOWED_MODELS
    env_verifier = os.environ.get("VERIFIER_MODEL")
    if env_verifier:
        if env_verifier not in allowed:
            raise ValueError(
                f"VERIFIER_MODEL '{env_verifier}' is not in ALLOWED_MODELS: {allowed}. "
                f"Model must be explicitly listed in ALLOWED_MODELS."
            )
        _verifier_model = env_verifier
        return _verifier_model
    
    # Fallback to cached value
    if _verifier_model is not None:
        return _verifier_model
    
    # Get from ALLOWED_MODELS
    if len(allowed) > 1:
        _verifier_model = allowed[-1]
        return _verifier_model
    elif len(allowed) == 1:
        # Only one model - verifier not available unless explicitly set via env
        _verifier_model = None
        return None
    
    return None


def is_verifier_available() -> bool:
    """Check if verifier model is available.
    
    Returns:
        bool: True if VERIFIER_MODEL is explicitly set and valid, or different model available.
    """
    # Verifier is available if VERIFIER_MODEL is explicitly set and valid
    env_verifier = os.environ.get("VERIFIER_MODEL")
    if env_verifier:
        allowed = _get_allowed_models()
        return env_verifier in allowed
    
    allowed = _get_allowed_models()
    return len(allowed) > 1


def reset_model_cache():
    """Reset cached model values. Useful for testing."""
    global _solver_model, _verifier_model
    _solver_model = None
    _verifier_model = None
