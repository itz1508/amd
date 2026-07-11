param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: inspect-dependencies.ps1"
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$python = Join-Path $repo.Path '.venv/Scripts/python.exe'
& $python -c "import importlib.util, json; mods=['amd_track1.entrypoint','amd_track1.router','amd_track1.executor','amd_track1.classifier']; print(json.dumps([{'module':m,'available':importlib.util.find_spec(m) is not None} for m in mods], indent=2))"
exit $LASTEXITCODE
