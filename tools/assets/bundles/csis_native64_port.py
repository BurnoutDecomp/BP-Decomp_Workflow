#!/usr/bin/env python3
"""Build the Phase-F CSIS bundle with native-x64 MOIR resources.

The X360 CSIS bundle mixes ordinary Registry resources with CSIS MOIR images.
Registry is serialized engine data and is rebuilt from the X360 source.  MOIR is
different: its records contain native pointer-width slots, so the 32-bit image is
not executable in the x64 game.  For the ten class sets shared with the Xbox One
release this tool imports the matching native-64 body, while retaining the X360
bundle/resource identity.  The sole X360-only class set (detonation/tendril) is a
data-only descriptor with no corresponding Xbox One AEMS bank; it is widened by a
small, fully walked MOIR schema instead of being passed through as 32-bit data.

Every Registry is delegated to engine_transcode's strict native-x64 porter.  All
MOIR headers, counts, entries, name offsets, ids, and string terminators are
validated, and the emitted platform-4 payloads must survive a byte-exact extract
round trip.

Usage:
  py csis_native64_port.py <X360 CSIS.BUNDLE> <PC CSIS.BUNDLE>
      [--xb1-root <Xbox One game folder>]
"""

import argparse
import hashlib
import os
import shutil
import struct
import tempfile

import engine_transcode
import vehicle_transcode as bundle


BINFILE32_HEAD = 16
BINFILE_XB1_HEAD = 8
MOIR32_HEAD = 0x28
MOIR64_HEAD = 0x40
MOIR32_ENTRY = 12
MOIR64_ENTRY = 24
X360_ONLY_KEYS = {('detonation', 'tendril')}


class PortError(bundle.PortError):
    pass


def _binary_body(data, endian, prefix, label, trailing=(0,)):
    if len(data) < prefix:
        raise PortError('%s: shorter than its BinaryFileResource prefix' % label)
    size, offset = struct.unpack_from(endian + 'II', data, 0)
    extra = len(data) - (size + offset)
    if offset != prefix or extra not in trailing:
        raise PortError('%s: BinaryFileResource size/offset %d/%d do not describe %d bytes'
                        % (label, size, offset, len(data)))
    if extra and any(data[offset + size:]):
        raise PortError('%s: nonzero native runtime-pointer trailer' % label)
    return data[offset:offset + size]


def _cstring(data, offset, label):
    if offset < 0 or offset >= len(data):
        raise PortError('%s: name offset %#x is out of bounds' % (label, offset))
    end = data.find(b'\0', offset)
    if end < 0:
        raise PortError('%s: unterminated name at %#x' % (label, offset))
    try:
        return data[offset:end].decode('ascii')
    except UnicodeDecodeError:
        raise PortError('%s: non-ASCII name at %#x' % (label, offset))


def _parse_moir32(body, label):
    if len(body) < MOIR32_HEAD or body[:4] != b'MOIR' or body[8] != 5:
        raise PortError('%s: not a complete 32-bit MOIR image' % label)
    count_a = struct.unpack_from('>H', body, 0x0A)[0]
    count_b = struct.unpack_from('>H', body, 0x0C)[0]
    system_id = struct.unpack_from('>H', body, 0x10)[0]
    count = count_a + count_b
    strings = MOIR32_HEAD + MOIR32_ENTRY * count
    if count == 0 or strings > len(body):
        raise PortError('%s: invalid MOIR entry counts %d+%d' % (label, count_a, count_b))
    if any(body[0x12:MOIR32_HEAD]):
        raise PortError('%s: unknown nonzero 32-bit MOIR header lanes' % label)

    entries = []
    for index in range(count):
        cursor = MOIR32_HEAD + MOIR32_ENTRY * index
        runtime, name_offset = struct.unpack_from('>II', body, cursor)
        interface_id, pad = struct.unpack_from('>HH', body, cursor + 8)
        if runtime != 0 or pad != 0 or name_offset < strings:
            raise PortError('%s: malformed 32-bit entry %d' % (label, index))
        entries.append((name_offset, interface_id,
                        _cstring(body, name_offset, label)))
    return {
        'version': body[4:8], 'flags': body[9], 'count_a': count_a,
        'count_b': count_b, 'system_id': system_id, 'entries': entries,
        'key': tuple(item[2] for item in entries),
    }


