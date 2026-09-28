#!/usr/bin/env python3
"""Port original X360 AEMS bytecode banks to the native x64 ABI.

ARTIST resolvemodulebank/CreateModuleInstance (82B717C8/82B71408) define
the input. XB1 14096C510/14096C290 and its unchanged INAIR, crumple and
scrape graphs pin the output ABI. Rebuild records, bytecode displacements,
templates and relocations; retain the original S10A/EAAC samples verbatim.
Unknown opcodes, native machine code and unaccounted nonzero data fail closed.
"""
import argparse
import hashlib
import os
from pathlib import Path
import struct
import tempfile

import vehicle_transcode as bundle
import aems_native64_port as native

PortError = bundle.PortError


def require(condition, message):
    if not condition:
        raise PortError(message)


def number(data, offset, width=4):
    require(0 <= offset <= len(data) - width, 'integer outside image')
    return int.from_bytes(data[offset:offset + width], 'big')


def align(value, boundary):
    return (value + boundary - 1) & -boundary


class Record:
    """A field-level endian/width rewrite, also mapping addressable fields."""
    def __init__(self, data):
        self.data = data
        self.out = bytearray()
        self.mapping = {}
        self.covered = bytearray(len(data))

    def field(self, offset, size, width=None, raw=False):
        require(0 <= offset <= len(self.data) - size, 'field outside record')
        require(not any(self.covered[offset:offset + size]), 'overlapping fields')
        new = len(self.out)
        self.mapping.update((offset + i, new + i) for i in range(size))
        self.covered[offset:offset + size] = b'\1' * size
        value = self.data[offset:offset + size]
        self.out += value if raw else int.from_bytes(value, 'big').to_bytes(width or size, 'little')

    def words(self, start, end):
        require((end - start) % 4 == 0, 'non-word numeric tail')
        for offset in range(start, end, 4):
            self.field(offset, 4)

    def pad(self, boundary):
        self.out += b'\0' * (align(len(self.out), boundary) - len(self.out))

    def finish(self):
        require(all(self.covered), 'unwalked record fields')
        self.pad(8)
        return self


def port_block(op, data):
    r = Record(data)
    size = len(data)
    exact = {0: 20, 3: 4, 4: 16, 6: 24, 7: 16, 10: 24, 11: 16,
             15: 16, 23: 8, 24: 8, 25: 8, 28: 16, 29: 28,
             31: 12, 33: 8, 34: 8, 35: 12, 36: 8}
    if op in exact:
        require(size == exact[op], 'opcode %d has unexpected size %d' % (op, size))
    if op in (0, 1, 4):
        pointers = 3 if op == 4 else 4
        for p in range(pointers):
            require(number(data, p * 4) == 0, 'serialized live client pointer')
            r.field(p * 4, 4, 8)
        if op == 1:
            require(size == 20 + 4 * data[16], 'class parameter count/size mismatch')
            r.field(16, 4, raw=True)
            r.pad(8)
            r.words(20, size)
        else:
            r.words(pointers * 4, size)
    elif op == 15:
        r.field(0, 4, 8)
        r.words(4, size)
    elif op == 27:
        require(size >= 28, 'short sample player')
        require(number(data, 0) == number(data, 8) == 0, 'serialized live sample player')
        expected = 28 + 12 * data[14] + (8 if data[15] else 0) + (32 if data[17] else 0)
        require(size == expected, 'sample player count/size mismatch: %d != %d' % (size, expected))
        for p in range(3):
            r.field(4 * p, 4, 8)
        r.field(12, 8, raw=True)
        r.words(20, 28)
        for p in range(data[14]):
            pos = 28 + 12 * p
            r.field(pos, 4, raw=True)
            r.words(pos + 4, pos + 12)
        r.words(28 + 12 * data[14], size)
    elif op == 8:
        trigger = number(data, 0, 2)
        width = data[2]
        require(width in (1, 2) and 16 <= trigger == size - 4, 'shuffle array bounds')
        r.field(0, 2)
        r.field(2, 2, raw=True)
        r.field(4, 4)
        r.field(8, 2)
        r.field(10, 2)
        r.field(12, 4)
        for p in range(16, trigger, width):
            r.field(p, width)
        r.field(trigger, 4)
    elif op == 10:
        r.words(0, 16)
        r.field(16, 4, raw=True)
        r.words(20, size)
    elif op in (12, 16):
        for p in range(0, 8, 2):
            r.field(p, 2)
        r.words(8, size)
        control = number(data, 0, 2)
        require(control % 4 == 0 and 8 <= control <= size - (8 if op == 16 else 4), 'internal control offset')
    elif op == 14:
        require(size >= 24, 'short envelope')
        r.field(0, 2)
        r.field(2, 2, raw=True)
        r.words(4, 16)
        r.field(16, 2, raw=True)
        r.field(18, 2)
        r.words(20, size)
        control = number(data, 0, 2)
        require(control % 4 == 0 and 20 <= control <= size - 4, 'envelope control offset')
    elif op == 18:
        r.field(0, 2, raw=True)
        r.field(2, 2)
        r.words(4, size)
    elif op in (13, 17, 20, 21, 22, 28):
        r.field(0, 4, raw=True)
        r.words(4, size)
    elif op in (3, 6, 7, 11, 23, 24, 25, 29, 31, 33, 34, 35, 36):
        r.words(0, size)
    else:
        raise PortError('unattested opcode %d' % op)
    return r.finish()


