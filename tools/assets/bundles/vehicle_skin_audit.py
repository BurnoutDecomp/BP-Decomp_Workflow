#!/usr/bin/env python3
"""vehicle_skin_audit -- does the PORTED vehicle mesh still carry the console's SKINNING?

WHY THIS EXISTS
    g_verletOffsets[128] is the only thing that moves a vehicle vertex.  The shipped PC
    vertex program (SHADERS.BNDL, 16 vs_3_0 programs declare it) computes

        pos = position + blendWeight.y * g_verletOffsets[blendIndex.y]
                       + blendWeight.x * g_verletOffsets[blendIndex.x]

    -- and note what that means: **the weights scale the OFFSET, not the position**.  Blend
    weights that do not sum to 1, or an index/weight pair that came apart in the port, would
    stretch or shrink the DEFORMATION while leaving the REST POSE perfectly intact.  Every
    deformation audit before this one tested the rest pose, so that whole failure mode was
    invisible: a car would measure exact at rest and smear its panels in a crash.

    BLENDINDICES is X360 D3DDECLTYPE_UBYTE4 (0x1A2286) and BLENDWEIGHT is UBYTE4N
    (0x1A2086) -- four bytes inside ONE dword, which renderable_transcode flips AS A DWORD
    (X360_DECLTYPE_LANES maps both to lane width 4, count 1).  That is the textbook
    mixed-width byteswap hazard, and this project has already shipped one (visualfxsurface
    flipped as uniform dwords, so no road could lay a tyre mark).  So it gets measured, not
    reasoned about.

WHAT IT COMPARES
    For every mesh in a car's VEH_<code>_GR.BIN whose merged VertexDescriptor set carries
    BOTH usage 2 (BLENDINDICES) and usage 1 (BLENDWEIGHT), every vertex, retail X360 bytes
    against the shipped PC bytes:
      T1 sum255    the four weight bytes sum to 255, on BOTH sides (permutation-invariant,
                   so it tests VALUE integrity and nothing else).
      T2 ordered   the ordered lane tuple ((i0,w0)..(i3,w3)) is identical.  A BE->LE port of
                   a packed dword is a lane reversal BY CONSTRUCTION, so T2 differing is
                   EXPECTED; what matters is that C2 below shows the difference is exactly a
                   consistent 4-byte reversal of both elements.
      T3 multiset  the unordered set {(i,w)} is identical -- permutation-BLIND on purpose.
                   T2 without T3 = a permutation; neither = corruption.
      T4 lanemask  WHICH lanes carry the non-zero weights, per side.  The shader reads .x
                   and .y only, so the live pair must land in lanes 0,1 of the DELIVERED
                   register.  This is the test that separates a correct reversal from one
                   that parks the influences in .z/.w (where they would be multiplied by
                   nothing and the car would not deform at all).
      T5 idxrange  every index < the car's verlet row count.

    --rows also joins the AT spec: rows = (# tags with mbSkinnedPoint) + SUM(part
    GetNumberOfDrivenPoints()), which is exactly what UpdateSkinningOffsets @0x825DFA90
    produces, against the mesh's max BLENDINDEX.  A mesh that indexes above that reads a row
    nothing ever writes.

    --tags checks the invariant the row-map banner flagged as data-dependent: two functions
    write maVerletOffsets_Scratch with two numberings -- UpdateSkinningOffsets uses the DENSE
    PACKED row, UpdateIKSuspensionOffsets @0x825E1CE0 uses the RAW TAG INDEX (`slwi r11,r8,5`,
    attested on both consoles).  They agree only if every unskinned tag sits after every
    skinned one.

MEASURED, 2026-09-07 (so nobody re-derives it)
    * 430/430 shipped VEHICLES/*_GR.BIN and 138/138 WHEELS/*_GR.BNDL are platform 4 with a
      retail twin -- the vehicle-graphics conversion is COMPLETE, not the 76/430 the older
      note records.
    * 430 cars, 144,958 renderable meshes of which 144,143 are skinned (the other 815 report
      "no blend pair" instead of a number -- the instrument declines rather than decoding),
      20,475,516 skinned vertices compared:
          multiset differences        0
          out-of-range indices        0
          weight-sum != 255      16,180 per side (0.079%) and ZERO of them asymmetric --
                                 every one fails identically on X360 and PC, so it is the
                                 console's own authoring (those vertices sum to 256, not to
                                 something wild; e.g. PEULM01 750 of 58,577)
          lanemask X360   0b1100 x 19,657,114  +  0b1000 x 818,402
          lanemask PC     0b0011 x 19,657,114  +  0b0001 x 818,402   (an exact mirror)
    * The port's transform is a CONSISTENT 4-byte reversal of BOTH elements: X360 lane mask
      0b1100 (live pair in memory bytes 2,3) -> PC 0b0011 (memory bytes 0,1).  D3D9 UBYTE4N
      delivers memory byte 0 as .x, so the live pair lands in .x/.y -- the two lanes the
      program reads.  The console must be delivering memory byte 3 as .x (an 8-in-32 fetch
      swap) or no X360 car would ever deform, so the reversal is not just consistent, it is
      the RIGHT one, lane for lane.
    * X360 VS 274C49FB microcode vs its PC twin, instruction for instruction:
        X360  trunc r5.xy, r1.xy | maxas a0<-r5.y | mul r1, r3.yyyy, c30[a0]
                                 | maxas a0<-r5.x | mad r5, r3.xxxx, c30[a0], r1 | add position
        PC    mova a0.xy, r0.yx  | mul r0.xyz, v4.y, c0[a0.x]
                                 | mad r0.xyz, c0[a0.y], v4.x, r0 | add r0.xyz, r0, v0
      Same formula, same lanes, same order, and neither side deforms the NORMAL.  The X360
      CTAB puts g_verletOffsets at c30 x128, the PC recompile at c0 x128 -- different
      register allocation, same declaration; the engine binds by NAME through
      GetVariableHandleByName so the move is handled.
    * Rows: on all 430 cars, mesh maxIndex + 1 == spec rows EXACTLY -- no overrun and no
      slack either.  Row histogram spans 22..128 (128 on 107 cars, 127 on 103, 126 on 83).
      Controls: asking the same predicate with rows-1 flags all 430 (so the match is tight,
      not vacuous), and joining each car's rows against a DIFFERENT car's mesh flags 75/430
      (shift by one) and 177/430 (random permutation), so the exact match is car-specific
      and not a coincidence of every car having about 126 rows.
    * Tags: all 430 cars have exactly FOUR unskinned tag points and they ARE the four wheel
      tags, always the last four.  So packed row == raw tag index for every skinned tag on
      every car -- and UpdateIKSuspensionOffsets' raw-indexed scratch write is gated on
      `lpSpec->IsSkinned()`, which no retail wheel tag satisfies, so the two writers cannot
      collide on any shipped car.
    => THE VEHICLE-MESH SKINNING PORT IS FAITHFUL.  A "the panels stretch" report is not
    this.

USAGE
    py tools/assets/bundles/vehicle_skin_audit.py --car PUSMC01        # one car, full census
    py tools/assets/bundles/vehicle_skin_audit.py --fleet              # all 430
    py tools/assets/bundles/vehicle_skin_audit.py --rows               # spec rows vs mesh idx
    py tools/assets/bundles/vehicle_skin_audit.py --tags               # the two-writer invariant
    py tools/assets/bundles/vehicle_skin_audit.py --platform           # the port-completeness sweep
    py tools/assets/bundles/vehicle_skin_audit.py --selftest           # negative controls
Set BRN_X360_ROOT to point at a different retail set.

⚠️ A NOTE ON AN INSTRUMENT THAT LIED, because it cost this wave time.  The first cut of the
--rows check resolved each mesh's VertexDescriptor by matching STRIDE, because the import
table is not in the payload bytes.  It picked the wrong descriptor and reported maxIndex ==
255 for EVERY car -- a uniform, confident, wrong number.  The descriptors here are resolved
through YAP's real import sidecars.  If you ever re-implement the payload walk without YAP,
cross-check one car against this path before believing it.
"""
import argparse
import collections
import os
import shutil
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import renderable_transcode as RT                                   # noqa: E402
from vehicle_transcode import GAME, RETAIL, YAP, PortError, read_bnd2   # noqa: E402
from vehicleattrib_transcode import read_bundle                     # noqa: E402

