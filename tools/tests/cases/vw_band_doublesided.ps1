# vw_band_doublesided -- BurnoutDecomp/b5-decomp#27 "Banding": shadow acne on double-sided
# world surfaces (lane BAND, wave VW).
#
# THE BUG. Double-sided world materials (and the Sign_* shaders) keep their FRONT faces in the
# shadow map -- their Z-only technique is CULLMODE none, on console and PC alike -- so a lit
# double-sided surface sits at depth equality with itself in the map. The console's pixel shaders
# for exactly those 22 materials pull the compare depth toward the light first
# (Diffuse_Opaque_Doublesided PS: z_ref = z - ShadowMap_Constants2.z * 0.0005, then the 2x2 PCF);
# the PC build compiles them from the nushaders HLSL, whose Shadow.fxh applied that bias only on
# its BPR branch, so on PC those surfaces shadow themselves into texel-row stripes.
#
# THE SCENE. The dock road at Paradise Wharf (Harbor Town), car parked facing -Z under the
# elevated steel walkway. Two lit double-sided surfaces fill the upper-left of the frame: the
# walkway deck underside and the lit face of its support column. Score = VW_BAND_acne.py (mean
# second difference of luminance / mean luminance) on the last static frame.
#   MEASURED (exe 15:29, same parked pose): deck 0.140 -> 0.010, column 0.166 -> 0.035 with the
#   biased shaders; the road control does not move.
# The spawn is pinned by the profile fixture and the car is parked on the handbrake, so every
# run renders the same view.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_band_doublesided
# A/B:      $env:VW_BAND_SHADERS = <SHADERS.BNDL>  installs that bundle as build\game\SHADERS.BNDL
#           for this run only (under the box lock); the first check puts the live one back.
@{
  Name    = 'vw_band_doublesided'
  Area    = 'render'
  Bug     = 'BurnoutDecomp/b5-decomp#27 -- banding (shadow acne) on double-sided surfaces'
  Frames  = $true
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'   # pinned spawn; run_case restores the box save
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 48
    SkipIntro      = $true
    AcceptGap      = 1.0
    FrameEvery     = 30
    ThrottleScript = '0:handbrake'
    Teleport       = '1288.4,15,-523.6,180'
  }
  DiagEnv = ''
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
        $lLive = [IO.Path]::GetFullPath((Join-Path $ctx.RunDir '..\..\..\..\..\build\game\SHADERS.BNDL'))
        Copy-Item $lSaved $lLive -Force
        $lOk = (Get-FileHash $lSaved).Hash -eq (Get-FileHash $lLive).Hash
        return @{ Pass = $lOk; Detail = "restored $lLive" }
      } }
    @{ Kind = 'Mark'; Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Script'; Name = 'acne: walkway deck + column (double-sided) vs road control'; Script = {
        param($ctx)
        $lCsv = Join-Path $ctx.FrameDir 'frames.csv'
        if (-not (Test-Path $lCsv)) { return @{ Pass = $false; Detail = 'no frames.csv' } }
        # The last frame whose car position is the parked pose (frames.csv cols 21..23 = car x,y,z).
        $lRow = Get-Content $lCsv | Where-Object { $_ -match '^\d+,' } | ForEach-Object {
                  $c = $_ -split ','; [pscustomobject]@{ N = [int]$c[0]; X = [double]$c[20]; Z = [double]$c[22] } } |
                Where-Object { [math]::Abs($_.X - 1288.4) -lt 0.5 -and [math]::Abs($_.Z + 523.6) -lt 0.5 } |
                Select-Object -Last 1
        if (-not $lRow) { return @{ Pass = $false; Detail = 'car never parked at the pose (teleport missed?)' } }
        $lFrame = Join-Path $ctx.FrameDir ('bb_{0:D6}.bmp' -f $lRow.N)
        $lPy = Join-Path $ctx.RunDir '..\..\..\..\..\tools\tests\tools\VW_BAND_acne.py'
        $lDeck   = [double](& py -3 $lPy $lFrame '0,30,135,125')
        $lColumn = [double](& py -3 $lPy $lFrame '175,90,200,230')
        $lRoad   = [double](& py -3 $lPy $lFrame '600,450,900,600')
        $lPass = ($lDeck -lt 0.05) -and ($lColumn -lt 0.08) -and ($lRoad -gt 0.05) -and ($lRoad -lt 0.25)
        return @{ Pass = $lPass; Detail = ("{0}: deck={1:f3} (<0.05) column={2:f3} (<0.08) road-control={3:f3} (0.05..0.25)" -f `
                  (Split-Path $lFrame -Leaf), $lDeck, $lColumn, $lRoad) }
      } }
  )
}
