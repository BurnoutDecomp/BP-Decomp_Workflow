#!/usr/bin/env python3
"""PROPS/PROPPHYSICS.BUNDLE -- read the prop TYPE table, and DIFF the ported blob against the
shipped X360 one.

WHY THIS EXISTS (b5-decomp#2, "props are sent flying way too much when hit at medium/high
speed", 2026-09-07). A prop's whole response to being hit is `impulse / mass` and
`torque / inertia`, so "the impulse is right and the response is wrong" is exactly what a
mis-ported mass looks like -- the documented x64-widening-ghost shape in this project. The
prop-type table is a WIRE CONTRACT: PROPS/PROPPHYSICS.BUNDLE is consumed IN PLACE (the blob
*is* the BrnPhysics::Props::PropPhysicsDataHeader object), and
tools/assets/bundles/world_type_transcode.py::transcode_propphysics rewrites it from the
console's 4-byte-pointer form to the host's 8-byte one. Nothing else checks that rewrite, and
a silently wrong mfMass would never fail a compile, a link or a boot.

WHAT IT ANSWERS, in one command:
    python tools/diagnostics/prop_gazetteer.py            # both tables + the field-for-field diff
    python tools/diagnostics/prop_gazetteer.py --json out.json
    python tools/diagnostics/prop_gazetteer.py --selftest # NEGATIVE CONTROL: flip one mass byte
                                                          # in a COPY of the ported blob and show
                                                          # the diff firing on it

MEASURED 2026-09-07 (b5 9a9a91ec): 219 prop types on both sides, identical slot set, and
**0 differences across 219 slots x 14 fields**. The masses the game reads at runtime match:
the solver's own jacobian ([prop-solve] invmA/invmB, BRN_PROP_DIAG) reported 1/150, 1/250,
1/50 and 1/1 for the types this table calls 150 / 250 / 50 / 1 kg.

LAYOUTS are the committed b5-decomp header's, not guesses --
b5-decomp/src/SharedClasses/Physics/Props/BrnPhysicsPropTypeData.h carries both the console
column and the x64 static_asserts, and PropPhysicsDataHeader::FixUp @0x8267F570 attests the
two relocated pointer slots.

  header  (console -> host):  mapPropTypes[500] @0x10 (4 -> 8 byte offsets),
                              mapPropPartTypes[300] @0x7E0 -> @0xFB0,
                              mapVolumeTypes[2048] @0xC90 -> @0x1810,
                              muTimeStamp @0x2C90 -> @0x5810, size 0x2C94 -> 0x5818
  PropTypeData (stride 112 on BOTH):
      mJointLocator@0x00 mCOMOffset@0x10 mInertia@0x20 mResourceId@0x30(u64) mfMass@0x38
      maCollisionVolumes@0x3C->0x40  maParts@0x40->0x48  mfSphereRadius@0x44->0x50
      mfMaxJointAngleCos@0x48->0x54  mfLeanThreshold@0x4C->0x58  mfMoveThreshold@0x50->0x5C
      mfSmashThreshold@0x54->0x60    muSceneUriId@0x58->0x64     muMaxState@0x5C->0x68
      muNumberOfParts@0x5D->0x69     muNumberOfVolumes@0x5E->0x6A mu8JointType@0x5F->0x6B
      mu8ExtraTypeInfo@0x60->0x6C

⚠️ mInertia (+0x20) is AUTHORED IN THE FILE AND DEAD IN THIS BUILD. PropManager::GetPropInertia
@0x82612640 does NOT read it: it folds a solid-box tensor out of the collision volumes' own
half-extents (and, for the two HACKShouldMoveComOffset lamppost uris 428364/428388, out of
K_LAMPOST_INERTIA_BOX == (2,1,2), re-read from the image this session at dyn-init thunk
0x82C5EAC8 -> 0x82FB9420, lanes flt_82001D9C=2.0 / flt_82001C98=1.0). The DecFIGS dwarfdump
has no PropTypeData::GetInertia call site either. Reported so nobody "fixes" the recon to use
the authored value -- the console's own instruction is the box fold.
"""
import argparse, collections, io, json, os, struct, sys, zlib

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORTED = os.path.join(REPO, "build", "game", "PROPS", "PROPPHYSICS.BUNDLE")

FIELDS = ["mass", "inertia", "com", "sphereR", "cosA", "lean", "move", "smash",
          "uri", "maxState", "nParts", "nVols", "jointType", "extra"]


