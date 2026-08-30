#!/usr/bin/env python3
"""Repack one X360 AEMS bundle with its matching native-x64 Xbox One bank.

AEMS banks are not ordinary endian-portable data.  Each ABKC image contains AEMS
bytecode plus pointer-width-dependent runtime templates and relocation tables.  The
X360 images therefore contain 32-bit PowerPC-shaped module records and
cannot execute in the reconstructed x64 process.  Burnout Paradise Remastered for
Xbox One ships the same named banks in the native-64 ABKC layout consumed by the only
x64 AEMS loader we can inspect.

This tool deliberately performs a narrow ABI substitution:

* the output container and resource id come from the X360 bundle;
* only the BinaryFileResource body comes from the same-named Xbox One bundle;
* the platform-4 BinaryFileResource prefix is rebuilt, never copied from a captured
  runtime pointer in the retail file;
* both ABKC layouts, version bytes, module counts, and the no-native-function-reloc
  invariant are checked;
* the native-64 module table is walked with its attested 104-byte fixed record;
* the repacked payload must extract byte-identically before the output is accepted.

The Xbox One build is a later content revision, so this is not presented as a pure
X360 endian conversion.  It is the ABI-required native-64 template/data source.  The allow
list contains only the bank names shared by the two releases.  CSIS has its own strict
converter and EXPLOSIONS_PATCHBANK has no native-x64 counterpart, so neither can pass
through this tool.

Usage:
  py aems_native64_port.py <x360 bank.bundle> <pc output.bundle>
      [--xb1-root <Xbox One game folder>]

The build driver exports [inputs].xb1_root as BRN_XB1_ROOT.
"""

import argparse
import hashlib
import os
import shutil
import struct
import sys
import tempfile

import vehicle_transcode as bundle


SUPPORTED_BANKS = {
    'BOOST_BANK_EXOTIC.BUNDLE',
    'BOOST_BANK_SEDAN.BUNDLE',
    'BOOST_BANK_SUPER.BUNDLE',
    'BOOST_BANK_TRUCK.BUNDLE',
    'BOOST_BANK_TUNER.BUNDLE',
    'BOOST_PATCH_BANK.BUNDLE',
    'CRUMPLEPATCHBANK.BUNDLE',
    'GEARWHINEPATCHBANK.BUNDLE',
    'INAIR.BUNDLE',
    'PATCH_BANK_HORNS.BUNDLE',
    'SCRAPEPATCHBANK.BUNDLE',
    'SKIDS.BUNDLE',
    'SUPRAAKTURBOPATCHBANK.BUNDLE',
    'SURFACE_PATCH_BANK.BUNDLE',
    'TRAFFIC_BANK.BUNDLE',
}

# Retail 1.0.0.5 carries the native-64 revision of these two banks.  Their
# ABKC revision byte advanced from 1 to 2; SKIDS also consolidated its two X360
# bytecode modules into one.  The replacement remains same-name and is still
# guarded by all native-layout/relocation checks below.
NATIVE64_REVISIONS = {
    'SKIDS.BUNDLE': (2, 1),
    'SURFACE_PATCH_BANK.BUNDLE': (2, 1),
}

BINFILE_HEAD = 16
ABKC_HEAD64 = 0x78
MODULE_FIXED64 = 104


class PortError(bundle.PortError):
    pass


def _u16(data, offset, endian):
    return int.from_bytes(data[offset:offset + 2], endian)


def _u32(data, offset, endian):
    return int.from_bytes(data[offset:offset + 4], endian)


def _binary_body(data, endian, label):
    if len(data) < BINFILE_HEAD:
        raise PortError('%s: %d bytes, shorter than BinaryFileResource prefix' %
                        (label, len(data)))
    size = _u32(data, 0, endian)
    offset = _u32(data, 4, endian)
    if offset != BINFILE_HEAD or size + offset != len(data):
        raise PortError('%s: BinaryFileResource size/offset %d/%d do not describe %d bytes' %
                        (label, size, offset, len(data)))
    return data[offset:]


