<#
.SYNOPSIS
Render preview stills for all (or selected) scenes in Blender 5.2 (50% res, 6 spp).
Usage:
  .\blender\stills_all.ps1
  .\blender\stills_all.ps1 -Scenes hook,cta
#>
param(
  [string[]]$Scenes,
  [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
  [string]$Preset = "preview"
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$TimelinePath = Join-Path $ProjectDir "timeline.json"

if (-not $Scenes -or $Scenes.Count -eq 0) {
  $tl = Get-Content $TimelinePath -Raw -Encoding UTF8 | ConvertFrom-Json
  $Scenes = $tl.lines | ForEach-Object { $_.id }
}

foreach ($sid in $Scenes) {
  $n = [int](python -c "import json; t=json.load(open(r'$TimelinePath', encoding='utf8')); l=[x for x in t['lines'] if x['id']=='$sid'][0]; print(max(1, round(l['end']*30)-round(l['start']*30)))")
  $mid = [Math]::Max(1, [int]($n / 2))
  Write-Host "=== Still $sid (frame $mid / $n) ==="
  & $Blender -b --factory-startup -P (Join-Path $PSScriptRoot "run.py") -- $sid $Preset "still:$mid" 2>&1 |
    Select-String -Pattern "Error|Traceback|SCENE_OK"
}
