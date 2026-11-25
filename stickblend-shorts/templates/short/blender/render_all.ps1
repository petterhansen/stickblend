<#
.SYNOPSIS
Render all (or selected) scenes in Blender 5.2 in parallel, encode to MP4, and sync to Remotion public/shorts/<slug>/.
Resumable: frames that already exist are skipped (run.py RESUME=1). A stamp (hash of timeline.json, blender/*.py,
preset, SPP, PCT, FMT) per scene detects stale frames; only then are they deleted. -Clean forces a full re-render.
Each scene logs to out/bl/<scene>.log and is retried once if Blender crashes (e.g. GPU driver reset).
Usage:
  .\blender\render_all.ps1 -Slug my-short
  .\blender\render_all.ps1 -Slug my-short -Spp 6 -Pct 75 -Jobs 2 -SkipExisting
#>
param(
  [Parameter(Mandatory = $true)][string]$Slug,
  [string[]]$Scenes,
  [int]$Spp = 6,
  [int]$Pct = 75,
  [int]$Jobs = 2,
  [string]$Fmt = "JPEG",
  [double]$ShadowDist = 18,
  [switch]$SkipExisting,
  [switch]$Clean,
  [string]$Preset = "final",
  [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $ProjectDir
$TimelinePath = Join-Path $ProjectDir "timeline.json"
$PublicDir = Join-Path $RepoRoot "remotion\public\shorts\$Slug"
$BlOutDir = Join-Path $PublicDir "bl"
$RunPy = Join-Path $PSScriptRoot "run.py"

New-Item -ItemType Directory -Force -Path $BlOutDir | Out-Null

if (-not $Scenes -or $Scenes.Count -eq 0) {
  $tl = Get-Content $TimelinePath -Raw -Encoding UTF8 | ConvertFrom-Json
  $Scenes = $tl.lines | ForEach-Object { $_.id }
}

if ($SkipExisting) {
  $Scenes = $Scenes | Where-Object {
    $mp4 = Join-Path $BlOutDir "$_.mp4"
    -not ((Test-Path $mp4) -and (Get-Item $mp4).Length -gt 10000)
  }
}

# Stamp: stale frames from an older timeline/scene code are deleted, valid ones are resumed
$hashSrc = @($TimelinePath) + (Get-ChildItem (Join-Path $PSScriptRoot "*.py") | ForEach-Object { $_.FullName })
$sha = [System.Security.Cryptography.SHA1]::Create()
$bytes = [System.Collections.Generic.List[byte]]::new()
foreach ($f in $hashSrc) { if (Test-Path $f) { $bytes.AddRange([System.IO.File]::ReadAllBytes($f)) } }
$Stamp = ([BitConverter]::ToString($sha.ComputeHash($bytes.ToArray())) -replace "-", "").Substring(0, 12) + "-$Preset-$Spp-$Pct-$Fmt"
foreach ($s in $Scenes) {
  $d = Join-Path $ProjectDir "outl\$s"; New-Item -ItemType Directory -Force -Path $d | Out-Null
  $stampFile = Join-Path $d ".stamp"
  $old = if (Test-Path $stampFile) { (Get-Content $stampFile -Raw).Trim() } else { "" }
  if ($Clean -or $old -ne $Stamp) {
    Get-ChildItem $d -Include "f*.jpg", "f*.png" -File -Recurse | Remove-Item -Force
    Set-Content -Path $stampFile -Value $Stamp -NoNewline
  }
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$ext = if ($Fmt.ToUpper() -eq "JPEG") { "jpg" } else { "png" }

$queue = [System.Collections.Generic.Queue[string]]::new()
foreach ($s in $Scenes) { $queue.Enqueue($s) }
$active = @()

while ($queue.Count -gt 0 -or $active.Count -gt 0) {
  while ($queue.Count -gt 0 -and $active.Count -lt $Jobs) {
    $sid = $queue.Dequeue()
    Write-Host "=== Starting $sid ($Preset, SPP=$Spp, PCT=$Pct%, FMT=$Fmt) ==="
    $job = Start-Job -ScriptBlock {
      param($Blender, $RunPy, $sid, $Preset, $Spp, $Pct, $Fmt, $ShadowDist, $ProjectDir, $BlOutDir, $ext)
      $env:SPP = "$Spp"
      $env:PCT = "$Pct"
      $env:FMT = "$Fmt"
      $env:SHADOW_DIST = "$ShadowDist"
      $log = Join-Path $ProjectDir "outl\$sid.log"
      foreach ($try in 1, 2) {
        & $Blender -b --factory-startup -P $RunPy -- $sid $Preset all *> $log
        if (Select-String -Path $log -Pattern "SCENE_OK" -Quiet) { break }
        Write-Output "  $sid attempt $try failed (see $log), resuming..."
      }
      $lines = Select-String -Path $log -Pattern "Error|Traceback|RESUME|SKIP|SCENE_OK" | ForEach-Object { $_.Line }
      $pattern = Join-Path $ProjectDir "out\bl\$sid\f%04d.$ext"
      $mp4Out = Join-Path $BlOutDir "$sid.mp4"
      ffmpeg -loglevel error -y -framerate 30 -i $pattern -vf "scale=1080:1920:flags=lanczos" -c:v libx264 -pix_fmt yuv420p -crf 16 $mp4Out
      if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed for $sid" }
      return ($lines -join "`n") + "`n  -> $mp4Out"
    } -ArgumentList $Blender, $RunPy, $sid, $Preset, $Spp, $Pct, $Fmt, $ShadowDist, $ProjectDir, $BlOutDir, $ext
    $active += $job
  }

  $done = $active | Where-Object { $_.State -ne "Running" }
  foreach ($j in $done) {
    Receive-Job $j
    Remove-Job $j
  }
  $active = @($active | Where-Object { $_.State -eq "Running" })
  if ($active.Count -gt 0) { Start-Sleep -Milliseconds 500 }
}

# Sync audio into Remotion public/shorts/<Slug>/
$AudioSrc = Join-Path $ProjectDir "audio"
if (Test-Path $AudioSrc) {
  $AudioDst = Join-Path $PublicDir "audio"
  New-Item -ItemType Directory -Force -Path $AudioDst | Out-Null
  Copy-Item -Path (Join-Path $AudioSrc "*") -Destination $AudioDst -Recurse -Force
}

Write-Host "TOTAL $([Math]::Round($sw.Elapsed.TotalSeconds, 1))s"
