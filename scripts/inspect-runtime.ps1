param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: inspect-runtime.ps1"
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -c "import amd_track1.entrypoint as entry; import json; print(json.dumps({'entrypoint': entry.__name__}, indent=2))"
exit $LASTEXITCODE