T_DEFORM = 65564
USAGE_BLENDWEIGHT = 1
USAGE_BLENDINDICES = 2
T_UBYTE4 = 0x1A2286
T_UBYTE4N = 0x1A2086
KU_MAX_VERLET_POINTS = 128
KU_WHEELS_BASE = 80
KU_WHEEL_STRIDE = 48


# ---------------------------------------------------------------------------
# descriptors + renderable headers
# ---------------------------------------------------------------------------
def parse_vd_elements(vd, end):
    u16 = lambda o: struct.unpack_from(end + 'H', vd, o)[0]
    u32 = lambda o: struct.unpack_from(end + 'I', vd, o)[0]
    n = u16(0x08)
    return vd[0x10 + 16 * n], [(vd[e + 9], vd[e + 10], u16(e + 2), u32(e + 4))
                               for e in (0x10 + 16 * i for i in range(n))]


def load_vds(root, end):
    out = {}
    d = os.path.join(root, 'VertexDescriptor')
    for f in sorted(os.listdir(d)):
        if f.lower().endswith('.dat'):
            out[int(f[:-4], 16)] = (open(os.path.join(d, f), 'rb').read(), end)
    return out


def skin_pair(vd_lookup, rids):
    """Merge a mesh's descriptors -> (stride, idx_off, wgt_off), or None when the mesh is
    not skinned. Never guesses: an unexpected declaration type raises rather than decoding."""
    stride = idx_off = wgt_off = None
    for rid in rids:
        if rid is None or rid not in vd_lookup:
            continue
        vd, end = vd_lookup[rid]
        s, els = parse_vd_elements(vd, end)
        if stride is None:
            stride = s
        elif s != stride:
            raise PortError('descriptor stride disagreement %d vs %d' % (s, stride))
        for usage, uidx, off, ty in els:
            if usage == USAGE_BLENDINDICES and uidx == 0:
                if ty != T_UBYTE4:
                    raise PortError('BLENDINDICES decl type 0x%06X, expected UBYTE4' % ty)
                idx_off = off if idx_off is None else idx_off
            elif usage == USAGE_BLENDWEIGHT and uidx == 0:
                if ty != T_UBYTE4N:
                    raise PortError('BLENDWEIGHT decl type 0x%06X, expected UBYTE4N' % ty)
                wgt_off = off if wgt_off is None else wgt_off
    if idx_off is None or wgt_off is None:
        return None
    return (stride, idx_off, wgt_off)


