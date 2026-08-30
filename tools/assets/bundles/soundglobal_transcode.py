#!/usr/bin/env python3
"""Port SOUND/BURNOUTGLOBALDATA.BIN from X360 BE to the native PC bundle.

The bundle contains one AttribSysVault resource with 825 collections spanning
22 sound classes.  Its PtrN stream fixes slots in both dependency blocks: the
VLT CollectionLoadData records and the BIN class layouts.  The smaller world
vault converter intentionally handles only the first shape, so using it here
would leave hundreds of BIN pointer cells and class fields big-endian.

This porter gets every class definition from the ARTIST XEX's embedded
AttribSys schema (ClassLoadData + Definition records).  The schema supplies the
field type, offset, element size, array capacity, flags, and layout extent; the
vault supplies the live collection headers, dynamic-array lengths, and PtrN
targets.  Nothing is inferred from plausible values.

Validation is deliberately strict:
  * every export is an Attrib::CollectionLoadData with an exact sized header;
  * every layout/entry target is named by the PtrN stream and matches its schema;
  * every type-1/type-3 pointer slot lands on a declared 4-byte field;
  * inline/dynamic Attrib::Array headers agree with their Definition records;
  * the emitted LE resource re-walks with the identical field plan and values;
  * flipping the LE field plan back reproduces the source byte-for-byte.

Usage:
  py soundglobal_transcode.py <x360 BURNOUTGLOBALDATA.BIN> <pc output bundle>

The build driver supplies BRN_X360_ROOT, used to locate
BURNOUT_X360_ARTIST.xex for its embedded schema.
"""

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import attribsys_schema_port as schema_port


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')

COLLECTION_TYPE = schema_port.GCOLLECTION_TYPE
CLASS_TYPE = schema_port.GCLASS_TYPE
DATABASE_TYPE = schema_port.GDATABASE_TYPE


class PortError(SystemExit):
    pass


def read_u(data, off, width, endian):
    if off < 0 or off + width > len(data):
        raise PortError('read +0x%X/%d overruns %d-byte image' %
                        (off, width, len(data)))
    return int.from_bytes(data[off:off + width], endian)


class Plan(object):
    def __init__(self, data, endian):
        self.data = data
        self.endian = endian
        self.fields = []
        self._by_span = {}
        self._covered = bytearray(len(data))

    def value(self, off, width):
        return read_u(self.data, off, width, self.endian)

    def field(self, off, width, tag):
        if off < 0 or off + width > len(self.data):
            raise PortError('%s at +0x%X/%d overruns the resource' %
                            (tag, off, width))
        span = (off, width)
        if span in self._by_span:
            return self.value(off, width)
        if any(self._covered[off:off + width]):
            prior = next((self._by_span[k] for k in self._by_span
                          if not (k[0] + k[1] <= off or off + width <= k[0])), '?')
            raise PortError('%s at +0x%X/%d overlaps %s' %
                            (tag, off, width, prior))
        self._covered[off:off + width] = b'\1' * width
        self._by_span[span] = tag
        self.fields.append((off, width, tag))
        return self.value(off, width)

    def has_exact_field(self, off, width):
        return (off, width) in self._by_span

    def apply(self):
        out = bytearray(self.data)
        for off, width, _tag in self.fields:
            out[off:off + width] = out[off:off + width][::-1]
        return bytes(out)


class Definition(object):
    def __init__(self, key, type_key, type_name, off, size, max_count, flags, align):
        self.key = key
        self.type_key = type_key
        self.type_name = type_name
        self.off = off
        self.size = size
        self.max_count = max_count
        self.flags = flags
        self.align = align


class ClassSchema(object):
    def __init__(self, key, layout_size, definitions):
        self.key = key
        self.layout_size = layout_size
        self.definitions = definitions
        self.by_key = {d.key: d for d in definitions}


def find_artist_xex(source_bundle):
    roots = []
    configured = os.environ.get('BRN_X360_ROOT')
    if configured:
        roots.append(configured)
    roots.append(os.path.dirname(os.path.dirname(os.path.abspath(source_bundle))))
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            if name.lower() == 'burnout_x360_artist.xex':
                return os.path.join(root, name)
    raise PortError('BURNOUT_X360_ARTIST.xex not found (set BRN_X360_ROOT)')


