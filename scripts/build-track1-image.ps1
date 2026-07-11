param(
    [string]$Tag = "amd-track1:latest",
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: build-track1-image.ps1 [-Tag <tag>]"
    Write-Host "Builds the Track 1 Docker image."
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

$dockerfile = Join-Path $repo.Path 'amd_track1/Dockerfile'
docker build -t $Tag -f $dockerfile $repo.Path
exit $LASTEXITCODE