def meshes_x360(header, imports):
    p = RT.parse_renderable(header, imports)
    return [dict(vd=m['vd_imports'], vb=[list(v) for v in m['vb_headers']]) for m in p.meshes]


def meshes_pc(header, imports):
    """The x64 widened form emitted by renderable_transcode.emit_x64."""
    num = struct.unpack_from('<H', header, 0x12)[0]
    tab = struct.unpack_from('<Q', header, 0x18)[0]
    out = []
    for mi in range(num):
        base = struct.unpack_from('<Q', header, tab + 8 * mi)[0]
        num_vd, num_vb = header[base + 0x28], header[base + 0x2A]
        vbs = []
        for vi in range(num_vb):
            off = struct.unpack_from('<Q', header, base + 0x38 + 8 * vi)[0]
            vbs.append(list(struct.unpack_from('<10I', header, off)))
        vds = [imports.get(base + 0x30 + 8 * (1 + num_vb) + 8 * di) for di in range(num_vd)]
        out.append(dict(vd=vds, vb=vbs))
    return out


def read_imports(path):
    try:
        return RT.parse_imports_yaml(open(path).read())
    except IOError:
        return {}


# ---------------------------------------------------------------------------
# the comparator
# ---------------------------------------------------------------------------
class Tally(object):
    def __init__(self):
        self.meshes = self.skinned = self.no_pair = self.verts = 0
        self.bad_sum = [0, 0]
        self.sum_hist = [collections.Counter(), collections.Counter()]
        self.lanemask = [collections.Counter(), collections.Counter()]
        self.nz = [collections.Counter(), collections.Counter()]
        self.idx_max = [-1, -1]
        self.idx_oob = [0, 0]
        self.ordered_bad = self.multiset_bad = 0
        self.examples = []


