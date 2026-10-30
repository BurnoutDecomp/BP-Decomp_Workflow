# Case definition for the root-reviewed private native Resource Windows run.
@{
  Name = 'resource_texture7_source22e_62144'
  NativePacketRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
  Suite = 'resource_windows'
  RunSlot = 62144
  Area = 'debug-menu'
  Bug = 'Source22e Texture Window, Sort, Draw and four callbacks require an actual populated native texture caption/image before further actions, independent changed/restored pixels and exact initial restore. Queue, partial-fixup and forced Replay states are excluded.'
  Frames = $true
  ProfileFixture = 'C:\Users\adri1\Documents\Codex\resource_texture_source22e_62144_20261029\profile_snapshots\resource_windows_20261029_213450\Profile.sav'
  ProfileFixtureSha256 = 'd7062394d301297191063dbf1c30cddd312ad28dae4e1f0e280bbbf796d09241'
  Run = @{
    StrictGameOwnership = $true
    AllowConcurrentGames = $true
    MaxConcurrentOtherGames = 100
    TitleStart = $true
    SkipIntro = $false
    AcceptGap = 1.0
    MaxSeconds = 360
    MaxLogMB = 64
    MinFreeGB = 2
    Drive = $true
    DriveDelay = 0.0
    ThrottleScript = '0:brake+handbrake'
    MotionProbe = $true
    FrameEvery = 1000000000
  }
  DiagEnv = 'BRN_DEBUG_UI_TRACE=1,BRN_FRAME_DUMP_REQUEST=1,BRN_FRAME_DUMP_MAX=28'
  Setup = {
    param($ctx)
    $driver = Join-Path $ctx.Case.NativePacketRoot 'ResourceNativeDriver.ps1'
    $driverArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$driver`"",'-Suite','resource_windows',
      '-GameLog',"`"$($ctx.GameLog)`"",'-GameDir',"`"$($ctx.GameDir)`"",'-DataDir',"`"$($ctx.WorkingDirectory)`"",
      '-RunDir',"`"$($ctx.RunDir)`"",'-Slot',"$($ctx.Slot)",'-TimeoutSec',"$($ctx.Case.Run.MaxSeconds - 40)")
    return Start-Process powershell.exe -ArgumentList $driverArgs -PassThru -WindowStyle Hidden
  }
  Checks = @(
    @{ Kind='NewAsserts'; Name='no new assert families' }
    @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    @{ Kind='Mark'; Name='reached DRIVING'; Phase='DRIVING' }
    @{ Kind='LogCount'; Name='current profile native read succeeded'; Pattern="\[SaveLoadPC\] bootup read: OK name='Profile'"; Min=1 }
    @{ Kind='LogCount'; Name='current profile progression/options validation succeeded'; Pattern='\[profile-save\] ValidateProfiles: progression=1 progressionDLC1=1 options=1 optionsDLC1=1 liveRevenge=1'; Min=1 }
    @{ Kind='LogCount'; Name='current profile deserialised as returning profile'; Pattern='\[profile-save\] deserialised: isNewProfile=0 -> playIntroVideo=0'; Min=1 }
    @{ Kind='LogCount'; Name='current returning-profile progress is active'; Pattern='\[one-profile\].*same=1.*isNewProfile gs=0 pm=0.*medalsFromTheStart gs=[0-9]+ pm=[0-9]+.*eventCount gs=[0-9]+ pm=[0-9]+.*spawnCarId gs=[0-9A-Fa-f]+ pm=[0-9A-Fa-f]+'; Min=1 }
    @{ Kind='LogCount'; Name='current profile native spawn/progression callback'; Pattern='\[GameStateModule::OnProfileLoaded\].*spawnCar=\S+ profileCar=\S+ rank=[0-9]+ maxCars=[0-9]+ savedPos=\('; Min=1 }
    @{ Kind='Script'; Name='native resource driver completed with owner-bound frames'; Script={
      param($ctx)
      $p=Join-Path $ctx.RunDir 'RESOURCE_DRIVER_RECEIPT.json'
      if(!(Test-Path -LiteralPath $p)){return @{Pass=$false;Detail='driver receipt absent'}}
      $j=Get-Content -LiteralPath $p -Raw|ConvertFrom-Json
      return @{Pass=($j.status -ceq 'complete' -and $j.suite -ceq 'resource_windows' -and [int]$j.slot -eq [int]$ctx.Case.RunSlot -and $j.texture_provider_readiness.status -ceq 'validated_actual_provider_readiness' -and [int]$j.phase_count -eq 11 -and @($j.frame_receipts).Count -eq 28);
        Detail=('status={0}; frames={1}; selected-pool={2}' -f $j.status,@($j.frame_receipts).Count,$j.selected_pool)}
    } }
  )
}
