"""Independent contract checks for the AMD Track 1 authority manifest."""

import json
from pathlib import Path


AMD_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = AMD_ROOT / "source_of_truth.json"

REQUIRED_ROOT_FIELDS = {
    "schema_version",
    "system",
    "canonical_repository",
    "canonical_package",
    "public_interface",
    "owned_components",
    "allowed_consumers",
    "prohibited_duplicate_owners",
    "prohibited_private_imports",
}
REQUIRED_PUBLIC_INTERFACE_FIELDS = {
    "type",
    "command",
    "python_executable",
    "pythonpath_required",
    "arguments",
    "required_environment_variables",
    "input_schema_version",
    "output_schema_version",
    "supported_exit_codes",
}
REQUIRED_ENVIRONMENT_VARIABLES = {
    "FIREWORKS_API_KEY",
    "FIREWORKS_BASE_URL",
    "ALLOWED_MODELS",
}
REQUIRED_PRIVATE_MODULES = {
    "amd_track1.executor",
    "amd_track1.router",
    "amd_track1.verifier",
    "amd_track1.validators",
    "amd_track1.model_roles",
    "amd_track1.client",
    "amd_track1.classifier",
}


def _load_manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"Missing manifest: {MANIFEST_PATH}"
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_source_of_truth_manifest_contract() -> None:
    """The manifest identifies AMD ownership and its only public boundary."""
    manifest = _load_manifest()

    assert REQUIRED_ROOT_FIELDS <= manifest.keys()
    assert manifest["schema_version"] == "1.0"
    assert manifest["system"] == "amd_track1"
    assert manifest["canonical_repository"] == r"D:\Dev\amd"
    assert manifest["canonical_package"] == "amd_track1"
    assert manifest["allowed_consumers"] == []
    assert r"D:\Dev\Edge" in manifest["prohibited_duplicate_owners"]

    public_interface = manifest["public_interface"]
    assert REQUIRED_PUBLIC_INTERFACE_FIELDS <= public_interface.keys()
    assert public_interface["type"] == "cli"
    assert public_interface["command"] == "python -m amd_track1.entrypoint"
    assert public_interface["pythonpath_required"] == r"D:\Dev\amd"
    assert public_interface["input_schema_version"] == "1.0"
    assert public_interface["output_schema_version"] == "1.0"
    assert set(public_interface["required_environment_variables"]) == (
        REQUIRED_ENVIRONMENT_VARIABLES
    )
    assert public_interface["supported_exit_codes"] == {
        "0": "success",
        "nonzero": "failure",
    }

    owned_components = manifest["owned_components"]
    assert owned_components
    assert len(owned_components) == len(set(owned_components))
    assert all(isinstance(item, str) and item for item in owned_components)
    assert REQUIRED_PRIVATE_MODULES <= set(manifest["prohibited_private_imports"])
