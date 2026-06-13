# Goal Scoping & Execution Traces

How to make `work next` drive toward a concrete milestone (e.g. "boot to the main menu")
instead of grinding the whole 4,319-TU program leaf-first. This is the reference for the
`work goal` command, the `goals.json` schema, and — most importantly — how to capture a
**Xenia execution trace** and turn it into an exact, real goal scope.

- Tooling: [`tools/work/work.py`](../tools/work/work.py) (`work goal …`),
  [`tools/work/trace_import.py`](../tools/work/trace_import.py) (trace parser/importer).
- Config: [`progress/goals.json`](../progress/goals.json).
- Operating summary lives in [`AGENTS.md`](../AGENTS.md); this file is the full version.

---

## 1. Why goals are *membership*, not call-graph closure

The obvious idea — "from `main`, automatically follow the call graph and reverse exactly
what's needed" — **does not work on this game**, and we measured why:

- The TU dependency graph (`tu_dep` in the ledger, built from X360 xrefs) is a single
  **strongly-connected component of ~2,984 TUs — 75% of the program.** Everything is
  mutually reachable (directors, components, event queues, the assert manager, and the
  global free-function bucket all reference each other).
- Consequence: the callee-closure of *any* boot seed (`main`, `mainCRTStartup`, the
  main-window render fn, …) is the same ~3,266-TU (75%) blob. Stopping traversal at a
  "foundation layer" (allocator/EASTL/string/assert) only shrank it to ~2,972 — the SCC
  is held together by game-level cycles, not just utilities.

So static reachability (closure / corridor / ancestors-∩-descendants) **cannot** carve out
a milestone here. A goal is instead a **membership selector**: an explicit decision about
which TUs are in scope. `work next` then ranks only in-scope TUs, keeping leaf-first order
within them. (Verified numbers reproduce via the snippet in §6.)

The accurate way to get "exactly what a milestone needs" is **dynamic**: run the real build
to that point and record what executed (§4). That sidesteps the SCC entirely.

---

## 2. The `goals.json` schema

Goals are grouped into **category buckets** under `goals` so like kinds sit together.
Goal *names* are unique across buckets; `active_goal` names one of them.

```jsonc
{
  "active_goal": "boot-trace",        // null => whole-program leaf-first (the default)
  "goals": {
    "milestones": {                   // execution-derived scopes (the accurate kind)
      "boot-trace": {
        "source": "trace",            // set by `work goal import-trace`
        "captured": "<timestamp>",
        "trace_stats": { },           // executed/mapped/tu counts
        "include_tus": ["GameSource/Gui/Foo.cpp", "class:BrnGui::Bar"]   // exact ids
      }
    },
    "pattern_slices": {               // hand-authored glob scopes (subsystem slices)
      "<name>": {
        "description": "...",
        "include": ["GameSource/Gui/**", "BrnGui::*", "*Director*"],     // globs
        "exclude": ["*Online*"]                                          // globs
      }
    }
  }
}
```

The CLI is bucket-agnostic (it flattens by name), so a goal can live in any bucket and may
carry any of the fields — `include_tus` and/or `include`/`exclude` — regardless of which
bucket it sits in. The buckets are organisation, not semantics.

**A goal's scope = `include_tus`  ∪  (TUs matching any `include` glob, minus any `exclude` glob).**

Two equal ways to express membership — use either or both in the same goal:

| Field | Membership by | Produced by | Matches against |
|-------|---------------|-------------|-----------------|
| `include` / `exclude` | **pattern** (glob, `*` = any chars) | hand-authoring | the TU id **and** every function name the TU contains |
| `include_tus` | **explicit list** of TU ids | `work goal import-trace` (a measured set) | exact TU id |

So `include_tus` is not special to one goal — it's the "enumerated" half of the model.
A trace produces a concrete list, so it lands in `include_tus`; a human writing intent uses
globs. You can give one goal both (e.g. a trace scope widened with `"include": ["BrnGui::*"]`).

**Which to use when (the rule of thumb):**
- **Milestone** ("game boots to X") → **trace goal** (`import-trace`). Only execution knows
  what a milestone needs; globs guessing at a milestone will be both too wide and too narrow.
- **Subsystem slice** ("work on all replay serialisers / all GUI") → **glob goal**. Here a
  pattern *is* the intent, and no run of the game defines the set.
- Milestones are **cumulative**: capture a longer run (boot → menu → junkyard), re-import,
  and the ledger's done-status absorbs the overlap — no trace-diffing is ever needed. The
  background preloading a trace picks up (e.g. world/junkyard loading before the menu shows)
  is *correct* scope: the game really executes it before reaching the milestone.

Because `include` globs match function *names* too, `BrnGui::*` scopes both class-keyed TUs
(`class:BrnGui::…`) and decfigs file-path TUs whose functions live in that namespace.

---

## 3. The `work goal` command

```
work goal                       # list defined goals + the active one, with TU/done counts
work goal show <name>           # scope size, % done, status breakdown, and the BOUNDARY report
work goal set <name>            # make <name> active (scopes `work next`)
work goal clear                 # back to whole-program leaf-first
work goal import-trace <name> [--trace-dir DIR]   # build a goal from a Xenia trace (§4)
```

`work next` prints a `[goal: <name>] N TUs in scope, M done` banner when a goal is active,
and only proposes in-scope TUs (still leaf-first by unresolved-dependency count).

