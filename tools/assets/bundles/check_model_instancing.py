#!/usr/bin/env python3
"""Prove, FROM THE DATA ALONE, whether a Model resource will come out of the load carrying
`CgsGraphics::Model::E_FLAG_MODEL_USES_INSTANCE_SHADER`.

WHY THIS EXISTS (task 119, 2026-08-04)
    The wheels are gated off in BrnRaceCarEntityModule_Render.cpp because the ported
    WHE_51916650_GR wheel model reads mu8Flags == 0, so the console's own guard
    `CGS_ASSERT(lpWheelModel->GetFlag(E_FLAG_MODEL_USES_INSTANCE_SHADER))` fails. Three waves
    assumed that was a PORTER defect -- a header bit dropped in transcode. IT IS NOT.

    * THE FLAG IS NEVER ON DISC. It is COMPUTED AT LOAD by
        CgsResource::ModelResourceType::PostFixUp   @0x828A7A68 (BURNOUT_X360_ARTIST.XEX)
    whose whole job is:

        for each renderable r of the model (mppRenderables[0 .. mu8NumRenderables))
            for each mesh m of r (mppMeshes[0 .. mu16NumMeshes))
                assert m->mu8NumVertexDescriptors == m->mpMaterialAssembly->GetLength()
                if (m->mu8InstanceCount) { anyInstanced = true; goto done; }
        done:
        if (anyInstanced) model->mu8Flags |= 0x01;

    Measured on the retail X360, on our port, and on the BPR Remaster, the on-disc byte is
    0x00 in ALL THREE. So "the port lost the bit" was never possible. What our build is
    missing is the OVERRIDE: b5-decomp's CgsModelResourceType declares GetTypeID / FixUp /
    FixDown / GetImportCount / GetImportPointer / GetSerialisedResourceDescriptor and NOT
    PostFixUp, so the pass binds to the empty base (CgsResourceTypeBase.cpp:42) and the flag
    is never raised. The loader does run the pass (Pool::PostFixUpEntry, CgsResourcePool.cpp:587).

WHAT THIS TOOL CHECKS
    1. header      Model +0x10..0x13 = {mu8NumRenderables, mu8Flags, mu8NumStates,
                   mu8VersionNumber} decoded and printed for every Model in the bundle.
    2. postfixup   the PostFixUp walk, replayed on the serialised data: resolve the model's
                   renderable imports inside the same bundle, walk their meshes, and report
                   the mu8Flags value the load WILL produce once PostFixUp exists.
    3. drawscale   the console instanced draw (shadow::Device::DrawInstancedIndexedPrimitive_
                   Custom @0x827ED808) issues ONE draw of
                       (mDrawIndexedParameters.muNumVertices + 1) * N / mu8InstanceCount
                   so (muNumVertices + 1) MUST divide by mu8InstanceCount. Any mesh that fails
                   this is not drawable by the console's own arithmetic and is reported.
    4. contest     with two bundles (X360 source + its port), a PER-SLOT equality contest over
                   every field this chain depends on -- per the house rule that byte statistics
                   are permutation-invariant and therefore cannot test a permutation.

LAYOUTS (both are the committed consumer's, not a guess)
    Model (20B, both targets -- serialised pointer slots stay 32-bit; CgsModel.h)
        +0x00 mppRenderables  +0x04 mpu8StateRenderableIndices  +0x08 mpfLodDistances
        +0x0C miGameExplorerIndex  +0x10 mu8NumRenderables  +0x11 mu8Flags
        +0x12 mu8NumStates  +0x13 mu8VersionNumber
    Renderable      X360 32b: ver@0x10 numMeshes@0x12 meshes@0x14 osti@0x18 flags@0x1C
                    ours x64: ver@0x10 numMeshes@0x12 meshes@0x18 osti@0x20 flags@0x28
    RenderableMesh  X360 32b: oobb@0x00 dip@0x10 material@0x20 quad@0x24 buffers@0x28
                    ours x64: oobb@0x00 dip@0x10 material@0x20 quad@0x28 buffers@0x30
                    quad = {mu8NumVertexDescriptors, mu8InstanceCount, mu8NumVertexBuffers,
                            mu8Flags}
    !! The BPR Remaster is NOT an oracle for RenderableMesh: it leads with a Matrix44 bounding
      box (quad at +0x5C), its wheel meshes carry mu8InstanceCount == 0, and its vertex counts
      differ from the X360's -- it re-authored the geometry and dropped console instancing.
      Confirmed per-struct, per the standing "agreement per slot, never per subsystem" rule.

Usage:
  py tools/assets/bundles/check_model_instancing.py <bundle> [<bundle> ...]
  py tools/assets/bundles/check_model_instancing.py --contest <x360_bundle> <ported_bundle>
Exit status is non-zero if any check fails.
"""

