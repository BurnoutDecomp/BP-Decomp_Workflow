"""Regression checks for black road mip tails (no game assets required)."""
import unittest
from unittest.mock import patch

import x360_tex as xt


class PackedMipOffsets(unittest.TestCase):
    def assert_slots(self, width, height, block_size, expected):
        base = xt.packed_mip_base(width, height)
        actual = [xt.packed_level_slot(base + i, base, width, height, block_size, True)
                  for i in range(len(expected))]
        self.assertEqual(expected, actual)

    def test_wide_asphalt(self):
        # ARTIST asphalt textures 50B9FD48 / 5687ADDD / 79519BF6.
        self.assert_slots(512, 256, 4,
                          [(0, 4), (0, 2), (0, 1), (4, 0), (2, 0), (1, 0)])

    def test_square_detail(self):
        self.assert_slots(256, 256, 4,
                          [(4, 0), (2, 0), (1, 0), (0, 2), (0, 1)])

    def test_tall_texture(self):
        self.assert_slots(64, 1024, 4,
                          [(4, 0), (2, 0), (1, 0), (0, 32), (0, 16),
                           (0, 8), (0, 4), (0, 2), (0, 1)])

    def test_uncompressed_offsets_are_texels(self):
        self.assert_slots(128, 128, 1,
                          [(16, 0), (8, 0), (4, 0), (0, 8), (0, 4)])

    def test_base_zero_uses_the_same_packing(self):
        self.assert_slots(32, 16, 4,
                          [(0, 4), (0, 2), (0, 1), (4, 0), (2, 0), (1, 0)])

    def test_unpacked_single_level_stays_at_origin(self):
        self.assertEqual((0, 0), xt.packed_level_slot(0, 0, 32, 8, 4, False))

    def test_packed_flag_is_required(self):
        with self.assertRaises(ValueError):
            xt.packed_level_slot(0, 0, 16, 16, 4, None)

    def test_port_keeps_authored_mips_in_order(self):
        # Synthetic linear DXT5 storage with distinct authored bytes per mip.
        # Coordinates are fixed independently of packed_level_slot. With the old
        # lookup table mip 7 reads mip 9's marker, and mip 9 reads empty padding.
        fetch = dict(width=512, height=256, depth=1, dimension=1,
                     data_format=20, mips=10, tiled=False, endian=1, packed_mips=True)
        regions, total, base = xt.storage_regions(512, 256, 10, 4, 16)
        body = bytearray(total)
        expected = bytearray()
        tail = regions[-1]
        slots = [(0, 4), (0, 2), (0, 1), (4, 0), (2, 0), (1, 0)]
        for level in range(10):
            width, height = max(1, 512 >> level), max(1, 256 >> level)
            bw, bh = max(1, (width + 3) // 4), max(1, (height + 3) // 4)
            marker = bytes([level + 1, 255 - level]) * 8
            expected.extend(bytes([255 - level, level + 1]) * (8 * bw * bh))
            if level < base:
                offset = regions[level][2]
                body[offset:offset + bw * bh * 16] = marker * (bw * bh)
            else:
                x, y = slots[level - base]
                for row in range(bh):
                    offset = tail[2] + ((y + row) * tail[4] + x) * 16
                    body[offset:offset + bw * 16] = marker * bw
        with patch.object(xt, 'parse_fetch_constant', return_value=fetch):
            pixels, _, stored = xt.port_pixels(b'', bytes(body))
        self.assertEqual(total, stored)
        self.assertEqual(bytes(expected), pixels)
        self.assertNotEqual(bytes(16), pixels[-16:])


if __name__ == '__main__':
    unittest.main()
