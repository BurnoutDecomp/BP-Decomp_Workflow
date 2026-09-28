#!/usr/bin/env python3
"""Build native-x64 CSIS descriptors from the original X360 bundle.

Use the existing verified MOIR field schema for every class set, retaining
all ARTIST ids/names. Registry data uses the existing engine graph porter.
No later-release assets or executable code are substituted.
"""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile

import csis_native64_port as schema
import engine_transcode
import vehicle_transcode as bundle


def convert(source, output):
    if bundle.read_bnd2(source)['platform'] != 2:
        raise bundle.PortError('expected X360 CSIS bundle (platform 2)')
    with tempfile.TemporaryDirectory(prefix='csis_x360_') as work:
        root = os.path.join(work, 'source')
        bundle.extract(source, root)
        payloads = {}
        classes = set()
        counts = {'Csis': 0, 'Registry': 0}
        for kind, path in bundle.payload_files(root):
            data = Path(path).read_bytes()
            if kind == 'Registry':
                emitted, _ = engine_transcode.port_payload(kind, data)
            elif kind == 'Csis':
                label = os.path.basename(path)
                body = schema._binary_body(data, '>', 16, label)
                parsed = schema._parse_moir32(body, label)
                if parsed['key'] in classes:
                    raise bundle.PortError('duplicate CSIS class set')
                classes.add(parsed['key'])
                emitted = schema._resource(schema._widen_moir32(body, label))
            else:
                raise bundle.PortError('unattested CSIS resource type: ' + kind)
            counts[kind] += 1
            payloads[(kind, os.path.basename(path))] = emitted
            Path(path).write_bytes(emitted)
        if counts != {'Csis': 11, 'Registry': 33}:
            raise bundle.PortError('incomplete X360 CSIS coverage: %r' % counts)
        bundle.fix_import_sidecars(root)
        bundle.rewrite_meta(root)
        Path(output).resolve().parent.mkdir(parents=True, exist_ok=True)
        bundle.run([bundle.YAP, 'c', root, str(output)])
        bundle.compare_bnd2(source, output, 'CSIS.BUNDLE')
        if bundle.read_bnd2(output)['platform'] != 4:
            raise bundle.PortError('expected native PC container')
        roundtrip = os.path.join(work, 'roundtrip')
        bundle.extract(output, roundtrip)
        actual = {(kind, os.path.basename(path)): Path(path).read_bytes()
                  for kind, path in bundle.payload_files(roundtrip)}
        if actual != payloads:
            raise bundle.PortError('CSIS payloads changed during repack')
        print('ported CSIS.BUNDLE: 33 registries and 11 native-x64 MOIR class sets from X360; sha256 ' +
              hashlib.sha256(Path(output).read_bytes()).hexdigest()[:16])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    convert(args.source, args.output)
