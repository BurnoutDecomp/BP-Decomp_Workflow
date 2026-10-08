"""Source matching controls for the public evidence audit."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import funcaudit


def index(tmp_path, monkeypatch, source):
    monkeypatch.setattr(funcaudit, "SRC", str(tmp_path))
    path = tmp_path / "Moved.cpp"
    path.write_text(source, encoding="utf-8", newline="")
    idx = funcaudit.PcIndex()
    idx.add_file(str(path))
    return idx


def test_namespace_function_survives_moved_or_unknown_primary_file(tmp_path, monkeypatch):
    idx = index(tmp_path, monkeypatch, "namespace BrnDirector { void PrintShotProperties(int f) {} }")
    for primary in ("GameSource/Director/BrnShotSelector.cpp", ""):
        d, count = idx.find("BrnDirector::PrintShotProperties", primary)
        assert d.file == "Moved.cpp" and count == 1


def test_header_inline_belongs_to_its_class(tmp_path, monkeypatch):
    idx = index(tmp_path, monkeypatch, """
namespace A {
class First { public: int GetName() const { return 1; } };
class Second { public: int GetName() const { return 2; } };
}
""")
    first, _ = idx.find("A::First::GetName", "Moved.cpp")
    second, _ = idx.find("A::Second::GetName", "Moved.cpp")
    assert "return 1" in first.code and "return 2" in second.code
    assert idx.find("A::Missing::GetName", "Moved.cpp") == (None, 0)


def test_namespace_collision_does_not_pair_wrong_class(tmp_path, monkeypatch):
    idx = index(tmp_path, monkeypatch, "namespace Other { void Manager::Update() {} }")
    assert idx.find("Wanted::Manager::Update", "Moved.cpp") == (None, 0)


def test_global_function_without_file_hint(tmp_path, monkeypatch):
    idx = index(tmp_path, monkeypatch, "float XMVectorCos(float x) { return x; }")
    d, count = idx.find("XMVectorCos", "")
    assert d.qual == "XMVectorCos" and d.nparams == 1 and count == 1


def test_reference_and_pointer_return_types_keep_function_name(tmp_path, monkeypatch):
    idx = index(tmp_path, monkeypatch, """
namespace Attrib {
const TypeDesc& Database::GetTypeDesc(int key) const { return desc; }
const TypeDesc* Database::GetPointer() { return &desc; }
}
""")
    assert idx.find("Attrib::Database::GetTypeDesc", "")[0].nparams == 1
    assert idx.find("Attrib::Database::GetPointer", "")[0].nparams == 0


def test_constructor_body_excludes_braced_initializers_and_calls(tmp_path, monkeypatch):
    idx = index(tmp_path, monkeypatch, """
namespace A::B {
class Foo { public: Foo() : x{1} { Helper(); } int x; };
void Run() { if (Check()) { Helper(); } }
void Declared();
}
""")
    d, _ = idx.find("A::B::Foo::Foo", "")
    assert d.code == "{ Helper(); }" and d.nparams == 0
    assert idx.find("A::B::Declared", "") == (None, 0)
    assert set(idx.by_exact) == {"A::B::Foo::Foo", "A::B::Run"}


def test_comments_strings_and_crlf_preserve_source_location(tmp_path, monkeypatch):
    idx = index(tmp_path, monkeypatch,
                '// void Fake() {}\r\nnamespace A {\r\nconst char* Text() { return "é }"; }\r\n}')
    d, _ = idx.find("A::Text", "")
    assert d.line == 3 and '"é }"' in d.raw
    assert "Fake" not in idx.by_exact


def test_macro_defined_functions_are_not_fabricated(tmp_path, monkeypatch):
    idx = index(tmp_path, monkeypatch, "#define EMPTY(Name) void Name() {}\nEMPTY(Unknown)\n")
    assert idx.find("Unknown", "") == (None, 0)
