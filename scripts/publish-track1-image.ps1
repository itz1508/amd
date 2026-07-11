param(
    [Parameter(Mandatory=$true)][string]$Tag,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: publish-track1-image.ps1 -Tag <tag>"
    Write-Host "Publishes the Track 1 Docker image to registry."
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

docker push $Tag
exit $LASTEXITCODE