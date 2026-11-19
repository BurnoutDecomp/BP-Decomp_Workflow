# Pair cases: two instances online

A pair case runs two game instances at once, one per slot, and gives one verdict. Sources: the
banner of `tools/tests/run_pair.ps1`, `tools/tests/_net_pair_common.ps1`,
`tools/tests/cases/net_lan_pair.ps1`, and the game-side harness in
`b5-decomp/src/GameShared/GameClasses/System/PC/BrnNetHarnessPC.cpp`.

```
powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_pair
powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_pair -SlotA 3 -SlotB 4
powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_pair -ExpectFail
powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_pair -NoRun -RunDir <pair run dir>
```

Parameters: `-Case` (required), `-SlotA` (1), `-SlotB` (2), `-RunDir`, `-RunsRoot`, `-ExpectFail`,
`-NoRun`, `-LockTimeoutSec` (7200), `-WaitSeconds` (0 = the lock timeout plus 30 minutes), `-Label`.
Exit codes as run_case: 0 as expected, 1 not, 2 the runner could not run it.

## The case file

A pair case is a `.ps1` under `tools/tests/cases/` (most `net_*` files, and `fxnetcrash_pair.ps1`;
the descriptor's `Pair` key is what marks one) that takes `param([string]$Role)`:

- Called with no `-Role` it returns the **descriptor**: `@{ Name; Bug; Pair = @{ Roles = @('Host','Guest') } }`,
  with no `Checks`, so run_case refuses it (exit 2) and run_all skips it: it can never run as a lone
  half by mistake.
- Called with `-Role <r>` it returns an ordinary run_case hashtable for that half: its own `Run`,
  `DiagEnv`, `Setup` and `Checks`. `Setup` is the place for non-`BRN_*` environment such as `BP_LAN`.
- Shared helpers live in `tools/tests/_net_pair_common.ps1`, outside `cases\` so run_all never
  picks it up. Dot-source it and capture `$NetPair`: its members are variables holding closures,
  because a check runs long after the case file's scope is gone. Members: `Spots` (Host / Guest
  teleports), `Setup` (a Setup factory: `BP_LAN=1`, `BP_LAN_NAME=<name>`), `Ordered`, `First`,
  `States` (parses the `[net] state` lines), `WallTime`, `FramesAround`, `FrameStat`, `Spawned`,
  `CarGoneFrame`, `CarGoneLog`.

## Pair-level checks

A half's own checks see only its own log. "The two hashes agree" needs both:

```powershell
Pair = @{ Roles = @('Host','Guest'); Checks = @(
  @{ Name = 'both halves agree'; Script = { param($p)
       $h = $p.Halves.Host.LogLines; $g = $p.Halves.Guest.LogLines
       ...; @{ Pass = $true; Detail = '...' } } }
) }
```

`$p.RunDir` is the pair folder; `$p.Halves.<role>` carries `LogLines`, `Log`, `RunDir`,
`MarksText`, `Verdict`, `Slot`. A pair check that throws or returns nothing FAILS. The pair
verdict is PASS only when both halves and every pair check pass, and nothing timed out.

## How it runs

- Each half is an ordinary `run_case.ps1 -Case <wrapper> -Slot <n> -RunDir <pair dir>\<role>` in
  its own powershell process, both started together; the wrapper is a one-line `.ps1` in the pair
  folder that calls the case with `-Role`. So each half gets flow_run's boot, its slot's box lock,
  exe staging and kill sweep, the `BRN_*` wipe plus `DiagEnv`, provenance and its own `REPORT.md`.
- Slot 0 is never used. Before starting, run_pair seeds a slot's missing `Memcard_<n>\Profile.sav`
  (it never overwrites one, and refuses a slot whose game is running); a slot without a profile
  would boot the first-boot path.
- A half that outlives the wait is stopped and its flow_run releases its own lock on exit.

Everything lands in `scratch\bugtest\runs\<case>\<timestamp>\`: `<role>\` (the half's run folder),
`<role>.case.ps1` (its wrapper), `<role>.console.log`, `signals\`, and the pair's `result.json` /
`REPORT.md`; `latest.json` one level up points at the newest pair.

## Cross-half environment

Set by run_pair just before each half starts; none is a `BRN_*` name, so flow_run's wipe leaves
them alone and they reach flow_run by inheritance:

| variable | value |
|---|---|
| `BP_PAIR_DIR` | the pair folder; signal files live in `<dir>\signals` (emptied at the start) |
| `BP_PAIR_ROLE`, `BP_PAIR_PEER_ROLE` | this half's role and the other's |
| `BP_PAIR_PEER_LOG` | the other half's live log, `build\game_slots\<its slot>\BrnGame.log` |
| `BP_PAIR_T0` | the pair start (FILETIME, UTC): a peer log last written before it is the previous run's and is ignored |

They feed `-MenuScript`'s `waitpeer:`, `waitfile:` and `signal:` steps
([menu-driving.md](menu-driving.md)): the Guest must not open a quick match before the Host's
game exists, so the schedule follows the game, not the clock.

## Game-side net harness (PC only, `BP_LAN` runs)

Passed through each half's `DiagEnv`; the witnesses print only when `BP_LAN=1` or a role is set,
so a default offline run prints none of them.

| variable | effect |
|---|---|
| `BRN_NET_HOST=1` | sign in, create an unranked free-burn lobby game |
| `BRN_NET_JOIN=1` | sign in, quick-match unranked free burn, retried until it lands (ignored when `BRN_NET_HOST` is also set) |
| `BRN_NET_DELAY=<s>` | hold the role until the boot has reached free roam |
| `BRN_NET_LEAVE_AT=<s>` | post GUI 52 (leave game) that long after first being in game |
| `BRN_NET_SCRIPT=<s>:<gui\|net>:<id>[:<w>/<w>...];...` | scheduled channel-40 GUI records |
| `BRN_NET_TEAM`, `BRN_NET_START_MODE` | read by the same harness; see their use in the `net_*` cases |

Witness lines are bounded `[net] ...` lines: `pclan up name=`, `harness armed role=`,
`login finished loggedIn=`, `create|quickjoin finished success= inGame=`, `player added`,
`playerlist`, and a `[net] state t= wall= loggedIn= inGame= host= players=` line on every change.
`wall=` is the local time of day, which lines a log event up with the dumped frames' file times
(`$NetPair.WallTime`, `$NetPair.FramesAround`). A budgeted witness that spent its budget before
the event proves nothing by its absence (`CarGoneLog` checks for exactly that).
