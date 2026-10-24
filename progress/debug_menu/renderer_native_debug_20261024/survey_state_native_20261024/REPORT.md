# occlusion_survey_state_off_on_off -- PASS (Original world-opaque occlusion off/on/off; source=3d7db422fd9a96f6891ac81c60370745dd966839)

Bug: The original world-opaque query and conditional-draw chain must consume the live debug controls and preserve the ordinary world image when restored.

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_survey_state_3d7_native_20261024\run`  exe a4cc9c43aaf2 (b5=3d7db422) 2026-10-24T15:46:57.2696130+02:00  b5 053e953f0  parent e68b398e7
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=True

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no new assert families | 0 assert family(ies), all known (0 lines) |
| PASS | zero assertions | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 0] |
| PASS | actual renderer startup resource ownership | 8 retained immediate pairs; 3 dispatch owners; actual member list/bank31 and equal heap owners; owned 2066/118 sky; one canonical completion |
| PASS | no game exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | ordinary free-roam phase reached | final phase DRIVING, want DRIVING |
| PASS | complete off-on-off query and retained-frame evidence | actual alias values: initial observed, baseline=off, enabled+ready=on, restored=off; frames=56/96 \| complete list11 frame=7045 total=4122 chunks=65 final=-1; batch row 65/192 \| same provider id=0 serial=1: result samples=0, decision=0; ordinals ended/result/decision=1/59/60 \| retained images=baseline.bmp,enabled.bmp,restored.bmp \| manual pixel inspection remains required; D3D9 query polarity is not Xenos parity |

marks.txt:
```
RUNSTART 2026-10-24T15:55:28.5729110+02:00
PROCESS pid=24656 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_survey_state_3d7_native_20261024\stage\slot\Burnout_PC.exe start=2026-10-24T13:55:28.5885839Z priority=BelowNormal
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_survey_state_3d7_native_20261024\run\frames
flyby    (never)
newprof    11,9s  frame=bb_001500.bmp
ingame     13,7s  frame=bb_002100.bmp
jystart    13,7s  frame=bb_002100.bmp
carsel     20,3s  frame=bb_002700.bmp
livery     23,2s  frame=bb_003300.bmp
accept     24,2s  frame=bb_003300.bmp
exitjy     24,2s  frame=bb_003300.bmp
strfin     24,2s  frame=bb_003300.bmp
END       180,1s  frame=bb_016500.bmp
asserts=0 phase=DRIVING
ASSERT_RELEASE=disabled (NoAssertRelease)
DIAGENV    [-DiagEnv BRN_OCCLUSION_DIAG=1 BRN_FRAME_DUMP_MAX=96 BRN_RENDER_PREPARE_DIAG=1]
TELEPORT (none)
SWEEP    (none)
SLOT     62066  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_survey_state_3d7_native_20261024\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_survey_state_3d7_native_20261024\stage\data)
SKIPINTRO -skipvideos (console latch; EA + Criterion logos not played)
TITLESTART requested=True ready-observed=True sent-at=8,1s; stimulus receipt only
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
DRIVE    n/a (not a -Drive run)
POLL     max period 1,14s at 118,8s over 498 polls (target 0.25s)
THROTTLE n/a (not a -Drive run)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 1% of the log
GAS      n/a (no -MotionProbe, so the game's own throttle witness is absent)
drive=False steer=none delay=6,0s hold=to-end
title-start tap:Start run=8,1s actions=8+45
```
