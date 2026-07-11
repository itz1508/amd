param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: detect-dead-code.ps1"
    Write-Host "Scans for unreachable imports and unused modules."
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -c "from amd_track1.capabilities.validation import validate_registry; import json; errors = validate_registry(); dead = [e for e in errors if 'unreachable' in e.lower()]; print(json.dumps({'unreachable': dead}, indent=2))"
exit $LASTEXITCODE