# private_source45_boot_profile_world_drive_62185 -- PASS (Source45 unbypassed startup current profile road baseline)

Bug: Console byte capacity for bank66 exhausted on widened native Flapt arrays

Run: `C:\Users\adri1\Documents\Codex\source45_native_20261030\run_62185_87e1a84185c94861bbc8164712a4326a`  exe e0635b4d424d (b5=e3d773c6) 2026-10-30T20:46:49.4742852+01:00  b5 d85e2d5e2  parent 9ad7cf56e  (b5 tree has 4 uncommitted tracked change(s))
Phase: DRIVING  asserts=0  flow_exit=0  expected=PASS  as_expected=True

| verdict | check | detail |
|---|---|---|
| PASS | original strict flow completed and owned game exited | original flow_exit=0 success=True assert_stop=False foreign_game=False cleanup=True |
| PASS | no NEW assert families | 0 assert family(ies), all known (0 lines) |
| PASS | assert lines (info: known noise counts too) | 0 line(s) match /\[ASSERT \d+\]/, want [-inf, 200] |
| PASS | no exceptions | 0 line(s) match /\[EXCEPTION\]/, want [-inf, 0] |
| PASS | reached DRIVING | final phase DRIVING, want DRIVING |
| PASS | the car moved (teleport seat -> first respawn, > 20 m) | path=236,8m net=234,6m samples 41..149 teleported=True later respawns=0 |
| PASS | info: GAMEWRECKED hud messages (gameplay, never fails) | 1 line(s) match /STARTING MESSAGE NAMED "GAMEWRECKED/, want [-inf, +inf] |
| PASS | actual GameData GameTalk owner completed startup exactly once | 1 line(s) match /\[GameData\] GameTalk ready owner=[0-9A-Fa-fx]+ manager=[0-9A-Fa-fx]+/, want [1, 1] |
| PASS | real owner and real singleton existed before GUI registration | owner=00007FF7C9724CF8 singleton=000000001A1BA650 readyAt=8639 guiAt=24786 |
| PASS | no repeat of first native GUI registration exception | 0 line(s) match /\[EXCEPTION\]\|GameTalkManager::RegisterMessageHandler \+.*\[rva/, want [-inf, 0] |
| PASS | real FLApt root finished within the native owner | 1 line(s) match /FLApt: allocated (948656\|958000)b runtime data for file/, want [1, 1] |
| PASS | real main title movie reached legal title-ready state | 1 line(s) match /\[BootLegal\] stage -?\d+ -> 7/, want [1, 1] |
| PASS | real profile serialization returned before BootProfile running | 1 line(s) match /\[BootProfile\] stage 3 -> 4/, want [1, 1] |
| PASS | EA actual decoder prepared | 1 line(s) match /\[Movie\] prepared .*EAFRANCHISE/, want [1, 1] |
| PASS | Criterion actual decoder prepared | 1 line(s) match /\[Movie\] prepared .*CRITERION/, want [1, 1] |
| PASS | video outer event reached movie manager | 0 line(s) match /GUI_OUT_UNEXPECTED.*(508\|509)/, want [-inf, 0] |
| PASS | both ordinary logo510 completions precede the legal title | EA=35782 Criterion=43594 title=45538 510between=1 510afterCriterion=1 |
| PASS | actual current profile progression load | actual profile load pass=True |
| PASS | exact owned startup captures and requested phase stop | 10 owned hash/ACK/phase-bound captures and exact owned phase-stop; labels=drive_8s,drive_15s,car_select,ea_movie_2s,criterion_movie_2s,title_ready,drive_25s,world_exit,ea_movie_5s,profile_ready |

marks.txt:
```
RUNSTART 2026-10-30T20:46:55.7356255+01:00
PROCESS pid=61208 image=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source45_native_62185_20261030\stage\slot\Burnout_PC.exe start=2026-10-30T19:46:55.7559897Z priority=inherited
FRAMEDIR C:\Users\adri1\Documents\Codex\source45_native_20261030\run_62185_87e1a84185c94861bbc8164712a4326a\frames
flyby    (never)
newprof    28,2s  frame=bb_004380.bmp
ingame     31,2s  frame=bb_004380.bmp
jystart    31,2s  frame=bb_004380.bmp
carsel     37,4s  frame=bb_004380.bmp
livery     40,6s  frame=bb_005629.bmp
accept     41,7s  frame=bb_005629.bmp
exitjy     41,7s  frame=bb_005629.bmp
strfin     41,7s  frame=bb_005629.bmp
END        68,8s  frame=bb_008177.bmp
asserts=0 phase=DRIVING
DIAGENV    [-DiagEnv BRN_FRAME_DUMP_REQUEST=1 BRN_FRAME_DUMP_MAX=10]
TELEPORT 3040.7,-5.8,-1937.9,180
SWEEP    (none)
SLOT     62185  exe=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source45_native_62185_20261030\stage\slot\Burnout_PC.exe (a copy; cwd=D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source45_native_62185_20261030\stage\data)
CONCURRENT_GAMES allow=True max_other=0
SKIPINTRO (not armed)
TITLESTART requested=True ready-observed=True sent-at=25,8s; stimulus receipt only
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
DRIVE    drove path=236,8m net=234,6m over 109 [motion] samples (samples 41..149: teleport seat up to the first respawn; later respawns=0 GAMEWRECKED=1)
POLL     max period 0,75s at 58,5s over 217 polls (target 0.25s)
THROTTLE first input at t+0,27s (on time)
SIMPAUSE 2 pause(s), 2 resume(s); first pause at 4% of the log
GAS      51 of 150 [motion] samples report gas > 0
drive=True steer=none delay=6,0s hold=to-end
title-start tap:Start run=25,8s actions=8+45
input accel/none           run=  47,6s t+  0,27s
```
