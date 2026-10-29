# props_physical_native_62140 -- FAIL (props-physical-native-62140)

Run: `C:\Users\adri1\Documents\Codex\props_native_20261029\p26r01\props_physical_native_62140\20261029T203126358Z`  exe 34dd9dad3c53 (b5=00830db6) 2026-10-27T21:24:38.2277801+01:00  b5 ae20985da  parent ae20985da  (b5 tree has 2 uncommitted tracked change(s))
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=False

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no new assert families | 0 assert family(ies), all known (0 lines) |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | native suite reached DRIVING | final phase DRIVING, want DRIVING |
| **FAIL** | exact staged PID/source/runtime/phase-stop handoff | missing exact-process owner, phase-stop or completion receipt |
| PASS | normal game files unchanged | protected normal files unchanged=36/36; changed= |
| **FAIL** | raw native one-target readback and per-site state/frame evidence | required native witness missing: C:\Users\adri1\Documents\Codex\props_native_20261029\p26r01\props_physical_native_62140\20261029T203126358Z\native_alias_batches.json |
| **FAIL** | causal live-object ROI evidence | ROI/native phase evidence missing: C:\Users\adri1\Documents\Codex\props_native_20261029\p26r01\props_physical_native_62140\20261029T203126358Z\native-state-captures.json |

marks.txt:
```
RUNSTART 2026-10-29T21:31:42.5223690+01:00
PROCESS pid=18972 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\props_physical_stage_62140_delta03\slot\Burnout_PC.exe start=2026-10-29T20:31:42.5653590Z priority=inherited
FRAMEDIR C:\Users\adri1\Documents\Codex\props_native_20261029\p26r01\props_physical_native_62140\20261029T203126358Z\frames
flyby      46,3s  frame=-
newprof  (never)
ingame     15,5s  frame=-
jystart    15,5s  frame=-
carsel     55,0s  frame=-
livery     65,7s  frame=-
accept     66,0s  frame=-
exitjy     66,0s  frame=-
strfin     66,0s  frame=-
END       574,7s  frame=bb_043982.bmp
asserts=0 phase=DRIVING
DIAGENV    [-DiagEnv BRN_DEBUG_UI_TRACE=1 BRN_TRAFFIC_DIAG=1 BRN_FRAME_DUMP_REQUEST=1 BRN_FRAME_DUMP_MAX=55 BRN_FRAME_DUMP_ARM=0]
TELEPORT 3040.7,-5.8,-1937.9,180
SWEEP    (none)
SLOT     62140  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\props_physical_stage_62140_delta03\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\props_physical_stage_62140_delta03\data)
CONCURRENT_GAMES allow=True max_other=1
SKIPINTRO -skipvideos (console latch; EA + Criterion logos not played)
TITLESTART requested=False ready-observed=False sent-at=never; stimulus receipt only
ACCEPTGAP boot=1,0s carsel=1,0s  [-AcceptGap 1 -- harness pump latency, not a game gate]
AUDIO    MUTED (BRN_AUDIO_MUTE=1; mastering voice at 0, audio simulation unchanged)
STARTEVT BRN_START_EVENT=1
AIDRIVE  (not armed)
DBGFINISH (not armed)
WINTELE  (not armed)
SHOWTIME not armed
SKIPTIP  BRN_SKIP_TRAINING_TIP=1
EVENTFSM BRN_EVENT_FSM=1
e-junc   (never)
e-case20 (never)
e-start  (never)
e-count  (never)
e-inprog (never) CUE UNVERIFIED -- nothing in the tree prints this text yet, so this
         line says nothing about the game. See the ladder banner.
LADDER   0/5 deepest=none startevent=True  BLIND(BRN_PROP_DIAG unset -- the [evt-flow] rungs cannot print)
CRASHARM crashEntry=always(flag deleted 2026-08-27) crashPlayer=0 deformTrace=0
EXIT     harness-stop (process was still alive)
DRIVE    n/a (not a -Drive run)
POLL     max period 3,56s at 559,0s over 1012 polls (target 0.25s)  *** THE HARNESS POLL LOOP WAS STARVED -- every scheduled input in this run is late by up to that much ***
THROTTLE n/a (not a -Drive run)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 0% of the log
GAS      n/a (no -MotionProbe, so the game's own throttle witness is absent)
drive=False steer=none delay=6,0s hold=to-end
```
