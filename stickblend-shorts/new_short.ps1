<#
.SYNOPSIS
Scaffold a new stickblend 2.5D + Remotion short project in <repo_root>\<Slug>.
Usage:
  .\stickblend-shorts\new_short.ps1 -Slug my-short
#>
param(
  [Parameter(Mandatory = $true)][string]$Slug
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Target = Join-Path $RepoRoot $Slug
$Template = Join-Path $PSScriptRoot "templates\short"

if (Test-Path $Target) {
  throw "Target directory already exists: $Target"
}

Copy-Item -Path $Template -Destination $Target -Recurse
Write-Host "Created new stickblend short project at: $Target"
Write-Host "Next steps:"
Write-Host "  1. Edit $Slug\STORY.md and $Slug\script.json"
Write-Host "  2. Run: python $Slug\scripts\voice_gemini.py"
Write-Host "  3. Edit $Slug\blender\shots.py and preview: .\$Slug\blender\stills_all.ps1"
Write-Host "  4. Render clips: .\$Slug\blender\render_all.ps1 -Slug $Slug"
