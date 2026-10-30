#pragma once
// TEMPORARY DIAGNOSTIC ONLY: never include in shipping source.
#include "GameSource/Gui/SatNav/BrnSatNavComponent.h"
#include <cstdint>
#include <cstdio>
#include <cstring>
namespace SatNavWitness {
inline std::uint32_t Bits32(const void* p) { std::uint32_t v; std::memcpy(&v,p,sizeof(v)); return v; }
inline std::uint64_t Bits64(const void* p) { std::uint64_t v; std::memcpy(&v,p,sizeof(v)); return v; }
inline unsigned Bits8(const void* p) { unsigned char v; std::memcpy(&v,p,sizeof(v)); return v; }
inline bool Format(const BrnGui::GuiEventRenderSatNav& p, char* out, size_t capacity) {
    static_assert(sizeof(void*) == 8 && sizeof(float) == 4, "native x64 witness");
    const int n = std::snprintf(out, capacity,
        "prefix=%08X,%08X,%08X,%08X,%08X,%08X,%08X,%016llX,%016llX tail=%016llX,%02X,%02X",
        Bits32(&p.mv3CarPosition.x), Bits32(&p.mv3CarPosition.y),
        Bits32(&p.mv3CarPosition.z), Bits32(&p.mv3CarPosition.w),
        Bits32(&p.mfCarOrientation), Bits32(&p.mfCarSpeedMph), Bits32(&p.miZoomLevel),
        static_cast<unsigned long long>(Bits64(&p.mpMapTexture)),
        static_cast<unsigned long long>(Bits64(&p.mpMaskTexture)),
        static_cast<unsigned long long>(Bits64(&p.mpRouteSegmentTexture)),
        Bits8(&p.mbRotateMap), Bits8(&p.mbUseTrajectory));
    return n >= 0 && static_cast<size_t>(n) < capacity;
}
}
