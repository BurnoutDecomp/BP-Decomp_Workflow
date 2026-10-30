"""Run the existing evidence/faithfulness audits on exact private source objects."""
from pathlib import Path
import hashlib, importlib.util, json, sys

OWN = Path(__file__).resolve().parent
WF = OWN.parents[2]
sys.path.insert(0, str(WF / "tools/re"))
import funcaudit as fa

REL = Path("b5-decomp/src/GameSource/Game/BrnGameModule.cpp")
NATIVE = {"DoUpdate_Sound": "823DCEC0", "DoUpdate_Effects": "823DD0A8",
          "DoUpdate_GameStatePostWorld": "823E92A8", "DoUpdate_ReplaysPreSim": "823DD2A0",
          "DoUpdate_ReplaysPostSim": "823DD408"}


def audit(part):
    root = OWN / part / "b5-decomp/src"
    fa.SRC = str(root)
    index = fa.PcIndex()
    index.add_file(str(OWN / part / REL))
    index.add_file(str(root / "GameSource/Game/BrnGameModule.hpp"))
    identity = json.loads((WF / "progress/identity.json").read_text(encoding="utf-8"))
    key2 = {"::".join(name.split("::")[-2:]) for name in identity}
    leaves = {name.split("::")[-1] for name in identity}
    out = {}
    for method, address in NATIVE.items():
        name = "BrnGame::BrnGameModule::" + method
        definition, count = index.find(name, "GameSource/Game/BrnGameModule.cpp")
        assert definition and count == 1, name
        feature = fa.console_features("0x" + address, str(OWN / "evidence/ARTIST" / ("0x" + address + ".json")))
        findings, flagged, helpers = fa.compare(name, feature, definition, index, key2, leaves)
        out[name] = {"findings": findings, "flagged": flagged, "helpers": helpers}
    return out


def main():
    before, after = audit("preimage"), audit("postimage")
    new_high = {}
    for name, row in after.items():
        for category, findings in row["findings"].items():
            if category in ["MISSING_CALLEE", "MISSING_CASE", "MISSING_ASSERT", "MISSING_EVENT", "NO_BODY"]:
                fresh = [f for f in findings if f not in before[name]["findings"].get(category, [])]
                if fresh:
                    new_high.setdefault(name, {})[category] = fresh
    receipt = {"before": before, "after": after, "new_high_signal": new_high,
               "passed_no_new_high_signal": not new_high, "behavior_proof": False,
               "scope": "five native bridge wrappers; separate source contract binds manual host scheduling"}
    (OWN / "AUDIT_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed_no_new_high_signal": not new_high, "new_high_signal": new_high}))
    return 1 if new_high else 0


if __name__ == "__main__":
    raise SystemExit(main())
