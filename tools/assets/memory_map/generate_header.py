#!/usr/bin/env python
# Generate a compiled-in C++ pool table from the editable memory-map YAML, so the PC build can stand up
# the real Burnout pool set (GameDataModule::CreatePools) without a runtime YAML parser.
#
# Pipeline: tools/assets/memory_map/export_yaml.py (XEX -> progress/memory_map_artist.yaml, editable) ->
#           tools/assets/memory_map/generate_header.py (YAML -> BrnMemoryMapData.h, build input).
#
# Usage: py tools/assets/memory_map/generate_header.py
import json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAML = os.path.join(ROOT, 'progress', 'memory_map_artist.yaml')
OUT  = os.path.join(ROOT, 'b5-decomp', 'src', 'GameSource', 'Resource', 'BrnMemoryMapData.h')

def parse_pools(text):
    pools = []
    cur = None
    in_pools = False
    in_heaps = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith('pools:'):
            in_pools = True; continue
        if not in_pools:
            continue
        m = re.match(r'  - id:\s*(-?\d+)', line)
        if m:
            if cur: pools.append(cur)
            cur = dict(id=int(m.group(1)), name='', nodes=0, maxres=0, maximp=0,
                       defrag=False, deps=[], heaps=[])
            in_heaps = False
            continue
        if cur is None:
            continue
        m = re.match(r'    name:\s*(.+)', line)
        if m:
            n = m.group(1).strip()
            if n.startswith("'") and n.endswith("'"): n = n[1:-1].replace("''", "'")
            cur['name'] = n; continue
        m = re.match(r'    max_heap_nodes:\s*(\d+)', line)
        if m: cur['nodes'] = int(m.group(1)); continue
        m = re.match(r'    max_resources:\s*(\d+)', line)
        if m: cur['maxres'] = int(m.group(1)); continue
        m = re.match(r'    max_imports:\s*(\d+)', line)
        if m: cur['maximp'] = int(m.group(1)); continue
        m = re.match(r'    allow_defragmentation:\s*(\w+)', line)
        if m: cur['defrag'] = (m.group(1) == 'true'); continue
        m = re.match(r'    dependencies:\s*\[([^\]]*)\]', line)
        if m:
            cur['deps'] = [int(x) for x in m.group(1).split(',') if x.strip()]; continue
        if line.startswith('    heaps:'):
            in_heaps = True; continue
        if in_heaps:
            m = re.match(r'\s*-\s*\{\s*type:\s*(\d+),\s*size:\s*(0x[0-9A-Fa-f]+),\s*align:\s*(\d+)\s*\}', line)
            if m:
                cur['heaps'].append((int(m.group(1)), int(m.group(2), 16), int(m.group(3))))
    if cur: pools.append(cur)
    return pools

def parse_allocators(text):
    """Parse the five `allocators:` record tables (single-line mappings)."""
    tables = {'raw_resources': [], 'linear': [], 'heap': [], 'rw_linear': [], 'rw_general': []}
    cur = None
    in_alloc = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith('allocators:'):
            in_alloc = True; continue
        if not in_alloc:
            continue
        m = re.match(r'  (\w+):\s*$', line)
        if m:
            cur = m.group(1)
            continue
        if cur is None or cur not in tables:
            continue
        m = re.match(r'    - \{ bank:\s*(\d+),\s*name:\s*([^,]+),\s*parent:\s*(\d+),\s*'
                     r'(?:size:\s*(0x[0-9A-Fa-f]+)|desc:\s*\[(.*)\])\s*\}\s*$', line)
        if not m:
            continue
        entry = dict(bank=int(m.group(1)), name=m.group(2).strip().strip("'"),
                     parent=int(m.group(3)), size=[0]*5, align=[1]*5)
        if m.group(4):
            entry['size'][0] = int(m.group(4), 16)
            entry['align'][0] = 16
        else:
            for dm in re.finditer(r'\{\s*type:\s*(\d+),\s*size:\s*(0x[0-9A-Fa-f]+),\s*align:\s*(\d+)\s*\}', m.group(5)):
                t = int(dm.group(1))
                entry['size'][t] = int(dm.group(2), 16)
                entry['align'][t] = int(dm.group(3))
        tables[cur].append(entry)
    return tables


