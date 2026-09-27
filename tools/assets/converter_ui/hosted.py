"""Public upload/download service. Run one Gunicorn process; see deploy/README.md.

The desktop server remains loopback-only. This entry point exposes uploads and
owned run results, never the desktop file picker, arbitrary paths, or setup tools.
"""
from __future__ import annotations

import atexit
from collections import Counter, defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import logging
import os
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
from urllib.parse import urlsplit
import uuid
import zipfile

from flask import Flask, g, jsonify, request, send_file
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

import engine
from server import ACTIVE, Application, STATIC

ID = re.compile(r"^[a-f0-9]{32}$")
COOKIE = "paradise_workspace"
GIB = 1024**3
LOG = logging.getLogger(__name__)


def integer(name, default, minimum=1, maximum=10**12):
    value = int(os.environ.get(name, default))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass
class Settings:
    origin: str
    data: Path
    file_bytes: int
    upload_bytes: int
    workspace_bytes: int
    total_bytes: int
    max_files: int
    max_sessions: int
    max_jobs: int
    workers: int
    retention: int
    job_seconds: int
    sessions_per_hour: int

    @classmethod
    def environment(cls):
        origin = os.environ.get("PARADISE_PUBLIC_URL", "").rstrip("/")
        parsed = urlsplit(origin)
        if (not parsed.hostname or parsed.path or parsed.query or parsed.fragment
                or parsed.username or parsed.password or parsed.scheme not in {"https", "http"}):
            raise ValueError("Set PARADISE_PUBLIC_URL to the site's origin, e.g. https://convert.example.com")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("A public deployment requires an HTTPS origin")
        return cls(origin, Path(os.environ.get("PARADISE_DATA_DIR", "/data")).resolve(),
                   integer("PARADISE_FILE_MIB", 512) * 1024**2,
                   integer("PARADISE_UPLOAD_GIB", 2) * GIB,
                   integer("PARADISE_WORKSPACE_GIB", 8) * GIB,
                   integer("PARADISE_TOTAL_GIB", 40) * GIB,
                   integer("PARADISE_MAX_FILES", 5000, maximum=engine.MAX_FILES),
                   integer("PARADISE_MAX_SESSIONS", 100, maximum=1000),
                   integer("PARADISE_MAX_JOBS", 2, maximum=8),
                   integer("PARADISE_WORKERS", 2, maximum=8),
                   integer("PARADISE_RETENTION_HOURS", 24, maximum=168) * 3600,
                   integer("PARADISE_JOB_MINUTES", 30, maximum=120) * 60,
                   integer("PARADISE_SESSIONS_PER_HOUR", 10, maximum=1000))


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def disk_usage(root):
    total = count = 0
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()]
        for name in files:
            path = Path(folder) / name
            try:
                if not path.is_symlink():
                    total += path.stat().st_size
                    count += 1
            except FileNotFoundError:
                pass  # A worker may publish/remove a staging file while counting.
    return total, count


class Workspace:
    def __init__(self, root):
        self.root = root
        self.work = root / "work"
        self.output = root / "output"
        self.work.mkdir(parents=True, exist_ok=True)
        self.app = Application(self.work)
        self.app.uploads = {p.name for p in (self.work / "uploads").glob("*") if p.is_dir() and ID.fullmatch(p.name)}
        self.operation = threading.Lock()
        self.readers = 0
        self.touched = engine.read_json(root / "session.json", {}).get("touched", time.time())

    def touch(self):
        self.touched = time.time()
        engine.write_json(self.root / "session.json", {"touched": self.touched})

    def active(self):
        return self.app.active and self.app.jobs[self.app.active]["status"] in ACTIVE

    def options(self, supplied, settings, destination=None):
        if not isinstance(supplied, dict):
            raise Problem("Invalid conversion options")
        result = {k: v for k, v in supplied.items() if k in {"keep_layout", "generate", "converter", "jobs"}}
        result.update(output=str(destination or self.output), source_root="", xb1_root="",
                      skip_current=False, replace=False)
        result["jobs"] = min(settings.workers, max(1, int(result.get("jobs", settings.workers))))
        return engine.defaults() | result

    def sources(self, values):
        if not isinstance(values, list) or not 1 <= len(values) <= 100:
            raise Problem("Upload files or a folder first")
        result = []
        for value in values:
            rel = engine.safe_relative(value)
            parts = rel.split("/")
            if len(parts) < 2 or parts[0] != "uploads" or parts[1] not in self.app.uploads:
                raise Problem("Select files uploaded in this browser session", 403)
            path = self.work / rel
            if (not engine.within(path, self.root) or
                    not engine.within(path, self.work / "uploads" / parts[1]) or not path.exists()):
                raise Problem("Uploaded files are missing or expired")
            result.append(str(path))
        return result


