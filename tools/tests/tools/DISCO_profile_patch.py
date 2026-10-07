#!/usr/bin/env python3
"""DISCO_profile_patch.py -- seed a Profile.sav with "all but one event discovered".

Lane DISCO (gameplay wave GW4) save patcher. It edits the DISCOVERED bit (ProfileEvent flag 1) of
the profile's event records so a harness case can drive to the LAST undiscovered junction of a
type and witness the discovery rewards:
    discovery -> GameStateModule::CheckForAllEventsOfATypeFound -> action 203 -> GUI 313 -> HUD
    (and with --scope all also CheckForAllEventsBeingFound -> action 202 -> GUI 312 -> HUD).

THE CONTAINER (GameShared/GameClasses/Gui/PC/CgsSaveLoadPC.cpp, little-endian):
    312-byte header {magic 'B5SV' 0x42355356, version 1, imageSize, mugshotsSize,
                     payloadHash = FNV-1a over image bytes then mugshot bytes, reserved 0,
                     title[32], description[256]}
    then imageSize bytes of profile image, then mugshotsSize bytes of mugshots.
THE IMAGE (GameSource/GameState/Progression/BrnProfile_SaveImage.cpp):
    +616    s32 event count
    +28784  ProfileEvent[175], 8 bytes each: u32 muEventID (the event junction id), u16 muFlags,
            2 bytes pad.  Flag bit 0 = E_FLAG_DISCOVERED.
The profile's event table is in ProgressionData's junction-table order (checked by this tool
against PROGRESSION.DAT, and it must hold: CheckForAllEventsOfATypeFound pairs junction i with
profile event i). The junction's mode comes from its offline RaceEventData (+0xEC):
    0 RACE, 1 ROAD_RAGE, 2 STUNT_ATTACK, 3 SURVIVOR (marked man), 4 BURNING_ROUTE.

Usage (from the repo root):
    py tools\\tests\\tools\\DISCO_profile_patch.py --in <src.sav> --list
    py tools\\tests\\tools\\DISCO_profile_patch.py --in <src.sav> --out <dst.sav> \\
        --mode 2 --leave 480897 [--scope type|all]
    py tools\\tests\\tools\\DISCO_profile_patch.py --in <after.sav> --check 480897
        (prints the junction's flags and the per-mode discovered tally; exit 0 when discovered)

--scope type (default): every event of --mode is marked discovered except --leave, which is
cleared; other modes are untouched. --scope all: every event of every mode is marked discovered
except --leave. The source file is never written.
"""

import argparse
import os
import struct
import sys

HEADER = struct.Struct('<6I32s256s')
MAGIC = 0x42355356
IMAGE_EVENT_COUNT = 616
IMAGE_EVENTS = 28784
EVENT_STRIDE = 8
EVENT_CAPACITY = 175
FLAG_DISCOVERED = 1
FNV_SEED = 2166136261
FNV_PRIME = 16777619

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
DEFAULT_PROGRESSION = os.path.join(ROOT, 'build', 'game', 'PROGRESSION.DAT')
PROGRESSION_TYPE_ID = 65550
JUNCTION_STRIDE = 16           # EventJunction: muID, offline slot, online slot, shot group
EVENT_MODE = 0xEC              # RaceEventData::mu8Mode
MODE_NAMES = {0: 'RACE', 1: 'ROAD_RAGE', 2: 'STUNT_ATTACK', 3: 'SURVIVOR', 4: 'BURNING_ROUTE'}


def fnv1a(data, h=FNV_SEED):
    for byte in data:
        h = ((h ^ byte) * FNV_PRIME) & 0xFFFFFFFF
    return h


def read_container(path):
    d = open(path, 'rb').read()
    magic, ver, isz, msz, phash, _res, title, desc = HEADER.unpack_from(d, 0)
    if magic != MAGIC or ver != 1:
        raise SystemExit('%s: not a B5SV v1 container (magic %#x ver %d)' % (path, magic, ver))
    if len(d) != HEADER.size + isz + msz:
        raise SystemExit('%s: size %d != header %d + image %d + mugshots %d'
                         % (path, len(d), HEADER.size, isz, msz))
    image = bytearray(d[HEADER.size:HEADER.size + isz])
    mugs = d[HEADER.size + isz:]
    if fnv1a(mugs, fnv1a(image)) != phash:
        raise SystemExit('%s: payload hash mismatch (corrupt container)' % path)
    return dict(isz=isz, msz=msz, title=title, desc=desc, image=image, mugs=mugs)


def write_container(path, c):
    phash = fnv1a(c['mugs'], fnv1a(c['image']))
    hdr = HEADER.pack(MAGIC, 1, len(c['image']), len(c['mugs']), phash, 0, c['title'], c['desc'])
    with open(path, 'wb') as f:
        f.write(hdr)
        f.write(c['image'])
        f.write(c['mugs'])
    return phash


def profile_events(image):
    n = struct.unpack_from('<i', image, IMAGE_EVENT_COUNT)[0]
    if not 0 <= n <= EVENT_CAPACITY:
        raise SystemExit('event count %d out of range' % n)
    out = []
    for i in range(n):
        eid, flags = struct.unpack_from('<IH', image, IMAGE_EVENTS + i * EVENT_STRIDE)
        out.append([eid, flags])
    return out


