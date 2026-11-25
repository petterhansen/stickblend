<#
.SYNOPSIS
Scaffold a new stickblend 2.5D + Remotion short project in <repo_root>\<Slug>.
Usage:
  .\stickblend-shorts\new_short.ps1 -Slug my-short                    # Szenen mit Schnitten (templates/short)
  .\stickblend-shorts\new_short.ps1 -Slug my-short -Template onetake  # ein durchgehender Kameraflug (templates/onetake)
#>
param(
  [Parameter(Mandatory = $true)][string]$Slug,
  [ValidateSet("short", "onetake")][string]$Template = "short"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Target = Join-Path $RepoRoot $Slug
$TemplateDir = Join-Path $PSScriptRoot "templates\$Template"

if (Test-Path $Target) {
  throw "Target directory already exists: $Target"
}

Copy-Item -Path $TemplateDir -Destination $Target -Recurse
Write-Host "Created new stickblend short project at: $Target"
if ($Template -eq "onetake") {
  Write-Host "Next steps (one-take):"
  Write-Host "  1. Edit $Slug\STORY.md and $Slug\script.json (hook = mid-action, 30-55 s)"
  Write-Host "  2. python $Slug\scriptsake_timeline.py   (or voice_gemini.py for the real voice)"
  Write-Host "  3. Edit $Sluglender\shots.py (see examplesufzug), preview: .\$Sluglenderender_all.ps1 -Preset preview -Spp 4"
  Write-Host "  4. Final: .\$Sluglenderender_all.ps1 ; then cd $Slug ; npm install ; npx remotion render src/index.ts Short out/short.mp4"
  return
}
Write-Host "Next steps:"
Write-Host "  1. Edit $Slug\STORY.md and $Slug\script.json"
Write-Host "  2. Run: python $Slug\scripts\voice_gemini.py"
Write-Host "  3. Edit $Slug\blender\shots.py and preview: .\$Slug\blender\stills_all.ps1"
Write-Host "  4. Render clips: .\$Slug\blender\render_all.ps1 -Slug $Slug"
