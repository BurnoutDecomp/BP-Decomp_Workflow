# environment24_cloud_layers_irradiance_channels_62180 -- FAIL (Environment24 bounded restorable controls; private source32; stationary PNR;76frame cap640x360;64MiB log; RootV8 normal41 guard and V5 concurrency)

Bug: Twenty-four pending original cloud and irradiance controls need separate native consumer positive/negative/restore witnesses.

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_remainder\run_62180_game01`  exe 474ba5bb1a72 (b5=abbc9047) 2026-10-29T10:12:42.4038115+01:00  b5 d85e2d5e2  parent a0123c9c5  (b5 tree has 4 uncommitted tracked change(s))
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=False

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no new assertions | 0 assert family(ies), all known (0 lines) |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | normal title route reached DRIVING | final phase DRIVING, want DRIVING |
| **FAIL** | exact selected restorable controls native P/N/R and cleanup complete; pixels require independent review | status=fail frames=34 phases=34 site_credit=0 |

marks.txt:
```
RUNSTART 2026-10-29T20:37:49.1632742+01:00
PROCESS pid=72668 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_remainder\stage\slot\Burnout_PC.exe start=2026-10-29T19:37:49.1862790Z priority=inherited
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_remainder\run_62180_game01\frames
flyby    (never)
newprof    14,5s  frame=-
ingame     16,3s  frame=-
jystart    16,3s  frame=-
carsel     23,0s  frame=-
livery     27,8s  frame=-
accept     28,9s  frame=-
exitjy     28,9s  frame=-
strfin     28,9s  frame=-
END       240,1s  frame=bb_032440.bmp
asserts=0 phase=DRIVING
ASSERT_RELEASE=disabled (NoAssertRelease)
DIAGENV    [-DiagEnv BRN_DEBUG_UI_TRACE=1 BRN_FRAME_DUMP_REQUEST=1 BRN_FRAME_DUMP_MAX=76]
TELEPORT (none)
SWEEP    (none)
SLOT     62180  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_remainder\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_remainder\stage\data)
CONCURRENT_GAMES allow=True max_other=1
SKIPINTRO -skipvideos (console latch; EA + Criterion logos not played)
TITLESTART requested=True ready-observed=True sent-at=9,6s; stimulus receipt only
ACCEPTGAP boot=1,0s carsel=1,0s  [-AcceptGap 1 -- harness pump latency, not a game gate]
AUDIO    MUTED (BRN_AUDIO_MUTE=1; mastering voice at 0, audio simulation unchanged)
STARTEVT (not armed)
AIDRIVE  (not armed)
DBGFINISH (not armed)
WINTELE  (not armed)
SHOWTIME not armed
SKIPTIP  (not armed)
EVENTFSM (not armed)
e-junc   (never)
e-case20 (never)
e-start  (never)
e-count  (never)
e-inprog (never) CUE UNVERIFIED -- nothing in the tree prints this text yet, so this
         line says nothing about the game. See the ladder banner.
LADDER   0/5 deepest=none startevent=False  BLIND(BRN_PROP_DIAG unset -- the [evt-flow] rungs cannot print)
CRASHARM crashEntry=always(flag deleted 2026-08-27) crashPlayer=0 deformTrace=0
EXIT     harness-stop (process was still alive)
DRIVE    drove path=101,8m net=99,2m over 846 [motion] samples (samples 49..894: last placement before the throttle up to the first respawn; later respawns=0 GAMEWRECKED=0)
POLL     max period 1,55s at 4,5s over 592 polls (target 0.25s)
THROTTLE first input at t+0,24s (on time)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 0% of the log
GAS      20 of 895 [motion] samples report gas > 0
drive=True steer=none delay=2,0s hold=to-end
throttlescript 0:accel,6:brake+handbrake
title-start tap:Start run=9,6s actions=8+45
input accel/none           run=  31,1s t+  0,24s
input brake+handbrake/none run=  36,4s t+  6,66s
```
