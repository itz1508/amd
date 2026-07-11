param(
    [Parameter(Mandatory=$true)][string]$Baseline,
    [Parameter(Mandatory=$true)][string]$Candidate,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: compare-benchmarks.ps1 -Baseline <path> -Candidate <path>"
    Write-Host "Compares two benchmark run records."
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -m amd_track1.benchmarking.cli compare $Baseline $Candidate
exit $LASTEXITCODE