def _compare(a, b, base, stride, io, wo, n, rows, t, label, damage=None):
    for v in range(n):
        o = base + v * stride
        ai, aw = a[o + io:o + io + 4], a[o + wo:o + wo + 4]
        bi, bw = bytearray(b[o + io:o + io + 4]), bytearray(b[o + wo:o + wo + 4])
        if damage:
            damage(bi, bw)
        t.verts += 1
        for side, (ii, ww) in enumerate(((ai, aw), (bi, bw))):
            s = sum(ww)
            t.sum_hist[side][s] += 1
            if s != 255:
                t.bad_sum[side] += 1
            mask = 0
            for k in range(4):
                if ww[k]:
                    mask |= 1 << k
            t.lanemask[side][mask] += 1
            t.nz[side][bin(mask).count('1')] += 1
            for k in range(4):
                if ww[k] or k < 2:
                    t.idx_max[side] = max(t.idx_max[side], ii[k])
                    if ii[k] >= rows:
                        t.idx_oob[side] += 1
        ao, bo = tuple(zip(ai, aw)), tuple(zip(bi, bw))
        if ao != bo:
            t.ordered_bad += 1
            if len(t.examples) < 6:
                t.examples.append('%s v%d  X360 %s  PC %s' % (label, v, ao, bo))
        if collections.Counter(ao) != collections.Counter(bo):
            t.multiset_bad += 1


def audit_dirs(x360_dir, pc_dir, rows=KU_MAX_VERLET_POINTS, damage=None):
    xvd, pvd = load_vds(x360_dir, '>'), load_vds(pc_dir, '<')
    t = Tally()
    rx, rp = os.path.join(x360_dir, 'Renderable'), os.path.join(pc_dir, 'Renderable')
    for name in sorted(f[:-len('_header.dat')] for f in os.listdir(rx)
                       if f.endswith('_header.dat')):
        hx = open(os.path.join(rx, name + '_header.dat'), 'rb').read()
        hp = open(os.path.join(rp, name + '_header.dat'), 'rb').read()
        bx = open(os.path.join(rx, name + '_body.dat'), 'rb').read()
        bp = open(os.path.join(rp, name + '_body.dat'), 'rb').read()
        mx = meshes_x360(hx, read_imports(os.path.join(rx, name + '_header.dat_imports.yaml')))
        mp = meshes_pc(hp, read_imports(os.path.join(rp, name + '_header.dat_imports.yaml')))
        if len(mx) != len(mp):
            raise PortError('%s: mesh count %d vs %d' % (name, len(mx), len(mp)))
        for mi, (a, b) in enumerate(zip(mx, mp)):
            t.meshes += 1
            pa, pb = skin_pair(xvd, a['vd']), skin_pair(pvd, b['vd'])
            if pa is None or pb is None:
                if pa != pb:
                    raise PortError('%s mesh %d: skin pair on one side only' % (name, mi))
                t.no_pair += 1
                continue
            if pa != pb:
                raise PortError('%s mesh %d: descriptors disagree across the port %r %r'
                                % (name, mi, pa, pb))
            t.skinned += 1
            stride, io, wo = pa
            for vi, vb in enumerate(a['vb']):
                if vb != b['vb'][vi]:
                    raise PortError('%s mesh %d vb %d: header differs' % (name, mi, vi))
                _compare(bx, bp, vb[6] & ~3, stride, io, wo, vb[8] // stride, rows, t,
                         '%s/m%d/vb%d' % (name, mi, vi), damage)
    return t


