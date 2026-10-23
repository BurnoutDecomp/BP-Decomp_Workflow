# edca_renderer_gui_batch_playability -- PASS (Checked renderer and GUI candidate playability; source=edca934dc502f71f64ad873cdd386afe5e3eeeb2)

Bug: Check frontend, junkyard exit, rendered world and sustained movement before any candidate delivery.

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_reflection_fix_20261024\run`  exe 0c55f39a7a5c (b5=edca934d) 2026-10-24T00:46:36.5380296+02:00  b5 b3300e0e8  parent cc54c12e
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=True

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no NEW assert families | 0 assert family(ies), all known (0 lines) |
| PASS | assert lines (info: known noise counts too) | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 200] |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | reached DRIVING | final phase DRIVING, want DRIVING |
| PASS | the car moved (teleport seat -> first respawn, > 20 m) | path=234,7m net=234,3m samples 52..141 teleported=True later respawns=0 |
| PASS | info: GAMEWRECKED hud messages (gameplay, never fails) | 1 line(s) match /STARTING MESSAGE NAMED "GAMEWRECKED/, want [-inf, +inf] |
| PASS | final world frame has scene variation | lum_std(last) on bb_005100.bmp region 0.15,0.2,0.85,0.8 = 66,5837, want [8, +inf] |
| PASS | final world frame is visible | lum_mean(last) on bb_005100.bmp region 0.15,0.2,0.85,0.8 = 110,689, want [12, +inf] |
| PASS | final world frame is not black | dark_frac(last) on bb_005100.bmp region 0.15,0.2,0.85,0.8 = 0,0901073, want [-inf, 0.9] |

marks.txt:
```
RUNSTART 2026-10-24T00:54:14.6739035+02:00
PROCESS pid=21916 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_reflection_fix_20261024\stage\slot\Burnout_PC.exe start=2026-10-23T22:54:14.6991817Z priority=BelowNormal
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_reflection_fix_20261024\run\frames
flyby    (never)
newprof    11,7s  frame=bb_001500.bmp
ingame     14,7s  frame=bb_002100.bmp
jystart    15,0s  frame=bb_002100.bmp
carsel     21,5s  frame=bb_002400.bmp
livery     26,2s  frame=bb_002700.bmp
accept     27,9s  frame=bb_002700.bmp
exitjy     27,9s  frame=bb_002700.bmp
strfin     27,9s  frame=bb_002700.bmp
END        50,4s  frame=bb_005100.bmp
asserts=0 phase=DRIVING
ASSERT_RELEASE=disabled (NoAssertRelease)
DIAGENV    [-DiagEnv BRN_FRAME_DUMP_MAX=24]
TELEPORT 3040.7,-5.8,-1937.9,180
SWEEP    (none)
SLOT     62059  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_reflection_fix_20261024\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_reflection_fix_20261024\stage\data)
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
DRIVE    drove path=234,7m net=234,3m over 90 [motion] samples (samples 52..141: teleport seat up to the first respawn; later respawns=0 GAMEWRECKED=1)
POLL     max period 1,08s at 47,6s over 146 polls (target 0.25s)
THROTTLE first input at t+0,25s (on time)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 4% of the log
GAS      45 of 142 [motion] samples report gas > 0
drive=True steer=none delay=6,0s hold=to-end
title-start tap:Start run=9,3s actions=8+45
input accel/none           run=  34,1s t+  0,25s
```