def _parse_moir64(body, label):
    if len(body) < MOIR64_HEAD or body[:4] != b'MOIR' or body[8] != 7:
        raise PortError('%s: not a complete native-64 MOIR image' % label)
    count_a = struct.unpack_from('<H', body, 0x0A)[0]
    count_b = struct.unpack_from('<H', body, 0x0C)[0]
    system_id = struct.unpack_from('<H', body, 0x10)[0]
    count = count_a + count_b
    strings = MOIR64_HEAD + MOIR64_ENTRY * count
    if count == 0 or strings > len(body) or len(body) & 7:
        raise PortError('%s: invalid native-64 MOIR counts/size' % label)
    if any(body[0x12:MOIR64_HEAD]):
        raise PortError('%s: unknown nonzero native-64 MOIR header lanes' % label)

    entries = []
    for index in range(count):
        cursor = MOIR64_HEAD + MOIR64_ENTRY * index
        runtime, name_offset = struct.unpack_from('<QQ', body, cursor)
        interface_id = struct.unpack_from('<H', body, cursor + 16)[0]
        if runtime != 0 or any(body[cursor + 18:cursor + 24]) or name_offset < strings:
            raise PortError('%s: malformed native-64 entry %d' % (label, index))
        entries.append((name_offset, interface_id,
                        _cstring(body, name_offset, label)))
    return {
        'version': body[4:8], 'flags': body[9], 'count_a': count_a,
        'count_b': count_b, 'system_id': system_id, 'entries': entries,
        'key': tuple(item[2] for item in entries),
    }


def _widen_moir32(body, label):
    source = _parse_moir32(body, label)
    count = len(source['entries'])
    string_start = MOIR64_HEAD + MOIR64_ENTRY * count
    names = [item[2].encode('ascii') + b'\0' for item in source['entries']]
    total = string_start + sum(len(name) for name in names)
    total = (total + 7) & ~7
    out = bytearray(total)
    out[:4] = b'MOIR'
    out[4:8] = source['version']
    out[8] = 7
    out[9] = source['flags']
    struct.pack_into('<H', out, 0x0A, source['count_a'])
    struct.pack_into('<H', out, 0x0C, source['count_b'])
    struct.pack_into('<H', out, 0x10, source['system_id'])

    name_cursor = string_start
    for index, ((unused_offset, interface_id, unused_name), encoded) in enumerate(
            zip(source['entries'], names)):
        del unused_offset, unused_name
        cursor = MOIR64_HEAD + MOIR64_ENTRY * index
        struct.pack_into('<Q', out, cursor + 8, name_cursor)
        struct.pack_into('<H', out, cursor + 16, interface_id)
        out[name_cursor:name_cursor + len(encoded)] = encoded
        name_cursor += len(encoded)

    emitted = _parse_moir64(bytes(out), label + ' widened')
    if (emitted['key'] != source['key'] or emitted['count_a'] != source['count_a'] or
            emitted['count_b'] != source['count_b'] or
            emitted['system_id'] != source['system_id'] or
            [x[1] for x in emitted['entries']] !=
            [x[1] for x in source['entries']]):
        raise PortError('%s: semantic mismatch after native-64 widening' % label)
    return bytes(out)


def _resource(body):
    return struct.pack('<II', len(body), BINFILE32_HEAD) + b'\0' * 8 + body


def _payload_map(root, expected_type, label):
    result = {}
    for kind, path in bundle.payload_files(root):
        if kind != expected_type:
            continue
        with open(path, 'rb') as stream:
            result[os.path.basename(path)] = (path, stream.read())
    if not result:
        raise PortError('%s: no %s resources' % (label, expected_type))
    return result


