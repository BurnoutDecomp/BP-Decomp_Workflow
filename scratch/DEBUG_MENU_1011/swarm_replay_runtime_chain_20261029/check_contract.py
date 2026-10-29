"""Compare the actual private frame source with the original assembly ordering.

This is a source contract check, not a gameplay witness. It rejects the old
source and deliberately removed/reordered edges before reporting a positive.
"""
from pathlib import Path
import hashlib, json, re
import tree_sitter, tree_sitter_cpp

OWN = Path(__file__).resolve().parent
PARSER = tree_sitter.Parser(tree_sitter.Language(tree_sitter_cpp.language()))
REL = Path("b5-decomp/src/GameSource/Game/BrnGameModule.cpp")


def functions(source):
    raw = source.encode("utf-8")
    text = lambda n: raw[n.start_byte:n.end_byte].decode("utf-8")
    rows = {}

    def walk(node):
        if node.type == "function_definition":
            decl = node.child_by_field_name("declarator")
            while decl is not None and decl.type != "function_declarator":
                decl = decl.child_by_field_name("declarator")
            if decl:
                name = text(decl.child_by_field_name("declarator")).split("::")[-1]
                body = node.child_by_field_name("body")
                calls = []

                def visit(n):
                    if n.type == "call_expression":
                        f = text(n.child_by_field_name("function"))
                        argnode = n.child_by_field_name("arguments")
                        args = [text(x) for x in argnode.named_children if x.type != "comment"]
                        calls.append({"function": f, "args": args, "offset": n.start_byte})
                    for c in n.named_children:
                        visit(c)

                visit(body)
                rows[name] = {"calls": sorted(calls, key=lambda x: x["offset"]),
                              "body": text(body)}
            return
        for c in node.named_children:
            walk(c)

    walk(PARSER.parse(raw).root_node)
    return rows


def check(source):
    rows = functions(source)
    main = rows["GameMain"]
    calls = main["calls"]
    errors = []

    def exact(name):
        matches = [c for c in calls if c["function"] == name]
        if len(matches) != 1:
            errors.append(f"{name}: expected one selected call, found {len(matches)}")
        return matches[0] if len(matches) == 1 else {"offset": -1, "args": []}

    native = ["DoUpdate_InputPreWorld", "DoUpdate_NetworkPreSim", "DoUpdate_GameStatePreWorld",
              "DoUpdate_ReplaysPreSim", "DoUpdate_GuiPreWorld", "DoPreUpdate_Sound",
              "ConstructUpdateSet", "lpState->Update", "DoUpdate_InputPostWorld",
              "DoUpdate_Effects", "FinishInGameSoundFramePC", "DoUpdate_ReplaysPostSim",
              "DoUpdate_GameStatePostWorld", "DoUpdate_NetworkPostSim", "UpdateTimers"]
    selected = [exact(n) for n in native]
    if [c["offset"] for c in selected] != sorted(c["offset"] for c in selected):
        errors.append("native producer/consumer call order")
    pre = exact("DoUpdate_ReplaysPreSim")
    post = exact("DoUpdate_ReplaysPostSim")
    if pre["args"][-1:] != ["lInitialModuleUpdateSet"]:
        errors.append("PreSim must receive initial FSM set")
    if post["args"][-1:] != ["lFullModuleUpdateSet"]:
        errors.append("PostSim must receive late output-derived set")
    if exact("BridgeReplayToGui")["offset"] >= exact("BridgeNetworkToGui")["offset"]:
        errors.append("Replay GUI events must precede Network GUI events")
    fx = exact("DoUpdate_Effects")["args"]
    if len(fx) != 11 or fx[2] != "&mPcInputOutputBuffer" or fx[6:8] != [
            "mpReplayPreSimOutputBuffer", "mpInGameSoundPreUpdateOutputPC"]:
        errors.append("Effects typed participant dataflow")
    if len(post["args"]) != 9 or post["args"][2:8] != [
            "mpWorldUpdateOutputBuffer", "mpEffectsOutputBuffer", "mpInGameSoundRootOutputPC",
            "mpDirectorOutputBuffer", "mpGuiOutputBuffer", "mpReplayPostSimOutputBuffer"]:
        errors.append("PostSim typed participant dataflow")
    if "mReplayModule.StoreSerialisers(" in main["body"]:
        errors.append("manual Effects-only registration bypass remains")
    if "GetGameDataRequestInterface()->mRequestQueue" not in main["body"]:
        errors.append("Replay resource request forwarding absent")
    finish = rows["FinishInGameSoundFramePC"]["body"]
    if "DestroyIOBuffer" in finish:
        errors.append("Sound output destroyed before PostSim")
    create, destroy = rows["CreateStaticIOBuffers"], rows["DestroyStaticIOBuffers"]
    lifetime = {}
    for stack in ["mpUpdateInputBufferStack", "mpUpdateOutputBufferStack"]:
        a = [c["args"][0] for c in create["calls"]
             if c["function"].startswith(stack + "->CreateIOBuffer")]
        b = [c["args"][0] for c in destroy["calls"]
             if c["function"].startswith(stack + "->DestroyIOBuffer")]
        lifetime[stack] = {"create": a, "destroy": b}
        if a != b[::-1]:
            errors.append(stack + " teardown is not reverse allocation order")
    allocated = lifetime["mpUpdateOutputBufferStack"]["create"]
    if "&mpReplayPreSimOutputBuffer" not in allocated or "&mpReplayPostSimOutputBuffer" not in allocated:
        errors.append("Replay phase outputs missing from frame lifetime")
    return errors, {"call_order": native, "lifetime": lifetime}


