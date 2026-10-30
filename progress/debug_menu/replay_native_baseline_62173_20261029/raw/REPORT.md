# private_replay_source22e6735_boot_profile_world_drive_62173 -- PASS (Private source22e6735 startup baseline; unbypassed EA/Criterion to ordinary title/profile/world/driving; 450s total120s video phase; ten frames; no forced Replay states; normal Source41 protected)

Bug: Console byte capacity for bank66 exhausted on widened native Flapt arrays

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\replay_native_baseline_62173_20261029\run_game01`  exe ccdbfa54ca4f (b5=22e67352) 2026-10-29T21:24:25.8848213+01:00  b5 d85e2d5e2  parent 29374006c  (b5 tree has 4 uncommitted tracked change(s))
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=True

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no NEW assert families | 0 assert family(ies), all known (0 lines) |
| PASS | assert lines (info: known noise counts too) | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 200] |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | reached DRIVING | final phase DRIVING, want DRIVING |
| PASS | the car moved (teleport seat -> first respawn, > 20 m) | path=193,3m net=193,2m samples 50..116 teleported=True later respawns=0 |
| PASS | info: GAMEWRECKED hud messages (gameplay, never fails) | 0 line(s) match /STARTING MESSAGE NAMED "GAMEWRECKED/, want [-inf, +inf] |
| PASS | actual GameData GameTalk owner completed startup exactly once | 1 line(s) match /\[GameData\] GameTalk ready owner=[0-9A-Fa-fx]+ manager=[0-9A-Fa-fx]+/, want [1, 1] |
| PASS | real owner and real singleton existed before GUI registration | owner=00007FF7A6694CF8 singleton=000000001A1BA650 readyAt=5216 guiAt=21363 |
| PASS | no repeat of first native GUI registration exception | 0 line(s) match /\[EXCEPTION\]\|GameTalkManager::RegisterMessageHandler \+.*\[rva/, want [-inf, 0] |
| PASS | real FLApt root finished within the native owner | 1 line(s) match /FLApt: allocated (948656\|958000)b runtime data for file/, want [1, 1] |
| PASS | real main title movie reached legal title-ready state | 1 line(s) match /\[BootLegal\] stage -?\d+ -> 7/, want [1, 1] |
| PASS | real profile serialization returned before BootProfile running | 1 line(s) match /\[BootProfile\] stage 3 -> 4/, want [1, 1] |
| PASS | EA actual decoder prepared | 1 line(s) match /\[Movie\] prepared .*EAFRANCHISE/, want [1, 1] |
| PASS | Criterion actual decoder prepared | 1 line(s) match /\[Movie\] prepared .*CRITERION/, want [1, 1] |
| PASS | video outer event reached movie manager | 0 line(s) match /GUI_OUT_UNEXPECTED.*(508\|509)/, want [-inf, 0] |
| PASS | both ordinary logo510 completions precede the legal title | EA=32288 Criterion=34003 title=42117 510between=1 510afterCriterion=1 |

marks.txt:
```
RUNSTART 2026-10-29T21:45:37.3115785+01:00
PROCESS pid=24664 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\replay_native_baseline_62173_20261029\stage\slot\Burnout_PC.exe start=2026-10-29T20:45:37.3338361Z priority=inherited
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\replay_native_baseline_62173_20261029\run_game01\frames
flyby    (never)
newprof    30,9s  frame=bb_003492.bmp
ingame     32,7s  frame=bb_003492.bmp
jystart    32,7s  frame=bb_003492.bmp
carsel     40,1s  frame=bb_004633.bmp
livery     43,4s  frame=bb_004633.bmp
accept     46,2s  frame=bb_004633.bmp
exitjy     46,2s  frame=bb_004633.bmp
strfin     46,2s  frame=bb_004633.bmp
END        62,9s  frame=bb_006546.bmp
asserts=0 phase=DRIVING
DIAGENV    [-DiagEnv BRN_FRAME_DUMP_REQUEST=1]
TELEPORT 3040.7,-5.8,-1937.9,180
SWEEP    (none)
SLOT     62173  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\replay_native_baseline_62173_20261029\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\replay_native_baseline_62173_20261029\stage\data)
CONCURRENT_GAMES allow=True max_other=0
SKIPINTRO (not armed)
TITLESTART requested=True ready-observed=True sent-at=27,4s; stimulus receipt only
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
DRIVE    drove path=193,3m net=193,2m over 67 [motion] samples (samples 50..116: teleport seat up to the first respawn; later respawns=0 GAMEWRECKED=0)
POLL     max period 2,05s at 5,0s over 131 polls (target 0.25s)  *** THE HARNESS POLL LOOP WAS STARVED -- every scheduled input in this run is late by up to that much ***
THROTTLE *** THE THROTTLE WAS APPLIED 1,32s LATE (schedule t+0) -- the poll loop was starved; treat every timing in this run as unusable. ***
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 4% of the log
GAS      32 of 117 [motion] samples report gas > 0
drive=True steer=none delay=6,0s hold=to-end
title-start tap:Start run=27,4s actions=8+45
input accel/none           run=  51,8s t+  1,32s
```
