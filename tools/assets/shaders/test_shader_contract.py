"""Sampler regressions; run: python -m unittest discover -s tools/assets/shaders -v.

The compiler test uses the Windows SDK fxc and checked-out NuShaders sources.
The remaining tests need neither game assets nor a graphics device.
"""
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import convert_shaders_bundle as converter
import shader_transcode as st


def technique(samplers, le=False):
    endian = '<' if le else '>'
    data = bytearray(0x98 + len(samplers) * 8)
    struct.pack_into(endian + 'I', data, 0x8C, 0x98)
    data[0x90] = len(samplers)
    struct.pack_into(endian + 'I', data, 0x94, len(data))
    data.extend(b'Test_Default\0')
    for index, (name, unit) in enumerate(samplers):
        struct.pack_into(endian + 'Ih', data, 0x98 + index * 8, len(data), unit)
        data.extend(name.encode('ascii') + b'\0')
    return bytes(data)


def program(variables):
    # The real serialized descriptor table, independent of the contract checker.
    data = bytearray(0x14 + len(variables) * 8)
    struct.pack_into('<H', data, 4, len(variables))
    for index, (name, unit, datatype, count) in enumerate(variables):
        struct.pack_into('<IBBBB', data, 0x14 + index * 8,
                         len(data), unit, datatype, count, 0)
        data.extend(name.encode('ascii') + b'\0')
    return bytes(data)


class SamplerContractTests(unittest.TestCase):
    def check_contract(self, expected, variables, le=False, slot=4):
        return converter.check_sampler_contract(
            {'tech': (technique(expected, le), {slot: 1})},
            {'00000001': program(variables)}, technique_le=le)

    def test_unused_bindings_and_non_samplers_are_allowed(self):
        for le in (False, True):
            with self.subTest(le=le):
                self.assertEqual([], self.check_contract(
                    [('baseMapSampler', 2), ('shadowMapSamplerHighDetail', 15)],
                    [('baseMapSampler', 2, 3, 1), ('world', 0, 2, 4)], le))

    def test_unbound_normal_maps_fail_for_both_byte_orders(self):
        for le in (False, True):
            with self.subTest(le=le):
                problems = self.check_contract(
                    [('baseMapSampler', 2)], [('NormalTextureSampler', 3, 3, 1)], le)
                self.assertEqual([('Test_Default', 'PS', 'NormalTextureSampler',
                                   3, None, 1, '00000001')], problems)

    def test_same_name_at_wrong_register_fails(self):
        problems = self.check_contract([('baseMapSampler', 2)],
                                       [('baseMapSampler', 0, 3, 1)])
        self.assertEqual((0, 2), problems[0][3:5])

    def test_extra_array_registers_fail(self):
        self.assertTrue(self.check_contract([('baseMapSampler', 2)],
                                           [('baseMapSampler', 2, 3, 2)]))

    def test_vertex_sampler_is_checked(self):
        problems = self.check_contract([], [('heightSampler', 0, 3, 1)], slot=0)
        self.assertEqual('VS', problems[0][1])

    def test_strict_report_rejects_bad_bundle(self):
        problems = self.check_contract([], [('NormalTextureSampler', 3, 3, 1)])
        with patch('builtins.print'):
            with self.assertRaises(SystemExit):
                converter.report_sampler_contract(problems, strict=True)
            self.assertEqual(1, converter.report_sampler_contract(problems, strict=False))


class RoadCompilerTests(unittest.TestCase):
    def test_compiled_road_samplers_match_artist(self):
        try:
            fxc = converter.find_fxc()
        except SystemExit:
            self.skipTest('Windows SDK fxc unavailable')
        source_dir = Path(converter.DEFAULT_FX_DIR)
        if not source_dir.is_dir():
            self.skipTest('NuShaders submodule unavailable')
        # ARTIST SHADERS.BNDL technique tables: the three plain surfaces use
        # base/detail/shadow; roads also use lineMap, and the lightmapped tunnel
        # adds LightmapTextureSampler at s3. No road normal maps at s3/s4.
        with tempfile.TemporaryDirectory() as tmp:
            sources = [p for p in source_dir.glob('*.fx')
                       if p.name.lower() in converter.X360_ROAD_SOURCES]
            self.assertEqual(6, len(sources))
            for source in sources:
                expected = {'baseMapSampler': 0, 'detailMapSampler': 1,
                            'shadowMapSamplerHighDetail': 15}
                if 'road_' in source.name.lower():
                    expected.update(baseMapSampler=2, lineMapSampler=0)
                if 'lightmapped' in source.name.lower():
                    expected['LightmapTextureSampler'] = 3
                for entry, profile in (('VS_Main', 'vs_3_0'), ('PS_Main', 'ps_3_0')):
                    with self.subTest(source=source.name, profile=profile):
                        bytecode = converter.compile_entry(
                            fxc, str(source), entry, profile, converter.DEFAULT_INCLUDE_DIR,
                            os.path.join(tmp, 'shader.fxo'))
                        samplers = {name: unit for name, kind, unit, count
                                    in st.parse_ctab(bytecode) if kind == 3}
                        self.assertEqual(expected if profile == 'ps_3_0' else {}, samplers)


if __name__ == '__main__':
    unittest.main()
