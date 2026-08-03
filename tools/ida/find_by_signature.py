#!/usr/bin/env python3
"""Locate a known function in a STRIPPED export set by content signature.

Motivation
----------
The little-endian oracle builds (BurnoutPR.exe, Burnout_External_Xbox_One.exe)
carry almost no symbols for middleware -- every rw::physics function is an
unnamed `sub_`. Name search finds nothing; you must match on what the code
*does*. This scans decompiled pseudocode for a control-flow fingerprint that
survives a recompile to a different ISA.

Discipline (this is the point of the tool)
------------------------------------------
ALWAYS validate a signature against a build where the answer is already known
before trusting it on the target. `--validate` prints the rank of an expected
address so you can see the signal-to-noise. A signature that does not put the
known answer at rank 1 is not a signature.

The bundled `simupdate` signature was validated to rank 1 (uniquely, score 7)
on all three builds: X360 ARTIST (rw::physics::Simulation::SimulationUpdate
@0x82BC6B40), Xbox One (@0x1409B7240) and BurnoutPR (@0x7EA550).

Usage
-----
    python tools/ida/find_by_signature.py <export_dir> [--sig simupdate]
                                          [--validate 0x82BC6B40]

Add signatures to SIGNATURES: a list of (weight, label, compiled regex) plus a
size band and a minimum score.
"""
import argparse
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor

SIGNATURES = {
    # rw::physics::Simulation::SimulationUpdate -- builds a 3-bit pipeline mask
    # from three non-zero counts, dispatches 4 ways, then tests the same three
    # bits again in the Spy* tail. Pure scalar control flow, so it survives
    # PPC/VMX -> x86/SSE -> x64/AVX unchanged.
    'simupdate': dict(
        band=(25, 500),
        minscore=5,
        parts=[
            (3, 'mask|=2,|=4',
             re.compile(r'\|=\s*2u?\b.*?\|=\s*4u?\b', re.S)),
            (1, 'bit1', re.compile(r'&\s*1\)\s*!=\s*0')),
            (1, 'bit2', re.compile(r'&\s*2\)\s*!=\s*0')),
            (1, 'bit4', re.compile(r'&\s*4\)\s*!=\s*0')),
            (1, 'ret0/ret1',
             re.compile(r'return 0.*?return 1', re.S)),
        ],
    ),
}

_SIG = None
_SRC = None


def _init(signame, src):
    global _SIG, _SRC
    _SIG = SIGNATURES[signame]
    _SRC = src


def _probe(fn):
    try:
        with open(os.path.join(_SRC, fn), 'r', encoding='utf-8',
                  errors='replace') as f:
            d = json.load(f)
    except Exception:
        return None
    pc = d.get('pseudocode') or ''
    if not pc:
        return None
    asm = d.get('assembly') or ''
    n = asm.count('\n') + 1
    lo, hi = _SIG['band']
    if not (lo <= n <= hi):
        return None
    score, hits = 0, []
    for w, label, rx in _SIG['parts']:
        if rx.search(pc):
            score += w
            hits.append(label)
    if score < _SIG['minscore']:
        return None
    return score, d.get('address'), d.get('name'), n, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('export_dir')
    ap.add_argument('--sig', default='simupdate', choices=sorted(SIGNATURES))
    ap.add_argument('--validate', help='address that SHOULD rank 1')
    ap.add_argument('--top', type=int, default=20)
    a = ap.parse_args()

    files = [f for f in os.listdir(a.export_dir) if f.endswith('.json')]
    print(f'scanning {len(files)} with signature {a.sig!r}', flush=True)

    res = []
    with ProcessPoolExecutor(max_workers=10, initializer=_init,
                             initargs=(a.sig, a.export_dir)) as ex:
        for r in ex.map(_probe, files, chunksize=300):
            if r:
                res.append(r)
    res.sort(reverse=True)

    print(f'{len(res)} hits\n')
    for s, addr, nm, n, hits in res[:a.top]:
        print(f'score={s} {addr} {nm} asm={n} {hits}')

    if a.validate:
        want = a.validate.lower()
        rank = next((i + 1 for i, r in enumerate(res)
                     if (r[1] or '').lower() == want), None)
        print()
        if rank == 1:
            print(f'VALIDATION OK: {a.validate} ranks 1/{len(res)}')
        elif rank:
            print(f'VALIDATION WEAK: {a.validate} ranks {rank}/{len(res)} '
                  '-- signature is not discriminative enough to trust')
        else:
            print(f'VALIDATION FAILED: {a.validate} not found at all')


if __name__ == '__main__':
    main()
