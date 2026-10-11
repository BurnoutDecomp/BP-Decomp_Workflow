"""Navigation regressions: component-relative paths, helpers and uncertain data."""
import json
from pathlib import Path
import tempfile
import unittest

import search as finder


HEADER = '''
namespace Game {
class Car : public CgsDev::DebugComponent {
  const char* GetName() const { return "Car"; }
  const char* GetPath() const { return "Physics"; }
};
}
'''


def pc(text, header=HEADER):
    sources = [finder.parse_source("fixture.h", header), finder.parse_source("fixture.cpp", text)]
    return finder.pc_entries(sources, finder.component_identities(sources))[0]


class NavigationTests(unittest.TestCase):
    def test_component_group_and_absolute_manager_path(self):
        rows = pc('''namespace Game { void Car::OnActivate() {
          const char* group = "Tailgate...";
          RegisterVariable(&a, group, "Cone Depth");
          RegisterFunction(Reset, this, "Reset speed");
          GetUI().GetVariableManager().RegisterVariable(&b, "Graphics/Vehicles", "Wheels");
        }}''')
        self.assertEqual([r["menus"] for r in rows], [
            ["Development", "Physics", "Car", "Tailgate..."],
            ["Development", "Physics", "Car"],
            ["Development", "Graphics", "Vehicles"]])
        self.assertTrue(all(r["resolved"] for r in rows))

    def test_anonymous_namespace_constants_and_literal_caption_slash(self):
        rows = pc('''namespace Game {
          namespace { const char* GROUP = "Graphics\\\\Vehicles"; }
          void Car::OnActivate() { RegisterVariable(&a, GROUP, "Brake / High Beam"); }
        }''')
        self.assertEqual(rows[0]["menus"], ["Development", "Physics", "Car", "Graphics", "Vehicles"])
        self.assertEqual(rows[0]["caption"], "Brake / High Beam")
        self.assertTrue(rows[0]["resolved"])

    def test_comments_strings_and_disabled_code_are_not_entries(self):
        rows = pc('''namespace Game { void Car::OnActivate() {
          // RegisterVariable(&a, "Comment");
          const char* example = "RegisterVariable(&a, \\\"String\\\")";
          #if 0
          RegisterVariable(&a, "Disabled");
          #else
          RegisterVariable(&a, "Active");
          #endif
        }}''')
        self.assertEqual([r["caption"] for r in rows], ["Active"])

    def test_local_shadow_does_not_escape_closed_block(self):
        rows = pc('''namespace Game { void Car::OnActivate() {
          const char* group = "Outer";
          if (flag) { const char* group = "Inner"; RegisterVariable(&a, group, "Inside"); }
          RegisterVariable(&b, group, "Outside");
        }}''')
        self.assertEqual([r["menus"][-1] for r in rows], ["Inner", "Outer"])

    def test_inherited_getter_and_unimplemented_override(self):
        header = '''namespace Game {
          class Parent : public CgsDev::DebugComponent {
            const char* GetName() const { return "Parent"; }
            const char* GetPath() const { return "World"; }
          };
          class Car : public Parent { const char* GetName() const { return "Car"; } };
        }'''
        rows = pc('namespace Game { void Car::OnActivate() { RegisterVariable(&a, "Enabled"); }}', header)
        self.assertEqual(rows[0]["menus"], ["Development", "World", "Car"])
        missing = header.replace('class Car : public Parent {', 'class Car : public Parent { const char* GetPath() const;')
        rows = pc('namespace Game { void Car::OnActivate() { RegisterVariable(&a, "Enabled"); }}', missing)
        self.assertFalse(rows[0]["resolved"])

    def test_shared_helpers_preserve_distinct_paths_and_nested_arguments(self):
        rows = pc('''namespace Native {
          void Lod(CgsDev::DebugInterface& debug, const char* path) {
            debug.RegisterVariable(&a, path, "LOD mode");
          }
          void Options(CgsDev::DebugInterface& debug, const char* path) {
            debug.RegisterVariable(&a, path, "Enabled"); Lod(debug, path);
          }
          void Attach() {
            Options(GetDebug(a, b), "World/Reflections/Traffic");
            Options(GetDebug(a, b), "World/ShadowMap/Small objects");
          }
        }''')
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["resolved"] for r in rows))
        self.assertEqual({tuple(r["menus"]) for r in rows}, {
            ("Development", "World", "Reflections", "Traffic"),
            ("Development", "World", "ShadowMap", "Small objects")})

    def test_dynamic_path_remains_unresolved(self):
        rows = pc('''namespace Game { void Car::OnActivate() {
          RegisterVariable(&a, BuildPath(), "Enabled");
        }}''')
        self.assertFalse(rows[0]["resolved"])

    def test_known_false_helper_condition_does_not_invent_a_visible_control(self):
        rows = pc('''namespace Native {
          void Lod(CgsDev::DebugInterface& debug, const char* path) {
            debug.RegisterVariable(&a, path, "LOD mode");
          }
          void Options(CgsDev::DebugInterface& debug, const char* path, bool mesh) {
            if (mesh) { Lod(debug, path); debug.RegisterVariable(&a, path, "Fixed LOD"); }
          }
          void Attach() {
            Options(debug, "World/Traffic", true);
            Options(debug, "World/Lights", false);
          }
        }''')
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["menus"] == ["Development", "World", "Traffic"] for r in rows))

    def test_duplicate_captions_in_different_menus_stay_separate(self):
        rows = pc('''namespace Game { void Car::OnActivate() {
          RegisterVariable(&a, "Alpha", "Enabled"); RegisterVariable(&b, "Beta", "Enabled");
        }}''')
        merged = finder.merge_entries(rows)
        self.assertEqual(len(merged), 2)
        self.assertEqual(len(finder.search(merged, "car ENABLED alpha")), 1)

    def test_unknown_component_receiver_does_not_become_an_absolute_path(self):
        rows = pc('''namespace Other { void Attach() {
          component->RegisterVariable(&a, "Submenu", "Enabled");
        }}''')
        self.assertFalse(rows[0]["resolved"])

    def test_unknown_original_overload_does_not_invent_a_path(self):
        row = {"caption": "Original", "component": "Game::Car", "component_name": "Car",
               "component_path": "Physics", "path": None, "uses_component_path": None,
               "registration_api": "sub_UNKNOWN", "kind": "variable", "original_export": "original.json",
               "pseudocode_line": 3, "function": "Game::Car::OnActivate"}
        original = finder.reference_entries({"entries": [row]}, {})
        self.assertFalse(original[0]["resolved"])
        self.assertEqual(finder.search(original, "Original"), [])
        self.assertEqual(len(finder.search(original, "Original", True)), 1)

    def test_embedded_data_cannot_terminate_script(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            finder.write_page({"caption": "</script><script>alert(1)</script>"}, path)
            page = path.read_text(encoding="utf-8")
            data = page.split('<script id="menu-index" type="application/json">')[1].split("</script>")[0]
            self.assertNotIn("<script>", data)
            self.assertEqual(json.loads(data)["caption"], "</script><script>alert(1)</script>")


if __name__ == "__main__":
    unittest.main()
