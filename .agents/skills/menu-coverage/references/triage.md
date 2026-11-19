# Why a screen does not show: finding the cause in one run

Depth for [`../SKILL.md`](../SKILL.md). Each cause below cost a campaign hours once; each has
a one-run way to see it. Paths are under `b5-decomp/src/` unless they start with `tools/`.

## A gate that never passes

A screen that waits for every expected apt component
(`GuiCache::AreAllAptComponentsInitialised`, `GameSource/Gui/BrnGuiCache.cpp`) shows nothing
at all while one is missing: no setup, no icons, no cursor, no prompts. The log can look
healthy (bundles loaded, components bound), because a gate has no consumer to grep.

With `BRN_SATNAV_DIAG=1` the cache prints, for the screen flow, one `[cnav-diag] expect ...`
line per registration (in registration order, by name or by hash), one
`[cnav-diag] ONLOAD '<name>' hash <h>` line per apt load, and
`[cnav-diag] SCREEN apt components: N of M still unloaded; hashes: ...`. Match the missing
hashes to the `expect` lines; the apt bundle's clip names are greppable as ASCII. Measured
2026-09-10: a toggle group composed its parent's name into each item twice, and a parked
component expected hash 0, so ten components never "loaded" and the crash-nav map drew only
its texture.

## An assert parks the game

An assert pauses the game on a dialog until it is released (`bug-test` covers the harness
side). A menu that ignores every tap is often sitting on one. Read the run log's
`[ASSERT n] <message>` lines first, and compare the expression with the console's: an assert
written with the wrong condition fired the moment a newly passing gate let the screen run.

## A gate flag with no drop

A state that "waits for X" re-runs its wait every time it is re-entered (pause then
unpause, a flow re-entering a state), so the flag needs its drop as well as its raise.
Measured 2026-09-10: pausing during a race hid the HUD on unpause because the "event
prepared" flag the race HUD waits on was never cleared; the console clears it on the GUI
event bridged from the start-playing-mode action. The HUD states print an always-on
`[hud-reveal]` line naming which reveal arm they took.

To find the drop: grep the exports' pseudocode for the store to the flag's member offset
(`<offset>) = 0`), then find who posts the event that runs that store by grepping the
event's type name, because templates hide the numeric id (`AddGuiEvent<Type>`).

## One producer, many consumers

For any game action or GUI event, enumerate every consumer's `case N:` (the
`HandleGameActions`, `HandleExternalRequests` and `RecEvent` handlers across modules) and
check each exists here. Reaching one consumer is not being consumed: measured 2026-09-10,
the stop-mode action reached one module while three others lacked the case, so events never
ended (rivals stayed, traffic never came back, the minimap kept the event's markers).

## An entry without its exit

A state machine whose entry is reconstructed and whose exit arms are gated is a trap: it
enters and stays. Check both directions of every state, and grep the log for
`request handler DEFERRED:` (`GameSource/Resource/BrnGameDataModule.cpp`) when a
resource-driven state machine stalls: a deferred stand-in never completes its request.

## Payload casts

A GUI queue record's layout is whatever its producer posted
(`GameShared/GameClasses/Gui/CgsGuiModule.h`): the `AddGuiEvent` template posts the payload
past the 12-byte `GuiEvent<N>` header, a raw `AddEvent(&whole, id, sizeof)` posts the whole
struct, and some ids are one-byte empty tags (`GameShared/GameClasses/Gui/CgsGuiEvent.h`).
Casting a payload pointer to a header-bearing struct shifts every field by 12 and the
consumer silently falls back (measured: post-FX hooks resolved to the fallback for two runs;
an input handler read the same wrong button for every press). Check which producer wrote
the record before casting.

## An unmaterialised GUI bank

The PC GUI resource servicer (`GameShared/GameClasses/Gui/Model/Resources/CgsGuiResourceModulePC.cpp`)
keeps one pool per bank it materialises and answers any other bank with
`[GuiResourceModule] bank <n> not materialised on PC -- '<name>' completed without IO.`
The notification still arrives, the resource is "bound", and the first use asserts that the
resource has no main memory. Adding a bank means copying an existing bank's pool block and
its load (and unload) arm.

## Unrecovered captions

A pointer table entry left as `0` with an "unrecovered" flag is usually one image read:
`tools/re/x360rd.py <table address> <bytes>`, then read each pointee as a string.

## Not in the exe, or shadowed

A reconstructed screen whose `.cpp` is not mounted in `tools/build/build_game_exe.bat` is
not built; `progress/linked_files.json` lists every file the compiler opened for the
published exe. A stub definition linked in place of the real body shadows it: when a flow
"does nothing", find every definition of the method (`python tools/re/hasbody.py` prints the
first three; `git -C b5-decomp grep` for the qualified name finds the rest) and check which
file the build mounts (`build-and-link`).