def _native_moir_by_key(root):
    result = {}
    for filename, (path, resource) in _payload_map(root, 'Csis', 'Xbox One CSIS').items():
        body = _binary_body(resource, '<', BINFILE_XB1_HEAD,
                            'Xbox One Csis/' + filename, trailing=(0, 8))
        parsed = _parse_moir64(body, 'Xbox One Csis/' + filename)
        if parsed['key'] in result:
            raise PortError('duplicate Xbox One MOIR semantic key %r' % (parsed['key'],))
        result[parsed['key']] = body
    return result


def _resolve_native_bundle(xb1_root):
    root = xb1_root or os.environ.get('BRN_XB1_ROOT')
    if not root:
        raise PortError('Xbox One data root is not configured; set [inputs].xb1_root in '
                        'build.config.toml or BRN_XB1_ROOT')
    path = os.path.join(os.path.abspath(root), 'SOUND', 'AEMS', 'CSIS.BUNDLE')
    if not os.path.isfile(path):
        raise PortError('Xbox One native CSIS bundle is missing: %s' % path)
    return path


def convert(source, output, xb1_root=None):
    native_source = _resolve_native_bundle(xb1_root)
    source_info = bundle.read_bnd2(source)
    native_info = bundle.read_bnd2(native_source)
    if source_info['platform'] != 2 or native_info['platform'] != 1:
        raise PortError('expected X360 platform 2 and Xbox One platform 1 CSIS bundles')

    work = tempfile.mkdtemp(prefix='csis64_')
    try:
        x360_root = os.path.join(work, 'x360')
        native_root = os.path.join(work, 'native64')
        bundle.extract(source, x360_root)
        bundle.extract(native_source, native_root)
        native_by_key = _native_moir_by_key(native_root)

        source_keys = set()
        imported = 0
        widened = 0
        expected_payloads = {}
        for kind, path in bundle.payload_files(x360_root):
            with open(path, 'rb') as stream:
                data = stream.read()
            if kind == 'Registry':
                ported, unused_info = engine_transcode.port_payload(kind, data)
                del unused_info
            elif kind == 'Csis':
                source_body = _binary_body(data, '>', BINFILE32_HEAD,
                                           'X360 ' + os.path.basename(path))
                parsed = _parse_moir32(source_body, 'X360 ' + os.path.basename(path))
                key = parsed['key']
                source_keys.add(key)
                if key in native_by_key:
                    ported = _resource(native_by_key[key])
                    imported += 1
                elif key in X360_ONLY_KEYS:
                    ported = _resource(_widen_moir32(source_body, 'X360-only %r' % (key,)))
                    widened += 1
                else:
                    raise PortError('no native-x64 CSIS body for X360 semantic key %r' % (key,))
            else:
                raise PortError('unexpected CSIS bundle resource type %r' % kind)
            with open(path, 'wb') as stream:
                stream.write(ported)
            expected_payloads[(kind, os.path.basename(path))] = ported

        common = source_keys - X360_ONLY_KEYS
        if common != set(native_by_key) or imported != 10 or widened != 1:
            raise PortError('CSIS coverage mismatch: common=%d native=%d imported=%d widened=%d'
                            % (len(common), len(native_by_key), imported, widened))

        bundle.fix_import_sidecars(x360_root)
        bundle.rewrite_meta(x360_root)
        out_dir = os.path.dirname(os.path.abspath(output))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        bundle.run([bundle.YAP, 'c', x360_root, output])
        bundle.compare_bnd2(source, output, 'CSIS.BUNDLE')

        roundtrip = os.path.join(work, 'roundtrip')
        bundle.extract(output, roundtrip)
        actual = {}
        for kind, path in bundle.payload_files(roundtrip):
            with open(path, 'rb') as stream:
                actual[(kind, os.path.basename(path))] = stream.read()
        if actual != expected_payloads:
            raise PortError('CSIS payloads changed during platform-4 repack')

        digest = hashlib.sha256(open(output, 'rb').read()).hexdigest()[:16]
        print('ported CSIS.BUNDLE: 33 X360 registries, %d Xbox One native64 MOIR, '
              '%d schema-widened X360-only MOIR, sha256 %s'
              % (imported, widened, digest))
        print('OK:', output)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--xb1-root')
    args = parser.parse_args(argv)
    convert(args.source, args.output, args.xb1_root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