import struct
import sys
import zlib

SIZE_MASK = 0x0FFFFFFF
T_RENDERABLE = 12
T_MODEL = 42

# X360 -> our x64 relayout of the two offsets that move.
REND_MESHTAB = {32: 0x14, 64: 0x18}
MESH_QUAD = {32: 0x24, 64: 0x28}


class CheckError(Exception):
    pass


# ---------------------------------------------------------------------------
# bnd2 v2 container (read-only)
# ---------------------------------------------------------------------------
class Bundle(object):
    def __init__(self, path):
        self.path = path
        d = open(path, 'rb').read()
        self.raw = d
        if d[0:4] != b'bnd2':
            raise CheckError('%s: not a bnd2 bundle (magic %r)' % (path, d[0:4]))
        le = struct.unpack_from('<I', d, 8)[0]
        be = struct.unpack_from('>I', d, 8)[0]
        if 1 <= le <= 8:
            self.E = '<'
        elif 1 <= be <= 8:
            self.E = '>'
        else:
            raise CheckError('%s: platform word %08x is neither LE nor BE sane' % (path, le))
        E = self.E
        (self.version, self.platform, self.debug_off,
         self.count, self.entries_off) = struct.unpack_from(E + '5I', d, 4)
        self.data_off = list(struct.unpack_from(E + '3I', d, 0x18))
        self.compressed = bool(struct.unpack_from(E + 'I', d, 0x24)[0] & 1)
        # platform 2 = X360 (32-bit BE), 1 = PC 32-bit, 4 = this project's x64 PC port.
        self.bits = 64 if self.platform == 4 else 32
        self.entries = []
        for i in range(self.count):
            o = self.entries_off + i * 0x40
            self.entries.append({
                'index': i,
                'id': struct.unpack_from(E + 'Q', d, o)[0],
                'usize': [w & SIZE_MASK for w in struct.unpack_from(E + '3I', d, o + 0x10)],
                'dsize': [w & SIZE_MASK for w in struct.unpack_from(E + '3I', d, o + 0x1C)],
                'doff': list(struct.unpack_from(E + '3I', d, o + 0x28)),
                'imp_off': struct.unpack_from(E + 'I', d, o + 0x34)[0],
                'type': struct.unpack_from(E + 'I', d, o + 0x38)[0],
                'nimports': struct.unpack_from(E + 'H', d, o + 0x3C)[0],
            })

    def payload(self, e, bank=0):
        if e['usize'][bank] == 0:
            return b''
        start = self.data_off[bank] + e['doff'][bank]
        blob = self.raw[start:start + e['dsize'][bank]]
        if self.compressed:
            blob = zlib.decompress(blob)
        return blob[:e['usize'][bank]]

    def imports(self, e):
        """[(resource_id, slot_offset)] -- 16-byte ImportEntry records inside bank 0."""
        if e['nimports'] == 0:
            return []
        p = self.payload(e, 0)
        out = []
        for i in range(e['nimports']):
            o = e['imp_off'] + i * 16
            out.append((struct.unpack_from(self.E + 'Q', p, o)[0],
                        struct.unpack_from(self.E + 'I', p, o + 8)[0]))
        return out

    def by_id(self, rid):
        for e in self.entries:
            if e['id'] == rid:
                return e
        return None


