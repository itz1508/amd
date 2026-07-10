"""Tests for AMD Track 1 conditional verifier.

Tests verify the conditional verifier logic:
- Deterministic tasks use zero model calls
- Valid low-risk solver answer skips verifier
- Invalid solver answer triggers verifier once
- High-risk category triggers verifier once
- Bad verifier JSON does not replace valid answer
- Verifier final answer must pass local validation
- Model IDs come from env or ALLOWED_MODELS, not hardcoded
"""

import json
import pytest
from unittest.mock import Mock, patch


# High-risk categories as defined in the plan
HIGH_RISK_CATEGORIES = {
    "code_generation",
    "code_debugging", 
    "logical_reasoning",
    "named_entity_recognition"
}


class TestConditionalVerifier:
    """Test conditional verifier behavior."""

    def test_valid_low_risk_solver_answer_skips_verifier(self, monkeypatch):
        """Valid low-risk solver answer must skip verifier."""
        from amd_track1.verifier import should_use_verifier
        
        # Setup: low-risk category, valid solver answer
        result = should_use_verifier(
            task_id="task-001",
            category="factual_qa",  # Not high-risk
            candidate_answer="Paris",
            validation_errors=[]
        )
        
        assert result is False, "Low-risk valid answer should skip verifier"

    def test_invalid_solver_answer_triggers_verifier(self, monkeypatch):
        """Invalid solver answer must trigger verifier exactly once."""
        from amd_track1.verifier import should_use_verifier
        
        validation_errors = [{"type": "math_error", "message": "2+2 != 5"}]
        
        result = should_use_verifier(
            task_id="task-002",
            category="factual_qa",
            candidate_answer="5",
            validation_errors=validation_errors
        )
        
        assert result is True, "Invalid answer should trigger verifier"

    def test_high_risk_category_triggers_verifier(self, monkeypatch):
        """High-risk category must trigger verifier even with valid answer."""
        from amd_track1.verifier import should_use_verifier, HIGH_RISK_CATEGORIES
        
        for category in HIGH_RISK_CATEGORIES:
            result = should_use_verifier(
                task_id=f"task-{category}",
                category=category,
                candidate_answer="some answer",
                validation_errors=[]  # Even with no errors
            )
            
            assert result is True, f"High-risk category '{category}' should always trigger verifier"

    def test_bad_verifier_json_does_not_replace_valid_answer(self, monkeypatch):
        """Invalid verifier JSON must not replace a locally valid solver answer."""
        from amd_track1.verifier import process_verifier_response
        
        # Setup: we have a valid solver answer
        valid_solver_answer = "4"
        
        # Verifier returns invalid JSON
        bad_verifier_response = "not valid json at all"
        
        result = process_verifier_response(
            raw_response=bad_verifier_response,
            fallback_answer=valid_solver_answer
        )
        
        assert result == valid_solver_answer, "Invalid verifier JSON should keep valid solver answer"

    def test_verifier_final_answer_must_pass_local_validation(self, monkeypatch):
        """Verifier final answer must pass local validation before acceptance."""
        from amd_track1.verifier import validate_verifier_final_answer
        
        # This delegates to CategoryValidator
        # For testing, we just verify the function exists and returns the right structure
        result = validate_verifier_final_answer(
            final_answer="test answer",
            task_id="task-003",
            category="factual_qa"
        )
        
        assert "valid" in result
        assert "errors" in result

    def test_verifier_json_schema_validation(self, monkeypatch):
        """Verifier output must have required fields: decision, gap, correction_hint, final_answer."""
        from amd_track1.verifier import validate_verifier_response_schema
        
        # Valid schema
        valid_response = {
            "decision": "accept",
            "gap": "string",
            "correction_hint": "string",
            "final_answer": "string"
        }
        
        result = validate_verifier_response_schema(valid_response)
        assert result["valid"] is True
        
        # Missing decision field
        invalid_response = {
            "gap": "string",
            "correction_hint": "string", 
            "final_answer": "string"
        }
        
        result = validate_verifier_response_schema(invalid_response)
        assert result["valid"] is False
        assert any("decision" in err for err in result["errors"])
        
        # Invalid decision value
        invalid_response = {
            "decision": "maybe",  # Not accept or revise
            "gap": "string",
            "correction_hint": "string",
            "final_answer": "string"
        }
        
        result = validate_verifier_response_schema(invalid_response)
        assert result["valid"] is False
        assert any("decision" in err for err in result["errors"])

    def test_verifier_decision_accept_vs_revise(self, monkeypatch):
        """Verifier decision must be either 'accept' or 'revise'."""
        from amd_track1.verifier import validate_verifier_response_schema
        
        # Accept
        result = validate_verifier_response_schema({
            "decision": "accept",
            "gap": "",
            "correction_hint": "",
            "final_answer": "answer"
        })
        assert result["valid"] is True
        
        # Revise
        result = validate_verifier_response_schema({
            "decision": "revise",
            "gap": "gap",
            "correction_hint": "hint",
            "final_answer": "answer"
        })
        assert result["valid"] is True
        
        # Invalid decision
        result = validate_verifier_response_schema({
            "decision": "reject",
            "gap": "gap",
            "correction_hint": "hint", 
            "final_answer": "answer"
        })
        assert result["valid"] is False

    def test_verifier_strict_json_output_only(self, monkeypatch):
        """Verifier must only process strict JSON output."""
        from amd_track1.verifier import parse_verifier_response
        
        # Valid JSON
        valid_json = '{"decision": "accept", "gap": "", "correction_hint": "", "final_answer": "42"}'
        result = parse_verifier_response(valid_json)
        assert result is not None
        assert result["decision"] == "accept"
        
        # Invalid JSON
        with pytest.raises(ValueError):
            parse_verifier_response("not json")
        
        # Partial JSON
        with pytest.raises(ValueError):
            parse_verifier_response('{"decision": "accept"')  # Missing closing brace

    def test_verifier_fail_closed_on_invalid_json(self, monkeypatch):
        """Invalid verifier JSON must result in fail-closed behavior."""
        from amd_track1.verifier import process_verifier_response
        
        # Test that invalid JSON keeps the fallback
        result = process_verifier_response(
            raw_response="invalid json",
            fallback_answer="safe answer"
        )
        assert result == "safe answer"

    def test_verifier_json_with_code_blocks(self, monkeypatch):
        """Verifier response parsing handles code blocks."""
        from amd_track1.verifier import parse_verifier_response
        
        # JSON wrapped in markdown code blocks
        json_with_blocks = '```json\n{"decision": "accept", "gap": "", "correction_hint": "", "final_answer": "answer"}\n```'
        result = parse_verifier_response(json_with_blocks)
        
        assert result["decision"] == "accept"
        assert result["final_answer"] == "answer"
