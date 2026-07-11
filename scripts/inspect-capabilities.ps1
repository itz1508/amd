param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: inspect-capabilities.ps1"
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -c "from amd_track1.capabilities import list_capabilities; import json; print(json.dumps(list_capabilities(), indent=2))"
exit $LASTEXITCODE
