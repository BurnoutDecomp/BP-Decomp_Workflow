from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).parent))
from source_status import build_evidence


def definition(qual):
    return SimpleNamespace(qual=qual, nparams=0, code="{ return 1; }", file="Moved.h", line=3)


def test_scoped_evidence_recovers_moved_functions_and_rejects_stubs_and_ambiguity():
    names = ("A::Run", "B::Run", "Global", "Overload", "Missing::Run")
    identity = {name: {"x360_addrs": ["0x82000000"]} for name in names}
    index = SimpleNamespace(by_exact={"A::Run": [definition("A::Run")],
                                     "B::Run": [definition("B::Run")],
                                     "Global": [definition("Global")],
                                     "Overload": [definition("Overload"), definition("Overload")]})
    tus = {name: {"functions": [name]} for name in names}
    result = build_evidence(tus, identity, [{"name": "B::Run"}], index, "a" * 40)
    assert set(result["functions"]) == {"A::Run", "Global"}
    assert set(result["tus"]) == {"A::Run", "Global"}
    assert result["functions"]["A::Run"]["file"] == "Moved.h"


def test_unsupported_or_partial_tus_and_vendor_buckets_are_not_completed():
    index = SimpleNamespace(by_exact={"A::Run": [definition("A::Run")]})
    identity = {"A::Run": {"x360_addrs": ["0x82000000"]}}
    tus = {"partial": {"functions": ["A::Run", "A::Missing"]},
           "template": {"functions": ["A::Run", "Array<int>::Get"]},
           "vendor:lib": {"functions": ["A::Run"], "source": "vendor"},
           "empty": {"functions": []}}
    result = build_evidence(tus, identity, [], index, "a" * 40)
    assert result["functions"] and result["tus"] == {}


def test_attested_rename_cannot_hide_a_stub_under_its_cpp_name():
    index = SimpleNamespace(by_exact={"Ledger::EventEvent": [definition("Actual::Event")]})
    identity = {"Ledger::EventEvent": {"x360_addrs": ["0x82000000"]}}
    tus = {"A": {"functions": ["Ledger::EventEvent"]}}
    result = build_evidence(tus, identity, [{"name": "Actual::Event"}], index, "a" * 40)
    assert result["functions"] == result["tus"] == {}
