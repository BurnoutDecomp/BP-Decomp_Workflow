"""Synthetic ABI/relocation tests; no game assets are embedded in the suite."""
import struct
import unittest

import aems_x360_port as port


def u32(data, pos):
    return struct.unpack_from('<I', data, pos)[0]


def fixture():
    """Small bytecode graph with a nonlocal value copy and both pointer kinds."""
    blocks = [bytearray(20), bytearray(24), bytearray(4), bytearray(16),
              bytearray(40), bytearray(16)]
    blocks[1][16] = 1
    struct.pack_into('>I', blocks[1], 20, 0x12345678)
    blocks[4][14] = 1
    blocks[4][16] = 0xff
    blocks[4][28] = 9
    struct.pack_into('>II', blocks[4], 32, 0xffffffff, 0xabcdef01)
    body = bytearray(0x9c)  # 0x5c header + 0x3c module + one player offset
    body[:4] = b'ABKC'
    body[7:9] = b'\1\5'
    struct.pack_into('>H', body, 0xa, 1)
    struct.pack_into('>I', body, 0x1c, 0x5c)
    struct.pack_into('>II', body, 0x40, 0xffffffff, 0xffffffff)
    struct.pack_into('>H', body, 0x5c + 0x1e, 999)
    body[0x5c + 0x24:0x5c + 0x28] = bytes((1, 1, 1, 0))
    program = len(body)
    # Source data starts at instance+24. Copy ClassData.parameters[0] (old+64)
    # to the player's input[0].value (old+124); also copy the table's return.
    for op in (0, 1, 3, 15, 27, 4):
        pairs = [(20, 80)] if op == 1 else ([(-1, 28)] if op == 15 else [])
        body += bytes((op, len(pairs), 0, 0))
        for pair in pairs:
            body += struct.pack('>ii', *pair)
        body += struct.pack('>I', len(blocks[(0, 1, 3, 15, 27, 4).index(op)]))
    body += b'\xff\0\0\0'
    template = len(body)
    body += bytes(24) + b''.join(blocks)
    table = len(body)
    body += struct.pack('>BBHiifhh', 2, 0, 2, -20, 20, .25, -1234, 2345)
    selector = len(body)
    body += struct.pack('>IH6Bi', 1, 0, 0xff, 0, 1, 2, 3, 4, -1)
    # Player is at instance+88, destroy subscriber at +128, total 144.
    struct.pack_into('>IIII', body, 0x5c + 0x28, program, template, 144, 128)
    struct.pack_into('>I', body, 0x5c + 0x3c, 88)
    table_site = template + 72
    selector_site = template + 92
    struct.pack_into('>I', body, table_site, table)
    struct.pack_into('>I', body, selector_site, selector)
    body += bytes(port.align(len(body), 128) - len(body))
    resident = len(body)
    samples = b'S10A' + struct.pack('>III', 0, 1, 16) + bytes.fromhex('0300bb80200001000000000000000000')
    body += samples
    funcs = len(body)
    body += struct.pack('>I', 0)
    ptrs = len(body)
    body += struct.pack('>3I', 2, table_site, selector_site)
    csis = len(body)
    body += struct.pack('>IIIB3s', 1, 0x60, csis + 16, 1, b'ABC')
    body += struct.pack('>HH', 0x73c8, 0x73c8) + b'TestClass\0'
    body += bytes(port.align(len(body), 16) - len(body))
    for p, val in ((0x14, len(body)), (0x18, resident), (0x20, resident),
                   (0x24, len(samples)), (0x30, funcs), (0x34, ptrs), (0x38, csis)):
        struct.pack_into('>I', body, p, val)
    return body


class AemsPort(unittest.TestCase):
    def setUp(self):
        self.source = fixture()
        self.output = port.port_body(self.source)

    def test_samples_and_source_unchanged(self):
        self.assertEqual(self.source, fixture())
        start = struct.unpack_from('>I', self.source, 0x20)[0]
        size = struct.unpack_from('>I', self.source, 0x24)[0]
        self.assertEqual(self.output[u32(self.output, 0x20):u32(self.output, 0x20) + size],
                         self.source[start:start + size])

    def test_native_module_and_instance(self):
        b = self.output
        self.assertEqual(b[8], 10)
        self.assertEqual(u32(b, 0x1c), 0x78)
        self.assertEqual(u32(b, 0x78 + 0x58), 256)
        self.assertEqual(u32(b, 0x78 + 0x5c), 224)
        self.assertEqual(u32(b, 0x78 + 0x68), 168)
        self.assertEqual(u32(b, 0x18) % 128, 0)
        t = struct.unpack_from('<Q', b, 0x78 + 0x50)[0]
        self.assertEqual(u32(b, t + 128), 0x12345678)
        self.assertEqual(u32(b, t + 168 + 48), 0xabcdef01)

    def test_instruction_offsets_match_native_field_layout(self):
        b = self.output
        pc = struct.unpack_from('<Q', b, 0x78 + 0x48)[0]
        actual = []
        while b[pc] != 0xff:
            op, n = b[pc:pc + 2]
            pairs = [struct.unpack_from('<ii', b, pc + 4 + 8 * i) for i in range(n)]
            actual.append((op, pairs, u32(b, pc + 4 + 8 * n)))
            pc += 8 + 8 * n
        self.assertEqual(actual, [(0, [], 40), (1, [(40, 128)], 48),
                                  (3, [], 8), (15, [(-1, 48)], 24),
                                  (27, [], 56), (4, [], 32)])

    def test_pointer_targets_and_class_reference(self):
        b = self.output
        p = u32(b, 0x34)
        self.assertEqual(u32(b, p), 2)
        sites = [u32(b, p + 4 + 4 * i) for i in range(2)]
        table, selector = [struct.unpack_from('<Q', b, site)[0] for site in sites]
        self.assertEqual(struct.unpack_from('<BBHiifhh', b, table), (2, 0, 2, -20, 20, .25, -1234, 2345))
        self.assertEqual(struct.unpack_from('<IH6Bi', b, selector), (1, 0, 255, 0, 1, 2, 3, 4, -1))
        c = u32(b, 0x38)
        self.assertEqual((u32(b, c), u32(b, c + 4), b[c + 12]), (1, 0x80, 1))
        ident = u32(b, c + 8)
        self.assertEqual(struct.unpack_from('<HH', b, ident), (0x73c8, 0x73c8))
        self.assertEqual(b[ident + 4:ident + 14], b'TestClass\0')

    def test_unknown_opcode_is_rejected(self):
        self.source[0x9c] = 39
        with self.assertRaises(port.PortError):
            port.port_body(self.source)

    def test_native_machine_code_is_rejected(self):
        p = struct.unpack_from('>I', self.source, 0x30)[0]
        struct.pack_into('>I', self.source, p, 1)
        with self.assertRaisesRegex(port.PortError, 'machine-code'):
            port.port_body(self.source)

    def test_unaccounted_pointer_is_rejected(self):
        p = struct.unpack_from('>I', self.source, 0x34)[0]
        struct.pack_into('>I', self.source, p + 4, 0x60)
        with self.assertRaisesRegex(port.PortError, 'pointer relocations'):
            port.port_body(self.source)

    def test_nonzero_unwalked_bytes_are_rejected(self):
        resident = struct.unpack_from('>I', self.source, 0x18)[0]
        self.source[resident - 1] = 1
        with self.assertRaisesRegex(port.PortError, 'unaccounted nonzero'):
            port.port_body(self.source)


if __name__ == '__main__':
    unittest.main()
