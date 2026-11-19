"""The byte-match ledger: committed records in, the published summary out.

Pure Python with no Windows or image dependency, so CI imports it to publish the
summary on every commit of the native branch.

  progress/bytematch/universe.json.gz   every ARTIST function: address, size, name,
                                        category (game | sdk | unnamed), area, TU.
                                        Built locally (`work match universe`).
  progress/bytematch/objects/<src>.json one record per native source file: the commit
                                        and source blob it was measured at, and every
                                        function its object defines with its verdict.
                                        Written by `work match measure --record`.
  progress/bytematch/state.json         the commit at which every record was last proven
                                        current (`work match refresh --record`).
  progress/bytematch.json               the published summary: universe x records x the
  progress/BYTEMATCH.md                 head of the native branch. CI owns these two.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import datetime as _dt
import gzip
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "progress" / "bytematch"
RECORDS = LEDGER / "objects"
UNIVERSE = LEDGER / "universe.json.gz"
STATE = LEDGER / "state.json"
SUMMARY = REPO / "progress" / "bytematch.json"
REPORT = REPO / "progress" / "BYTEMATCH.md"
SCHEMA = 1
BRANCH = "x360"

STATUSES = ("exact", "nonmatching", "missing", "sdk", "unnamed")
RANK = {"exact": 3, "nonmatching": 2}


def now_iso():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------- records
def record_path(source: str, root: Path = RECORDS) -> Path:
    return root / (source + ".json")


def dump_record(record: dict) -> str:
    """One field per line and one function per line, so a re-measure diffs cleanly."""
    head = {k: v for k, v in record.items() if k != "functions"}
    lines = ["{"]
    for key in sorted(head):
        lines.append(f" {json.dumps(key)}: {json.dumps(head[key], sort_keys=True)},")
    functions = record.get("functions", [])
    lines.append(' "functions": [')
    for n, fn in enumerate(functions):
        lines.append("  " + json.dumps(fn, sort_keys=True) + ("," if n + 1 < len(functions) else ""))
    lines.append(" ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _same_measurement(old_text: str, record: dict) -> bool:
    """True when the stored record says what the new one says, measured at another time."""
    try:
        old = json.loads(old_text)
    except ValueError:
        return False
    return ({k: v for k, v in old.items() if k != "measured"} ==
            {k: v for k, v in json.loads(json.dumps(record)).items() if k != "measured"})


def write_record(record: dict, root: Path = RECORDS) -> Path:
    """Store a record; an unchanged measurement keeps its file (and its old time), so a full
    re-measure touches only the records whose content changed."""
    path = record_path(record["source"], root)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dump_record(record)
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if old == text or _same_measurement(old, record):
            return path
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def load_records(root: Path = RECORDS):
    out = []
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("schema") != SCHEMA:
            raise ValueError(f"{path}: schema {record.get('schema')}, expected {SCHEMA}")
        expected = path.relative_to(root).as_posix()[: -len(".json")]
        if record.get("source") != expected:
            raise ValueError(f"{path}: records source {record.get('source')!r}, its path says {expected!r}")
        out.append(record)
    return out


def load_universe(path: Path = UNIVERSE):
    with open(path, "rb") as fh:
        return json.loads(gzip.decompress(fh.read()))


def write_universe(universe: dict, path: Path | None = None):
    path = path or UNIVERSE
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(universe, sort_keys=True, separators=(",", ":")).encode()
    with open(path, "wb") as fh:
        fh.write(gzip.compress(data, mtime=0))


def load_state(path: Path = STATE):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


# ---------------------------------------------------------------------------- summary
def best_verdicts(records):
    """{ARTIST address: (row, source)}: an exact copy anywhere wins, then the best score.

    Inline and template functions are emitted into every object that uses them; the
    linker keeps one copy, so the best measured copy is the function's verdict.
    """
    best = {}
    for record in records:
        for row in record.get("functions", []):
            address = row.get("artist")
            if not address or row.get("status") not in RANK:
                continue
            key = (RANK[row["status"]], row.get("score", 0.0))
            current = best.get(address)
            if current is None or key > current[0] or (key == current[0] and record["source"] < current[2]):
                best[address] = (key, row, record["source"])
    return {address: (row, source) for address, (_, row, source) in best.items()}


def staleness(records, head_blobs):
    """{source: "current" | "changed" | "deleted"} against the branch head's blobs.

    head_blobs maps a repo path to its blob id at the head commit (None: not checked).
    Only the source file itself is compared; headers are covered by `work match
    refresh`, which re-measures every object whose include closure changed and then
    advances state.json's verified commit.
    """
    out = {}
    for record in records:
        source = record["source"]
        if head_blobs is None:
            out[source] = "current"
        elif source not in head_blobs:
            out[source] = "deleted"
        elif head_blobs[source] != record.get("blob"):
            out[source] = "changed"
        else:
            out[source] = "current"
    return out


def _bucket():
    return {"functions": 0, "bytes": 0, "exact": 0, "exact_bytes": 0, "nonmatching": 0,
            "nonmatching_bytes": 0, "missing": 0, "missing_bytes": 0, "fuzzy_bytes": 0.0}


def _add(bucket, status, size, score):
    bucket["functions"] += 1
    bucket["bytes"] += size
    if status in ("exact", "nonmatching", "missing"):
        bucket[status] += 1
        bucket[status + "_bytes"] += size
    bucket["fuzzy_bytes"] += size * (score or 0.0) / 100.0


def build_summary(universe, records, *, head=None, head_blobs=None, state=None, behind=None,
                  previous=None, generated_at=None):
    generated_at = generated_at or now_iso()
    state = state or {}
    verdicts = best_verdicts(records)
    stale = staleness(records, head_blobs)
    stale_sources = {s for s, v in stale.items() if v != "current"}
    first_exact = dict((previous or {}).get("first_exact", {}))

    totals = {"game": _bucket(), "sdk": {"functions": 0, "bytes": 0}, "unnamed": {"functions": 0, "bytes": 0}}
    areas = defaultdict(_bucket)
    rows = []
    sources = sorted({r["source"] for r in records})
    source_index = {s: i for i, s in enumerate(sources)}
    area_names = sorted({row[4] or "unassigned" for row in universe["functions"]})
    area_index = {a: i for i, a in enumerate(area_names)}
    tu_names = sorted({row[5] for row in universe["functions"] if row[5]})
    tu_index = {u: i for i, u in enumerate(tu_names)}
    for address, size, name, category, area, tu in universe["functions"]:
        verdict = verdicts.get(address)
        if category == "sdk":
            status, score, source = "sdk", 100.0, None
            totals["sdk"]["functions"] += 1
            totals["sdk"]["bytes"] += size
        elif category == "unnamed":
            status, score, source = "unnamed", 0.0, None
            totals["unnamed"]["functions"] += 1
            totals["unnamed"]["bytes"] += size
        else:
            if verdict:
                row, source = verdict
                status, score = row["status"], float(row.get("score", 0.0))
            else:
                status, score, source = "missing", 0.0, None
            _add(totals["game"], status, size, score)
            _add(areas[area or "unassigned"], status, size, score)
            if status == "exact":
                first_exact.setdefault(address, [head, generated_at])
            else:
                first_exact.pop(address, None)
        rows.append([address, name, size, status, score,
                     source_index[source] if source is not None else -1,
                     1 if source in stale_sources else 0, area_index[area or "unassigned"],
                     tu_index[tu] if tu else -1])

    files = []
    by_source = defaultdict(_bucket)
    unpaired = Counter()
    for record in records:
        unpaired[record["source"]] += int(record.get("unpaired", 0))
        for row in record.get("functions", []):
            if row.get("status") == "unpaired":
                unpaired[record["source"]] += 1
    for address, row in ((r[0], r) for r in rows if r[5] >= 0):
        _add(by_source[sources[row[5]]], row[3], row[2], row[4])
    for record in records:
        source = record["source"]
        bucket = by_source.get(source, _bucket())
        files.append({"source": source, "commit": record.get("commit"), "measured": record.get("measured"),
                      "compiled": bool(record.get("compiled", True)), "stale": stale[source],
                      "unpaired": unpaired[source], **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in bucket.items()}})

    game = totals["game"]
    game["fuzzy_bytes"] = round(game["fuzzy_bytes"], 1)
    # The whole image is the real denominator: every ARTIST function, whoever provides it.
    # "matched" = byte-identical to ARTIST: exact from our source, or linked from the XDK.
    totals["all"] = {
        "functions": game["functions"] + totals["sdk"]["functions"] + totals["unnamed"]["functions"],
        "bytes": game["bytes"] + totals["sdk"]["bytes"] + totals["unnamed"]["bytes"],
        "matched": game["exact"] + totals["sdk"]["functions"],
        "matched_bytes": game["exact_bytes"] + totals["sdk"]["bytes"],
    }
    objects = {"sources": len(records), "compiled": sum(1 for r in records if r.get("compiled", True)),
               "stale": len(stale_sources), "unpaired": sum(unpaired.values())}
    area_rows = []
    for area, bucket in areas.items():
        bucket["fuzzy_bytes"] = round(bucket["fuzzy_bytes"], 1)
        area_rows.append({"area": area, **bucket})
    area_rows.sort(key=lambda a: (-a["bytes"], a["area"]))
    recent = sorted(((v[1], a) for a, v in first_exact.items() if v and v[1]), reverse=True)[:50]
    names = {r[0]: r for r in rows}
    meta = {"schema": SCHEMA, "branch": BRANCH, "b5_commit": head, "generated_at": generated_at,
            "verified_commit": state.get("verified_commit"), "verified_at": state.get("verified_at"),
            "behind": behind, "toolchain": state.get("toolchain"),
            "universe": universe.get("meta", {})}
    return {
        "meta": meta,
        "totals": {**totals, "objects": objects},
        "areas": area_rows,
        "files": sorted(files, key=lambda f: f["source"]),
        "sources": sources,
        "area_names": area_names,
        "tu_names": tu_names,
        "columns": ["artist", "name", "size", "status", "score", "source", "stale", "area", "tu"],
        "functions": rows,
        "first_exact": {a: first_exact[a] for a in sorted(first_exact)},
        "recent": [{"artist": a, "name": names[a][1] if a in names else None, "size": names[a][2] if a in names else 0,
                    "source": sources[names[a][5]] if a in names and names[a][5] >= 0 else None,
                    "commit": first_exact[a][0], "at": when} for when, a in recent],
    }


def pct(part, whole):
    return f"{100.0 * part / whole:.2f}%" if whole else "n/a"


def render_markdown(summary) -> str:
    meta, totals = summary["meta"], summary["totals"]
    game, sdk, unnamed = totals["game"], totals["sdk"], totals["unnamed"]
    whole = totals.get("all") or {
        "functions": game["functions"] + sdk["functions"] + unnamed["functions"],
        "bytes": game["bytes"] + sdk["bytes"] + unnamed["bytes"],
        "matched": game["exact"] + sdk["functions"], "matched_bytes": game["exact_bytes"] + sdk["bytes"]}
    head = (meta.get("b5_commit") or "")[:12] or "unknown"
    lines = [
        "# Byte matching",
        "",
        f"The native Xbox 360 tree (b5-decomp `{meta['branch']}`) compiled with the XDK and compared,",
        "function by function, with `BURNOUT_X360_ARTIST.XEX`. Generated by",
        "`tools/bytematch/bytematch.py summary`; do not edit. Procedure: the `byte-match` skill.",
        "",
        f"- Branch head: `{head}`; generated {meta['generated_at']}.",
    ]
    if meta.get("verified_commit"):
        behind = meta.get("behind")
        lag = "" if behind is None else (" (current)" if behind == 0 else f" ({behind} commit{'s' if behind != 1 else ''} behind the head)")
        lines.append(f"- Every record proven current at `{meta['verified_commit'][:12]}`{lag}.")
    else:
        lines.append("- No full refresh recorded yet: records stand at the commits they name.")
    lines += [
        "",
        f"**{whole['matched']:,} of the image's {whole['functions']:,} functions "
        f"({pct(whole['matched'], whole['functions'])}) byte-match ARTIST**, "
        f"{pct(whole['matched_bytes'], whole['bytes'])} of its {whole['bytes']:,} bytes of code: "
        f"{game['exact']:,} compiled from our source and {sdk['functions']:,} linked from the XDK's libraries.",
        "",
        "| Part of the image | Functions | Byte-match ARTIST | Code bytes | Code bytes matching | Fuzzy code match |",
        "|---|---:|---:|---:|---:|---:|",
        f"| **Whole image** | {whole['functions']:,} | {whole['matched']:,} ({pct(whole['matched'], whole['functions'])}) | "
        f"{whole['bytes']:,} | {pct(whole['matched_bytes'], whole['bytes'])} | |",
        f"| Our source (game and middleware) | {game['functions']:,} | {game['exact']:,} ({pct(game['exact'], game['functions'])}) | "
        f"{game['bytes']:,} | {pct(game['exact_bytes'], game['bytes'])} | {pct(game['fuzzy_bytes'], game['bytes'])} |",
        f"| XDK libraries (linked, not written) | {sdk['functions']:,} | {sdk['functions']:,} (all) | {sdk['bytes']:,} | 100.00% | |",
        f"| Not yet named | {unnamed['functions']:,} | not measurable yet | {unnamed['bytes']:,} | | |",
        "",
        f"Game functions: {game['exact']:,} exact, {game['nonmatching']:,} compiled but not matching, "
        f"{game['missing']:,} with no compiled body yet. Objects: {totals['objects']['sources']:,} measured, "
        f"{totals['objects']['sources'] - totals['objects']['compiled']:,} failed to compile, "
        f"{totals['objects']['stale']:,} changed since they were measured.",
        "",
        "## By area",
        "",
        "| Area | Functions | Exact | Not matching | Missing | Exact code | Fuzzy code |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for area in summary["areas"][:40]:
        lines.append(f"| {area['area']} | {area['functions']:,} | {area['exact']:,} | {area['nonmatching']:,} | {area['missing']:,} | "
                     f"{pct(area['exact_bytes'], area['bytes'])} | {pct(area['fuzzy_bytes'], area['bytes'])} |")
    if len(summary["areas"]) > 40:
        lines.append(f"| ... {len(summary['areas']) - 40} more in `progress/bytematch.json` | | | | | | |")
    near = sorted((r for r in summary["functions"] if r[3] == "nonmatching"), key=lambda r: (-r[4], -r[2]))[:25]
    lines += ["", "## Closest to matching", "", "| Function | ARTIST | Bytes | Score | Source |", "|---|---|---:|---:|---|"]
    for r in near:
        lines.append(f"| `{r[1]}` | {r[0]} | {r[2]} | {r[4]:.1f} | {summary['sources'][r[5]] if r[5] >= 0 else ''} |")
    if summary["recent"]:
        lines += ["", "## Recently matched", "", "| Function | ARTIST | Bytes | First exact |", "|---|---|---:|---|"]
        for r in summary["recent"][:25]:
            lines.append(f"| `{r['name']}` | {r['artist']} | {r['size']} | {r['at']} `{(r['commit'] or '')[:12]}` |")
    return "\n".join(lines) + "\n"


def write_summary(summary, path: Path = SUMMARY, report: Path = REPORT):
    path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    report.write_text(render_markdown(summary), encoding="utf-8", newline="\n")
