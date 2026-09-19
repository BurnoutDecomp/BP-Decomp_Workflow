"""audit_view.py -- what the evidence audits say about ONE translation unit, for agents.

CI runs tools/re/funcaudit.py (every reconstructed body vs the console's own function) and
tools/re/stubaudit.py (every body that is still a stand-in) on every b5-decomp commit and
commits the results as progress/funcaudit.json + progress/stubs.json. The work server draws
its "Verified vs Console" ring from them. This module reads those committed files -- no
server, no IDA exports needed -- and formats the slice that belongs to one TU, so `work show`
and `work audit` put the same evidence in front of the agent that the dashboard shows.

The verdict vocabulary (see funcaudit.py's docstring):
    NO_BODY, MISSING_CASE, EXTRA_CASE, MISSING_EVENT, MISSING_CALLEE, MISSING_ASSERT   HIGH SIGNAL
    MISSING_EVENT?, MISSING_STRING, UNCITED_DATA, FEWER_PARAMS, INFO_*                  context
A TU whose functions carry high-signal findings is NOT verified, whatever its ledger status.

The third tier, progress/asmaudit.json (tools/re/asmaudit.py, run by the build job on every
published exe): each function of the BUILT exe against the console's machine code -- named
callees, conditional-branch count, constants. Tiers A same shape / B close / C diverges /
T trivial. A tier C is a diff to read, not a verdict: `python tools/re/asmaudit.py --func NAME`
prints which callees and constants exist on one side only (`--asm` adds both streams).
"""
from __future__ import annotations

import functools
import json
import os
import posixpath

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FUNCAUDIT = os.path.join(ROOT, "progress", "funcaudit.json")
STUBS = os.path.join(ROOT, "progress", "stubs.json")
ASMAUDIT = os.path.join(ROOT, "progress", "asmaudit.json")
ASM_TIER_TEXT = {"A": "same shape", "B": "close", "C": "DIVERGES", "T": "trivial"}
HIGH_SIGNAL = ("NO_BODY", "MISSING_CASE", "EXTRA_CASE", "MISSING_EVENT", "MISSING_CALLEE", "MISSING_ASSERT")
ORDER = list(HIGH_SIGNAL) + ["MISSING_EVENT?", "MISSING_STRING", "UNCITED_DATA", "FEWER_PARAMS",
                             "INFO_TRUNCATED_CALLEES", "INFO_UNNAMED_CALLEES"]
SRC_PREFIX = "b5-decomp/src/"


@functools.lru_cache(maxsize=None)
def load():
    """(funcaudit, stubs) as committed, or None for a missing/unreadable file."""
    out = []
    for path in (FUNCAUDIT, STUBS):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                out.append(json.load(fh))
        except (OSError, ValueError):
            out.append(None)
    return tuple(out)