class Portal:
    def __init__(self, settings):
        self.settings = settings
        if engine.within(settings.data, engine.REPO) or engine.within(engine.REPO, settings.data):
            raise ValueError("PARADISE_DATA_DIR must be separate from the repository")
        self.root = settings.data / "sessions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.apps = {}
        self.reserved = 0
        self.rates = defaultdict(deque)
        self.stop = threading.Event()
        secret_path = settings.data / "session-secret"
        try:
            with open(secret_path, "xb") as f:
                os.chmod(secret_path, 0o600)
                f.write(secrets.token_bytes(32))
        except FileExistsError:
            pass
        self.secret = secret_path.read_bytes()
        if len(self.secret) < 32:
            raise ValueError("Invalid session-secret file")
        self.maintainer = threading.Thread(target=self.maintain, daemon=True, name="workspace-cleanup")
        self.maintainer.start()
        atexit.register(self.close)

    def sign(self, value):
        return hmac.new(self.secret, value.encode(), hashlib.sha256).hexdigest()

    def workspace(self, create=False):
        cookie = request.cookies.get(COOKIE, "")
        identifier, _, signature = cookie.partition(".")
        valid = ID.fullmatch(identifier) and hmac.compare_digest(signature, self.sign(identifier))
        with self.lock:
            if valid and (self.root / identifier / "session.json").is_file():
                workspace = self.apps.get(identifier)
                if workspace is None:
                    workspace = self.apps[identifier] = Workspace(self.root / identifier)
                if workspace.touched + self.settings.retention > time.time() or workspace.active():
                    workspace.readers += 1
                    g.workspace = workspace
                    g.new_cookie = cookie
                    return workspace
            if not create:
                raise Problem("This session expired. Reload the page to start a new workspace.", 401)
            now = time.time()
            # ProxyFix accepts exactly one trusted proxy hop; Docker does not publish
            # the backend port. Client IPs are HMACed and never written to disk.
            key = self.sign(request.remote_addr or "unknown")
            for old in list(self.rates):
                if not self.rates[old] or self.rates[old][-1] < now - 3600:
                    del self.rates[old]
            bucket = self.rates[key]
            while bucket and bucket[0] < now - 3600:
                bucket.popleft()
            if len(bucket) >= self.settings.sessions_per_hour or len(self.rates) > 10000:
                raise Problem("Too many new workspaces. Try again later.", 429)
            if sum(1 for p in self.root.iterdir() if p.is_dir()) >= self.settings.max_sessions:
                raise Problem("The server is full. Please try again after older workspaces expire.", 503)
            self.reserve(None, 64 << 20)
            self.reserved -= 64 << 20
            identifier = uuid.uuid4().hex
            workspace = self.apps[identifier] = Workspace(self.root / identifier)
            workspace.touch()
            workspace.readers += 1
            g.workspace = workspace
            g.new_cookie = identifier + "." + self.sign(identifier)
            bucket.append(now)
            return workspace

    @contextmanager
    def operation(self, workspace):
        if not workspace.operation.acquire(blocking=False):
            raise Problem("Another operation is in progress in this workspace. Please wait.", 409)
        try:
            workspace.touch()
            yield
        finally:
            workspace.operation.release()

    def reserve(self, workspace, amount):
        with self.lock:
            if workspace and disk_usage(workspace.root)[0] + amount > self.settings.workspace_bytes:
                raise Problem("Workspace storage limit reached. Download your results, then delete your files.", 413)
            if disk_usage(self.root)[0] + self.reserved + amount > self.settings.total_bytes:
                raise Problem("The server has reached its storage limit. Please try again later.", 503)
            if shutil.disk_usage(self.root).free < self.reserved + amount + (256 << 20):
                raise Problem("The server is low on disk space. Please try again later.", 503)
            self.reserved += amount

    def entry(self, workspace, identifier):
        if not ID.fullmatch(identifier):
            raise Problem("Unknown run", 404)
        result = next((r for r in workspace.app.history if r["id"] == identifier), None)
        if not result:
            raise Problem("Unknown run in this workspace", 404)
        return result

    def maintain(self):
        while not self.stop.wait(5):
            try:
                with self.lock:
                    overfull = disk_usage(self.root)[0] > self.settings.total_bytes
                    for folder in list(self.root.iterdir()):
                        if not ID.fullmatch(folder.name) or folder.is_symlink() or not folder.is_dir():
                            continue
                        workspace = self.apps.get(folder.name)
                        touched = workspace.touched if workspace else engine.read_json(folder / "session.json", {}).get("touched", 0)
                        if workspace:
                            with workspace.app.lock:
                                finished = sorted((j for j in workspace.app.jobs.values() if j["status"] not in ACTIVE),
                                                  key=lambda j: j["started"], reverse=True)
                                for job in finished[:3]:
                                    job["events"] = job["events"][-256:]
                                for job in finished[3:]:
                                    workspace.app.jobs.pop(job["id"], None)
                        if workspace and workspace.active():
                            job = workspace.app.jobs[workspace.app.active]
                            overage = disk_usage(folder)[0] > self.settings.workspace_bytes
                            if overfull or overage or time.time() - job["started"] > self.settings.job_seconds:
                                job["error"] = "Server storage or run-time limit reached. Completed outputs can still be downloaded."
                                workspace.app.cancel(job["id"])
                        elif touched + self.settings.retention < time.time() and not (workspace and workspace.readers):
                            if engine.within(folder, self.root):
                                shutil.rmtree(folder)
                                self.apps.pop(folder.name, None)
            except Exception:
                LOG.exception("Workspace cleanup failed")

    def close(self):
        self.stop.set()
        for workspace in list(self.apps.values()):
            if workspace.active():
                workspace.app.cancel(workspace.app.active)
            if workspace.app.runner:
                workspace.app.runner.join(timeout=10)


