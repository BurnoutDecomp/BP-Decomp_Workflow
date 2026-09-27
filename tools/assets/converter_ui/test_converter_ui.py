"""Regression coverage for routing, source protection and output publication.

Run: python -m unittest discover -s tools/assets/converter_ui -p 'test_*.py'
Fixtures contain only synthetic container directories; no game data is committed.
"""
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import threading
import sys
import time
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import engine
import server


def bundle(path, types, platform=2):
    endian = ">" if platform == 2 else "<"
    data = bytearray(48 + 64 * len(types))
    data[:4] = b"bnd2"
    struct.pack_into(endian + "9I", data, 4, 2, platform, 0, len(types), 48,
                     len(data), len(data), len(data), 0)
    for i, tid in enumerate(types):
        struct.pack_into(endian + "I", data, 48 + 64 * i + 56, tid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="paradise-ui-test-")
        self.root = Path(self.temp.name)
        self.src = self.root / "source"
        self.src.mkdir()
        self.out = self.root / "output"
        self.preflight = mock.patch.object(engine.stager, "preflight", return_value=[])
        self.preflight.start()

    def tearDown(self):
        self.preflight.stop()
        self.temp.cleanup()

    def plan(self, paths=None, **options):
        return engine.scan([str(p) for p in (paths or [self.src])],
                           {"output": str(self.out), "generate": False, **options})

    def test_identical_environment_basenames_use_resource_types(self):
        env = bundle(self.src / "one/PARADISE_INGAME_JUNK.BUNDLE", [0x10012, 0x10013])
        cube = bundle(self.src / "two/PARADISE_INGAME_JUNK.BUNDLE", [0x2B])
        rows = self.plan([env, cube])["rows"]
        self.assertEqual([r["rule"] for r in rows], ["environment-settings", "environment-colour-cubes"])
        self.assertTrue(all(r["status"] == "ready" for r in rows))
        self.assertNotEqual(rows[0]["output"], rows[1]["output"])

    def test_unknown_resource_set_is_never_generic_container_conversion(self):
        file = bundle(self.src / "custom.bundle", [0xF00DBABE])
        row = self.plan([file])["rows"][0]
        self.assertEqual(row["status"], "unsupported")
        self.assertFalse(self.out.exists())

    def test_truncated_directory_is_blocked_without_scanning_payload(self):
        file = bundle(self.src / "broken.bundle", [0x10012])
        file.write_bytes(file.read_bytes()[:-10])
        self.assertEqual(self.plan([file])["rows"][0]["status"], "blocked")

    def test_non_x360_source_is_not_sent_to_x360_converter(self):
        file = bundle(self.src / "TRK_UNIT123_GR.BNDL", [0], platform=3)
        self.assertEqual(self.plan([file])["rows"][0]["status"], "unsupported")

    def test_loose_vehicle_gets_canonical_path(self):
        file = bundle(self.src / "VEH_PUSMC01_GR.BIN", [0x10006])
        row = self.plan([file])["rows"][0]
        self.assertEqual(row["rule"], "vehicle-graphics")
        self.assertEqual(row["relative"], "VEHICLES/VEH_PUSMC01_GR.BIN")

    def test_flattening_duplicate_names_blocks_both(self):
        bundle(self.src / "a/thing.bundle", [0x10012])
        bundle(self.src / "b/thing.bundle", [0x10013])
        rows = self.plan(keep_layout=False)["rows"]
        self.assertEqual([r["status"] for r in rows], ["blocked", "blocked"])

    def test_nested_folder_layout_survives_content_detection(self):
        bundle(self.src / "a/thing.bundle", [0x10012])
        bundle(self.src / "b/thing.bundle", [0x10013])
        rows = self.plan(keep_layout=True)["rows"]
        self.assertEqual([r["output_relative"] for r in rows], ["a/thing.bundle", "b/thing.bundle"])
        self.assertEqual([r["status"] for r in rows], ["ready", "ready"])

    def test_output_cannot_be_source_or_tooling_tree(self):
        for target in (self.root, self.src, self.src / "inside", engine.REPO / "tools/new", engine.REPO / "build/game/new"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.plan(output=str(target))

    def test_upload_path_rejects_traversal_drives_and_device_names(self):
        for value in ("../escape", "/absolute", "C:/escape", "a/../../b", "a\\..\\b", "NUL.txt", "a/CON", "x/aux.", "a//b"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                engine.safe_relative(value)

    def test_pc_copy_preserves_source_and_resumes_by_signature(self):
        file = bundle(self.src / "already.bundle", [0x10012], 4)
        original = file.read_bytes()
        plan = self.plan([file])
        plan["job_id"] = "copy-test"
        jobdir = self.root / "job"
        jobdir.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            engine.execute_job(plan, ["0"], jobdir)
        self.assertEqual((self.out / "ENVIRONMENTSETTINGS/already.bundle").read_bytes(), original)
        self.assertEqual(file.read_bytes(), original)
        self.assertEqual(self.plan([file])["rows"][0]["status"], "current")
        self.assertEqual(self.plan([file], skip_current=False)["rows"][0]["status"], "exists")

    def test_failed_validation_cannot_replace_existing_output(self):
        file = bundle(self.src / "env.bundle", [0x10012])
        target = self.out / "ENVIRONMENTSETTINGS/env.bundle"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing output must survive")
        plan = self.plan([file], replace=True, skip_current=False)
        plan["job_id"] = "failed-validation"
        fake_root = self.root / "worker"
        fake_root.mkdir()
        jobdir = self.root / "job"
        jobdir.mkdir()
        def fake_convert(rule, argv, *args):
            # Exit success but emit the wrong platform: a converter success alone
            # must never be enough to replace an existing, potentially valid file.
            bundle(Path(argv[-1]), [0x10012], 2)
        output = io.StringIO()
        with mock.patch.object(engine.stager.WorkerRoots, "get", return_value=str(fake_root)), \
             mock.patch.object(engine, "run_converter", side_effect=fake_convert), \
             contextlib.redirect_stdout(output):
            engine.execute_job(plan, ["0"], jobdir)
        self.assertEqual(target.read_bytes(), b"existing output must survive")
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(events[-1]["status"], "completed_with_errors")

    def test_successful_replacement_keeps_backup(self):
        file = bundle(self.src / "already.bundle", [0x10012], 4)
        target = self.out / "ENVIRONMENTSETTINGS/already.bundle"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"old output")
        plan = self.plan([file], replace=True, skip_current=False)
        plan["job_id"] = "backup-test"
        jobdir = self.root / "job"
        jobdir.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            engine.execute_job(plan, ["0"], jobdir)
        backup = self.out / ".asset-converter/backups/backup-test/ENVIRONMENTSETTINGS/already.bundle"
        self.assertEqual(backup.read_bytes(), b"old output")
        self.assertEqual(target.read_bytes(), file.read_bytes())

    def test_source_changed_after_scan_is_not_converted(self):
        file = bundle(self.src / "already.bundle", [0x10012], 4)
        plan = self.plan([file])
        plan["job_id"] = "changed-input"
        file.write_bytes(file.read_bytes() + b"changed")
        jobdir = self.root / "job"
        jobdir.mkdir()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            engine.execute_job(plan, ["0"], jobdir)
        self.assertIn("Source changed after inspection", output.getvalue())
        self.assertFalse((self.out / "ENVIRONMENTSETTINGS/already.bundle").exists())


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="paradise-ui-http-")
        self.work = mock.patch.object(engine, "WORK", Path(self.temp.name) / "cache")
        self.work.start()
        self.app = server.Application()
        self.http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.http.app = self.app
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.http.server_port}"

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.work.stop()
        self.temp.cleanup()

    def test_api_requires_session_token_and_local_origin(self):
        for headers in ({}, {"X-Asset-Token":self.app.token,"Origin":"https://unrelated.example"},
                        {"X-Asset-Token":self.app.token,"Host":"unrelated.example"}):
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.base + "/api/bootstrap", headers=headers))
            self.assertEqual(caught.exception.code, 403)
        with urlopen(Request(self.base + "/api/bootstrap", headers={"X-Asset-Token":self.app.token})) as reply:
            self.assertIn("catalog", json.load(reply))

    def test_upload_rejects_parent_path(self):
        self.app.uploads.add("test")
        request = Request(self.base + "/api/upload?batch=test&path=..%2Foutside.txt", data=b"data", method="PUT", headers={"X-Asset-Token":self.app.token})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        self.assertEqual(caught.exception.code, 400)
        self.assertFalse((Path(self.temp.name) / "outside.txt").exists())

    def test_quit_endpoint_stops_the_local_server(self):
        request = Request(self.base + "/api/shutdown", data=b"{}",
                          headers={"X-Asset-Token":self.app.token})
        with urlopen(request) as reply:
            self.assertTrue(json.load(reply)["ok"])
        self.thread.join(3)
        self.assertFalse(self.thread.is_alive())

    def test_browser_upload_is_streamed_locally_then_detected(self):
        headers = {"X-Asset-Token":self.app.token, "Content-Type":"application/json"}
        with urlopen(Request(self.base + "/api/upload-batch", data=b"{}", headers=headers)) as reply:
            session = json.load(reply)
        file = bundle(Path(self.temp.name) / "fixture.bundle", [0x10012])
        with urlopen(Request(self.base + "/api/upload?batch=" + session["batch"] + "&path=custom.bundle", data=file.read_bytes(), method="PUT", headers=headers)) as reply:
            staged = json.load(reply)
        self.assertEqual(Path(staged["path"]).read_bytes(), file.read_bytes())
        data = json.dumps({"sources":[session["root"]], "options":{"output":str(Path(self.temp.name) / "converted")}}).encode()
        with mock.patch.object(engine.stager, "preflight", return_value=[]):
            with urlopen(Request(self.base + "/api/scan", data=data, headers=headers)) as reply:
                plan = json.load(reply)
        self.assertEqual(plan["rows"][0]["rule"], "environment-settings")

    def test_cancel_stops_converter_child_and_keeps_run_report(self):
        marker = Path(self.temp.name) / "child-finished"
        child = "import time,pathlib;time.sleep(2);pathlib.Path(" + repr(str(marker)) + ").write_text('unexpected')"
        parent = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);print('child started',flush=True);time.sleep(60)"
        job = {"id":"cancel-test", "status":"preparing", "started":time.time(), "ended":None,
               "output":str(Path(self.temp.name) / "out"), "options":{}, "rows":[],
               "label":"Cancellation test", "kind":"setup", "events":[], "sequence":0,
               "cancelled":False, "result":None}
        (engine.WORK / "jobs/cancel-test").mkdir(parents=True)
        self.app.jobs[job["id"]] = job
        self.app.active = job["id"]
        runner = threading.Thread(target=self.app.run, args=(job, [sys.executable,"-u","-c",parent]), daemon=True)
        runner.start()
        deadline = time.monotonic() + 5
        while not job["events"] and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(job["events"], "worker did not start")
        self.app.cancel(job["id"])
        runner.join(5)
        self.assertFalse(runner.is_alive())
        self.assertEqual(job["status"], "cancelled")
        time.sleep(2.1)
        self.assertFalse(marker.exists(), "converter child survived cancellation")
        self.assertTrue((engine.WORK / "jobs/cancel-test/report.json").is_file())


if __name__ == "__main__":
    unittest.main()