class Bank:
    def __init__(self, data, label):
        self.data = data
        self.label = label
        self.covered = bytearray(len(data))
        self.out = bytearray(0x78)
        self.mapping = {}
        self.modules = []
        self.pointer_sites = {}

    def mark(self, pos, size):
        require(0 <= pos <= len(self.data) - size, 'span outside bank')
        self.covered[pos:pos + size] = b'\1' * size

    def append(self, data, alignment=4):
        self.out += b'\0' * (align(len(self.out), alignment) - len(self.out))
        pos = len(self.out)
        self.out += data
        return pos

    def zero(self, start, end):
        require(not any(self.data[start:end]), 'nonzero reserved data at %#x' % start)
        self.mark(start, end - start)

    def port(self):
        b = self.data
        u = lambda p: number(b, p)
        h = lambda p: number(b, p, 2)
        count = native._validate_x360(b, self.label)
        require(u(0x1c) == 0x5c, 'unattested module header size')
        require(u(0x20) == u(0x18) and u(0x20) + u(0x24) <= u(0x30), 'sample/resident bounds')
        require(u(u(0x30)) == 0, 'native machine-code bank is unsupported')
        self.zero(0xc, 0x14)
        self.zero(0x28, 0x30)
        require(u(0x3c) == 0 and u(0x40) == u(0x44) == 0xffffffff, 'bank runtime sentinels')
        self.zero(0x48, 0x5c)
        self.mark(0, 0x5c)
        self.out[:10] = b[:10]
        self.out[8] = 10
        struct.pack_into('<H', self.out, 0xa, count)
        struct.pack_into('<I', self.out, 0x1c, 0x78)
        struct.pack_into('<i', self.out, 0x48, -1)

        cursor = u(0x1c)
        for i in range(count):
            self.zero(cursor + 4, cursor + 0x1c)
            current, maximum, globals_, functions = struct.unpack_from('>4H', b, cursor + 0x1c)
            players, destructor, classdata, alternate = b[cursor + 0x24:cursor + 0x28]
            require(current == globals_ == functions == alternate == 0, 'unsupported module record extension')
            require(destructor <= 1 and classdata <= 1 and u(cursor + 0x38) == 0, 'module runtime fields')
            rec = bytearray(0x68 + 4 * players)
            struct.pack_into('<I', rec, 0, u(cursor))
            struct.pack_into('<4H', rec, 0x38, current, maximum, globals_, functions)
            rec[0x40:0x44] = bytes((players, destructor, classdata, alternate))
            dest = self.append(rec, 4)
            self.mapping[cursor + 4] = dest + 8
            self.mark(cursor, 0x3c + 4 * players)
            self.modules.append(dict(old=cursor, new=dest, program=u(cursor + 0x28),
                                     template=u(cursor + 0x2c), size=u(cursor + 0x30),
                                     destroy=u(cursor + 0x34), players=players, nodes=[]))
            cursor += 0x3c + 4 * players

        for m in self.modules:
            pc = m['program']
            oldpos = 24
            template = bytearray(48)
            offsets = {}
            self.zero(m['template'], m['template'] + 24)
            while True:
                require(pc < u(0x18), 'program outside resident bank')
                if b[pc] == 0xff:
                    self.zero(pc + 1, pc + 4)
                    self.mark(pc, 4)
                    break
                op, assignments = b[pc:pc + 2]
                self.zero(pc + 2, pc + 4)
                pairs = [struct.unpack_from('>ii', b, pc + 4 + 8 * j) for j in range(assignments)]
                length = 8 + assignments * 8
                delta = u(pc + length - 4)
                require(delta > 0 and oldpos + delta <= m['size'], 'template displacement outside instance')
                start = m['template'] + oldpos
                block = port_block(op, b[start:start + delta])
                newpos = len(template)
                offsets.update((oldpos + a, newpos + c) for a, c in block.mapping.items())
                m['nodes'].append((op, pairs, oldpos, newpos, len(block.out)))
                template += block.out
                self.mark(start, delta)
                self.mark(pc, length)
                if op in (15, 27):
                    p = 0 if op == 15 else 4
                    self.pointer_sites[start + p] = (op, number(b, start + p))
                oldpos += delta
                pc += length
            require(oldpos == m['size'], 'unwalked instance tail')
            program = bytearray()
            for op, pairs, oldpos, newpos, newsize in m['nodes']:
                program += bytes((op, len(pairs), 0, 0))
                for src, dst in pairs:
                    require(oldpos + dst in offsets and (src == -1 or oldpos + src in offsets), 'assignment outside mapped fields')
                    newsrc = -1 if src == -1 else offsets[oldpos + src] - newpos
                    struct_src = struct.pack('<ii', newsrc, offsets[oldpos + dst] - newpos)
                    program += struct_src
                program += struct.pack('<I', newsize)
            program += b'\xff\0\0\0'
            newprogram = self.append(program)
            newtemplate = self.append(template, 8)
            self.mapping.update((m['template'] + a, newtemplate + c) for a, c in offsets.items())
            struct.pack_into('<QQIi', self.out, m['new'] + 0x48, newprogram, newtemplate,
                             len(template), offsets[m['destroy']])
            expected_players = [p for op, _, p, _, _ in m['nodes'] if op == 27]
            source_players = [u(m['old'] + 0x3c + 4 * i) for i in range(m['players'])]
            require(source_players == expected_players, 'module player table differs from graph')
            for i, old in enumerate(source_players):
                struct.pack_into('<I', self.out, m['new'] + 0x68 + 4 * i, offsets[old])

        external = {}
        for site, (kind, target) in sorted(self.pointer_sites.items()):
            if target not in external:
                if kind == 15:
                    width, elements = b[target], number(b, target + 2, 2)
                    require(width in (1, 2, 4), 'table element width')
                    r = Record(b[target:target + 16 + width * elements])
                    r.field(0, 2, raw=True)
                    r.field(2, 2)
                    r.words(4, 16)
                    for j in range(elements):
                        r.field(16 + width * j, width)
                else:
                    elements = u(target)
                    require(elements > 0, 'empty sample selection table')
                    r = Record(b[target:target + 4 + 12 * elements])
                    r.field(0, 4)
                    for j in range(elements):
                        pos = 4 + 12 * j
                        r.field(pos, 2)
                        r.field(pos + 2, 6, raw=True)
                        r.field(pos + 8, 4)
                self.mark(target, len(r.data))
                external[target] = (kind, self.append(r.finish().out, 8))
            require(external[target][0] == kind, 'conflicting external table types')
            struct.pack_into('<Q', self.out, self.mapping[site], external[target][1])
        resident = align(len(self.out), 128)
        self.out += b'\0' * (resident - len(self.out))
        samples = b[u(0x20):u(0x20) + u(0x24)]
        require(samples[:4] == b'S10A', 'unrecognized sample bank')
        self.mark(u(0x20), len(samples))
        samplepos = self.append(samples, 1)
        require(samplepos == resident, 'resident/sample gap')
        funcpos = self.append(struct.pack('<I', 0))
        self.mark(u(0x30), 4)
        ptrs = [u(u(0x34) + 4 + 4 * i) for i in range(u(u(0x34)))]
        require(len(set(ptrs)) == len(ptrs) and set(ptrs) == set(self.pointer_sites), 'unaccounted pointer relocations')
        ptrpos = self.append(struct.pack('<I', len(ptrs)) + b''.join(struct.pack('<I', self.mapping[p]) for p in ptrs))
        self.mark(u(0x34), 4 + 4 * len(ptrs))
        count_csis = u(u(0x38))
        require(count_csis == count, 'unattested CSIS relocation count')
        csispos = self.append(bytearray(4 + 12 * count_csis))
        struct.pack_into('<I', self.out, csispos, count_csis)
        self.mark(u(0x38), 4 + 12 * count_csis)
        for i in range(count_csis):
            site = u(0x38) + 4 + 12 * i
            target, name = u(site), u(site + 4)
            require(target == self.modules[i]['old'] + 4 and b[site + 8] == 1, 'non-class CSIS relocation')
            end = b.find(b'\0', name + 4)
            require(name >= u(0x38) + 4 + 12 * count_csis and end >= name + 4, 'invalid CSIS id/name')
            iddata = struct.pack('<HH', h(name), h(name + 2)) + b[name + 4:end + 1]
            idpos = self.append(iddata)
            self.mark(name, end + 1 - name)
            struct.pack_into('<IIB', self.out, csispos + 4 + 12 * i, self.mapping[target], idpos, 1)
            self.out[csispos + 13 + 12 * i:csispos + 16 + 12 * i] = b[site + 9:site + 12]
        self.out += b'\0' * (align(len(self.out), 16) - len(self.out))
        for p, value in enumerate(b):
            require(self.covered[p] or value == 0, 'unaccounted nonzero bank data at %#x' % p)
        for pos, val in ((0x14, len(self.out)), (0x18, resident), (0x20, resident),
                         (0x24, len(samples)), (0x30, funcpos), (0x34, ptrpos), (0x38, csispos)):
            struct.pack_into('<I', self.out, pos, val)
        native._validate_native64(self.out, self.label + ' converted')
        return bytes(self.out)


