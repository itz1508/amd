param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: inspect-skills.ps1"
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$skillPath = Join-Path $repo.Path '.agents/skills/amd-track1'
Get-ChildItem -Path $skillPath -Recurse | Select-Object FullName, PSIsContainer | ConvertTo-Json -Depth 3