def report(t, rows, title):
    print('==== %s ====' % title)
    print('  meshes %d (skinned %d, no blend pair %d)   vertices %d'
          % (t.meshes, t.skinned, t.no_pair, t.verts))
    print('  T1 sum!=255      X360 %d  PC %d' % (t.bad_sum[0], t.bad_sum[1]))
    for s, lbl in ((0, 'X360'), (1, 'PC  ')):
        print('     sums %s %s' % (lbl, dict(sorted(t.sum_hist[s].items())[:6])))
    print('  T2 ordered diff  %d  %s' % (t.ordered_bad,
                                         'IDENTICAL' if not t.ordered_bad else 'DIFFERS (expected: BE->LE lane reversal)'))
    print('  T3 multiset diff %d  %s' % (t.multiset_bad,
                                         'IDENTICAL' if not t.multiset_bad else '*** CORRUPT ***'))
    for s, lbl in ((0, 'X360'), (1, 'PC  ')):
        print('  T4 lanemask %s %s   nz %s' % (lbl,
              {bin(m): c for m, c in sorted(t.lanemask[s].items())}, dict(sorted(t.nz[s].items()))))
    for s, lbl in ((0, 'X360'), (1, 'PC  ')):
        print('  T5 idx %s max %d  >=%d: %d' % (lbl, t.idx_max[s], rows, t.idx_oob[s]))
    for e in t.examples:
        print('     e.g. %s' % e)
    ok = (t.bad_sum[0] == t.bad_sum[1] and not t.multiset_bad and t.idx_oob == [0, 0]
          and t.skinned > 0)
    print('  VERDICT: %s' % ('PASS' if ok else 'FAIL'))
    return ok


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------
def extract_pair(gr_name, tmp):
    a, b = os.path.join(tmp, 'x'), os.path.join(tmp, 'p')
    for d in (a, b):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    for src, dst in ((os.path.join(RETAIL, 'VEHICLES', gr_name), a),
                     (os.path.join(GAME, 'VEHICLES', gr_name), b)):
        r = subprocess.run([YAP, 'e', src, dst], capture_output=True, text=True)
        if r.returncode != 0:
            raise PortError('YAP failed on %s: %s' % (src, (r.stdout + r.stderr)[-200:]))
    return a, b


# ---------------------------------------------------------------------------
# spec-side walks
# ---------------------------------------------------------------------------
def _be32(b, o):
    return struct.unpack_from('>I', b, o)[0]


def _bes32(b, o):
    return struct.unpack_from('>i', b, o)[0]


def spec_walk(blob, invert=False):
    """-> (flags, skinned, unskinned, packedRow, wheelTagIndices, nTag, drivenSum)."""
    if _bes32(blob, 0) != 1:
        raise PortError('miVersionNumber != 1 -- not a big-endian StreamedDeformationSpec')
    tag_off, n_tag = _be32(blob, 4), _bes32(blob, 8)
    ik_off, n_ik = _be32(blob, 20), _bes32(blob, 24)
    flags = [bool(blob[tag_off + 80 * i + 65]) for i in range(n_tag)]
    if invert:
        flags = [not f for f in flags]
    packed, r = {}, 0
    for i, f in enumerate(flags):
        if f:
            packed[i] = r
            r += 1
    driven = sum(_bes32(blob, ik_off + 480 * i + 464) for i in range(n_ik))
    wheels = [_bes32(blob, KU_WHEELS_BASE + KU_WHEEL_STRIDE * w + 32) for w in range(4)]
    return (flags, [i for i, f in enumerate(flags) if f],
            [i for i, f in enumerate(flags) if not f], packed, wheels, n_tag, driven)


def car_spec(code):
    b = read_bundle(os.path.join(RETAIL, 'VEHICLES', 'VEH_%s_AT.BIN' % code))
    ds = [e['data'] for e in b['entries'] if e['type'] == T_DEFORM]
    if len(ds) != 1:
        raise PortError('%s: %d deformation specs' % (code, len(ds)))
    return ds[0]


def car_codes():
    return sorted(f[4:-7] for f in os.listdir(os.path.join(GAME, 'VEHICLES'))
                  if f.upper().endswith('_GR.BIN'))