def port_body(body, label='AEMS'):
    return Bank(body, label).port()


def convert(source, output):
    require(bundle.read_bnd2(source)['platform'] == 2, 'expected X360 platform 2')
    with tempfile.TemporaryDirectory(prefix='aems_x360_') as work:
        root = os.path.join(work, 'source')
        bundle.extract(source, root)
        path, resource = native._one_aems_payload(root, source)
        body = native._binary_body(resource, 'big', source)
        emitted = port_body(body, source)
        payload = struct.pack('<II', len(emitted), 16) + b'\0' * 8 + emitted
        Path(path).write_bytes(payload)
        bundle.fix_import_sidecars(root)
        bundle.rewrite_meta(root)
        Path(output).resolve().parent.mkdir(parents=True, exist_ok=True)
        bundle.run([bundle.YAP, 'c', root, str(output)])
        bundle.compare_bnd2(source, output, os.path.basename(source))
        require(bundle.read_bnd2(output)['platform'] == 4, 'expected PC platform 4')
        roundtrip = os.path.join(work, 'roundtrip')
        bundle.extract(output, roundtrip)
        _, actual = native._one_aems_payload(roundtrip, output)
        require(actual == payload, 'ported payload changed during repack')
        print('ported %s: original X360 bytecode and samples, %d -> %d bytes, sha256 %s' %
              (os.path.basename(source), len(body), len(emitted), hashlib.sha256(emitted).hexdigest()[:16]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    convert(args.source, args.output)