# ---------------------------------------------------------------------------
# typed reads
# ---------------------------------------------------------------------------
def read_model(b, e):
    p = b.payload(e, 0)
    if len(p) < 20:
        raise CheckError('Model %016X: %d-byte payload is shorter than the 20-byte header'
                         % (e['id'], len(p)))
    return {
        'id': e['id'],
        'size': len(p),
        'mu8NumRenderables': p[0x10],
        'mu8Flags': p[0x11],
        'mu8NumStates': p[0x12],
        'mu8VersionNumber': p[0x13],
        'state_indices': None,
        'import_ids': [rid for rid, _ in b.imports(e)],
        'import_slots': [off for _, off in b.imports(e)],
        'slot_values': [struct.unpack_from(b.E + 'I', p, off)[0] for _, off in b.imports(e)],
    }


def read_renderable(b, e):
    """-> {'version','flags','meshes':[{...}]} in the bundle's own layout."""
    p = b.payload(e, 0)
    E = b.E
    bits = b.bits
    ver = struct.unpack_from(E + 'H', p, 0x10)[0]
    if ver != 11:
        raise CheckError('Renderable %016X: version %d (expected 11) -- wrong endianness or '
                         'the layout model is wrong; refusing to report numbers I cannot trust'
                         % (e['id'], ver))
    num = struct.unpack_from(E + 'H', p, 0x12)[0]
    tab = REND_MESHTAB[bits]
    quad = MESH_QUAD[bits]
    if bits == 64:
        tbl = struct.unpack_from(E + 'Q', p, tab)[0]
        flags = struct.unpack_from(E + 'H', p, 0x28)[0]
        step, unpack = 8, E + 'Q'
    else:
        tbl = struct.unpack_from(E + 'I', p, tab)[0]
        flags = struct.unpack_from(E + 'H', p, 0x1C)[0]
        step, unpack = 4, E + 'I'
    meshes = []
    for i in range(num):
        mo = struct.unpack_from(unpack, p, tbl + step * i)[0]
        meshes.append({
            'index': i,
            'numVD': p[mo + quad + 0],
            'instanceCount': p[mo + quad + 1],
            'numVB': p[mo + quad + 2],
            'flags': p[mo + quad + 3],
            'dip': struct.unpack_from(E + '4I', p, mo + 0x10),
        })
    return {'id': e['id'], 'version': ver, 'flags': flags, 'meshes': meshes,
            'sphere': struct.unpack_from(E + '4f', p, 0)}


# ---------------------------------------------------------------------------
# the PostFixUp replay
# ---------------------------------------------------------------------------
def replay_postfixup(b, model):
    """CgsResource::ModelResourceType::PostFixUp @0x828A7A68, replayed on serialised data.
    -> (flag_value, [(renderable_id, [instance counts])], [problems])"""
    per_rend = []
    problems = []
    any_instanced = False
    for rid in model['import_ids']:
        e = b.by_id(rid)
        if e is None:
            problems.append('renderable %016X imported by model %016X is not in this bundle'
                            % (rid, model['id']))
            continue
        if e['type'] != T_RENDERABLE:
            problems.append('model %016X imports %016X which is type %d, not Renderable(12)'
                            % (model['id'], rid, e['type']))
            continue
        r = read_renderable(b, e)
        counts = [m['instanceCount'] for m in r['meshes']]
        per_rend.append((rid, counts))
        if any(counts):
            any_instanced = True
        for m in r['meshes']:
            n = m['instanceCount']
            if n > 1 and (m['dip'][3] + 1) % n != 0:
                problems.append(
                    'renderable %016X mesh[%d]: (muNumVertices+1)=%d is not divisible by '
                    'mu8InstanceCount=%d -- DrawInstancedIndexedPrimitive_Custom\'s '
                    '(n+1)*N/max would truncate' % (rid, m['index'], m['dip'][3] + 1, n))
    return (0x01 if any_instanced else 0x00), per_rend, problems


