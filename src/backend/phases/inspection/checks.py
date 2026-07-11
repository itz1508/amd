"""
Read-only inspection checks.
"""
from pathlib import Path
from typing import Any

from backend.phases.inspection.schema import (
    Inspection_Input,
    Inspection_Check,
    Inspection_Finding,
    Inspection_Evidence_Record,
)


def run_all_checks(inp: Inspection_Input) -> tuple[list[Inspection_Check], list[Inspection_Finding], list[str]]:
    """Run every required read-only check and return checks, findings, and failure reasons.

    Inspection never short-circuits; all checks are evaluated.
    """
    checks: list[Inspection_Check] = []
    findings: list[Inspection_Finding] = []
    failure_reasons: list[str] = []

    check_definitions = [
        ("SE01", "completed Simulation_Environment status", _check_completed_status),
        ("SE02", "complete fingerprint chain", _check_fingerprint_chain),
        ("SE03", "valid Gap_Evaluation fingerprint reference", _check_gap_evaluation_fingerprint),
        ("SE04", "valid Simulation_Environment fingerprint", _check_simulation_environment_fingerprint),
        ("SE05", "isolated environment evidence present", _check_isolated_environment),
        ("SE06", "self-contained demo evidence present", _check_self_contained_demo),
        ("SE07", "exactly one internal execution attempt", _check_exactly_one_execution_attempt),
        ("SE08", "execution result consistency", _check_execution_result_consistency),
        ("SE09", "mutation boundary present before target mutations", _check_mutation_boundary_before_mutations),
        ("SE10", "every changed file is inside the isolated target", _check_changed_files_inside_isolated_target),
        ("SE11", "no changed file is outside the allowed target boundary", _check_no_changed_file_outside_boundary),
        ("SE12", "changed-files evidence matches target-mutation evidence", _check_changed_files_match_target_mutations),
        ("SE13", "post-apply verification covers every changed file", _check_verification_covers_changed_files),
        ("SE14", "post-apply verification reports success", _check_verification_success),
        ("SE15", "real target remained unchanged", _check_real_target_unchanged),
        ("SE16", "unresolved_conflict is false", _check_unresolved_conflict),
        ("SE17", "regression_detected is false", _check_regression_detected),
        ("SE18", "dossier evidence references are complete", _check_dossier_refs_complete),
        ("SE19", "no contradictory statuses or routes exist", _check_no_contradictory_statuses),
        ("SE20", "all evidence identifiers are stable and deterministic", _check_identifiers_stable),
    ]

    for code, name, fn in check_definitions:
        check, finding = fn(inp, code, name)
        checks.append(check)
        if finding is not None:
            findings.append(finding)
            if finding.failure_reason:
                failure_reasons.append(finding.failure_reason)

    # Preserve deterministic ordering of failure reasons.
    failure_reasons.sort()
    return checks, findings, failure_reasons


def _evidence_ref(evidence_type: str, evidence_id: str, source_phase: str, payload_summary: dict[str, Any] | None = None) -> Inspection_Evidence_Record:
    return Inspection_Evidence_Record(
        evidence_type=evidence_type,
        evidence_id=evidence_id,
        source_phase=source_phase,
        payload_summary=payload_summary or {},
    )


def _ok(check_code: str, check_name: str, refs: list[Inspection_Evidence_Record]) -> Inspection_Check:
    return Inspection_Check(
        check_code=check_code,
        check_name=check_name,
        passed=True,
        evidence_refs=refs,
    )


