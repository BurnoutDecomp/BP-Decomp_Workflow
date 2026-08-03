#!/usr/bin/env python3
"""Index an .ida-exports build directory into compact, greppable side files.

Recursive grep over an export dir is not viable (BurnoutPR.exe is 187k small
JSON files and times out past 5 minutes returning nothing). Index once, then
query the index.

Usage:
    python tools/ida/export_index.py <export_dir> <out_base>

e.g.
    python tools/ida/export_index.py .ida-exports/BurnoutPR.exe D:/idx/bpr

Writes three files:
    <out_base>.tsv      addr, name, n_xrefs_to, n_xrefs_from, asm_lines,
                        pseudocode_chars, prototype
    <out_base>.edges    addr <TAB> comma-separated callee addresses
    <out_base>.floats   addr <TAB> comma-separated float literals in pseudocode

Notes
-----
* `xrefs_to` / `xrefs_from` entries are DICTS ({'address':..,'name':..}), not
  strings. Stringifying them naively corrupts every edge (a comma-joined dict
  splits into two fields, inflating out-degree). `_addrs()` handles both shapes.
* Timings, 10 workers: 30k files ~25 s, 77k ~60 s, 187k ~150 s.
* Put the output on D: — C: runs tight on this machine.
"""
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor

FLOAT_RE = re.compile(r'\b(\d+\.\d+(?:e[-+]?\d+)?)\b', re.I)


def _addrs(lst):
    """Extract addresses from an xrefs list that may hold dicts or strings."""
    out = []
    for x in lst or ():
        if isinstance(x, dict):
            a = x.get('address')
            if a:
                out.append(str(a))
        elif isinstance(x, str):
            out.append(x)
    return out


def _one(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            d = json.load(f)
    except Exception:
        return None
    asm = d.get('assembly') or ''
    pc = d.get('pseudocode') or ''
    return (
        d.get('address', ''),
        d.get('name', ''),
        len(d.get('xrefs_to') or ()),
        len(d.get('xrefs_from') or ()),
        asm.count('\n') + (1 if asm else 0),
        len(pc),
        (d.get('prototype') or '').replace('\t', ' ').replace('\n', ' '),
        _addrs(d.get('xrefs_from')),
        sorted(set(FLOAT_RE.findall(pc)))[:40],
    )


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, outbase = sys.argv[1], sys.argv[2]
    files = [os.path.join(src, f) for f in os.listdir(src) if f.endswith('.json')]
    print(f'{len(files)} files', flush=True)

    n = 0
    with open(outbase + '.tsv', 'w', encoding='utf-8', newline='\n') as tsv, \
            open(outbase + '.edges', 'w', encoding='utf-8', newline='\n') as edg, \
            open(outbase + '.floats', 'w', encoding='utf-8', newline='\n') as flo:
        tsv.write('addr\tname\tn_to\tn_from\tasm_lines\tpc_chars\tprototype\n')
        with ProcessPoolExecutor(max_workers=10) as ex:
            for r in ex.map(_one, files, chunksize=200):
                if r is None:
                    continue
                addr, name, nt, nf, al, pcn, proto, xf, floats = r
                tsv.write(f'{addr}\t{name}\t{nt}\t{nf}\t{al}\t{pcn}\t{proto}\n')
                if xf:
                    edg.write(addr + '\t' + ','.join(xf) + '\n')
                if floats:
                    flo.write(addr + '\t' + ','.join(floats) + '\n')
                n += 1
                if n % 20000 == 0:
                    print(f'  {n}', flush=True)
    print(f'done {n}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
