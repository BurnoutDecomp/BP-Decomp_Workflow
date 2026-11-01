"""Materialize and execute the reviewed private GUI startup/menu continuation."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
sys.path.insert(0, r"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\jump_build_20261031")
import materialize_and_run as m

P = m.W / "scratch/DEBUG_MENU_1011/gui_audio_native_prepare_20261101"
REVIEW = m.W / "progress/debug_menu/gui_audio_route_20261101/NATIVE_PREP_REVIEW.json"


def main():
    verdict = m.read(REVIEW)
    # The final peer verdict is also inspected by Root; no production source is changed.
    assert str(verdict.get("verdict", "")).lower() == "pass"
    assert m.sha(P / "AUTHORED_FILES.json") == verdict["authored_manifest_sha256"]
    assert m.sha(Path(__file__)) == verdict["launcher_sha256"]
    assert not (P / "stage").exists() and not (P / "STAGING.json").exists()
    result = subprocess.run(["pwsh", "-NoProfile", "-File", str(P / "Invoke-PrivateCase.ps1")], capture_output=True, text=True)
    (P / "ROOT_PREP_PREFLIGHT.json").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    assert result.returncode == 0, result.stdout + result.stderr
    template = m.read(P / "STAGING.TEMPLATE.json")
    pins = m.read(P / "SOURCE_PINS.json")
    build_receipt = Path(pins["candidate"]["build_receipt"]["path"])
    assert m.sha(build_receipt) == pins["candidate"]["build_receipt"]["sha256"] == template["build_receipt_sha256"]
    receipt = m.read(build_receipt)
    assert receipt["status"] == "BUILD_PASS" and receipt["b5_commit"] == template["source_commit"]
    assert receipt["exe_sha256"] == template["exe_sha256"]
    profile = m.N / "Memcard/Profile.sav"
    profile_sha = m.sha(profile)
    raw = profile.read_bytes()
    assert m.sha(profile) == profile_sha == template["profile_sha256"] == m.sha(template["profile_fixture"])
    normal = {str(m.N / name): m.sha(m.N / name) for name in receipt["artifacts"]}
    cfg = m.N / "config.ini"
    normal.update({str(profile): profile_sha, str(cfg): m.sha(cfg)})
    slot, data = m.safe(P / "stage/slot"), m.safe(P / "stage/data")
    slot.mkdir(parents=True)
    data.mkdir()
    ids = m.read(m.IDS)
    assert m.sha(m.IDS) == pins["asset_roster"]["sha256"] and len(ids["files"]) == 5622
    for rel, row in ids["files"].items():
        relative = Path(rel)
        assert not relative.is_absolute() and ".." not in relative.parts
        original = m.safe(Path(ids["source_root"]) / relative)
        info = original.stat()
        assert info.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
        assert (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) == (row["dev"], row["ino"], row["bytes"], row["mtime_ns"])
        target = m.safe(data / relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(original, target)
    for name, row in receipt["artifacts"].items():
        original = build_receipt.parent / name
        assert m.sha(original) == row["sha256"]
        shutil.copyfile(original, slot / name)
        assert m.sha(slot / name) == row["sha256"]
    subprocess.run(["pwsh", "-NoProfile", "-File", r"D:\rtex11\NewPrivateResourceConfig.ps1", "-SourcePath", str(cfg), "-DestinationPath", str(slot / "config.ini"), "-ExpectedSourceSha256", normal[str(cfg)], "-ExpectedSourceBytes", str(cfg.stat().st_size), "-PrivateWidth", "1280", "-PrivateHeight", "720"], check=True, capture_output=True)
    private = data / "Memcard_62209/Profile.sav"
    private.parent.mkdir()
    with private.open("xb") as f:
        f.write(raw)
    assert private.stat().st_nlink == 1 and not os.path.samefile(private, profile)
    assert m.sha(private) == profile_sha
    template.update(status="root_materialized_private_stage", exe_dir=str(slot), cwd=str(data), profile=str(private), actual_stage_created=True, allowed_concurrent_game=None)
    template.update(config_path=str(slot / "config.ini"), config_sha256=m.sha(slot / "config.ini"))
    m.write_new(P / "STAGING.json", template)
    m.write_new(P / "ROOT_RUN_AUTHORITY.json", {"final_review_path": str(REVIEW), "final_review_sha256": m.sha(REVIEW), "authored_manifest_sha256": m.sha(P / "AUTHORED_FILES.json"), "launcher_sha256": m.sha(Path(__file__)), "normal_before": normal, "latest_profile_freshly_copied": True, "fixture_identical_to_latest": True, "raw_frames_max": 8, "allowed_concurrent_game": None})
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handles = []
    try:
        for rel in ids["files"]:
            handle = kernel.CreateFileW(str(data / rel), 0x80000000, 1, None, 3, 0x80, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
        env = dict(os.environ, BPH_KEEP_SLOT_EXE="1", PYTHONDONTWRITEBYTECODE="1", TMP=str(m.H / "tmp"), TEMP=str(m.H / "tmp"))
        command = ["pwsh", "-NoProfile", "-File", str(P / "Invoke-PrivateCase.ps1"), "-Execute"]
        with (P / "ROOT_INVOCATION.log").open("x", encoding="utf-8") as log:
            proc = subprocess.Popen(command, cwd=P, env=env, stdout=log, stderr=subprocess.STDOUT)
            m.write_new(P / "ROOT_PROCESS.json", {"pid": proc.pid, "command": command, "asset_read_locks": len(handles)})
            print({"gui_wrapper_pid": proc.pid, "manual_captures": 8, "max_frames": 8}, flush=True)
            code = proc.wait()
        after = {name: m.sha(name) for name in normal}
        m.write_new(P / "ROOT_EXIT.json", {"exit_code": code, "normal_unchanged": after == normal, "site_credit": 0})
        assert after == normal
        print({"gui_exit": code, "normal_unchanged": True}, flush=True)
        raise SystemExit(code)
    finally:
        for handle in handles:
            kernel.CloseHandle(handle)


if __name__ == "__main__":
    main()