def _validate_x360(body, label):
    if len(body) < 0x50 or body[:4] != b'ABKC':
        raise PortError('%s: missing complete ABKC image' % label)
    if body[8] != 5:
        raise PortError('%s: ABKC layout marker %#x, expected 0x05 (32-bit X360)' %
                        (label, body[8]))
    total = _u32(body, 0x14, 'big')
    modules = _u16(body, 0x0A, 'big')
    module_offset = _u32(body, 0x1C, 'big')
    # Some retail X360 banks pad the BinaryFileResource payload to its 16-byte
    # allocation alignment.  ABKC's own total deliberately stops before that
    # zero-filled tail (SKIDS and SURFACE_PATCH_BANK carry eight bytes).  Treat
    # only a short all-zero alignment tail as outside the ABKC image; any real
    # size disagreement remains an error.
    tail = body[total:] if total <= len(body) else b''
    if total > len(body) or len(tail) >= 16 or any(tail):
        raise PortError('%s: ABKC total size %d does not describe body size %d' %
                        (label, total, len(body)))
    if modules == 0 or module_offset < 0x50 or module_offset >= len(body):
        raise PortError('%s: invalid X360 module count/offset %d/%#x' %
                        (label, modules, module_offset))
    return modules


def _validate_native64(body, label):
    if len(body) < ABKC_HEAD64 or body[:4] != b'ABKC':
        raise PortError('%s: missing complete native-64 ABKC image' % label)
    if body[8] != 10:
        raise PortError('%s: ABKC layout marker %#x, expected 0x0A (native 64-bit)' %
                        (label, body[8]))

    module_count = _u16(body, 0x0A, 'little')
    total_size = _u32(body, 0x14, 'little')
    resident_size = _u32(body, 0x18, 'little')
    module_offset = _u32(body, 0x1C, 'little')
    sample_offset = _u32(body, 0x20, 'little')
    sample_size = _u32(body, 0x24, 'little')
    function_reloc = _u32(body, 0x30, 'little')
    pointer_reloc = _u32(body, 0x34, 'little')
    csis_reloc = _u32(body, 0x38, 'little')

    tail = body[total_size:] if total_size <= len(body) else b''
    if total_size > len(body) or len(tail) >= 16 or any(tail):
        raise PortError('%s: native-64 total size %d does not describe body size %d' %
                        (label, total_size, len(body)))
    if module_count == 0:
        raise PortError('%s: native-64 bank has no modules' % label)
    if not (ABKC_HEAD64 <= module_offset < resident_size <= len(body)):
        raise PortError('%s: native-64 module/resident bounds are %#x/%#x/%#x' %
                        (label, module_offset, resident_size, len(body)))
    if sample_offset < resident_size or sample_offset + sample_size > len(body):
        raise PortError('%s: native-64 sample span %#x+%#x is invalid' %
                        (label, sample_offset, sample_size))
    if not (sample_offset + sample_size <= function_reloc <= pointer_reloc <=
            csis_reloc <= len(body)):
        raise PortError('%s: native-64 relocation offsets are not monotonic/in bounds' % label)
    function_count = _u32(body, function_reloc, 'little')
    if function_reloc + 4 + 4 * function_count > pointer_reloc:
        raise PortError('%s: native-64 function relocation table overruns its span' % label)
    if function_count:
        raise PortError('%s: native-64 bank contains %d native function relocations; '
                        'only AEMS bytecode banks are supported' %
                        (label, function_count))

    cursor = module_offset
    for index in range(module_count):
        if cursor + MODULE_FIXED64 > resident_size:
            raise PortError('%s: module %d fixed record overruns resident image' %
                            (label, index))
        pointer_count = body[cursor + 0x40]
        alternate_count = body[cursor + 0x43]
        stride = MODULE_FIXED64 + 4 * (pointer_count + alternate_count)
        if cursor + stride > resident_size:
            raise PortError('%s: module %d stride %#x overruns resident image' %
                            (label, index, stride))
        cursor += stride

    return module_count


def _one_aems_payload(root, label):
    files = bundle.payload_files(root)
    if len(files) != 1 or files[0][0] != 'AemsBank':
        shape = [(kind, os.path.basename(path)) for kind, path in files]
        raise PortError('%s: expected exactly one AemsBank resource, found %r' %
                        (label, shape))
    path = files[0][1]
    with open(path, 'rb') as fh:
        return path, fh.read()


