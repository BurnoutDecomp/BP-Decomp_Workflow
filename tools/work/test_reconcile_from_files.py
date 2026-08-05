import unittest
from unittest import mock

import reconcile_from_files as reconcile


class ReconcileFromFilesTests(unittest.TestCase):
    def build(self, status, index, files, texts, *, no_demote=True, homes=None):
        with mock.patch.object(reconcile, "read_source", side_effect=lambda path: texts[path]), mock.patch.object(
            reconcile, "source_path"
        ) as source_path:
            source_path.return_value.exists.return_value = True
            return reconcile.build_reconciled_status(
                status,
                index,
                files,
                no_demote=no_demote,
                mapped_homes=homes or {},
            )

    def test_stale_blocking_note_cannot_turn_done_file_into_blocked(self):
        tu = "Game/Foo.cpp"
        path = "b5-decomp/src/Game/Foo.cpp"
        status = {"tu": {tu: {"status": "done", "notes": "Previously BLOCKED on data; now landed."}}, "func": {}}
        index = {tu: {"source": "decfigs", "functions": ["Foo::Bar"]}}

        result, changes, _ = self.build(status, index, [path], {path: "void Foo::Bar() {}"})

        self.assertEqual("done", result["tu"][tu]["status"])
        self.assertEqual([], changes)

    def test_file_evidence_promotes_stale_blocked_row_to_done(self):
        tu = "Game/Foo.cpp"
        path = "b5-decomp/src/Game/Foo.cpp"
        status = {"tu": {tu: {"status": "blocked", "notes": "BLOCKED on old dependency"}}, "func": {}}
        index = {tu: {"source": "decfigs", "functions": ["Foo::Bar"]}}

        result, _, _ = self.build(status, index, [path], {path: "void Foo::Bar() {}"})

        self.assertEqual("done", result["tu"][tu]["status"])
        self.assertEqual("reviewed", result["func"]["Foo::Bar"]["status"])

    def test_vendor_buckets_are_explicitly_blocked(self):
        tu = "vendor:lua"
        status = {"tu": {}, "func": {}}
        index = {tu: {"source": "vendor", "functions": ["lua_call"]}}

        result, _, _ = self.build(status, index, [], {})

        self.assertEqual("blocked", result["tu"][tu]["status"])
        self.assertIn("Vendor/runtime code", result["tu"][tu]["notes"])

    def test_class_tu_uses_resolved_home(self):
        tu = "class:Foo"
        path = "b5-decomp/src/Game/Foo.cpp"
        status = {"tu": {}, "func": {}}
        index = {tu: {"source": "class", "functions": ["Foo::Bar"]}}

        result, _, evidence = self.build(
            status,
            index,
            [path],
            {path: "void Foo::Bar() {}"},
            homes={tu: path},
        )

        self.assertEqual("done", result["tu"][tu]["status"])
        self.assertEqual([path], evidence[tu])

    def test_promote_only_retains_done_without_current_file_evidence(self):
        tu = "Game/Missing.cpp"
        status = {"tu": {tu: {"status": "done"}}, "func": {}}
        index = {tu: {"source": "decfigs", "functions": ["Missing::Body"]}}

        result, _, _ = self.build(status, index, [], {}, no_demote=True)

        self.assertEqual("done", result["tu"][tu]["status"])

    def test_authoritative_mode_removes_missing_and_stale_rows(self):
        missing = "Game/Missing.cpp"
        stale = "Game/NoLongerIndexed.cpp"
        status = {"tu": {missing: {"status": "done"}, stale: {"status": "blocked"}}, "func": {}}
        index = {missing: {"source": "decfigs", "functions": ["Missing::Body"]}}

        result, _, _ = self.build(status, index, [], {}, no_demote=False)

        self.assertNotIn(missing, result["tu"])
        self.assertNotIn(stale, result["tu"])


if __name__ == "__main__":
    unittest.main()
