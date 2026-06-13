#!/usr/bin/env python3
"""
work - the decomp ledger CLI.

The single interface every agent (Claude Code, Codex, ...) uses to drive the
reconstruction loop. It is NOT an agent launcher; it is a state/query tool the
in-chat agent shells out to, the same way it runs git. See AGENTS.md / STRATEGY.md.

Ledger: progress/ledger.sqlite (source of truth for status). Rebuildable structure
comes from the committed progress/identity.json + progress/tu_index.json; status is
preserved across re-seeds.

Commands:
    work seed [--deps]        build/update the ledger from the Phase 0 JSONs
    work status               overview: counts by status, % done
    work goal [list|set <name>|clear|show <name>]
                              scope `next` to a membership goal (progress/goals.json)
    work next [-n N]          the next leaf-first ready TU(s) to work on
                              (restricted to the active goal's TUs, if one is set)
    work show <tu>            dossier for a TU (functions, signatures, deps)
    work start <tu>           claim a TU (todo -> in_progress)
    work submit <tu>          mark a TU reconstructed (compile/review gates: Phase 3)
    work block <tu> "reason"  mark blocked; work unblock <tu> to clear
    work set <tu> --status S  manual status override

Run as:  python tools/work/work.py <cmd>   (or the work.cmd shim from repo root)
"""
import argparse, json, os, re, sqlite3, subprocess, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_skeleton import signature_from_pseudocode, load_export  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(ROOT, "progress", "identity.json")
TU_INDEX = os.path.join(ROOT, "progress", "tu_index.json")
DB = os.path.join(ROOT, "progress", "ledger.sqlite")
# Committed mirrors so a fresh clone can rebuild the (git-ignored) ledger with
# full status + dependency graph, without needing IDA or the .ida-exports.
STATUS_JSON = os.path.join(ROOT, "progress", "status.json")
TU_DEPS_JSON = os.path.join(ROOT, "progress", "tu_deps.json")
GOALS_JSON = os.path.join(ROOT, "progress", "goals.json")
X360_EXPORTS = os.path.join(ROOT, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")

TU_STATUS = ("todo", "in_progress", "compiled", "done", "blocked")
SCHEMA = """
CREATE TABLE IF NOT EXISTS tu(
  id TEXT PRIMARY KEY, source TEXT, status TEXT DEFAULT 'todo',
  n_funcs INTEGER, n_decfigs INTEGER, dest_path TEXT,
  owner TEXT, notes TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS func(
  name TEXT PRIMARY KEY, tu_id TEXT, x360_addr TEXT,
  status TEXT DEFAULT 'todo', attempts INTEGER DEFAULT 0,
  verify_tier INTEGER DEFAULT 0, match_required INTEGER DEFAULT 0,
  blocker TEXT, dest_path TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS tu_dep(
  tu_id TEXT, dep_id TEXT, weight INTEGER,
  PRIMARY KEY(tu_id, dep_id));
CREATE TABLE IF NOT EXISTS event(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  tu_id TEXT, func TEXT, action TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS ix_func_tu ON func(tu_id);
CREATE INDEX IF NOT EXISTS ix_dep_tu ON tu_dep(tu_id);
"""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def connect():
    if not os.path.exists(DB):
        sys.exit("no ledger yet — run: python tools/work/work.py seed")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def log(con, action, tu_id=None, func=None, detail=None):
    con.execute("INSERT INTO event(ts,tu_id,func,action,detail) VALUES(?,?,?,?,?)",
                (now(), tu_id, func, action, detail))


def normalize_path(p):
    """Resolve `GameSource/Unity/../World/X.cpp` -> `GameSource/World/X.cpp`."""
    parts = []
    for seg in p.replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
        else:
            parts.append(seg)
    return "/".join(parts)


def dest_for(tu_id, source):
    """Mirror a DecFIGS primary_file under b5-decomp/src/; class TUs decide later."""
    if source == "decfigs":
        return "b5-decomp/src/" + normalize_path(tu_id)
    return None


# ---------------------------------------------------------------- seed
def cmd_seed(args):
    identity = json.load(open(IDENTITY, encoding="utf-8"))
    index = json.load(open(TU_INDEX, encoding="utf-8"))
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    if args.reset:
        con.executescript("DELETE FROM tu; DELETE FROM func; DELETE FROM tu_dep; DELETE FROM event;")

    # upsert TUs and funcs, preserving any existing status
    for tu_id, t in index.items():
        con.execute(
            "INSERT INTO tu(id,source,status,n_funcs,n_decfigs,dest_path,updated_at) "
            "VALUES(?,?,'todo',?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "source=excluded.source,n_funcs=excluded.n_funcs,n_decfigs=excluded.n_decfigs,"
            "dest_path=COALESCE(tu.dest_path,excluded.dest_path)",
            (tu_id, t["source"], t["n_funcs"], t["n_decfigs"], dest_for(tu_id, t["source"]), now()))
        for name in t["functions"]:
            e = identity.get(name, {})
            addr = (e.get("x360_addrs") or [None])[0]
            con.execute(
                "INSERT INTO func(name,tu_id,x360_addr,status,updated_at) "
                "VALUES(?,?,?,'todo',?) ON CONFLICT(name) DO UPDATE SET "
                "tu_id=excluded.tu_id,x360_addr=excluded.x360_addr",
                (name, tu_id, addr, now()))
    con.commit()
    n_tu = con.execute("SELECT COUNT(*) FROM tu").fetchone()[0]
    n_fn = con.execute("SELECT COUNT(*) FROM func").fetchone()[0]
    print(f"seeded {n_tu} TUs, {n_fn} functions")

    # restore committed progress (status) so a fresh clone resumes where we left off
    n_restored = restore_status(con)
    if n_restored:
        print(f"restored status for {n_restored} TUs from {os.path.basename(STATUS_JSON)}")

    # dependency graph: rebuild from exports (--deps) or load the committed mirror
    if args.deps and os.path.isdir(X360_EXPORTS):
        build_deps(con, identity)
    else:
        n_edges = load_deps_from_json(con)
        if n_edges:
            print(f"loaded {n_edges} dependency edges from {os.path.basename(TU_DEPS_JSON)}")
        elif args.deps:
            print("  (--deps requested but no .ida-exports/ and no tu_deps.json — `next` will be heuristic)")
    con.commit()
    sync_status(con)
    con.close()


# ---------------------------------------------------------------- committed mirrors
def sync_status(con):
    """Write the mutable progress (non-default rows only) to the committed status.json."""
    tu = {}
    for r in con.execute("SELECT id,status,owner,notes FROM tu WHERE status!='todo'"):
        tu[r["id"]] = {k: r[k] for k in ("status", "owner", "notes") if r[k]}
    fn = {}
    for r in con.execute("SELECT name,status,verify_tier,attempts FROM func "
                         "WHERE status!='todo' OR verify_tier!=0 OR attempts!=0"):
        d = {"status": r["status"]}
        if r["verify_tier"]:
            d["verify_tier"] = r["verify_tier"]
        if r["attempts"]:
            d["attempts"] = r["attempts"]
        fn[r["name"]] = d
    os.makedirs(os.path.dirname(STATUS_JSON), exist_ok=True)
    json.dump({"tu": tu, "func": fn}, open(STATUS_JSON, "w", encoding="utf-8"),
              indent=1, sort_keys=True)


def restore_status(con):
    if not os.path.exists(STATUS_JSON):
        return 0
    st = json.load(open(STATUS_JSON, encoding="utf-8"))
    for tid, d in st.get("tu", {}).items():
        con.execute("UPDATE tu SET status=?, owner=?, notes=? WHERE id=?",
                    (d.get("status", "todo"), d.get("owner"), d.get("notes"), tid))
    for nm, d in st.get("func", {}).items():
        con.execute("UPDATE func SET status=?, verify_tier=?, attempts=? WHERE name=?",
                    (d.get("status", "todo"), d.get("verify_tier", 0), d.get("attempts", 0), nm))
    con.commit()
    return len(st.get("tu", {}))


def load_deps_from_json(con):
    if not os.path.exists(TU_DEPS_JSON):
        return 0
    edges = json.load(open(TU_DEPS_JSON, encoding="utf-8"))
    con.execute("DELETE FROM tu_dep")
    con.executemany("INSERT INTO tu_dep(tu_id,dep_id,weight) VALUES(?,?,?)", edges)
    con.commit()
    return len(edges)


def build_deps(con, identity):
    """TU->TU call edges from xrefs_from, so `next` can be leaf-first."""
    print("building dependency graph from xrefs (reading X360 exports)...", flush=True)
    addr2name = {}
    for name, e in identity.items():
        for a in (e.get("x360_addrs") or []):
            addr2name[a] = name
    name2tu = {r["name"]: r["tu_id"] for r in con.execute("SELECT name,tu_id FROM func")}

    def callees(row):
        exp = load_export(row[1]) if row[1] else None
        outs = set()
        if exp:
            for xr in exp.get("xrefs_from", []):
                nm = addr2name.get(xr.get("address"))
                if nm:
                    outs.add(nm)
        return row[0], outs  # (caller_name, set[callee_name])

    rows = con.execute("SELECT name,x360_addr FROM func").fetchall()
    edges = Counter()  # (tu, dep_tu) -> weight
    with ThreadPoolExecutor(max_workers=16) as ex:
        for caller, outs in ex.map(callees, [(r["name"], r["x360_addr"]) for r in rows]):
            ctu = name2tu.get(caller)
            for callee in outs:
                dtu = name2tu.get(callee)
                if dtu and dtu != ctu:
                    edges[(ctu, dtu)] += 1
    edge_rows = [[t, d, w] for (t, d), w in edges.items()]
    con.execute("DELETE FROM tu_dep")
    con.executemany("INSERT INTO tu_dep(tu_id,dep_id,weight) VALUES(?,?,?)", edge_rows)
    con.commit()
    # persist the committed mirror so a clone gets leaf-first `next` without IDA
    json.dump(edge_rows, open(TU_DEPS_JSON, "w", encoding="utf-8"))
    print(f"  {len(edges)} TU->TU dependency edges (mirrored to {os.path.basename(TU_DEPS_JSON)})")


# ---------------------------------------------------------------- status
def cmd_status(args):
    con = connect()
    print("translation units:")
    for r in con.execute("SELECT status,COUNT(*) c FROM tu GROUP BY status ORDER BY c DESC"):
        print(f"  {r['status']:12s} {r['c']}")
    tot = con.execute("SELECT COUNT(*) FROM tu").fetchone()[0]
    done = con.execute("SELECT COUNT(*) FROM tu WHERE status='done'").fetchone()[0]
    print(f"  {'TOTAL':12s} {tot}   ({100*done//max(tot,1)}% done)")
    print("functions:")
    for r in con.execute("SELECT status,COUNT(*) c FROM func GROUP BY status ORDER BY c DESC"):
        print(f"  {r['status']:12s} {r['c']}")


# ---------------------------------------------------------------- goals (membership scoping)
def load_goals():
    """The goal selector config. Missing file => no goals (whole-program ordering)."""
    if not os.path.exists(GOALS_JSON):
        return {"active_goal": None, "goals": {}}
    return json.load(open(GOALS_JSON, encoding="utf-8"))


# goals.json groups goals into named category buckets under `goals` (e.g. "milestones",
# "pattern_slices") so like kinds sit together. A goal object carries any of these fields;
# a category bucket is a dict of {goal_name: goal_object}. Goal names are unique across
# buckets. These helpers flatten that so the rest of the CLI is category-agnostic.
GOAL_FIELDS = ("description", "include", "exclude", "include_tus", "exclude_tus",
               "executed_funcs", "source", "trace_stats", "captured")


def goal_index(goals):
    """Flatten the category buckets into an ordered {name: (category, goal)} map.
    Tolerates a legacy flat layout (a goal object placed directly under `goals`)."""
    out = {}
    for key, val in goals.get("goals", {}).items():
        if not isinstance(val, dict):
            continue
        if any(k in val for k in GOAL_FIELDS):      # a goal object sitting at top level
            out[key] = (None, val)
        else:                                        # a category bucket of goals
            for name, goal in val.items():
                if isinstance(goal, dict):
                    out[name] = (key, goal)
    return out


def find_goal(goals, name):
    """(category, goal) for a goal by name, or (None, None) if undefined."""
    return goal_index(goals).get(name, (None, None))


def put_goal(goals, name, goal, category):
    """Insert/replace a goal under `category`, removing any prior copy in other buckets."""
    buckets = goals.setdefault("goals", {})
    for members in buckets.values():
        if isinstance(members, dict):
            members.pop(name, None)
    buckets.setdefault(category, {})[name] = goal


def _glob_re(g):
    """Tiny glob: `*` matches any run of chars, everything else is literal."""
    return re.compile("^" + ".*".join(re.escape(p) for p in g.split("*")) + "$")


def tu_match_targets(con):
    """Per-TU strings a selector may match: the TU id, the function names it holds,
    and (for class-keyed TUs) the bare `Namespace::Class`."""
    targets = defaultdict(list)
    for r in con.execute("SELECT id FROM tu"):
        tid = r["id"]
        targets[tid].append(tid)
        if tid.startswith("class:"):
            targets[tid].append(tid[len("class:"):])
    for r in con.execute("SELECT name, tu_id FROM func"):
        targets[r["tu_id"]].append(r["name"])
    return targets


def resolve_goal_tus(con, goal):
    """Resolve a goal to its set of in-scope TU ids. Scope is the union of:
      - `include_tus`: an explicit list of TU ids (e.g. an execution-trace import), and
      - `include`/`exclude` globs matched against each TU's id or any function it holds,
    minus `exclude_tus`: explicit TU ids carved out of the final scope — the knob for
    dropping a mega-bucket TU (e.g. `class:<global>`) that a trace pulled in via one
    executed function. It survives re-imports, unlike editing `include_tus` by hand.
    A glob-matched TU is excluded by any `exclude` glob; explicit `include_tus` are kept
    regardless of globs. Returns None only if the goal selects nothing at all."""
    explicit = set(goal.get("include_tus", []))
    carved = set(goal.get("exclude_tus", []))
    inc = [_glob_re(g) for g in goal.get("include", [])]
    if not inc:
        sel = explicit - carved
        return sel if sel else None
    exc = [_glob_re(g) for g in goal.get("exclude", [])]
    targets = tu_match_targets(con)
    sel = set(explicit)
    for tid, strs in targets.items():
        if any(rx.match(s) for rx in inc for s in strs) and \
           not any(rx.match(s) for rx in exc for s in strs):
            sel.add(tid)
    sel -= carved
    return sel if sel else None


def active_goal_set(con, goals=None):
    """(name, tu_id_set) for the active goal, or (None, None) if whole-program."""
    goals = goals if goals is not None else load_goals()
    name = goals.get("active_goal")
    if not name:
        return None, None
    _, g = find_goal(goals, name)
    if g is None:
        sys.exit(f"active_goal {name!r} is not defined in {os.path.basename(GOALS_JSON)}")
    return name, resolve_goal_tus(con, g)


# ---------------------------------------------------------------- goal command
def cmd_goal(args):
    goals = load_goals()
    index = goal_index(goals)
    action = getattr(args, "action", "list") or "list"

    if action == "list":
        active = goals.get("active_goal")
        print(f"active goal: {active or '(none — whole-program leaf-first)'}")
        if not index:
            print(f"no goals defined in {os.path.basename(GOALS_JSON)}")
            return
        con = connect()
        targets = tu_match_targets(con)
        status = {r["id"]: r["status"] for r in con.execute("SELECT id,status FROM tu")}
        # group the flattened index back by category, preserving JSON bucket order
        by_cat = {}
        for name, (cat, g) in index.items():
            by_cat.setdefault(cat, []).append((name, g))
        for cat, members in by_cat.items():
            print(f"\n{cat or '(uncategorised)'}:")
            for name, g in members:
                sel = resolve_goal_tus_cached(g, targets) or set()
                done = sum(1 for t in sel if status.get(t) == "done")
                mark = "*" if name == active else " "
                print(f" {mark} {name:22s} {len(sel):4d} TUs, {done:4d} done   {g.get('description','')[:58]}")
        return

    if action == "clear":
        goals["active_goal"] = None
        save_goals(goals)
        print("active goal cleared — `work next` is whole-program leaf-first again")
        return

    if action == "import-trace":
        if not args.name:
            sys.exit("usage: work goal import-trace <name> [--trace-dir DIR]")
        import trace_import
        trace_dir = args.trace_dir or os.path.join(ROOT, ".trace", "funcdata")
        if not os.path.isdir(trace_dir):
            sys.exit(f"trace dir not found: {trace_dir}\n  capture one with Xenia trace_function_data "
                     f"(see tools/work/trace_import.py header), or pass --trace-dir.")
        con = connect()
        tus, names, stats = trace_import.load_for_goal(con, trace_dir)
        existing = find_goal(goals, args.name)[1] or {}
        goal = {
            # trace imports are milestones; keep a hand-written description across re-imports
            "description": existing.get("description")
                or f"MILESTONE (execution-derived, {stats['tus']} TUs) from a Xenia trace.",
            "source": "trace",
            "captured": now(),
            "trace_stats": stats,
            "include_tus": tus,
            # the function-level truth. TU membership alone can't say what ran (one
            # executed function pulls in its whole TU); `goal show` and the dossier
            # use this to mark what the milestone actually exercised.
            "executed_funcs": names,
        }
        if existing.get("exclude_tus"):  # hand-curated carve-outs survive re-imports
            goal["exclude_tus"] = existing["exclude_tus"]
        put_goal(goals, args.name, goal, category="milestones")
        save_goals(goals)
        print(f"imported trace -> milestone {args.name!r}: {stats['executed_addrs']} executed funcs, "
              f"{stats['mapped_funcs']} mapped, {len(tus)} TUs")
        report_trace_coverage(con, goal)
        print(f"  activate with: work goal set {args.name}")
        return

    if action == "set":
        if not args.name:
            sys.exit("usage: work goal set <name>")
        if args.name not in index:
            sys.exit(f"unknown goal {args.name!r}. defined: {', '.join(index) or '(none)'}")
        goals["active_goal"] = args.name
        save_goals(goals)
        print(f"active goal -> {args.name}")
        cmd_goal(argparse.Namespace(action="show", name=args.name))
        return

    if action == "show":
        name = args.name or goals.get("active_goal")
        if not name:
            sys.exit("usage: work goal show <name> (or set an active_goal)")
        cat, g = find_goal(goals, name)
        if g is None:
            sys.exit(f"unknown goal {name!r}")
        con = connect()
        sel = resolve_goal_tus(con, g) or set()
        print(f"goal: {name}   [{cat or 'uncategorised'}]")
        if g.get("description"):
            print(f"  {g['description']}")
        print(f"  include: {g.get('include', [])}")
        print(f"  exclude: {g.get('exclude', [])}")
        if g.get("exclude_tus"):
            print(f"  exclude_tus (explicit carve-outs, survive re-import): {g['exclude_tus']}")
        # status breakdown within scope
        counts = Counter()
        for r in con.execute("SELECT id,status FROM tu"):
            if r["id"] in sel:
                counts[r["status"]] += 1
        total = sum(counts.values())
        print(f"\n  {total} TUs in scope  ({100*counts['done']//max(total,1)}% done)")
        for s in TU_STATUS:
            if counts[s]:
                print(f"    {s:12s} {counts[s]}")
        report_trace_coverage(con, g)
        # advisory boundary report: in-scope TUs that call OUT of scope -> will be stubbed
        ext = Counter()
        st = {r["id"]: r["status"] for r in con.execute("SELECT id,status FROM tu")}
        for r in con.execute("SELECT tu_id,dep_id,weight FROM tu_dep"):
            if r["tu_id"] in sel and r["dep_id"] not in sel and st.get(r["dep_id"]) != "done":
                ext[r["dep_id"]] += r["weight"]
        print(f"\n  boundary: {len(ext)} out-of-scope TUs are called from in-scope code "
              f"(trap-stubbed until you widen the globs or reach them).")
        for tu, w in ext.most_common(12):
            print(f"    x{w:<4d} {tu[:66]}")
        if len(ext) > 12:
            print(f"    ... +{len(ext)-12} more")
        return

    sys.exit(f"unknown goal action {action!r} (use: list | set <name> | clear | show [name])")


def resolve_goal_tus_cached(goal, targets):
    """resolve_goal_tus against a prebuilt targets map (avoids re-querying per goal)."""
    explicit = set(goal.get("include_tus", []))
    carved = set(goal.get("exclude_tus", []))
    inc = [_glob_re(g) for g in goal.get("include", [])]
    if not inc:
        sel = explicit - carved
        return sel if sel else None
    exc = [_glob_re(g) for g in goal.get("exclude", [])]
    sel = set(explicit)
    sel.update(tid for tid, strs in targets.items()
               if any(rx.match(s) for rx in inc for s in strs)
               and not any(rx.match(s) for rx in exc for s in strs))
    sel -= carved
    return sel if sel else None


def report_trace_coverage(con, goal, top=8):
    """For a trace goal, report how much of the in-scope FUNCTION count the trace
    actually executed, and flag mega-bucket TUs that a single executed function
    pulled in nearly whole-unexecuted — the candidates for `exclude_tus`.
    Silent for goals without `executed_funcs` (glob goals, pre-upgrade imports)."""
    executed = set(goal.get("executed_funcs") or [])
    if not executed:
        return
    sel = resolve_goal_tus(con, goal) or set()
    nf = {r["id"]: r["n_funcs"] for r in con.execute("SELECT id, n_funcs FROM tu")}
    ran_in_tu = Counter()
    for r in con.execute("SELECT name, tu_id FROM func"):
        if r["name"] in executed and r["tu_id"] in sel:
            ran_in_tu[r["tu_id"]] += 1
    total = sum(nf.get(t, 0) for t in sel)
    ran = sum(ran_in_tu.values())
    print(f"  function coverage: the trace executed {ran} of the {total} functions these "
          f"{len(sel)} TUs hold ({100*ran//max(total,1)}%) — TU granularity pulls in whole units.")
    flags = sorted(((nf.get(t, 0) - ran_in_tu[t], ran_in_tu[t], nf.get(t, 0), t)
                    for t in sel if nf.get(t, 0) >= 20 and ran_in_tu[t] * 3 < nf.get(t, 0)),
                   reverse=True)
    if flags:
        print("  mostly-unexecuted TUs in scope (candidates for the goal's `exclude_tus`):")
        for _unex, r, n, t in flags[:top]:
            print(f"    {r:4d}/{n:<5d} executed  {t[:62]}")
        if len(flags) > top:
            print(f"    ... +{len(flags)-top} more")


def save_goals(goals):
    json.dump(goals, open(GOALS_JSON, "w", encoding="utf-8"), indent=1)


# ---------------------------------------------------------------- next
def cmd_next(args):
    con = connect()
    has_deps = con.execute("SELECT COUNT(*) FROM tu_dep").fetchone()[0] > 0
    gname, gset = active_goal_set(con)
    # rank todo TUs by (# dependency TUs not yet done) asc -> leaves first,
    # then decfigs-sourced first, then smallest first.
    if has_deps:
        q = """
        SELECT t.id, t.source, t.n_funcs, t.dest_path,
          (SELECT COUNT(*) FROM tu_dep d JOIN tu dt ON dt.id=d.dep_id
            WHERE d.tu_id=t.id AND dt.status NOT IN ('done')) AS unresolved
        FROM tu t WHERE t.status='todo'
        ORDER BY unresolved ASC, (t.source='decfigs') DESC, t.n_funcs ASC"""
    else:
        q = """SELECT t.id,t.source,t.n_funcs,t.dest_path, NULL AS unresolved
        FROM tu t WHERE t.status='todo'
        ORDER BY (t.source='decfigs') DESC, t.n_funcs ASC"""
    # A goal scopes `next` to its in-scope TUs, keeping the leaf-first order within
    # that subset. Filter in Python so we never hit SQL parameter limits on big sets.
    ranked = con.execute(q).fetchall()
    if gset is not None:
        status = {r["id"]: r["status"] for r in con.execute("SELECT id,status FROM tu")}
        n_done = sum(1 for t in gset if status.get(t) == "done")
        print(f"[goal: {gname}]  {len(gset)} TUs in scope, {n_done} done  "
              f"(clear with `work goal clear`; details: `work goal show {gname}`)")
        ranked = [r for r in ranked if r["id"] in gset]
        if has_deps:
            # Re-rank counting unresolved deps over IN-SCOPE TUs only. Out-of-scope
            # callees stay todo for the whole goal and get trap-stubbed regardless of
            # order, so counting them would permanently distort leaf-first within the
            # scope (measured: ~26% of picks inverted on the boot-trace goal).
            deps = defaultdict(set)
            for d in con.execute("SELECT tu_id, dep_id FROM tu_dep"):
                deps[d["tu_id"]].add(d["dep_id"])
            ranked = [dict(r) for r in ranked]
            for r in ranked:
                r["unresolved"] = sum(1 for x in deps.get(r["id"], ())
                                      if x in gset and status.get(x) != "done")
            ranked.sort(key=lambda r: (r["unresolved"], r["source"] != "decfigs", r["n_funcs"]))
    rows = ranked[:args.n]
    if not rows:
        msg = "no todo TUs in this goal — switch/clear the goal or run `work status`" if gset is not None \
              else "no todo TUs — run `work status`"
        print(msg)
        return
    dep_label = "unresolved-deps(in-scope)" if gset is not None and has_deps else "unresolved-deps"
    for r in rows:
        dep = "" if r["unresolved"] is None else f"  {dep_label}={r['unresolved']}"
        print(f"[{r['source']:7s}] {r['n_funcs']:4d} fn{dep}  {r['id']}")
    if not has_deps:
        print("\n(ordering is heuristic — run `work seed --deps` for true leaf-first)")


# ---------------------------------------------------------------- show
def cmd_show(args):
    con = connect()
    t = con.execute("SELECT * FROM tu WHERE id=?", (args.tu,)).fetchone()
    if not t:
        sys.exit(f"unknown TU: {args.tu!r}")

    # --full: the Phase 2 dossier (everything needed to reconstruct)
    if getattr(args, "full", False):
        import dossier
        funcs = con.execute("SELECT * FROM func WHERE tu_id=? ORDER BY name", (args.tu,)).fetchall()
        text = dossier.assemble(con, t, funcs, with_asm=args.asm)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            open(args.out, "w", encoding="utf-8").write(text)
            print(f"wrote dossier ({len(funcs)} functions) -> {args.out}")
        else:
            print(text)
        return

    print(f"TU      : {t['id']}")
    print(f"source  : {t['source']}    status: {t['status']}    funcs: {t['n_funcs']}")
    print(f"dest    : {t['dest_path'] or '(class TU — choose a path)'}")
    if t["notes"]:
        print(f"notes   : {t['notes']}")
    deps = con.execute(
        "SELECT d.dep_id, dt.status, d.weight FROM tu_dep d JOIN tu dt ON dt.id=d.dep_id "
        "WHERE d.tu_id=? ORDER BY d.weight DESC", (args.tu,)).fetchall()
    if deps:
        print(f"\ncalls into {len(deps)} other TU(s):")
        for d in deps[:12]:
            print(f"  [{d['status']:11s}] x{d['weight']:<3d} {d['dep_id'][:60]}")
        if len(deps) > 12:
            print(f"  ... +{len(deps)-12} more")
    print("\nfunctions:")
    for f in con.execute("SELECT * FROM func WHERE tu_id=? ORDER BY name", (args.tu,)):
        exp = load_export(f["x360_addr"]) if f["x360_addr"] else None
        sig = signature_from_pseudocode(exp.get("pseudocode")) if exp else None
        print(f"  [{f['status']:9s}] {f['x360_addr']}  {f['name']}")
        if sig:
            print(f"             {sig[:110]}")
    print("\n(`work show <tu> --full` for the complete dossier: pseudocode, locals, "
          "Feb-2007 original source, callee signatures, asm with --asm.)")


# ---------------------------------------------------------------- transitions
def set_tu(con, tu, status, owner=None, notes=None):
    if status not in TU_STATUS:
        sys.exit(f"status must be one of {TU_STATUS}")
    r = con.execute("SELECT id FROM tu WHERE id=?", (tu,)).fetchone()
    if not r:
        sys.exit(f"unknown TU: {tu!r}")
    con.execute("UPDATE tu SET status=?, owner=COALESCE(?,owner), notes=COALESCE(?,notes), updated_at=? WHERE id=?",
                (status, owner, notes, now(), tu))
    log(con, status, tu_id=tu, detail=notes)
    con.commit()
    sync_status(con)  # keep the committed status.json in step with the ledger


def cmd_start(args):
    con = connect()
    set_tu(con, args.tu, "in_progress", owner=os.environ.get("WORK_AGENT", "agent"))
    print(f"started {args.tu}")
    cmd_show(args)


def resolve_files(con, tu, explicit):
    """The .cpp file(s) to compile for this TU: explicit --files, else the recorded
    dest_path. No git-status guessing — compiling "whatever changed" has attributed
    the wrong file to a TU before (see reconcile_from_files.py); fail fast instead,
    listing the modified .cpp files as candidates the caller can pass explicitly."""
    if explicit:
        return explicit
    row = con.execute("SELECT dest_path FROM tu WHERE id=?", (tu,)).fetchone()
    if row and row["dest_path"] and os.path.exists(os.path.join(ROOT, row["dest_path"])):
        return [row["dest_path"]]
    hints = []
    try:
        out = subprocess.run(["git", "-C", os.path.join(ROOT, "b5-decomp"),
                              "status", "--porcelain", "--", "src"],
                             capture_output=True, text=True).stdout
        hints = ["b5-decomp/" + ln[3:].strip() for ln in out.splitlines()
                 if ln[3:].strip().endswith(".cpp")]
    except Exception:
        pass
    msg = [f"{tu}: no dest_path recorded and no --files given — name the TU's .cpp explicitly:",
           f"  work submit \"{tu}\" --files <b5-decomp/src/...cpp>",
           "(a single explicit file is then recorded as the TU's dest_path)"]
    if hints:
        msg.append("modified/untracked .cpp in b5-decomp/src, if one of these is it:")
        msg += [f"  {h}" for h in hints[:10]]
    sys.exit("\n".join(msg))


def cmd_submit(args):
    import verify
    con = connect()
    funcs = con.execute("SELECT * FROM func WHERE tu_id=? ORDER BY name", (args.tu,)).fetchall()
    if not funcs:
        sys.exit(f"unknown TU: {args.tu!r}")
    files = resolve_files(con, args.tu, args.files)
    row = con.execute("SELECT dest_path FROM tu WHERE id=?", (args.tu,)).fetchone()
    if args.files and len(files) == 1 and row and not row["dest_path"]:
        # remember the explicit choice so re-submit/parity/reconcile find the file
        con.execute("UPDATE tu SET dest_path=? WHERE id=?", (files[0], args.tu))
    con.execute("UPDATE func SET status='recovered', updated_at=? WHERE tu_id=? AND status='todo'", (now(), args.tu))
    con.commit()

    status, glog = verify.compile_gate(files)
    print(f"compile gate: {status.upper()}  (files: {', '.join(files) or 'none'})")
    if status == "fail":
        con.execute("UPDATE func SET attempts=attempts+1 WHERE tu_id=?", (args.tu,))
        set_tu(con, args.tu, "in_progress", notes=args.note)
        log(con, "compile_fail", tu_id=args.tu, detail=glog[:2000])
        con.commit()
        print("\n--- compiler output (fix and re-submit) ---")
        print(glog[-3000:])
        return

    tier = 1 if status == "pass" else 0
    con.execute("UPDATE func SET status='compiles', verify_tier=?, updated_at=? WHERE tu_id=?", (tier, now(), args.tu))
    set_tu(con, args.tu, "compiled", notes=args.note)
    if status == "skip":
        print(f"  (gate skipped: {glog.strip()})")
        log(con, "compile_skip", tu_id=args.tu, detail=glog[:200])

    # cheap deterministic pre-review gate (NO LLM): structural parity signals.
    import parity
    if parity.load_config().get("automated_check", {}).get("enabled"):
        res = parity.check_tu(funcs, files)
        if res["verdict"] == "SKIP":
            print(f"\nautomated parity: SKIP ({res.get('reason')})")
        else:
            print("\n" + parity.format_report(res))
            log(con, "parity", tu_id=args.tu, detail=res["verdict"])
            con.commit()
            if res["verdict"] == "GREEN":
                print("  -> structurally consistent; a trivial/standard TU may skip the LLM review.")
            elif res["verdict"] == "YELLOW":
                print("  -> mild drift; prefer an LLM review.")
            else:
                print("  -> gross divergence; review and look hard at the flagged signal(s).")

    packet = verify.reviewer_packet(con, dict_row(con, "tu", args.tu), funcs, files)
    con.commit()
    print(f"\nreviewer packet -> {os.path.relpath(packet, ROOT)}")
    print("Next: choose a reviewer per progress/review.config.json policy, run the review, then record the verdict:")
    print(f"  work review \"{args.tu}\" --verdict pass   # or: --verdict fail --notes \"...\"")


def dict_row(con, table, tu):
    return con.execute(f"SELECT * FROM {table} WHERE id=?", (tu,)).fetchone()


def cmd_review(args):
    con = connect()
    t = dict_row(con, "tu", args.tu)
    if not t:
        sys.exit(f"unknown TU: {args.tu!r}")
    if args.verdict == "pass":
        con.execute("UPDATE func SET status='reviewed', verify_tier=2, updated_at=? WHERE tu_id=?", (now(), args.tu))
        set_tu(con, args.tu, "done", notes=args.notes)
        log(con, "review_pass", tu_id=args.tu, detail=args.notes)
        con.commit()
        print(f"review PASS -> {args.tu} done")
    else:
        set_tu(con, args.tu, "in_progress", notes=args.notes)
        log(con, "review_fail", tu_id=args.tu, detail=args.notes)
        con.commit()
        print(f"review FAIL -> {args.tu} back to in_progress")
        if args.notes:
            print(f"  notes: {args.notes}")


def cmd_block(args):
    con = connect()
    set_tu(con, args.tu, "blocked", notes=args.reason)
    print(f"blocked {args.tu}: {args.reason}")


def cmd_unblock(args):
    con = connect()
    set_tu(con, args.tu, "todo")
    print(f"unblocked {args.tu}")


def cmd_set(args):
    con = connect()
    set_tu(con, args.tu, args.status, notes=args.note)
    print(f"{args.tu} -> {args.status}")


def cmd_parity(args):
    """Standalone structural parity check (no LLM, no status change)."""
    import parity
    con = connect()
    funcs = con.execute("SELECT * FROM func WHERE tu_id=? ORDER BY name", (args.tu,)).fetchall()
    if not funcs:
        sys.exit(f"unknown TU: {args.tu!r}")
    files = resolve_files(con, args.tu, args.files)
    res = parity.check_tu(funcs, files)
    if res["verdict"] == "SKIP":
        print(f"automated parity: SKIP ({res.get('reason')})")
        return
    print(parity.format_report(res))
    sys.exit(0 if res["verdict"] == "GREEN" else 1)


def cmd_stubs(args):
    import gen_stubs
    sys.argv = ["gen_stubs", args.tu] + (["--list"] if args.list else [])
    gen_stubs.main()


def cmd_auto(args):
    """Deterministic NO-LLM drafting of the provably-mechanical TUs (forwarders +
    compiler thunks). The per-TU compile gate is the judge: a draft that compiles
    and parity-checks GREEN is recorded done gate-only; anything else is reverted
    and left for the agent. See tools/work/auto_draft.py and STRATEGY.md."""
    import auto_draft as ad
    import verify, parity
    identity = json.load(open(IDENTITY, encoding="utf-8"))
    index = json.load(open(TU_INDEX, encoding="utf-8"))

    if args.scan or not args.run:
        sys.argv = ["auto_draft", "--scan"]
        ad.main()
        if not args.run:
            print("\nrun the safe ones end-to-end (draft -> gate -> done) with:  work auto --run [-n N]")
        return

    con = connect()
    # fully-auto decfigs TUs that are still todo (decfigs => we know the dest path)
    todo = {r["id"] for r in con.execute("SELECT id FROM tu WHERE status='todo' AND source='decfigs'")}
    landed = reverted = 0
    for tu_key, t in index.items():
        if landed >= args.n:
            break
        if tu_key not in todo:
            continue
        kinds = ad.func_kinds(t["functions"], identity)
        ks = [k for _, _, k, _ in kinds]
        if not ks or not all(k in ("thunk", "forwarder") for k in ks):
            continue
        dest = ad.dest_for(tu_key, "decfigs")  # None for header-keyed TUs (defs belong in .cpp)
        if not dest:
            continue
        full = os.path.join(ROOT, dest)
        if os.path.exists(full):  # never clobber existing reconstruction work
            print(f"  skip  (dest exists) {tu_key}")
            continue
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(ad.emit_tu(tu_key, kinds))
        status, _glog = verify.compile_gate([dest])
        if status != "pass":
            os.remove(full)
            reverted += 1
            print(f"  skip  ({status}) {tu_key}")
            continue
        funcs = con.execute("SELECT * FROM func WHERE tu_id=? ORDER BY name", (tu_key,)).fetchall()
        pres = parity.check_tu(funcs, [dest]) if parity.load_config().get("automated_check", {}).get("enabled") else {"verdict": "SKIP"}
        if pres["verdict"] in ("RED",):
            print(f"  hold  (compiled, parity {pres['verdict']} — leaving for review) {tu_key}")
            con.execute("UPDATE func SET status='compiles', verify_tier=1 WHERE tu_id=?", (tu_key,))
            set_tu(con, tu_key, "compiled", notes="auto-drafted; parity not green — needs review")
            continue
        # gate-only landing: tier 1 (compiled), NOT tier 2 — no reviewer saw this.
        # The TU is still 'done' by policy (mechanical shapes; the gate is the judge).
        con.execute("UPDATE func SET status='compiles', verify_tier=1, updated_at=? WHERE tu_id=?", (now(), tu_key))
        set_tu(con, tu_key, "done", notes="auto-drafted (deterministic forwarder/thunk); gate-only")
        log(con, "auto_done", tu_id=tu_key, detail=f"parity={pres['verdict']}")
        con.commit()
        landed += 1
        print(f"  DONE  {tu_key}")
    print(f"\nauto: {landed} landed (gate-passed, recorded done), {reverted} reverted to agent")


def cmd_bootstrap(args):
    """One command to make a fresh clone workable and resume where we left off."""
    print("== work bootstrap ==")
    # 1) submodules — two controlled levels, NOT --recursive (the EA libs carry
    #    deeply self-referential test-package submodules that blow past Windows
    #    MAX_PATH). Only init what is NOT already populated, so we never run a
    #    checkout that could clobber uncommitted reconstruction work.
    print("[1/4] git submodules ...", flush=True)
    b5 = os.path.join(ROOT, "b5-decomp")
    if not os.path.exists(os.path.join(b5, "CMakeLists.txt")):
        subprocess.run(["git", "submodule", "update", "--init"], cwd=ROOT)
    else:
        print("  b5-decomp already populated — skipping (won't touch local changes)")
    for name, marker in (("EABase", "include/Common"), ("EASTL", "include"),
                         ("EAThread", "include"), ("renderware", "include")):
        if not os.path.isdir(os.path.join(b5, "vendor", name, marker)):
            subprocess.run(["git", "submodule", "update", "--init", "--", f"vendor/{name}"], cwd=b5)

    # 2) the committed structure must be present (identity/tu_index are in git)
    print("[2/4] checking committed artifacts ...", flush=True)
    missing = [p for p in (IDENTITY, TU_INDEX) if not os.path.exists(p)]
    if missing:
        print(f"  MISSING {', '.join(os.path.basename(m) for m in missing)} — these are committed;"
              " regenerate with build_identity.py / build_tu_index.py (needs .ida-exports).")
    have_exports = os.path.isdir(X360_EXPORTS)
    if not have_exports:
        print("  note: .ida-exports/ absent (git-ignored). The ledger still rebuilds from the")
        print("        committed mirrors, but reconstructing NEW functions (dossier/stubs) needs")
        print("        them — regenerate with: tools/export_db.ps1 -DbName BURNOUT_X360_ARTIST.XEX")

    # 3) (re)build the ledger from committed identity/tu_index + status + dep mirrors
    print("[3/4] building ledger ...", flush=True)
    seed_args = argparse.Namespace(deps=have_exports, reset=False)
    cmd_seed(seed_args)

    # 4) refresh the burnout.wiki type index if the committed cache is stale vs. the
    #    newest dump (the dossier reads references/Wiki/types.json; committed so it
    #    works without Python, rebuilt here so a newer dump takes effect on resume)
    print("[4/4] wiki type index ...", flush=True)
    try:
        import wiki_index
        if wiki_index.needs_rebuild():
            wiki_index.build_index()
        elif wiki_index.newest_dump():
            print("  types.json up to date with newest dump — skipping")
        else:
            print("  no burnoutwiki-*.xml dump present — using committed types.json (if any)")
    except Exception as e:
        print(f"  skipped (wiki index unavailable: {e})")

    print("\n== ready ==  resume with:")
    print("  work status      # what's done")
    print("  work next        # the next leaf-first TU to reconstruct")
    cmd_status(argparse.Namespace())


def main():
    ap = argparse.ArgumentParser(prog="work")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("bootstrap").set_defaults(fn=cmd_bootstrap)
    s = sub.add_parser("seed"); s.add_argument("--deps", action="store_true"); s.add_argument("--reset", action="store_true"); s.set_defaults(fn=cmd_seed)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    g = sub.add_parser("goal", help="scope `next` to a membership goal (see progress/goals.json)")
    g.add_argument("action", nargs="?", default="list",
                   choices=["list", "set", "clear", "show", "import-trace"])
    g.add_argument("name", nargs="?")
    g.add_argument("--trace-dir", help="Xenia funcdata dir for import-trace (default .trace/funcdata)")
    g.set_defaults(fn=cmd_goal)
    n = sub.add_parser("next"); n.add_argument("-n", type=int, default=1); n.set_defaults(fn=cmd_next)
    sh = sub.add_parser("show"); sh.add_argument("tu")
    sh.add_argument("--full", action="store_true", help="emit the full reconstruction dossier")
    sh.add_argument("--asm", action="store_true", help="include assembly in --full output")
    sh.add_argument("-o", "--out", help="write dossier to a file instead of stdout")
    sh.set_defaults(fn=cmd_show)
    st = sub.add_parser("start"); st.add_argument("tu"); st.set_defaults(fn=cmd_start)
    su = sub.add_parser("submit"); su.add_argument("tu"); su.add_argument("--note")
    su.add_argument("--files", nargs="*", help="explicit .cpp paths to compile (else the TU's recorded dest_path)")
    su.set_defaults(fn=cmd_submit)
    rv = sub.add_parser("review"); rv.add_argument("tu")
    rv.add_argument("--verdict", required=True, choices=["pass", "fail"])
    rv.add_argument("--notes"); rv.set_defaults(fn=cmd_review)
    pa = sub.add_parser("parity"); pa.add_argument("tu")
    pa.add_argument("--files", nargs="*", help="explicit .cpp paths (else the TU's recorded dest_path)")
    pa.set_defaults(fn=cmd_parity)
    sb = sub.add_parser("stubs"); sb.add_argument("tu"); sb.add_argument("--list", action="store_true")
    sb.set_defaults(fn=cmd_stubs)
    au = sub.add_parser("auto"); au.add_argument("--scan", action="store_true", help="census of fully-mechanical TUs")
    au.add_argument("--run", action="store_true", help="draft+gate+land the safe ones")
    au.add_argument("-n", type=int, default=25, help="max TUs to land in a --run sweep")
    au.set_defaults(fn=cmd_auto)
    b = sub.add_parser("block"); b.add_argument("tu"); b.add_argument("reason"); b.set_defaults(fn=cmd_block)
    u = sub.add_parser("unblock"); u.add_argument("tu"); u.set_defaults(fn=cmd_unblock)
    se = sub.add_parser("set"); se.add_argument("tu"); se.add_argument("--status", required=True); se.add_argument("--note"); se.set_defaults(fn=cmd_set)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