@functools.lru_cache(maxsize=None)
def load_asm():
    """progress/asmaudit.json as committed by the build job, or None."""
    try:
        with open(ASMAUDIT, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


@functools.lru_cache(maxsize=None)
def _asm_index():
    """canonical name -> asmaudit row (tiers A/B/C/T only; X is a count in the stats)."""
    data = load_asm()
    if not data:
        return {}
    return {r.get("name"): r for r in data.get("results") or []}


@functools.lru_cache(maxsize=None)
def _indexes():
    fa, st = load()
    by_name = {}
    by_file = {}
    if fa:
        for r in fa.get("results") or []:
            by_name[r.get("name")] = r
            by_file.setdefault(r.get("file") or r.get("tu") or "", []).append(r)
    stubs_by_file = {}
    if st:
        for r in st.get("rows") or []:
            stubs_by_file.setdefault(r.get("file") or "", []).append(r)
    return by_name, by_file, stubs_by_file


def audit_file_for_dest(dest_path):
    if not dest_path:
        return None
    p = dest_path.replace("\\", "/")
    p = posixpath.normpath(p)
    if p.startswith(SRC_PREFIX):
        p = p[len(SRC_PREFIX):]
    return p


def weight(findings):
    return sum(len(v) for k, v in (findings or {}).items() if k in HIGH_SIGNAL)


def tu_slice(dest_path, func_names):
    """Findings for these functions (by canonical name) + the stubs in the TU's file."""
    by_name, by_file, stubs_by_file = _indexes()
    file = audit_file_for_dest(dest_path)
    found = {n: by_name[n] for n in func_names if n in by_name}
    # functions the ledger files elsewhere but the audit found in this file
    if file:
        for r in by_file.get(file, []):
            found.setdefault(r.get("name"), r)
    stubs = stubs_by_file.get(file, []) if file else []
    return file, found, stubs


def totals_line():
    fa, st = load()
    if not fa:
        return "console audit: progress/funcaudit.json not found (CI writes it on every b5-decomp commit)"
    s = fa.get("stats") or {}
    meta = fa.get("meta") or {}
    paired = int(s.get("paired") or 0)
    clean = int(s.get("clean") or 0)
    pct = (100.0 * clean / paired) if paired else 0.0
    line = (f"console audit @ b5 {str(meta.get('b5_commit') or '')[:12]}: {clean}/{paired} paired bodies clean "
            f"({pct:.1f}% verified), {int(s.get('no_body') or 0)} named with no body, "
            f"{int(s.get('unpaired_no_file') or 0)} not audited")
    if st:
        ss = st.get("stats") or {}
        line += f"; stubs {int(ss.get('stubs') or 0)} ({int(ss.get('live') or 0)} on live paths)"
    asm = load_asm()
    if asm:
        a = asm.get("stats") or {}
        line += (f"\ninstruction shape of the built exe (b5 {str((asm.get('meta') or {}).get('b5_commit') or '')[:12]}): "
                 f"{int(a.get('A') or 0)}/{int(a.get('scoreable') or 0)} same shape ({a.get('shape_percent')}%), "
                 f"{int(a.get('C') or 0)} diverge, {int(a.get('not_in_exe') or 0)} named but not in the exe")
    return line


def format_asm(func_names, file=None, max_funcs=20):
    """The instruction-shape rows for these functions (plus the file's), worst first."""
    idx = _asm_index()
    if not idx:
        return ""
    rows = {n: idx[n] for n in func_names if n in idx}
    if file:
        for n, r in idx.items():
            if r.get("file") == file:
                rows.setdefault(n, r)
    if not rows:
        return "  instruction shape: none of these functions is in the built exe (not linked, inlined, or not written)"
    tiers = {}
    for r in rows.values():
        tiers[r.get("tier")] = tiers.get(r.get("tier"), 0) + 1
    meta = load_asm().get("meta") or {}
    lines = [f"  instruction shape (built exe of b5 {str(meta.get('b5_commit') or '')[:12]}): "
             f"{len(rows)} in the exe -- " + ", ".join(f"{tiers.get(t, 0)} {t} {ASM_TIER_TEXT[t].lower()}" for t in "ABCT" if tiers.get(t))]
    ranked = sorted(rows.values(), key=lambda r: (101 if r.get("score") is None else r["score"]))
    for r in ranked[:max_funcs]:
        if r.get("tier") == "A":
            continue
        c = r.get("counts") or {}
        d = r.get("diff") or {}
        n = c.get("n") or [0, 0]
        cond = c.get("cond") or [0, 0]
        lines.append(f"    [{r.get('tier')} {r.get('score') if r.get('score') is not None else '--':>5}] {r.get('name')} "
                     f"@{r.get('addr')}  console {n[0]} / pc {n[1]} insns, branches {cond[0]}/{cond[1]}")
        if d.get("calls_only_console"):
            lines.append(f"        callees only on the console: {', '.join(d['calls_only_console'])}"
                         + (f" (+{d['calls_only_console_n'] - len(d['calls_only_console'])})" if d.get("calls_only_console_n", 0) > len(d["calls_only_console"]) else ""))
        if d.get("calls_only_pc"):
            lines.append(f"        callees only in our exe    : {', '.join(d['calls_only_pc'])}")
        if d.get("imm_only_console"):
            lines.append(f"        constants only on the console: {d['imm_only_console']}")
        if d.get("imm_only_pc"):
            lines.append(f"        constants only in our exe    : {d['imm_only_pc']}")
        for note in r.get("notes") or []:
            lines.append(f"        note: {note}")
    if len(ranked) > max_funcs:
        lines.append(f"    ... +{len(ranked) - max_funcs} more; python tools/re/asmaudit.py --func NAME [--asm] for one function")
    return "\n".join(lines)


def format_tu(dest_path, func_names, limit_items=6, max_funcs=40):
    """Human-readable block for `work show` / `work audit`."""
    fa, st = load()
    if not fa:
        return ("console audit: progress/funcaudit.json is not in this checkout -- pull main, or run\n"
                "  python tools/re/funcaudit.py --tu <file> --cache progress/funcaudit_features.json.gz")
    file, found, stubs = tu_slice(dest_path, func_names)
    meta = fa.get("meta") or {}
    lines = [f"console audit (b5 {str(meta.get('b5_commit') or '')[:12]}, {meta.get('generated_at') or '?'}; "
             f"file {file or '(no destination)'}):"]
    if not found and not stubs:
        lines.append("  nothing the audit can name differs in this TU; not proof of a match "
                     "(inlined callees, virtual dispatch, argument order and constant VALUES are invisible to it)")
        asm_block = format_asm(func_names, file, max_funcs=max_funcs)
        if asm_block:
            lines.append(asm_block)
        return "\n".join(lines)
    hi = sum(weight(r.get("findings")) for r in found.values())
    no_body = [n for n, r in found.items() if "NO_BODY" in (r.get("findings") or {})]
    lines.append(f"  {len(found)} function(s) with findings, {hi} high-signal item(s), "
                 f"{len(no_body)} named with no body, {len(stubs)} stub bod(ies) in the file "
                 f"({sum(1 for s in stubs if s.get('live_callers'))} on live paths)")
    ranked = sorted(found.values(), key=lambda r: -weight(r.get("findings")))
    for r in ranked[:max_funcs]:
        f = r.get("findings") or {}
        w = weight(f)
        flag = " (flagged in source)" if r.get("flagged") else ""
        lines.append(f"  [{w:>3} hs] {r.get('name')} @{r.get('addr') or '?'} line {r.get('line') or '?'}{flag}")
        for cat in sorted(f, key=lambda c: ORDER.index(c) if c in ORDER else 99):
            if cat.startswith("INFO_"):
                continue
            items = f[cat]
            shown = "; ".join(str(x) for x in items[:limit_items])
            more = f" (+{len(items) - limit_items} more)" if len(items) > limit_items else ""
            lines.append(f"      {cat:<15} {shown}{more}")
    if len(ranked) > max_funcs:
        lines.append(f"  ... +{len(ranked) - max_funcs} more functions with findings")
    if stubs:
        lines.append("  stub bodies in this file:")
        for s in sorted(stubs, key=lambda s: ({"HIGH": 0, "MEDIUM": 1}.get(s.get("tier"), 2), s.get("line") or 0)):
            live = f" LIVE via {', '.join(s.get('live_callers') or [])}" if s.get("live_callers") else ""
            size = f", console {s.get('console_lines')} lines" if s.get("console_lines") is not None else ""
            lines.append(f"    [{s.get('tier'):<6}] {s.get('name')} (line {s.get('line')}, {s.get('why')}{size}){live}")
    asm_block = format_asm(func_names, file, max_funcs=max_funcs)
    if asm_block:
        lines.append(asm_block)
    lines.append("  re-run live for this file: python tools/re/funcaudit.py --tu <file> "
                 "--cache progress/funcaudit_features.json.gz  (and stubaudit.py --file <file>; "
                 "asmaudit.py --tu <file> needs a built exe)")
    return "\n".join(lines)