# ---------------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------------
def do_platform():
    ok = True
    for sub, suffix in (('VEHICLES', '_GR.BIN'), ('WHEELS', '_GR.BNDL')):
        g, r = os.path.join(GAME, sub), os.path.join(RETAIL, sub)
        shipped = sorted(f for f in os.listdir(g) if f.upper().endswith(suffix))
        retail = sorted(f for f in os.listdir(r) if f.upper().endswith(suffix))
        plat, bad = {}, []
        for f in shipped:
            try:
                p = read_bnd2(os.path.join(g, f))['platform']
            except PortError as e:
                bad.append((f, str(e)))
                continue
            plat[p] = plat.get(p, 0) + 1
            if p != 4:
                bad.append((f, 'platform %d' % p))
        missing = set(x.upper() for x in retail) - set(x.upper() for x in shipped)
        print('%-9s shipped %-4d retail %-4d  platforms %s  missing %d  bad %d'
              % (sub, len(shipped), len(retail), plat, len(missing), len(bad)))
        for f, why in bad[:10]:
            print('    BAD %s: %s' % (f, why))
        ok &= not bad and not missing
    print('VERDICT: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def do_rows():
    bad, slack, hist = [], [], {}
    tmp = tempfile.mkdtemp(prefix='vehskin_')
    try:
        for code in car_codes():
            _, sk, un, _, _, n_tag, driven = spec_walk(car_spec(code))
            rows = len(sk) + driven
            hist[rows] = hist.get(rows, 0) + 1
            a, b = extract_pair('VEH_%s_GR.BIN' % code, tmp)
            t = audit_dirs(a, b, KU_MAX_VERLET_POINTS)
            mi = max(t.idx_max)
            flag = ''
            if mi >= rows or rows > KU_MAX_VERLET_POINTS:
                flag = ' ***'
                bad.append((code, rows, mi))
            elif mi + 1 < rows:
                slack.append((code, rows, mi))
            print('%-12s tags=%-4d skinned=%-4d driven=%-4d rows=%-4d maxIdx=%-4d%s'
                  % (code, n_tag, len(sk), driven, rows, mi, flag), flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('  mesh reads an unwritten row: %d %s' % (len(bad), bad[:8]))
    print('  spare rows (not a failure):  %d %s' % (len(slack), slack[:6]))
    print('  rows histogram %s' % sorted(hist.items()))
    print('  VERDICT: %s' % ('PASS' if not bad else 'FAIL'))
    return not bad


def do_tags(invert=False):
    bad, have_un, wheel_un, wheel_bad, exact = [], 0, 0, 0, 0
    hist = collections.Counter()
    codes = car_codes()
    for code in codes:
        flags, sk, un, packed, wheels, n_tag, _ = spec_walk(car_spec(code), invert)
        hist[len(un)] += 1
        if un:
            have_un += 1
        if sk and un and max(sk) > min(un):
            bad.append((code, n_tag, len(sk), min(i for i in un if i < max(sk))))
        for w in wheels:
            if not (0 <= w < n_tag):
                wheel_bad += 1
            elif not flags[w]:
                wheel_un += 1
        if set(un) == set(w for w in wheels if 0 <= w < n_tag):
            exact += 1
    print('  cars                                 %d' % len(codes))
    print('  cars with any unskinned tag          %d  (if 0 the test is vacuous)' % have_un)
    print('  unskinned-count histogram            %s' % dict(hist))
    print('  unskinned set IS the four wheel tags %d' % exact)
    print('  wheel tags that are UNSKINNED        %d  (the raw-index scratch write in'
          '\n                                          UpdateIKSuspensionOffsets is gated on'
          '\n                                          IsSkinned(), so those never collide)' % wheel_un)
    print('  wheel tag index out of range         %d' % wheel_bad)
    print('  two writers DISAGREE on             %d cars %s' % (len(bad), bad[:8]))
    print('  VERDICT: %s' % ('PASS' if not bad else 'FAIL'))
    return not bad


def do_fleet():
    tot = collections.Counter()
    lanes = [collections.Counter(), collections.Counter()]
    fails = []
    tmp = tempfile.mkdtemp(prefix='vehskin_')
    try:
        for gr in sorted(f for f in os.listdir(os.path.join(GAME, 'VEHICLES'))
                         if f.upper().endswith('_GR.BIN')):
            a, b = extract_pair(gr, tmp)
            t = audit_dirs(a, b, KU_MAX_VERLET_POINTS)
            bad = (t.bad_sum[0] != t.bad_sum[1] or t.multiset_bad or t.idx_oob != [0, 0]
                   or t.skinned == 0)
            if bad:
                fails.append(gr)
            for k, v in (('cars', 1), ('meshes', t.meshes), ('skinned', t.skinned),
                         ('nopair', t.no_pair), ('verts', t.verts),
                         ('badsumX', t.bad_sum[0]), ('badsumP', t.bad_sum[1]),
                         ('multiset', t.multiset_bad), ('oob', sum(t.idx_oob))):
                tot[k] += v
            for s in (0, 1):
                lanes[s].update(t.lanemask[s])
            print('%-28s %s meshes=%-4d verts=%-7d sum!=255=%s multiset=%d oob=%s maxIdx=%d'
                  % (gr, 'FAIL' if bad else 'ok  ', t.meshes, t.verts, t.bad_sum,
                     t.multiset_bad, t.idx_oob, max(t.idx_max)), flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    print('==== FLEET TOTALS ====')
    for k in ('cars', 'meshes', 'skinned', 'nopair', 'verts', 'badsumX', 'badsumP',
              'multiset', 'oob'):
        print('  %-9s %d' % (k, tot[k]))
    print('  lanemask X360 %s' % {bin(m): c for m, c in sorted(lanes[0].items())})
    print('  lanemask PC   %s' % {bin(m): c for m, c in sorted(lanes[1].items())})
    print('  cars failing  %d %s' % (len(fails), fails[:10]))
    print('  VERDICT: %s' % ('PASS' if not fails else 'FAIL'))
    return not fails


def do_selftest(code='PUSMC01'):
    """The comparator must BITE. Pre-registered expectations printed before each run."""
    tmp = tempfile.mkdtemp(prefix='vehskin_')
    try:
        a, b = extract_pair('VEH_%s_GR.BIN' % code, tmp)
        report(audit_dirs(a, b), KU_MAX_VERLET_POINTS, 'LIVE %s' % code)

        def rev_w(i, w):
            w[:] = w[::-1]

        def rev_both(i, w):
            i[:], w[:] = i[::-1], w[::-1]

        def bump(i, w):
            w[0] = (w[0] + 1) & 0xFF

        for fn, name, expect in (
                (rev_w, 'C1 weights-only reversal', 'T2 AND T3 must fire'),
                (rev_both, 'C2 consistent reversal of BOTH (undoes the port)',
                 'T2 and T3 must BOTH pass, and the PC lanemask must return to the X360 one '
                 '-- that is the proof the port is exactly a consistent 4-byte reversal'),
                (bump, 'C3 +1 on weight byte 0', 'T1 must fire on every vertex')):
            print()
            print('  [%s] expect: %s' % (name, expect))
            report(audit_dirs(a, b, damage=fn), KU_MAX_VERLET_POINTS, name)

        print()
        print('  [C4 --tags with the skinned flag INVERTED] expect: nearly every car flags')
        do_tags(invert=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--car')
    ap.add_argument('--fleet', action='store_true')
    ap.add_argument('--rows', action='store_true')
    ap.add_argument('--tags', action='store_true')
    ap.add_argument('--platform', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if not any((a.car, a.fleet, a.rows, a.tags, a.platform, a.selftest)):
        ap.print_help()
        return 2
    ok = True
    if a.platform:
        ok &= do_platform()
    if a.car:
        tmp = tempfile.mkdtemp(prefix='vehskin_')
        try:
            x, p = extract_pair('VEH_%s_GR.BIN' % a.car, tmp)
            ok &= report(audit_dirs(x, p), KU_MAX_VERLET_POINTS, a.car)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if a.tags:
        ok &= do_tags()
    if a.rows:
        ok &= do_rows()
    if a.fleet:
        ok &= do_fleet()
    if a.selftest:
        do_selftest()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
