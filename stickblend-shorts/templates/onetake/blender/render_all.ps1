<#
.SYNOPSIS
One-Take-Short rendern: alle Sets (zwei parallel), fortsetzbar, -> public/bl/onetake.mp4
  .\blender\render_all.ps1                       # final, alle Sets
  .\blender\render_all.ps1 -Preset preview -Spp 4 # schnelle Bewegungs-Vorschau -> out/preview.mp4
  .\blender\render_all.ps1 -Sets A,C -Clean       # nur diese Sets, von vorn
Fortsetzen: vorhandene Bilder werden uebersprungen. Ein Fingerabdruck (Hash aus Wort-Zeitachse, blender/*.py, Preset,
SPP, PCT) pro Set erkennt veraltete Bilder (neue Stimme, geaenderte Kamera); nur dann werden sie geloescht.
Log pro Set: out/bl/<set>.log; stuerzt Blender ab, wird einmal fortgesetzt.
#>
param(
  [string[]]$Sets,
  [string]$Preset = "final",
  [int]$Spp = 12,
  [int]$Pct = 0,
  [int]$Jobs = 2,
  [switch]$Clean,
  [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)
$ErrorActionPreference = "Stop"
$Proj = Split-Path -Parent $PSScriptRoot
$RunPy = Join-Path $PSScriptRoot "run.py"
$BlDir = Join-Path $Proj "out\bl"; New-Item -ItemType Directory -Force -Path $BlDir | Out-Null
if (-not $Sets -or $Sets.Count -eq 0) {
  $line = (& $Blender -b --factory-startup -P $RunPy -- --list 2>&1 | Select-String "^SETS ").Line
  $Sets = $line.Substring(5).Split(" ", [StringSplitOptions]::RemoveEmptyEntries)
}
# Fingerabdruck
$files = @(Get-ChildItem (Join-Path $Proj "src\timeline*.json")) + @(Get-ChildItem (Join-Path $PSScriptRoot "*.py"))
$bytes = [System.Collections.Generic.List[byte]]::new()
foreach ($f in $files) { $bytes.AddRange([System.IO.File]::ReadAllBytes($f.FullName)) }
$sha = [System.Security.Cryptography.SHA1]::Create()
$Stamp = ([BitConverter]::ToString($sha.ComputeHash($bytes.ToArray())) -replace "-", "").Substring(0, 12) + "-$Preset-$Spp-$Pct"
foreach ($s in $Sets) {
  $d = Join-Path $BlDir $s; New-Item -ItemType Directory -Force -Path $d | Out-Null
  $sf = Join-Path $d ".stamp"; $old = if (Test-Path $sf) { (Get-Content $sf -Raw).Trim() } else { "" }
  if ($Clean -or $old -ne $Stamp) { Get-ChildItem $d -Filter "f*.png" -File | Remove-Item -Force; Set-Content $sf $Stamp -NoNewline }
}
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$queue = [System.Collections.Generic.Queue[string]]::new(); foreach ($s in $Sets) { $queue.Enqueue($s) }
$active = @()
while ($queue.Count -gt 0 -or $active.Count -gt 0) {
  while ($queue.Count -gt 0 -and $active.Count -lt $Jobs) {
    $sid = $queue.Dequeue(); Write-Host "=== $sid ($Preset, SPP=$Spp) ==="
    $active += Start-Job -ScriptBlock {
      param($Blender, $RunPy, $sid, $Preset, $Spp, $Pct, $BlDir)
      $env:SPP = "$Spp"; if ($Pct -gt 0) { $env:PCT = "$Pct" }
      $log = Join-Path $BlDir "$sid.log"
      foreach ($try in 1, 2) {
        & $Blender -b --factory-startup -P $RunPy -- $sid $Preset all *> $log
        if (Select-String -Path $log -Pattern "SET_OK" -Quiet) { break }
        Write-Output "  $sid Versuch $try fehlgeschlagen (siehe $log)"
      }
      (Select-String -Path $log -Pattern "Error|Traceback|RESUME|SET_OK" | ForEach-Object { $_.Line }) -join "`n"
    } -ArgumentList $Blender, $RunPy, $sid, $Preset, $Spp, $Pct, $BlDir
  }
  foreach ($j in @($active | Where-Object { $_.State -ne "Running" })) { Receive-Job $j; Remove-Job $j }
  $active = @($active | Where-Object { $_.State -eq "Running" })
  if ($active.Count -gt 0) { Start-Sleep -Milliseconds 500 }
}
# Alle Sets in globaler Reihenfolge zu einem Clip
$all = Join-Path $BlDir "all"; if (Test-Path $all) { Remove-Item $all -Recurse -Force }; New-Item -ItemType Directory $all | Out-Null
foreach ($s in $Sets) { Copy-Item (Join-Path $BlDir "$s\f*.png") $all }
$outv = if ($Preset -eq "preview") { Join-Path $Proj "out\preview.mp4" } else { Join-Path $Proj "public\bl\onetake.mp4" }
New-Item -ItemType Directory -Force -Path (Split-Path $outv) | Out-Null
$first = (Get-ChildItem $all -Filter "f*.png" | Sort-Object Name | Select-Object -First 1).BaseName.Substring(1)
ffmpeg -loglevel error -y -framerate 30 -start_number ([int]$first) -i (Join-Path $all "f%04d.png") -vf "scale=1080:1920:flags=lanczos" -c:v libx264 -pix_fmt yuv420p -crf 16 $outv
Write-Host "-> $outv  TOTAL $([Math]::Round($sw.Elapsed.TotalSeconds, 1))s"
