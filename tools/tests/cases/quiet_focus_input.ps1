# quiet_focus_input -- keys typed in ANOTHER window must not reach the game.
#
# Bug (lane quiet), user's words: "only uses input on the actual window not system wide, so that
# i can scroll on x without it going all over the place".
#
# THE STIMULUS IS REAL, AND IT RUNS ALONGSIDE THE BOOT. GetAsyncKeyState reads GLOBAL key state,
# so the only honest reproduction is to hold real keys down on the desktop while a DIFFERENT
# window owns the foreground -- which has to happen WHILE the game is up, and every Check runs
# after flow_run has returned. The `Setup` block below is the hook for exactly that: run_case
# calls it before the boot and kills whatever it returns if that outlives the run, so this case is
# one ordinary command and works inside a sweep.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case quiet_focus_input
#
# Setup launches tools\tests\offline\quiet_background_keys.ps1 against THIS SLOT's live log. The
# injector arms itself on flow_run's own 'strfin' cue, raises a topmost form so the GAME IS NOT
# FOREGROUND, holds W (accelerate / stick +Y) and A (steer left) for 25 s, releases them, and
# writes a per-200 ms CSV -- into the run's own directory -- of which window really had the
# foreground and whether the keys were really down. Check 7 reads that CSV: a run where the
# stimulus did not happen, or where the game held the foreground anyway, CANNOT be evaluated and
# fails rather than passing.
# It presses REAL KEYS on the desktop for 25 s. They land in the injector's own topmost form,
# which swallows them, and they are released in its finally block.
#
# WHY BRN_INPUT_KEEP_KEYBOARD=1. Since 2026-09-03 the input leaf refuses the host keyboard
# outright whenever BRN_INPUT_ALLOW_BACKGROUND is set -- a blunt instrument that made unattended
# runs safe and made the actual rule untestable, because the keyboard was off for a reason that
# had nothing to do with focus. KEEP_KEYBOARD is the documented escape from that blanket refusal,
# so it is exactly the configuration in which "does the leaf respect the window?" is a question
# with an answer. On the pre-fix build it answers NO: the leaf's focus gate returned "foreground"
# unconditionally under BRN_INPUT_ALLOW_BACKGROUND, so every injected key landed.
#
# WHAT IS MEASURED. Not a new counter -- the CAR. The run does NOT pass -Drive, so nothing in the
# harness ever touches a throttle or steering channel, and the [motion] probe's `gas` and `steer`
# fields are the player's OWN control values as the physics state holds them. If a background key
# reaches the game those two move; if it does not, they stay at zero for the whole run.
#   RED  (pre-fix, 20260906_145815): gas rose to 1.000, steering to 0.393, and the car DROVE
#        20.85 m -- with the game's window present and NOT foreground for 117 of 117 samples.
#   GREEN (post-fix, 20260906_150444): both stay at 0 and the path is 0.16 m, through an identical
#        118-of-118-sample injection.
# Check 8 is the same fact stated as distance, so a reader does not have to trust the field names.
@{
  Name    = 'quiet_focus_input'
  Area    = 'input'
  Bug     = 'lane quiet -- the game reads the keyboard system-wide, so typing in another window drives the test car'
  Frames  = $false
  # Held back from a -Parallel sweep and run alone on slot 0. Its stimulus must own the
  # DESKTOP's foreground, and a Start-Job-spawned process demonstrably cannot: see check 8's
  # banner and run_all.ps1's Solo banner for the measurement.
  Solo    = $true
  Run     = @{
    MaxSeconds  = 70
    SkipIntro   = $true
    AcceptGap   = 1.0
    MotionProbe = $true      # [motion] gas/steer/pos is the whole measurement
    Drive       = $false     # NOTHING in the harness presses anything -- the desktop keys are the only stimulus
  }
  # The documented escape from the blanket harness keyboard refusal; see the banner.
  DiagEnv = 'BRN_INPUT_KEEP_KEYBOARD=1'
  # The concurrent stimulus. See run_case.ps1's Setup banner for the contract; the returned
  # process is killed if it outlives the run (it holds keys for 25 s of a 70 s run, so it always
  # finishes and releases them on its own).
  Setup   = {
    param($ctx)
    $inj = Join-Path $ctx.Root 'tools\tests\offline\quiet_background_keys.ps1'
    Start-Process powershell -PassThru -WindowStyle Minimized -ArgumentList `
      '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $inj,
      '-Keys', 'W,A', '-HoldSeconds', '25', '-ArmDelay', '5',
      '-LogPath', $ctx.GameLog, '-OutCsv', (Join-Path $ctx.RunDir 'bgkeys.csv') `
      -RedirectStandardOutput (Join-Path $ctx.RunDir 'bgkeys.log') `
      -RedirectStandardError  (Join-Path $ctx.RunDir 'bgkeys.err')
  }
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    # The probe has to have produced samples at all, or checks 5/6 are vacuous.
    @{ Kind = 'LogCount'; Name = '[motion] samples exist'; Pattern = '\[motion\] n \d+ pos'; Min = 10 }
    # THE BUG. A background key must not move the throttle...
    # After='strfin' -- the junkyard/car-select podium samples (the first 17 of a run, all before
    # that cue) carry a FROZEN steer of 0.340339 and are not a control reading at all; measured on
    # the RED run 20260906_145134, where they are the only non-zero steer values in 233 samples.
    @{ Kind = 'LogValue'; Name = 'throttle never rose (no background key reached ACCELERATE)';
       After = 'strfin'; Pattern = '\[motion\].* gas (?<g>-?[\d.]+) '; Group = 'g'; Agg = 'all'; Min = -0.001; Max = 0.001 }
    # ...nor the steering.
    @{ Kind = 'LogValue'; Name = 'steering never moved (no background key reached the stick)';
       After = 'strfin'; Pattern = '\[motion\].* steer (?<s>-?[\d.]+) '; Group = 's'; Agg = 'all'; Min = -0.001; Max = 0.001 }
    # THE STIMULUS ACTUALLY HAPPENED, AND IT HAPPENED IN THE BACKGROUND. Without this the case
    # would pass on a run where the injector never started -- the "a stimulus that silently did
    # not happen is worse than no stimulus" failure this harness has already been bitten by.
    @{ Kind = 'Script'; Name = 'the injector held keys down while the game was NOT foreground'; Script = {
        param($ctx)
        # THE CSV IS THIS RUN'S OWN, in this run's directory. An earlier version took the newest
        # bgkeys_*.csv out of a shared scratch dir, which is one stale file away from scoring a
        # run against somebody else's stimulus.
        $csvPath = Join-Path $ctx.RunDir 'bgkeys.csv'
        if (-not (Test-Path $csvPath)) {
          $injLog = Join-Path $ctx.RunDir 'bgkeys.log'
          $why = if (Test-Path $injLog) { (Get-Content $injLog) -join ' | ' } else { 'no bgkeys.log either' }
          return @{ Pass = $false; Detail = "no bgkeys.csv in the run dir -- the Setup stimulus did not run. Injector said: $why" }
        }
        $rows = @(Get-Content $csvPath | Select-Object -Skip 1)
        # Fields: t_ms,fg_hwnd,game_hwnd,form_hwnd,game_is_foreground,keys_down -- all integers or
        # hex, deliberately (a "{0:f2}" here once produced a de-DE decimal COMMA and shifted every
        # index, so the run read as "no key was ever down" with a raw column that said 2).
        $held = @($rows | Where-Object { [int](($_ -split ',')[5]) -gt 0 }).Count
        $fgGame = @($rows | Where-Object { ($_ -split ',')[4] -eq '1' }).Count
        # A background sample only counts when the game's window EXISTS and is not the foreground:
        # game_hwnd 0x0 means the game was not running, which is not a measurement of anything.
        $bgHeld = @($rows | Where-Object { $f = $_ -split ','
                                           [int]$f[5] -gt 0 -and $f[4] -eq '0' -and $f[2] -ne '0x0' }).Count
        $ok = ($bgHeld -ge 20)
        return @{ Pass = $ok; Detail = ("bgkeys.csv: {0} samples, {1} with a key really down, {2} of those with the game's window present and NOT foreground ({3} with the game foreground); want >= 20" -f `
                    $rows.Count, $held, $bgHeld, $fgGame) }
      } }
    # ⭐⭐ THE CROSS-CHECK, AND IT IS NOT REDUNDANT WITH CHECK 7. Check 7 is the INJECTOR's view of
    # the foreground; this is the GAME's, printed by the gate itself. They can disagree, and when
    # they do the run proves nothing: measured 2026-09-06 in a `run_all -Parallel 3` sweep, the
    # injector recorded 118/118 samples with no Burnout window foreground while the game under
    # test logged `focus=1` and never once logged a change -- i.e. one of the two processes was
    # not looking at the desktop the other was on, and the "the car did not move" result was then
    # about a stimulus that never reached the game. A case that cannot see the gate close has not
    # tested the gate.
    # ⛔ CONSEQUENCE: run this case on its OWN (plain `run_case.ps1`), not inside a `-Parallel`
    # sweep, until the Setup process is guaranteed the same desktop as the game.
    @{ Kind = 'LogCount'; Name = 'the game itself saw the focus leave (the gate actually closed)';
       Pattern = '\[input\] focus=0 '; Min = 1 }
    # The same fact as distance, independent of the field names above.
    @{ Kind = 'Script'; Name = 'the car did not move'; Script = {
        param($ctx)
        $mx = [regex]::Matches(($ctx.LogLines -join "`n"), '\[motion\] n \d+ pos (-?[0-9.]+) (-?[0-9.]+) (-?[0-9.]+)')
        if ($mx.Count -lt 2) { return @{ Pass = $false; Detail = "only $($mx.Count) [motion] sample(s)" } }
        $p = @(); foreach ($m in $mx) { $p += ,@([double]$m.Groups[1].Value, [double]$m.Groups[2].Value, [double]$m.Groups[3].Value) }
        $path = 0.0
        for ($i = 1; $i -lt $p.Count; $i++) {
          $d = [math]::Sqrt((($p[$i][0]-$p[$i-1][0]) * ($p[$i][0]-$p[$i-1][0])) +
                            (($p[$i][1]-$p[$i-1][1]) * ($p[$i][1]-$p[$i-1][1])) +
                            (($p[$i][2]-$p[$i-1][2]) * ($p[$i][2]-$p[$i-1][2])))
          if ($d -lt 20.0) { $path += $d }   # a >20 m step is a placement, not driving
        }
        return @{ Pass = ($path -lt 5.0); Detail = ("path={0:f2}m over {1} [motion] samples (want < 5 m)" -f $path, $p.Count) }
      } }
  )
}
