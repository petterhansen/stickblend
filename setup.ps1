<#
.SYNOPSIS
One-time setup for stickblend-starter:
  1. Installs Remotion npm dependencies
  2. Downloads reusable royalty-free music & CC0 SFX into assets_audio/
  3. Downloads a starter pack of CC0 Poly Haven 3D models, PBR textures, and pure-sky HDRIs into assets3d/
#>
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host "=== 1/3 Installing Remotion dependencies ==="
Push-Location (Join-Path $Root "remotion")
npm install
Pop-Location

Write-Host "`n=== 2/3 Downloading royalty-free music & CC0 SFX library ==="
python (Join-Path $Root "stickblend\tools\fetch_audio.py")

Write-Host "`n=== 3/3 Downloading CC0 Poly Haven starter 3D assets (1K) ==="
python (Join-Path $Root "stickblend\tools\polyhaven.py") --res 1k `
  street_lamp_01 painted_wooden_bench Chandelier_01 ArmChair_01 ClassicConsole_01 `
  WoodenTable_01 WoodenChair_01 fancy_picture_frame_01 antique_ceramic_vase_01 `
  brass_vase_01 book_encyclopedia_set_01 shrub_01 shrub_02 `
  cobblestone_pavement herringbone_parquet large_sandstone_blocks_01 dark_wood green_metal_rust `
  belfast_sunset_puresky kloofendal_48d_partly_cloudy_puresky

if (-not (Test-Path (Join-Path $Root ".env"))) {
  Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
  Write-Host "`nCreated .env from .env.example — remember to add your GEMINI_API_KEY!"
}

Write-Host "`nSetup complete! Run: .\stickblend-shorts\new_short.ps1 -Slug my-first-short"
