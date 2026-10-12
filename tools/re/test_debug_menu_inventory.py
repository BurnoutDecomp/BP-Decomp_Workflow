"""Parser checks for inventory evidence: nested calls, escaping and repeated rows."""
import unittest
import hashlib
from debug_menu_inventory import assembly_registrations, call_arguments, registrations


class RegistrationTests(unittest.TestCase):
    def test_assembly_supplement_requires_pinned_export_and_real_call(self):
        raw = b'original export'
        data = {'name': 'Debug::OnActivate', 'assembly': '0x82275FA8  bl        RegisterFunction'}
        evidence = {'function': data['name'], 'export_sha256': hashlib.sha256(raw).hexdigest(),
                    'call_address': '0x82275FA8', 'assembly_callee': 'RegisterFunction',
                    'kind': 'function', 'registration_api': 'Debug::RegisterFunction',
                    'caption': 'Save', 'path': '', 'arguments': ['this', 'Save', '""', '"Save"'],
                    'evidence': {'registers': 'verified'}}
        row = assembly_registrations(data, raw, [evidence])[0]
        self.assertEqual(row['caption'], 'Save')
        self.assertIsNone(row['pseudocode_line'])
        self.assertEqual(row['state'], 'pending')
        self.assertEqual(row['original_call_address'], '0x82275FA8')
        with self.assertRaisesRegex(ValueError, 'export changed'):
            assembly_registrations(data, b'changed export', [evidence])
        data['assembly'] = '0x82275FA8  bl        OtherFunction'
        with self.assertRaisesRegex(ValueError, 'call changed'):
            assembly_registrations(data, raw, [evidence])

    def test_nested_arguments(self):
        source = 'Register(this, Foo(a, b[2]), "Menu", "A, (B)")'
        args, end = call_arguments(source, source.index('('))
        self.assertEqual(args, ['this', 'Foo(a, b[2])', '"Menu"', '"A, (B)"'])
        self.assertEqual(end, len(source))

    def test_multiline_repeated_caption_is_not_deduplicated(self):
        api = {'sub_ABC': {'kind': 'variable', 'component_path': False}}
        body = 'void F() { sub_ABC(this, &a, "M",\n"Same"); sub_ABC(this, &b, "M", "Same"); }'
        rows = registrations(body, api)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['caption'], 'Same')
        self.assertNotEqual(rows[0]['arguments'][1], rows[1]['arguments'][1])
        self.assertEqual(rows[1]['pseudocode_line'], 2)

    def test_computed_caption_and_implicit_path_stay_unresolved(self):
        api = {'Register': {'kind': 'function', 'component_path': True}}
        rows = registrations('void F() { Register(this, fn, this, names[i]); }', api)
        self.assertIsNone(rows[0]['caption'])
        self.assertIsNone(rows[0]['path'])
        self.assertEqual(rows[0]['caption_resolution'], 'needs-evidence')
        self.assertEqual(rows[0]['state'], 'pending')

    def test_missing_wrapper_does_not_invent_a_path_overload(self):
        api = {'Register': {'kind': 'variable', 'component_path': None}}
        rows = registrations('void F() { Register(this, &value, "Count"); }', api)
        self.assertIsNone(rows[0]['uses_component_path'])
        self.assertIsNone(rows[0]['path_expression'])
        self.assertEqual(rows[0]['path_resolution'], 'needs-wrapper-export')


if __name__ == '__main__':
    unittest.main()
