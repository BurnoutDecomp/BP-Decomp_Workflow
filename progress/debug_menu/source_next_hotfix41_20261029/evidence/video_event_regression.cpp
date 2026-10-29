#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"
#include "GameSource/Gui/BrnGuiVideoEvents.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace CgsDev {
namespace Assert {
int BeginAssert() { return 0; }
int FireAssert(const char* text, const char*, int) { std::fprintf(stderr, "ASSERT: %s\n", text); std::exit(90); }
void* EndAssert() { return nullptr; }
}
namespace Log { StrStreamBase* gpDebugPrint = nullptr; }
namespace Message { u64 gxMessageFilterFlags = 0; }
}

static bool VerifyRecord(CgsGui::StateInterface& interface, int type,
    u64 expectedId, u32 expectedSound, bool expectedKeep)
{
    const CgsModule::Event* event = nullptr;
    s32 size = 0;
    auto* queue = interface.GetOutputEventQueue();
    const int channel = queue->CgsModule::VariableEventQueue<65536,16>::GetFirstEvent(&event, &size);
    if (channel != 40 || size != 64 || event == nullptr) {
        std::printf("FAIL video%d reached observer queue channel%d bytes%d (expected40/64)\n", type, channel, size);
        return false;
    }
    s32 words[3];
    std::memcpy(words, event, sizeof(words));
    if (words[0] != 48 || words[1] != type || words[2] != 16) return false;
    // Independently pinned ARTIST emitter/consumer offsets, after unboxing.
    const auto* bytes = reinterpret_cast<const unsigned char*>(event) + words[2];
    u64 id; u32 sound; f32 rectangle[4];
    std::memcpy(&id, bytes + 16, sizeof(id));
    std::memcpy(&sound, bytes + 24, sizeof(sound));
    std::memcpy(rectangle, bytes, sizeof(rectangle));
    if (type == 508 && (id != expectedId || sound != expectedSound ||
        bytes[37] != static_cast<unsigned char>(expectedKeep) || rectangle[2] != 1.0f || rectangle[3] != 1.0f)) return false;
    std::printf("PASS video%d outer40 bytes64 raw48 offset16 id%016llX sound%08X keep%d\n",
        type, id, sound, bytes[37]);
    queue->CgsModule::VariableEventQueue<65536,16>::Clear();
    return true;
}

int main()
{
    CgsGui::StateInterface interface;
    interface.Construct();
    BrnGui::GuiEventPlayVideo play;
    play.muVideoResourceId = 0xF4DE3E5CULL;
    play.muSoundStreamName = 0x656EB109u;
    play.mbKeepMemoryWhenFinished = true;
    interface.OutputGuiEvent(play);
    if (!VerifyRecord(interface, 508, play.muVideoResourceId, play.muSoundStreamName, true)) return 17;
    BrnGui::GuiEventStopVideo stop;
    interface.OutputGuiEvent(stop);
    if (!VerifyRecord(interface, 509, 0, 0, false)) return 18;
    return 0;
}
