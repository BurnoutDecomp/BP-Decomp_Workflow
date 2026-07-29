#!/usr/bin/env python3
"""X360 (big-endian, platform-2) -> PC x64 (little-endian, platform-4) transcoder
for the ARTIST traffic / AI / trigger LANE bundles:

  B5TRAFFIC.BNDL   BrnTraffic::TrafficData     (type 65538 / 0x10002, "BaseTraffic")
  AI.DAT           BrnAI::AISectionsData       (type 65537 / 0x10001, "WorldMapData")
  TRIGGERS.DAT     BrnTrigger::TriggerData     (type 65539 / 0x10003, "TriggerData")

CONVENTION -- WIDENING REBUILD (user directive, 2026-07-29: "I don't want any file
32 bits -- of course we need to widen it/port it"). Every serialised pointer slot
becomes a real 64-bit slot, exactly as the ZoneList / PolygonSoupList / IdList ports
in world_support_transcode.py do. No Ptr32<T> / PointerFromU32 anywhere: the
committed x64 consumers (BrnTraffic::TrafficData / Hull / Pvs / FlowType,
BrnAI::AISectionsData / AISection / Portal, BrnTrigger::TriggerData / Landmark /
Killzone / SignatureStunt) declare REAL host pointers, and their FixUp bodies
relocate those 64-bit slots in place.

WHO RELOCATES THE LANE GRAPH (the "TrafficDataResourceType has no FixUp" anomaly):
it DOES have one. The DecFIGS DWARF for BrnTrafficDataResourceType.h declares all
four virtuals -- GetTypeID (cpp:40), GetSerialisedResourceDescriptor (cpp:54),
FixDown (cpp:117) and **FixUp (cpp:133)**. The X360 ARTIST symbol table simply does
not NAME the FixUp thunk (it is reached only through the type's vtable, so it has no
direct xref -- which is also why BrnTraffic::TrafficData::FixUp @0x827637D8 looks
xref-less). CgsResource::Pool::FixUpEntry calls it through the registered
CgsResource::Type. So the payload is stored with OFFSETS in every pointer slot and
the resource system rebases them at load; Hull::GetSection dereferencing mpaSections
as a real pointer is correct, post-FixUp. Nothing here stores real pointers.

LAYOUT AUTHORITY: references/DecFIGS/dwarfdump/SharedClasses/{Traffic,AI,Trigger}/*.h
(member names + order + types) run through the LAYOUT ENGINE below, which computes
both the 4-byte-pointer (console) and 8-byte-pointer (host) offsets from the same
field list. Every console offset it computes is ASSERTED against the X360-attested
offsets (CONSOLE_PIN), so a wrong field list cannot silently produce a wrong port.

BLOCK MODEL: the serialised payload is a tightly-packed set of blocks, each reached
by one or more pointer slots. The transcoder
  1. walks the pointer graph, tagging every referenced offset with its element KIND
     and count (an EMPTY array's slot points one-past-the-end, i.e. at the next
     block's start -- those references are positional only and never claim a kind);
  2. derives each block's console extent from the sorted distinct offsets;
  3. re-lays the blocks out at the host strides and builds an old->new offset map
     (interior offsets are converted through the element stride, which TriggerData's
     mppRegions table needs -- it points INTO the Landmark / GenericRegion arrays);
  4. re-emits every element field-by-field at the requested endianness and pointer
     width, rewriting each pointer slot through the map;
  5. patches the payload's own size word (TrafficData::muSizeInBytes @+4,
     AISectionsData::muSizeInBytes @+60, TriggerData::muSize @+4) to the new size.

VALIDATION (always on; --verify does it without writing):
  1. identity   emit(BE, pointer width 4) at the ORIGINAL block offsets must
                reproduce the input byte for byte, and every byte the block model
                does not cover must be zero (full-coverage proof).
  2. stride     every block's count * console stride must fit its measured extent,
                and no two live kinds may claim one offset.
  3. LE walk    the emitted LE blob is re-parsed with 8-byte pointers and the whole
                pointer graph re-walked: every relocated slot must land in range, on
                the right block, and every count must re-read identically.
  4. semantic   a fixed sample of scalar values (counts, ids, floats, grid params)
                must be equal between the BE parse and the LE re-parse.

Usage:
  py tools/assets/bundles/lane_transcode.py --bundle <in.bndl> <out.bndl>
  py tools/assets/bundles/lane_transcode.py <extracted_dir> [--verify]
  py tools/assets/bundles/lane_transcode.py --all      (convert all three in place:
      build/game_x360_world -> build/game, backing up the X360 originals first)
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')


class TranscodeError(ValueError):
    pass


def _expect(cond, what):
    if not cond:
        raise TranscodeError(what)


def align(x, a):
    return (x + a - 1) & ~(a - 1)


# =============================================================================
# LAYOUT ENGINE
# =============================================================================
# A field is (name, type, count). Types:
#   u8 s8 u16 s16 u32 s32 f32 u64 s64   -- scalars
#   id                                   -- CgsID (u64)
#   v3 v4                                -- rw::math::vpu Vector3 / Vector4 (16B, align 16)
#   v2                                   -- Vector2Template<float> (8B, align 4)
#   m44a                                 -- Matrix44Affine (64B, align 16)
#   ptr:<Kind>                           -- pointer slot; <Kind> names the pointee kind
#   @<Name>                              -- embedded aggregate declared in STRUCTS

_SCALAR = {
    'u8': (1, 1), 's8': (1, 1), 'u16': (2, 2), 's16': (2, 2),
    'u32': (4, 4), 's32': (4, 4), 'f32': (4, 4),
    'u64': (8, 8), 's64': (8, 8), 'id': (8, 8),
    'v2': (8, 4), 'v3': (16, 16), 'v4': (16, 16), 'm44a': (64, 16),
}

STRUCTS = {}      # name -> list of fields
CONSOLE_PIN = {}  # name -> (console size, {member: console offset})


def _size_align(ty, pw):
    if ty in _SCALAR:
        return _SCALAR[ty]
    if ty.startswith('ptr:'):
        return (pw, pw)
    if ty.startswith('@'):
        lay = layout(ty[1:], pw)
        return (lay['size'], lay['align'])
    raise TranscodeError('unknown field type %r' % ty)


_LAYOUT_CACHE = {}


def layout(name, pw):
    key = (name, pw)
    if key in _LAYOUT_CACHE:
        return _LAYOUT_CACHE[key]
    fields = STRUCTS[name]
    off, maxal, out = 0, 1, []
    for fname, ty, n in fields:
        sz, al = _size_align(ty, pw)
        off = align(off, al)
        out.append((fname, ty, off, n, sz))
        off += sz * n
        maxal = max(maxal, al)
    res = {'size': align(off, maxal), 'align': maxal, 'fields': out,
           'off': dict((f[0], f[2]) for f in out)}
    _LAYOUT_CACHE[key] = res
    return res


def check_console_pins():
    """Every console (pw=4) offset the engine computes must match the X360 truth."""
    for name, (size, offs) in CONSOLE_PIN.items():
        lay = layout(name, 4)
        _expect(lay['size'] == size,
                '%s console sizeof: engine %d != X360 %d' % (name, lay['size'], size))
        for m, o in offs.items():
            _expect(lay['off'][m] == o,
                    '%s.%s console offset: engine %d != X360 %d' % (name, m, lay['off'][m], o))


# ---------------------------------------------------------------- traffic ---
STRUCTS['TrafficLightController'] = [        # BrnJunctionLogicBox.h:51
    ('mauTrafficLightIds', 'u16', 2), ('mauStopLineIds', 'u8', 6),
    ('mauStopLineHulls', 'u16', 6), ('muNumStopLines', 'u8', 1),
    ('muNumTrafficLights', 'u8', 1)]
STRUCTS['JunctionLogicBox'] = [              # BrnJunctionLogicBox.h:77
    ('muID', 'u32', 1), ('mauStateTimings', 'u16', 16),
    ('mauStoppedLightStates', 'u8', 16), ('muNumStates', 'u8', 1),
    ('muNumLights', 'u8', 1), ('muEventJunctionID', 'u32', 1),
    ('miOfflineStartDataIndex', 's32', 1), ('miOnlineStartDataIndex', 's32', 1),
    ('maTrafficLightControllers', '@TrafficLightController', 8),
    ('mPosition', 'v3', 1)]
STRUCTS['TrafficLightCollection'] = [        # BrnTrafficLightCollection.h:78
    ('muNumTrafficLights', 'u16', 1), ('muNumTrafficLightTypes', 'u16', 1),
    ('muNumCoronas', 'u16', 1),
    ('mpaPosAndYRotations', 'ptr:Vector3Plus', 1),
    ('mpaInstanceIDs', 'ptr:u32', 1),
    ('mpauInstanceTypes', 'ptr:u8', 1),
    ('mpaTrafficLightTypes', 'ptr:TrafficLightType', 1),
    ('mpaCoronaTypes', 'ptr:u8', 1),
    ('mpaCoronaPositions', 'ptr:Vector3', 1),
    ('mauInstanceHashOffsets', 'u16', 129),
    ('mpauInstanceHashTable', 'ptr:u32', 1),
    ('mpauInstanceHashToIndexLookup', 'ptr:u16', 1)]
STRUCTS['TrafficData'] = [                   # BrnTrafficData.h:54
    ('muDataVersion', 'u8', 1), ('muNumHulls', 'u16', 1), ('muSizeInBytes', 'u32', 1),
    ('mpPvs', 'ptr:Pvs', 1), ('mpapHulls', 'ptr:HullPtr', 1),
    ('mpapFlowTypes', 'ptr:FlowPtr', 1),
    ('muNumFlowTypes', 'u16', 1), ('muNumVehicleTypes', 'u16', 1),
    ('muNumVehicleAssets', 'u8', 1), ('muNumVehicleTraits', 'u8', 1),
    ('muNumKillZones', 'u16', 1), ('muNumKillZoneRegions', 'u16', 1),
    ('mpaKillZoneIds', 'ptr:KillZoneId', 1), ('mpaKillZones', 'ptr:KillZone', 1),
    ('mpaKillZoneRegions', 'ptr:KillZoneRegion', 1),
    ('mpaVehicleTypes', 'ptr:VehicleTypeData', 1),
    ('mpaVehicleTypesUpdate', 'ptr:VehicleTypeUpdateData', 1),
    ('mpaVehicleAssets', 'ptr:VehicleAsset', 1),
    ('mpaVehicleTraits', 'ptr:VehicleTraits', 1),
    ('mTrafficLights', '@TrafficLightCollection', 1),
    ('muNumPaintColours', 'u8', 1), ('mpaPaintColours', 'ptr:Vector4', 1)]
STRUCTS['Pvs'] = [                           # BrnTrafficPvs.h:46
    ('mGridMin', 'v3', 1), ('mCellSize', 'v3', 1), ('mRecipCellSize', 'v3', 1),
    ('muNumCells_X', 'u32', 1), ('muNumCells_Z', 'u32', 1), ('muNumCells', 'u32', 1),
    ('mpaHullPvs', 'ptr:SetU16x8', 1)]
STRUCTS['Hull'] = [                          # BrnTrafficHull.h:53
    ('muNumSections', 'u8', 1), ('muNumSectionSpans', 'u8', 1),
    ('muNumJunctions', 'u8', 1), ('muNumStoplines', 'u8', 1),
    ('muNumNeighbours', 'u8', 1), ('muNumStaticTraffic', 'u8', 1),
    ('muNumVehicleAssets', 'u8', 1), ('muNumRungs', 'u16', 1),
    ('muFirstTrafficLight', 'u16', 1), ('muLastTrafficLight', 'u16', 1),
    ('muNumLightTriggers', 'u8', 1), ('muNumLightTriggersStartData', 'u8', 1),
    ('mpaSections', 'ptr:Section', 1), ('mpaRungs', 'ptr:LaneRung', 1),
    ('mpafCumulativeRungLengths', 'ptr:f32', 1),
    ('mpaNeighbourData', 'ptr:Neighbour', 1),
    ('mpaSectionSpans', 'ptr:SectionSpan', 1),
    ('mpaStaticTrafficVehicles', 'ptr:StaticTrafficVehicle', 1),
    ('mpaSectionFlows', 'ptr:SectionFlow', 1),
    ('mpaJunctions', 'ptr:JunctionLogicBox', 1),
    ('mpaStopLines', 'ptr:StopLine', 1),
    ('mpaLightTriggers', 'ptr:LightTrigger', 1),
    ('mpaLightTriggerStartData', 'ptr:LightTriggerStartData', 1),
    ('mpaLightTriggerJunctionLookup', 'ptr:u8', 1),
    ('mauVehicleAssets', 'u8', 16)]
STRUCTS['FlowType'] = [                      # BrnTrafficFlowType.h:45
    ('mpauVehicleTypeIds', 'ptr:u16', 1), ('mpauCumulativeProb', 'ptr:u8', 1),
    ('muNumVehicleTypes', 'u8', 1)]
STRUCTS['Section'] = [                       # BrnTrafficSection.h:106
    ('muRungOffset', 'u32', 1), ('muNumRungs', 'u8', 1),
    ('muStopLineOffset', 'u8', 1), ('muNumStopLines', 'u8', 1),
    ('muSpanIndex', 'u8', 1),
    ('mauForwardHulls', 'u16', 3), ('mauBackwardHulls', 'u16', 3),
    ('mauForwardSections', 'u8', 3), ('mauBackwardSections', 'u8', 3),
    ('muTurnLeftProb', 'u8', 1), ('muTurnRightProb', 'u8', 1),
    ('muNeighbourOffset', 'u16', 1),
    ('muLeftNeighbourCount', 'u8', 1), ('muRightNeighbourCount', 'u8', 1),
    ('muChangeLeftProb', 'u8', 1), ('muChangeRightProb', 'u8', 1),
    ('mfSpeed', 'f32', 1), ('mfLength', 'f32', 1),
    # FLAG (serialised tail pad): the DWARF member list sums to 44 but the shipped
    # record stride is 48 (Hull::GetSection @0x821F52E0 indexes with (i*3)<<4, and
    # the block-extent check over all 315 hulls confirms 48). Modelled as an
    # explicit trailing pad so host sizeof(Section) == 48 too.
    ('maPad2C', 'u8', 4)]
STRUCTS['LaneRung'] = [('maPoints', 'v3', 2)]
STRUCTS['Neighbour'] = [('muSection', 'u8', 1), ('muSharedLength', 'u8', 1),
                        ('muOurStartRung', 'u8', 1), ('muTheirStartRung', 'u8', 1)]
STRUCTS['SectionSpan'] = [('muMaxVehicles', 'u16', 1), ('mfMaxVehicleRecip', 'f32', 1)]
STRUCTS['StaticTrafficVehicle'] = [('mTransform', 'm44a', 1), ('mFlowTypeID', 'u16', 1),
                                   ('mExistsAtAllChance', 'u8', 1), ('muFlags', 'u8', 1)]
STRUCTS['SectionFlow'] = [('muFlowTypeId', 'u16', 1), ('muVehiclesPerMinute', 'u16', 1)]
STRUCTS['StopLine'] = [('muParamFixed', 'u16', 1)]
STRUCTS['LightTrigger'] = [('mDimensions', 'v3', 1), ('mPosPlusYRot', 'v3', 1)]
STRUCTS['LightTriggerStartData'] = [
    ('maStartingPositions', 'v3', 8), ('maStartingDirections', 'v3', 8),
    ('maDestinationIDs', 'id', 16), ('maeDestinationDifficulties', 'u8', 16),
    ('muNumStartingPositions', 'u8', 1), ('muNumDestinations', 'u8', 1),
    ('muNumLanes', 'u8', 1)]
STRUCTS['SetU16x8'] = [('maElements', 'u16', 8), ('muLength', 'u32', 1)]
STRUCTS['KillZoneId'] = [('mId', 'u64', 1)]
STRUCTS['KillZone'] = [('muOffset', 'u16', 1), ('muCount', 'u8', 1)]
STRUCTS['KillZoneRegion'] = [('muHull', 'u16', 1), ('muSection', 'u8', 1),
                             ('muStartRung', 'u8', 1), ('muEndRung', 'u8', 1)]
STRUCTS['VehicleTypeData'] = [('muTrailerFlowTypeId', 'u16', 1), ('mxVehicleFlags', 'u8', 1),
                              ('muVehicleClass', 'u8', 1), ('muInitialDirt', 'u8', 1),
                              ('muAssetId', 'u8', 1), ('muTraitsId', 'u8', 1),
                              # X360 record stride is 8 (mpaVehicleTypesUpdate -
                              # mpaVehicleTypes == 30 * 8); the DWARF list sums to 7.
                              ('maPad7', 'u8', 1)]
STRUCTS['VehicleTypeUpdateData'] = [('mfWheelRadius', 'f32', 1), ('mfSuspensionRoll', 'f32', 1),
                                    ('mfSuspensionPitch', 'f32', 1),
                                    ('mfSuspensionTravel', 'f32', 1), ('mfMass', 'f32', 1)]
STRUCTS['VehicleAsset'] = [('mVehicleId', 'id', 1)]
STRUCTS['VehicleTraits'] = [('mfSwervingAmountModifier', 'f32', 1), ('mfAcceleration', 'f32', 1),
                            ('muCuttingUpChance', 'u8', 1), ('muTailgatingChance', 'u8', 1),
                            ('muPatience', 'u8', 1), ('muTantrumAttackCumProb', 'u8', 1),
                            ('muTantrumStopCumProb', 'u8', 1)]
STRUCTS['TrafficLightType'] = [('muCoronaOffset', 'u8', 1), ('muNumCoronas', 'u8', 1)]
STRUCTS['Vector3'] = [('v', 'v3', 1)]
STRUCTS['Vector3Plus'] = [('v', 'v3', 1)]
STRUCTS['Vector4'] = [('v', 'v4', 1)]
STRUCTS['Vector2'] = [('v', 'v2', 1)]
STRUCTS['u8'] = [('v', 'u8', 1)]
STRUCTS['u16'] = [('v', 'u16', 1)]
STRUCTS['u32'] = [('v', 'u32', 1)]
STRUCTS['f32'] = [('v', 'f32', 1)]
STRUCTS['CgsID'] = [('v', 'id', 1)]
STRUCTS['HullPtr'] = [('p', 'ptr:Hull', 1)]
STRUCTS['FlowPtr'] = [('p', 'ptr:FlowType', 1)]

CONSOLE_PIN['TrafficData'] = (0x170, {
    'muSizeInBytes': 4, 'mpPvs': 8, 'mpapHulls': 0x0C, 'mpapFlowTypes': 0x10,
    'muNumFlowTypes': 0x14, 'muNumVehicleTypes': 0x16, 'muNumVehicleAssets': 0x18,
    'muNumVehicleTraits': 0x19, 'muNumKillZones': 0x1A, 'muNumKillZoneRegions': 0x1C,
    'mpaKillZoneIds': 0x20, 'mpaKillZones': 0x24, 'mpaKillZoneRegions': 0x28,
    'mpaVehicleTypes': 0x2C, 'mpaVehicleTypesUpdate': 0x30, 'mpaVehicleAssets': 0x34,
    'mpaVehicleTraits': 0x38, 'mTrafficLights': 0x3C, 'muNumPaintColours': 0x168,
    'mpaPaintColours': 0x16C})
CONSOLE_PIN['TrafficLightCollection'] = (0x12C, {
    'mpaPosAndYRotations': 8, 'mpauInstanceHashTable': 0x124,
    'mpauInstanceHashToIndexLookup': 0x128})
CONSOLE_PIN['Pvs'] = (0x40, {'muNumCells_X': 0x30, 'muNumCells': 0x38, 'mpaHullPvs': 0x3C})
CONSOLE_PIN['Hull'] = (0x50, {'muNumRungs': 8, 'mpaSections': 0x10, 'mauVehicleAssets': 0x40})
CONSOLE_PIN['FlowType'] = (0x0C, {'muNumVehicleTypes': 8})
CONSOLE_PIN['Section'] = (48, {'mfSpeed': 36, 'mfLength': 40})
CONSOLE_PIN['JunctionLogicBox'] = (0x120, {'mPosition': 0x110})
CONSOLE_PIN['LightTriggerStartData'] = (0x1A0, {'maDestinationIDs': 0x100})
CONSOLE_PIN['StaticTrafficVehicle'] = (80, {'mFlowTypeID': 64})
CONSOLE_PIN['SetU16x8'] = (20, {'muLength': 16})

# --------------------------------------------------------------------- AI ---
STRUCTS['AISectionsData'] = [                # AISectionsData.h:568
    ('mpaSections', 'ptr:AISection', 1), ('mpaSectionResetPairs', 'ptr:SectionResetPair', 1),
    ('mafSectionMinSpeeds', 'f32', 5), ('mafSectionMaxSpeeds', 'f32', 5),
    ('muNumSections', 'u32', 1), ('muNumSectionResetPairs', 'u32', 1),
    ('muVersion', 'u32', 1), ('muSizeInBytes', 'u32', 1)]
STRUCTS['AISection'] = [                     # AISectionsData.h:339
    ('mpaPortals', 'ptr:Portal', 1), ('mpaNoGoLines', 'ptr:BoundaryLine', 1),
    ('mpaCorners', 'ptr:Vector2', 1), ('mId', 'u32', 1), ('miSpanIndex', 's16', 1),
    ('muNumNoGoLines', 'u16', 1), ('mu8NumPortals', 'u8', 1), ('muSpeed', 'u8', 1),
    ('mu8eDistrict', 'u8', 1), ('mx8Flags', 'u8', 1)]
STRUCTS['Portal'] = [
    ('mPositionX', 'f32', 1), ('mPositionY', 'f32', 1), ('mPositionZ', 'f32', 1),
    ('mpaBoundaryLines', 'ptr:BoundaryLine', 1), ('mu16LinkSection', 'u16', 1),
    ('mu8NumBoundaryLines', 'u8', 1), ('mau8Pad', 'u8', 1)]
STRUCTS['BoundaryLine'] = [('mVerts', 'v4', 1)]
STRUCTS['SectionResetPair'] = [('meResetSpeed', 'u32', 1), ('muStartSectionIndex', 'u16', 1),
                               ('muResetSectionIndex', 'u16', 1)]
CONSOLE_PIN['AISectionsData'] = (0x40, {'mafSectionMinSpeeds': 8, 'muNumSections': 0x30,
                                        'muSizeInBytes': 0x3C})
CONSOLE_PIN['AISection'] = (24, {'mId': 12, 'mu8NumPortals': 20, 'mx8Flags': 23})
CONSOLE_PIN['Portal'] = (20, {'mpaBoundaryLines': 0x0C, 'mu8NumBoundaryLines': 0x12})

# ---------------------------------------------------------------- trigger ---
STRUCTS['BoxRegion'] = [                     # BrnRegion.h:128
    ('mPositionX', 'f32', 1), ('mPositionY', 'f32', 1), ('mPositionZ', 'f32', 1),
    ('mRotationX', 'f32', 1), ('mRotationY', 'f32', 1), ('mRotationZ', 'f32', 1),
    ('mDimensionX', 'f32', 1), ('mDimensionY', 'f32', 1), ('mDimensionZ', 'f32', 1)]
STRUCTS['TriggerRegion'] = [                 # BrnTriggerBase.h
    ('mBoxRegion', '@BoxRegion', 1), ('mId', 's32', 1), ('miRegionIndex', 's16', 1),
    ('meType', 'u8', 1), ('muPad', 'u8', 1)]
STRUCTS['StartingGrid'] = [('maStartingPositions', 'v3', 8), ('maStartingDirections', 'v3', 8)]
STRUCTS['Landmark'] = [
    ('_base', '@TriggerRegion', 1), ('mpaStartingGrids', 'ptr:StartingGrid', 1),
    ('miStartingGridCount', 's8', 1), ('muDesignIndex', 'u8', 1),
    ('muDistrict', 'u8', 1), ('mu8Flags', 'u8', 1)]
STRUCTS['SignatureStunt'] = [
    ('mId', 'id', 1), ('miCamera', 's64', 1),
    ('mppStuntElements', 'ptr:GenericRegionPtr', 1), ('miStuntElementCount', 's32', 1)]
STRUCTS['GenericRegion'] = [
    ('_base', '@TriggerRegion', 1), ('miGroupID', 's32', 1),
    ('miCameraCut1', 's16', 1), ('miCameraCut2', 's16', 1),
    ('miCameraType1', 's8', 1), ('miCameraType2', 's8', 1),
    ('meType', 'u8', 1), ('miIsOneWay', 's8', 1)]
STRUCTS['Blackspot'] = [('_base', '@TriggerRegion', 1), ('muScoreType', 'u8', 1),
                        ('miScoreAmount', 's32', 1)]
STRUCTS['VFXBoxRegion'] = [('_base', '@TriggerRegion', 1)]
STRUCTS['RoamingLocation'] = [('mPosition', 'v3', 1), ('muDistrictIndex', 'u8', 1)]
STRUCTS['SpawnLocation'] = [('mPosition', 'v3', 1), ('mDirection', 'v3', 1),
                            ('mJunkyardId', 'id', 1), ('muType', 'u8', 1)]
STRUCTS['Killzone'] = [('mppTriggers', 'ptr:GenericRegionPtr', 1), ('miTriggerCount', 's32', 1),
                       ('mpRegionIds', 'ptr:CgsID', 1), ('miRegionIdCount', 's32', 1)]
STRUCTS['RegionPtr'] = [('p', 'ptr:*', 1)]           # points into Landmark/GenericRegion/...
STRUCTS['GenericRegionPtr'] = [('p', 'ptr:GenericRegion', 1)]
STRUCTS['TriggerData'] = [                   # BrnTriggerData.h
    ('miVersionNumber', 's32', 1), ('muSize', 'u32', 1),
    ('mPlayerStartPosition', 'v3', 1), ('mPlayerStartDirection', 'v3', 1),
    ('mpLandmarks', 'ptr:Landmark', 1), ('miLandmarkCount', 's32', 1),
    ('miOnlineLandmarkCount', 's32', 1),
    ('mpSignatureStunts', 'ptr:SignatureStunt', 1), ('miSignatureStuntCount', 's32', 1),
    ('mpGenericRegions', 'ptr:GenericRegion', 1), ('miGenericRegionCount', 's32', 1),
    ('mpKillzones', 'ptr:Killzone', 1), ('miKillzoneCount', 's32', 1),
    ('mpBlackspots', 'ptr:Blackspot', 1), ('miBlackspotCount', 's32', 1),
    ('mpVFXBoxRegions', 'ptr:VFXBoxRegion', 1), ('miVFXBoxRegionCount', 's32', 1),
    ('mpRoamingLocations', 'ptr:RoamingLocation', 1), ('miRoamingLocationCount', 's32', 1),
    ('mpSpawnLocations', 'ptr:SpawnLocation', 1), ('miSpawnLocationCount', 's32', 1),
    ('mppRegions', 'ptr:RegionPtr', 1), ('miRegionCount', 's32', 1)]
CONSOLE_PIN['TriggerData'] = (0x80, {
    'mPlayerStartPosition': 0x10, 'mpLandmarks': 0x30, 'miLandmarkCount': 0x34,
    'miOnlineLandmarkCount': 0x38, 'mpSignatureStunts': 0x3C, 'mpGenericRegions': 0x44,
    'mpKillzones': 0x4C, 'mpBlackspots': 0x54, 'mpVFXBoxRegions': 0x5C,
    'mpRoamingLocations': 0x64, 'mpSpawnLocations': 0x6C, 'mppRegions': 0x74,
    'miRegionCount': 0x78})
CONSOLE_PIN['TriggerRegion'] = (44, {'mId': 0x24, 'miRegionIndex': 0x28, 'meType': 0x2A})
CONSOLE_PIN['Landmark'] = (52, {'mpaStartingGrids': 0x2C, 'miStartingGridCount': 0x30})
CONSOLE_PIN['SignatureStunt'] = (24, {'mppStuntElements': 0x10, 'miStuntElementCount': 0x14})
CONSOLE_PIN['GenericRegion'] = (56, {'miGroupID': 0x2C})
CONSOLE_PIN['Killzone'] = (16, {'miTriggerCount': 4, 'mpRegionIds': 8, 'miRegionIdCount': 0x0C})
CONSOLE_PIN['SpawnLocation'] = (48, {'mDirection': 0x10, 'mJunkyardId': 0x20})
CONSOLE_PIN['Blackspot'] = (52, {'miScoreAmount': 0x30})
CONSOLE_PIN['StartingGrid'] = (256, {'maStartingDirections': 0x80})

check_console_pins()


# =============================================================================
# READ / WRITE
# =============================================================================
_FMT = {'u8': 'B', 's8': 'b', 'u16': 'H', 's16': 'h', 'u32': 'I', 's32': 'i',
        'f32': 'f', 'u64': 'Q', 's64': 'q', 'id': 'Q'}


def rd(buf, off, ty, pw, end='>'):
    if ty in _FMT:
        return struct.unpack_from(end + _FMT[ty], buf, off)[0]
    if ty == 'v2':
        return struct.unpack_from(end + '2f', buf, off)
    if ty in ('v3', 'v4'):
        return struct.unpack_from(end + '4f', buf, off)
    if ty == 'm44a':
        return struct.unpack_from(end + '16f', buf, off)
    if ty.startswith('ptr:'):
        return struct.unpack_from(end + ('I' if pw == 4 else 'Q'), buf, off)[0]
    raise TranscodeError('rd %r' % ty)


def wr(buf, off, ty, val, pw, end='<'):
    if ty in _FMT:
        struct.pack_into(end + _FMT[ty], buf, off, val)
    elif ty == 'v2':
        struct.pack_into(end + '2f', buf, off, *val)
    elif ty in ('v3', 'v4'):
        struct.pack_into(end + '4f', buf, off, *val)
    elif ty == 'm44a':
        struct.pack_into(end + '16f', buf, off, *val)
    elif ty.startswith('ptr:'):
        struct.pack_into(end + ('I' if pw == 4 else 'Q'), buf, off, val)
    else:
        raise TranscodeError('wr %r' % ty)


def copy_element(src, soff, dst, doff, kind, spw, dpw, send, dend, remap):
    """Field-by-field re-emit of one element of `kind`."""
    sl = layout(kind, spw)['fields']
    dl = layout(kind, dpw)['off']
    for fname, ty, soffs, n, _ in sl:
        dbase = dl[fname]
        if ty.startswith('@'):
            sub = ty[1:]
            ssz = layout(sub, spw)['size']
            dsz = layout(sub, dpw)['size']
            for i in range(n):
                copy_element(src, soff + soffs + i * ssz, dst, doff + dbase + i * dsz,
                             sub, spw, dpw, send, dend, remap)
            continue
        ssz = _size_align(ty, spw)[0]
        dsz = _size_align(ty, dpw)[0]
        for i in range(n):
            v = rd(src, soff + soffs + i * ssz, ty, spw, send)
            if ty.startswith('ptr:'):
                v = remap(v, ty[4:])
            wr(dst, doff + dbase + i * dsz, ty, v, dpw, dend)


# =============================================================================
# BLOCK MODEL
# =============================================================================
class Model(object):
    def __init__(self, data, root_kind):
        self.d = data
        self.root_kind = root_kind
        self.refs = []                        # (target, kind, count, tag)
        self.blocks = []                      # (start, end, kind, count)

    def add(self, target, kind, count, tag):
        self.refs.append((target, kind, count, tag))

    def rd(self, off, ty):
        return rd(self.d, off, ty, 4, '>')

    def f(self, kind, base, member, ty=None):
        lay = layout(kind, 4)
        for fname, fty, foff, n, _ in lay['fields']:
            if fname == member:
                return rd(self.d, base + foff, ty or fty, 4, '>')
        raise TranscodeError('%s has no member %s' % (kind, member))

    # ---- partition -------------------------------------------------------
    def build(self):
        N = len(self.d)
        byoff = defaultdict(list)
        for t, k, c, g in self.refs:
            _expect(0 <= t <= N, 'pointer 0x%X out of payload (%s)' % (t, g))
            byoff[t].append((k, c, g))
        offs = sorted(set(list(byoff) + [0, N]))
        blocks = []
        rootsz = layout(self.root_kind, 4)['size']
        blocks.append((0, min(o for o in offs if o > 0), self.root_kind, 1))
        for i, off in enumerate(offs):
            if off == 0 or off == N:
                continue
            nxt = offs[i + 1] if i + 1 < len(offs) else N
            live = [(k, c, g) for k, c, g in byoff[off] if c > 0]
            if not live:
                # No slot with a KNOWN positive count starts here. A slot whose count
                # the graph does not expose (count == -1: mpaSectionFlows,
                # mpaLightTriggerJunctionLookup, mpaCoronaTypes, mpaCoronaPositions --
                # all flip-only element types whose console and host strides are equal)
                # still owns these bytes, so make it the block and take the count from
                # the measured extent. A slot with count == 0 is a one-past-the-end
                # alias of the NEXT block and never claims anything.
                unk = [(k, c, g) for k, c, g in byoff[off] if c < 0]
                if not unk:
                    continue
                ukinds = set(k for k, _, _ in unk)
                _expect(len(ukinds) == 1,
                        'offset 0x%X claimed by unsized %s (%s)'
                        % (off, ukinds, [g for _, _, g in unk][:3]))
                k, _, g = unk[0]
                _expect(layout(k, 4)['size'] == layout(k, 8)['size'],
                        'unsized block 0x%X kind %s widens -- a real count is required' % (off, k))
                live = [(k, (nxt - off) // layout(k, 4)['size'], g)]
            kinds = set(k for k, _, _ in live)
            _expect(len(kinds) == 1,
                    'offset 0x%X claimed by %s (%s)' % (off, kinds, [g for _, _, g in live][:3]))
            k, c, g = live[0]
            need = layout(k, 4)['size'] * c
            _expect(need <= nxt - off,
                    'block 0x%X %s count %d needs %d but extent is %d (%s)'
                    % (off, k, c, need, nxt - off, g))
            blocks.append((off, nxt, k, c))
        blocks.sort()
        # merge: consecutive blocks must tile [0, N)
        self.blocks = blocks
        self.rootsz = rootsz
        return blocks

    # ---- placement -------------------------------------------------------
    def place(self, pw, identity):
        """Return {console_start: new_start} and the new total size."""
        self.new = {}
        if identity:
            for s, e, k, c in self.blocks:
                self.new[s] = s
            self.total = len(self.d)
            self.newext = dict((s, e - s) for s, e, k, c in self.blocks)
            return
        cur = 0
        self.newext = {}
        for s, e, k, c in self.blocks:
            lay = layout(k, pw)
            cur = align(cur, max(lay['align'], 16))
            self.new[s] = cur
            grew = lay['size'] != layout(k, 4)['size']
            size = lay['size'] * c if grew else (e - s)
            self.newext[s] = size
            cur += size
        self.total = align(cur, 16)

    # ---- remap -----------------------------------------------------------
    def make_remap(self, pw, identity):
        starts = [b[0] for b in self.blocks]
        blocks = self.blocks
        new = self.new
        total = self.total
        N = len(self.d)
        import bisect

        def remap(t, expect_kind=None):
            if t == N:
                return total
            i = bisect.bisect_right(starts, t) - 1
            _expect(0 <= i < len(blocks), 'remap 0x%X: no block' % t)
            s, e, k, c = blocks[i]
            _expect(s <= t < e, 'remap 0x%X outside block 0x%X..0x%X' % (t, s, e))
            cs = layout(k, 4)['size']
            hs = layout(k, pw)['size']
            d = t - s
            if cs != hs:
                _expect(d % cs == 0,
                        'remap 0x%X: interior offset %d in widened %s (stride %d)' % (t, d, k, cs))
                return new[s] + (d // cs) * hs
            return new[s] + d
        return remap

    # ---- emit ------------------------------------------------------------
    def emit(self, pw, end, identity=False):
        self.place(pw, identity)
        remap = self.make_remap(pw, identity)
        out = bytearray(self.total)
        covered = 0
        for s, e, k, c in self.blocks:
            cs = layout(k, 4)['size']
            hs = layout(k, pw)['size']
            base = self.new[s]
            n = c if cs != hs else (e - s) // cs
            for i in range(n):
                copy_element(self.d, s + i * cs, out, base + i * hs, k, 4, pw, '>', end, remap)
            covered += n * cs
        self.covered = covered
        return bytes(out), remap


# =============================================================================
# PER-FORMAT GRAPH WALKS
# =============================================================================
def model_trafficdata(d):
    m = Model(d, 'TrafficData')
    g = lambda mem, ty=None: m.f('TrafficData', 0, mem, ty)
    tlc = layout('TrafficData', 4)['off']['mTrafficLights']
    t = lambda mem, ty=None: m.f('TrafficLightCollection', tlc, mem, ty)

    nHulls = g('muNumHulls')
    nFlow = g('muNumFlowTypes')
    nVehType = g('muNumVehicleTypes')
    nTL = t('muNumTrafficLights')

    m.add(g('mpPvs'), 'Pvs', 1, 'root.mpPvs')
    m.add(g('mpapHulls'), 'HullPtr', nHulls, 'root.mpapHulls')
    m.add(g('mpapFlowTypes'), 'FlowPtr', nFlow, 'root.mpapFlowTypes')
    m.add(g('mpaKillZoneIds'), 'KillZoneId', g('muNumKillZones'), 'root.mpaKillZoneIds')
    m.add(g('mpaKillZones'), 'KillZone', g('muNumKillZones'), 'root.mpaKillZones')
    m.add(g('mpaKillZoneRegions'), 'KillZoneRegion', g('muNumKillZoneRegions'), 'root.KZR')
    m.add(g('mpaVehicleTypes'), 'VehicleTypeData', nVehType, 'root.mpaVehicleTypes')
    m.add(g('mpaVehicleTypesUpdate'), 'VehicleTypeUpdateData', nVehType, 'root.VTU')
    m.add(g('mpaVehicleAssets'), 'VehicleAsset', g('muNumVehicleAssets'), 'root.VA')
    m.add(g('mpaVehicleTraits'), 'VehicleTraits', g('muNumVehicleTraits'), 'root.VT')
    m.add(g('mpaPaintColours'), 'Vector4', g('muNumPaintColours'), 'root.paint')
    m.add(t('mpaPosAndYRotations'), 'Vector3Plus', nTL, 'tlc.pos')
    m.add(t('mpaInstanceIDs'), 'u32', nTL, 'tlc.ids')
    m.add(t('mpauInstanceTypes'), 'u8', nTL, 'tlc.types')
    m.add(t('mpaTrafficLightTypes'), 'TrafficLightType', t('muNumTrafficLightTypes'), 'tlc.tlt')
    m.add(t('mpaCoronaTypes'), 'u8', -1, 'tlc.coronaTypes')
    m.add(t('mpaCoronaPositions'), 'Vector3', -1, 'tlc.coronaPos')
    m.add(t('mpauInstanceHashTable'), 'u32', nTL, 'tlc.hashTable')
    m.add(t('mpauInstanceHashToIndexLookup'), 'u16', nTL, 'tlc.hashLookup')

    pvs = g('mpPvs')
    m.add(m.f('Pvs', pvs, 'mpaHullPvs'), 'SetU16x8', m.f('Pvs', pvs, 'muNumCells'), 'pvs.hullpvs')

    hullarr = g('mpapHulls')
    HP = [('mpaSections', 'Section', 'muNumSections'),
          ('mpaRungs', 'LaneRung', 'muNumRungs'),
          ('mpafCumulativeRungLengths', 'f32', 'muNumRungs'),
          ('mpaNeighbourData', 'Neighbour', 'muNumNeighbours'),
          ('mpaSectionSpans', 'SectionSpan', 'muNumSectionSpans'),
          ('mpaStaticTrafficVehicles', 'StaticTrafficVehicle', 'muNumStaticTraffic'),
          ('mpaSectionFlows', 'SectionFlow', None),
          ('mpaJunctions', 'JunctionLogicBox', 'muNumJunctions'),
          ('mpaStopLines', 'StopLine', 'muNumStoplines'),
          ('mpaLightTriggers', 'LightTrigger', 'muNumLightTriggers'),
          ('mpaLightTriggerStartData', 'LightTriggerStartData', 'muNumLightTriggersStartData'),
          ('mpaLightTriggerJunctionLookup', 'u8', None)]
    for i in range(nHulls):
        ho = rd(d, hullarr + 4 * i, 'ptr:Hull', 4, '>')
        m.add(ho, 'Hull', 1, 'hull[%d]' % i)
        for pn, kind, cn in HP:
            cnt = m.f('Hull', ho, cn) if cn else -1
            m.add(m.f('Hull', ho, pn), kind, cnt, 'hull[%d].%s' % (i, pn))

    flowarr = g('mpapFlowTypes')
    for i in range(nFlow):
        fo = rd(d, flowarr + 4 * i, 'ptr:FlowType', 4, '>')
        m.add(fo, 'FlowType', 1, 'flow[%d]' % i)
        n = m.f('FlowType', fo, 'muNumVehicleTypes')
        m.add(m.f('FlowType', fo, 'mpauVehicleTypeIds'), 'u16', n, 'flow[%d].ids' % i)
        m.add(m.f('FlowType', fo, 'mpauCumulativeProb'), 'u8', n, 'flow[%d].prob' % i)
    return m


def model_aisections(d):
    m = Model(d, 'AISectionsData')
    g = lambda mem: m.f('AISectionsData', 0, mem)
    ns = g('muNumSections')
    m.add(g('mpaSections'), 'AISection', ns, 'root.mpaSections')
    m.add(g('mpaSectionResetPairs'), 'SectionResetPair', g('muNumSectionResetPairs'), 'root.srp')
    sec = g('mpaSections')
    stride = layout('AISection', 4)['size']
    pstride = layout('Portal', 4)['size']
    for i in range(ns):
        o = sec + i * stride
        npo = m.f('AISection', o, 'mu8NumPortals')
        m.add(m.f('AISection', o, 'mpaPortals'), 'Portal', npo, 'sec[%d].portals' % i)
        m.add(m.f('AISection', o, 'mpaNoGoLines'), 'BoundaryLine',
              m.f('AISection', o, 'muNumNoGoLines'), 'sec[%d].nogo' % i)
        m.add(m.f('AISection', o, 'mpaCorners'), 'Vector2', 4, 'sec[%d].corners' % i)
        po = m.f('AISection', o, 'mpaPortals')
        for p in range(npo):
            pp = po + p * pstride
            m.add(m.f('Portal', pp, 'mpaBoundaryLines'), 'BoundaryLine',
                  m.f('Portal', pp, 'mu8NumBoundaryLines'), 'sec[%d].portal[%d].bl' % (i, p))
    return m


def model_triggerdata(d):
    m = Model(d, 'TriggerData')
    g = lambda mem: m.f('TriggerData', 0, mem)
    pairs = [('mpLandmarks', 'miLandmarkCount', 'Landmark'),
             ('mpSignatureStunts', 'miSignatureStuntCount', 'SignatureStunt'),
             ('mpGenericRegions', 'miGenericRegionCount', 'GenericRegion'),
             ('mpKillzones', 'miKillzoneCount', 'Killzone'),
             ('mpBlackspots', 'miBlackspotCount', 'Blackspot'),
             ('mpVFXBoxRegions', 'miVFXBoxRegionCount', 'VFXBoxRegion'),
             ('mpRoamingLocations', 'miRoamingLocationCount', 'RoamingLocation'),
             ('mpSpawnLocations', 'miSpawnLocationCount', 'SpawnLocation'),
             ('mppRegions', 'miRegionCount', 'RegionPtr')]
    for pn, cn, kind in pairs:
        m.add(g(pn), kind, g(cn), 'root.' + pn)
    lm, nlm = g('mpLandmarks'), g('miLandmarkCount')
    ls = layout('Landmark', 4)['size']
    for i in range(nlm):
        o = lm + i * ls
        m.add(m.f('Landmark', o, 'mpaStartingGrids'), 'StartingGrid',
              m.f('Landmark', o, 'miStartingGridCount'), 'lm[%d].grids' % i)
    ss, nss = g('mpSignatureStunts'), g('miSignatureStuntCount')
    ssz = layout('SignatureStunt', 4)['size']
    for i in range(nss):
        o = ss + i * ssz
        m.add(m.f('SignatureStunt', o, 'mppStuntElements'), 'GenericRegionPtr',
              m.f('SignatureStunt', o, 'miStuntElementCount'), 'ss[%d].elems' % i)
    kz, nkz = g('mpKillzones'), g('miKillzoneCount')
    ksz = layout('Killzone', 4)['size']
    for i in range(nkz):
        o = kz + i * ksz
        m.add(m.f('Killzone', o, 'mppTriggers'), 'GenericRegionPtr',
              m.f('Killzone', o, 'miTriggerCount'), 'kz[%d].triggers' % i)
        m.add(m.f('Killzone', o, 'mpRegionIds'), 'CgsID',
              m.f('Killzone', o, 'miRegionIdCount'), 'kz[%d].ids' % i)
    return m


FORMATS = {
    'TrafficData':    (model_trafficdata, 'muSizeInBytes'),
    'AISections':     (model_aisections, None),      # size word is inside AISectionsData
    'AISectionsData': (model_aisections, None),
    'TriggerData':    (model_triggerdata, 'muSize'),
}
SIZE_MEMBER = {'TrafficData': ('TrafficData', 'muSizeInBytes'),
               'AISectionsData': ('AISectionsData', 'muSizeInBytes'),
               'TriggerData': ('TriggerData', 'muSize')}
YAP_TYPE_TO_KIND = {'TrafficData': 'TrafficData', 'AISections': 'AISectionsData',
                    'TriggerData': 'TriggerData'}


# =============================================================================
# CONVERT + VALIDATE
# =============================================================================
def convert_payload(kind, data, verbose=True):
    builder = {'TrafficData': model_trafficdata, 'AISectionsData': model_aisections,
               'TriggerData': model_triggerdata}[kind]
    m = builder(data)
    blocks = m.build()

    # ---- 1. identity: emit BE / 4-byte pointers at the original offsets ----
    ident, _ = m.emit(4, '>', identity=True)
    _expect(len(ident) == len(data), 'identity length %d != %d' % (len(ident), len(data)))
    # every byte the model did not write must be zero in the source (pure padding)
    diffs = [i for i in range(len(data)) if ident[i] != data[i]]
    nonzero_gap = [i for i in diffs if data[i] != 0 or ident[i] != 0]
    _expect(not diffs, '%s identity re-emit differs at %d bytes (first 0x%X)'
            % (kind, len(diffs), diffs[0] if diffs else -1))
    coverage = m.covered

    # ---- 2. the widened LE emit ----
    le, remap = m.emit(8, '<', identity=False)
    le = bytearray(le)
    sk, sm = SIZE_MEMBER[kind]
    soff = layout(sk, 8)['off'][sm]
    struct.pack_into('<I', le, soff, len(le))
    le = bytes(le)

    # ---- 3. re-walk the LE result with the consumer's own logic ----
    walk_le(kind, le, m)

    # ---- 4. semantics ----
    semantic_check(kind, data, le)

    if verbose:
        print('   %-16s %8d -> %8d bytes ; %5d blocks ; %d payload bytes modelled'
              % (kind, len(data), len(le), len(blocks), coverage))
    return le


def walk_le(kind, le, bem):
    """Re-parse the emitted LE blob with 8-byte pointers and re-walk the graph."""
    N = len(le)

    def R(base, k, mem, ty=None):
        lay = layout(k, 8)
        for fname, fty, foff, n, _ in lay['fields']:
            if fname == mem:
                return rd(le, base + foff, ty or fty, 8, '<')
        raise TranscodeError('%s.%s' % (k, mem))

    def inrange(p, what):
        _expect(0 <= p <= N, 'LE walk: %s -> 0x%X outside 0..0x%X' % (what, p, N))

    if kind == 'TrafficData':
        nH = R(0, 'TrafficData', 'muNumHulls')
        _expect(nH == bem.f('TrafficData', 0, 'muNumHulls'), 'hull count drift')
        pvs = R(0, 'TrafficData', 'mpPvs')
        inrange(pvs, 'mpPvs')
        _expect(R(pvs, 'Pvs', 'muNumCells') == R(pvs, 'Pvs', 'muNumCells_X') *
                R(pvs, 'Pvs', 'muNumCells_Z'), 'pvs cell count')
        inrange(R(pvs, 'Pvs', 'mpaHullPvs'), 'mpaHullPvs')
        ha = R(0, 'TrafficData', 'mpapHulls')
        inrange(ha, 'mpapHulls')
        hs = layout('Hull', 8)['size']
        for i in range(nH):
            ho = rd(le, ha + 8 * i, 'ptr:Hull', 8, '<')
            inrange(ho, 'hull[%d]' % i)
            ns = R(ho, 'Hull', 'muNumSections')
            sec = R(ho, 'Hull', 'mpaSections')
            inrange(sec + ns * layout('Section', 8)['size'], 'hull[%d].sections end' % i)
            nr = R(ho, 'Hull', 'muNumRungs')
            inrange(R(ho, 'Hull', 'mpaRungs') + nr * 32, 'hull[%d].rungs end' % i)
            for s in range(ns):
                so = sec + s * layout('Section', 8)['size']
                _expect(R(so, 'Section', 'muRungOffset') <= nr,
                        'hull[%d].sec[%d] muRungOffset %d > muNumRungs %d'
                        % (i, s, R(so, 'Section', 'muRungOffset'), nr))
        nF = R(0, 'TrafficData', 'muNumFlowTypes')
        fa = R(0, 'TrafficData', 'mpapFlowTypes')
        for i in range(nF):
            fo = rd(le, fa + 8 * i, 'ptr:FlowType', 8, '<')
            inrange(fo, 'flow[%d]' % i)
            inrange(R(fo, 'FlowType', 'mpauVehicleTypeIds'), 'flow[%d].ids' % i)
    elif kind == 'AISectionsData':
        ns = R(0, 'AISectionsData', 'muNumSections')
        sec = R(0, 'AISectionsData', 'mpaSections')
        st = layout('AISection', 8)['size']
        inrange(sec + ns * st, 'sections end')
        pt = layout('Portal', 8)['size']
        for i in range(ns):
            o = sec + i * st
            np_ = R(o, 'AISection', 'mu8NumPortals')
            inrange(R(o, 'AISection', 'mpaPortals') + np_ * pt, 'sec[%d].portals' % i)
            inrange(R(o, 'AISection', 'mpaCorners') + 32, 'sec[%d].corners' % i)
            po = R(o, 'AISection', 'mpaPortals')
            for p in range(np_):
                pp = po + p * pt
                inrange(R(pp, 'Portal', 'mpaBoundaryLines') +
                        16 * R(pp, 'Portal', 'mu8NumBoundaryLines'), 'sec[%d].p[%d]' % (i, p))
    elif kind == 'TriggerData':
        _expect(R(0, 'TriggerData', 'miVersionNumber') == 34, 'trigger version')
        nr = R(0, 'TriggerData', 'miRegionCount')
        rp = R(0, 'TriggerData', 'mppRegions')
        inrange(rp + 8 * nr, 'mppRegions end')
        lm = R(0, 'TriggerData', 'mpLandmarks')
        nlm = R(0, 'TriggerData', 'miLandmarkCount')
        ls = layout('Landmark', 8)['size']
        gr = R(0, 'TriggerData', 'mpGenericRegions')
        ngr = R(0, 'TriggerData', 'miGenericRegionCount')
        gs = layout('GenericRegion', 8)['size']
        for i in range(nr):
            t = rd(le, rp + 8 * i, 'ptr:*', 8, '<')
            ok = (lm <= t < lm + nlm * ls and (t - lm) % ls == 0) or \
                 (gr <= t < gr + ngr * gs and (t - gr) % gs == 0)
            _expect(ok, 'region[%d] -> 0x%X is not a Landmark/GenericRegion element' % (i, t))
        for i in range(nlm):
            o = lm + i * ls
            n = struct.unpack_from('<b', le, o + layout('Landmark', 8)['off']['miStartingGridCount'])[0]
            inrange(R(o, 'Landmark', 'mpaStartingGrids') + 256 * max(n, 0), 'lm[%d].grids' % i)


def semantic_check(kind, be, le):
    """A fixed set of scalar values must survive the port unchanged."""
    def B(k, base, mem):
        lay = layout(k, 4)
        for fn, ft, fo, n, _ in lay['fields']:
            if fn == mem:
                return rd(be, base + fo, ft, 4, '>')
        raise TranscodeError(mem)

    def L(k, base, mem):
        lay = layout(k, 8)
        for fn, ft, fo, n, _ in lay['fields']:
            if fn == mem:
                return rd(le, base + fo, ft, 8, '<')
        raise TranscodeError(mem)

    if kind == 'TrafficData':
        for mem in ('muDataVersion', 'muNumHulls', 'muNumFlowTypes', 'muNumVehicleTypes',
                    'muNumVehicleAssets', 'muNumVehicleTraits', 'muNumKillZones',
                    'muNumKillZoneRegions', 'muNumPaintColours'):
            _expect(B('TrafficData', 0, mem) == L('TrafficData', 0, mem), 'root.' + mem)
        bp, lp = B('TrafficData', 0, 'mpPvs'), L('TrafficData', 0, 'mpPvs')
        for mem in ('mGridMin', 'mCellSize', 'mRecipCellSize', 'muNumCells_X',
                    'muNumCells_Z', 'muNumCells'):
            _expect(B('Pvs', bp, mem) == L('Pvs', lp, mem), 'pvs.' + mem)
        bh, lh = B('TrafficData', 0, 'mpapHulls'), L('TrafficData', 0, 'mpapHulls')
        nH = B('TrafficData', 0, 'muNumHulls')
        chs, lhs = layout('Section', 4)['size'], layout('Section', 8)['size']
        for i in range(nH):
            bo = rd(be, bh + 4 * i, 'ptr:Hull', 4, '>')
            lo = rd(le, lh + 8 * i, 'ptr:Hull', 8, '<')
            for mem in ('muNumSections', 'muNumRungs', 'muNumNeighbours', 'muNumJunctions',
                        'muNumStoplines', 'muNumStaticTraffic', 'muFirstTrafficLight',
                        'muLastTrafficLight'):
                _expect(B('Hull', bo, mem) == L('Hull', lo, mem), 'hull[%d].%s' % (i, mem))
            bs, ls_ = B('Hull', bo, 'mpaSections'), L('Hull', lo, 'mpaSections')
            for s in range(B('Hull', bo, 'muNumSections')):
                for mem in ('muRungOffset', 'muNumRungs', 'mfSpeed', 'mfLength',
                            'muNeighbourOffset', 'muSpanIndex'):
                    _expect(B('Section', bs + s * chs, mem) == L('Section', ls_ + s * lhs, mem),
                            'hull[%d].sec[%d].%s' % (i, s, mem))
    elif kind == 'AISectionsData':
        for mem in ('muNumSections', 'muNumSectionResetPairs', 'muVersion',
                    'mafSectionMinSpeeds', 'mafSectionMaxSpeeds'):
            _expect(B('AISectionsData', 0, mem) == L('AISectionsData', 0, mem), 'ai.' + mem)
        bs, ls_ = B('AISectionsData', 0, 'mpaSections'), L('AISectionsData', 0, 'mpaSections')
        cst, hst = layout('AISection', 4)['size'], layout('AISection', 8)['size']
        for i in range(B('AISectionsData', 0, 'muNumSections')):
            for mem in ('mId', 'miSpanIndex', 'muNumNoGoLines', 'mu8NumPortals', 'muSpeed',
                        'mu8eDistrict', 'mx8Flags'):
                _expect(B('AISection', bs + i * cst, mem) == L('AISection', ls_ + i * hst, mem),
                        'aisec[%d].%s' % (i, mem))
    elif kind == 'TriggerData':
        for mem in ('miVersionNumber', 'miLandmarkCount', 'miOnlineLandmarkCount',
                    'miSignatureStuntCount', 'miGenericRegionCount', 'miKillzoneCount',
                    'miBlackspotCount', 'miVFXBoxRegionCount', 'miRoamingLocationCount',
                    'miSpawnLocationCount', 'miRegionCount', 'mPlayerStartPosition',
                    'mPlayerStartDirection'):
            _expect(B('TriggerData', 0, mem) == L('TriggerData', 0, mem), 'trig.' + mem)
        bl, ll = B('TriggerData', 0, 'mpLandmarks'), L('TriggerData', 0, 'mpLandmarks')
        cls_, hls = layout('Landmark', 4)['size'], layout('Landmark', 8)['size']
        for i in range(B('TriggerData', 0, 'miLandmarkCount')):
            for mem in ('miStartingGridCount', 'muDesignIndex', 'muDistrict', 'mu8Flags'):
                _expect(B('Landmark', bl + i * cls_, mem) == L('Landmark', ll + i * hls, mem),
                        'lm[%d].%s' % (i, mem))
            _expect(B('TriggerRegion', bl + i * cls_, 'mId') ==
                    L('TriggerRegion', ll + i * hls, 'mId'), 'lm[%d].mId' % i)


# =============================================================================
# DIRECTORY / BUNDLE DRIVERS
# =============================================================================
MARKER = '.lane_transcoded'


def convert_dir(root, verify_only=False):
    done = 0
    for tname in sorted(os.listdir(root)):
        tdir = os.path.join(root, tname)
        if not os.path.isdir(tdir):
            continue
        kind = YAP_TYPE_TO_KIND.get(tname)
        if kind is None:
            print('   %-16s SKIPPED (not a lane type)' % tname)
            continue
        marker = os.path.join(tdir, MARKER)
        if os.path.exists(marker) and not verify_only:
            print('   %-16s already transcoded' % tname)
            continue
        for fn in sorted(os.listdir(tdir)):
            if not fn.lower().endswith('.dat'):
                continue
            path = os.path.join(tdir, fn)
            data = open(path, 'rb').read()
            le = convert_payload(kind, data)
            if not verify_only:
                with open(path, 'wb') as f:
                    f.write(le)
            done += 1
        if not verify_only:
            open(marker, 'w').write('lane_transcode\n')
    if not verify_only:
        patch_meta(os.path.join(root, '.meta.yaml'))
    return done


def patch_meta(meta_path):
    _expect(os.path.isfile(meta_path), 'no .meta.yaml at %s' % meta_path)
    txt = open(meta_path, 'r', encoding='utf-8', errors='replace').read()
    import re
    new = re.sub(r'(?m)^(\s*platform:\s*)\d+\s*$', r'\g<1>4', txt)
    new = re.sub(r'(?m)^(\s*compressed:\s*)\w+\s*$', r'\g<1>false', new)
    _expect('platform: 4' in new.replace('platform:  4', 'platform: 4') or 'platform:4' in new,
            'platform not patched in %s' % meta_path)
    open(meta_path, 'w', encoding='utf-8').write(new)


def run_yap(args):
    r = subprocess.run([YAP] + args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('YAP failed (%d): %s' % (r.returncode, ' '.join(args[:2])))


def convert_bundle(src, dst):
    _expect(os.path.isfile(YAP), 'YAP.exe not found at %s' % YAP)
    tmp = tempfile.mkdtemp(prefix='lane_')
    try:
        run_yap(['e', src, tmp])
        n = convert_dir(tmp)
        _expect(n > 0, 'no lane resources found in %s' % src)
        run_yap(['c', tmp, dst])
        print('   wrote %s (%d bytes)' % (dst, os.path.getsize(dst)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


LANE_FILES = ['B5TRAFFIC.BNDL', 'AI.DAT', 'TRIGGERS.DAT']


def convert_all():
    game = os.path.join(ROOT, 'build', 'game')
    backup = os.path.join(ROOT, 'build', 'game_x360_world')
    os.makedirs(backup, exist_ok=True)
    for fn in LANE_FILES:
        src = os.path.join(game, fn)
        bak = os.path.join(backup, fn)
        _expect(os.path.isfile(src) or os.path.isfile(bak), 'missing %s' % fn)
        if not os.path.isfile(bak):
            shutil.copy2(src, bak)
            print('backed up %s -> build/game_x360_world/' % fn)
        print('%s:' % fn)
        tmp = src + '.new'
        convert_bundle(bak, tmp)
        os.replace(tmp, src)
        print('   staged build/game/%s' % fn)


def main(argv):
    if argv and argv[0] == '--all':
        convert_all()
        return 0
    if len(argv) >= 3 and argv[0] == '--bundle':
        convert_bundle(argv[1], argv[2])
        return 0
    if not argv or argv[0].startswith('-'):
        sys.stderr.write(__doc__.split('Usage', 1)[1])
        return 2
    root = argv[0]
    _expect(os.path.isdir(root), 'not a directory: %s' % root)
    convert_dir(root, verify_only='--verify' in argv[1:])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
