#!/usr/bin/env python3
"""Batch-convert the staged X360 world data to platform-4 via
convert_world_bundle.py, in parallel.

- TRK_UNIT<N>_GR.BNDL (all), WORLDTEX.BIN, GLOBALBACKDROPS.BNDL -> the full
  per-type port (Renderable/InstanceList/Model/Texture/Material/MatTech/
  TextureState/VertexDescriptor; MaterialState/Prop*/StaticSoundMap still
  passthrough pending the engine-side widening reconciliation).
- Each worker gets its OWN copy of build/tools/volatility (the CLI stores
  imported resources in an exe-adjacent data dir; shared-resource ids across
  units would race a shared store).
- Output -> build/game_p4_world/<same name>. Existing outputs are skipped, so
  the batch is resumable.

Usage:  py tools/assets/bundles/batch_convert_world.py [--workers N] [--limit N]
"""
import argparse
import multiprocessing
import os
import shutil
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
GAME = os.path.join(ROOT, 'build', 'game_x360_world')   # the X360 originals (build/game holds staged conversions)
OUT = os.path.join(ROOT, 'build', 'game_p4_world')
VOLA_SRC = os.path.join(ROOT, 'build', 'tools', 'volatility')
WORKTMP = os.path.join(ROOT, 'build', 'tools', 'volatility_workers')


def _worker_init():
    import convert_world_bundle
    wid = multiprocessing.current_process().name
    wdir = os.path.join(WORKTMP, wid)
    if not os.path.isdir(wdir):
        shutil.copytree(VOLA_SRC, wdir)
    convert_world_bundle.VOLA = os.path.join(wdir, 'Volatility.Cli.exe')
    convert_world_bundle.VOLA_RES = os.path.join(wdir, 'data', 'Resources')


def _convert_one(name):
    import convert_world_bundle
    src = os.path.join(GAME, name)
    dst = os.path.join(OUT, name)
    if os.path.isfile(dst) and os.path.getsize(dst) > 0:
        return (name, 'skip', '')
    try:
        manifest = convert_world_bundle.convert(src, dst)
        return (name, 'ok', str(manifest['ported']))
    except BaseException as e:
        if os.path.isfile(dst):
            os.remove(dst)
        return (name, 'FAIL', '%s\n%s' % (e, traceback.format_exc(limit=3)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORKTMP, exist_ok=True)

    names = sorted(n for n in os.listdir(GAME)
                   if n.startswith('TRK_UNIT') and n.endswith('_GR.BNDL'))
    for extra in ('GLOBALBACKDROPS.BNDL', 'GLOBALPROPS.BIN'):
        if os.path.isfile(os.path.join(GAME, extra)):
            names.append(extra)
    if args.limit:
        names = names[:args.limit]

    print('converting %d bundles with %d workers' % (len(names), args.workers), flush=True)
    ok = fail = skip = 0
    with multiprocessing.Pool(args.workers, initializer=_worker_init) as pool:
        for name, status, detail in pool.imap_unordered(_convert_one, names):
            if status == 'ok':
                ok += 1
            elif status == 'skip':
                skip += 1
            else:
                fail += 1
                print('FAIL %s: %s' % (name, detail), flush=True)
            done = ok + fail + skip
            if done % 10 == 0 or status == 'FAIL':
                print('[%d/%d] ok=%d skip=%d fail=%d (last: %s %s)'
                      % (done, len(names), ok, skip, fail, name, status), flush=True)
    print('DONE ok=%d skip=%d fail=%d' % (ok, skip, fail), flush=True)
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(main())