def store_flags(image, index, flags):
    struct.pack_into('<H', image, IMAGE_EVENTS + index * EVENT_STRIDE + 4, flags)


def progression_junctions(path):
    """[(junction id, offline-event mode)] in ProgressionData junction-table order."""
    d = open(path, 'rb').read()
    magic, _ver, plat, _dbg, cnt, eoff, d0 = struct.unpack_from('<4sIIIIII', d, 0)
    if magic != b'bnd2' or plat != 4:
        raise SystemExit('%s: not a platform-4 (PC) bnd2 bundle' % path)
    payload = None
    for i in range(cnt):
        e = eoff + i * 0x40
        if struct.unpack_from('<I', d, e + 56)[0] != PROGRESSION_TYPE_ID:
            continue
        usz = struct.unpack_from('<I', d, e + 16)[0] & 0x0FFFFFFF
        doff = struct.unpack_from('<I', d, e + 40)[0]
        payload = d[d0 + doff:d0 + doff + usz]
        break
    if payload is None:
        raise SystemExit('%s: no ProgressionData resource' % path)
    w = struct.unpack_from('<20I', payload, 0)
    base, n = w[6], w[7]
    out = []
    for i in range(n):
        o = base + i * JUNCTION_STRIDE
        jid, offline = struct.unpack_from('<II', payload, o)
        mode = payload[offline + EVENT_MODE] if offline else None
        out.append((jid, mode))
    return out


def tally(events, modes):
    t = {}
    for (eid, flags), (_jid, mode) in zip(events, modes):
        a = t.setdefault(mode, [0, 0])
        a[1] += 1
        if flags & FLAG_DISCOVERED:
            a[0] += 1
    return t


def print_tally(t):
    for mode in sorted(t, key=lambda m: -1 if m is None else m):
        print('  mode %s %-14s discovered %3d / %3d' % (mode, MODE_NAMES.get(mode, '?'), t[mode][0], t[mode][1]))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--in', dest='src', required=True)
    ap.add_argument('--out')
    ap.add_argument('--progression', default=DEFAULT_PROGRESSION)
    ap.add_argument('--mode', type=int)
    ap.add_argument('--leave', type=int, help='junction id left undiscovered')
    ap.add_argument('--scope', choices=('type', 'all'), default='type')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--check', type=int, help='junction id that must now be discovered')
    args = ap.parse_args(argv)

    c = read_container(args.src)
    events = profile_events(c['image'])
    modes = progression_junctions(args.progression)
    if len(modes) != len(events) or any(e[0] != m[0] for e, m in zip(events, modes)):
        raise SystemExit('profile event order does not match the ProgressionData junction table '
                         '(%d events vs %d junctions)' % (len(events), len(modes)))
    by_id = {e[0]: i for i, e in enumerate(events)}

    if args.list:
        for i, ((eid, flags), (_j, mode)) in enumerate(zip(events, modes)):
            print('%3d junction %-7d mode %s %-14s flags %#06x%s' % (
                i, eid, mode, MODE_NAMES.get(mode, '?'), flags,
                ' DISCOVERED' if flags & FLAG_DISCOVERED else ''))
        print_tally(tally(events, modes))
        return 0

    if args.check is not None:
        if args.check not in by_id:
            raise SystemExit('junction %d not in the profile' % args.check)
        i = by_id[args.check]
        flags = events[i][1]
        print('junction %d (index %d, mode %s) flags %#06x discovered=%d' % (
            args.check, i, modes[i][1], flags, flags & FLAG_DISCOVERED))
        print_tally(tally(events, modes))
        return 0 if flags & FLAG_DISCOVERED else 1

    if args.out is None or args.leave is None or (args.scope == 'type' and args.mode is None):
        raise SystemExit('patching needs --out, --leave and (for --scope type) --mode')
    if os.path.abspath(args.out) == os.path.abspath(args.src):
        raise SystemExit('refusing to overwrite the source file')
    if args.leave not in by_id:
        raise SystemExit('junction %d not in the profile' % args.leave)
    li = by_id[args.leave]
    if args.scope == 'type' and modes[li][1] != args.mode:
        raise SystemExit('junction %d is mode %s, not %d' % (args.leave, modes[li][1], args.mode))

    changed = 0
    for i, ((eid, flags), (_j, mode)) in enumerate(zip(events, modes)):
        if i == li:
            new = flags & ~FLAG_DISCOVERED
        elif args.scope == 'all' or mode == args.mode:
            new = flags | FLAG_DISCOVERED
        else:
            new = flags
        if new != flags:
            store_flags(c['image'], i, new)
            events[i][1] = new
            changed += 1
    phash = write_container(args.out, c)
    c2 = read_container(args.out)           # round-trip: header, size and hash re-validated
    assert c2['image'] == c['image']
    print('wrote %s: %d event records changed, junction %d (index %d) left undiscovered, hash %#010x'
          % (args.out, changed, args.leave, li, phash))
    print_tally(tally(events, modes))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
