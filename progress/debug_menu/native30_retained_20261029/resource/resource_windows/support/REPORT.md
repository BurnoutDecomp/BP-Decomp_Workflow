# resource_windows_native_62144 -- PASS

Bug: Heap, Histogram, Type Stats, and Bundle Window effects must be visible and restore. Texture, queue, and partial-fixup actions are excluded from this old-34dd run.

Run: `D:\r21v9\suites\resource_windows\runs\resource_windows_20261029_184609`  exe 34dd9dad3c53 (b5=00830db6) 2026-10-27T21:24:38.2277801+01:00  b5 ae20985da  parent ae20985da  (b5 tree has 2 uncommitted tracked change(s))
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=True

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no new assert families | 0 assert family(ies), all known (0 lines) |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | reached DRIVING | final phase DRIVING, want DRIVING |
| PASS | native resource driver completed with owner-bound frames | status=complete; frames=20; selected-pool=OpenWorldGr |

marks.txt:
```
RUNSTART 2026-10-29T20:32:52.1797524+01:00
PROCESS pid=24996 image=D:\r21v9\suites\resource_windows\stage\resource_windows_20261029_184609\slot\Burnout_PC.exe start=2026-10-29T19:32:52.7839459Z priority=inherited
FRAMEDIR D:\r21v9\suites\resource_windows\runs\resource_windows_20261029_184609\frames
flyby    (never)
newprof    13,6s  frame=bb_001662.bmp
ingame     15,5s  frame=bb_001662.bmp
jystart    15,5s  frame=bb_001662.bmp
carsel     21,8s  frame=bb_002784.bmp
livery     26,4s  frame=bb_002784.bmp
accept     27,5s  frame=bb_003370.bmp
exitjy     27,5s  frame=bb_003370.bmp
strfin     27,5s  frame=bb_003370.bmp
END        92,4s  frame=bb_008358.bmp
asserts=0 phase=DRIVING
DIAGENV    [-DiagEnv BRN_DEBUG_UI_TRACE=1 BRN_FRAME_DUMP_REQUEST=1 BRN_FRAME_DUMP_MAX=48]
TELEPORT (none)
SWEEP    (none)
SLOT     62144  exe=D:\r21v9\suites\resource_windows\stage\resource_windows_20261029_184609\slot\Burnout_PC.exe (a copy; cwd=D:\r21v9\suites\resource_windows\stage\resource_windows_20261029_184609\data)
CONCURRENT_GAMES allow=True max_other=0
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
DRIVE    *** THE CAR NEVER MOVED *** path=3,9m net=3,8m over 46 [motion] samples (samples 0..45: last placement before the throttle up to the first respawn; later respawns=1 GAMEWRECKED=0)  -- but see GAS: THE PRESS NEVER REACHED THE CAR (mfGas 0 on every sample). VOID.
POLL     max period 1,52s at 82,3s over 225 polls (target 0.25s)
THROTTLE first input at t+0,00s (on time)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 2% of the log
GAS      0 of 306 [motion] samples report gas > 0  *** THE THROTTLE NEVER REACHED THE GAME -- the harness held accel and the car's own mfGas stayed 0 ***
drive=True steer=none delay=0,0s hold=to-end
throttlescript 0:brake+handbrake
title-start tap:Start run=9,3s actions=8+45
input brake+handbrake/none run=  27,5s t+  0,00s
```
