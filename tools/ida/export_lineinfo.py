"""IDAPython: export per-instruction source file/line attribution from an IDB.

Purpose: the DecFIGS Internal PS3 build carries DWARF line info (origin source
file + line for every instruction, including inlined code). That data did NOT
survive into the Ghidra XML/JSON exports, so we read it straight from the `.i64`.

This script is DIAGNOSTIC-FIRST. The DWARF line table can live in several places
in an IDB depending on how it was imported (regular/repeatable comments,
anterior "extra" comment lines, or IDA's source-line subsystem). The first run
probes all of them, prints a capability report, and aborts early if none carry
origin info — so we learn the real storage form in one headless launch instead
of guessing. When origin info is found, it writes the full map to JSON.

Run headless:
    idat.exe -A -S"tools/ida/export_lineinfo.py" "IDA Files/DecFIGS_..._PS3.ELF.i64"
Output (next to the .i64, or LINEINFO_OUT):
    <db>.lineinfo.json     full map: function -> [{ea, file, line, raw, src}]
    <db>.lineinfo.txt      probe/summary report
Env:
    LINEINFO_OUT   override output path stem
    LINEINFO_MAX   stop after N functions (0 = all; default 0)
    LINEINFO_PROBE_N  abort-early threshold of funcs to scan before giving up
                      if zero origin info seen (default 800)
"""
import json
import os
import re

import ida_auto
import ida_bytes
import ida_funcs
import ida_lines
import idautils
import idc

ida_auto.auto_wait()

DB = idc.get_idb_path()
STEM = os.environ.get("LINEINFO_OUT") or os.path.splitext(DB)[0] + ".lineinfo"
OUT_JSON = STEM + ".json"
OUT_TXT = STEM + ".txt"
MAX = int(os.environ.get("LINEINFO_MAX", "0") or "0")
PROBE_N = int(os.environ.get("LINEINFO_PROBE_N", "0") or "0")

# Patterns that look like origin file/line attribution in a comment string.
FILE_LINE_RE = re.compile(
    r"([A-Za-z0-9_./\\-]+\.(?:cpp|c|h|hpp|inl|cc))(?:[ :]+line[ :]*|[ :]+)(\d+)",
    re.IGNORECASE,
)


def _capability_report():
    """List source-line-ish APIs available in this IDA build (printed once)."""
    found = []
    for modname in ("ida_nalt", "ida_lines", "ida_bytes", "idc"):
        try:
            mod = __import__(modname)
        except Exception:
            continue
        for attr in dir(mod):
            low = attr.lower()
            if any(k in low for k in ("source", "srcfile", "linnum", "lineno", "src_")):
                found.append(f"{modname}.{attr}")
    return found


import ida_nalt

_BAD = (None, idc.BADADDR, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF, -1)


def _source_lineinfo(ea):
    """(file, line) from IDA's DWARF source-line subsystem, or (None, None)."""
    sf = None
    try:
        sf = ida_lines.get_sourcefile(ea)  # str path, or None
    except Exception:
        sf = None
    ln = None
    try:
        v = ida_nalt.get_source_linnum(ea)
        if v not in _BAD:
            ln = int(v)
    except Exception:
        ln = None
    if ln is None:
        try:
            v = idc.get_source_linnum(ea)
            if v not in _BAD:
                ln = int(v)
        except Exception:
            ln = None
    return (sf or None), ln


def _harvest(ea):
    """Return list of (src_tag, text) origin candidates at this address.

    Primary source is IDA's DWARF source-line subsystem; comments/anterior are
    kept as fallbacks in case some builds stash attribution there.
    """
    out = []
    sf, ln = _source_lineinfo(ea)
    if sf is not None or ln is not None:
        out.append(("srcline", "%s line %s" % (sf or "?", ln if ln is not None else "?")))
    c = ida_bytes.get_cmt(ea, False)
    if c:
        out.append(("cmt", c))
    rc = ida_bytes.get_cmt(ea, True)
    if rc:
        out.append(("rcmt", rc))
    i = 0
    while i < 32:
        line = ida_lines.get_extra_cmt(ea, ida_lines.E_PREV + i)
        if line is None:
            break
        if line:
            out.append(("ant", line))
        i += 1
    return out


