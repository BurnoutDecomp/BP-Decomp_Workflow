"""ARTIST schema and RoadnoiseEffect826E5D08 surface-field regression."""
import struct
import unittest

import attribsys_transcode as port


def convert(data):
    widths = port.PAYLOAD_CLASS_SCHEMAS[(port.CLS_AUDIOSURFACE, False)](len(data))
    fields = []
    offset = 0
    for width in widths:
        fields.append((offset, width, 'audiosurface'))
        offset += width
    return port.flip(data, fields)


class AudioSurface(unittest.TestCase):
    def test_original_surface_loop(self):
        # One original SURFACELIST collection: road loop9, transition-on -1.
        source = bytes.fromhex(
            '3f800000000000003f8000003fc000003f00000000000002ffff000000000009')
        actual = convert(source)
        self.assertEqual(struct.unpack_from('<h', actual, 0x1e)[0], 9)
        self.assertEqual(struct.unpack_from('<h', actual, 0x18)[0], -1)

    def test_distinct_signed_halfwords(self):
        source = struct.pack('>fB3s3fI4h', 1.5, 0, b'\0\0\0',
                             3, 2.5, 0.5, 2, -1, -32768, 32767, 11)
        self.assertEqual(struct.unpack_from('<4h', convert(source), 0x18),
                         (-1, -32768, 32767, 11))

    def test_scalars_bool_and_padding(self):
        # XEX schema82CD3D88/82CD53B0: SoftLanding is one byte at+4.
        values = (1.5, 1, b'\x12\x34\x56', 3, 2.5, 0.5, 2, -1, 0, 0, 9)
        self.assertEqual(struct.unpack('<fB3s3fI4h', convert(struct.pack('>fB3s3fI4h', *values))), values)


if __name__ == '__main__':
    unittest.main()
