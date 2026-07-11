param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: run-track1-tests.ps1"
    Write-Host "Runs all Track 1 tests."
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -m pytest tests/ -v --tb=short
exit $LASTEXITCODE