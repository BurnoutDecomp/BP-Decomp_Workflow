# Building the menu coverage map

Depth for [`../SKILL.md`](../SKILL.md).

## Reading the console's FSMs

`build/game/FSM/*.BUNDLE` comes from `build data` (a local build output, not in git). Each is
a bnd2 container whose payload is plain Lua text, so a byte-level regex reads it directly:

```python
import os, re
fsm_dir = "build/game/FSM"
for name in sorted(os.listdir(fsm_dir)):
    data = open(os.path.join(fsm_dir, name), "rb").read()
    states = re.findall(rb'\["(\d+)"\]\s*=\s*"([A-Z0-9_]+)"', data)
    print(name, [s.decode() for _, s in states])
```

Save it to a file and run it with Python: a shell heredoc can mangle the backslashes.

- `stateNames` maps each state id to its name; each state has a
  `NextState_<id><NAME>( eventId )` function whose branches name the events (`TOGGLE_LEFT`,
  `GO_BACK`, `ADVANCE`, ...) and the state each leads to. That is the real route graph:
  a settings row can lead through an intermediate state rather than straight to the
  screen it names.
- `BRNSCREENFSM.BUNDLE` belongs to the screen flow; the HUD flow switches between several
  bundles over a session (the boot-phase bundles, free-burn, event, crash); the overlay flow
  uses `BRNOVERLAY.BUNDLE`. Which bundle runs on which flow is in the `RunFsm` posts (grep
  `RunFsm` and the bundle names in `b5-decomp/src/GameSource/Game/`).
- The bundles are console data: a state the console's FSMs never reference is unreachable
  in the original, whatever our pool registers.

## Intersecting with the pools

Collect each flow's `CgsIDCompress("<NAME>")` registrations (the screen, HUD and overlay flow
`.cpp` files named in the skill) and compare with the union of every bundle's `stateNames`.

- In a pool, in no FSM: unreachable on the console too. When this was first measured
  (2026-09), `CN_STATS`, `ON_STATS` and `ON_RIVALS` were in the screen pool and in no FSM;
  `CrashNavStats` had been reconstructed, mounted and verified and still could not be
  opened. Rerun the intersection rather than trusting that list.
- In an FSM, in no pool: a real missing state (it was `CN_ACHIEVE` then). The witness prints
  `[screen] MISSING STATE` if the script ever asks for it.
- A screen-flow state missing from `BRNSCREENFSM.BUNDLE` may still be reachable through
  another flow: `PAUSED` lives in the HUD flow's bundles, `NULL` in its own.

## Per screen: bodies, events, overrides

- Compare the console's functions for the state's class with our bodies
  (`python tools/re/hasbody.py`, `work show`, `work audit`). A header-only shell inherits the
  base `CgsGui::State` behaviour: it registers for no events and does nothing, so every
  control on it is dead.
- A state receives only the GUI event ids it registers for (`RegisterForEvents`,
  `PriorityRegisterForEvent` on `CgsGui::StateInterface`); an id it never registers is a
  silent drop even when the handler exists.
- **The vtable outranks the DWARF.** The DWARF declares methods that the console's vtable
  fills with a shared, ICF-folded empty body (a bare return). So:
  - a DWARF-declared override is real only if the console's slot holds a distinct body;
  - pin the slot order by aligning against a state whose overrides are all real;
  - an identical body serves several classes after folding, so the disassembler can print
    another class's name for a slot: one reconstruction may serve several screens, and the
    class layout those bodies touch has to exist first;
  - a trivial accessor (for example "load zero resources") is folded across many vtables
    and cannot anchor one; use another slot.
  - `python tools/re/vtable_override_audit.py --table <addr>` prints one console table slot
    by slot (it needs the ARTIST database and exports, both local inputs); the generated
    `progress/VTABLE_OVERRIDE_AUDIT.md` lists every console override with no body here,
    classified, with hand verdicts in `tools/re/vtable_override_verdicts.json`.
- A flagged "missing override" can be a false positive when the class does the work another
  way (for instance loading its own resources instead of through `GetResourcesToLoad`).
  Read the body before writing one.

## The online status table

Online screens additionally need a live online service, so for them record, per state:
reachable per the FSM, bodied, what service it waits for, and whether its path runs
through a console platform service (sign-in, Xbox Live) that needs a product decision about
a PC equivalent. Record such a block in the table; never invent a path around it.

## The map itself

One row per state: flow, FSM bundle and reachability, bodies present, registered events, the
witness line seen, the frame that shows it, and the case that produced both. Keep it as a
tracked report under `progress/` and update it as screens land.
