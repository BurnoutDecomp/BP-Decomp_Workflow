// Standalone integration check against the ACTUAL decomp storage backend.
// Build with CgsSaveLoadPC.cpp and /I b5-decomp/src, then run in a test directory
// holding Memcard/Profile.sav. Writes Memcard/NativeRoundtrip.sav in that directory.
#include "GameShared/GameClasses/Gui/PC/CgsSaveLoadPC.h"
#include <Windows.h>
#include <cstdio>
#include <cstring>
#include <vector>

template<class T> T Read(const std::vector<u8>& image, size_t offset)
{
    T value;
    std::memcpy(&value, image.data() + offset, sizeof(value));
    return value;
}

int main()
{
    std::vector<u8> image(262144), mugshots(960800);
    if (CgsGui::SaveLoadPC::ReadContainer("Profile", image.data(), (u32)image.size(),
                                      mugshots.data(), (u32)mugshots.size()) !=
        CgsGui::SaveLoadPC::E_CONTAINERREAD_OK)
        return 1;
    std::printf("Actual C++ ReadContainer: OK\n");
    std::printf("versions=%u,%u,%u,%u,%u cars=%u events=%u rank=%d hours=%.5f\n",
        Read<u32>(image, 0), Read<u32>(image, 118064), Read<u32>(image, 148080),
        Read<u32>(image, 177632), Read<u32>(image, 187432), Read<u32>(image, 604),
        Read<u32>(image, 616), (int)Read<s8>(image, 112), Read<float>(image, 108)/3600);
    // Windows must interpret the source Xbox timestamp as a real date.
    FILETIME date = Read<FILETIME>(image, 117984);
    SYSTEMTIME systemTime = {};
    if (!FileTimeToSystemTime(&date, &systemTime)) return 2;
    std::printf("licence date=%04u-%02u-%02u\n", systemTime.wYear, systemTime.wMonth, systemTime.wDay);
    if (GetFileAttributesA("Memcard\\NativeRoundtrip.sav") != INVALID_FILE_ATTRIBUTES) return 3;
    if (!CgsGui::SaveLoadPC::WriteContainer("NativeRoundtrip", image.data(), (u32)image.size(),
                                          mugshots.data(), (u32)mugshots.size(),
                                          "Burnout Paradise", "Converted from Xenia (Xbox 360)")) return 4;
    std::printf("Actual C++ WriteContainer: OK\n");
    return 0;
}
