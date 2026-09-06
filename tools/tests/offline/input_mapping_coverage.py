"""input_mapping_coverage.py -- does the PC pad bind what the CONSOLE pad binds?

THE ORACLE IS THE IMAGE, not taste. `gaDefaultGameInputMapping` is a DATA symbol with no IDA
export, so for a long time the PC input leaf carried an honest park saying the console's
control->action table "cannot be read on this host" and every pad binding was a PC guess. It
can be read, and this script reads it:

    BrnGame::BrnGameModule::PrepareInitialInputMapping @0x823BCF40
        -> CgsInput::InputIO::PostWorldInputBuffer::PostMappingRequest(buf, &unk_82CDBEB8, -1)
           memcpy's exactly 112 bytes from 0x82CDBEB8   <-- THE TABLE
        -> CgsInput::InputModule::ProcessMappingQueue @0x828E7098 copies those 112 bytes into
           every one of the 4 ports (pad id -1 == "all pads")
        -> CgsInput::InputPads::Update @0x828F8690 (an EXPORT HOLE; disassembled with
           tools/re/ppcdis.py) walks it at this + port*0x70 + 0x7B8, stride 4, 28 entries,
           four signed bytes each: for every raw control i and every action id in entry i,
           maActionInfo[id].mfValue = MAX(mfValue, rawControl[i]).   -1 == no action.

So the table is ActionMapping[28] = int8_t[4], control index -> up to four EGameInputActions.
28 == CgsInput::EPadButton's pad range (E_PADBUTTON_UP..E_WHEELBUTTON_RIGHT_PADDLE); the DWARF
declares gaDefaultGameInputMapping[34] on PS3, but the X360 memcpy is 112 bytes, and the entry
at 0x82CDBF28 (the 29th) is all -1, so 28 is the used extent on our spine.

USAGE
    py -3 tools/tests/offline/input_mapping_coverage.py [--log <BrnGame.log>] [--json]

It builds the PC side from, in order of preference:
  1. the RUNTIME dump in a run's BrnGame.log -- lines
         [input-map] control <n> <NAME> -> actions a,b,c,d
     printed once at input bring-up when BRN_INPUT_MAP_DUMP=1 (CgsInputPadsPC.cpp). This is
     the built exe speaking, which is the only thing a GREEN run may be graded on.
  2. failing that, a STATIC parse of the KA_BINDINGS table in CgsInputPadsPC.cpp -- the
     per-action `uXPadButtons` / `eXPadAnalogue` columns of the pre-2026-09-06 leaf. This is
     what makes the RED run's failure detail name the actual missing bindings instead of just
     "no witness line".

Exit 0 only when the runtime dump exists AND every control's action set equals the image's.
"""
import argparse
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# --- the console table -----------------------------------------------------------------------
KU_MAPPING_VA = 0x82CDBEB8   # &unk_82CDBEB8, the argument PrepareInitialInputMapping posts
KU_MAPPING_CONTROLS = 28     # 112 bytes / 4 == the memcpy in PostMappingRequest
KU_IMAGE_BASE = 0x82000000
KA_IMAGE_CANDIDATES = (
    os.environ.get("BRN_IMAGE_BIN", ""),
    os.path.join(ROOT, "scratch", "postfx_step9_final", "envfix", "work", "image.bin"),
)

# CgsInput::EPadButton, references/DecFIGS/dwarfdump/GameShared/GameClasses/System/Input/
# Devices/PS3/CgsInputDevicePS3Pad.h:40 -- the index space of the mapping table. Controls
# 24..27 are wheel-only (DeviceX360Pad::Update @0x828E7AB0 writes 0 into them for a pad).
KA_CONTROL_NAMES = [
    "E_PADBUTTON_UP", "E_PADBUTTON_DOWN", "E_PADBUTTON_LEFT", "E_PADBUTTON_RIGHT",
    "E_PADBUTTON_START", "E_PADBUTTON_SELECT", "E_PADBUTTON_LTHUMB", "E_PADBUTTON_RTHUMB",
    "E_PADBUTTON_CROSS", "E_PADBUTTON_CIRCLE", "E_PADBUTTON_SQUARE", "E_PADBUTTON_TRIANGLE",
    "E_PADBUTTON_L1", "E_PADBUTTON_R1", "E_PADBUTTON_L2", "E_PADBUTTON_R2",
    "E_PADBUTTON_ANALOGUE_0_UP", "E_PADBUTTON_ANALOGUE_0_DOWN",
    "E_PADBUTTON_ANALOGUE_0_LEFT", "E_PADBUTTON_ANALOGUE_0_RIGHT",
    "E_PADBUTTON_ANALOGUE_1_UP", "E_PADBUTTON_ANALOGUE_1_DOWN",
    "E_PADBUTTON_ANALOGUE_1_LEFT", "E_PADBUTTON_ANALOGUE_1_RIGHT",
    "E_WHEELBUTTON_ACCELERATOR", "E_WHEELBUTTON_BRAKE",
    "E_WHEELBUTTON_LEFT_PADDLE", "E_WHEELBUTTON_RIGHT_PADDLE",
]