def _x360_root():
    """build.config.toml's x360_root -- the shipped console game folder."""
    cfg = os.path.join(REPO, "build.config.toml")
    if not os.path.exists(cfg):
        return None
    for line in open(cfg, encoding="utf-8", errors="replace"):
        if line.strip().startswith("x360_root"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _entry(d, be):
    """bnd2 v2: return (blob_bytes, base_offset). Decompresses a zlib'd console resource."""
    F = ">" if be else "<"
    ent_off = struct.unpack_from(F + "I", d, 0x14)[0]
    data0 = struct.unpack_from(F + "I", d, 0x18)[0]
    csize = struct.unpack_from(F + "3I", d, ent_off + 0x1C)[0]
    disk = struct.unpack_from(F + "3I", d, ent_off + 0x28)[0]
    raw = d[data0 + disk: data0 + disk + csize] if csize else d[data0 + disk:]
    if raw[:1] == b"\x78":                      # zlib -- the console bundles are compressed
        return zlib.decompress(raw), 0
    return d, data0 + disk


def read_table(path, be):
    """One row per populated prop-type slot. `be` selects the console (big-endian, 4-byte
    pointers) vs the ported (little-endian, 8-byte) layout."""
    d, base = _entry(open(path, "rb").read(), be)
    F = ">" if be else "<"
    ptr = 4 if be else 8
    # field offsets that move with the widening
    o = dict(vols=0x3C, parts=0x40, R=0x44, cos=0x48, lean=0x4C, move=0x50, smash=0x54,
             uri=0x58, st=0x5C) if be else \
        dict(vols=0x40, parts=0x48, R=0x50, cos=0x54, lean=0x58, move=0x5C, smash=0x60,
             uri=0x64, st=0x68)
    rows = []
    for i in range(500):
        off = struct.unpack_from(F + ("I" if be else "Q"), d, base + 0x10 + ptr * i)[0]
        if off == 0:
            continue
        p = base + off
        if p + 112 > len(d):
            print("  slot %d: offset 0x%X out of range" % (i, off), file=sys.stderr)
            continue
        f = lambda k: struct.unpack_from(F + "f", d, p + o[k])[0]
        rows.append(dict(
            slot=i,
            mass=struct.unpack_from(F + "f", d, p + 0x38)[0],
            inertia=[round(x, 4) for x in struct.unpack_from(F + "4f", d, p + 0x20)[:3]],
            com=[round(x, 4) for x in struct.unpack_from(F + "4f", d, p + 0x10)[:3]],
            sphereR=f("R"), cosA=f("cos"), lean=f("lean"), move=f("move"), smash=f("smash"),
            uri=struct.unpack_from(F + "I", d, p + o["uri"])[0],
            maxState=d[p + o["st"]], nParts=d[p + o["st"] + 1], nVols=d[p + o["st"] + 2],
            jointType=d[p + o["st"] + 3], extra=d[p + o["st"] + 4]))
    return rows


def diff(a, b):
    A = {r["slot"]: r for r in a}
    B = {r["slot"]: r for r in b}
    out = []
    if set(A) != set(B):
        out.append("SLOT SETS DIFFER: x360 has %d, ported has %d, symmetric difference %s"
                   % (len(A), len(B), sorted(set(A) ^ set(B))[:20]))
    for s in sorted(set(A) & set(B)):
        for k in FIELDS:
            if A[s][k] != B[s][k]:
                out.append("slot %-3d %-10s x360=%s ported=%s" % (s, k, A[s][k], B[s][k]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write the ported table here")
    ap.add_argument("--selftest", action="store_true",
                    help="negative control: corrupt one mass in a COPY and show the diff bite")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    ported = read_table(PORTED, be=False)
    root = _x360_root()
    console = os.path.join(root, "PROPS", "PROPPHYSICS.BUNDLE") if root else None

    if not args.quiet:
        hist = collections.Counter(round(r["mass"], 3) for r in ported)
        print("ported %s: %d prop types" % (PORTED, len(ported)))
        print("  mass histogram: " + ", ".join("%g kg x%d" % kv for kv in sorted(hist.items())))
        print("  joint types:    " + str(dict(collections.Counter(r["jointType"] for r in ported))))
        print("  move thresholds (mph): " +
              str(dict(collections.Counter(round(r["move"], 2) for r in ported))))

    if args.json:
        json.dump(ported, open(args.json, "w"), indent=1)
        print("  -> %s" % args.json)

    if not console or not os.path.exists(console):
        print("\nNO X360 SOURCE BUNDLE (build.config.toml x360_root=%r) -- diff skipped." % root)
        return 0

    x360 = read_table(console, be=True)
    print("\nX360 %s: %d prop types" % (console, len(x360)))
    d = diff(x360, ported)
    print("DIFF x360 vs ported: %d difference(s) across %d slots x %d fields"
          % (len(d), len(x360), len(FIELDS)))
    for line in d[:40]:
        print("   " + line)

    if args.selftest:
        # NEGATIVE CONTROL, through the real reader: flip the first prop type's mass in a copy
        # of the ported blob and prove the diff reports it. A checker nobody has seen FAIL is
        # not a checker.
        import tempfile
        blob = bytearray(open(PORTED, "rb").read())
        base = _entry(bytes(blob), False)[1]
        off = struct.unpack_from("<Q", blob, base + 0x10 + 8 * ported[0]["slot"])[0]
        struct.pack_into("<f", blob, base + off + 0x38, 12345.0)
        tmp = os.path.join(tempfile.gettempdir(), "PROPPHYSICS.selftest.BUNDLE")
        open(tmp, "wb").write(bytes(blob))
        bad = read_table(tmp, be=False)
        dd = diff(x360, bad)
        print("\nSELFTEST (mass of slot %d forced to 12345.0 in a copy):" % ported[0]["slot"])
        for line in dd[:5]:
            print("   " + line)
        print("   -> %d difference(s) reported. The control %s."
              % (len(dd), "BITES" if dd else "DID NOT BITE -- the checker is blind"))
        os.remove(tmp)
        return 0 if dd else 1

    return 1 if d else 0


if __name__ == "__main__":
    sys.exit(main())
