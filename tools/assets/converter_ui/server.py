"""Offline, loopback-only browser UI. Requires Python 3.11+, no pip packages."""
from __future__ import annotations

import argparse
import copy
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
import uuid
import webbrowser

import engine

STATIC = Path(__file__).with_name("static")
ACTIVE = {"preparing", "running", "cancelling"}


def pick(kind):
    # A separate process keeps Tk on its own main thread and its dialog lifetime
    # independent of HTTP threads. Browser upload controls are the fallback.
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if kind == "files":
            return list(filedialog.askopenfilenames(parent=root, title="Choose original game assets"))
        result = filedialog.askdirectory(parent=root, title="Choose a folder", mustexist=True)
        return [result] if result else []
    finally:
        root.destroy()


class Application:
    def __init__(self):
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.plans = {}
        self.jobs = {}
        self.active = None
        self.process = None
        self.runner = None
        self.uploads = set()
        self.picker_lock = threading.Lock()
        self.history_path = engine.WORK / "history.json"
        self.preferences = engine.read_json(engine.WORK / "preferences.json", {})
        self.history = engine.read_json(self.history_path, [])[:50]
        for entry in self.history:
            if entry["status"] in ACTIVE:
                entry["status"] = "interrupted"

    def event(self, job, data):
        with self.lock:
            job["sequence"] += 1
            data = {"time": time.time(), **data, "sequence": job["sequence"]}
            job["events"].append(data)
            if len(job["events"]) > 10000:
                del job["events"][:1000]
            if data["event"] == "row":
                for row in job["rows"]:
                    if row["id"] == data["id"]:
                        row.update({k: v for k, v in data.items() if k in {"status", "detail", "elapsed"}})
                        break
            elif data["event"] == "finished":
                job["result"] = data["status"]
            elif data["event"] == "fatal":
                job["result"] = "failed"
                job["error"] = data["message"]
            with open(engine.WORK / "jobs" / job["id"] / "activity.log", "a", encoding="utf-8") as log:
                log.write(json.dumps(data, ensure_ascii=False) + "\n")

    def summary(self, job):
        counts = dict(engine.collections.Counter(r["status"] for r in job["rows"]))
        return {k: job[k] for k in ("id", "status", "started", "ended", "output", "label", "kind")} | {
            "counts": counts, "total": len(job["rows"]), "sequence": job["sequence"],
            "error": job.get("error", "")}

    def save(self, job, final=False):
        with self.lock:
            report = self.summary(job) | {"files": copy.deepcopy(job["rows"]), "options": job["options"]}
            engine.write_json(engine.WORK / "jobs" / job["id"] / "report.json", report)
            self.history = [self.summary(job)] + [h for h in self.history if h["id"] != job["id"]]
            self.history = self.history[:50]
            engine.write_json(self.history_path, self.history)
        if final and job["kind"] == "conversion" and Path(job["output"]).is_dir():
            target = Path(job["output"]) / engine.RESERVED / "reports" / (job["id"] + ".json")
            if engine.within(target, job["output"]):
                engine.write_json(target, report)

    def start(self, plan=None, selected=None):
        with self.lock:
            if self.active and self.jobs[self.active]["status"] in ACTIVE:
                raise ValueError("A run is already active. Finish or cancel it first.")
            identifier = uuid.uuid4().hex
            jobdir = engine.WORK / "jobs" / identifier
            jobdir.mkdir(parents=True)
            if plan:
                selected = set(selected or [])
                rows = [copy.deepcopy(r) for r in plan["rows"] if r["id"] in selected and r["status"] in engine.READY]
                if not rows:
                    raise ValueError("Select at least one ready file")
                engine.validate_output(plan["options"]["output"], plan["sources"], sum(r["size"] for r in rows) * 3 + (64 << 20))
                spec = copy.deepcopy(plan)
                spec["job_id"] = identifier
                engine.write_json(jobdir / "input.json", {"plan": spec, "selected": list(selected)})
                command = [sys.executable, "-u", str(Path(engine.__file__)), str(jobdir / "input.json")]
            else:
                rows = []
                command = [sys.executable, "-u", str(engine.REPO / "tools/build/build.py"), "tools"]
            job = {"id": identifier, "status": "preparing", "started": time.time(), "ended": None,
                   "output": plan["options"]["output"] if plan else str(engine.REPO / "build/tools"),
                   "options": plan["options"] if plan else {}, "rows": rows,
                   "label": f"{len(rows)} asset(s)" if plan else "Build converter tools",
                   "kind": "conversion" if plan else "setup", "events": [], "sequence": 0,
                   "cancelled": False, "result": None}
            for row in rows:
                row["status"] = "queued"
            self.jobs[identifier] = job
            self.active = identifier
            self.save(job)
            self.runner = threading.Thread(target=self.run, args=(job, command), daemon=True)
            self.runner.start()
            return self.summary(job) | {"rows": copy.deepcopy(rows)}

    def run(self, job, command):
        p = None
        try:
            with self.lock:
                if job["cancelled"]:
                    return
                p = subprocess.Popen(command, cwd=engine.REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace",
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                     start_new_session=os.name != "nt")
                self.process = p
                job["status"] = "running"
            checkpoint = time.monotonic()
            for line in p.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if not isinstance(data, dict) or "event" not in data:
                        raise ValueError()
                except ValueError:
                    data = {"event": "log", "message": line[:8000]}
                self.event(job, data)
                if time.monotonic() - checkpoint > 3:
                    self.save(job)
                    checkpoint = time.monotonic()
            p.wait()
            with self.lock:
                job["status"] = "cancelled" if job["cancelled"] else (job["result"] or ("completed" if p.returncode == 0 else "failed"))
                if job["kind"] == "conversion" and not job["result"] and not job["cancelled"]:
                    job["status"] = "failed"
                    job["error"] = "The conversion worker exited before reporting completion. See the run log."
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
            self.event(job, {"event": "fatal", "message": str(exc)})
        finally:
            if p:
                p.stdout.close()
            with self.lock:
                if job["cancelled"]:
                    job["status"] = "cancelled"
                for row in job["rows"]:
                    if row["status"] in {"queued", "running"}:
                        row.update(status="cancelled" if job["cancelled"] else "failed",
                                   detail="Run cancelled; completed outputs were kept" if job["cancelled"] else job.get("error", "Worker stopped"))
                job["ended"] = time.time()
                self.process = None
                self.active = None
            self.save(job, final=True)
            # Only this run's private staging/work directories are removed.
            directory = engine.WORK / "jobs" / job["id"] / "workers"
            shutil.rmtree(directory, ignore_errors=True)
            if job["kind"] == "conversion":
                directory = Path(job["output"]) / engine.RESERVED / "staging" / job["id"]
                if engine.within(directory, job["output"]):
                    shutil.rmtree(directory, ignore_errors=True)

    def cancel(self, identifier):
        with self.lock:
            job = self.jobs.get(identifier)
            if not job or job["status"] not in ACTIVE:
                return
            job["cancelled"] = True
            job["status"] = "cancelling"
            p = self.process
        if p:
            if os.name != "nt" and p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
            else:
                engine.kill_tree(p)

    def job_snapshot(self, identifier, after):
        with self.lock:
            job = self.jobs.get(identifier)
            if not job:
                raise ValueError("Run not active in this server session; open its saved report in Recent runs")
            events = [e for e in job["events"] if e["sequence"] > after]
            answer = self.summary(job) | {"events": copy.deepcopy(events)}
            if after == 0:
                answer["rows"] = copy.deepcopy(job["rows"])
            elif (job["events"] and after < job["events"][0]["sequence"] - 1) or job["status"] not in ACTIVE:
                answer["rows"] = [{k: r[k] for k in ("id", "status", "detail")} for r in job["rows"]]
            return answer


