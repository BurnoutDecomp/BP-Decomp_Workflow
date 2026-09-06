# input_pad_coverage -- "a few controls are missing on the controller, although the features exist"
#
# THE ORACLE IS THE CONSOLE'S OWN TABLE, not taste. gaDefaultGameInputMapping (the control ->
# action map every X360 port is loaded with) lives at 0x82CDBEB8 in the image; the argument
# BrnGame::BrnGameModule::PrepareInitialInputMapping @0x823BCF40 hands to PostMappingRequest.
# tools\tests\offline\input_mapping_coverage.py decodes those 28 x 4 signed bytes and diffs
# them against what THIS BUILD says it binds -- the `[input-map] control <n> <NAME> -> actions
# a,b,c,d` lines CgsInputPadsPC.cpp prints once at input bring-up under BRN_INPUT_MAP_DUMP=1.
#
# RED (pre-fix): the build prints no [input-map] lines at all, so the script falls back to a
# static parse of the old per-action KA_BINDINGS pad columns and the failure detail NAMES the
# missing bindings -- measured 29 player-visible ones (LOOKBACK on L1, RESET on R1, map zoom on
# L2, event inspect on R2, the three GUI_OPTION rows, GUI_CANCEL on Back, both thumb clicks,
# DIRTY_TRICK, GUI_LEFT/RIGHT on the dpad, menu nav on the left stick, ...).
# GREEN (post-fix): 28 [input-map] lines that equal the image table exactly.
# * The static fallback also covers the post-fix shape (it reads the in-source
# KA_DEFAULT_GAME_INPUT_MAPPING when that is present), so running the script with no log still
# reports whether the transcription matches the image -- it just cannot be GREEN without the
# runtime dump, on purpose: only the built exe's own words grade a build.
#
# The run itself is deliberately cheap: the dump fires on the first input update, long before
# car select, so this case never needs to reach DRIVING. Eleven lanes share one box.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case input_pad_coverage -ExpectFail -Label pre-fix
#
# ⭐⭐ SHORTENED 2026-09-06 (lane harness2). WHAT CHANGED AND WHAT DID NOT.
#   The Run block below now carries `SkipIntro` and `AcceptGap`, and a smaller `MaxSeconds`.
#   Nothing else about the scenario moved and NO CHECK was touched.
#     SkipIntro  passes the CONSOLE's own "-skipvideos" command-line latch (BrnMain.cpp:434 ->
#                BootVideos::Update's soft-reboot exit) so the EA-Franchise and Criterion VP6
#                logos are not played. It is not a harness bypass and it is not new game code.
#     AcceptGap  is HARNESS latency, not a game gate: the Accept pump used to press every 3.0 s
#                at car select, and the junkyard leg of a returning boot was measurably two
#                consecutive pump periods long (carsel 16.5s -> livery 19.9s -> accept 23.0s).
#   MEASURED, same build, same scenario: boot-to-DRIVING 23.0 s -> 16.2 s.
#   MaxSeconds is cut by that saving plus the slack this case's own schedule shows it never used.
#   This case never leaves the boot: its oracle is the one-shot [input-map] dump. 30 s is the
#   boot plus a margin, not a driving budget.
#
@{
  Name    = 'input_pad_coverage'
  Area    = 'input'
  Bug     = 'bug-test wave 2026-09-06, lane input -- a few controls are missing on the controller, although the features exist'
  Frames  = $false
  Run     = @{ MaxSeconds = 30; SkipIntro = $true; AcceptGap = 1.0 }
  DiagEnv = 'BRN_INPUT_MAP_DUMP=1'
  Checks  = @(
    @{ Kind = 'Script'; Name = 'PC pad binds what the console pad binds'; Script = {
        param($ctx)
        # Walk up from the run dir to the repo root (runs live at
        # <root>\scratch\bugtest\runs\<case>\<ts>, but -RunDir can put them anywhere).
        $py = $null
        $dir = Get-Item $ctx.RunDir
        while ($dir -and -not $py) {
          $cand = Join-Path $dir.FullName 'tools\tests\offline\input_mapping_coverage.py'
          if (Test-Path $cand) { $py = $cand } else { $dir = $dir.Parent }
        }
        if (-not $py) { return @{ Pass = $false; Detail = 'tools\tests\offline\input_mapping_coverage.py not found above the run dir' } }
        $env:PYTHONIOENCODING = 'utf-8'
        $out = & py -3 $py --log $ctx.Log 2>&1
        $code = $LASTEXITCODE
        $outPath = Join-Path $ctx.RunDir 'input_mapping_coverage.txt'
        ($out | Out-String) | Set-Content $outPath -Encoding UTF8
        $line = @($out | Where-Object { "$_" -match '^RESULT:' }) | Select-Object -Last 1
        if (-not $line) { $line = ($out | Select-Object -Last 1) }
        return @{ Pass = ($code -eq 0); Detail = ("{0}  (full diff: {1})" -f "$line", $outPath) }
      } }
    @{ Kind = 'LogCount'; Name = 'the build dumps all 28 pad controls'; Pattern = '\[input-map\] control '; Min = 28 }
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
  )
}