# The XINPUT_GAMEPAD wButtons bit each pad control is driven by, exactly as
# CgsInput::DeviceX360Pad::Update @0x828E7AB0 stores them (device float array base this+76:
# mask 0x1 -> +76 = control 0 ... mask 0x200 -> +128 = control 13). Used only by the STATIC
# parse of the old KA_BINDINGS shape.
KA_XPAD_NAME_TO_CONTROL = {
    "KU_XPAD_DPAD_UP": 0, "KU_XPAD_DPAD_DOWN": 1, "KU_XPAD_DPAD_LEFT": 2,
    "KU_XPAD_DPAD_RIGHT": 3, "KU_XPAD_START": 4, "KU_XPAD_BACK": 5,
    "KU_XPAD_LTHUMB": 6, "KU_XPAD_RTHUMB": 7, "KU_XPAD_A": 8, "KU_XPAD_B": 9,
    "KU_XPAD_X": 10, "KU_XPAD_Y": 11, "KU_XPAD_LSHOULDER": 12, "KU_XPAD_RSHOULDER": 13,
}
KA_ANALOGUE_NAME_TO_CONTROL = {"E_PCANALOGUE_LTRIGGER": 14, "E_PCANALOGUE_RTRIGGER": 15}

KS_PADS_PC_CPP = os.path.join(
    ROOT, "b5-decomp", "src", "GameShared", "GameClasses", "System", "Input", "PC",
    "CgsInputPadsPC.cpp")
KS_ACTIONS_H = os.path.join(
    ROOT, "b5-decomp", "src", "GameSource", "Input", "GameInputActions.h")


def read_console_table(image_path):
    """The 28 x 4 signed bytes at 0x82CDBEB8, big-endian image, offset = VA - 0x82000000."""
    off = KU_MAPPING_VA - KU_IMAGE_BASE
    with open(image_path, "rb") as f:
        f.seek(off)
        raw = f.read(KU_MAPPING_CONTROLS * 4)
    if len(raw) != KU_MAPPING_CONTROLS * 4:
        raise SystemExit("image too short for 0x%08X" % KU_MAPPING_VA)
    return [list(struct.unpack_from(">4b", raw, i * 4)) for i in range(KU_MAPPING_CONTROLS)]


