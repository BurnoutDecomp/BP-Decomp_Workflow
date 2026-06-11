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
    work next [-n N] [--any]  the next leaf-first ready TU(s) to work on
    work show <tu>            dossier for a TU (functions, signatures, deps)
    work start <tu>           claim a TU (todo -> in_progress)
    work submit <tu>          mark a TU reconstructed (compile/review gates: Phase 3)
    work block <tu> "reason"  mark blocked; work unblock <tu> to clear
    work set <tu> --status S  manual status override

Run as:  python tools/work/work.py <cmd>   (or the work.cmd shim from repo root)
"""
import argparse, json, os, sqlite3, subprocess, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_skeleton import signature_from_pseudocode, load_export  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(ROOT, "progress", "identity.json")
TU_INDEX = os.path.join(ROOT, "progress", "tu_index.json")
DB = os.path.join(ROOT, "progress", "ledger.sqlite")
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

    if args.deps:
        build_deps(con, identity)
    con.close()


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
    con.execute("DELETE FROM tu_dep")
    con.executemany("INSERT INTO tu_dep(tu_id,dep_id,weight) VALUES(?,?,?)",
                    [(t, d, w) for (t, d), w in edges.items()])
    con.commit()
    print(f"  {len(edges)} TU->TU dependency edges")


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


# ---------------------------------------------------------------- next
def cmd_next(args):
    con = connect()
    has_deps = con.execute("SELECT COUNT(*) FROM tu_dep").fetchone()[0] > 0
    # rank todo TUs by (# dependency TUs not yet done) asc -> leaves first,
    # then decfigs-sourced first, then smallest first.
    if has_deps:
        q = """
        SELECT t.id, t.source, t.n_funcs, t.dest_path,
          (SELECT COUNT(*) FROM tu_dep d JOIN tu dt ON dt.id=d.dep_id
            WHERE d.tu_id=t.id AND dt.status NOT IN ('done')) AS unresolved
        FROM tu t WHERE t.status='todo'
        ORDER BY unresolved ASC, (t.source='decfigs') DESC, t.n_funcs ASC
        LIMIT ?"""
    else:
        q = """SELECT t.id,t.source,t.n_funcs,t.dest_path, NULL AS unresolved
        FROM tu t WHERE t.status='todo'
        ORDER BY (t.source='decfigs') DESC, t.n_funcs ASC LIMIT ?"""
    rows = con.execute(q, (args.n,)).fetchall()
    if not rows:
        print("no todo TUs — run `work status`")
        return
    for r in rows:
        dep = "" if r["unresolved"] is None else f"  unresolved-deps={r['unresolved']}"
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


def cmd_start(args):
    con = connect()
    set_tu(con, args.tu, "in_progress", owner=os.environ.get("WORK_AGENT", "agent"))
    print(f"started {args.tu}")
    cmd_show(args)


def resolve_files(con, tu, explicit):
    """The .cpp file(s) to compile for this TU: explicit > dest_path > git-detected."""
    if explicit:
        return explicit
    files = []
    row = con.execute("SELECT dest_path FROM tu WHERE id=?", (tu,)).fetchone()
    if row and row["dest_path"] and os.path.exists(os.path.join(ROOT, row["dest_path"])):
        files.append(row["dest_path"])
    if not files:
        # fall back to modified/untracked .cpp in the b5-decomp submodule
        try:
            out = subprocess.run(["git", "-C", os.path.join(ROOT, "b5-decomp"),
                                  "status", "--porcelain", "--", "src"],
                                 capture_output=True, text=True).stdout
            for ln in out.splitlines():
                p = ln[3:].strip()
                if p.endswith(".cpp"):
                    files.append("b5-decomp/" + p)
        except Exception:
            pass
    return files


def cmd_submit(args):
    import verify
    con = connect()
    funcs = con.execute("SELECT * FROM func WHERE tu_id=? ORDER BY name", (args.tu,)).fetchall()
    if not funcs:
        sys.exit(f"unknown TU: {args.tu!r}")
    files = resolve_files(con, args.tu, args.files)
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
    packet = verify.reviewer_packet(con, dict_row(con, "tu", args.tu), funcs, files)
    con.commit()
    print(f"\nreviewer packet -> {os.path.relpath(packet, ROOT)}")
    print("Next: spawn a FRESH-EYES reviewer sub-agent with that packet (it should not see")
    print("your reconstruction reasoning), then record the verdict:")
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


def main():
    ap = argparse.ArgumentParser(prog="work")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("seed"); s.add_argument("--deps", action="store_true"); s.add_argument("--reset", action="store_true"); s.set_defaults(fn=cmd_seed)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    n = sub.add_parser("next"); n.add_argument("-n", type=int, default=1); n.set_defaults(fn=cmd_next)
    sh = sub.add_parser("show"); sh.add_argument("tu")
    sh.add_argument("--full", action="store_true", help="emit the full reconstruction dossier")
    sh.add_argument("--asm", action="store_true", help="include assembly in --full output")
    sh.add_argument("-o", "--out", help="write dossier to a file instead of stdout")
    sh.set_defaults(fn=cmd_show)
    st = sub.add_parser("start"); st.add_argument("tu"); st.set_defaults(fn=cmd_start)
    su = sub.add_parser("submit"); su.add_argument("tu"); su.add_argument("--note")
    su.add_argument("--files", nargs="*", help="explicit .cpp paths to compile (else dest_path / git-detected)")
    su.set_defaults(fn=cmd_submit)
    rv = sub.add_parser("review"); rv.add_argument("tu")
    rv.add_argument("--verdict", required=True, choices=["pass", "fail"])
    rv.add_argument("--notes"); rv.set_defaults(fn=cmd_review)
    b = sub.add_parser("block"); b.add_argument("tu"); b.add_argument("reason"); b.set_defaults(fn=cmd_block)
    u = sub.add_parser("unblock"); u.add_argument("tu"); u.set_defaults(fn=cmd_unblock)
    se = sub.add_parser("set"); se.add_argument("tu"); se.add_argument("--status", required=True); se.add_argument("--note"); se.set_defaults(fn=cmd_set)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
