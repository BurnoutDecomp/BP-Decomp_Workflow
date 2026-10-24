# gui_six_posts_batch_playability -- PASS (Checked renderer and GUI candidate playability; source=d3ec7d2dd65a37b489d1dbf61a53b9ce030385ee)

Bug: Check frontend, junkyard exit, rendered world and sustained movement before any candidate delivery.

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_gui_six_posts_20261024\run`  exe 4ebe1a82b1ee (b5=d3ec7d2d) 2026-10-24T12:31:24.9738815+02:00  b5 b3300e0e8  parent cc54c12e
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=True

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no NEW assert families | 0 assert family(ies), all known (0 lines) |
| PASS | assert lines (info: known noise counts too) | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 200] |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | reached DRIVING | final phase DRIVING, want DRIVING |
| PASS | the car moved (teleport seat -> first respawn, > 20 m) | path=236,6m net=234,7m samples 38..141 teleported=True later respawns=0 |
| PASS | info: GAMEWRECKED hud messages (gameplay, never fails) | 1 line(s) match /STARTING MESSAGE NAMED "GAMEWRECKED/, want [-inf, +inf] |
| PASS | final world frame has scene variation | lum_std(last) on bb_006900.bmp region 0.15,0.2,0.85,0.8 = 48,6052, want [8, +inf] |
| PASS | final world frame is visible | lum_mean(last) on bb_006900.bmp region 0.15,0.2,0.85,0.8 = 80,0551, want [12, +inf] |
| PASS | final world frame is not black | dark_frac(last) on bb_006900.bmp region 0.15,0.2,0.85,0.8 = 0,122479, want [-inf, 0.9] |

marks.txt:
```
RUNSTART 2026-10-24T12:33:48.5961218+02:00
PROCESS pid=24152 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_gui_six_posts_20261024\stage\slot\Burnout_PC.exe start=2026-10-24T10:33:48.6190195Z priority=BelowNormal
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_gui_six_posts_20261024\run\frames
flyby    (never)
newprof    11,8s  frame=bb_001500.bmp
ingame     14,8s  frame=bb_002100.bmp
jystart    14,8s  frame=bb_002100.bmp
carsel     20,9s  frame=bb_003000.bmp
livery     23,3s  frame=bb_003300.bmp
accept     24,4s  frame=bb_003600.bmp
exitjy     24,4s  frame=bb_003600.bmp
strfin     24,4s  frame=bb_003600.bmp
END        50,4s  frame=bb_006900.bmp
asserts=0 phase=DRIVING
ASSERT_RELEASE=disabled (NoAssertRelease)
DIAGENV    [-DiagEnv BRN_FRAME_DUMP_MAX=24]
TELEPORT 3040.7,-5.8,-1937.9,180
SWEEP    (none)
SLOT     62061  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_gui_six_posts_20261024\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_playability_gui_six_posts_20261024\stage\data)
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
DRIVE    drove path=236,6m net=234,7m over 104 [motion] samples (samples 38..141: teleport seat up to the first respawn; later respawns=0 GAMEWRECKED=1)
POLL     max period 0,72s at 50,4s over 162 polls (target 0.25s)
THROTTLE first input at t+0,11s (on time)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 2% of the log
GAS      52 of 142 [motion] samples report gas > 0
drive=True steer=none delay=6,0s hold=to-end
title-start tap:Start run=9,3s actions=8+45
input accel/none           run=  30,5s t+  0,11s
```
