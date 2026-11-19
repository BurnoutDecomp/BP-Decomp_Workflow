---
name: goal-scoping
description: >-
  Scope `work next` / `work claim` to a milestone or a subsystem with `work goal`
  (list / set / show / clear / import-trace): glob goals (include / exclude in
  progress/goals.json) for subsystem slices vs execution-derived trace goals from a Xenia
  trace_functions / trace_function_data capture (tools/work/trace_import.py) for
  milestones, the TU-granularity caveat (executed_funcs, exclude_tus carve-outs such as
  class:<global>), and reading the boundary report of out-of-scope callees that get
  trap-stubbed. Load before setting, tuning or importing a goal, or when asked to drive the
  work toward a milestone ("boot to the main menu", "reach the loading screen").
---

# Goal scoping

By default `work next` is whole-program leaf-first. An **active goal** makes `work next`
(and `work claim` without ids) rank only the TUs in that goal's scope, keeping leaf-first
order within it. Use it to drive toward a concrete milestone or to work one subsystem.

Not for: the reconstruction loop itself (`reconstruct-tu`), or running the decomp build
(`bug-test`). The full write-up (schema, trace reproduction, binary format) is
`references/GOAL_SCOPING.md`, a local input; this skill is the operating procedure.

## What a goal is

- **A membership selector, not a call-graph closure.** The X360 TU call graph is one
  strongly-connected component spanning most of the program, so the closure of any boot seed
  is most of the game: reachability cannot carve out a milestone.
- Goals live in `progress/goals.json` (a tracked file) under category buckets
  (`milestones`, `pattern_slices`); names are unique across buckets, and `active_goal` names
  the active one (`null` = whole program). A goal may carry any of: `description`,
  `include`, `exclude`, `include_tus`, `exclude_tus`, `executed_funcs`, `source`,
  `trace_stats`, `captured`.
- **Scope** = (`include_tus` ∪ TUs matching any `include` glob and no `exclude` glob) minus
  `exclude_tus`. Explicit `include_tus` are kept whatever the globs say; `exclude_tus` is the
  only way to drop one of them.
- **Globs**: `*` matches any run of characters (`/` and `::` included, so `**` is the same
  as `*`); everything else is literal; the match is against the whole string. Each TU is
  matched by its id, by every function name it contains and, for a `class:` TU, by the bare
  `Namespace::Class`. So `GameSource/Gui/**` matches by path, `BrnGui::*` by namespace, and
  `*Director*` by either.

