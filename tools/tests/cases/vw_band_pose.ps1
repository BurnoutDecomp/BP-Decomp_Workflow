# vw_band_pose -- lane BAND (wave VW) fixed-pose probe for issue #27: teleport the car to a
# pose, park it on the handbrake, dump frames. Caller knobs:
#   $env:VW_BAND_POSE    = 'x,y,z,heading'   (default: the I-88 deck at Paradise Wharf)
#   $env:VW_BAND_DIAG    = 'BRN_X=1,...'     (passed through DiagEnv)
#   $env:VW_BAND_THROTTLE = flow_run -ThrottleScript (default: nudge to arm the teleport, then park)
#   $env:VW_BAND_SHADERS = <bundle path>     (installed as build\game\SHADERS.BNDL for this run
#                                             only, under the box lock; restored by the first check)
@{
  Name    = 'vw_band_pose'
  Area    = 'render'
  Bug     = 'BurnoutDecomp/b5-decomp#27 -- banding on specific surfaces (pose probe)'
  Frames  = $true
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'   # pinned spawn; run_case restores the box save
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 48
    SkipIntro      = $true
    AcceptGap      = 1.0
    FrameEvery     = 30
    ThrottleScript = $(if ($env:VW_BAND_THROTTLE) { $env:VW_BAND_THROTTLE } else { '0:accel,2.5:handbrake' })
    Teleport       = $(if ($env:VW_BAND_POSE) { $env:VW_BAND_POSE } else { '1369.5,23.0,481.5,324' })
  }
  DiagEnv = $(if ($env:VW_BAND_DIAG) { $env:VW_BAND_DIAG } else { '' })
  Setup   = {
    param($ctx)
    if ($env:VW_BAND_SHADERS) {
      $lLive = Join-Path $ctx.Root 'build\game\SHADERS.BNDL'
      Copy-Item $lLive (Join-Path $ctx.RunDir 'SHADERS.BNDL.live') -Force
      Copy-Item $env:VW_BAND_SHADERS $lLive -Force
      Write-Host "[case] VW_BAND_SHADERS: installed $($env:VW_BAND_SHADERS) for this run"
    }
  }
  Checks  = @(
    @{ Kind = 'Script'; Name = 'live SHADERS.BNDL restored'; Script = {
        param($ctx)
        $lSaved = Join-Path $ctx.RunDir 'SHADERS.BNDL.live'
        if (-not (Test-Path $lSaved)) { return @{ Pass = $true; Detail = 'no swap this run' } }
        $lLive = Join-Path (Split-Path (Split-Path $ctx.RunDir -Parent) -Parent) '..\..\..\build\game\SHADERS.BNDL'
        $lLive = [IO.Path]::GetFullPath($lLive)
        Copy-Item $lSaved $lLive -Force
        $lOk = (Get-FileHash $lSaved).Hash -eq (Get-FileHash $lLive).Hash
        return @{ Pass = $lOk; Detail = "restored $lLive" }
      } }
    @{ Kind = 'Mark'; Name = 'reached DRIVING'; Phase = 'DRIVING' }
  )
}
