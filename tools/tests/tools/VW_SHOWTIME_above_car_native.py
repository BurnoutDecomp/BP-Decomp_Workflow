"""Run b5-decomp/tests/run_playtest_above_car.py with its fixture's PerfMonCpu stub matched to
the real five-argument AddMonitor declaration.

The fixture stubs AddMonitor(const char*, s32, s32, double, s32, s32); the six-argument form
was removed tree-wide (the console only has AddMonitor(name, page, minimum, budget, scaled)), so
the stub no longer satisfies AboveCarRenderer::Construct's call and the fixture fails to link
before any check runs. Only the stub line is rewritten, in a temporary copy; the production
bodies the fixture extracts are untouched.

usage (from the workflow checkout):
  python tools/tests/tools/VW_SHOWTIME_above_car_native.py
"""
import os
import runpy
import sys
import tempfile
from pathlib import Path

os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
WORKFLOW = Path(__file__).resolve().parents[3]
TESTS = WORKFLOW / "b5-decomp" / "tests"
FIXTURE = TESTS / "PlaytestAboveCar.cpp"
OLD_STUB = "s32 AddMonitor(const char*,s32,s32,double,s32,s32){return 1;}"
NEW_STUB = "s32 AddMonitor(const char*,PerfMonCpuPage,bool,f32,bool){return 1;}"


def main():
    text = FIXTURE.read_text(encoding="utf-8-sig")
    if OLD_STUB not in text and NEW_STUB not in text:
        raise SystemExit("PlaytestAboveCar.cpp: AddMonitor stub not found; fixture changed upstream")
    with tempfile.TemporaryDirectory(prefix="vw_showtime_above_car_") as directory:
        patched = Path(directory) / "PlaytestAboveCar.cpp"
        patched.write_text(text.replace(OLD_STUB, NEW_STUB), encoding="utf-8")
        sys.path.insert(0, str(TESTS))
        import fxgs_common

        original = fxgs_common.compile_and_run

        def compile_and_run(test_cpp, *args, **kwargs):
            if Path(test_cpp).name == FIXTURE.name:
                test_cpp = patched
            return original(test_cpp, *args, **kwargs)

        fxgs_common.compile_and_run = compile_and_run
        sys.argv = [str(TESTS / "run_playtest_above_car.py")]
        runpy.run_path(str(TESTS / "run_playtest_above_car.py"), run_name="__main__")


if __name__ == "__main__":
    main()
