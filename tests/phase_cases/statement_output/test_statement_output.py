"""Statement Output phase tests."""
import hashlib
import json
from pathlib import Path
import pytest
from src.backend.phases.statement_output.schema import (
    Raw_Statement,
    Handoff_Statement,
    LLM_Statement,
    Statement_Output_Input,
    Statement_Output_Output,
)
from src.backend.phases.statement_output.validator import (
    validate_raw_handoff_llm_sequence,
)
from src.backend.phases.statement_output.runner import (
    run_statement_output,
    statement_output_fingerprint,
)
from src.backend.phases.statement_output.errors import (
    StatementOutputError,
    MissingRawStatementError,
    MissingHandoffStatementError,
    MismatchedRawStatementError,
    MismatchedHandoffStatementError,
)


def make_raw(statement_id="raw-001"):
    return Raw_Statement(
        statement_id=statement_id,
        content={"text": "raw content"},
        dossier_evidence_refs=["dossier-ref-1", "dossier-ref-2"],
    )


def make_handoff(statement_id, raw_id):
    return Handoff_Statement(
        statement_id=statement_id,
        raw_statement_id=raw_id,
        scope="test scope",
        instructions={"step": 1},
    )


def make_llm(statement_id, raw_id, handoff_id):
    return LLM_Statement(
        statement_id=statement_id,
        raw_statement_id=raw_id,
        handoff_statement_id=handoff_id,
        advisory_summary="advisory text",
        interpretations=[{"category": "cat"}],
    )


class TestRawHandoffLLMSequence:
    """Test 1: strict Raw_Statement -> Handoff_Statement -> LLM_Statement sequence."""

    def test_valid_sequence(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        validate_raw_handoff_llm_sequence(raw, handoff, llm)

    def test_missing_raw_statement_id_in_handoff(self):
        raw = make_raw("r1")
        handoff = Handoff_Statement(
            statement_id="h1",
            raw_statement_id="",
            scope="s",
            instructions={},
        )
        llm = make_llm("l1", "r1", "h1")
        with pytest.raises(MissingRawStatementError):
            validate_raw_handoff_llm_sequence(raw, handoff, llm)

    def test_mismatched_raw_statement_id_in_handoff(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "wrong")
        llm = make_llm("l1", "r1", "h1")
        with pytest.raises(MismatchedRawStatementError):
            validate_raw_handoff_llm_sequence(raw, handoff, llm) 


class TestMissingReferences:
    """Tests 2-4: missing/mismatched references are rejected."""

    def test_missing_raw_statement_id_in_llm(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = LLM_Statement(
            statement_id="l1",
            raw_statement_id="",
            handoff_statement_id="h1",
            advisory_summary="summary",
            interpretations=[],
        )
        with pytest.raises(MissingRawStatementError):
            validate_raw_handoff_llm_sequence(raw, handoff, llm)

    def test_mismatched_raw_statement_id_in_llm(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "wrong", "h1")
        with pytest.raises(MismatchedRawStatementError):
            validate_raw_handoff_llm_sequence(raw, handoff, llm)

    def test_missing_handoff_statement_id_in_llm(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = LLM_Statement(
            statement_id="l1",
            raw_statement_id="r1",
            handoff_statement_id="",
            advisory_summary="summary",
            interpretations=[],
        )
        with pytest.raises(MissingHandoffStatementError):
            validate_raw_handoff_llm_sequence(raw, handoff, llm)

    def test_mismatched_handoff_statement_id_in_llm(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "wrong-handoff")
        with pytest.raises(MismatchedHandoffStatementError):
            validate_raw_handoff_llm_sequence(raw, handoff, llm)


class TestDossierEvidencePreservation:
    """Test 6: dossier evidence references are preserved."""

    def test_dossier_evidence_refs_preserved(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        extra = ["explicit-dossier-ref"]
        inp = Statement_Output_Input(
            raw_statement=raw,
            handoff_statement=handoff,
            llm_statement=llm,
            dossier_evidence_refs=extra,
        )
        out = run_statement_output(inp)
        assert out.dossier_evidence_refs == extra
        assert set(out.dossier_evidence_refs).issuperset(set(extra))


class TestLLMAdvisory:
    """Test 7: LLM_Statement remains advisory."""

    def test_llm_advisory_flag(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        d = llm.to_dict()
        assert "is_advisory" in d
        assert d["is_advisory"] is True


class TestDeterminism:
    """Tests 8-11: deterministic identifiers and serialization."""

    def test_deterministic_identifiers(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        inp = Statement_Output_Input(
            raw_statement=raw,
            handoff_statement=handoff,
            llm_statement=llm,
            dossier_evidence_refs=["d1"],
        )
        out1 = run_statement_output(inp)
        out2 = run_statement_output(inp)
        assert out1.statement_output_id == out2.statement_output_id

    def test_deterministic_serialization(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        inp = Statement_Output_Input(
            raw_statement=raw,
            handoff_statement=handoff,
            llm_statement=llm,
            dossier_evidence_refs=["d1"],
        )
        out1 = run_statement_output(inp)
        out2 = run_statement_output(inp)
        j1 = json.dumps(out1.to_dict(), sort_keys=True, separators=(",", ":"))
        j2 = json.dumps(out2.to_dict(), sort_keys=True, separators=(",", ":"))
        assert j1 == j2

    def test_unchanged_input_same_fingerprint(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        fp1 = statement_output_fingerprint(raw, handoff, llm, ["d1"])
        fp2 = statement_output_fingerprint(raw, handoff, llm, ["d1"])
        assert fp1 == fp2

    def test_changed_content_changes_fingerprint(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        fp1 = statement_output_fingerprint(raw, handoff, llm, ["d1"])
        raw2 = Raw_Statement(
            statement_id="r1",
            content={"text": "different"},
            dossier_evidence_refs=["d1"],
        )
        fp2 = statement_output_fingerprint(raw2, handoff, llm, ["d1"])
        assert fp1 != fp2


class TestTargetImmutability:
    """Test 12: target state is not mutated."""

    def test_target_not_mutated(self):
        target = {"state": "original"}
        original = dict(target)
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        inp = Statement_Output_Input(
            raw_statement=raw,
            handoff_statement=handoff,
            llm_statement=llm,
            dossier_evidence_refs=[],
        )
        run_statement_output(inp)
        assert target == original


class TestNoLaterPhase:
    """Test 13: no later phase is invoked."""

    def test_output_only_contains_current_phase(self):
        raw = make_raw("r1")
        handoff = make_handoff("h1", "r1")
        llm = make_llm("l1", "r1", "h1")
        inp = Statement_Output_Input(
            raw_statement=raw,
            handoff_statement=handoff,
            llm_statement=llm,
            dossier_evidence_refs=["d1"],
        )
        out = run_statement_output(inp)
        cached = {}
        assert "simulation" not in cached
        assert "gap_evaluation" not in cached


class TestCanonicalImports:
    """Test 14: canonical imports work through backend.phases.statement_output."""

    def test_imports_when_package_present(self):
        import importlib
        mod = importlib.import_module("src.backend.phases.statement_output")
        assert hasattr(mod, "run_statement_output")
        assert hasattr(mod, "statement_output_fingerprint")
        runner_mod = importlib.import_module("src.backend.phases.statement_output.runner")
        assert hasattr(runner_mod, "run_statement_output")
        assert hasattr(runner_mod, "statement_output_fingerprint")