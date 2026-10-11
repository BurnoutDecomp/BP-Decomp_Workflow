"""Parser checks for inventory evidence: nested calls, escaping and repeated rows."""
import unittest
from debug_menu_inventory import call_arguments, registrations


class RegistrationTests(unittest.TestCase):
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
