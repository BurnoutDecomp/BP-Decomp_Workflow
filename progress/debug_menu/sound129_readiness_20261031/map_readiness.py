"""Bind pending Sound sites to current Git declarations and navigation references.

This is a navigation/readiness report, not semantic or native verification.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REPO = ROOT / 'b5-decomp'
REV = 'ca80277748eb098822a035093cff9d306d079e2a'
REL = 'src/GameSource/Sound/BrnDebugComponent.cpp'


def git(*args):
    return subprocess.run(['git', '-C', str(REPO), *args], check=True,
                          capture_output=True).stdout


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def balanced(text, start, opening='(', closing=')'):
    depth, quoted, escape = 0, False, False
    for at in range(start, len(text)):
        ch = text[at]
        if quoted:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return at
    raise ValueError('unclosed expression')


def main():
    inventory_raw = (ROOT / 'progress/debug_menu/entries.json').read_bytes()
    verdict_raw = (ROOT / 'progress/debug_menu/verdicts.json').read_bytes()
    inventory = json.loads(inventory_raw)
    verdicts = json.loads(verdict_raw)
    raw = git('show', f'{REV}:{REL}')
    source = raw.decode('utf-8')
    start = source.index('void DebugComponent::OnActivate()')
    brace = source.index('{', start)
    end = balanced(source, brace, '{', '}')
    body = source[brace:end + 1]
    bindings = []
    for match in re.finditer(r'\bRegisterVariable\s*\(', body):
        first = body.index('(', match.start())
        last = balanced(body, first)
        call = body[first + 1:last]
        labels = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', call)
        assert len(labels) == 2, call
        # There are no comma expressions in these scalar pointer arguments.
        expr = call.split(',', 1)[0].strip()
        target = re.search(r'&\s*((?:[A-Za-z_]\w*::)*[A-Za-z_]\w*)', expr)
        assert target, expr
        bindings.append({'group': labels[0], 'caption': labels[1],
                         'source_line': source[:brace + match.start()].count('\n') + 1,
                         'binding_expression': expr, 'symbol': target.group(1).split('::')[-1]})
    rows = [r for r in inventory['entries']
            if r['function'] == 'BrnSound::Debug::DebugComponent::OnActivate']
    assert len(rows) == len(bindings) == 136
    for row, binding in zip(rows, bindings):
        assert (row['path'], row['caption']) == (binding['group'], binding['caption'])
        binding.update(id=row['id'], state=verdicts.get(row['id'], {}).get('state', 'pending'),
                       original_arguments=row['arguments'])
    symbols = sorted({r['symbol'] for r in bindings})
    args = ['grep', '-n', '-w', '-F']
    for name in symbols:
        args.extend(['-e', name])
    refs_raw = git(*args, REV, '--', 'src')
    refs = collections.defaultdict(list)
    pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, symbols)) + r')\b')
    for line in refs_raw.decode('utf-8', errors='replace').splitlines():
        path, number, text = line[len(REV) + 1:].split(':', 2)
        for name in set(pattern.findall(text)):
            refs[name].append({'path': path, 'line': int(number), 'text': text.strip()})
    pending = []
    for binding in bindings:
        if binding['state'] != 'pending':
            continue
        binding['navigation_references'] = refs[binding['symbol']]
        binding['non_component_reference_paths'] = sorted({r['path'] for r in refs[binding['symbol']]
                                                          if r['path'] != REL})
        binding['binding_status'] = 'present_matching_original_caption_order'
        binding['semantic_behavior_status'] = 'pending'
        pending.append(binding)
    assert len(pending) == 129
    report = {'scope': '129 pending Sound OnActivate sites; Console is a separate pending site',
              'b5_commit': REV, 'source_path': REL, 'source_sha256': digest(raw),
              'source_git_blob': git('rev-parse', f'{REV}:{REL}').decode().strip(),
              'inventory_sha256': digest(inventory_raw), 'verdicts_sha256': digest(verdict_raw),
              'original_onactivate_sha256': digest((ROOT / '.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826D5CB0.json').read_bytes()),
              'all_136_caption_order_match': True, 'pending_count': len(pending),
              'already_disposed_count': len(bindings) - len(pending),
              'limitations': ['Names and references are navigation only; not proof of reads, lifecycle, audio output or semantic parity.',
                             'An absent reference is not an original-noop disposition.',
                             'Duplicate captions and backing cells remain separate original sites.',
                             'Existing source review and follow-on repairs must be reused; this report recovers no new body.'],
              'group_counts': dict(collections.Counter(r['group'] for r in pending)),
              'sites': pending, 'new_site_credit': 0, 'production_source_changes': 0}
    (OUT / 'READINESS.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: report[k] for k in ('b5_commit', 'all_136_caption_order_match', 'pending_count', 'already_disposed_count', 'group_counts', 'new_site_credit')}))


if __name__ == '__main__':
    main()