def parse_memory_map_image(text):
    """Parse the exact typed image rows appended to the ARTIST source YAML."""
    image = {'banks': [], 'pools': [], 'allocator_events': {}}
    in_image = False
    table = None
    family = None
    for raw in text.splitlines():
        if raw == 'memory_map_image:':
            in_image = True
            continue
        if not in_image:
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if not line:
            continue
        if indent == 2 and line.endswith(':'):
            table = line[:-1]
            family = None
            continue
        if table == 'allocator_events' and indent == 4 and line.endswith(':'):
            family = line[:-1]
            image['allocator_events'][family] = []
            continue
        if line.startswith('- '):
            row = json.loads(line[2:])
            if table in ('banks', 'pools'):
                image[table].append(row)
            elif table == 'allocator_events' and family is not None:
                image['allocator_events'][family].append(row)
            else:
                raise ValueError('typed row outside a declared memory_map_image table')
    if not in_image:
        raise ValueError('missing memory_map_image section')
    return image


def validate_memory_map_image(image, allocators):
    expected = {
        'banks': 16, 'pools': 27,
        'raw_resources': ('raw_resources', 1, 6),
        'linear': ('linear', 7, 4),
        'heap': ('heap', 8, 4),
        'rw_linear': ('rw_linear', 4, 2),
        'rw_general': ('rw_general', 4, 3),
    }
    for table in ('banks', 'pools'):
        rows = image[table]
        if len(rows) != expected[table]:
            raise ValueError('%s image row count %d != %d' % (table, len(rows), expected[table]))
        if [row['index'] for row in rows] != list(range(len(rows))):
            raise ValueError('%s image indexes are not contiguous table order' % table)
    for family, (allocator_key, count, event_type) in list(expected.items())[2:]:
        rows = image['allocator_events'].get(family, [])
        defs = allocators.get(allocator_key, [])
        if len(rows) != count or len(defs) != count:
            raise ValueError('%s allocator row count mismatch' % family)
        for index, (row, definition) in enumerate(zip(rows, defs)):
            if row['index'] != index:
                raise ValueError('%s image indexes are not contiguous table order' % family)
            if (row['name'], row['bank_id'], row['parent_bank_id']) != \
               (definition['name'], definition['bank'], definition['parent']):
                raise ValueError('%s typed row identity diverges from allocator definition %d' % (family, index))
            if row['event_type'] != event_type or row['event_user_offset'] != 0:
                raise ValueError('%s typed event header differs from the attested null-user/event type at row %d' % (family, index))
            if family in ('linear', 'heap'):
                if row['request_size'] != definition['size'][0]:
                    raise ValueError('%s request size diverges from allocator definition %d' % (family, index))
                if row['heap_pointer'] != 0 or row['linear_pointer'] != 0:
                    raise ValueError('%s raw allocator pointers are non-zero at row %d' % (family, index))
    if any(row['event_user_offset'] != 0 for row in image['pools']):
        raise ValueError('non-null raw pool event user is not mapped to a native pointer')
    for row in image['banks']:
        if len(row['sizes']) != 5 or len(row['blocks']) != 5:
            raise ValueError('bank row must have exactly five X360 resource lanes')
    for row in image['pools']:
        if len(row['descriptor']) != 3 or len(row['max_resources_by_type']) != 3:
            raise ValueError('pool row must have exactly three in-memory pool lanes')
        if len(row['dependency_ids']) != 16:
            raise ValueError('pool row dependency table must retain all sixteen ids')