**Division of labour.** Glob goals are for subsystem slices ("all GUI", "all replay
serialisers"), where a pattern is the intent. Milestones ("boots to the main menu") need an
execution-derived trace goal: only a real run knows what a milestone needs. The glob goals
shipped in `goals.json` are approximate pattern slices, not runnable-milestone scopes.

## Commands

| Command | What it does |
|---|---|
| `work goal` or `work goal list` | goals by category with TU and done counts; `*` marks the active one |
| `work goal show [<name>]` | scope size, % done, status breakdown, trace coverage, boundary report (defaults to the active goal) |
| `work goal set <name>` | make `<name>` active (writes `progress/goals.json`), then show it |
| `work goal clear` | back to whole-program leaf-first |
| `work goal import-trace <name> [--trace-dir DIR]` | build a milestone goal from a Xenia trace (default DIR `.trace/funcdata`) |

- `set`, `clear` and `import-trace` rewrite the tracked `progress/goals.json`: whether and how
  to commit it is `land-change`.
- With a goal active, `work next` prints `[goal: <name>] N TUs in scope, M done` and counts
  unresolved dependencies over in-scope TUs only (`unresolved-deps(in-scope)`): out-of-scope
  callees stay todo for the whole goal and get trap-stubbed regardless of order, so counting
  them would permanently distort leaf-first inside the scope.
- With a coordination server configured, `work next` and `work claim` use the server's goal
  (`[server goal: <name>]`); the local `active_goal` drives only local ranking.

## Procedure: a subsystem slice (glob goal)

1. Add or edit the goal in `progress/goals.json` (`pattern_slices`): `description`,
   `include`, `exclude`.
2. `work goal show <name>`: check the scope size and read the boundary report.
3. Widen or narrow the globs deliberately until the boundary is what you intend, then
   `work goal set <name>`.

## Procedure: a milestone (trace goal)

1. **The maintainer captures a trace** of the real X360 build in Xenia. Agents never
   launch a game other than the decomp's own exe (`bug-test`): if you need a trace, ask
   for one and give these settings (header of `tools/work/trace_import.py`). In the
   emulator's `*.config.toml`, `[CPU]` section:
   ```toml
   trace_functions = true
   trace_function_data = true
   trace_function_data_path = "<absolute dir>/"
   ```
   The path is a directory (create it first); Xenia writes chunk files `.0`, `.1`, ... into
   it. Launch the XEX, play or boot up to the milestone, then close the emulator. Turn the
   three settings back off afterwards.
2. Optional dry look: `python tools/work/trace_import.py <trace_dir> [--json out.json]`
   prints executed, mapped and TU counts without touching a goal.
3. `work goal import-trace <name> [--trace-dir DIR]`. It parses the chunks into executed
   guest addresses, maps them through `progress/identity.json` names to TUs, and writes a
   `milestones` goal whose `include_tus` is that exact set and whose `executed_funcs` is the
   executed function list. Kernel import/export thunks map to no game name and are dropped.
4. Read the coverage it prints (see the caveat below), add carve-outs to the goal's
   `exclude_tus`, then `work goal show <name>` and `work goal set <name>`.
5. **Grow it** by capturing further (window, menu, in-race) and re-importing under the same
   name: milestones are cumulative, and the ledger's done status absorbs the overlap.
   Re-import keeps a hand-written `description` and `exclude_tus`, and replaces everything
   else (`include` / `exclude` globs added to a trace goal by hand are dropped: re-add them).
6. Traces are large binary files and git-ignored (`.trace/`); the derived TU list lives in
   `goals.json`. Delete the trace after importing.

## The TU-granularity caveat

One executed function pulls its whole TU into scope, so a trace goal's TU count understates
the work: the TUs it names hold many more functions than ran. That is why the import stores
`executed_funcs`:

- `work goal show` (and the import) report function coverage, and list mostly-unexecuted TUs
  (twenty or more functions, fewer than a third executed) as candidates for `exclude_tus`;
  the classic one is `class:<global>`, a free-function bucket pulled in by a handful of calls.
- Carve those out with the goal's `exclude_tus`. It survives re-imports; editing
  `include_tus` by hand does not.
- The dossier (`work show <tu> --full`) marks each function `[EXECUTED in goal trace]` or
  `[not executed in goal trace]` for the active goal. This is advisory: the work unit, and
  "done", remain the whole TU.

## Reading the boundary report

`work goal show` ends with the out-of-scope TUs that in-scope code calls, weighted by call
count, skipping dependencies that are already done or external. Those callees will be
trap-stubbed until you widen the scope or reach them. Use it to decide deliberately:
pull a heavily used dependency into scope (a glob or `include_tus` entry), or leave it out
and accept the stubs. Only the top entries are listed, with a count of the rest.

## Never

- Never scope by call-graph closure or reachability: it returns most of the program.
- Never edit `include_tus` of a trace goal by hand to drop a TU: use `exclude_tus`.
- Never treat a shipped glob slice as a runnable milestone scope.
- Never commit trace files.
- Never assume a local `work goal set` changes what a coordination server hands out.

## Tools

- `tools/work/work.py` (`work goal ...`): goal CLI; ranking in `work next` / `work claim`.
- `tools/work/trace_import.py`: trace parser (header = capture instructions and format).
- `progress/goals.json`: goal definitions and the active goal.

## Read next

- `references/GOAL_SCOPING.md` (local input): the long-form reference.
- `reconstruct-tu`: the loop that consumes the scoped queue.
