# vw_band_baseline -- baseline_boot_drive, unchanged, with an optional shader-bundle swap for
# lane BAND (wave VW): $env:VW_BAND_SHADERS = <SHADERS.BNDL> installs that bundle as
# build\game\SHADERS.BNDL for this run only (under the box lock) and the first check puts the
# live one back. With the variable unset this is baseline_boot_drive plus one passing check.
$lCase = & (Join-Path $PSScriptRoot 'baseline_boot_drive.ps1')
$lCase.Name = 'vw_band_baseline'
$lCase.Setup = {
  param($ctx)
  if ($env:VW_BAND_SHADERS) {
    $lLive = Join-Path $ctx.Root 'build\game\SHADERS.BNDL'
    Copy-Item $lLive (Join-Path $ctx.RunDir 'SHADERS.BNDL.live') -Force
    Copy-Item $env:VW_BAND_SHADERS $lLive -Force
    Write-Host "[case] VW_BAND_SHADERS: installed $($env:VW_BAND_SHADERS) for this run"
  }
}
$lCase.Checks = @(
  @{ Kind = 'Script'; Name = 'live SHADERS.BNDL restored'; Script = {
      param($ctx)
      $lSaved = Join-Path $ctx.RunDir 'SHADERS.BNDL.live'
      if (-not (Test-Path $lSaved)) { return @{ Pass = $true; Detail = 'no swap this run' } }
      $lLive = [IO.Path]::GetFullPath((Join-Path $ctx.RunDir '..\..\..\..\..\build\game\SHADERS.BNDL'))
      Copy-Item $lSaved $lLive -Force
      $lOk = (Get-FileHash $lSaved).Hash -eq (Get-FileHash $lLive).Hash
      return @{ Pass = $lOk; Detail = "restored $lLive" }
    } }
) + $lCase.Checks
$lCase
