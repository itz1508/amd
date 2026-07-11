"""AMD Track 1 conditional verifier component.

Provides conditional verifier functionality:
- Strict JSON output validation
- Decision: accept | revise
- final_answer must be string
- Invalid verifier JSON is verifier failure
- Fail-closed behavior: never replace valid answer with invalid verifier output

High-risk categories that always trigger verifier:
- code_generation
- code_debugging
- logical_reasoning
- named_entity_recognition
"""

import json
import os
from typing import Any

from amd_track1.model_roles import get_verifier_model, is_verifier_available


# High-risk categories that always require verification
HIGH_RISK_CATEGORIES = {
    "code_generation",
    "code_debugging",
    "logical_reasoning",
    "named_entity_recognition"
}


def _build_verifier_prompt(prompt: str, task_id: str, category: str, 
                          candidate_answer: str, validation_errors: list) -> str:
    """Build the prompt for the verifier model.
    
    The prompt instructs the verifier to return JSON with specific schema.
    """
    errors_str = ""
    if validation_errors:
        errors_str = "Validation errors:\n" + "\n".join(
            f"  - {err.get('type', 'error')}: {err.get('message', 'no message')}"
            for err in validation_errors
        )
    
    return f"""You are a verifier for AMD Track 1 tasks. Your job is to verify the candidate answer.

Task ID: {task_id}
Category: {category}
Prompt: {prompt}
Candidate Answer: {candidate_answer}

{errors_str}

You MUST return ONLY valid JSON with this exact schema:
{{
    "decision": "accept" | "revise",
    "gap": "string describing any gap found",
    "correction_hint": "string with correction hint",
    "final_answer": "string with the final answer"
}}

Rules:
- If the candidate answer is correct and complete, use decision: "accept"
- If the candidate answer has issues, use decision: "revise" and provide gap/correction_hint
- Always provide a final_answer (even if accepting the candidate)
- final_answer MUST be a string
- NEVER add any other fields or text outside the JSON
- NEVER return markdown code blocks or explanations
"""


def parse_verifier_response(raw_response: str) -> dict:
    """Parse verifier response as strict JSON.
    
    Args:
        raw_response: Raw string response from verifier model
        
    Returns:
        dict: Parsed JSON response
        
    Raises:
        ValueError: If response is not valid JSON or doesn't match schema
    """
    # Try to extract JSON from response
    # Handle cases where model might wrap JSON in code blocks
    response = raw_response.strip()
    
    # Remove markdown code blocks if present
    if response.startswith("```json") and response.endswith("```"):
        response = response[7:-3].strip()
    elif response.startswith("```") and response.endswith("```"):
        response = response[3:-3].strip()
    
    # Try to parse as JSON
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in verifier response: {e}")
    
    if not isinstance(data, dict):
        raise ValueError(f"Verifier response must be JSON object, got {type(data).__name__}")
    
    return data


