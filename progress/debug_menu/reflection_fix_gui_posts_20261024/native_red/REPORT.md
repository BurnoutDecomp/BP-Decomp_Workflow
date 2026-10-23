# ea5_renderer_gui_batch_playability -- FAIL (Checked renderer and GUI candidate playability; source=ea5ce572baedd4ad8918f6d5bfcdfd756250d411)

Bug: Check frontend, junkyard exit, rendered world and sustained movement before any candidate delivery.

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_ea5_20261024\run`  exe da209c90da27 (b5=ea5ce572) 2026-10-24T00:16:24.6035758+02:00  b5 b3300e0e8  parent cc54c12e
Phase: BOOT  asserts=0  flow_exit=1  expected=PASS  as_expected=False

| verdict | check | detail |
|---|---|---|
| **FAIL** | original strict flow completed and owned game exited | original flow_exit=1 success=False assert_stop=False foreign_game=True cleanup=True |
| PASS | no NEW assert families | 0 assert family(ies), all known (0 lines) |
| PASS | assert lines (info: known noise counts too) | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 200] |
| **FAIL** | no exceptions | 1 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| **FAIL** | reached DRIVING | final phase BOOT, want DRIVING |
| **FAIL** | the car moved (teleport seat -> first respawn, > 20 m) | path=3,1m net=3,1m samples 0..11 teleported=False later respawns=0 |
| PASS | info: GAMEWRECKED hud messages (gameplay, never fails) | 0 line(s) match /STARTING MESSAGE NAMED "GAMEWRECKED/, want [-inf, +inf] |
| **FAIL** | final world frame has scene variation | lum_std(last) on bb_002400.bmp region 0.15,0.2,0.85,0.8 = 0, want [8, +inf] |
| **FAIL** | final world frame is visible | lum_mean(last) on bb_002400.bmp region 0.15,0.2,0.85,0.8 = 0, want [12, +inf] |
| **FAIL** | final world frame is not black | dark_frac(last) on bb_002400.bmp region 0.15,0.2,0.85,0.8 = 1, want [-inf, 0.9] |

marks.txt:
```
RUNSTART 2026-10-24T00:22:20.4401211+02:00
PROCESS pid=12432 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_ea5_20261024\stage\slot\Burnout_PC.exe start=2026-10-23T22:22:20.4648448Z priority=BelowNormal
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_ea5_20261024\run\frames
flyby    (never)
newprof    11,7s  frame=bb_001500.bmp
ingame     14,6s  frame=bb_002100.bmp
jystart    14,8s  frame=bb_002100.bmp
carsel   (never)
livery   (never)
accept   (never)
exitjy   (never)
strfin   (never)
END        19,3s  frame=bb_002400.bmp
asserts=0 phase=BOOT
ASSERT_RELEASE=disabled (NoAssertRelease)
FOREIGN_GAME=appeared-or-process-enumeration-failed; only owned process cleanup attempted
DIAGENV    [-DiagEnv BRN_FRAME_DUMP_MAX=24]
TELEPORT 3040.7,-5.8,-1937.9,180
SWEEP    (none)
SLOT     62058  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_ea5_20261024\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_ea5_20261024\stage\data)
SKIPINTRO -skipvideos (console latch; EA + Criterion logos not played)
TITLESTART requested=True ready-observed=True sent-at=9,3s; stimulus receipt only
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
DRIVE    *** THE CAR NEVER MOVED *** path=3,1m net=3,1m over 12 [motion] samples (samples 0..11: last placement before the throttle up to the first respawn; later respawns=0 GAMEWRECKED=0)  -- but see THROTTLE: THE STIMULUS DID NOT HAPPEN, so this measured nothing
POLL     max period 0,89s at 16,8s over 57 polls (target 0.25s)
THROTTLE *** THE THROTTLE WAS NEVER APPLIED -- the run never reached the schedule, so it measured NOTHING. This run is VOID. ***
SIMPAUSE 1 pause(s), 1 resume(s); first pause at 29% of the log
GAS      0 of 12 [motion] samples report gas > 0
drive=True steer=none delay=6,0s hold=to-end
title-start tap:Start run=9,3s actions=8+45
```
