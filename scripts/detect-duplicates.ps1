param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: detect-duplicates.ps1"
    Write-Host "Scans capability definitions for duplicate IDs."
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -c "from amd_track1.capabilities.validation import validate_registry; import json; errors = validate_registry(); dup = [e for e in errors if 'duplicate' in e.lower()]; print(json.dumps({'duplicates': dup}, indent=2))"
exit $LASTEXITCODE