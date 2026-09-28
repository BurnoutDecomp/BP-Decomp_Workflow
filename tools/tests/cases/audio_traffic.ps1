# audio_traffic -- lane SNDTRAF (gameplay wave GW2). Traffic had no engine, horn or skid sound:
# the traffic sound state manager was a boot shell (Prepare returned true without loading
# anything, no TrafficState was ever created, UpdateParams was the base no-op) and the four
# traffic effect / control classes had no Attach / UpdateParams / ProcessUpdate bodies.
#
# Run it:  powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case audio_traffic
#
# THE CHAIN THIS CASE WITNESSES (BRN_TRAFFICSND_DIAG, every witness first-N capped):
#   [trafficsnd] manager prepared  TrafficStateManager::Prepare reached its finished state:
#                                  the TrafficCsis / HornsCsis interfaces and the Traffic_Bank /
#                                  patch_bank_horns banks loaded, six TrafficStates prepared.
#   [trafficsnd] attach            UpdateParams bound a traffic sound entity from the traffic
#                                  module's per-frame list to a free TrafficState.
#   [trafficsnd] voice started     an effect told its voice to play: type=engine from
#                                  TrafficEngine::Attach (engine-on cars), type=horn|alarm from
#                                  TrafficHorn::ProcessUpdate, type=skid from
#                                  TrafficSkid::UpdateParams (physical cars only).
#
# THE SCENARIO is traffic_soak_lane's: the live traffic lane, throttle held, weaving, so traffic
# passes the camera microphone within the attach radius. Engine voices need only an attached
# car with its engine on; horns and skids depend on what the traffic does, so they are INFO.
@{
  Name    = 'audio_traffic'
  Area    = 'sound'
  Bug     = 'traffic cars make no engine, horn or skid sound'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    SkipIntro      = $true
    AcceptGap      = 1.0
    MaxSeconds     = 80
    Teleport       = '3323.9,-2.4,-1793.2,0'
    ThrottleScript = '0:accel'
    SteerScript    = '0:none,6:left,7:none,14:right,15:none'
  }
  DiagEnv = 'BRN_TRAFFICSND_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # PRECONDITION: the manager finished preparing (banks loaded, states created). If this is
    # red, nothing below can happen -- and sound boot itself waits on it.
    @{ Kind = 'LogCount';   Name = 'traffic sound manager prepared'
       Pattern = '\[trafficsnd\] manager prepared'; Min = 1 }

    # THE LANE'S PROOF: traffic entities were attached and their engine voices started.
    @{ Kind = 'LogCount';   Name = 'traffic entities attached to states'
       Pattern = '\[trafficsnd\] attach slot='; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'traffic engine voices started'
       Pattern = '\[trafficsnd\] voice started type=engine'; Min = 1 }

    # No traffic sound assert (slot bookkeeping, missing content, a mis-bound controller).
    @{ Kind = 'LogCount';   Name = 'no traffic sound assert'
       Pattern = '\[ASSERT \d+\].*(BrnTrafficStateManager|BrnTrafficState|BrnTrafficControl|BrnTrafficEngine|BrnTrafficHorn|BrnTrafficSkid|Failed to find Effect Object)'
       Max = 0 }

    # INFO: horns / alarms, skids (physical cars) and culls depend on the traffic the run meets.
    @{ Kind = 'LogCount';   Name = 'info: horn or alarm voices'; Pattern = '\[trafficsnd\] voice started type=(horn|alarm)' }
    @{ Kind = 'LogCount';   Name = 'info: skid voices';          Pattern = '\[trafficsnd\] voice started type=skid' }
    @{ Kind = 'LogCount';   Name = 'info: culls for a nearer car'; Pattern = '\[trafficsnd\] cull ' }
  )
}
