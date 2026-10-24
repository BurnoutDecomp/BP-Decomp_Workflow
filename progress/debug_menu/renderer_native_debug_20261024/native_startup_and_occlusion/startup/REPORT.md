# native_renderer_startup_ownership_playability -- PASS (Checked renderer and GUI candidate playability; source=037deb9fecff882de2e2fb55de020e0f54348360)

Bug: Check frontend, junkyard exit, rendered world and sustained movement before any candidate delivery.

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_native_renderer_startup_20261024\run`  exe 5b44650ea619 (b5=037deb9f) 2026-10-24T14:04:50.4412987+02:00  b5 053e953f0  parent e68b398e7
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=True

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no NEW assert families | 0 assert family(ies), all known (0 lines) |
| PASS | assert lines (info: known noise counts too) | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 200] |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | reached DRIVING | final phase DRIVING, want DRIVING |
| PASS | the car moved (teleport seat -> first respawn, > 20 m) | path=236,8m net=234,7m samples 38..143 teleported=True later respawns=0 |
| PASS | info: GAMEWRECKED hud messages (gameplay, never fails) | 1 line(s) match /STARTING MESSAGE NAMED "GAMEWRECKED/, want [-inf, +inf] |
| PASS | final world frame has scene variation | lum_std(last) on bb_006900.bmp region 0.15,0.2,0.85,0.8 = 68,359, want [8, +inf] |
| PASS | final world frame is visible | lum_mean(last) on bb_006900.bmp region 0.15,0.2,0.85,0.8 = 117,838, want [12, +inf] |
| PASS | final world frame is not black | dark_frac(last) on bb_006900.bmp region 0.15,0.2,0.85,0.8 = 0,104585, want [-inf, 0.9] |
| PASS | zero startup/gameplay assertions | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 0] |
| PASS | actual renderer startup resource ownership | 8 retained immediate pairs; 3 dispatch owners; actual member list/bank31 and equal heap owners; owned 2066/118 sky; one canonical completion |

marks.txt:
```
RUNSTART 2026-10-24T14:10:45.6815895+02:00
PROCESS pid=33424 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_native_renderer_startup_20261024\stage\slot\Burnout_PC.exe start=2026-10-24T12:10:45.6969432Z priority=BelowNormal
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_native_renderer_startup_20261024\run\frames
flyby    (never)
newprof    11,5s  frame=bb_001500.bmp
ingame     13,4s  frame=bb_002100.bmp
jystart    13,4s  frame=bb_002100.bmp
carsel     20,0s  frame=bb_003000.bmp
livery     22,5s  frame=bb_003300.bmp
accept     23,6s  frame=bb_003300.bmp
exitjy     23,6s  frame=bb_003300.bmp
strfin     23,6s  frame=bb_003300.bmp
END        50,0s  frame=bb_006900.bmp
asserts=0 phase=DRIVING
ASSERT_RELEASE=disabled (NoAssertRelease)
DIAGENV    [-DiagEnv BRN_FRAME_DUMP_MAX=24 BRN_RENDER_PREPARE_DIAG=1]
TELEPORT 3040.7,-5.8,-1937.9,180
SWEEP    (none)
SLOT     62062  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_native_renderer_startup_20261024\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\candidate_native_renderer_startup_20261024\stage\data)
SKIPINTRO -skipvideos (console latch; EA + Criterion logos not played)
TITLESTART requested=True ready-observed=True sent-at=7,9s; stimulus receipt only
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
DRIVE    drove path=236,8m net=234,7m over 106 [motion] samples (samples 38..143: teleport seat up to the first respawn; later respawns=0 GAMEWRECKED=1)
POLL     max period 0,99s at 44,5s over 146 polls (target 0.25s)
THROTTLE first input at t+0,02s (on time)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 2% of the log
GAS      52 of 144 [motion] samples report gas > 0
drive=True steer=none delay=6,0s hold=to-end
title-start tap:Start run=7,9s actions=8+45
input accel/none           run=  29,6s t+  0,02s
```
