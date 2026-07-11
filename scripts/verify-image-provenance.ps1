param(
    [Parameter(Mandatory=$true)][string]$Image,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: verify-image-provenance.ps1 -Image <image>"
    Write-Host "Verifies Docker image provenance (size, layers, creation date)."
    exit 0
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not ($repo.Path -match 'D:\\Dev\\amd$')) {
    Write-Error "Repository authority mismatch"
    exit 2
}

docker inspect $Image --format 'Image: {{.Id}} Size: {{.Size}} Layers: {{len .RootFS.Layers}} Created: {{.Created}}'
exit $LASTEXITCODE