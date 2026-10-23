# occlusion_native_edca_off_on_off -- FAIL (Original world-opaque occlusion off/on/off; source=edca934dc502f71f64ad873cdd386afe5e3eeeb2)

Bug: The original world-opaque query and conditional-draw chain must consume the live debug controls and preserve the ordinary world image when restored.

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_native_edca_execution_20261024\run`  exe 0c55f39a7a5c (b5=edca934d) 2026-10-24T00:46:36.5380296+02:00  b5 b3300e0e8  parent cc54c12e
Phase: DRIVING  asserts=0  flow_exit=1  expected=PASS  as_expected=False

| verdict | check | detail |
|---|---|---|
| **FAIL** | original strict flow completed and owned game exited | original flow_exit=1 success=False assert_stop=False foreign_game=True cleanup=True |
| PASS | no new assert families | 0 assert family(ies), all known (0 lines) |
| **FAIL** | no game exceptions | 1 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | ordinary free-roam phase reached | final phase DRIVING, want DRIVING |
| **FAIL** | complete off-on-off query and retained-frame evidence | debug-key helper did not complete the bounded sequence \| baseline.txt does not read back FALSE for Renderer/OcclusionCull/Occlusion enabled \| baseline.txt does not read back FALSE for Renderer/OcclusionCull/Cull world opaque \| enabled.txt does not read back TRUE for Renderer/OcclusionCull/Occlusion enabled \| enabled.txt does not read back TRUE for Renderer/OcclusionCull/Cull world opaque \| enabled-ready.txt does not read back TRUE for Renderer/OcclusionCull/Occlusion enabled \| enabled-ready.txt does not read back TRUE for Renderer/OcclusionCull/Cull world opaque \| restored.txt does not read back FALSE for Renderer/OcclusionCull/Occlusion enabled \| restored.txt does not read back FALSE for Renderer/OcclusionCull/Cull world opaque \| no live [occ-state] enabled=1 ready=1 world_opaque=1 witness \| no off/on/off state transition was recorded by the renderer \| no complete pre-cap list-11 frame with total>64, contiguous 64-index query/draw cursors, and final -1 \| no same-batch, same-id/serial ended + S_OK result + decision provider triple for a selected list-11 frame \| missing helper phase boundary note baseline-end \| missing helper phase boundary note enabled-start \| missing helper phase boundary note enabled-end \| missing helper phase boundary note restored-start \| missing helper phase boundary note restored-end \| missing retained phase image(s): baseline.bmp, enabled.bmp, restored.bmp \| flags: initial/baseline=off, enabled+ready=on, restored=off; frames=11/96 \| no complete selected list11 frame \| no provider result/decision triple \| retained images= \| manual pixel inspection remains required; D3D9 query polarity is not Xenos parity |

marks.txt:
```
RUNSTART 2026-10-24T01:01:04.0079013+02:00
PROCESS pid=28244 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_native_edca_execution_20261024\stage\slot\Burnout_PC.exe start=2026-10-23T23:01:04.0306451Z priority=BelowNormal
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_native_edca_execution_20261024\run\frames
flyby    (never)
newprof    11,7s  frame=bb_001500.bmp
ingame     14,7s  frame=bb_002100.bmp
jystart    15,0s  frame=bb_002100.bmp
carsel     22,3s  frame=bb_002400.bmp
livery     26,0s  frame=bb_002700.bmp
accept     27,7s  frame=bb_002700.bmp
exitjy     27,7s  frame=bb_002700.bmp
strfin     27,7s  frame=bb_002700.bmp
END        38,2s  frame=bb_003000.bmp
asserts=0 phase=DRIVING
ASSERT_RELEASE=disabled (NoAssertRelease)
FOREIGN_GAME=appeared-or-process-enumeration-failed; only owned process cleanup attempted
DIAGENV    [-DiagEnv BRN_OCCLUSION_DIAG=1 BRN_FRAME_DUMP_MAX=96]
TELEPORT (none)
SWEEP    (none)
SLOT     62060  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_native_edca_execution_20261024\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\occlusion_native_edca_execution_20261024\stage\data)
SKIPINTRO -skipvideos (console latch; EA + Criterion logos not played)
TITLESTART requested=True ready-observed=True sent-at=9,2s; stimulus receipt only
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
POLL     max period 0,87s at 11,5s over 113 polls (target 0.25s)
THROTTLE n/a (not a -Drive run)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 10% of the log
GAS      n/a (no -MotionProbe, so the game's own throttle witness is absent)
drive=False steer=none delay=6,0s hold=to-end
title-start tap:Start run=9,2s actions=8+45
```
