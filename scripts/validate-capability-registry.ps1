param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: validate-capability-registry.ps1"
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -c "from amd_track1.capabilities import validate_registry; import json; print(json.dumps(validate_registry(), indent=2))"
exit $LASTEXITCODE