def load_schema(xex):
    vlt, bin_data = schema_port.extract_schema_from_xex(xex)
    _walk, exports, fixups = schema_port.walk_vlt(vlt, True)

    db_exports = [e for e in exports if e[1] == DATABASE_TYPE]
    if len(db_exports) != 1:
        raise PortError('embedded schema has %d DatabaseLoadData exports' % len(db_exports))
    db = db_exports[0]
    num_types = read_u(vlt, db[3] + 8, 4, 'big')
    name_targets = [target for slot, kind, _dep, target in fixups
                    if kind == 3 and slot == db[3] + 12]
    if len(name_targets) != 1:
        raise PortError('embedded schema has no unique typename pointer')
    names = []
    at = name_targets[0]
    for _ in range(num_types):
        try:
            end = bin_data.index(b'\0', at)
        except ValueError:
            raise PortError('embedded schema typename table is unterminated')
        names.append(bin_data[at:end].decode('latin1'))
        at = end + 1

    # The DatabaseLoadData typeSizes array and typename list use the same order.
    type_size = {}
    type_name = {}
    for i, name in enumerate(names):
        size = read_u(vlt, db[3] + 16 + i * 4, 4, 'big')
        # The serialized schema stores the type key in every Definition.  Build
        # the name map from those records below; hash reimplementation is not a
        # prerequisite for porting.
        type_size[name] = size

    fix_by_slot = {slot: target for slot, kind, _dep, target in fixups if kind == 3}
    raw_classes = []
    definition_type_keys = []
    for _eid, kind, _size, off in exports:
        if kind != CLASS_TYPE:
            continue
        key = read_u(vlt, off, 8, 'big')
        ndefs = read_u(vlt, off + 12, 4, 'big')
        defs_at = fix_by_slot.get(off + 16)
        if defs_at is None:
            raise PortError('schema class %016X has no definitions pointer' % key)
        layout_size = read_u(vlt, off + 28, 4, 'big')
        defs = []
        for i in range(ndefs):
            p = defs_at + i * 24
            dkey = read_u(bin_data, p, 8, 'big')
            tkey = read_u(bin_data, p + 8, 8, 'big')
            definition_type_keys.append(tkey)
            defs.append((dkey, tkey,
                         read_u(bin_data, p + 16, 2, 'big'),
                         read_u(bin_data, p + 18, 2, 'big'),
                         read_u(bin_data, p + 20, 2, 'big'),
                         read_u(bin_data, p + 22, 1, 'big'),
                         read_u(bin_data, p + 23, 1, 'big')))
        raw_classes.append((key, layout_size, defs))

    # Type IDs are the schema's canonical lookup8 hashes.  Importing the small,
    # already-gated implementation avoids duplicating that algorithm here.
    from vehicleattrib_transcode import hash64
    for name in names:
        type_name[hash64(name)] = name

    classes = {}
    for key, layout_size, raw_defs in raw_classes:
        defs = []
        for dkey, tkey, off, size, max_count, flags, align in raw_defs:
            name = type_name.get(tkey)
            if name is None:
                raise PortError('schema class %016X definition %016X has unnamed type %016X' %
                                (key, dkey, tkey))
            expected = type_size.get(name)
            if expected is not None and expected != size:
                raise PortError('schema type %s says size %d but definition says %d' %
                                (name, expected, size))
            defs.append(Definition(dkey, tkey, name, off, size,
                                   max_count, flags, align))
        classes[key] = ClassSchema(key, layout_size, defs)
    return classes


def fourcc(plan, off, tag):
    plan.field(off, 4, tag)
    raw = plan.data[off:off + 4]
    return raw if plan.endian == 'big' else raw[::-1]


