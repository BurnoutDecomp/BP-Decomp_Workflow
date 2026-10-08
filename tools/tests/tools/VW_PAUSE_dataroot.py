"""Private mirror root for a run against ONE replaced data file, without touching build\\game.

  python tools/tests/tools/VW_PAUSE_dataroot.py <mirror_root> <slot> <published name>=<replacement file> [...]

Builds <mirror_root> so that tools\\diagnostics\\flow_run.ps1 run from it (root = two levels above its own
directory) launches the real slot exe against a data set that differs from build\\game ONLY in the named files:
  <mirror>\\tools, \\b5-decomp, \\scratch   directory junctions to the real ones (cases, fixtures, run dirs unchanged)
  <mirror>\\build\\game                    the real build\\game, every file HARD-LINKED (no copy), except each
                                         replaced name, which is a real copy of the replacement
  <mirror>\\build\\game_slots\\<slot>        the real slot folder, hard-linked
Run a case from it with:
  powershell -ExecutionPolicy Bypass -File <mirror>\\tools\\tests\\run_case.ps1 -Case <name> -Slot <slot>
Delete the mirror with rmdir /s on the junction-free parts only (the script prints the command).
Hard links share content with build\\game: nothing here writes data files, only Memcard_<slot> and the slot log,
which belong to the slot that ran.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def junction(link, target):
    if link.exists():
        return
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)


def mirror(src, dst, replaced):
    count = 0
    for directory, _subdirs, files in os.walk(src):
        rel = Path(directory).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for name in files:
            target = dst / rel / name
            if target.exists():
                target.unlink()
            key = str(rel / name).replace("\\", "/").lstrip("./")
            if key in replaced:
                shutil.copyfile(replaced[key], target)
                print(f"replaced {key} <- {replaced[key]}")
            else:
                os.link(Path(directory) / name, target)
            count += 1
    return count


def main():
    root = Path(sys.argv[1]).resolve()
    slot = sys.argv[2]
    replaced = {}
    for spec in sys.argv[3:]:
        name, path = spec.split("=", 1)
        replaced[name.replace("\\", "/")] = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ("tools", "b5-decomp", "scratch"):
        junction(root / name, REPO / name)
    game = mirror(REPO / "build" / "game", root / "build" / "game", replaced)
    slots = mirror(REPO / "build" / "game_slots" / slot, root / "build" / "game_slots" / slot, {})
    missing = [name for name in replaced if not (root / "build" / "game" / name).exists()]
    if missing:
        raise SystemExit(f"replacement target(s) not in build\\game: {missing}")
    print(f"mirror {root}: {game} game files, {slots} slot files")
    print(f"remove: rmdir {root / 'tools'} & rmdir {root / 'b5-decomp'} & rmdir {root / 'scratch'} & rmdir /s /q {root / 'build'}")


if __name__ == "__main__":
    main()
