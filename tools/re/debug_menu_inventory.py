"""Inventory ARTIST debug registrations without equating a label with working behavior.

The registration managers' original xrefs identify typed wrappers, including
unnamed wrappers. Search every exported body for those APIs, then retain each
call site's arguments and provenance. Loop-built rows and computed captions stay
explicitly unresolved. Verdicts are maintained separately and survive regeneration.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BUILD = 'BURNOUT_X360_ARTIST.XEX'
MANAGERS = {'0x82829A80': 'variable', '0x8282E7E0': 'function'}


def call_arguments(text: str, opening: int) -> tuple[list[str], int]:
    """Read balanced C++ arguments, preserving strings, casts and nested calls."""
    arguments, start, stack = [], opening + 1, ['(']
    quote, escaped = '', False
    pairs = {')': '(', ']': '[', '}': '{'}
    for position in range(start, len(text)):
        char = text[position]
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = ''
            continue
        if char in '\"\'':
            quote = char
        elif char in '([{':
            stack.append(char)
        elif char in ')]}':
            if not stack or stack.pop() != pairs[char]:
                raise ValueError(f'unbalanced call at {opening}')
            if not stack:
                arguments.append(text[start:position].strip())
                return arguments, position + 1
        elif char == ',' and len(stack) == 1:
            arguments.append(text[start:position].strip())
            start = position + 1
    raise ValueError(f'unterminated call at {opening}')


def literal(expression: str) -> str | None:
    if re.fullmatch(r'"(?:\\.|[^"\\])*"', expression):
        # These exported C strings contain C escapes; avoid decoding arbitrary
        # symbolic expressions as if they were recovered captions.
        return bytes(expression[1:-1], 'utf-8').decode('unicode_escape')
    return None


def registrations(body: str, apis: dict) -> list[dict]:
    if not apis:
        return []
    pattern = re.compile(r'(?<![\w:])(' + '|'.join(re.escape(name) for name in sorted(apis, key=len, reverse=True)) + r')\s*\(')
    rows = []
    for match in pattern.finditer(body, body.find('{') + 1):
        arguments, end = call_arguments(body, match.end() - 1)
        api = apis[match[1]]
        if not arguments:
            continue
        caption_expression = arguments[-1]
        caption = literal(caption_expression)
        # Every manager/component API ends with (path, caption), except the
        # component-path overload, whose final argument is the caption alone.
        implicit = api.get('component_path', False)
        path_expression = arguments[-2] if implicit is False and len(arguments) >= 2 else None
        rows.append({
            'kind': api['kind'], 'registration_api': match[1],
            'caption': caption, 'caption_expression': caption_expression,
            'path': literal(path_expression) if path_expression is not None else None,
            'path_expression': path_expression, 'uses_component_path': implicit,
            'path_resolution': 'needs-wrapper-export' if implicit is None else 'known-overload',
            'arguments': arguments, 'pseudocode_line': body.count('\n', 0, match.start()) + 1,
            'original_call': re.sub(r'\s+', ' ', body[match.start():end]),
            'caption_resolution': 'literal' if caption is not None else 'needs-evidence',
            'state': 'pending',
        })
    return rows


def build_inventory(export_dir: Path, identity: dict) -> dict:
    cache, missing = {}, set()

    def read(address):
        address = '0x' + address.removeprefix('0x').upper()
        if address not in cache:
            path = export_dir / (address + '.json')
            if not path.is_file():
                missing.add(address)
                return None
            cache[address] = json.loads(path.read_text(encoding='utf-8-sig'))
        return cache[address]

    apis, wrappers = {}, set()
    for address, kind in MANAGERS.items():
        manager = read(address)
        if not manager:
            raise ValueError(f'missing registration manager {address}')
        apis[manager['name']] = {'kind': kind, 'component_path': False}
        for reference in manager.get('xrefs_to', []):
            name = reference['name']
            # Registration overloads are in the original debug-core block.
            # Other callers are user registrations and must remain in inventory.
            in_core = 0x8282D000 <= int(reference['address'], 16) < 0x8282FB00
            is_wrapper = in_core and (name.startswith('sub_') or '::RegisterVariable' in name or '::RegisterFunction' in name)
            if not is_wrapper:
                continue
            wrapper = read(reference['address'])
            pseudocode = wrapper.get('pseudocode') or '' if wrapper else ''
            implicit = '::GetComponentPath(' in pseudocode if wrapper else None
            # Missing wrapper exports remain explicit in metadata. Their callers
            # are still found by the full-corpus search and their raw args retained.
            apis[name] = {'kind': kind, 'component_path': implicit}
            wrappers.add(reference['address'].upper())

    command = ['rg', '-l', '--glob', '0x*.json', '-F']
    for name in apis:
        command.extend(['-e', name])
    command.append(str(export_dir))
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr)
    candidates = sorted(Path(line) for line in result.stdout.splitlines() if line)
    rows, functions, digest = [], [], hashlib.sha256()
    for path in candidates:
        raw = path.read_bytes()
        digest.update(path.name.encode('utf-8') + b'\0' + raw)
        data = json.loads(raw.decode('utf-8-sig'))
        address = str(data['address'])
        if address.upper() in wrappers or address.upper() in {a.upper() for a in MANAGERS}:
            continue
        body = data.get('pseudocode') or ''
        found = registrations(body, apis)
        if not found:
            continue
        name = data['name']
        component = name.rsplit('::', 1)[0]
        component_name, component_path = None, None
        for method, label in (('GetName', 'name'), ('GetPath', 'path')):
            entry = identity.get(component + '::' + method, {})
            addresses = entry.get('x360_addrs', [])
            if addresses:
                original = read(addresses[0])
                returned = re.search(r'\breturn\s+("(?:\\.|[^"\\])*")\s*;', original.get('pseudocode') or '') if original else None
                if returned:
                    if label == 'name':
                        component_name = literal(returned[1])
                    else:
                        component_path = literal(returned[1])
        for ordinal, row in enumerate(found, 1):
            row.update({'id': f'{name}#{ordinal:04d}', 'function': name,
                'original_address': address, 'original_export': f'.ida-exports/{BUILD}/{path.name}',
                'component': component, 'component_name': component_name, 'component_path': component_path})
            rows.append(row)
        functions.append({'name': name, 'address': address, 'registration_sites': len(found)})

    # Include all original activation entry points even when their bodies register
    # nothing directly (delegation, a HUD-only page, missing export or a true no-op).
    activations = []
    for name, entry in sorted(identity.items()):
        if name.endswith('::OnActivate') and 'Debug' in name:
            activations.append({'name': name, 'addresses': entry['x360_addrs'],
                'registration_sites': sum(f['registration_sites'] for f in functions if f['name'] == name),
                'state': 'pending'})
    return {'schema': 1, 'original_build': BUILD, 'source_digest': digest.hexdigest(),
        'scope': 'Static registration call sites, plus every named debug OnActivate. Loop-generated rows and symbolic captions require further enumeration; no behavioral verdict is inferred from registration.',
        'registration_apis': apis, 'missing_exports': sorted(missing),
        'functions': functions, 'activations': activations, 'entries': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exports', type=Path, default=ROOT / '.ida-exports' / BUILD)
    parser.add_argument('--output', type=Path, default=ROOT / 'progress/debug_menu/entries.json')
    parser.add_argument('--verdicts', type=Path, default=ROOT / 'progress/debug_menu/verdicts.json')
    args = parser.parse_args()
    identity = json.loads((ROOT / 'progress/identity.json').read_text(encoding='utf-8-sig'))
    inventory = build_inventory(args.exports, identity)
    verdicts = json.loads(args.verdicts.read_text(encoding='utf-8-sig')) if args.verdicts.is_file() else {}
    by_id = {row['id']: row for row in inventory['entries']}
    unknown = sorted(set(verdicts) - set(by_id))
    if unknown:
        raise ValueError('verdicts refer to missing call sites: ' + ', '.join(unknown))
    for key, verdict in verdicts.items():
        if verdict.get('state') not in ('pending', 'verified', 'original-noop', 'original-broken'):
            raise ValueError(f'invalid state for {key}')
        if verdict.get('state') != 'pending' and (not verdict.get('evidence') or not verdict.get('notes')):
            raise ValueError(f'verdict lacks evidence/notes for {key}')
        by_id[key].update(verdict)
    inventory['summary'] = {'registration_sites': len(by_id),
        'registration_functions': len(inventory['functions']), 'activation_functions': len(inventory['activations']),
        'symbolic_captions': sum(row['caption'] is None for row in by_id.values()),
        'states': dict(Counter(row['state'] for row in by_id.values()))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(inventory['summary'], ensure_ascii=False))
    print('Missing exports:', ', '.join(inventory['missing_exports']) or 'none')
    print('Inventory:', args.output)


if __name__ == '__main__':
    main()