def _resolve_xb1_bank(source, xb1_root):
    name = os.path.basename(source).upper()
    if name not in SUPPORTED_BANKS:
        if name == 'EXPLOSIONS_PATCHBANK.BUNDLE':
            raise PortError('%s has no Xbox One native-x64 counterpart' % name)
        raise PortError('%s is not in the attested shared-bank allow list' % name)
    root = xb1_root or os.environ.get('BRN_XB1_ROOT')
    if not root:
        raise PortError('Xbox One data root is not configured; set [inputs].xb1_root in '
                        'build.config.toml or BRN_XB1_ROOT')
    candidate = os.path.join(os.path.abspath(root), 'SOUND', 'AEMS', name)
    if not os.path.isfile(candidate):
        raise PortError('matching native-x64 AEMS bank is missing: %s' % candidate)
    return name, candidate


def convert(source, output, xb1_root=None):
    name, native_source = _resolve_xb1_bank(source, xb1_root)
    source_info = bundle.read_bnd2(source)
    native_info = bundle.read_bnd2(native_source)
    if source_info['platform'] != 2:
        raise PortError('%s: source platform %d, expected X360 platform 2' %
                        (source, source_info['platform']))
    if native_info['platform'] != 1:
        raise PortError('%s: native source platform %d, expected Xbox One retail marker 1' %
                        (native_source, native_info['platform']))

    work = tempfile.mkdtemp(prefix='aems64_')
    try:
        x360_root = os.path.join(work, 'x360')
        native_root = os.path.join(work, 'native64')
        bundle.extract(source, x360_root)
        bundle.extract(native_source, native_root)
        x360_path, x360_resource = _one_aems_payload(x360_root, 'X360 ' + name)
        _native_path, native_resource = _one_aems_payload(native_root, 'Xbox One ' + name)

        x360_body = _binary_body(x360_resource, 'big', 'X360 ' + name)
        native_body = _binary_body(native_resource, 'little', 'Xbox One ' + name)
        x360_modules = _validate_x360(x360_body, 'X360 ' + name)
        native_modules = _validate_native64(native_body, 'Xbox One ' + name)
        revision = NATIVE64_REVISIONS.get(name)
        same_family = (x360_body[:7] == native_body[:7] and
                       x360_body[9] == native_body[9])
        expected_revision = revision and native_body[7] == revision[0]
        if not same_family or (x360_body[7] != native_body[7] and
                               not expected_revision):
            raise PortError('%s: ABKC version family differs between releases' % name)
        expected_modules = revision and native_modules == revision[1]
        if x360_modules != native_modules and not expected_modules:
            raise PortError('%s: module count changed X360 %d -> Xbox One %d' %
                            (name, x360_modules, native_modules))

        # BinaryFileResource is two u32 fields on the reconstructed target.  Keep
        # its 16-byte serialized payload alignment but zero the trailing bytes:
        # the Xbox One bundle's +8 lane can contain a captured runtime pointer.
        ported_resource = (struct.pack('<II', len(native_body), BINFILE_HEAD) +
                           b'\0' * 8 + native_body)
        with open(x360_path, 'wb') as fh:
            fh.write(ported_resource)

        bundle.fix_import_sidecars(x360_root)
        bundle.rewrite_meta(x360_root)
        out_dir = os.path.dirname(os.path.abspath(output))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        bundle.run([bundle.YAP, 'c', x360_root, output])

        bundle.compare_bnd2(source, output, name)
        emitted = bundle.read_bnd2(output)
        if emitted['platform'] != 4:
            raise PortError('%s: emitted platform %d, expected 4' %
                            (output, emitted['platform']))
        roundtrip_root = os.path.join(work, 'roundtrip')
        bundle.extract(output, roundtrip_root)
        _roundtrip_path, roundtrip_resource = _one_aems_payload(roundtrip_root,
                                                                 'roundtrip ' + name)
        if roundtrip_resource != ported_resource:
            raise PortError('%s: native-64 payload changed during platform-4 repack' % name)

        digest = hashlib.sha256(native_body).hexdigest()[:16]
        print('ported %s: X360 identity + Xbox One native64 body, %d modules, '
              '%d -> %d bytes, sha256 %s' %
              (name, native_modules, len(x360_body), len(native_body), digest))
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