def check_bundle(path, verbose=True):
    b = Bundle(path)
    models = [e for e in b.entries if e['type'] == T_MODEL]
    print('=== %s  (bnd2 v%d platform %d, %d-bit layout, %d resources, %d Model)'
          % (path, b.version, b.platform, b.bits, b.count, len(models)))
    failures = 0
    for e in models:
        m = read_model(b, e)
        flag, per_rend, problems = replay_postfixup(b, m)
        state = 'SET' if flag else 'CLEAR'
        print('  Model %016X  %dB  numRenderables=%d numStates=%d version=%d'
              % (m['id'], m['size'], m['mu8NumRenderables'], m['mu8NumStates'],
                 m['mu8VersionNumber']))
        print('      on-disc mu8Flags = 0x%02X   (always 0 -- the flag is not authored)'
              % m['mu8Flags'])
        print('      PostFixUp would produce mu8Flags = 0x%02X  -> E_FLAG_MODEL_USES_'
              'INSTANCE_SHADER %s' % (flag, state))
        if verbose:
            for rid, counts in per_rend:
                print('        renderable %016X  mu8InstanceCount per mesh: %s' % (rid, counts))
        nonnull = [(off, val) for off, val in zip(m['import_slots'], m['slot_values']) if val]
        if nonnull:
            print('      WARN import slots not serialised-null: %s'
                  % ', '.join('+0x%X=0x%X' % t for t in nonnull))
        for pr in problems:
            print('      FAIL %s' % pr)
            failures += 1
        if not flag and m['mu8NumRenderables']:
            print('      NOTE this model would NOT get the flag even with PostFixUp present.')
    return failures


def contest(src_path, port_path):
    """Per-slot equality contest over every field the instancing chain reads."""
    a, c = Bundle(src_path), Bundle(port_path)
    print('=== CONTEST  %s  vs  %s' % (src_path, port_path))
    fails = 0
    checked = 0
    a_models = {e['id']: e for e in a.entries if e['type'] == T_MODEL}
    c_models = {e['id']: e for e in c.entries if e['type'] == T_MODEL}
    if set(a_models) != set(c_models):
        print('  FAIL Model id sets differ')
        return 1
    for rid in sorted(a_models):
        ma, mc = read_model(a, a_models[rid]), read_model(c, c_models[rid])
        for k in ('mu8NumRenderables', 'mu8Flags', 'mu8NumStates', 'mu8VersionNumber',
                  'import_ids', 'import_slots'):
            checked += 1
            if ma[k] != mc[k]:
                print('  FAIL Model %016X.%s: source %r != port %r' % (rid, k, ma[k], mc[k]))
                fails += 1
    a_rend = {e['id']: e for e in a.entries if e['type'] == T_RENDERABLE}
    c_rend = {e['id']: e for e in c.entries if e['type'] == T_RENDERABLE}
    if set(a_rend) != set(c_rend):
        print('  FAIL Renderable id sets differ')
        return fails + 1
    for rid in sorted(a_rend):
        ra, rc = read_renderable(a, a_rend[rid]), read_renderable(c, c_rend[rid])
        for k in ('version', 'flags'):
            checked += 1
            if ra[k] != rc[k]:
                print('  FAIL Renderable %016X.%s: %r != %r' % (rid, k, ra[k], rc[k]))
                fails += 1
        checked += 1
        if len(ra['meshes']) != len(rc['meshes']):
            print('  FAIL Renderable %016X: %d meshes vs %d'
                  % (rid, len(ra['meshes']), len(rc['meshes'])))
            fails += 1
            continue
        for ma_, mc_ in zip(ra['meshes'], rc['meshes']):
            for k in ('numVD', 'instanceCount', 'numVB', 'flags', 'dip'):
                checked += 1
                if ma_[k] != mc_[k]:
                    print('  FAIL Renderable %016X mesh[%d].%s: %r != %r'
                          % (rid, ma_['index'], k, ma_[k], mc_[k]))
                    fails += 1
    print('  %d slots contested, %d disagreements' % (checked, fails))
    return fails


def main(argv):
    if not argv:
        sys.stderr.write(__doc__)
        return 2
    try:
        if argv[0] == '--contest':
            if len(argv) != 3:
                sys.stderr.write('--contest takes exactly two bundles\n')
                return 2
            return 1 if contest(argv[1], argv[2]) else 0
        bad = 0
        for path in argv:
            bad += check_bundle(path)
        return 1 if bad else 0
    except CheckError as e:
        sys.stderr.write('ERROR: %s\n' % e)
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