def _parse(text):
    m = FILE_LINE_RE.search(text)
    if m:
        return m.group(1), int(m.group(2))
    return None, None


def main():
    caps = _capability_report()
    src_counter = {}
    fileline_hits = 0
    raw_hits = 0
    functions = {}
    samples = []
    scanned_funcs = 0

    for fva in idautils.Functions():
        if MAX and scanned_funcs >= MAX:
            break
        scanned_funcs += 1
        f = ida_funcs.get_func(fva)
        if not f:
            continue
        fname = ida_funcs.get_func_name(fva) or ("sub_%X" % fva)
        rows = []
        for ea in idautils.Heads(f.start_ea, f.end_ea):
            # Primary: structured DWARF source-line subsystem.
            sf, ln = _source_lineinfo(ea)
            if sf is not None or ln is not None:
                raw_hits += 1
                src_counter["srcline"] = src_counter.get("srcline", 0) + 1
                fileline_hits += 1
                rows.append({"ea": "%X" % ea, "file": sf, "line": ln, "src": "srcline"})
                if len(samples) < 25:
                    samples.append("0x%X  [srcline]  %s : %s" % (ea, sf, ln))
                continue
            # Fallback: attribution stashed in comments/anterior lines.
            cands = _harvest(ea)
            if not cands:
                continue
            raw_hits += 1
            for src, text in cands:
                src_counter[src] = src_counter.get(src, 0) + 1
            filep, line = None, None
            for src, text in cands:
                filep, line = _parse(text)
                if filep:
                    break
            if filep:
                fileline_hits += 1
                rows.append({"ea": "%X" % ea, "file": filep, "line": line, "src": "cmt"})
                if len(samples) < 25:
                    samples.append("0x%X  [cmt]  %s:%d" % (ea, filep, line))
            elif len(samples) < 25:
                s, t = cands[0]
                samples.append("0x%X  [%s]  RAW: %s" % (ea, s, t[:80]))
        if rows:
            functions["%X" % fva] = {"name": fname, "rows": rows}

        # Early abort only if explicitly enabled (PROBE_N > 0). Disabled by
        # default: low-address EA/SDK functions legitimately carry no game-source
        # lines, so a small prefix of misses says nothing.
        if PROBE_N and scanned_funcs >= PROBE_N and fileline_hits == 0:
            break

    report = []
    report.append("DB: %s" % DB)
    report.append("source-line-ish APIs in this build: %s"
                  % (", ".join(caps) or "(none)"))
    report.append("functions scanned: %d" % scanned_funcs)
    report.append("instructions with ANY comment/anterior/etc: %d" % raw_hits)
    report.append("instructions with parsed file:line: %d" % fileline_hits)
    report.append("functions with attribution: %d" % len(functions))
    report.append("harvest-source counts: %s" % json.dumps(src_counter))
    report.append("")
    report.append("SAMPLES:")
    report.extend(samples)
    if fileline_hits == 0:
        report.append("")
        report.append(">>> NO file:line attribution found via comments/anterior/"
                      "source-line API. The DWARF line table is not reachable this "
                      "way; need a different extraction (e.g. libdwarf on the ELF, "
                      "or the DWARF plugin's own store).")

    with open(OUT_TXT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(report))
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(functions, fh)

    print("[LINEINFO] wrote %s and %s" % (OUT_TXT, OUT_JSON))
    print("[LINEINFO] file:line hits = %d across %d functions"
          % (fileline_hits, len(functions)))
    idc.qexit(0 if fileline_hits or raw_hits else 2)


main()
