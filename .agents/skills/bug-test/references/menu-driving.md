# Menu driving

How a harness run presses buttons, walks menus and proves which screen it reached. Sources:
`tools/diagnostics/flow_run.ps1` (the switches and their banners), the game's channel table in
`b5-decomp/src/GameShared/GameClasses/System/Input/PC/CgsInputPadsPC.cpp`, the action ids in
`b5-decomp/src/GameSource/Input/GameInputActions.h`, and the shipped screen FSM. The menu
campaign itself is the `menu-coverage` skill; the debug UI is `debug-menu-campaign`.

## Channels

The harness never types at the window. Each input is a session-wide named event
`Local\BurnoutPC_Input_<Channel>` (suffixed `_<n>` on slot n) that the game's input leaf reads by
action id. Two kinds, and the difference is the whole point:

- **Taps** are auto-reset: one input update observes one `Set()`. Menu channels are taps.
- **Holds** are manual-reset: every update between `Set()` and `Reset()` sees the button down.
  Pedals, steering, bumpers, boost and the camera buttons are holds; a pedal you can only tap for
  one frame cannot drive a car.

| channel | action | notes |
|---|---|---|
| `DPadUp` `DPadDown` `DPadLeft` `DPadRight` | 37 38 39 40 | GUI d-pad (the crash-nav panel's filter toggles) |
| `Prev` / `Next` | 41 / 42 | GUI_UP / GUI_DOWN: highlight previous / next row |
| `OptionPrev` / `OptionNext` | 43 / 44 | GUI_LEFT / GUI_RIGHT: previous / next item (the car carousel) |
| `Start` | 45 | START: pause (Driver Details), press-start, exit the map |
| `PauseMap` | 46 | GUI_BACK: in game, opens the main map (the other offline pause) |
| `Accept` | 49 | GUI_SELECT, the A button |
| `Stop` | 50 | GUI_CANCEL, the B button: the back-out. There is no `Back` channel |
| `Option0` | 51 | GUI_OPTION0 |
| `ShoulderL` / `ShoulderR` | 54 / 55 | tab left / right (`TOGGLE_LEFT` / `TOGGLE_RIGHT`); holds |
| `GuiZoom` / `GuiInspect` | 56 / 57 | GUI triggers: map zoom, inspect the hovered icon |
| `EventDetails` | 58 | opens the event map; in free roam it toggles road rules |
| `Accelerate` `Brake` `HandBrake` `Boost` | 0 1 2 3 | driving holds |
| `Lookback` / `ChangeView` | 6 / 5 | the director's camera holds |
| `SteerLeft` `SteerRight` `SteerFrac25` `SteerFrac50` `StickUp` `StickDown` `CameraLeft` `CameraRight` `CameraUp` `CameraDown` | stick | analogue holds |

Never add `ShoulderL` / `ShoulderR` to `-MenuTapAt`: those two events are created manual-reset
for the bumper holds, and a second, auto-reset handle on the same name silently gets whatever
mode the first creator chose. `_box_lock.ps1` clears the seven driving and bumper holds when it
takes the lock, because a hold stranded by a killed run stays down for the next run (LB+RB held
tips the pause screen into CN_SETTINGS and looks exactly like the game dying).

## Which switch reaches what

| need | switch |
|---|---|
| one press at a time on the DRIVING clock | `-MenuTapAt "<sec>:<Channel>,..."` |
| presses that wait for the game | `-MenuScript` (below) |
| a pause-screen tab (actions 54/55) | `-ShoulderAt "<sec>:<L\|R>[:hold]"`; `-MenuTapAt` cannot carry them |
| the offline pause and back | `-PauseAt`, `-PauseTarget map\|driver`, `-UnpauseAt` |
| a camera button | `-CamButtonAt "<sec>:<V\|B>[:hold]"` |
| bind the title's controller | `-TitleStart` |
| move the car-select carousel | `-CarSelectTaps "<Channel>:<count>"` (recipe below) |

Grep `flow_run.console.log` for the arming line (`MENU-TAP schedule`, `BUMPER schedule`,
`PAUSE schedule`, `CAMBUTTON schedule`, `CAR-SELECT taps`, `MENUSCRIPT armed`) before trusting a
run: a schedule that never armed is indistinguishable in the log from a dead game-side handler.
A one-entry `-ShoulderAt` once never pressed under Windows PowerShell 5.1 (a returned one-element
array unrolls and `.Count` reads `$null`); since 2026-09-16 flow_run wraps the object-returning
schedule parses (`-ShoulderAt`, `-CamButtonAt`) in `@()` at the call site, and any new schedule
switch that returns objects must do the same.

## -MenuScript

Steps separated by `;`, run in order from the DRIVING mark, at most one poll (250 ms) apart. A
regex cannot contain `;`.

| step | does |
|---|---|
| `wait:<regex>` | until this instance's log prints a matching line, counted from where the previous wait matched (the first wait scans from launch) |
| `waitpeer:<regex>` | the same on the other pair half's live log (`BP_PAIR_PEER_LOG`) |
| `waitfile:<name>` | until the file exists (a relative name lives in the pair's `signals` folder, or `<OutDir>\signals` outside a pair) |
| `signal:<name>` | create that file (the other half's `waitfile`) |
| `tap:<Chan>[x<n>]` | n taps (1..50), `-MenuScriptGap` apart; tap channels: the `-MenuTapAt` set plus `PauseMap` |
| `tapuntil:<Chan>:<regex>` | tap, then re-tap every max(1 s, gap) until this log matches, at most 8 taps, then the script STALLS. Only lines printed after the first tap count. For a menu that ignores a press while it animates in |
| `hold:<Chan>:<sec>` | a manual-reset hold of a driving, bumper, boost, camera, stick or GUI-trigger channel; not on a channel `-Drive` also holds |
| `sleep:<sec>` | wall-clock pause |
| `gap:<sec>` | change the spacing after each tap |
| `timeout:<sec>` | later waits give up after that long (0 = never, the default); a timed-out wait STALLS the script |
| `mark:<name>` | a `MENUSCRIPT` line in `marks.txt`, for checks to anchor on |

`marks.txt` gets `MENUSCRIPT done=<k>/<n> state=<run|done|stalled>` (with the next step when it did
not finish) and one line per step ending `(log line <n>)`: the number of complete `BrnGame.log`
lines the harness had read when the step ran. A check attributes a game line to the tap before it
by comparing line numbers; `tools/tests/cases/pause_event_intro.ps1` is the worked example. Check
`done=k/n` first: a stalled script answers a different question.

## The offline pause

- Two pauses, two screens: action 46 (`-PauseTarget map`, `PauseMap`) opens CN_MAP_MAIN; action 45
  (`-PauseTarget driver`, `Start`) opens CN_D_DETAIL, the Driver Details screen a player gets from
  START. Both stop the sim.
- Back out with `Stop` (50) or `Start` (45). The map's exit arm takes those two only; `Accept` (49)
  picks an icon there and never resumes.
- The ring, from the shipped `BRNSCREENFSM.BUNDLE` (plain Lua text in the built game data under
  `build\game\FSM\`, a local build output):

```
CN_D_DETAIL --TOGGLE_LEFT (LB)--> CN_MAP_MAIN
            --TOGGLE_RIGHT (RB)--> CN_SETTINGS
            --GO_BACK-->           INGAME
CN_SETTINGS --TOGGLE_LEFT-->  CN_D_DETAIL     --TOGGLE_RIGHT--> ON_PLAY     --GO_BACK--> INGAME
            rows --> CN_PROFILE  CN_OPTIONS  CN_TRAX  CN_CREDITS  CN_COLOUR  CN_ENTER_ON
```

- Settings rows (`BrnCrashNavSettings.cpp`): PROFILE 0, OPTIONS 1, TRAX 2, CREDITS 3, COLOUR 4,
  ACCOUNT_MAN 5, SPONSOR_CODE 6. CREDITS stays disabled until the profile unlocks it, so counting
  `Next` presses from row 0 skips it; the menu wraps (`SetupMenu(7, true)`), so the high rows are
  nearer with `Prev`. Row 5 goes to CN_ENTER_ON, the console's sign-in screen, not straight to
  CN_ACCT_MAN.
- A recipe recorded as reaching CN_TRAX (2026-09-16):
  `-Drive -PauseAt 25 -PauseTarget driver -ShoulderAt "30:R:2" -MenuTapAt "36:Next,38:Next,40:Accept"`.

## Car select and which car drives

- The junkyard flow accepts the default car (the Cavalry, Classic Muscle, per flow_run's
  `-CarSelectTaps` banner). A defect that only shows on a car somebody picked is invisible to every
  run that accepts the default: say in the report which car drove.
- Move the carousel through the game's own path: `-CarSelectTaps 'OptionNext:<n>'` with
  `DiagEnv 'BRN_CARSEL_TAPSTEP=1'` and an `-AcceptGap` of a few seconds, one tap per pump slot
  (`tools/tests/cases/junkyard_carousel.ps1`). A harness tap is one input update and reaches the
  carousel as DOWN + RELEASED with no PRESSED; the lever replays that release as the press.
  flow_run's banner example `DPadRight:2` is not the measured recipe.
- Or swap the car: `DiagEnv 'BRN_DEBUG_PLAYER_CAR=<vehicle id or name>'` (for example `PDDK01`).
  It fires once, through the console's own debug change-car event, after the car is on the road
  outside the junkyard with no mode running; it logs `[car] ***** HARNESS-ONLY PLAYER CAR SWAP`,
  and an unknown name logs `[car] FAIL` instead. It is not the player's path.
- The available cars depend on the profile, so pin it with `ProfileFixture`.

## Screen diagnostics

- `DiagEnv 'BRN_SCREEN_DIAG=1'`: `ScriptedFsm::SetState`, the choke point of every scripted
  transition in every FSM, prints `[screen] ENTER '<to>' (from '<from>') seq <n>`, and
  `[screen] MISSING STATE '<id>'` when a script asks for a state nobody registered. One run names
  every menu the game opened, in order.
- A state absent from `BRNSCREENFSM.BUNDLE` is not necessarily unreachable: that bundle is only the
  screen flow's, and other flows (the HUD flow's pause, for one) have their own FSMs. Trace before
  calling a screen dead. A state the console's own bundles never name is unreachable in the
  original too; making it reachable is a divergence.
- `DiagEnv 'BRN_SATNAV_DIAG=1'` adds `[cnav-diag]` lines for the crash-nav screen: every expected
  apt component (`expect hash`), every apt `ONLOAD`, and `SCREEN apt components: N of M still
  unloaded`. A screen gate that never passes hides the whole screen; diff the expected set against
  the loaded one.
- A finished screen and a hung screen are the same picture: tell "never arrived" from "arrived and
  cannot leave" by the log lines after the screen appeared, then open the frames.

## Debug UI keys

The debug-menu cases drive the in-game debug UI from `Setup` through
`tools/tests/tools/VW_DEFORM_debugkeys.ps1`, which presses keys on the debug-key channels
(`Local\BurnoutPC_DebugKey_XX`, slot-suffixed) from a steps file (`wait:`, `key:<vk>`, `cmd:`,
`sleep:`, `note:`) and logs each step with the game-log line count. Never run it by hand beside
another game. See `debug-menu-campaign`.
