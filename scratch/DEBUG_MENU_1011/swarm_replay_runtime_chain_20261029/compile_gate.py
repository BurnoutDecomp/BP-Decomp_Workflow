"""Compile the private GameModule against immutable source24 and named provider layers."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, tempfile

OWN = Path(__file__).resolve().parent
WF = OWN.parents[2]
BASE = "f1d1a5ebce785cfe2dc5315b2b3292d95983e6b8"
IMMUTABLE = Path(r"C:/Users/adri1/.codex/worktrees/swarm-shipping-build-20261027/BP-Decomp_Workflow")


def lines(path):
    return [x.strip() for x in path.read_text(encoding="utf-8").splitlines()
            if x.strip() and not x.lstrip().startswith("#")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", action="append", default=[])
    ap.add_argument("--name", default="GameModule")
    ap.add_argument("--source", default="")
    args = ap.parse_args()
    actual = subprocess.check_output(["git", "-C", str(IMMUTABLE / "b5-decomp"),
                                      "rev-parse", "HEAD"], text=True).strip()
    assert actual == BASE, actual
    layers = [OWN / "postimage/b5-decomp/src"] + [Path(x).resolve() for x in args.layer]
    for layer in layers:
        assert layer.is_dir(), layer
    includes = layers + [IMMUTABLE / x.replace("\\", "/")
                         for x in lines(WF / "tools/build/msvc_includes.txt")]
    flags = " ".join(lines(WF / "tools/build/msvc_flags.txt"))
    src = Path(args.source).resolve() if args.source else OWN / "postimage/b5-decomp/src/GameSource/Game/BrnGameModule.cpp"
    pinned = {str(p): sha(p) for layer in layers for p in layer.rglob("*") if p.is_file()}
    pinned[str(src)] = sha(src)
    out = OWN / "gates" / args.name
    out.mkdir(parents=True, exist_ok=False)
    # Object/PDB space remains on C; only small immutable receipts/logs enter the packet.
    with tempfile.TemporaryDirectory(prefix="replay_runtime_gate_", dir=os.environ["TEMP"]) as tmp:
        tmp = Path(tmp)
        rsp = tmp / "compile.rsp"
        rsp.write_text(flags + " /c /showIncludes\n" +
                       "\n".join('/I"' + str(p) + '"' for p in includes) +
                       '\n"' + str(src) + '"\n/Fo"' + str(tmp / "GameModule.obj") + '"\n',
                       encoding="utf-8")
        bat = tmp / "gate.cmd"
        bat.write_text('@echo off\ncall "' + str(WF / "tools/build/msvc_env.bat") +
                       '" >nul 2>&1\nif errorlevel 1 exit /b 200\ncl @"' + str(rsp) +
                       '"\nexit /b %errorlevel%\n', encoding="utf-8")
        result = subprocess.run(["cmd", "/c", str(bat)], cwd=tmp, capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
        log = result.stdout + result.stderr
        drift = [name for name, digest in pinned.items() if sha(Path(name)) != digest]
        assert not drift, "private source changed during compile: " + repr(drift)
        (out / "COMPILE.log").write_text(log, encoding="utf-8")
        (out / "compile.rsp").write_bytes(rsp.read_bytes())
        opened = []
        for line in log.splitlines():
            if "including file:" in line:
                path = Path(line.split("including file:", 1)[1].strip())
                if path.is_file() and any(path.is_relative_to(layer) for layer in layers):
                    opened.append({"path": str(path), "sha256": sha(path)})
        receipt = {"base": BASE, "source": str(src), "source_sha256": sha(src),
                   "layers": [str(p) for p in layers], "opened_private_headers": opened,
                   "pinned_private_sources": pinned, "concurrent_source_drift": False,
                   "returncode": result.returncode, "passed": result.returncode == 0,
                   "canonical_flags": flags, "runtime_proof": False}
        (out / "RESULT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"gate": args.name, "passed": result.returncode == 0,
                          "returncode": result.returncode,
                          "private_headers": len(opened), "receipt": str(out / "RESULT.json")}))
        if result.returncode:
            print("\n".join(x for x in log.splitlines() if "error " in x or "warning " in x))
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
