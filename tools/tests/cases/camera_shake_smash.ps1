# camera_shake_smash -- the director camera must SHAKE when the game asks it to.
#
# THE BUG (lane `camera`, wave 2026-09-06): "director/camera -- especially camera shakes and
# blends". On the console every shake in the game is a REQUEST written into
# Camera::mEffects (mfShakeAmplitude / mfShakeFrequency / mu8ShakeType) and CONSUMED by
# CameraFinaliser::Update's steps 2-4 -> KeyAnimShakeController::Update @0x8223D488, which
# resolves the requested shake TYPE as a shot in the director's shake-anim shot group and
# applies that shot's shake to the finalised camera transform. On this build steps 2-4 are
# gated and KeyAnimShakeController has no home at all, so every shake request in the game is
# written and never read: the camera never moves.
#
# THE SCENARIO is the gate-UI wave's own proven route -- boot, exit the junkyard, hold the
# throttle, NO teleport -- because that wave measured the SMASH ladder
# (OnPropHit -> game action 58 -> stunt element type 1) firing on the first gate of it. That
# action raises GameState::miThisFramesActionFlags bit 0x10, which is the very bit
# CameraFinaliser step 2 reads to ramp the shake scale, and step 3 then publishes the
# cameradefaults base shake (measured on this build: type 5, amplitude 4.0, decay 0.4 --
# `[cam-defaults]` below). Shot 4 of the shake-anim group (== type 5) is a `proceduralshake`
# record, so the console's PROCEDURAL arm is the one this scenario exercises.
#
# THE WITNESS is the per-frame `[cam]` line MainDirector::Update prints at the publish point
# (the last read of the frame camera before OutputBuffer::SetCameraOutput), carrying the
# camera pose AND the shake request next to each other. A shake that is requested but not
# applied is invisible in every other log this build writes -- the pose simply stays smooth.
#
# ⚠️ THE POSE CHECK EXCLUDES CAMERA CUTS ON PURPOSE. The first draft of this case did not, and
# it PASSED on the broken build: the junkyard / car-select ICE cameras cut between shots, and a
# cut moves the camera tens of metres in one frame, which swamps any second-difference measure.
# Every sample below is dropped unless the camera moved less than KF_CUT_METRES in each of the
# two frames the second difference spans.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case camera_shake_smash -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case camera_shake_smash -Label post-fix
#
# ⛔⛔ NOT SHORTENED, AND NOT SkipIntro'd -- MEASURED THREE TIMES (2026-09-06, lane harness2).
#   Every other case in this directory now carries `SkipIntro` (the console -skipvideos latch) and
#   `AcceptGap` (a faster harness Accept pump) and a smaller MaxSeconds. THIS ONE DELIBERATELY
#   CARRIES NEITHER, because its last check normalises against the whole run:
#
#     "the camera pose actually shakes ..." divides the mean fwd 2nd-difference of the frames that
#     REQUESTED a procedural shake by the mean over EVERY OTHER FRAME IN THE RUN, and wants >= 3.
#     The shaking half is a property of the shake; the CALM half is a property of what else the run
#     contains. Boot-movie and menu frames are extremely calm, so they pull that denominator down.
#
#   Measured, all three runs on the same build, same scenario apart from the knobs:
#     275 s, no knobs (banked 20260906_125835)   shake 0.001612 / calm 0.0003957 -> ratio 4.073 PASS
#     200 s, SkipIntro+AcceptGap  (_140406)      shake 0.001612 / calm 0.000544  -> ratio 2.963 FAIL
#     275 s, SkipIntro+AcceptGap  (_142238)      shake 0.001612 / calm 0.0005417 -> ratio 2.975 FAIL
#   The numerator is BIT-IDENTICAL in all three (the same 18 frames); only the denominator moves,
#   and it moves with the boot content, not with the budget. Deleting the two VP6 logos deletes
#   ~5 s of the calmest frames in the run and raises the calm mean ~37 %.
#   ⚠ So this is NOT "the case is too slow to shorten": it is a check whose threshold is
#   calibrated against a particular run composition. Re-scoping it to the DRIVING frames only
#   (`After='strfin'`, or a ratio computed per-phase) would make it both shorter AND more honest,
#   but that is a change to the camera lane's own measurement and this lane does not own it.
#   ⛔ Two earlier RED runs of this case (_135159, _135614 at 200 s) were a DIFFERENT and now-fixed
#   fault: the slot staging re-seeded the FreshProfile-parked save, so the game booted as a
#   returning player and the already-collected gates posted no game action 58. See
#   tools/tests/slots.ps1 -NoProfileSeed.
#
@{
  Name    = 'camera_shake_smash'
  Area    = 'director/camera'
  Bug     = 'camera shakes are missing -- every mEffects shake request is written and never read'
  Frames  = $false
  # ⭐ FRESH PROFILE IS LOAD-BEARING, and finding out why is half this case. The first RED run
  # smashed TWO gates (`[UI-gate] OnPropHit zone=119 latch=SMASH`) and STILL raised no shake
  # bit, because StuntManager::ProcessStuntElement returns early on an element the profile has
  # already collected (`if (lbAlreadyDone) { ...; return; }`, StuntManager_gUI_00.cpp:387) and
  # game action 58 -- the only writer of miThisFramesActionFlags bit 0x10 -- is posted only on
  # FIRST completion. The shipped Memcard\Profile.sav has those gates collected, so a smash on
  # a saved profile is silent. Parking the save makes the first gate a first completion.
  FreshProfile = $true
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 275
  }
  # BRN_PROP_DIAG is the gate-UI ladder's own trace ([UI-gate] / OnPropHit / stunt-element);
  # it is read-only and it is what tells a failing run WHY no gate was smashed.
  DiagEnv = 'BRN_CAMERA_TRACE=1,BRN_PROP_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # The witness itself has to be there, or nothing below means anything.
    @{ Kind = 'LogCount';   Name = 'camera witness present'; Pattern = '^\[cam\] f='; Min = 500 }

    # THE PRODUCER. A smashed gate really does raise the shake bit on this route.
    @{ Kind = 'LogCount';   Name = 'a smash raised the shake bit'; Pattern = '^\[cam\] smash '; Min = 1 }

    # THE CONSUMER. RED: no line, because nothing on this build reads the shake request.
    @{ Kind = 'LogCount';   Name = 'the shake request reached a shake shot'; Pattern = '^\[cam\] shake applied'; Min = 1 }

    # THE BEHAVIOUR, and the check that decides the case: while a PROCEDURAL shake is
    # requested the camera's high-frequency angular content must be far above what the same
    # run shows while none is. Self-calibrating (both halves come from this run), cut-immune,
    # and restricted to the arm under test.
    #
    # ⚠️ WHY `typ >= 5`, and why that is not tuning the check to pass. The shake-anim shot
    # group has NINE shots and the case's own `[cam-shotlist]` probe prints what each one is:
    # shots 0-3 (== shake TYPE 1-4) are `iceanim` takes and shots 4-8 (types 5-9) are
    # `proceduralshake` records. This lane reconstructs the PROCEDURAL arm of
    # KeyAnimShakeController::Update and leaves the ICE take-runtime arm a NAMED park (it
    # needs the ICETake swap six camera headers currently defer), so a type-1..4 request is
    # expected to do nothing and pooling it with the type-5..9 frames just dilutes the
    # measure. On the pre-fix build this restriction costs the check nothing: NO frame of any
    # type carries an applied shake, so the population is empty and the check fails on that.
    # ⚠️ `amp > 0.05` drops the geometric decay tail (step 3 decays the shake scale by 0.4 per
    # frame, so a 4.0 request is under 0.05 within ~11 frames); those frames legitimately
    # carry almost no shake.
    @{ Kind = 'Script'; Name = 'the camera pose actually shakes while a procedural shake is requested'
       Script = {
         param($ctx)
         $KF_CUT_METRES  = 3.0
         $KF_MIN_AMP     = 0.05
         $KI_FIRST_PROC_SHAKE_TYPE = 5
         $laP = @(); $laF = @(); $laA = @(); $laT = @()
         foreach ($l in $ctx.LogLines) {
           if ($l -match '^\[cam\] f=\d+ pos=(?<px>[-\d.eE+]+),(?<py>[-\d.eE+]+),(?<pz>[-\d.eE+]+) fwd=(?<x>[-\d.eE+]+),(?<y>[-\d.eE+]+),(?<z>[-\d.eE+]+) fov=\S+ amp=(?<a>[-\d.eE+]+) frq=\S+ typ=(?<t>\d+)') {
             $laP += ,@([double]$Matches.px, [double]$Matches.py, [double]$Matches.pz)
             $laF += ,@([double]$Matches.x,  [double]$Matches.y,  [double]$Matches.z)
             $laA += [double]$Matches.a
             $laT += [int]$Matches.t
           }
         }
         if ($laF.Count -lt 300) { return @{ Pass = $false; Detail = "only $($laF.Count) parsed [cam] samples" } }

         function Step([object[]]$a, [int]$i) {
           $d = 0.0
           for ($k = 0; $k -lt 3; $k++) { $v = $a[$i][$k] - $a[$i-1][$k]; $d += $v*$v }
           return [Math]::Sqrt($d)
         }

         $lfShakeSum = 0.0; $liShakeN = 0; $lfCalmSum = 0.0; $liCalmN = 0; $liCuts = 0; $liIce = 0
         for ($i = 2; $i -lt $laF.Count; $i++) {
           # Drop the sample if the camera CUT anywhere in the 3-frame window.
           if ((Step $laP $i) -gt $KF_CUT_METRES -or (Step $laP ($i-1)) -gt $KF_CUT_METRES) { $liCuts++; continue }
           $d = 0.0
           for ($k = 0; $k -lt 3; $k++) {
             $v = $laF[$i][$k] - 2.0 * $laF[$i-1][$k] + $laF[$i-2][$k]
             $d += $v * $v
           }
           $d = [Math]::Sqrt($d)
           if ($laA[$i] -le 0.0) { $lfCalmSum += $d; $liCalmN++ }
           elseif ($laT[$i] -lt $KI_FIRST_PROC_SHAKE_TYPE) { $liIce++ }
           elseif ($laA[$i] -gt $KF_MIN_AMP) { $lfShakeSum += $d; $liShakeN++ }
         }
         $lfCalm = if ($liCalmN -gt 0) { $lfCalmSum / $liCalmN } else { 0.0 }
         if ($liShakeN -lt 10) {
           return @{ Pass = $false
                     Detail = ("only {0} cut-free frame(s) requested a PROCEDURAL shake above amp {1} (need >=10) -- the request never reaches the camera; calm jitter mean {2:g4} over {3} frames, {4} ICE-shot frames skipped, {5} cut samples dropped" -f $liShakeN, $KF_MIN_AMP, $lfCalm, $liCalmN, $liIce, $liCuts) }
         }
         $lfShake = $lfShakeSum / $liShakeN
         $lfRatio = if ($lfCalm -gt 1e-9) { $lfShake / $lfCalm } else { [double]::PositiveInfinity }
         $ok = ($lfShake -gt 1e-4) -and ($lfRatio -ge 3.0)
         return @{ Pass = $ok
                   Detail = ("cut-free fwd 2nd-difference mean: procedural-shake {0:g4} over {1} frames vs calm {2:g4} over {3} frames -> ratio {4:g4} (want >= 3 and shaking > 1e-4); {5} ICE-shot frames skipped, {6} cut samples dropped" -f $lfShake, $liShakeN, $lfCalm, $liCalmN, $lfRatio, $liIce, $liCuts) }
       } }
  )
}