def create_app(settings=None):
    cfg = settings or Settings.environment()
    portal = Portal(cfg)
    app = Flask(__name__, static_folder=None)
    app.config.update(MAX_CONTENT_LENGTH=cfg.file_bytes, MAX_FORM_MEMORY_SIZE=65536)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)
    app.extensions["paradise"] = portal

    @app.before_request
    def boundary():
        if request.path == "/healthz":
            return
        if request.host.lower() != urlsplit(cfg.origin).netloc.lower():
            raise Problem("Unrecognized host", 403)
        if request.headers.get("Origin", cfg.origin) != cfg.origin or request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise Problem("Use the converter on its own website", 403)
        if request.path.startswith("/api/"):
            workspace = portal.workspace(create=request.path == "/api/bootstrap" and request.method == "GET")
            if request.path != "/api/bootstrap" and not request.path.startswith("/api/download/"):
                expected = portal.sign("csrf:" + workspace.root.name)
                if not hmac.compare_digest(request.headers.get("X-Asset-Token", ""), expected):
                    raise Problem("Session token is missing. Reload the page.", 403)
            # Reading a job is enough to retain a visitor's current workspace.
            if time.time() - workspace.touched > 60:
                workspace.touch()

    @app.after_request
    def response_headers(response):
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"})
        if getattr(g, "new_cookie", None):
            response.set_cookie(COOKIE, g.new_cookie, max_age=cfg.retention, httponly=True,
                                secure=cfg.origin.startswith("https:"), samesite="Strict", path="/")
        if response.status_code in {429, 503}:
            response.headers["Retry-After"] = "60"
        return response

    @app.teardown_request
    def release(_error):
        if getattr(g, "workspace", None):
            with portal.lock:
                g.workspace.readers -= 1

    @app.errorhandler(Exception)
    def failure(error):
        if isinstance(error, Problem):
            return jsonify(error=str(error)), error.status
        if isinstance(error, HTTPException):
            return jsonify(error=error.description), error.code
        if isinstance(error, (ValueError, TypeError, KeyError)):
            return jsonify(error=str(error)), 400
        LOG.exception("Hosted request failed")
        return jsonify(error="Server operation failed. Please try again or contact the operator."), 500

    def body():
        if request.content_length is None or request.content_length > 1024**2:
            raise Problem("Invalid or oversized request", 413)
        data = request.get_json()
        if not isinstance(data, dict):
            raise Problem("Expected a JSON object")
        return data

    @app.get("/healthz")
    def health():
        return {"ok": True}

    @app.get("/")
    @app.get("/<name>")
    def static_file(name="index.html"):
        if name not in {"index.html", "app.js", "style.css", "favicon.svg"}:
            raise Problem("Not found", 404)
        return send_file(STATIC / name)

    @app.get("/api/bootstrap")
    def bootstrap():
        workspace = g.workspace
        return {"mode": "hosted", "token": portal.sign("csrf:" + workspace.root.name),
                "defaults": workspace.options({}, cfg), "preferences": workspace.app.preferences,
                "catalog": engine.catalog(), "active": workspace.app.active,
                "limits": {"file_bytes": cfg.file_bytes, "upload_bytes": cfg.upload_bytes,
                           "max_files": cfg.max_files, "workers": cfg.workers, "retention_hours": cfg.retention // 3600},
                "tools": [{"name": Path(p).name, "ready": (engine.REPO / p).is_file()}
                          for p in sorted(set(engine.stager.BUILT_BINARIES.values()))]}

    @app.post("/api/preferences")
    def preferences():
        data, workspace = body(), g.workspace
        sources = data.get("sources", [])
        if sources:
            workspace.sources(sources)
        with workspace.app.lock:
            workspace.app.preferences = {"options": workspace.options(data.get("options", {}), cfg),
                "sources": sources, "theme": "dark" if data.get("theme") == "dark" else "light"}
            engine.write_json(workspace.work / "preferences.json", workspace.app.preferences)
        return {"ok": True}

    @app.post("/api/upload-batch")
    def upload_batch():
        workspace = g.workspace
        with portal.operation(workspace):
            if len(workspace.app.uploads) >= 100:
                raise Problem("Too many upload batches. Delete your files to start over.", 413)
            batch = uuid.uuid4().hex
            (workspace.work / "uploads" / batch).mkdir(parents=True)
            workspace.app.uploads.add(batch)
        return {"batch": batch, "root": "uploads/" + batch}

    @app.put("/api/upload")
    def upload():
        workspace = g.workspace
        with portal.operation(workspace):
            batch = request.args.get("batch", "")
            if batch not in workspace.app.uploads:
                raise Problem("Unknown upload batch", 404)
            folder = workspace.work / "uploads" / batch
            relative = engine.safe_relative(request.args.get("path", ""))
            target = folder / relative
            if not engine.within(target, workspace.root) or not engine.within(target, folder) or target.exists() or len(relative) > 1000:
                raise Problem("Duplicate or invalid upload path")
            length = request.content_length
            if length is None or not 0 <= length <= cfg.file_bytes:
                raise Problem("This file exceeds the server's per-file upload limit", 413)
            size, count = disk_usage(workspace.work / "uploads")
            if size + length > cfg.upload_bytes or count >= cfg.max_files:
                raise Problem("Upload allowance reached. Download your results and delete your files to start over.", 413)
            portal.reserve(workspace, length)
            partial = target.with_name(target.name + ".uploading")
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(partial, "xb") as f:
                    left = length
                    while left:
                        chunk = request.stream.read(min(left, 1024**2))
                        if not chunk:
                            raise Problem("Upload interrupted")
                        f.write(chunk)
                        left -= len(chunk)
                os.replace(partial, target)
            finally:
                partial.unlink(missing_ok=True)
                with portal.lock:
                    portal.reserved -= length
        return {"relative": relative}

    @app.post("/api/scan")
    def scan():
        workspace, data = g.workspace, body()
        with portal.operation(workspace):
            if workspace.active():
                raise Problem("Wait for your active conversion to finish", 409)
            sources = workspace.sources(data.get("sources"))
            # A new directory for every plan makes earlier runs' downloads immutable.
            destination = workspace.output / uuid.uuid4().hex
            plan = engine.scan(sources, workspace.options(data.get("options", {}), cfg, destination))
            for row in plan["rows"]:
                if os.name != "nt" and row["status"] in engine.READY:
                    rule = engine.BY_ID.get(row["rule"])
                    closure = engine.stager.tool_import_closure(rule.tool) if rule else set()
                    windows = any("find_fxc(" in (engine.ASSETS / p).read_text(encoding="utf-8", errors="replace") for p in closure)
                    if windows:
                        row.update(status="blocked", detail="This shader route requires Windows fxc.exe. Use the desktop converter for this file.")
            plan["counts"] = dict(Counter(row["status"] for row in plan["rows"]))
            plan["free_bytes"] = min(plan["free_bytes"], max(0, cfg.workspace_bytes - disk_usage(workspace.root)[0]))
            workspace.app.plans = {plan["id"]: plan}
        return plan

    @app.post("/api/start")
    def start():
        workspace, data = g.workspace, body()
        with portal.operation(workspace), portal.lock:
            if sum(bool(w.active()) for w in portal.apps.values()) >= cfg.max_jobs:
                raise Problem("All conversion slots are busy. Please try again shortly.", 503)
            plan = workspace.app.plans.get(data.get("plan"))
            if not plan:
                raise Problem("Inspect your files again before starting")
            selected = data.get("selected")
            if not isinstance(selected, list) or len(selected) > cfg.max_files:
                raise Problem("Invalid file selection")
            selected_ids = set(selected)
            estimate = sum(row["size"] for row in plan["rows"] if row["id"] in selected_ids) * 3 + (256 << 20)
            portal.reserve(workspace, estimate)
            try:
                result = workspace.app.start(plan, selected)
                workspace.app.plans.clear()
                return result
            finally:
                portal.reserved -= estimate

    @app.post("/api/cancel")
    def cancel():
        workspace, data = g.workspace, body()
        portal.entry(workspace, data.get("id", ""))
        workspace.app.cancel(data["id"])
        return {"ok": True}

    @app.get("/api/job/<identifier>")
    def job(identifier):
        portal.entry(g.workspace, identifier)
        return g.workspace.app.job_snapshot(identifier, max(0, int(request.args.get("after", 0))))

    @app.get("/api/history")
    def history():
        return {"runs": g.workspace.app.history}

    @app.get("/api/report/<identifier>")
    @app.get("/api/log/<identifier>")
    def report(identifier):
        workspace = g.workspace
        portal.entry(workspace, identifier)
        filename = "report.json" if "/report/" in request.path else "activity.log"
        path = workspace.work / "jobs" / identifier / filename
        if not engine.within(path, workspace.root) or path.is_symlink() or not path.is_file():
            raise Problem("This report is not available", 404)
        return send_file(path, as_attachment=True, download_name=f"paradise-{identifier[:8]}-{filename}")

    @app.get("/api/download/<identifier>")
    @app.post("/api/archive/<identifier>")
    def download(identifier):
        workspace = g.workspace
        with portal.operation(workspace):
            entry = portal.entry(workspace, identifier)
            if entry["status"] in ACTIVE or workspace.active():
                raise Problem("Wait for your conversion to finish before downloading", 409)
            root = Path(entry["output"])
            if not engine.within(root, workspace.root) or not engine.within(root, workspace.output):
                raise Problem("Invalid output location", 403)
            archive = workspace.work / "jobs" / identifier / "converted.zip"
            if not engine.within(archive, workspace.root) or archive.is_symlink():
                raise Problem("Invalid archive location", 403)
            if not archive.is_file():
                paths = [p for p in root.rglob("*") if p.is_file() and not p.is_symlink()
                         and engine.RESERVED not in p.relative_to(root).parts and engine.within(p, root)]
                if not paths:
                    raise Problem("This run did not produce downloadable files", 404)
                reserve = sum(p.stat().st_size + 1024 for p in paths) + (1 << 20)
                portal.reserve(workspace, reserve)
                partial = archive.with_suffix(".partial")
                try:
                    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zipped:
                        for file in paths:
                            zipped.write(file, file.relative_to(root).as_posix())
                    os.replace(partial, archive)
                finally:
                    partial.unlink(missing_ok=True)
                    with portal.lock:
                        portal.reserved -= reserve
            if request.method == "POST":
                return {"url": "/api/download/" + identifier}
            # send_file streams/ranges the archive; it never builds a browser-sized blob.
            return send_file(archive, as_attachment=True, download_name=f"paradise-converted-{identifier[:8]}.zip", conditional=True)

    @app.post("/api/delete-workspace")
    def delete_workspace():
        workspace = g.workspace
        with portal.operation(workspace), portal.lock:
            if workspace.active() or workspace.readers > 1:
                raise Problem("Wait for this workspace's active operations to finish first", 409)
            if not engine.within(workspace.root, portal.root) or workspace.root == portal.root:
                raise Problem("Invalid workspace", 403)
            shutil.rmtree(workspace.root)
            portal.apps.pop(workspace.root.name, None)
        response = jsonify(ok=True)
        g.new_cookie = None
        response.delete_cookie(COOKIE, path="/")
        return response

    return app