class Handler(BaseHTTPRequestHandler):
    server_version = "ParadiseAssetConverter/1"

    @property
    def app(self):
        return self.server.app

    def log_message(self, *_):
        pass

    def headers_common(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")

    def send(self, data, status=200, mime="application/json; charset=utf-8"):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.headers_common()
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authenticate(self):
        host = self.headers.get("Host", "")
        expected = f"127.0.0.1:{self.server.server_port}"
        if host != expected or self.headers.get("Origin", "http://" + expected) != "http://" + expected:
            raise PermissionError("Only the local app can access this server")
        token = self.headers.get("X-Asset-Token", "")
        if not hmac.compare_digest(token, self.app.token):
            raise PermissionError("Session expired. Open the link printed by convert-assets.cmd")

    def body(self):
        n = int(self.headers.get("Content-Length", "0"))
        if n < 0 or n > 4 * 1024 * 1024:
            raise ValueError("Request too large")
        data = json.loads(self.rfile.read(n) or b"{}")
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def dispatch(self, method):
        try:
            url = urlsplit(self.path)
            path, query = url.path, parse_qs(url.query)
            if not path.startswith("/api/"):
                if method != "GET" or path not in {"/", "/app.js", "/style.css", "/favicon.svg"}:
                    return self.send({"error": "Not found"}, 404)
                file = STATIC / ("index.html" if path == "/" else path[1:])
                return self.send(file.read_bytes(), mime=mimetypes.guess_type(file)[0] or "application/octet-stream")
            self.authenticate()
            if method == "GET":
                if path == "/api/bootstrap":
                    return self.send({"defaults": engine.defaults(), "catalog": engine.catalog(),
                        "preferences": self.app.preferences,
                        "active": self.app.active, "repo": str(engine.REPO),
                        "tools": [{"name": Path(p).name, "ready": (engine.REPO / p).is_file()}
                                  for p in sorted(set(engine.stager.BUILT_BINARIES.values()))]})
                if path == "/api/history":
                    return self.send({"runs": self.app.history})
                if path.startswith("/api/job/"):
                    return self.send(self.app.job_snapshot(path.split("/")[-1], int(query.get("after", ["0"])[0])))
                if path.startswith("/api/report/") or path.startswith("/api/log/"):
                    identifier = path.split("/")[-1]
                    if not any(h["id"] == identifier for h in self.app.history):
                        raise ValueError("Unknown run")
                    file = engine.WORK / "jobs" / identifier / ("report.json" if "/report/" in path else "activity.log")
                    return self.send(file.read_bytes(), mime="application/json" if file.suffix == ".json" else "text/plain; charset=utf-8")
            if method == "PUT" and path == "/api/upload":
                batch = query.get("batch", [""])[0]
                if batch not in self.app.uploads:
                    raise ValueError("Unknown upload session")
                relative = engine.safe_relative(query.get("path", [""])[0])
                folder = engine.WORK / "uploads" / batch
                target = folder / relative
                if not engine.within(target, folder) or target.exists():
                    raise ValueError("Duplicate or invalid upload path")
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= 16 * 1024**3:
                    raise ValueError("File too large. Use Choose files or Choose folder for direct local access.")
                if engine.stager.free_bytes(str(folder)) < length + (64 << 20):
                    raise ValueError("Not enough disk space to stage this upload")
                target.parent.mkdir(parents=True, exist_ok=True)
                partial = target.with_name(target.name + ".uploading")
                try:
                    with open(partial, "xb") as f:
                        left = length
                        while left:
                            chunk = self.rfile.read(min(left, 1024 * 1024))
                            if not chunk:
                                raise ValueError("Upload interrupted")
                            f.write(chunk)
                            left -= len(chunk)
                    os.replace(partial, target)
                finally:
                    partial.unlink(missing_ok=True)
                return self.send({"path": str(target), "relative": relative})
            if method == "POST":
                data = self.body()
                if path == "/api/scan":
                    plan = engine.scan(data.get("sources"), data.get("options", {}))
                    with self.app.lock:
                        if len(self.app.plans) >= 12:
                            del self.app.plans[next(iter(self.app.plans))]
                        self.app.plans[plan["id"]] = plan
                    return self.send(plan)
                if path == "/api/preferences":
                    opts = {k: v for k, v in data.get("options", {}).items() if k in engine.defaults()}
                    sources = [p for p in data.get("sources", [])[:50]
                               if isinstance(p, str) and not engine.within(p, engine.WORK / "uploads")]
                    self.app.preferences = {"options": opts, "sources": sources,
                                            "theme": "dark" if data.get("theme") == "dark" else "light"}
                    engine.write_json(engine.WORK / "preferences.json", self.app.preferences)
                    return self.send({"ok": True})
                if path == "/api/start":
                    plan = self.app.plans.get(data.get("plan"))
                    if not plan:
                        raise ValueError("File preview expired; inspect the files again")
                    return self.send(self.app.start(plan, data.get("selected")))
                if path == "/api/setup":
                    return self.send(self.app.start())
                if path == "/api/cancel":
                    self.app.cancel(data.get("id"))
                    return self.send({"ok": True})
                if path == "/api/shutdown":
                    self.send({"ok": True})
                    def shutdown():
                        if self.app.active:
                            self.app.cancel(self.app.active)
                        if self.app.runner:
                            self.app.runner.join(timeout=15)
                        self.server.shutdown()
                    threading.Thread(target=shutdown, daemon=True).start()
                    return
                if path == "/api/pick":
                    if data.get("kind") not in {"files", "folder"}:
                        raise ValueError("Invalid picker type")
                    if not self.app.picker_lock.acquire(blocking=False):
                        raise ValueError("A file chooser is already open")
                    try:
                        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--pick", data["kind"]],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                        if p.returncode:
                            raise ValueError("Native file chooser unavailable. Paste a local path or use browser upload.")
                        return self.send({"paths": json.loads(p.stdout)})
                    finally:
                        self.app.picker_lock.release()
                if path == "/api/upload-batch":
                    batch = uuid.uuid4().hex
                    self.app.uploads.add(batch)
                    return self.send({"batch": batch, "root": str(engine.WORK / "uploads" / batch)})
                if path == "/api/open-output":
                    entry = next((h for h in self.app.history if h["id"] == data.get("id")), None)
                    if not entry or not Path(entry["output"]).is_dir():
                        raise ValueError("Output folder does not exist yet")
                    if os.name == "nt":
                        os.startfile(entry["output"])
                    else:
                        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", entry["output"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return self.send({"ok": True})
            return self.send({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except PermissionError as exc:
            self.send({"error": str(exc)}, 403)
        except (ValueError, OSError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
            self.send({"error": str(exc)}, 400)
        except Exception as exc:
            self.send({"error": f"{type(exc).__name__}: {exc}"}, 500)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0, help="0 chooses a free port")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--pick", choices=["files", "folder"], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.pick:
        print(json.dumps(pick(args.pick)))
        return
    # Re-launching the script reopens the running instance instead of starting
    # competing schedulers against the same output directory.
    if args.port == 0:
        old = engine.read_json(engine.WORK / "server.json", {})
        try:
            previous = urlsplit(old.get("url", ""))
            if previous.hostname == "127.0.0.1" and previous.port and previous.fragment:
                request = Request(f"http://127.0.0.1:{previous.port}/api/bootstrap",
                                  headers={"X-Asset-Token": previous.fragment})
                with urlopen(request, timeout=1) as response:
                    existing = json.load(response)
                if existing.get("repo") == str(engine.REPO):
                    print("Asset converter is already running: " + old["url"], flush=True)
                    if not args.no_browser:
                        webbrowser.open(old["url"])
                    return
        except (OSError, ValueError):
            pass
    app = Application()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    server.app = app
    url = f"http://127.0.0.1:{server.server_port}/#{app.token}"
    engine.WORK.mkdir(parents=True, exist_ok=True)
    engine.write_json(engine.WORK / "server.json", {"url": url, "pid": os.getpid()})
    print("\n  PARADISE / Asset converter\n")
    print("  " + url)
    print("\n  Keep this window open. Press Ctrl+C to stop.\n", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        if app.active:
            app.cancel(app.active)
        if app.runner:
            app.runner.join(timeout=15)
    finally:
        server.server_close()
        for batch in app.uploads:
            directory = engine.WORK / "uploads" / batch
            if engine.within(directory, engine.WORK / "uploads"):
                shutil.rmtree(directory, ignore_errors=True)


if __name__ == "__main__":
    main()
