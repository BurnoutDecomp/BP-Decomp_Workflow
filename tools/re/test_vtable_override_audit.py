#!/usr/bin/env python3
"""Offline tests for vtable_override_audit.py: no image, no exports, no tree.

    python tools/re/test_vtable_override_audit.py
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtable_override_audit as v  # noqa: E402


class FakeTree:
    """Answers "does this have a body?" from a fixed set."""

    def __init__(self, bodies=()):
        self.bodies = set(bodies)
        self.text = {}

    def lookup(self, cls, leaf):
        name = cls + "::" + leaf
        return ("exact", [name + ".cpp:1"]) if name in self.bodies else (None, [])


class FakeTable:
    owner, owner_why, parent = "BrnGameState::FaceOffMode", "test", 0x820D0498


def full_rows():
    return [{"name": n, "cls": "MISSING", "addr": "0x%08X" % a, "confidence": "high",
             "slots": [{"slot": 5, "table": "0x820D0500"}]} for n, a in v.CONTROL]


class Control(unittest.TestCase):
    TABLES = {0x820D0500: FakeTable()}

    def test_passes_when_every_case_is_found(self):
        self.assertTrue(v.evaluate_control(full_rows(), FakeTree(), self.TABLES, {})[0])

    def test_fails_when_a_bodyless_case_is_lost(self):
        for dropped in range(len(v.CONTROL)):
            rows = full_rows()
            del rows[dropped]
            ok, lines = v.evaluate_control(rows, FakeTree(), self.TABLES, {})
            self.assertFalse(ok, v.CONTROL[dropped][0])
            self.assertTrue(any("FAIL" in x for x in lines))

    def test_fails_when_a_case_is_misclassified(self):
        rows = full_rows()
        rows[0]["cls"] = "ICF_NAME_ONLY"
        self.assertFalse(v.evaluate_control(rows, FakeTree(), self.TABLES, {})[0])

    def test_fails_when_the_address_moved(self):
        rows = full_rows()
        rows[0]["addr"] = "0x82000000"
        self.assertFalse(v.evaluate_control(rows, FakeTree(), self.TABLES, {})[0])

    def test_a_fixed_case_passes_without_a_row(self):
        name = v.CONTROL[0][0]
        rows = [r for r in full_rows() if r["name"] != name]
        self.assertTrue(v.evaluate_control(rows, FakeTree([name]), self.TABLES, {})[0])

    def test_a_fixed_case_still_reported_fails(self):
        self.assertFalse(v.evaluate_control(full_rows(), FakeTree([v.CONTROL[0][0]]),
                                            self.TABLES, {})[0])

    def test_fails_when_the_table_owner_is_wrong(self):
        class Wrong(FakeTable):
            owner = "CgsSceneManager::CgsCollision::BaseCollisionGenerator"
        self.assertFalse(v.evaluate_control(full_rows(), FakeTree(), {0x820D0500: Wrong()}, {})[0])


class Names(unittest.TestCase):
    def test_plain(self):
        n = v.Name("BrnGameState::FaceOffMode::Start")
        self.assertEqual((n.cls, n.leaf, n.dtor), ("BrnGameState::FaceOffMode", "Start", False))

    def test_deleting_destructor(self):
        self.assertTrue(v.Name("A::B::`vector deleting destructor'").dtor)

    def test_adjustor_is_a_thunk_of_the_method(self):
        n = v.Name("BrnParticle::IInternalAllocator::Free`adjustor{4}' ")
        self.assertTrue(n.thunk)
        self.assertEqual(n.leaf, "Free")

    def test_clipped_template_head(self):
        n = v.Name("rw::math::vpu::Vector3,8>::GetCurre")
        self.assertTrue(n.clipped_template)
        self.assertEqual((n.cls, n.leaf), ("", "GetCurre"))

    def test_unnamed(self):
        self.assertFalse(v.Name("sub_82200570").named)


class Dwarf(unittest.TestCase):
    def test_a_qualified_head_splits_at_the_lone_colon(self):
        self.assertEqual(v.split_class_head("BrnGameState::FaceOffMode : public BrnGameState::OfflineGameMode"),
                         ("BrnGameState::FaceOffMode", "public BrnGameState::OfflineGameMode"))

    def test_template_arguments_do_not_split(self):
        self.assertEqual(v.split_class_head("A::B<C::D,8u>"), ("A::B<C::D,8u>", None))


class Tables(unittest.TestCase):
    def test_a_second_destructor_starts_a_new_table(self):
        g = {1: {"n": "A::`vector deleting destructor'"}, 2: {"n": "A::F"},
             3: {"n": "destructor'`adjustor{"}, 4: {"n": "B::G"}}
        self.assertEqual(v.split_on_second_dtor([1, 2, 3, 4], g), [[1, 2], [3, 4]])

    def test_one_destructor_keeps_the_table_whole(self):
        g = {1: {"n": "A::F"}, 2: {"n": "A::`scalar deleting destructor'"}, 3: {"n": "A::G"}}
        self.assertEqual(v.split_on_second_dtor([1, 2, 3], g), [[1, 2, 3]])


class Trailers(unittest.TestCase):
    """The defect the hand sample found: `const override {` must read as a definition."""

    def scan(self, code):
        defs, decls = {}, {}
        v.sls.scan_file("x.h", code, defs, decls)
        return defs, decls

    def test_inline_const_override_is_a_definition(self):
        defs, _ = self.scan('struct S : B { const char* GetName() const override { return "x"; } };')
        self.assertIn("S::GetName", defs)

    def test_declaration_stays_a_declaration(self):
        defs, decls = self.scan("struct S : B { const char* GetName() const override; };")
        self.assertNotIn("S::GetName", defs)
        self.assertIn("S::GetName", decls)


if __name__ == "__main__":
    unittest.main()