def main():
    before = (OWN / "preimage" / REL).read_text(encoding="utf-8")
    after = (OWN / "postimage" / REL).read_text(encoding="utf-8")
    errors, info = check(after)
    controls = {"source24_before": check(before)[0]}
    mutants = {
        "drop_pre_sim": after.replace("DoUpdate_ReplaysPreSim(mpUpdateInputBufferStack", "DroppedPreSim(mpUpdateInputBufferStack", 1),
        "wrong_post_set": after.replace("mpGuiOutputBuffer, mpReplayPostSimOutputBuffer,\n                                           lFullModuleUpdateSet", "mpGuiOutputBuffer, mpReplayPostSimOutputBuffer,\n                                           lInitialModuleUpdateSet", 1),
        "null_effects_replay": after.replace("                                 mpDirectorOutputBuffer,\n                                 mpReplayPreSimOutputBuffer,", "                                 mpDirectorOutputBuffer,\n                                 nullptr,", 1),
        "wrong_lifo": after.replace("&mpReplayPostSimOutputBuffer);", "&mpReplayPreSimOutputBuffer);", 1),
        "early_sound_teardown": after.replace("void BrnGameModule::FinishInGameSoundFramePC(BrnUpdateSet lUpdateSet)\n    {", "void BrnGameModule::FinishInGameSoundFramePC(BrnUpdateSet lUpdateSet)\n    { DestroyIOBuffer();", 1),
        "drop_replay_gui": after.replace("BridgeReplayToGui(mpGuiInputBuffer", "DroppedReplayGui(mpGuiInputBuffer", 1),
    }
    for name, source in mutants.items():
        assert source != after, name + " mutation did not bind"
        controls[name] = check(source)[0]
    assert controls["source24_before"], "baseline negative failed to detect the gap"
    assert all(controls.values()), controls
    asm = OWN / "evidence/ARTIST/DoUpdate.asm.txt"
    raw = asm.read_text(encoding="utf-8")
    for name in [x for x in info["call_order"] if x.startswith("DoUpdate_") or x == "ConstructUpdateSet"]:
        assert name in raw, "source contract missing raw ARTIST witness " + name
    receipt = {"passed": not errors, "errors": errors, "source_sha256": hashlib.sha256(after.encode()).hexdigest(),
               "assembly_sha256": hashlib.sha256(asm.read_bytes()).hexdigest(),
               "positive_contract": info, "negative_controls": controls,
               "native_behavior_proof": False}
    (OWN / "CONTRACT_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": not errors, "errors": errors, "negative_controls_rejected": len(controls)}))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