def plan_element(plan, off, definition, tag):
    name = definition.type_name
    size = definition.size
    primitive = {
        'EA::Reflection::Bool': 1,
        'EA::Reflection::Int8': 1,
        'EA::Reflection::UInt8': 1,
        'EA::Reflection::Int16': 2,
        'EA::Reflection::UInt16': 2,
        'EA::Reflection::Int32': 4,
        'EA::Reflection::UInt32': 4,
        'EA::Reflection::Float': 4,
        'EA::Reflection::Text': 4,
        'EA::Reflection::Int64': 8,
        'EA::Reflection::UInt64': 8,
    }
    if name in primitive:
        width = primitive[name]
        if size != width:
            raise PortError('%s type %s is %d bytes, expected %d' %
                            (tag, name, size, width))
        plan.field(off, width, tag)
        return
    if name.startswith('AttribSys::Enums::'):
        if size not in (1, 2, 4, 8):
            raise PortError('%s enum %s has unsupported size %d' % (tag, name, size))
        plan.field(off, size, tag)
        return
    if name == 'Attrib::RefSpec':
        if size != 24:
            raise PortError('%s RefSpec size is %d, not 24' % (tag, size))
        plan.field(off, 8, tag + '.mClassKey')
        plan.field(off + 8, 8, tag + '.mCollectionKey')
        plan.field(off + 16, 4, tag + '.mpCollectionPtr')
        if any(plan.data[off + 20:off + 24]):
            raise PortError('%s RefSpec pad is non-zero' % tag)
        return
    if name == 'Attrib::Types::RwVector2':
        if size != 16:
            raise PortError('%s RwVector2 size is %d, not 16' % (tag, size))
        plan.field(off, 4, tag + '.x')
        plan.field(off + 4, 4, tag + '.y')
        if any(plan.data[off + 8:off + 16]):
            raise PortError('%s RwVector2 pad is non-zero' % tag)
        return
    if name == 'Attrib::Types::RwVector3':
        if size != 16:
            raise PortError('%s RwVector3 size is %d, not 16' % (tag, size))
        for i, axis in enumerate(('x', 'y', 'z')):
            plan.field(off + i * 4, 4, tag + '.' + axis)
        if any(plan.data[off + 12:off + 16]):
            raise PortError('%s RwVector3 pad is non-zero' % tag)
        return
    if name == 'Attrib::Types::Matrix':
        if size != 64:
            raise PortError('%s Matrix size is %d, not 64' % (tag, size))
        for i in range(16):
            plan.field(off + i * 4, 4, '%s[%d]' % (tag, i))
        return
    raise PortError('%s has no endian lane rule for schema type %s (%d bytes)' %
                    (tag, name, size))


def plan_array(plan, off, definition, tag, fixed):
    alloc = plan.field(off, 2, tag + '.alloc')
    count = plan.field(off + 2, 2, tag + '.count')
    elem_size = plan.field(off + 4, 2, tag + '.elementSize')
    type_info = plan.field(off + 6, 2, tag + '.typeInfo')
    if count > alloc:
        raise PortError('%s count %d exceeds allocation %d' % (tag, count, alloc))
    if elem_size != definition.size:
        raise PortError('%s element size %d != schema %d' %
                        (tag, elem_size, definition.size))
    if fixed and definition.max_count != 0xFFFF and alloc != definition.max_count:
        raise PortError('%s allocation %d != fixed schema capacity %d' %
                        (tag, alloc, definition.max_count))
    if not fixed and definition.max_count != 0xFFFF and alloc > definition.max_count:
        raise PortError('%s allocation %d exceeds schema maximum %d' %
                        (tag, alloc, definition.max_count))
    data_at = ((type_info >> 12) & 0xFFFF8) + 8
    for i in range(alloc):
        plan_element(plan, off + data_at + i * elem_size,
                     definition, '%s[%d]' % (tag, i))
    return data_at + alloc * elem_size


def plan_layout(plan, bin_base, target, cls, tag):
    start = bin_base + target
    if target + cls.layout_size > len(plan.data) - bin_base:
        raise PortError('%s layout BIN+0x%X/%d overruns BIN' %
                        (tag, target, cls.layout_size))
    for definition in cls.definitions:
        field_tag = '%s.%016X' % (tag, definition.key)
        at = start + definition.off
        if definition.flags == 6:
            if definition.max_count != 1:
                raise PortError('%s scalar has maxCount %d' %
                                (field_tag, definition.max_count))
            plan_element(plan, at, definition, field_tag)
        elif definition.flags == 7:
            used = plan_array(plan, at, definition, field_tag, True)
            if definition.off + used > cls.layout_size:
                raise PortError('%s fixed array overruns %d-byte layout' %
                                (field_tag, cls.layout_size))
        elif definition.flags == 5:
            # Dynamic attributes live in CollectionLoadData entries, not in the
            # class's fixed layout block.
            continue
        else:
            raise PortError('%s has unsupported Definition flags 0x%02X' %
                            (field_tag, definition.flags))


