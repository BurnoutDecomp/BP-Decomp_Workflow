# clean_minimap_boot_drive_62188 -- PASS (clean reviewed minimap boot/drive regression)

Bug: Console byte capacity for bank66 exhausted on widened native Flapt arrays

Run: `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\minimap_regression_20261030\native_clean_62188\runs\fixed_62188_f055af4fd49241aa823a301322926a8c`  exe 39b62961b592 (b5=3f4f9c06) 2026-10-31T00:19:00.5071060+01:00  b5 e3d773c6c  parent 1897884e8  (b5 tree has 4 uncommitted tracked change(s))
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=True

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no NEW assert families | 0 assert family(ies), all known (0 lines) |
| PASS | assert lines (info: known noise counts too) | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 0] |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | reached DRIVING | final phase DRIVING, want DRIVING |
| PASS | the car moved (teleport seat -> first respawn, > 20 m) | path=234,7m net=233,6m samples 43..129 teleported=True later respawns=0 |
| PASS | info: GAMEWRECKED hud messages (gameplay, never fails) | 1 line(s) match /STARTING MESSAGE NAMED "GAMEWRECKED/, want [-inf, +inf] |
| PASS | actual GameData GameTalk owner completed startup exactly once | 1 line(s) match /\[GameData\] GameTalk ready owner=[0-9A-Fa-fx]+ manager=[0-9A-Fa-fx]+/, want [1, 1] |
| PASS | real owner and real singleton existed before GUI registration | owner=00007FF73B294CF8 singleton=000000001A1BA650 readyAt=8639 guiAt=24786 |
| PASS | no repeat of first native GUI registration exception | 0 line(s) match /\[EXCEPTION\]\|GameTalkManager::RegisterMessageHandler \+.*\[rva/, want [-inf, 0] |
| PASS | real FLApt root finished within the native owner | 1 line(s) match /FLApt: allocated (948656\|958000)b runtime data for file/, want [1, 1] |
| PASS | actual current profile load | actual profile load pass=True |

marks.txt:
```
RUNSTART 2026-10-31T00:19:06.2639177+01:00
PROCESS pid=22552 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\minimap_regression_20261030\native_clean_62188\fixed\stage\slot\Burnout_PC.exe start=2026-10-30T23:19:06.2781125Z priority=inherited
FRAMEDIR D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\minimap_regression_20261030\native_clean_62188\runs\fixed_62188_f055af4fd49241aa823a301322926a8c\frames
flyby    (never)
newprof    26,7s  frame=-
ingame     29,3s  frame=-
jystart    29,3s  frame=-
carsel     35,8s  frame=-
livery     38,5s  frame=-
accept     40,2s  frame=-
exitjy     40,2s  frame=-
strfin     40,2s  frame=-
END        61,9s  frame=bb_006651.bmp
asserts=0 phase=DRIVING
DIAGENV    [-DiagEnv BRN_FRAME_DUMP_REQUEST=1 BRN_FRAME_DUMP_MAX=5]
TELEPORT 3040.7,-5.8,-1937.9,180
SWEEP    (none)
SLOT     62188  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\minimap_regression_20261030\native_clean_62188\fixed\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\minimap_regression_20261030\native_clean_62188\fixed\stage\data)
CONCURRENT_GAMES allow=True max_other=0
SKIPINTRO (not armed)
TITLESTART requested=True ready-observed=True sent-at=23,3s; stimulus receipt only
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
DRIVE    drove path=234,7m net=233,6m over 87 [motion] samples (samples 43..129: teleport seat up to the first respawn; later respawns=0 GAMEWRECKED=1)
POLL     max period 0,90s at 43,0s over 185 polls (target 0.25s)
THROTTLE first input at t+0,16s (on time)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 4% of the log
GAS      42 of 130 [motion] samples report gas > 0
drive=True steer=none delay=6,0s hold=24s
steerscript    0:none,8:left25,10:none,19:right25,21:none
title-start tap:Start run=23,3s actions=8+45
input accel/none           run=  46,4s t+  0,16s
input accel/left25         run=  54,4s t+  8,21s
input accel/none           run=  56,3s t+ 10,07s
```
