# occlusion_targeted_037_off_on_off -- FAIL (Original world-opaque occlusion off/on/off; source=037deb9fecff882de2e2fb55de020e0f54348360)

Bug: The original world-opaque query and conditional-draw chain must consume the live debug controls and preserve the ordinary world image when restored.

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_targeted_037_native_20261024\run`  exe 5b44650ea619 (b5=037deb9f) 2026-10-24T14:04:50.4412987+02:00  b5 053e953f0  parent e68b398e7
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=False

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no new assert families | 0 assert family(ies), all known (0 lines) |
| PASS | zero assertions | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 0] |
| PASS | actual renderer startup resource ownership | 8 retained immediate pairs; 3 dispatch owners; actual member list/bank31 and equal heap owners; owned 2066/118 sky; one canonical completion |
| PASS | no game exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | ordinary free-roam phase reached | final phase DRIVING, want DRIVING |
| **FAIL** | complete off-on-off query and retained-frame evidence | debug-key helper did not complete the bounded sequence \| expected 5 actual OccEnabled readbacks, observed 0 \| expected 5 actual OccWorld readbacks, observed 0 \| targeted component/alias/script lookup failed \| no live [occ-state] enabled=1 ready=1 world_opaque=1 witness \| no off/on/off state transition was recorded by the renderer \| no complete pre-cap list-11 frame with total>64, contiguous 64-index query/draw cursors, and final -1 \| no same-batch, same-id/serial ended + S_OK result + decision provider triple for a selected list-11 frame \| missing helper phase boundary note baseline-start \| missing helper phase boundary note baseline-end \| missing helper phase boundary note enabled-start \| missing helper phase boundary note enabled-end \| missing helper phase boundary note restored-start \| missing helper phase boundary note restored-end \| missing retained phase image(s): baseline.bmp, enabled.bmp, restored.bmp \| actual alias values: initial observed, baseline=off, enabled+ready=on, restored=off; frames=43/96 \| no complete selected list11 frame \| no provider result/decision triple \| retained images= \| manual pixel inspection remains required; D3D9 query polarity is not Xenos parity |

marks.txt:
```
RUNSTART 2026-10-24T14:17:01.9140489+02:00
PROCESS pid=59420 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_targeted_037_native_20261024\stage\slot\Burnout_PC.exe start=2026-10-24T12:17:01.9331618Z priority=BelowNormal
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_targeted_037_native_20261024\run\frames
flyby    (never)
newprof    11,6s  frame=bb_001500.bmp
ingame     13,4s  frame=bb_002100.bmp
jystart    13,4s  frame=bb_002100.bmp
carsel     20,1s  frame=bb_003000.bmp
livery     22,6s  frame=bb_003300.bmp
accept     23,7s  frame=bb_003300.bmp
exitjy     23,7s  frame=bb_003300.bmp
strfin     23,7s  frame=bb_003300.bmp
END       129,6s  frame=bb_012600.bmp
asserts=0 phase=DRIVING
ASSERT_RELEASE=disabled (NoAssertRelease)
DIAGENV    [-DiagEnv BRN_OCCLUSION_DIAG=1 BRN_FRAME_DUMP_MAX=96 BRN_RENDER_PREPARE_DIAG=1]
TELEPORT (none)
SWEEP    (none)
SLOT     62063  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_targeted_037_native_20261024\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_targeted_037_native_20261024\stage\data)
SKIPINTRO -skipvideos (console latch; EA + Criterion logos not played)
TITLESTART requested=True ready-observed=True sent-at=8,0s; stimulus receipt only
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
EXIT     self  code=0 (0x00000000)
DRIVE    n/a (not a -Drive run)
POLL     max period 1,05s at 36,6s over 368 polls (target 0.25s)
THROTTLE n/a (not a -Drive run)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 1% of the log
GAS      n/a (no -MotionProbe, so the game's own throttle witness is absent)
drive=False steer=none delay=6,0s hold=to-end
title-start tap:Start run=8,0s actions=8+45
```