def emit_memory_map_image(L, image, allocators, version, platform):
    bank_count = len(image['banks'])
    pool_count = len(image['pools'])
    raw_count = len(allocators['raw_resources'])
    linear_count = len(allocators['linear'])
    heap_count = len(allocators['heap'])
    rw_linear_count = len(allocators['rw_linear'])
    rw_general_count = len(allocators['rw_general'])

    L.append('')
    L.append('    // Native typed data initializer for the complete ARTIST memory-map image. This is a')
    L.append('    // PC data-initialization mechanism, not a recovered engine API. InitMemoryMap obtains')
    L.append('    // this single image, fixes it once, and GameData/statistics readers use its typed rows.')
    L.append('    struct MemoryMapImageInitializer')
    L.append('    {')
    L.append('        struct Image')
    L.append('        {')
    L.append('            CgsMemory::MemoryMap map;')
    L.append('            CgsMemory::MemoryMapBank maBanks[%d];' % bank_count)
    L.append('            CgsMemory::MemoryMapPool maPools[%d];' % pool_count)
    L.append('            CgsMemory::MemoryMapRawResource maRawResources[%d];' % raw_count)
    L.append('            CgsMemory::MemoryMapLinearAllocator maLinearAllocators[%d];' % linear_count)
    L.append('            CgsMemory::MemoryMapHeapAllocator maHeapAllocators[%d];' % heap_count)
    L.append('            CgsMemory::MemoryMapRWLinearAllocator maRWLinearAllocators[%d];' % rw_linear_count)
    L.append('            CgsMemory::MemoryMapRWGeneralAllocator maRWGeneralAllocators[%d];' % rw_general_count)
    L.append('        };')
    L.append('')
    L.append('        static Image& GetImage()')
    L.append('        {')
    L.append('            static Image lImage = {};')
    L.append('            static const bool lbInitialized = (Initialize(lImage), true);')
    L.append('            (void)lbInitialized;')
    L.append('            return lImage;')
    L.append('        }')
    L.append('')
    L.append('        static CgsMemory::MemoryMap& GetMemoryMap() { return GetImage().map; }')
    L.append('')
    L.append('    private:')
    L.append('        static std::uintptr_t OffsetFromMap(const Image& lrImage, const void* lpAddress)')
    L.append('        {')
    L.append('            return reinterpret_cast<std::uintptr_t>(lpAddress) -')
    L.append('                   reinterpret_cast<std::uintptr_t>(&lrImage.map);')
    L.append('        }')
    L.append('')
    L.append('        static void CopyFixedName(char* lpDestination, u32 luCapacity, const char* lpcSource)')
    L.append('        {')
    L.append('            u32 luIndex = 0;')
    L.append('            for (; luIndex < luCapacity && lpcSource[luIndex] != 0; ++luIndex)')
    L.append('                lpDestination[luIndex] = lpcSource[luIndex];')
    L.append('            for (; luIndex < luCapacity; ++luIndex)')
    L.append('                lpDestination[luIndex] = 0;')
    L.append('        }')
    L.append('')
    L.append('        static void Initialize(Image& lrImage)')
    L.append('        {')
    L.append('            CgsMemory::MemoryMap& lrMap = lrImage.map;')
    L.append('            lrMap.miVersion = %d;' % version)
    L.append('            lrMap.miPlatform = %d;' % platform)
    L.append('            lrMap.muNumBanks = %d;' % bank_count)
    L.append('            lrMap.muNumPools = %d;' % pool_count)
    L.append('            lrMap.muNumRawResources = %d;' % raw_count)
    L.append('            lrMap.muNumLinearAllocators = %d;' % linear_count)
    L.append('            lrMap.muNumHeapAllocators = %d;' % heap_count)
    L.append('            lrMap.muNumRWLinearAllocators = %d;' % rw_linear_count)
    L.append('            lrMap.muNumRWGeneralAllocators = %d;' % rw_general_count)
    L.append('')
    L.append('            // These are native-layout-relative table addresses; FixUp adds the same image base once.')
    for field, member, row_type in [
        ('mpBanks','maBanks','MemoryMapBank'),
        ('mpPools','maPools','MemoryMapPool'),
        ('mpRawResources','maRawResources','MemoryMapRawResource'),
        ('mpLinearAllocators','maLinearAllocators','MemoryMapLinearAllocator'),
        ('mpHeapAllocators','maHeapAllocators','MemoryMapHeapAllocator'),
        ('mpRWLinearAllocators','maRWLinearAllocators','MemoryMapRWLinearAllocator'),
        ('mpRWGeneralAllocators','maRWGeneralAllocators','MemoryMapRWGeneralAllocator'),
    ]:
        L.append('            lrMap.%s = reinterpret_cast<CgsMemory::%s*>(OffsetFromMap(lrImage, &lrImage.%s[0]));' % (field,row_type,member))
    L.append('')
    L.append('            // CgsMemory::MemoryBank::Params rows; the five size/block lanes and flags are raw ARTIST data.')
    for row in image['banks']:
        i=row['index']
        L.append('            {')
        L.append('                CgsMemory::MemoryBank::Params& lrParams = lrImage.maBanks[%d].mBankParams;' % i)
        L.append('                CopyFixedName(lrParams.macName, sizeof(lrParams.macName), "%s");' % row['name'].replace('\\','\\\\').replace('"','\\"'))
        L.append('                lrParams.mnParentBankId = %d;' % row['parent_bank_id'])
        L.append('                lrParams.mnBankId = %d;' % row['bank_id'])
        L.append('                const u32 lauSizes[5] = {%s};' % ', '.join(str(x) for x in row['sizes']))
        L.append('                const u32 lauBlocks[5] = {%s};' % ', '.join(str(x) for x in row['blocks']))
        L.append('                for (s32 liType = 0; liType < CgsMemory::MemoryBank::KI_NUM_TYPES; ++liType)')
        L.append('                {')
        L.append('                    lrParams.mauBankSize[liType] = lauSizes[liType];')
        L.append('                    lrParams.mauBankBlocks[liType] = lauBlocks[liType];')
        L.append('                }')
        L.append('                lrParams.mbIsLeaf = %s;' % ('true' if row['is_leaf'] else 'false'))
        L.append('                lrParams.mbAllowFragmentation = %s;' % ('true' if row['allow_fragmentation'] else 'false'))
        L.append('            }')
    L.append('')
    L.append('            // CgsResource::Events::CreatePoolRequest rows, including all sixteen dependency ids.')
    for row in image['pools']:
        i=row['index']
        L.append('            {')
        L.append('                CgsResource::Events::CreatePoolRequest& lrRequest = lrImage.maPools[%d].mRequest;' % i)
        L.append('                lrRequest.mpUser = nullptr;')
        L.append('                lrRequest.miEventId = %d;' % row['event_id'])
        L.append('                lrRequest.miPoolId = %d;' % row['pool_id'])
        L.append('                CopyFixedName(lrRequest.mpcName, sizeof(lrRequest.mpcName), "%s");' % row['name'].replace('\\','\\\\').replace('"','\\"'))
        L.append('                lrRequest.miDeletionDelayFrames = %d;' % row['deletion_delay_frames'])
        L.append('                lrRequest.muMaxResources = %d;' % row['max_resources'])
        L.append('                lrRequest.muMaxImports = %d;' % row['max_imports'])
        L.append('                const u32 lauSizes[3] = {%s};' % ', '.join(str(x[0]) for x in row['descriptor']))
        L.append('                const u32 lauAlignments[3] = {%s};' % ', '.join(str(x[1]) for x in row['descriptor']))
        L.append('                const u32 lauMaxResources[3] = {%s};' % ', '.join(str(x) for x in row['max_resources_by_type']))
        L.append('                for (s32 liType = 0; liType < 3; ++liType)')
        L.append('                {')
        L.append('                    lrRequest.mDescriptor.m_baseResourceDescriptors[liType].m_size = lauSizes[liType];')
        L.append('                    lrRequest.mDescriptor.m_baseResourceDescriptors[liType].m_alignment = lauAlignments[liType];')
        L.append('                    lrRequest.mauMaxResources[liType] = lauMaxResources[liType];')
        L.append('                }')
        L.append('                lrRequest.miNumDependencies = %d;' % row['num_dependencies'])
        L.append('                const s32 laiDependencyIds[16] = {%s};' % ', '.join(str(x) for x in row['dependency_ids']))
        L.append('                for (s32 liDependency = 0; liDependency < 16; ++liDependency)')
        L.append('                    lrRequest.maiDependencyIds[liDependency] = laiDependencyIds[liDependency];')
        L.append('                lrRequest.miBankId = %d;' % row['bank_id'])
        L.append('                lrRequest.miParentBankId = %d;' % row['parent_bank_id'])
        L.append('                lrRequest.mbAllowDefragmentation = %s;' % ('true' if row['allow_defragmentation'] else 'false'))
        L.append('            }')
    L.append('')
    L.append('            // The five typed allocator families use the original request event constructors and data.')
    for family, member, type_name, allocator_key in [
        ('raw_resources','maRawResources','CreateResourceRequest','raw_resources'),
        ('linear','maLinearAllocators','CreateAllocatorRequest','linear'),
        ('heap','maHeapAllocators','CreateAllocatorRequest','heap'),
        ('rw_linear','maRWLinearAllocators','CreateLinearAllocatorRequest','rw_linear'),
        ('rw_general','maRWGeneralAllocators','CreateGeneralAllocatorRequest','rw_general'),
    ]:
        rows=image['allocator_events'][family]
        defs=allocators[allocator_key]
        for row, definition in zip(rows, defs):
            i=row['index']
            L.append('            {')
            L.append('                CgsMemory::MemoryIO::%s& lrRequest = lrImage.%s[%d].mRequest;' % (type_name,member,i))
            L.append('                lrRequest.Construct(nullptr, %d);' % row['event_id'])
            L.append('                lrRequest.SetBankName("%s");' % row['name'].replace('\\','\\\\').replace('"','\\"'))
            L.append('                lrRequest.SetBankId(%d);' % row['bank_id'])
            L.append('                lrRequest.SetParentBankId(%d);' % row['parent_bank_id'])
            if family in ('linear','heap'):
                L.append('                lrRequest.SetResourceType(%d);' % row['resource_type'])
                L.append('                lrRequest.SetSize(%d);' % row['request_size'])
                L.append('                lrRequest.SetHeapAllocator(nullptr);')
                L.append('                lrRequest.SetLinearAllocator(nullptr);')
            else:
                L.append('                rw::ResourceDescriptor lrDescriptor;')
                L.append('                const u32 lauSizes[5] = {%s};' % ', '.join(str(x) for x in definition['size']))
                L.append('                const u32 lauAlignments[5] = {%s};' % ', '.join(str(x) for x in definition['align']))
                L.append('                for (s32 liType = 0; liType < static_cast<s32>(rw::KU_RESOURCE_LANE_COUNT); ++liType)')
                L.append('                {')
                L.append('                    lrDescriptor.m_baseResourceDescriptors[liType].m_size = lauSizes[liType];')
                L.append('                    lrDescriptor.m_baseResourceDescriptors[liType].m_alignment = lauAlignments[liType];')
                L.append('                }')
                L.append('                lrRequest.SetDescriptor(&lrDescriptor);')
            L.append('            }')
    L.append('        }')
    L.append('    };')