def build_plan(data, endian, schemas):
    plan = Plan(data, endian)
    vlt_off = plan.field(0, 4, 'resource.vltOffset')
    vlt_size = plan.field(4, 4, 'resource.vltSize')
    bin_off = plan.field(8, 4, 'resource.binOffset')
    bin_size = plan.field(12, 4, 'resource.binSize')
    if vlt_off != 16 or bin_off != vlt_off + vlt_size:
        raise PortError('vault spans are not contiguous (vlt=0x%X+0x%X bin=0x%X)' %
                        (vlt_off, vlt_size, bin_off))
    if bin_off + bin_size > len(data):
        raise PortError('BIN overruns resource (%d > %d)' %
                        (bin_off + bin_size, len(data)))

    exports = []
    pointer_records = []
    pos = vlt_off
    vlt_end = vlt_off + vlt_size
    while pos < vlt_end:
        cc = fourcc(plan, pos, 'chunk.fourCC')
        size = plan.field(pos + 4, 4, 'chunk.size')
        if size < 8 or pos + size > vlt_end:
            raise PortError('bad %r chunk size 0x%X at +0x%X' % (cc, size, pos))
        body = pos + 8
        if cc in (b'Vers', b'StrN'):
            plan.field(body, 8, cc.decode('ascii') + '.value')
        elif cc == b'DepN':
            plan.field(body, 4, 'DepN.pad')
            count = plan.field(body + 4, 4, 'DepN.count')
            ids = body + 8
            for i in range(count):
                plan.field(ids + i * 8, 8, 'DepN[%d].id' % i)
            name_offsets = ids + count * 8
            for i in range(count):
                plan.field(name_offsets + i * 4, 4, 'DepN[%d].nameOffset' % i)
        elif cc == b'DatN':
            pass
        elif cc == b'ExpN':
            plan.field(body, 4, 'ExpN.baseAllocExports')
            count = plan.field(body + 4, 4, 'ExpN.count')
            at = body + 8
            if at + count * 24 > pos + size:
                raise PortError('ExpN entries overrun their chunk')
            for i in range(count):
                eid = plan.field(at, 8, 'ExpN[%d].exportId' % i)
                kind = plan.field(at + 8, 8, 'ExpN[%d].typeId' % i)
                entry_size = plan.field(at + 16, 4, 'ExpN[%d].size' % i)
                entry_off = plan.field(at + 20, 4, 'ExpN[%d].offset' % i)
                exports.append((eid, kind, entry_size, entry_off))
                at += 24
        elif cc == b'PtrN':
            at = body
            current = None
            for i in range((size - 8) // 16):
                slot = plan.field(at, 4, 'PtrN[%d].slot' % i)
                kind = plan.field(at + 4, 2, 'PtrN[%d].type' % i)
                dep = plan.field(at + 6, 2, 'PtrN[%d].dep' % i)
                target = plan.field(at + 8, 8, 'PtrN[%d].target' % i)
                if kind == 2:
                    current = dep
                pointer_records.append((i, current, slot, kind, dep, target))
                at += 16
        else:
            raise PortError('unknown VLT chunk %r at +0x%X' % (cc, pos))
        pos += size
    if pos != vlt_end:
        raise PortError('VLT chunk walk did not tile its image')

    if fourcc(plan, bin_off, 'StrE.fourCC') != b'StrE':
        raise PortError('BIN does not begin with StrE')
    string_size = plan.field(bin_off + 4, 4, 'StrE.size')
    if string_size < 8 or string_size > bin_size:
        raise PortError('invalid StrE size 0x%X' % string_size)

    collections = []
    vlt_slots = {}
    for i, (_eid, kind, entry_size, entry_off) in enumerate(exports):
        if kind != COLLECTION_TYPE:
            raise PortError('export %d type %016X is not CollectionLoadData' % (i, kind))
        at = vlt_off + entry_off
        key = plan.field(at, 8, 'collection[%d].key' % i)
        class_key = plan.field(at + 8, 8, 'collection[%d].class' % i)
        plan.field(at + 16, 8, 'collection[%d].parent' % i)
        plan.field(at + 24, 4, 'collection[%d].tableReserve' % i)
        plan.field(at + 28, 4, 'collection[%d].tableKeyShift' % i)
        num_entries = plan.field(at + 32, 4, 'collection[%d].numEntries' % i)
        num_types = plan.field(at + 36, 2, 'collection[%d].numTypes' % i)
        types_len = plan.field(at + 38, 2, 'collection[%d].typesLen' % i)
        plan.field(at + 40, 4, 'collection[%d].layout' % i)
        plan.field(at + 44, 4, 'collection[%d].pad' % i)
        expected = 48 + types_len * 8 + num_entries * 16
        if expected != entry_size:
            raise PortError('collection %d size %d != 48+%d*8+%d*16 (%d)' %
                            (i, entry_size, types_len, num_entries, expected))
        cls = schemas.get(class_key)
        if cls is None:
            raise PortError('collection %016X uses class %016X absent from ARTIST schema' %
                            (key, class_key))
        cursor = at + 48
        for t in range(types_len):
            plan.field(cursor, 8, 'collection[%d].type[%d]' % (i, t))
            cursor += 8
        entries = []
        vlt_slots[entry_off + 40] = ('layout', i, None)
        for e in range(num_entries):
            entry_key = plan.field(cursor, 8, 'collection[%d].entry[%d].key' % (i, e))
            plan.field(cursor + 8, 4, 'collection[%d].entry[%d].value' % (i, e))
            type_index = plan.field(cursor + 12, 2,
                                    'collection[%d].entry[%d].typeIndex' % (i, e))
            flags = plan.field(cursor + 14, 1,
                               'collection[%d].entry[%d].flags' % (i, e))
            pad = plan.field(cursor + 15, 1,
                             'collection[%d].entry[%d].pad' % (i, e))
            if type_index > num_types or pad != 0:
                raise PortError('collection %d entry %d has invalid type/pad' % (i, e))
            definition = cls.by_key.get(entry_key)
            if definition is None:
                raise PortError('class %016X has no definition for entry %016X' %
                                (class_key, entry_key))
            entries.append((e, entry_key, flags, definition, cursor + 8 - vlt_off))
            vlt_slots[cursor + 8 - vlt_off] = ('entry', i, e)
            cursor += 16
        collections.append((i, key, cls, entry_off + 40, entries))

    fixups = {}
    for index, current, slot, kind, dep, target in pointer_records:
        if kind == 0:
            continue
        if kind == 2:
            if dep not in (0, 1):
                raise PortError('PtrN[%d] selects dependency %d' % (index, dep))
            continue
        if kind not in (1, 3):
            raise PortError('PtrN[%d] has unsupported type %d' % (index, kind))
        if current not in (0, 1):
            raise PortError('PtrN[%d] writes before selecting a dependency' % index)
        key = (current, slot)
        if key in fixups:
            raise PortError('duplicate PtrN slot dep%d+0x%X' % key)
        fixups[key] = (kind, dep, target, index)

    # Plan every fixed class layout and dynamic entry payload from the VLT fixups.
    for i, _key, cls, layout_slot, entries in collections:
        layout_fix = fixups.get((0, layout_slot))
        if cls.layout_size:
            if layout_fix is None or layout_fix[0] != 3 or layout_fix[1] != 1:
                raise PortError('collection %d has no VLT->BIN layout fixup' % i)
            plan_layout(plan, bin_off, layout_fix[2], cls, 'collection[%d]' % i)
        elif layout_fix is not None:
            raise PortError('collection %d has a layout fixup but schema layoutSize is 0' % i)

        for e, entry_key, flags, definition, slot in entries:
            entry_fix = fixups.get((0, slot))
            if entry_fix is None or entry_fix[0] != 3 or entry_fix[1] != 1:
                raise PortError('collection %d entry %d has no VLT->BIN fixup' % (i, e))
            if definition.flags != 5:
                raise PortError('collection %d entry %d definition flags are 0x%02X, not dynamic' %
                                (i, e, definition.flags))
            if not (flags & 0x02):
                raise PortError('collection %d entry %d is not marked as an array' % (i, e))
            target = entry_fix[2]
            if target < string_size:
                raise PortError('collection %d entry %d points inside StrE' % (i, e))
            plan_array(plan, bin_off + target, definition,
                       'collection[%d].entry[%d].%016X' % (i, e, entry_key), False)

    # Every runtime pointer write must land on a field whose serialized lane is
    # exactly one u32.  This validates both VLT and nested BIN pointer graphs.
    for (current, slot), (kind, dep, target, index) in fixups.items():
        absolute = (vlt_off if current == 0 else bin_off) + slot
        if not plan.has_exact_field(absolute, 4):
            raise PortError('PtrN[%d] writes dep%d+0x%X, which is not a declared u32 slot' %
                            (index, current, slot))
        if kind == 3:
            limit = vlt_size if dep == 0 else bin_size if dep == 1 else -1
            if limit < 0 or target >= limit:
                raise PortError('PtrN[%d] target dep%d+0x%X is outside its block' %
                                (index, dep, target))
        if current == 0 and slot not in vlt_slots:
            raise PortError('PtrN[%d] VLT slot 0x%X is not a collection pointer' %
                            (index, slot))

    return plan, len(collections), len(fixups)


def port_resource(data, schemas):
    be, collections, fixups = build_plan(data, 'big', schemas)
    out = be.apply()
    le, collections2, fixups2 = build_plan(out, 'little', schemas)
    shape_be = [(o, w) for o, w, _tag in be.fields]
    shape_le = [(o, w) for o, w, _tag in le.fields]
    if shape_be != shape_le:
        raise PortError('LE re-walk produced a different field plan')
    for (off, width, tag), (off2, width2, _tag2) in zip(be.fields, le.fields):
        before = read_u(data, off, width, 'big')
        after = read_u(out, off2, width2, 'little')
        if before != after:
            raise PortError('%s value changed across endian port' % tag)
    if le.apply() != data:
        raise PortError('LE -> BE round trip is not byte-identical')
    if collections != collections2 or fixups != fixups2:
        raise PortError('collection/fixup counts changed across endian port')
    return out, collections, fixups, len(be.fields)


def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write((result.stdout or '') + (result.stderr or ''))
        raise PortError('command failed (%d): %s' %
                        (result.returncode, ' '.join(argv[:3])))


def convert_bundle(source, output):
    xex = find_artist_xex(source)
    schemas = load_schema(xex)
    work = tempfile.mkdtemp(prefix='soundglobal_')
    try:
        extracted = os.path.join(work, 'bundle')
        run([YAP, 'e', source, extracted])
        resource_dir = os.path.join(extracted, 'AttribSysVault')
        resources = [] if not os.path.isdir(resource_dir) else [
            os.path.join(resource_dir, name) for name in os.listdir(resource_dir)
            if name.lower().endswith('.dat')]
        if len(resources) != 1:
            raise PortError('expected one AttribSysVault resource, found %d' % len(resources))
        with open(resources[0], 'rb') as fh:
            data = fh.read()
        ported, collections, fixups, fields = port_resource(data, schemas)
        with open(resources[0], 'wb') as fh:
            fh.write(ported)

        meta_path = os.path.join(extracted, '.meta.yaml')
        with open(meta_path, 'r', encoding='utf-8') as fh:
            meta = fh.read()
        meta = re.sub(r'(^\s*platform:\s*)2\s*$', r'\g<1>4', meta, flags=re.M)
        meta = re.sub(r'(^\s*compressed:\s*)true\s*$', r'\g<1>false', meta, flags=re.M)
        with open(meta_path, 'w', encoding='utf-8') as fh:
            fh.write(meta)
        run([YAP, 'c', extracted, output])
        print('ported sound global vault: %d collections, %d fixups, %d endian fields' %
              (collections, fixups, fields))
        print('OK:', output)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv):
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    convert_bundle(argv[1], argv[2])
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
