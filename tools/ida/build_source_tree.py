"""Compact the raw DecFIGS lineinfo dump into usable source-structure artifacts.

Input:  <db>.lineinfo.json  (from tools/ida/export_lineinfo.py) -- per-instruction
        {func -> {name, rows:[{ea,file,line,src}]}}, ~hundreds of MB.

Outputs (next to the input, prefixed `decfigs_`):
  decfigs_func_files.json   func_addr -> {name, primary_file, span_count,
                                          inlined_files:[...]}   (compact, shippable)
  decfigs_source_tree.txt   sorted unique normalized source files = the original
                            source-tree skeleton the recovered C++ should mirror
  decfigs_inlining.json     func_addr -> ordered spans
                            [{file, n_instr, first_ea, last_ea, line_lo, line_hi,
                              inlined}]  -- inlined==True where the span's file
                            differs from the function's primary (home) file

Run:  python tools/ida/build_source_tree.py ["IDA Files/DecFIGS_..._PS3.ELF.lineinfo.json"]
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = ROOT / "IDA Files" / "DecFIGS_Burnout_Internal_PS3.ELF.lineinfo.json"

# Build-machine prefixes to strip so paths become repo-relative. The real tree
# root is everything from `Code/` onward (e.g. Code/GameSource/...).
_PREFIX_RE = re.compile(r"^.*?[/\\]Code[/\\]", re.IGNORECASE)


def normalize(path: str | None) -> str | None:
    if not path:
        return None
    p = path.replace("\\", "/")
    m = _PREFIX_RE.search(path)
    if m:
        p = path[m.end():].replace("\\", "/")
    return p.lstrip("/")


def main() -> None:
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN
    if not in_path.exists():
        sys.exit(f"input not found: {in_path}")
    data = json.loads(in_path.read_text(encoding="utf-8"))

    func_files: dict[str, dict] = {}
    inlining: dict[str, list] = {}
    all_files: Counter[str] = Counter()
    funcs_with_inlining = 0

    for faddr, fobj in data.items():
        rows = fobj.get("rows") or []
        if not rows:
            continue
        # Build spans: consecutive instructions sharing a (normalized) file.
        spans: list[dict] = []
        cur = None
        last_line = None
        for r in rows:
            nf = normalize(r.get("file"))
            ln = r.get("line")
            if ln is not None:
                last_line = ln
            if nf is None:
                # no file at this ea; extend current span's range if any
                if cur is not None:
                    cur["last_ea"] = r["ea"]
                    cur["n_instr"] += 1
                continue
            if cur is None or nf != cur["file"]:
                cur = {"file": nf, "n_instr": 1, "first_ea": r["ea"],
                       "last_ea": r["ea"], "line_lo": ln, "line_hi": ln}
                spans.append(cur)
            else:
                cur["n_instr"] += 1
                cur["last_ea"] = r["ea"]
                if ln is not None:
                    cur["line_lo"] = ln if cur["line_lo"] is None else min(cur["line_lo"], ln)
                    cur["line_hi"] = ln if cur["line_hi"] is None else max(cur["line_hi"], ln)
        if not spans:
            continue
        # Where the function LIVES = the file its entry/prologue maps to (first
        # span). The "most instructions" file is often just a heavily-inlined
        # header (containers, math, logging) and is NOT the definition site.
        entry_file = spans[0]["file"]
        by_file: Counter[str] = Counter()
        for s in spans:
            by_file[s["file"]] += s["n_instr"]
            all_files[s["file"]] += s["n_instr"]
        dominant = by_file.most_common(1)[0][0]
        for s in spans:
            s["inlined"] = s["file"] != entry_file
        inlined_files = sorted({s["file"] for s in spans if s["inlined"]})
        if inlined_files:
            funcs_with_inlining += 1

        func_files[faddr] = {
            "name": fobj.get("name"),
            "home_file": entry_file,        # where the function is defined
            "dominant_file": dominant,      # file with the most (often inlined) code
            "span_count": len(spans),
            "inlined_files": inlined_files,
        }
        inlining[faddr] = spans

    out_dir = ROOT / "references" / "DecFIGS"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "decfigs_func_files.json").write_text(
        json.dumps(func_files, indent=0), encoding="utf-8")
    (out_dir / "decfigs_inlining.json").write_text(
        json.dumps(inlining, indent=2), encoding="utf-8")
    tree = sorted(all_files)
    (out_dir / "decfigs_source_tree.txt").write_text(
        "\n".join(tree) + "\n", encoding="utf-8")

    print(f"functions with attribution : {len(func_files)}")
    print(f"functions showing inlining : {funcs_with_inlining} "
          f"(>1 source file in body)")
    print(f"unique source files (tree) : {len(tree)}")
    print(f"outputs in {out_dir}:")
    print("  decfigs_func_files.json, decfigs_inlining.json, decfigs_source_tree.txt")
    print("\nTop 15 source files by instruction count:")
    for f, n in all_files.most_common(15):
        print(f"  {n:>8}  {f}")


if __name__ == "__main__":
    main()
