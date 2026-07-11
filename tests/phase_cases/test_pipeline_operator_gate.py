"""Pipeline operator-gate behavior tests."""
import json
from pathlib import Path

from backend.cli import run_pipeline


def test_pipeline_stops_at_operator_gate_without_placeholder_execution(tmp_path):
    """Full pipeline must stop when gap evaluation needs operator evidence."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    (target / "example.py").write_text("print('ok')\n", encoding="utf-8")

    output_root = tmp_path / "out"
    exit_code = run_pipeline(str(target), str(output_root))

    assert exit_code == 0
    assert (output_root / "01_snapshot.json").exists()
    assert (output_root / "02_scan.json").exists()
    assert (output_root / "03_analysis_classification.json").exists()
    assert (output_root / "04_statement_output.json").exists()
    assert (output_root / "05_gap_evaluation.json").exists()

    stop_path = output_root / "06_final_handoff.json"
    assert stop_path.exists()
    stop = json.loads(stop_path.read_text(encoding="utf-8"))
    assert stop["phase"] == "final_handoff"
    assert stop["status"] == "operator_action_required"
    assert stop["terminal_state"] == "operator_action_required"
    assert stop["presimulation_gate"]["passed"] is False
    assert "presimulation" in stop["blocked_phases"]
    assert "execution" in stop["blocked_phases"]
    assert stop["three_statement_chain"]["dossier_statement_id"]
    assert stop["three_statement_chain"]["handoff_statement_id"]
    assert stop["three_statement_chain"]["llm_statement_id"]

    assert not (output_root / "06_simulation_environment.json").exists()
    assert not (output_root / "07_inspection.json").exists()
    assert not (output_root / "08_final_result.json").exists()
    assert not (output_root / "09_cleanup.json").exists()
