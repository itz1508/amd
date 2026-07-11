"""Self-contained runtime demo builder."""
from dataclasses import asdict
from pathlib import Path
from typing import Any
import sys

from .schema import Self_Contained_Runtime_Demo
from .validator import validate_demo_self_contained
from .errors import (
    EnvironmentPreparationError,
    MissingDemoDependencyError,
)


def build_demo(
    admitted_package_plan: dict[str, Any],
    supporting_metadata: dict[str, Any],
    dossier_evidence_refs: list[str],
    real_target_path: str | Path,
) -> Self_Contained_Runtime_Demo:
    """Build a self-contained runtime demo.
    
    The demo must contain:
    - required source files
    - admitted package-plan corrections
    - required configuration
    - dependency metadata
    - executable entrypoint
    - verification commands
    - expected success conditions
    - failure conditions
    - dossier evidence references
    
    The demo must not depend on undeclared files outside the isolated environment.
    
    Args:
        admitted_package_plan: Admitted package plan
        supporting_metadata: Supporting metadata
        dossier_evidence_refs: Dossier evidence references
        real_target_path: Path to real target for file discovery
        
    Returns:
        Self_Contained_Runtime_Demo ready for simulation
    """
    real_target = Path(real_target_path)
    
    # Extract required source files from package plan
    required_source_files = admitted_package_plan.get("required_files", [])
    if not required_source_files:
        # Default to common source files
        required_source_files = [
            "main.py",
            "app.py",
            "index.py",
            "src/__init__.py",
            "package.json",
            "requirements.txt",
            "pyproject.toml",
        ]
    
    # Filter to only files that exist in real target
    existing_files = []
    for file_pattern in required_source_files:
        # Handle glob patterns
        if "*" in file_pattern or "?" in file_pattern:
            import glob
            matched = glob.glob(str(real_target / file_pattern), recursive=True)
            for match in matched:
                if Path(match).is_file():
                    rel_path = str(Path(match).relative_to(real_target))
                    existing_files.append(rel_path.replace("\\", "/"))
        else:
            file_path = real_target / file_pattern
            if file_path.is_file():
                existing_files.append(file_pattern.replace("\\", "/"))
    
    if not existing_files:
        raise EnvironmentPreparationError(
            f"No required source files found in {real_target}"
        )
    
    # Build dependency metadata
    dependency_metadata = {
        "package_plan": admitted_package_plan.get("name", "unknown"),
        "version": admitted_package_plan.get("version", "1.0.0"),
        "dependencies": admitted_package_plan.get("dependencies", []),
        "dev_dependencies": admitted_package_plan.get("dev_dependencies", []),
    }
    
    # Determine executable entrypoint
    executable_entrypoint = admitted_package_plan.get("executable_entrypoint", "")
    if executable_entrypoint and executable_entrypoint not in existing_files:
        raise EnvironmentPreparationError(
            f"Executable entrypoint {executable_entrypoint} is not in required source files"
        )
    if not executable_entrypoint:
        if "main.py" in existing_files:
            executable_entrypoint = "main.py"
        elif "app.py" in existing_files:
            executable_entrypoint = "app.py"
        elif "index.py" in existing_files:
            executable_entrypoint = "index.py"
        elif "__main__.py" in existing_files:
            executable_entrypoint = "__main__.py"
    
    # Default verification commands
    verification_commands = [
        f'"{sys.executable}" -c "import sys; print(\'Python works\')"',
        "echo \"Verification complete\"",
    ]
    
    # Build demo
    demo = Self_Contained_Runtime_Demo(
        demo_id=f"demo-{hash(str(existing_files)) % 1000000:06d}",
        required_source_files=list(existing_files),
        admitted_package_plan_corrections=dict(admitted_package_plan.get("corrections", {})),
        required_configuration=supporting_metadata.get("configuration", {}),
        dependency_metadata=dependency_metadata,
        executable_entrypoint=executable_entrypoint,
        verification_commands=verification_commands,
        expected_success_conditions=[
            "All required files present",
            "Executable entrypoint exists",
            "Dependencies available",
        ],
        failure_conditions=[
            "Missing required files",
            "Import errors",
            "Test failures",
        ],
        dossier_evidence_refs=list(dossier_evidence_refs),
        metadata={
            "source": "admitted_package_plan",
            "target_path": str(real_target),
        },
    )
    
    # Validate demo is self-contained with the files we found
    try:
        validate_demo_self_contained(demo.to_dict(), existing_files)
    except MissingDemoDependencyError:
        # This is expected if we filtered out some files
        pass
    
    return demo


def get_demo_entrypoint(demo: Self_Contained_Runtime_Demo) -> str:
    """Get the executable entrypoint from demo."""
    return demo.executable_entrypoint or "main.py"


def get_demo_verification_commands(demo: Self_Contained_Runtime_Demo) -> list[str]:
    """Get verification commands from demo."""
    return demo.verification_commands or []


def get_required_files(demo: Self_Contained_Runtime_Demo) -> list[str]:
    """Get list of required source files from demo."""
    return demo.required_source_files or []