def main():
    text = open(YAML, encoding='latin1').read()
    pools = parse_pools(text)
    allocators = parse_allocators(text)
    image = parse_memory_map_image(text)
    validate_memory_map_image(image, allocators)
    version = int(re.search(r'^version:\s*(\d+)', text, re.M).group(1))
    platform = int(re.search(r'^platform:\s*(\d+)', text, re.M).group(1))
    L = []
    L.append('// GENERATED by tools/assets/memory_map/generate_header.py from progress/memory_map_artist.yaml -- do not edit by hand.')
    L.append('// The real Burnout X360 (ARTIST) resource-pool definition table (from the binary memory map')
    L.append('// unk_82F2A788). GameDataModule::CreatePools stands these up via PoolModule::CreatePool. Per-type')
    L.append('// muHeapSize is the pool\'s heap budget for memory type t (0 = type unused); the pool\'s total')
    L.append('// per-type region (descriptor) is heapSize + the pool overhead (entry arrays / hash / heap nodes),')
    L.append('// computed at create time via Pool::GetOverheadMemoryRequired.')
    L.append('#pragma once')
    L.append('')
    L.append('#include "types.hpp"')
    L.append('#include <cstdint>')
    L.append('#include "GameShared/GameClasses/Memory/MemoryMap/CgsMemoryMap.h"')
    L.append('')
    L.append('namespace BrnResource')
    L.append('{')
    L.append('    struct MemoryMapPoolDef')
    L.append('    {')
    L.append('        s32         miId;')
    L.append('        const char* mpcName;')
    L.append('        s32         miMaxHeapNodes;')
    L.append('        s32         miMaxResources;')
    L.append('        s32         miMaxImports;')
    L.append('        bool        mbAllowDefrag;')
    L.append('        u32         mauHeapSize[3];   // per memory type (0 = unused)')
    L.append('        u32         mauHeapAlign[3];')
    L.append('        s32         miNumDeps;')
    L.append('        s32         maiDeps[8];        // dependent pool ids (import sources)')
    L.append('    };')
    L.append('')
    L.append('    static const MemoryMapPoolDef KAC_MEMORY_MAP_POOLS[] =')
    L.append('    {')
    for p in pools:
        sz = [0, 0, 0]; al = [0, 0, 0]
        for (t, s, a) in p['heaps']:
            if 0 <= t < 3: sz[t] = s; al[t] = a
        deps = p['deps'][:8]
        depstr = ', '.join('%d' % d for d in deps) if deps else '0'
        cname = p['name'].replace('"', '\\"')
        L.append('        { %d, "%s", %d, %d, %d, %s, {0x%X,0x%X,0x%X}, {%d,%d,%d}, %d, {%s} },'
                 % (p['id'], cname, p['nodes'], p['maxres'], p['maximp'],
                    'true' if p['defrag'] else 'false',
                    sz[0], sz[1], sz[2], al[0], al[1], al[2], len(deps), depstr))
    L.append('    };')
    L.append('')
    L.append('    static const s32 KI_NUM_MEMORY_MAP_POOLS = %d;' % len(pools))
    L.append('')
    L.append('    // The memory map\'s five allocator record tables (unk_82F2A788 header counts @+16..+32,')
    L.append('    // table offsets @+44..+60): the definitions GameDataModule::CreateAllocators (0x8266DD00)')
    L.append('    // publishes as type-10 (raw resource) / 14 (linear + heap) / 11 (rw linear) / 12 (rw')
    L.append('    // general) create requests. miBankId keys the AllocatorList registry; miParentBankId is')
    L.append('    // the X360 CreateBanks-tree parent the leaf bank is carved from. Descriptor lanes are the')
    L.append('    // rw 5-entry {size, align} set (only lanes 0/2 are populated by the map).')
    L.append('    struct MemoryMapAllocatorDef')
    L.append('    {')
    L.append('        s32         miBankId;')
    L.append('        const char* mpcName;')
    L.append('        s32         miParentBankId;')
    L.append('        u32         mauSize[5];    // per rw memory-type lane (0 = unused)')
    L.append('        u32         mauAlign[5];')
    L.append('    };')
    L.append('')
    tbl_names = [('raw_resources', 'KAC_MEMORY_MAP_RAW_ALLOCATORS',       'KI_NUM_MEMORY_MAP_RAW_ALLOCATORS'),
                 ('linear',        'KAC_MEMORY_MAP_LINEAR_ALLOCATORS',    'KI_NUM_MEMORY_MAP_LINEAR_ALLOCATORS'),
                 ('heap',          'KAC_MEMORY_MAP_HEAP_ALLOCATORS',      'KI_NUM_MEMORY_MAP_HEAP_ALLOCATORS'),
                 ('rw_linear',     'KAC_MEMORY_MAP_RWLINEAR_ALLOCATORS',  'KI_NUM_MEMORY_MAP_RWLINEAR_ALLOCATORS'),
                 ('rw_general',    'KAC_MEMORY_MAP_RWGENERAL_ALLOCATORS', 'KI_NUM_MEMORY_MAP_RWGENERAL_ALLOCATORS')]
    for key, arr, cnt in tbl_names:
        rows = allocators.get(key, [])
        L.append('    static const MemoryMapAllocatorDef %s[] =' % arr)
        L.append('    {')
        for e in rows:
            L.append('        { %d, "%s", %d, {0x%X,0x%X,0x%X,0x%X,0x%X}, {%d,%d,%d,%d,%d} },'
                     % (e['bank'], e['name'].replace('"', '\\"'), e['parent'],
                        e['size'][0], e['size'][1], e['size'][2], e['size'][3], e['size'][4],
                        e['align'][0], e['align'][1], e['align'][2], e['align'][3], e['align'][4]))
        L.append('    };')
        L.append('    static const s32 %s = %d;' % (cnt, len(rows)))
        L.append('')
    L.pop()   # trailing blank
    emit_memory_map_image(L, image, allocators, version, platform)
    L.append('}')
    text = '\n'.join(L) + '\n'
    open(OUT, 'w', newline='\n').write(text)
    print('wrote %d pool defs -> %s' % (len(pools), os.path.normpath(OUT)))

if __name__ == '__main__':
    main()
