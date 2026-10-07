# junkyard_carousel_noprestream -- the A side of junkyard_carousel's A/B (lane CARSEL, GW4).
#
# Same scenario and exe as junkyard_carousel, with BRN_CARSEL_NOPRESTREAM=1: the carousel request
# is still BUILT and logged, but its action-69 post is withheld, so the car change waits on the
# streamer alone. Compare the two with
#   C:\Python310\python.exe tools\tests\tools\CARSEL_carousel_report.py
# which reads every run dir of both cases and prints the per-change secondsSinceRequest.
# Only the floor checks apply here (the pre-stream witnesses are absent by design).
$lCase = & (Join-Path $PSScriptRoot 'junkyard_carousel.ps1')
$lCase.Name    = 'junkyard_carousel_noprestream'
$lCase.Bug     = 'GW4 census #6 A/B -- carousel car change with the action-69 pre-stream withheld'
$lCase.DiagEnv = 'BRN_CARSEL_DIAG=1,BRN_RCEM_ACTION_DIAG=1,BRN_CARSEL_TAPSTEP=1,BRN_CARSEL_NOPRESTREAM=1'
$lCase.Checks  = @($lCase.Checks | Where-Object { $_.Name -match '^no NEW assert|^no exceptions|^reached DRIVING|^both car changes completed' })
$lCase
