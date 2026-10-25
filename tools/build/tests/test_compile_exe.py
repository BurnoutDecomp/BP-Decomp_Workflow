"""Failed builds must leave the last runnable binary and its symbols intact.

Run with: python -m unittest discover -s tools/build/tests -v
The real-link test also runs when MSVC's cl is on PATH.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location(
    "compile_exe", Path(__file__).resolve().parents[1] / "compile_exe.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class BuildVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="build identity ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "selected source"
        self.repo.mkdir()
        self.renderer = self.repo / "src/GameShared/GameClasses/Development/DebugSystem/Core/CgsDebugManager.cpp"
        self.renderer.parent.mkdir(parents=True)
        self.renderer.write_text('#include "BrnBuildVersion.h"\nconst char* commit = B5_BUILD_COMMIT;\n')
        self.git("init", "--quiet")
        self.git("config", "user.name", "Build test")
        self.git("config", "user.email", "build-test@example.invalid")
        self.git("add", "src")
        self.git("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "initial")
        self.out = self.root / "output with spaces"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args],
                                       text=True, stderr=subprocess.STDOUT).strip()

    def generate(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return Path(driver.write_build_version(str(self.out), str(self.repo)))

    def test_overlay_uses_selected_source_commit(self):
        header = self.generate()
        self.assertIn('"' + self.git("rev-parse", "--short=12", "HEAD") + '"', header.read_text())
        self.assertNotIn("unknown", header.read_text())

    def test_unchanged_identity_does_not_rewrite_header(self):
        header = self.generate()
        os.utime(header, ns=(1_000_000_000, 1_000_000_000))
        self.generate()
        self.assertEqual(header.stat().st_mtime_ns, 1_000_000_000)

    def test_dirty_and_new_commit_refresh_identity(self):
        header = self.generate()
        previous = header.read_text()
        self.renderer.write_text(self.renderer.read_text() + "// local change\n")
        self.generate()
        self.assertIn("+dirty", header.read_text())
        self.git("-c", "commit.gpgsign=false", "commit", "--quiet", "-am", "next")
        self.generate()
        self.assertNotIn("+dirty", header.read_text())
        self.assertNotEqual(header.read_text(), previous)

    def test_only_renderer_compile_flags_change(self):
        header = self.generate()
        other = str(self.repo / "src/Other.cpp")
        flags = ["/nologo", "/EHsc"]
        options = driver.source_compile_options([str(self.renderer), other], flags, str(self.repo), str(header))
        self.assertEqual(options[other][0], flags)
        self.assertEqual(options[str(self.renderer)][0], flags + ["/I" + str(header.parent)])
        self.assertNotEqual(options[other][1], options[str(self.renderer)][1])

    def test_commit_change_invalidates_content_cached_renderer(self):
        header = self.generate()
        obj = str(self.out / "renderer.obj")
        Path(obj).write_bytes(b"cached object")
        deps = [str(self.renderer), str(header)]
        digest = driver.deps_digest(deps, driver.HashCache())
        Path(obj + ".d").write_text("flags\n@digest " + digest + "\n" + "\n".join(deps) + "\n")
        self.assertFalse(driver.is_stale(obj, "flags", driver.StatCache(), driver.HashCache()))
        # A commit with identical source bytes must still change the rendered identity.
        self.git("-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", "identity only")
        self.generate()
        self.assertTrue(driver.is_stale(obj, "flags", driver.StatCache(), driver.HashCache()))

    @unittest.skipUnless(os.name == "nt" and shutil.which("cl"), "requires MSVC cl")
    def test_msvc_sees_generated_header_and_records_dependency(self):
        header = self.generate()
        options = driver.source_compile_options([str(self.renderer)], ["/nologo"], str(self.repo), str(header))
        flags, fingerprint = options[str(self.renderer)]
        obj = str(self.out / "renderer.obj")
        rc, shown, _ = driver.compile_one(str(self.renderer), obj, flags, fingerprint,
            dict(os.environ), driver.detect_note_prefix(dict(os.environ), str(self.out)), driver.HashCache())
        self.assertEqual(rc, 0, "\n".join(shown))
        self.assertIn(str(header), Path(obj + ".d").read_text())
        self.assertIn(self.git("rev-parse", "--short=12", "HEAD").encode(), Path(obj).read_bytes())


class LinkPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="link safety ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exe = self.root / "Burnout_PC.exe"
        self.map = self.exe.with_suffix(".map")
        self.cgsmap = self.exe.with_suffix(".cgsmap")
        self.provenance = Path(str(self.exe) + ".provenance.json")
        self.old = {self.exe: b"old executable", self.map: b"old map",
                    self.cgsmap: b"old binary symbols", self.provenance: b"old identity"}
        for path, data in self.old.items():
            path.write_bytes(data)
        self.obj_dir = self.root / "obj"
        self.obj_dir.mkdir()

    def link(self, tail=None, objs=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return driver.run_link(objs or [], str(self.exe), tail or ["/MAP"],
                                   str(self.obj_dir), dict(os.environ), driver.Diags())

    def assert_preserved(self):
        for path, data in self.old.items():
            self.assertEqual(path.read_bytes(), data, str(path))
        self.assertEqual(list(self.root.glob(".link-*")), [])

    def fake_success(self, objs, exe, tail, *unused):
        # These assertions run while the child linker would be writing outputs.
        for path, data in self.old.items():
            self.assertEqual(path.read_bytes(), data)
        Path(exe).write_bytes(b"new executable")
        for arg in tail:
            if arg.startswith("/MAP:"):
                Path(arg.partition(":")[2]).write_bytes(b"new map")
        return 0

    def test_failed_link_does_not_delete_working_build(self):
        def fail(*args):
            self.fake_success(*args)
            Path(args[1]).unlink()  # LINK deletes its output after LNK1120.
            return 1120
        with mock.patch.object(driver, "_run_link", side_effect=fail):
            self.assertEqual(self.link(), 1120)
        self.assert_preserved()

    def test_interrupted_link_preserves_working_build(self):
        def interrupted(*args):
            self.fake_success(*args)
            raise KeyboardInterrupt
        with mock.patch.object(driver, "_run_link", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.link()
        self.assert_preserved()

    def test_success_replaces_executable_and_map(self):
        with mock.patch.object(driver, "_run_link", side_effect=self.fake_success):
            self.assertEqual(self.link(), 0)
        self.assertEqual(self.exe.read_bytes(), b"new executable")
        self.assertEqual(self.map.read_bytes(), b"new map")
        self.assertEqual(list(self.root.glob(".link-*")), [])

    def test_executable_locked_during_publication_rolls_back_map(self):
        original_replace = os.replace

        def replace(src, dst):
            if Path(dst) == self.exe:
                raise PermissionError("executable is locked")
            return original_replace(src, dst)

        with mock.patch.object(driver, "_run_link", side_effect=self.fake_success), \
                mock.patch.object(driver.os, "replace", side_effect=replace):
            self.assertEqual(self.link(), 1)
        self.assert_preserved()

    def test_success_without_executable_is_failure(self):
        with mock.patch.object(driver, "_run_link", return_value=0):
            self.assertEqual(self.link(), 1)
        self.assert_preserved()

    def test_explicit_output_paths_are_also_staged(self):
        named_map = self.root / "named symbols.map"
        named_pdb = self.root / "named symbols.pdb"
        named_map.write_bytes(b"original named map")
        named_pdb.write_bytes(b"original named pdb")

        def fail(objs, exe, tail, *unused):
            for arg in tail:
                key, _, value = arg.partition(":")
                if key in ("/MAP", "/PDB", "/IMPLIB", "/ILK"):
                    self.assertEqual(Path(value).parent, Path(exe).parent)
                    Path(value).write_bytes(b"incomplete output")
            return 1120

        with mock.patch.object(driver, "_run_link", side_effect=fail):
            self.assertEqual(self.link([f"/MAP:{named_map}", f"/PDB:{named_pdb}",
                                        f"/OUT:{self.exe}"]), 1120)
        self.assertEqual(named_map.read_bytes(), b"original named map")
        self.assertEqual(named_pdb.read_bytes(), b"original named pdb")
        self.assert_preserved()

    @unittest.skipUnless(os.name == "nt" and shutil.which("cl"), "requires MSVC cl")
    def test_real_msvc_unresolved_external_preserves_runnable_exe(self):
        source = self.root / "main.cpp"
        obj = self.obj_dir / "main.obj"

        def compile_source(body):
            source.write_text(body, encoding="utf-8")
            result = subprocess.run(["cl", "/nologo", "/c", str(source), f"/Fo{obj}"],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        compile_source('__declspec(dllexport) int exported() { return 42; }\n'
                       'int main() { return exported() == 42 ? 0 : 1; }\n')
        tail = ["/SUBSYSTEM:CONSOLE", "/MAP", "/OPT:REF"]
        self.assertEqual(self.link(tail, [str(obj)]), 0)
        self.assertEqual(subprocess.run([str(self.exe)], timeout=10).returncode, 0)
        for path in self.old:
            self.old[path] = path.read_bytes()
        for suffix in (".lib", ".exp"):
            path = self.exe.with_suffix(suffix)
            self.assertTrue(path.is_file(), str(path))
            self.old[path] = path.read_bytes()
        compile_source('extern int missing();\nint main() { return missing(); }\n')
        self.assertNotEqual(self.link(tail, [str(obj)]), 0)
        self.assert_preserved()
        self.assertEqual(subprocess.run([str(self.exe)], timeout=10).returncode, 0)


if __name__ == "__main__":
    unittest.main()
