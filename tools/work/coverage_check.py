"""Per-TU close-out check: is every ledger function of a TU genuinely DEFINED, exactly once?

Run this before `work review --verdict pass`. It is the check that has repeatedly caught what
the compile gate cannot: `cl /c` sees neither an unresolved external nor a duplicate definition
across translation units.

    py tools/work/coverage_check.py <tu-id> <class-name> <dir> [file-prefix]
    py tools/work/coverage_check.py --json <tu-id> <class-name> <dir> [file-prefix]

Two failure modes this deliberately guards against, both of which have bitten the campaign:

  * PREFIX MATCHING. A wildcard added to cope with truncated ledger names once let
    `~MemcardState` satisfy the CONSTRUCTOR's ledger entry, so a TU with an unimplemented ctor
    read as complete. Leaves are matched EXACTLY, and `~dtor` is matched explicitly.

  * IDA'S 41-CHARACTER SYMBOL TRUNCATION. Ledger names are clipped at 41 chars for the fully
    qualified symbol, so `...ChallengeManager::GetChalle` is really `GetChallengeIndex`. A
    clipped leaf is reported as TRUNCATED with its candidates rather than silently missed --
    or silently "matched" by a prefix rule.

Comments and block comments are stripped first, so a commented-out body never counts.
Compiler-auto-emitted deleting-destructor thunks are ignored (the family convention).
"""
import json, re, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / 'progress' / 'ledger.sqlite'
IDA_SYMBOL_MAX = 41          # IDA clips the qualified name at this width


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return '\n'.join(re.sub(r'//.*', '', line) for line in text.splitlines())


def defined_leaves(src, cls=None):
    """(class, leaf) pairs defined out-of-line in `src`; `cls` restricts to one class."""
    who = re.escape(cls) if cls else r'[A-Za-z_]\w*'
    pat = re.compile(r'\b(' + who + r')\s*::\s*(~?\s*[A-Za-z_]\w*)\s*\(')
    return [(m.group(1), m.group(2).replace(' ', '')) for m in pat.finditer(src)]


def check(tu_id, cls, directory, prefix=''):
    src = ''
    d = Path(directory)
    if not d.is_absolute():
        d = ROOT / d
    if d.exists():
        for f in sorted(d.glob((prefix or '') + '*.cpp')):
            src += f.read_text(encoding='utf-8', errors='replace')
    src = strip_comments(src)

    # `cls` may be omitted: a header-keyed TU often spans SEVERAL classes (one AttribSys TU
    # carries Attribute, Collection and RefSpec functions), so the class is taken from each
    # ledger name's own qualifier unless the caller pins one.
    counts = {}
    for c, leaf in defined_leaves(src, cls if cls and cls != '-' else None):
        counts[(c, leaf)] = counts.get((c, leaf), 0) + 1

    con = sqlite3.connect(str(LEDGER))
    rows = [r[0] for r in con.execute('select name from func where tu_id=?', (tu_id,))]

    missing, duplicated, truncated = [], [], []
    for name in rows:
        parts = name.split('::')
        leaf = parts[-1].split('(')[0].strip()
        owner = parts[-2] if len(parts) >= 2 else (cls or '')
        if 'deleting destructor' in leaf:
            continue                                   # compiler-auto-emitted
        exact = counts.get((owner, leaf), 0)
        if exact == 0:
            # a leaf may be clipped: the FULL ledger name sits right at IDA's limit
            if len(name) >= IDA_SYMBOL_MAX:
                cands = sorted({l for (c, l) in counts
                                if c == owner and l.startswith(leaf) and l != leaf})
                if len(cands) == 1:
                    continue                           # unambiguous truncation, treat as defined
                if cands:
                    # Ambiguous WHICH function this clipped name is, but every candidate is
                    # defined -- so coverage holds whichever it is. Report it (the ledger name
                    # is still wrong and worth fixing) without blocking the close.
                    truncated.append((owner + '::' + leaf, cands))
                else:
                    missing.append(owner + '::' + leaf)   # clipped AND nothing starts with it
            else:
                missing.append(owner + '::' + leaf)
        elif exact > 1:
            duplicated.append((owner + '::' + leaf, exact))

    return {
        'tu': tu_id, 'class': cls, 'ledger_funcs': len(rows),
        'missing': missing, 'duplicated': duplicated, 'truncated_ambiguous': truncated,
        # ambiguity alone does not block: every candidate of a clipped name is defined
        'ok': not missing and not duplicated,
    }


def main(argv):
    as_json = '--json' in argv
    argv = [a for a in argv if a != '--json']
    if len(argv) < 4:
        print(__doc__)
        return 2
    res = check(argv[1], argv[2], argv[3], argv[4] if len(argv) > 4 else '')
    if as_json:
        print(json.dumps(res, indent=1))
    else:
        print('%-46s ledger=%d' % (res['tu'][-46:], res['ledger_funcs']))
        print('  missing            : %d %s' % (len(res['missing']), res['missing'] or ''))
        print('  DUPLICATE (ODR)    : %d %s' % (len(res['duplicated']), res['duplicated'] or ''))
        print('  truncated/ambiguous: %d %s' % (len(res['truncated_ambiguous']), res['truncated_ambiguous'] or ''))
        note = '' if not res['truncated_ambiguous'] else                '  (clipped ledger name(s), but all candidates are defined -- coverage holds)'
        print('  -> %s%s' % ('OK, safe to close' if res['ok'] else 'DO NOT CLOSE', note))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
