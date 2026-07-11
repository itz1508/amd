param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: run-benchmarks.ps1"
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -m amd_track1.benchmarking.cli smoke
exit $LASTEXITCODE