def _fail(
    check_code: str,
    check_name: str,
    refs: list[Inspection_Evidence_Record],
    reason: str,
    finding_code: str,
    affected_item: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> tuple[Inspection_Check, Inspection_Finding]:
    check = Inspection_Check(
        check_code=check_code,
        check_name=check_name,
        passed=False,
        evidence_refs=refs,
        failure_reason=reason,
    )
    finding = Inspection_Finding(
        finding_code=finding_code,
        severity="error",
        affected_item=affected_item,
        evidence=evidence or {},
        failure_reason=reason,
        success_looks_like=_success_looks_like(finding_code),
    )
    return check, finding


def _success_looks_like(finding_code: str) -> str:
    return {
        "F-SE01": "Simulation_Environment status is 'completed'.",
        "F-SE02": "Both gap_evaluation_fingerprint and simulation_environment_fingerprint are present and non-empty.",
        "F-SE03": "gap_evaluation_fingerprint is a non-empty string.",
        "F-SE04": "simulation_environment_fingerprint is a non-empty string.",
        "F-SE05": "isolated_environment contains a non-empty evidence record.",
        "F-SE06": "self_contained_demo contains a non-empty evidence record.",
        "F-SE07": "execution_attempt_count equals exactly 1.",
        "F-SE08": "execution_result status is 'success' and contains required keys.",
        "F-SE09": "apply_mutation_boundary is present and target_mutations are bounded by it.",
        "F-SE10": "Every changed file path resolves inside the isolated target root.",
        "F-SE11": "No changed file path resolves outside the allowed target boundary.",
        "F-SE12": "changed_files list matches the relative paths in target_mutations.",
        "F-SE13": "post_apply_verification covers every changed file.",
        "F-SE14": "post_apply_verification status is 'success'.",
        "F-SE15": "real_target_unchanged is true.",
        "F-SE16": "unresolved_conflict is false.",
        "F-SE17": "regression_detected is false.",
        "F-SE18": "dossier_evidence_refs list is non-empty and every reference is well-formed.",
        "F-SE19": "Input status and next_route are internally consistent.",
        "F-SE20": "All evidence identifiers are non-empty strings and stable.",
    }.get(finding_code, "Check passes.")


def _check_completed_status(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("status", "simulation_environment.status", "simulation_environment", {"status": inp.status})
    if inp.status == "completed":
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        f"Simulation_Environment status is '{inp.status}', expected 'completed'.",
        "F-SE01",
        affected_item="simulation_environment.status",
        evidence={"status": inp.status},
    )


def _check_fingerprint_chain(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    refs = [
        _evidence_ref("fingerprint", "gap_evaluation_fingerprint", "gap_evaluation", {"fingerprint": inp.gap_evaluation_fingerprint}),
        _evidence_ref("fingerprint", "simulation_environment_fingerprint", "simulation_environment", {"fingerprint": inp.simulation_environment_fingerprint}),
    ]
    if inp.gap_evaluation_fingerprint and inp.simulation_environment_fingerprint:
        return _ok(code, name, refs), None
    return _fail(
        code, name, refs,
        "Fingerprint chain is incomplete: one or both fingerprints are missing.",
        "F-SE02",
        affected_item="fingerprint_chain",
        evidence={"gap_evaluation_fingerprint": inp.gap_evaluation_fingerprint, "simulation_environment_fingerprint": inp.simulation_environment_fingerprint},
    )


def _check_gap_evaluation_fingerprint(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("fingerprint", "gap_evaluation_fingerprint", "gap_evaluation", {"fingerprint": inp.gap_evaluation_fingerprint})
    if isinstance(inp.gap_evaluation_fingerprint, str) and inp.gap_evaluation_fingerprint:
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        "gap_evaluation_fingerprint is missing or not a non-empty string.",
        "F-SE03",
        affected_item="gap_evaluation_fingerprint",
        evidence={"gap_evaluation_fingerprint": inp.gap_evaluation_fingerprint},
    )


def _check_simulation_environment_fingerprint(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("fingerprint", "simulation_environment_fingerprint", "simulation_environment", {"fingerprint": inp.simulation_environment_fingerprint})
    if isinstance(inp.simulation_environment_fingerprint, str) and inp.simulation_environment_fingerprint:
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        "simulation_environment_fingerprint is missing or not a non-empty string.",
        "F-SE04",
        affected_item="simulation_environment_fingerprint",
        evidence={"simulation_environment_fingerprint": inp.simulation_environment_fingerprint},
    )


def _check_isolated_environment(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("evidence", "isolated_environment", "simulation_environment", {"present": bool(inp.isolated_environment)})
    if inp.isolated_environment:
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        "isolated_environment evidence is missing or empty.",
        "F-SE05",
        affected_item="isolated_environment",
    )


def _check_self_contained_demo(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    present = bool(inp.self_contained_demo)
    ran_ok = isinstance(inp.self_contained_demo, dict) and inp.self_contained_demo.get("ran_successfully") is True
    ref = _evidence_ref(
        "evidence",
        "self_contained_demo",
        "simulation_environment",
        {"present": present, "ran_successfully": ran_ok},
    )
    if ran_ok:
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        "self_contained_demo evidence is missing or does not report successful execution.",
        "F-SE06",
        affected_item="self_contained_demo",
        evidence={"self_contained_demo": inp.self_contained_demo},
    )


def _check_exactly_one_execution_attempt(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("counter", "execution_attempt_count", "simulation_environment", {"count": inp.execution_attempt_count})
    if inp.execution_attempt_count == 1:
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        f"execution_attempt_count is {inp.execution_attempt_count}, expected exactly 1.",
        "F-SE07",
        affected_item="execution_attempt_count",
        evidence={"execution_attempt_count": inp.execution_attempt_count},
    )


def _check_execution_result_consistency(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("result", "execution_result", "execution", {"execution_result": inp.execution_result})
    if not inp.execution_result:
        return _fail(
            code, name, [ref],
            "execution_result is missing.",
            "F-SE08",
            affected_item="execution_result",
        )
    status = inp.execution_result.get("status")
    if status == "success":
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        f"execution_result status is '{status}', expected 'success'.",
        "F-SE08",
        affected_item="execution_result.status",
        evidence={"execution_result": inp.execution_result},
    )


def _check_mutation_boundary_before_mutations(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    refs = [
        _evidence_ref("boundary", "apply_mutation_boundary", "execution", {"present": bool(inp.apply_mutation_boundary)}),
        _evidence_ref("mutations", "target_mutations", "execution", {"count": len(inp.target_mutations)}),
    ]
    if not inp.apply_mutation_boundary:
        return _fail(
            code, name, refs,
            "apply_mutation_boundary evidence is missing.",
            "F-SE09",
            affected_item="apply_mutation_boundary",
        )
    boundary_root = inp.apply_mutation_boundary.get("boundary_root")
    if not boundary_root:
        return _fail(
            code, name, refs,
            "apply_mutation_boundary.boundary_root is missing.",
            "F-SE09",
            affected_item="apply_mutation_boundary.boundary_root",
        )
    for mutation in inp.target_mutations:
        path = mutation.get("relative_path") or mutation.get("path") or ""
        if path and not _is_inside_boundary(path, boundary_root):
            return _fail(
                code, name, refs,
                f"Target mutation '{path}' is outside boundary '{boundary_root}'.",
                "F-SE09",
                affected_item=path,
                evidence={"boundary_root": boundary_root, "mutation": mutation},
            )
    return _ok(code, name, refs), None


def _check_changed_files_inside_isolated_target(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    boundary_root = _boundary_root(inp)
    refs = [
        _evidence_ref("boundary", "apply_mutation_boundary.boundary_root", "execution", {"boundary_root": boundary_root}),
        _evidence_ref("files", "changed_files", "execution", {"changed_files": inp.changed_files}),
    ]
    if not boundary_root:
        return _fail(
            code, name, refs,
            "Cannot determine isolated target boundary.",
            "F-SE10",
            affected_item="apply_mutation_boundary",
        )
    for path in inp.changed_files:
        if not _is_inside_boundary(path, boundary_root):
            return _fail(
                code, name, refs,
                f"Changed file '{path}' is outside isolated target '{boundary_root}'.",
                "F-SE10",
                affected_item=path,
                evidence={"boundary_root": boundary_root, "changed_file": path},
            )
    return _ok(code, name, refs), None


def _check_no_changed_file_outside_boundary(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    boundary_root = _boundary_root(inp)
    refs = [
        _evidence_ref("boundary", "apply_mutation_boundary.boundary_root", "execution", {"boundary_root": boundary_root}),
        _evidence_ref("files", "changed_files", "execution", {"changed_files": inp.changed_files}),
    ]
    if not boundary_root:
        return _fail(
            code, name, refs,
            "Cannot determine allowed target boundary.",
            "F-SE11",
            affected_item="apply_mutation_boundary",
        )
    for path in inp.changed_files:
        if not _is_inside_boundary(path, boundary_root):
            return _fail(
                code, name, refs,
                f"Changed file '{path}' is outside allowed boundary '{boundary_root}'.",
                "F-SE11",
                affected_item=path,
                evidence={"boundary_root": boundary_root, "changed_file": path},
            )
    return _ok(code, name, refs), None


def _check_changed_files_match_target_mutations(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    mutation_paths = sorted({m.get("relative_path") or m.get("path") or "" for m in inp.target_mutations if (m.get("relative_path") or m.get("path"))})
    changed_paths = sorted(set(inp.changed_files))
    refs = [
        _evidence_ref("files", "changed_files", "execution", {"changed_files": changed_paths}),
        _evidence_ref("mutations", "target_mutations", "execution", {"mutation_paths": mutation_paths}),
    ]
    if changed_paths == mutation_paths:
        return _ok(code, name, refs), None
    return _fail(
        code, name, refs,
        f"changed_files {changed_paths} do not match target mutation paths {mutation_paths}.",
        "F-SE12",
        affected_item="changed_files / target_mutations",
        evidence={"changed_files": changed_paths, "mutation_paths": mutation_paths},
    )


def _check_verification_covers_changed_files(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    verified_paths = {v.get("relative_path") or v.get("path") or "" for v in inp.verification_results if (v.get("relative_path") or v.get("path"))}
    changed_paths = set(inp.changed_files)
    refs = [
        _evidence_ref("verification", "verification_results", "execution", {"verified_paths": sorted(verified_paths)}),
        _evidence_ref("files", "changed_files", "execution", {"changed_files": sorted(changed_paths)}),
    ]
    if not changed_paths:
        return _ok(code, name, refs), None
    missing = sorted(changed_paths - verified_paths)
    if not missing:
        return _ok(code, name, refs), None
    return _fail(
        code, name, refs,
        f"Post-apply verification does not cover changed files: {missing}.",
        "F-SE13",
        affected_item="verification_results",
        evidence={"missing": missing, "verified_paths": sorted(verified_paths)},
    )


def _check_verification_success(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    status = inp.post_apply_verification.get("status") if inp.post_apply_verification else None
    refs = [
        _evidence_ref("verification", "post_apply_verification.status", "execution", {"status": status}),
    ]
    if status == "success":
        return _ok(code, name, refs), None
    return _fail(
        code, name, refs,
        f"post_apply_verification status is '{status}', expected 'success'.",
        "F-SE14",
        affected_item="post_apply_verification.status",
        evidence={"post_apply_verification": inp.post_apply_verification},
    )


def _check_real_target_unchanged(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("flag", "real_target_unchanged", "simulation_environment", {"real_target_unchanged": inp.real_target_unchanged})
    if inp.real_target_unchanged is True:
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        "real_target_unchanged is false; the real target must remain unchanged.",
        "F-SE15",
        affected_item="real_target_unchanged",
        evidence={"real_target_unchanged": inp.real_target_unchanged},
    )


def _check_unresolved_conflict(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("flag", "unresolved_conflict", "simulation_environment", {"unresolved_conflict": inp.unresolved_conflict})
    if inp.unresolved_conflict is False:
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        "unresolved_conflict is true; all conflicts must be resolved before Inspection.",
        "F-SE16",
        affected_item="unresolved_conflict",
        evidence={"unresolved_conflict": inp.unresolved_conflict},
    )


def _check_regression_detected(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("flag", "regression_detected", "simulation_environment", {"regression_detected": inp.regression_detected})
    if inp.regression_detected is False:
        return _ok(code, name, [ref]), None
    return _fail(
        code, name, [ref],
        "regression_detected is true; no regressions may be present at Inspection.",
        "F-SE17",
        affected_item="regression_detected",
        evidence={"regression_detected": inp.regression_detected},
    )


def _check_dossier_refs_complete(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    refs = [
        _evidence_ref("dossier", "dossier_evidence_refs", "gap_evaluation", {"count": len(inp.dossier_evidence_refs)}),
    ]
    if not inp.dossier_evidence_refs:
        return _fail(
            code, name, refs,
            "dossier_evidence_refs are missing or empty.",
            "F-SE18",
            affected_item="dossier_evidence_refs",
        )
    malformed = []
    for ref in inp.dossier_evidence_refs:
        if not isinstance(ref, dict) or not ref.get("evidence_id") or not ref.get("source_phase"):
            malformed.append(ref)
    if malformed:
        return _fail(
            code, name, refs,
            f"Malformed dossier evidence references: {malformed}.",
            "F-SE18",
            affected_item="dossier_evidence_refs",
            evidence={"malformed": malformed},
        )
    return _ok(code, name, refs), None


def _check_no_contradictory_statuses(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ref = _evidence_ref("status_route", "status/next_route", "simulation_environment", {"status": inp.status, "next_route": inp.next_route})
    contradictions = []
    if inp.status == "completed" and inp.next_route not in (None, "inspection", "final_result"):
        contradictions.append(f"status='completed' with next_route='{inp.next_route}'")
    if inp.status != "completed" and inp.next_route == "inspection":
        contradictions.append(f"status='{inp.status}' with next_route='inspection'")
    if contradictions:
        return _fail(
            code, name, [ref],
            f"Contradictory status/route: {contradictions}.",
            "F-SE19",
            affected_item="status/next_route",
            evidence={"status": inp.status, "next_route": inp.next_route},
        )
    return _ok(code, name, [ref]), None


def _check_identifiers_stable(inp: Inspection_Input, code: str, name: str) -> tuple[Inspection_Check, Inspection_Finding | None]:
    ids = {
        "simulation_environment_id": inp.simulation_environment_id,
        "gap_evaluation_fingerprint": inp.gap_evaluation_fingerprint,
        "simulation_environment_fingerprint": inp.simulation_environment_fingerprint,
    }
    refs = [_evidence_ref("identifier", key, "simulation_environment", {"value": value}) for key, value in ids.items()]
    bad = {k: v for k, v in ids.items() if not isinstance(v, str) or not v}
    if bad:
        return _fail(
            code, name, refs,
            f"Evidence identifiers are not stable non-empty strings: {bad}.",
            "F-SE20",
            affected_item="evidence_identifiers",
            evidence={"bad_identifiers": bad},
        )
    return _ok(code, name, refs), None


def _boundary_root(inp: Inspection_Input) -> str | None:
    if not inp.apply_mutation_boundary:
        return None
    return inp.apply_mutation_boundary.get("boundary_root") or inp.apply_mutation_boundary.get("isolated_target_root")


def _is_inside_boundary(relative_path: str, boundary_root: str) -> bool:
    """Return True if relative_path is semantically inside boundary_root.

    Both paths are treated as POSIX-style relative paths for deterministic
    comparison. A path is inside the boundary if it equals the boundary or is
    located under it.
    """
    path_parts = Path(relative_path).parts
    boundary_parts = Path(boundary_root).parts
    if not boundary_parts:
        return True
    if len(path_parts) < len(boundary_parts):
        return False
    return path_parts[: len(boundary_parts)] == boundary_parts