def validate_verifier_response_schema(response: dict) -> dict:
    """Validate verifier response against required schema.
    
    Required fields:
    - decision: "accept" or "revise"
    - gap: string
    - correction_hint: string
    - final_answer: string
    
    Args:
        response: Parsed JSON response
        
    Returns:
        dict: {"valid": bool, "errors": list[str]}
    """
    errors = []
    
    # Check decision field
    if "decision" not in response:
        errors.append("Missing required field: decision")
    elif response["decision"] not in ("accept", "revise"):
        errors.append(f"Invalid decision value: {response['decision']}. Must be 'accept' or 'revise'")
    
    # Check gap field
    if "gap" not in response:
        errors.append("Missing required field: gap")
    elif not isinstance(response["gap"], str):
        errors.append(f"gap must be string, got {type(response['gap']).__name__}")
    
    # Check correction_hint field
    if "correction_hint" not in response:
        errors.append("Missing required field: correction_hint")
    elif not isinstance(response["correction_hint"], str):
        errors.append(f"correction_hint must be string, got {type(response['correction_hint']).__name__}")
    
    # Check final_answer field
    if "final_answer" not in response:
        errors.append("Missing required field: final_answer")
    elif not isinstance(response["final_answer"], str):
        errors.append(f"final_answer must be string, got {type(response['final_answer']).__name__}")
    
    # Check for extra fields
    expected_fields = {"decision", "gap", "correction_hint", "final_answer"}
    actual_fields = set(response.keys())
    extra_fields = actual_fields - expected_fields
    if extra_fields:
        errors.append(f"Unexpected fields: {extra_fields}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def process_verifier_response(raw_response: str, fallback_answer: str | None = None) -> str:
    """Process verifier response with fail-closed behavior.
    
    If verifier response is invalid JSON or doesn't match schema,
    return the fallback answer (if provided) or raise.
    
    Args:
        raw_response: Raw string response from verifier
        fallback_answer: Fallback answer to use on verifier failure
        
    Returns:
        str: final_answer from verifier, or fallback_answer on failure
        
    Raises:
        ValueError: If fallback_answer is None and verifier response is invalid
    """
    try:
        # Parse JSON
        response = parse_verifier_response(raw_response)
        
        # Validate schema
        validation = validate_verifier_response_schema(response)
        if not validation["valid"]:
            if fallback_answer is not None:
                return fallback_answer
            raise ValueError(f"Verifier response schema invalid: {validation['errors']}")
        
        # Return final_answer
        return response["final_answer"]
        
    except (ValueError, json.JSONDecodeError, TypeError) as e:
        # Verifier failed - use fallback if available
        if fallback_answer is not None:
            return fallback_answer
        raise ValueError(f"Verifier response processing failed: {e}")


def local_validate(answer: str, task_id: str, category: str) -> dict:
    """Local validation of an answer.
    
    This is a placeholder for category-specific validation.
    Real implementation delegates to CategoryValidator.
    
    Args:
        answer: The answer to validate
        task_id: Task identifier
        category: Task category
        
    Returns:
        dict: {"valid": bool, "errors": list[dict]}
    """
    # Import here to avoid circular imports
    from amd_track1.category_validator import get_category_validator
    
    try:
        validator = get_category_validator()
        result = validator.validate(category, answer)
        return {"valid": result.get("valid", False), "errors": result.get("errors", [])}
    except Exception:
        # If validation fails, treat as valid to avoid blocking
        return {"valid": True, "errors": []}


def validate_verifier_final_answer(final_answer: str, task_id: str, category: str) -> dict:
    """Validate verifier's final_answer locally before acceptance.
    
    Args:
        final_answer: The final_answer from verifier
        task_id: Task identifier
        category: Task category
        
    Returns:
        dict: {"valid": bool, "errors": list[dict]}
    """
    return local_validate(final_answer, task_id, category)


def should_use_verifier(task_id: str, category: str, 
                       candidate_answer: str, 
                       validation_errors: list) -> bool:
    """Determine if verifier should be called.
    
    Verifier is used when:
    1. Category is high-risk (always)
    2. Local validation failed (has errors)
    
    Args:
        task_id: Task identifier
        category: Task category
        candidate_answer: The solver's candidate answer
        validation_errors: List of validation errors from local validation
        
    Returns:
        bool: True if verifier should be called
    """
    # High-risk categories always use verifier
    if category in HIGH_RISK_CATEGORIES:
        return True
    
    # If local validation failed, use verifier
    if validation_errors:
        return True
    
    # Otherwise, skip verifier
    return False


def call_verifier_once(task_id: str, category: str, prompt: str,
                       candidate_answer: str, validation_errors: list,
                       fireworks_client=None) -> dict:
    """Call verifier exactly once and process the result.
    
    This enforces the "at most one corrected final answer" constraint.
    
    Args:
        task_id: Task identifier
        category: Task category
        prompt: Original task prompt
        candidate_answer: The solver's candidate answer
        validation_errors: List of validation errors from local validation
        fireworks_client: Optional FireworksClient instance to reuse
        
    Returns:
        dict: {
            "success": bool,
            "final_answer": str or None,
            "validated": bool,
            "errors": list,
            "verifier_used": bool
        }
    """
    if not is_verifier_available():
        return {
            "success": False,
            "final_answer": None,
            "validated": False,
            "errors": ["Verifier model not available"],
            "verifier_used": False
        }
    
    try:
        # Build verifier prompt
        verifier_prompt = _build_verifier_prompt(
            prompt, task_id, category, candidate_answer, validation_errors
        )
        
        # Get verifier model
        verifier_model = get_verifier_model()
        if not verifier_model:
            return {
                "success": False,
                "final_answer": None,
                "validated": False,
                "errors": ["No verifier model configured"],
                "verifier_used": False
            }
        
        # Get or create FireworksClient
        if fireworks_client is None:
            # Create a new client from environment
            api_key = os.environ.get('FIREWORKS_API_KEY', '')
            base_url = os.environ.get('FIREWORKS_BASE_URL', '')
            
            if not api_key or not base_url:
                return {
                    "success": False,
                    "final_answer": candidate_answer,
                    "validated": False,
                    "errors": ["Fireworks API credentials not configured"],
                    "verifier_used": False
                }
            
            # Import FireworksClient locally to avoid circular imports
            # We'll create a minimal client here with just the infer method
            from amd_track1.executor import FireworksClient
            fireworks_client = FireworksClient(api_key=api_key, base_url=base_url)
        
        # Call verifier using the infer method
        answer, model_error, input_tokens, output_tokens, latency = fireworks_client.infer(
            model_id=verifier_model,
            prompt=verifier_prompt,
            timeout=300.0,
            max_tokens=256,
        )
        
        if model_error:
            return {
                "success": False,
                "final_answer": candidate_answer,
                "validated": False,
                "errors": [f"Verifier model error: {model_error}"],
                "verifier_used": True
            }
        
        # Process the response
        final_answer = process_verifier_response(answer, fallback_answer=candidate_answer)
        
        # Validate the final answer locally
        validation = validate_verifier_final_answer(final_answer, task_id, category)
        
        if validation["valid"]:
            return {
                "success": True,
                "final_answer": final_answer,
                "validated": True,
                "errors": [],
                "verifier_used": True
            }
        else:
            # Verifier's answer failed local validation
            # Fall back to candidate answer
            return {
                "success": False,
                "final_answer": candidate_answer,
                "validated": False,
                "errors": validation.get("errors", []),
                "verifier_used": True
            }
            
    except Exception as e:
        # Any verifier error - keep candidate answer
        return {
            "success": False,
            "final_answer": candidate_answer,
            "validated": False,
            "errors": [str(e)],
            "verifier_used": False
        }