def action_names():
    """id -> E_GAMEINPUTACTIONS_* from the owning header, for readable diffs."""
    out = {}
    try:
        text = open(KS_ACTIONS_H, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return out
    for name, value in re.findall(r"(E_GAMEINPUTACTIONS_[A-Z0-9_]+)\s*=\s*(-?\d+)", text):
        out.setdefault(int(value), name)
    return out


def pc_from_log(log_path):
    """The built exe's own dump: '[input-map] control 13 E_PADBUTTON_R1 -> actions 7,55,-1,25'."""
    if not log_path or not os.path.exists(log_path):
        return None, "no log"
    pat = re.compile(r"\[input-map\]\s+control\s+(\d+)\s+\S+\s+->\s+actions\s+([-\d,]+)")
    found = {}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pat.search(line)
            if m:
                found[int(m.group(1))] = [int(x) for x in m.group(2).split(",")]
    if len(found) < KU_MAPPING_CONTROLS:
        return None, "log has %d/%d [input-map] control lines" % (len(found), KU_MAPPING_CONTROLS)
    return [found.get(i, [-1, -1, -1, -1]) for i in range(KU_MAPPING_CONTROLS)], "runtime dump"


def pc_from_source(src_path):
    """Static parse of the legacy per-action KA_BINDINGS pad columns (the pre-fix shape)."""
    try:
        text = open(src_path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return None, "no source at %s" % src_path
    declared = source_declares_console_table(src_path)
    if declared is not None:
        # Post-fix shape: the leaf carries the console table itself, so THAT is the pad map.
        return declared, "in-source KA_DEFAULT_GAME_INPUT_MAPPING (%d rows)" % len(declared)
    body = re.search(r"KA_BINDINGS\[\]\s*=\s*\{(.*?)\n\s*\};", text, re.S)
    if not body:
        return None, "no KA_BINDINGS table in %s" % os.path.basename(src_path)
    names = {v: k for k, v in action_names().items()}
    per_control = [set() for _ in range(KU_MAPPING_CONTROLS)]
    rows = 0
    for line in body.group(1).splitlines():
        line = line.split("//")[0].strip()
        m = re.match(r"\{\s*([A-Za-z0-9_]+)\s*,\s*[A-Za-z0-9_]+\s*,\s*([A-Za-z0-9_]+)\s*,"
                     r"\s*([A-Za-z0-9_]+)\s*\}", line)
        if not m:
            continue
        rows += 1
        action, button, analogue = m.group(1), m.group(2), m.group(3)
        action_id = int(action) if re.fullmatch(r"-?\d+", action) else names.get(action)
        if action_id is None:
            continue
        control = KA_XPAD_NAME_TO_CONTROL.get(button)
        if control is not None:
            per_control[control].add(action_id)
        control = KA_ANALOGUE_NAME_TO_CONTROL.get(analogue)
        if control is not None:
            per_control[control].add(action_id)
    if rows == 0:
        return None, "KA_BINDINGS parsed to 0 rows (table shape changed?)"
    return [sorted(s) or [-1] for s in per_control], "static parse of KA_BINDINGS (%d rows)" % rows


def source_declares_console_table(src_path):
    """Post-fix invariant: if the leaf carries the console table verbatim, it must MATCH."""
    try:
        text = open(src_path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    body = re.search(r"KA_DEFAULT_GAME_INPUT_MAPPING\s*\[[^\]]*\]\s*\[[^\]]*\]\s*=\s*\{(.*?)\n\s*\};",
                     text, re.S)
    if not body:
        return None
    rows = []
    for line in body.group(1).splitlines():
        line = line.split("//")[0]
        m = re.search(r"\{\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\}", line)
        if m:
            rows.append([int(m.group(i)) for i in range(1, 5)])
    return rows or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="", help="a run's BrnGame.log (for the runtime dump)")
    ap.add_argument("--src", default=KS_PADS_PC_CPP)
    ap.add_argument("--image", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    image = args.image
    if not image:
        for cand in KA_IMAGE_CANDIDATES:
            if cand and os.path.exists(cand):
                image = cand
                break
    if not image or not os.path.exists(image):
        print("FAIL: no X360 image.bin (set BRN_IMAGE_BIN)")
        return 2

    console = read_console_table(image)
    names = action_names()

    pc, origin = pc_from_log(args.log)
    runtime = pc is not None
    if pc is None:
        why = origin
        pc, origin = pc_from_source(args.src)
        origin = "%s (%s)" % (origin, why) if pc is not None else why
    if pc is None:
        print("FAIL: could not build the PC pad map -- %s" % origin)
        return 2

    missing, extra = [], []
    for control in range(KU_MAPPING_CONTROLS):
        want = set(a for a in console[control] if a >= 0)
        have = set(a for a in pc[control] if a >= 0)
        for action in sorted(want - have):
            missing.append((control, action))
        for action in sorted(have - want):
            extra.append((control, action))

    # The subset a player can actually feel: the driving rows BridgeControllerToWorld reads
    # (0..13) and the GUI rows BridgeControllerToGui's scan tables admit (21, 37..59).
    def visible(action):
        return action <= 13 or action == 21 or 37 <= action <= 59
    headline = [(c, a) for c, a in missing if visible(a)]

    table_rows = source_declares_console_table(args.src)
    table_ok = None
    if table_rows is not None:
        table_ok = (table_rows == console)

    def label(control, action):
        return "%s(%d) -> %d %s" % (KA_CONTROL_NAMES[control], control, action,
                                    names.get(action, "?"))

    if args.json:
        print(json.dumps({
            "origin": origin, "runtime": runtime, "image": image,
            "console": console, "pc": pc,
            "missing": missing, "extra": extra, "headline": headline,
            "source_table_matches_image": table_ok,
        }, indent=1))
    else:
        print("[input-map] oracle  0x%08X in %s" % (KU_MAPPING_VA, image))
        print("[input-map] PC side: %s" % origin)
        for control in range(KU_MAPPING_CONTROLS):
            want = [a for a in console[control] if a >= 0]
            have = [a for a in pc[control] if a >= 0]
            gap = sorted(set(want) - set(have))
            print("  %-32s console %-16s pc %-16s %s"
                  % (KA_CONTROL_NAMES[control], ",".join(map(str, want)) or "-",
                     ",".join(map(str, have)) or "-",
                     ("MISSING " + ",".join(map(str, gap))) if gap else ""))
        if table_ok is not None:
            print("[input-map] in-source console table == image: %s" % table_ok)
        print("[input-map] missing %d (player-visible %d), extra %d"
              % (len(missing), len(headline), len(extra)))
        for control, action in headline:
            print("    MISSING  %s" % label(control, action))

    ok = runtime and not missing and not extra and (table_ok is not False)
    detail = []
    if not runtime:
        detail.append("no runtime [input-map] dump (%s)" % origin)
    if headline:
        detail.append("%d player-visible pad bindings the console has and the PC does not: %s"
                      % (len(headline), "; ".join(label(c, a) for c, a in headline[:12])))
    elif missing:
        detail.append("%d pad bindings missing" % len(missing))
    if extra:
        detail.append("%d pad bindings the console does not have: %s"
                      % (len(extra), "; ".join(label(c, a) for c, a in extra[:8])))
    if table_ok is False:
        detail.append("the in-source console table does NOT match the image")
    print("RESULT: %s -- %s" % ("PASS" if ok else "FAIL",
                                " | ".join(detail) if detail else "PC pad == console pad"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
