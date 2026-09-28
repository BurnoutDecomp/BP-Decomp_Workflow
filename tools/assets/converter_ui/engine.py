"""Planning and isolated execution for the local asset converter.

The manifest and build_game_data remain the authorities for conversion policy.
This adapter adds loose-file detection and atomic output publication; it contains
no binary payload conversion code. Only allowlisted manifest tools are executed.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import fnmatch
import json
import os
from pathlib import Path
import queue
import shutil
import struct
import subprocess
import sys
import threading
import time
import uuid

ASSETS = Path(__file__).resolve().parents[1]
REPO = ASSETS.parents[1]
sys.path.insert(0, str(ASSETS))
import build_game_data as stager

WORK = Path(os.environ.get("PARADISE_WORK_DIR", str(REPO / "build/converter-ui"))).resolve()
MAX_FILES = 30000
RESERVED = ".asset-converter"
EXECUTABLE_ACTIONS = {"convert", "copy", "generate"}
READY = {"ready", "replace"}
GOOD = {"converted", "copied", "generated", "current"}
RULES, FILE_RULES, GEN_RULES = stager.load_manifest(stager.DEFAULT_MANIFEST)
BY_ID = {r.id: r for r in RULES}
TOPS = {p.split("/")[0].upper() for r in FILE_RULES for p in r.match
        if "/" in p and not stager.has_wildcard(p.split("/")[0])}
# Only unambiguous, fully supported resource sets may select a loose-file route.
CONTENT_ROUTES = [
    ({0x10012, 0x10013, 0x10014}, set(), "environment-settings", "ENVIRONMENTSETTINGS"),
    ({0x2B}, set(), "environment-colour-cubes", "ENVIRONMENTSETTINGS/COLOURCUBES"),
    ({0}, set(), "texture-bundles", ""),
    ({0, 0x21}, {0x21}, "language-fonts", "LANGUAGE/FONTS"),
    ({0, 0x10020}, {0x10020}, "flapt-hud", ""),
    ({0x1F, 0x2C, 0x2E}, set(), "gui-banks", ""),
    ({0x10001, 0x10002, 0x10003}, set(), "lane-data", ""),
    ({0xB000, 0x43, 0x25}, {0xB000, 0x43}, "world-support", ""),
    ({65550}, set(), "progression-data", ""),
    ({0x42}, set(), "video-list", "VIDEOS"),
]


def within(path, parent):
    return Path(path).resolve().is_relative_to(Path(parent).resolve())


def safe_relative(value):
    value = str(value).replace("\\", "/")
    parts = value.split("/")
    if (not value or any(p in ("", ".", "..") or ":" in p or "\0" in p
                         or p.endswith((".", " ")) for p in parts)
            or any(p.upper().split(".")[0] in {"CON", "PRN", "AUX", "NUL", *(
                f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10))}
                   for p in parts)):
        raise ValueError("Invalid relative path: " + value)
    return "/".join(parts)


def inspect_bundle(path):
    """Read only the uncompressed entry directory, never the large payloads."""
    with open(path, "rb") as f:
        h = f.read(40)
        if h[:4] != b"bnd2":
            return {"platform": None, "types": [], "resources": 0}
        if len(h) != 40:
            raise ValueError("Truncated bnd2 header")
        platform = stager.bnd2_platform(path)
        endian = ">" if struct.unpack_from(">I", h, 8)[0] == platform else "<"
        version, _, _, count, offset, *_ = struct.unpack_from(endian + "9I", h, 4)
        if version != 2 or offset < 40 or count > 1000000 or offset + count * 64 > os.path.getsize(path):
            raise ValueError("Invalid bnd2 resource directory")
        f.seek(offset)
        types = set()
        for _ in range(count):
            entry = f.read(64)
            if len(entry) != 64:
                raise ValueError("Truncated bnd2 entry")
            types.add(struct.unpack_from(endian + "I", entry, 56)[0])
        return {"platform": platform, "types": sorted(types), "resources": count,
                "compressed": bool(struct.unpack_from(endian + "I", h, 36)[0] & 1)}


def anchored(path):
    parts = Path(path).parts
    for i in range(len(parts) - 2, -1, -1):
        if parts[i].upper() in TOPS:
            return "/".join(parts[i:])
    return None


def choose_rule(path, rel, info, override="auto"):
    if override != "auto":
        r = BY_ID.get(override)
        if not r or r.action != "convert":
            raise ValueError("Choose a converter from the format guide")
        # Context-dependent drivers need their canonical directory even for a loose file.
        prefix = r.match[0].rsplit("/", 1)[0] if "/" in r.match[0] else ""
        return r, (prefix + "/" if prefix and not stager.has_wildcard(prefix) else "") + Path(path).name, "Selected manually"
    for candidate in dict.fromkeys([rel, anchored(path), Path(path).name]):
        if candidate:
            r = next((r for r in FILE_RULES if r.accepts(candidate)), None)
            if r:
                return r, candidate, "Matched game path"
    types = set(info["types"])
    for allowed, required_any, rid, prefix in CONTENT_ROUTES:
        if types and types <= allowed and (not required_any or types & required_any):
            return BY_ID[rid], (prefix + "/" if prefix else "") + Path(path).name, "Detected from resource types"
    # Constrained basenames (VEH_*_GR.BIN, exact names) survive being moved.
    # Generic *.BUNDLE patterns cannot identify a resource family on their own.
    matches = []
    for r in FILE_RULES:
        for pat in r.match:
            if "/" not in pat:
                continue
            parent, name = pat.rsplit("/", 1)
            if stager.has_wildcard(parent) or name.startswith(("*", "?", "[")):
                continue
            if fnmatch.fnmatch(Path(path).name.lower(), name.lower()):
                matches.append((r, parent + "/" + Path(path).name, "Matched known filename"))
    if len({r.id for r, _, _ in matches}) == 1:
        return matches[0]
    return stager.CATCHALL, rel, "No supported route detected"


def source_root(path, configured=""):
    # Prefer the file's own dump over a configured different build.
    start = Path(path) if Path(path).is_dir() else Path(path).parent
    for p in [start, *start.parents]:
        if (p / "BURNOUT_X360_ARTIST.XEX").is_file() or (p / "SHADERS.BNDL").is_file():
            return str(p)
    if configured:
        return str(Path(configured).expanduser().resolve())
    return str(start)


def validate_output(output, sources, need_bytes=0):
    if not output or not Path(output).is_absolute():
        raise ValueError("Choose an absolute output folder path")
    dest = Path(output).resolve()
    forbidden = [REPO / "tools", REPO / "b5-decomp", REPO / "build/game",
                 WORK, REPO / ".git"]
    if dest == REPO or dest == Path(dest.anchor) or any(within(dest, p) for p in forbidden):
        raise ValueError("Choose a separate output folder, outside the source code and live build/game folder")
    if dest.exists() and not dest.is_dir():
        raise ValueError("The output path is a file; choose a folder")
    if not within(dest / RESERVED, dest):
        raise ValueError("The output metadata folder points outside the destination")
    for src in sources:
        p = Path(src).resolve()
        if (p.is_dir() and (within(dest, p) or within(p, dest))) or (p.is_file() and within(p, dest)):
            raise ValueError("Output must be separate from the selected sources")
    if need_bytes and stager.free_bytes(str(dest)) < need_bytes:
        raise ValueError("Not enough space on the output drive for this selection")
    return dest


def catalog():
    return [{"id": r.id, "name": r.id.replace("-", " ").title(), "action": r.action,
             "patterns": r.match, "tool": r.tool, "description": r.reason or r.why}
            for r in RULES]


def defaults():
    cfg = stager._CFG
    return {"output": str(REPO / "build/converted-assets"),
            "source_root": cfg.get("inputs", {}).get("x360_root", ""),
            "xb1_root": cfg.get("inputs", {}).get("xb1_root", ""),
            "jobs": min(4, max(1, (os.cpu_count() or 2) // 2)),
            "keep_layout": True, "replace": False, "skip_current": True,
            "generate": True, "converter": "auto"}


def read_json(path, fallback):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


def make_item(row, out):
    if row["rule"] == "already-pc":
        rule = stager.Rule({"id": "already-pc", "action": "copy", "verify": ["bnd2_platform=4"]}, -1)
    else:
        rule = BY_ID.get(row["rule"], stager.CATCHALL)
    return stager.Item(rule, row["source"], row["relative"], str(out), row["output_relative"], row["size"], row.get("kind", "file"))


def scan(sources, supplied_options):
    if not isinstance(sources, list) or not sources or len(sources) > MAX_FILES:
        raise ValueError("Add at least one file or folder")
    options = defaults() | supplied_options
    options["jobs"] = max(1, min(8, int(options["jobs"])))
    paths = list(dict.fromkeys(str(Path(str(s).strip().strip('"')).expanduser().resolve()) for s in sources))
    for p in paths:
        if not Path(p).exists():
            raise ValueError("Source does not exist: " + p)
        if Path(p).is_dir() and within(p, REPO / "build/game"):
            raise ValueError("Choose the original data folder. build/game is the live run folder and contains junctions.")
    dest = validate_output(options["output"], paths)
    options["output"] = str(dest)
    found, seen, warnings = [], set(), []
    def add(p, rel):
        key = os.path.normcase(str(p.resolve()))
        if key not in seen:
            seen.add(key)
            found.append((p, safe_relative(rel)))
            if len(found) > MAX_FILES:
                raise ValueError(f"More than {MAX_FILES:,} files selected. Select a smaller folder.")
    for text in paths:
        p = Path(text)
        if p.is_file():
            add(p, p.name)
            continue
        root = Path(stager.find_game_root(str(p)))
        def walk_error(exc):
            warnings.append(str(exc))
        for folder, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
            kept = []
            for name in sorted(dirs):
                child = Path(folder) / name
                if name in {RESERVED, ".build_game_data", ".git", "__pycache__"}:
                    continue
                if child.is_symlink() or bool(getattr(child.stat(), "st_file_attributes", 0) & 0x400):
                    warnings.append("Skipped linked folder: " + str(child))
                elif within(child, dest):
                    warnings.append("Skipped output folder: " + str(child))
                else:
                    kept.append(name)
            dirs[:] = kept
            for name in sorted(names):
                file = Path(folder) / name
                if file.is_symlink():
                    warnings.append("Skipped linked file: " + str(file))
                    continue
                add(file, file.relative_to(root).as_posix())
    state = read_json(dest / RESERVED / "state.json", {})
    rows, destinations = [], collections.defaultdict(list)
    preflight_cache = {}
    for i, (path, relative) in enumerate(found):
        row = {"id": str(i), "name": path.name, "source": str(path), "relative": relative,
               "size": 0, "status": "ready", "detail": "", "kind": "file",
               "rule": "catch-all", "tool": None, "action": "unhandled",
               "output_relative": relative, "platform": None, "types": [], "resources": 0,
               "source_root": source_root(path, options["source_root"])}
        try:
            row["size"] = path.stat().st_size
            row["source_stamp"] = [row["size"], path.stat().st_mtime_ns]
            info = inspect_bundle(path)
            row.update(info)
            rule, canonical, row["detection"] = choose_rule(path, relative, info, options["converter"])
            row.update(rule=rule.id, tool=rule.tool, action=rule.action, relative=canonical)
            # Preserve arbitrary nested folders too; canonicalize loose files or
            # known game-directory anchors without flattening a selected tree.
            out_rel = (canonical if anchored(path) or "/" not in relative else relative) if options["keep_layout"] else path.name
            if rule.out_name:
                out_rel = str(Path(out_rel).with_name(stager.expand(rule.out_name, {
                    "stem": path.stem, "ext": path.suffix, "name": path.name}))).replace("\\", "/")
            row["output_relative"] = safe_relative(out_rel)
            if info["platform"] == 4 and rule.action != "skip":
                row.update(rule="already-pc", action="copy", tool=None,
                           detail="Already a PC container; copy without reconverting")
            elif rule.action == "skip" or stager.denied(out_rel):
                row.update(status="skipped", detail=rule.why or "Not needed by the PC runtime")
            elif info["platform"] is not None and info["platform"] != 2:
                row.update(status="unsupported", detail=f"Platform {info['platform']} is not supported. Select original Xbox 360 data.")
            elif rule.action == "unhandled":
                row.update(status="unsupported", detail=rule.reason or "No supported converter for this file")
            elif rule.action == "convert" and info["platform"] != 2:
                row.update(status="unsupported", detail="This converter expects an Xbox 360 bnd2 bundle")
            target = dest / row["output_relative"]
            if not within(target, dest) or within(target, dest / RESERVED):
                raise ValueError("Output path leaves the selected destination or uses a reserved folder")
            row["output"] = str(target)
            if row["status"] == "ready":
                item = make_item(row, target)
                if options["skip_current"] and target.is_file() and state.get(row["output_relative"]) == stager._signature(item, ""):
                    row.update(status="current", detail="Unchanged since the last successful conversion")
                elif target.exists():
                    row.update(status="replace" if options["replace"] and target.is_file() else "exists",
                               detail="Existing output will be backed up" if options["replace"] else "Output already exists; enable Replace existing to update it")
            if row["status"] in READY:
                key = (row["rule"], row["source_root"])
                if key not in preflight_cache:
                    gaps = stager.preflight([make_item(row, target)], [], row["source_root"], str(dest))
                    issues = [str(Path(p).name) + " is missing. " + fix for p, _, fix in gaps]
                    if row["rule"] == "sound-global-attribsys" and not (Path(row["source_root"]) / "BURNOUT_X360_ARTIST.XEX").is_file():
                        issues.append("Choose the original game folder containing BURNOUT_X360_ARTIST.XEX in Advanced settings")
                    preflight_cache[key] = issues
                if preflight_cache[key]:
                    row.update(status="blocked", detail="\n".join(preflight_cache[key]))
            destinations[os.path.normcase(str(target)).casefold()].append(row)
        except (OSError, ValueError, struct.error) as exc:
            row.update(status="blocked", detail=str(exc))
        rows.append(row)
    for same in destinations.values():
        if len(same) > 1:
            for row in same:
                row.update(status="blocked", detail="Multiple inputs would write this output. Keep folder layout or select them separately.")
    # Generate the runtime schema/loading assets only when an actual game folder
    # was selected, not for every loose file using a configured reference dump.
    game_roots = {source_root(p) for p in paths if Path(p).is_dir()}
    if options["generate"]:
        for root in sorted(game_roots):
            if not (Path(root) / "BURNOUT_X360_ARTIST.XEX").is_file():
                continue
            for rule in GEN_RULES:
                row = {"id": str(len(rows)), "name": rule.id.replace("generate-", "").replace("-", " ").title(),
                    "source": str(Path(root) / "BURNOUT_X360_ARTIST.XEX"), "source_root": root,
                    "relative": "<generated>", "output_relative": rule.out_subdir or ".",
                    "output": str(dest / (rule.out_subdir or "")), "size": 0, "kind": "generate",
                    "rule": rule.id, "tool": rule.tool, "action": "generate", "status": "ready",
                    "detail": "Generate runtime support files from the original executable", "types": [], "platform": 2}
                generated_dir = dest / (rule.out_subdir or "")
                existing = (any((generated_dir / name).exists() for name in rule.outputs)
                            if rule.outputs else generated_dir.exists())
                if existing:
                    row.update(status="replace" if options["replace"] else "exists",
                               detail="Existing support files will be backed up" if options["replace"] else
                               "Support files already exist; enable Replace existing to regenerate this set together")
                stamp = Path(row["source"]).stat()
                row["source_stamp"] = [stamp.st_size, stamp.st_mtime_ns]
                gaps = stager.preflight([], [make_item(row, generated_dir)], root, str(dest))
                if gaps:
                    row.update(status="blocked", detail="\n".join(Path(p).name + " is missing. " + fix for p, _, fix in gaps))
                rows.append(row)
    if len(game_roots) > 1:
        for row in rows:
            if row["kind"] == "generate":
                row.update(status="blocked", detail="Select one original game folder at a time to generate support files")
    return {"id": uuid.uuid4().hex, "created": time.time(), "sources": paths,
            "options": options, "rows": rows, "warnings": warnings,
            "free_bytes": stager.free_bytes(str(dest)),
            "counts": dict(collections.Counter(r["status"] for r in rows))}


def kill_tree(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        process.kill()


_emit_lock = threading.Lock()


def emit(kind, **data):
    with _emit_lock:
        print(json.dumps({"event": kind, "time": time.time(), **data}, ensure_ascii=False), flush=True)


def run_converter(rule, argv, cwd, root, env, row, log_path):
    command = [sys.executable, "-u", str(root / "tools/assets" / rule.tool), *argv]
    tail = collections.deque(maxlen=20)
    with open(log_path, "a", encoding="utf-8") as log:
        for attempt in (1, 2):
            emit("log", id=row["id"], message=f"{row['name']}: {rule.tool}")
            log.write("COMMAND: " + subprocess.list2cmdline(command) + "\n")
            log.flush()
            p = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            expired = threading.Event()
            def timeout():
                expired.set()
                kill_tree(p)
            timer = threading.Timer(1800, timeout)
            timer.start()
            try:
                for line in p.stdout:
                    if log.tell() < 8 * 1024**2:
                        log.write(line[:16384])
                        log.flush()
                    line = line.strip()
                    if line:
                        tail.append(line)
                        emit("log", id=row["id"], message=line[:2000])
                p.wait()
            finally:
                timer.cancel()
                p.stdout.close()
            if expired.is_set():
                raise RuntimeError("Converter timed out after 30 minutes; see the run log")
            if p.returncode == 0:
                return
            if attempt == 1 and stager.TRANSIENT_LAUNCH_RE.search("\n".join(tail)):
                emit("log", id=row["id"], message="Toolchain startup failed; retrying once…")
                time.sleep(stager.RETRY_PAUSE_S)
                continue
            raise RuntimeError("Converter exited with code %d\n%s" % (p.returncode, "\n".join(tail)))


def execute_job(plan, selected, jobdir):
    """Runs in a separate process, so cancel can terminate every converter child."""
    options = plan["options"]
    dest = validate_output(options["output"], plan["sources"])
    rows = [dict(r) for r in plan["rows"] if r["id"] in set(selected) and r["status"] in READY]
    validate_output(str(dest), plan["sources"], sum(r["size"] for r in rows) * 3 + (64 << 20))
    dest.mkdir(parents=True, exist_ok=True)
    jobdir = Path(jobdir)
    metadata = dest / RESERVED
    state_path = metadata / "state.json"
    state = read_json(state_path, {})
    publish_lock = threading.Lock()
    slots = queue.Queue()
    count = min(options["jobs"], max(1, sum(r["action"] != "copy" for r in rows)))
    roots = stager.WorkerRoots(str(jobdir / "workers"), count, quiet=True)
    if any(r["action"] != "copy" for r in rows):
        emit("log", message=f"Preparing {count} isolated converter workspace(s)…")
        for n in range(count):
            roots.get(n)
    for n in range(count):
        slots.put(n)

    def worker(row):
        slot = slots.get()
        started = time.time()
        root = Path(roots.get(slot)) if row["action"] != "copy" else jobdir
        stage = metadata / "staging" / plan["job_id"] / row["id"]
        try:
            emit("row", id=row["id"], status="running", detail="Converting…")
            if row.get("source_stamp"):
                st = Path(row["source"]).stat()
                if row["source_stamp"] != [st.st_size, st.st_mtime_ns]:
                    raise ValueError("Source changed after inspection. Inspect the files again.")
            if not within(stage, dest):
                raise ValueError("The staging path points outside the destination")
            stage.mkdir(parents=True, exist_ok=True)
            item = make_item(row, stage / row["output_relative"])
            rule = item.rule
            if rule.action == "copy":
                Path(item.out).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item.src, item.out)
            else:
                srcroot = Path(row["source_root"])
                if rule.produces:
                    # These legacy drivers derive filenames from BRN_X360_ROOT.
                    # Stage the selected bytes so a different configured dump can
                    # never silently replace the user's selected input.
                    overlay = root / "selected-input" / row["id"]
                    chosen = overlay / safe_relative(row["relative"])
                    chosen.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(row["source"], chosen)
                    xex = srcroot / "BURNOUT_X360_ARTIST.XEX"
                    if xex.is_file():
                        shutil.copy2(xex, overlay / xex.name)
                    srcroot = overlay
                ctx = stager.context_for(item.src, item.src_rel, item.out, item.out_rel,
                                        str(srcroot), str(stage), str(root))
                if rule.action == "generate":
                    ctx["outdir"] = str(stage / (rule.out_subdir or ""))
                    for origin, target in rule.stage_in:
                        staged = root / safe_relative(target)
                        staged.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(srcroot / safe_relative(origin), staged)
                Path(ctx["outdir"]).mkdir(parents=True, exist_ok=True)
                env = os.environ.copy()
                env.update(BRN_X360_ROOT=str(srcroot), PYTHONIOENCODING="utf-8",
                           NUSHADERS_TUB=stager._resolved_nushaders_tub(),
                           BRN_VOLA_CACHE=str(WORK / "vola-cache"))
                if options.get("xb1_root"):
                    env["BRN_XB1_ROOT"] = options["xb1_root"]
                argv = [stager.expand(a, ctx) for a in rule.argv]
                run_converter(rule, argv, stager.expand(rule.cwd, ctx) if rule.cwd else str(root),
                              root, env, row, jobdir / (row["id"] + ".log"))
                if rule.produces:
                    made = root / safe_relative(stager.expand(rule.produces, ctx))
                    Path(item.out).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(made), item.out)
                if rule.produces_dir:
                    for file in (root / rule.produces_dir).iterdir():
                        if file.is_file() and not stager.denied(file.name):
                            shutil.copy2(file, Path(ctx["outdir"]) / file.name)
            products = list(stage.rglob("*")) if rule.action == "generate" else [Path(item.out)]
            products = [p for p in products if p.is_file()]
            if not products:
                raise ValueError("The converter produced no files")
            for product in products:
                error = stager.check_verify(str(product), rule.verify)
                if error:
                    raise ValueError(f"Output validation failed: {product.name}: {error}")
            with publish_lock:
                published = []
                for product in products:
                    rel = product.relative_to(stage)
                    target = dest / rel
                    if not within(target, dest) or within(target, metadata) or target.resolve() == Path(row["source"]).resolve():
                        raise ValueError("Output path changed while converting")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        if not options["replace"]:
                            if rule.action == "generate":
                                continue
                            raise ValueError("Output appeared during conversion. Enable Replace existing or choose another folder.")
                        backup = metadata / "backups" / plan["job_id"] / rel
                        if not within(backup, dest):
                            raise ValueError("The backup path points outside the destination")
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, backup)
                    if options["replace"]:
                        os.replace(product, target)
                    elif os.name == "nt":
                        os.rename(product, target)  # Windows fails if a file appeared.
                    else:
                        os.link(product, target)    # POSIX no-replace publication.
                        product.unlink()
                    published.append(str(target))
                if row["kind"] != "generate" and published:
                    state[row["output_relative"]] = stager._signature(make_item(row, published[0]), "")
                    write_json(state_path, state)
            status = {"copy": "copied", "convert": "converted", "generate": "generated"}[rule.action] if published else "exists"
            row.update(status=status, detail=f"{len(published)} file(s) written" if published else "Existing support files kept",
                       products=published, elapsed=round(time.time() - started, 2))
        except Exception as exc:
            row.update(status="failed", detail=str(exc), elapsed=round(time.time() - started, 2))
        finally:
            shutil.rmtree(stage, ignore_errors=True)
            slots.put(slot)
        emit("row", **{k: row[k] for k in ("id", "status", "detail", "elapsed", "products") if k in row})
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        results = list(executor.map(worker, rows))
    shutil.rmtree(jobdir / "workers", ignore_errors=True)
    emit("finished", status="completed" if all(r["status"] in GOOD | {"exists"} for r in results) else "completed_with_errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args()
    try:
        spec = read_json(args.job, {})
        if os.environ.get("PARADISE_SANDBOX") == "1":
            from sandbox import restrict
            jobdir = Path(args.job).resolve().parent
            # The public service stores work and output beside each other under
            # a private session root. Never grant access to all sessions or /data.
            workspace = WORK.parent
            if not within(jobdir, WORK / "jobs") or not within(spec["plan"]["options"]["output"], workspace / "output"):
                raise ValueError("Invalid hosted workspace layout")
            scratch = jobdir / "tmp"
            scratch.mkdir(parents=True, exist_ok=True)
            os.environ.update(TMPDIR=str(scratch), TMP=str(scratch), TEMP=str(scratch),
                              HOME=str(scratch), DOTNET_EnableDiagnostics="0")
            import resource
            ceiling = int(os.environ.get("PARADISE_OUTPUT_FILE_MIB", "2048")) * 1024**2
            resource.setrlimit(resource.RLIMIT_FSIZE, (ceiling, ceiling))
            restrict(workspace, REPO)
        execute_job(spec["plan"], spec["selected"], Path(args.job).parent)
    except Exception as exc:
        emit("fatal", message=str(exc))
        sys.exit(1)
