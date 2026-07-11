param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: validate-skill-tree.ps1"
    Write-Host "Validates the progressive-disclosure skill tree integrity."
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$skillFile = Join-Path $repo.Path '.agents/skills/amd-track1/SKILL.md'
$subskillsDir = Join-Path $repo.Path '.agents/skills/amd-track1/subskills'

if (-not (Test-Path $skillFile)) {
    Write-Error "Parent skill file not found: $skillFile"
    exit 1
}

if (-not (Test-Path $subskillsDir)) {
    Write-Error "Subskills directory not found: $subskillsDir"
    exit 1
}

$subskillCount = (Get-ChildItem $subskillsDir -Filter '*.md' -File | Measure-Object).Count
Write-Host "Parent skill: OK"
Write-Host "Subskills count: $subskillCount"
exit 0