**The boundary report** (in `work goal show`) is the tuning tool: it lists out-of-scope TUs
that in-scope code calls — i.e. what will be **trap-stubbed** until you widen scope or reach
them. Use it to decide whether to pull more TUs in. Example: a loading-screen glob goal
shows it would stub `CgsAssertManager`, the event queues, and `BrnGuiCache`.

---

## 4. Capturing a Xenia execution trace (full reproduction)

This is how the `boot-trace` goal (925 TUs, 21%) was produced. ~10 minutes end to end.

### 4.1 Prerequisites
- The prepared Xenia copy (Adriwin's, set up for this):
  `C:\Logiciels\Xbox360\Xenia Burnout 5\Xenia Burnout5 - For Reverse\`
  - emulator: `xenia_burnout5.exe`
  - game: `Burnout_tcartwright\BURNOUT_X360_ARTIST.XEX`
  - config: `xenia-burnout5.config.toml`
- `progress/identity.json` and the ledger (`work bootstrap` if missing).

### 4.2 Enable tracing
**Back up the config first** (`cp xenia-burnout5.config.toml xenia-burnout5.config.toml.bak`),
then in the `[CPU]` section set:

```toml
trace_functions = true
trace_function_data = true
trace_function_data_path = "e:/Reverse_Engineering/Burnout/BP-Decomp_Workflow/.trace/funcdata/"
```

Notes learned the hard way:
- `trace_function_data_path` is a **directory** — Xenia writes 32 MB chunk files into it
  named `.0`, `.1`, … Create the dir first.
- Xenia **rewrites the config on launch** but preserves your edits (it round-trips).
- Xenia **ignores `log_file`** and always logs to its own `xenia.log` in the emulator dir.
- The cheaper signals do **not** work: debug `log_level=3` logs kernel/GPU calls but no
  guest-function execution; `disassemble_functions` did not emit to the log in this build.
  `trace_function_data` is the one that produces a parseable executed-function set.

### 4.3 Run to the milestone
Launch the XEX, let it boot, and **stop at the point you want to scope to**. The longer/
further you go, the larger the scope (window → loading → attract demo → menu → in-race).

```powershell
$dir = "C:\Logiciels\Xbox360\Xenia Burnout 5\Xenia Burnout5 - For Reverse"
$p = Start-Process -FilePath (Join-Path $dir "xenia_burnout5.exe") `
     -ArgumentList "`"$(Join-Path $dir 'Burnout_tcartwright\BURNOUT_X360_ARTIST.XEX')`"" `
     -WorkingDirectory $dir -PassThru
Start-Sleep -Seconds 30          # boot→attract; raise/lower to reach your milestone
Stop-Process -Id $p.Id -Force    # closing the emulator flushes the trace
```

A 30 s run reaches the attract-mode demo (you'll see AI cars — note the boundary report
then includes RaceCar/Traffic/Collision, confirming gameplay code ran).

### 4.4 Import
```
work goal import-trace boot-trace          # reads .trace/funcdata by default
work goal show boot-trace                  # inspect scope + boundary
work goal set boot-trace                   # start working it
```

`import-trace` prints e.g. `5516 executed funcs, 1880 mapped, 925 TUs`. The ~34% mapping
rate is expected: the unmapped ~66% are kernel import/export thunks (almost all in the
`0x82Cxxxxx` region; the export table is at `0x82C76DFC`), which are not game functions.

### 4.5 Restore the emulator
Set the three `trace_*` flags back to `false` (or restore your `.bak`) so normal runs aren't
slowed and don't write 32 MB each launch. Delete `.trace/` when done — it's git-ignored.

---

## 5. The trace binary format (for `trace_import.py` maintainers)

Each executed guest function is one block in the chunk files:

```
offset  size  field
  0      u32   block size in bytes  == 56 + ninstr*8
  4      u32   function start guest address   (e.g. 0x8292b480 = XEX entry point)
  8      u32   function end guest address      (ninstr = (end-start)/4)
 12      40B   rest of the 56-byte header (counts/flags — unused by us)
 56    ninstr*u64  per-instruction execution counts (1 = executed once, …)
```

The chunked writer interleaves blocks (threads), so a strict size-walk desyncs. The parser
instead **scans** every 4-byte offset for the self-validating relation
`size == 56 + ((end-start)/4)*8` with `start`/`end` in `0x82000000–0x82C80000`. Random data
effectively never satisfies it, so false positives are negligible. Pipeline:
executed addrs → `identity.json` x360_addrs → ledger `func.tu_id`. See
[`tools/work/trace_import.py`](../tools/work/trace_import.py).

---

## 6. Reproducing the SCC / scope measurements

```python
# 75% SCC + closure check (run from repo root)
import sqlite3, collections
con = sqlite3.connect("progress/ledger.sqlite"); con.row_factory = sqlite3.Row
adj = collections.defaultdict(set)
for t, d in con.execute("SELECT tu_id,dep_id FROM tu_dep"): adj[t].add(d)
# Tarjan/closure as in the analysis -> largest SCC ≈ 2984 TUs; closure(main) ≈ 3266 (75%).
```

`work goal show <name>` reports the live scope size and done-count for any goal, which is
the quick way to compare a glob goal vs. a trace goal vs. whole-program.
