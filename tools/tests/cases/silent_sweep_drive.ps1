# silent_sweep_drive -- the returning-player drive the silent-link sweep's class A fixes are checked on.
# Same scenario as baseline_boot_drive, booted with TitleStart, with frames dumped and the native
# particle witness armed. The particle lines are what prove NativeParticleVertex's descriptor did not
# stop the Spark / SimpleParticle draws.
@{
  Name    = 'silent_sweep_drive'
  Area    = 'harness'
  Bug     = 'none -- regression run for the silent-link sweep'
  Frames  = $true
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 70
    TitleStart  = $true
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'
  }
  DiagEnv = 'BRN_SIMPLEFX_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount';   Name = 'NativeParticleVertex::Construct no longer reported missing'; Pattern = 'NativeParticleVertex::Construct'; Max = 0 }
    @{ Kind = 'LogCount';   Name = 'no vertex element dropped'; Pattern = 'VertexDescriptor: (unknown vertex format|element type has no default)'; Max = 0 }
    @{ Kind = 'Script';     Name = 'the car moved (teleport seat -> first respawn, > 20 m)'; Script = {
        param($ctx)
        $s = Get-DriveSegment $ctx.LogLines
        if (-not $s.Known) { return @{ Pass = $false; Detail = ("{0} [motion] sample(s): no car position in this log" -f $s.Samples) } }
        return @{ Pass = ($s.Path -gt 20.0); Detail = ("path={0:f1}m net={1:f1}m teleported={2} later respawns={3}" -f $s.Path, $s.Net, $s.Teleported, $s.Respawns) }
      } }
    @{ Kind = 'LogCount'; Name = 'info: GAMEWRECKED hud messages (gameplay, never fails)'; Pattern = 'STARTING MESSAGE NAMED "GAMEWRECKED' }
  )
}
