// STUBS_BANKPL round-trip test: the camera parameter bank through TextFileWriteSerialiser then
// TextFileReadSerialiser, against the game's own objects (driver: STUBS_BANKPL_roundtrip.py).
//
//   1. bank A: Construct (the console seed + naming pass), write file A.
//   2. bank B: Construct, perturb fields in blocks of every walked type, read file A into B.
//   3. write file B from bank B; file B must equal file A byte for byte, and every perturbed field
//      must be back at bank A's value.
//   4. naming pass: a derived block in the version-5 walk carries its walk name; a derived block
//      outside it keeps a null name.

#include "GameSource/Director/Camera/BrnBehaviourParameterBank.h"
#include "GameSource/Director/Camera/Behaviours/Serialisation.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <string>

using namespace BrnDirector;
using namespace BrnDirector::Camera;

namespace
{
    int giFailures = 0;

    void Check(bool lbOk, const char* lpcWhat)
    {
        std::printf("%s %s\n", lbOk ? "ok  " : "FAIL", lpcWhat);
        if (!lbOk)
            ++giFailures;
    }

    std::string ReadFile(const std::string& lrPath)
    {
        std::string lText;
        if (FILE* lpFile = std::fopen(lrPath.c_str(), "r"))
        {
            char lacBuffer[4096];
            size_t luRead;
            while ((luRead = std::fread(lacBuffer, 1, sizeof(lacBuffer), lpFile)) > 0)
                lText.append(lacBuffer, luRead);
            std::fclose(lpFile);
        }
        return lText;
    }

    BehaviourParameterBank* NewBank()
    {
        void* lpMemory = std::calloc(1, sizeof(BehaviourParameterBank));
        BehaviourParameterBank* lpBank = new (lpMemory) BehaviourParameterBank();
        lpBank->Construct();
        return lpBank;
    }

    void Write(BehaviourParameterBank& lrBank, const std::string& lrPath)
    {
        TextFileWriteSerialiser lSerialiser;
        lSerialiser.Construct(lrPath.c_str());
        lrBank.Serialise(lSerialiser);
        lSerialiser.Destruct();
    }

    void Read(BehaviourParameterBank& lrBank, const std::string& lrPath)
    {
        TextFileReadSerialiser lSerialiser;
        lSerialiser.Construct(lrPath.c_str());
        lrBank.Serialise(lSerialiser);
        lSerialiser.Destruct();
    }
}

int main(int argc, char** argv)
{
    const std::string lDir   = argc > 1 ? argv[1] : ".";
    const std::string lFileA = lDir + "\\bank_a.txt";
    const std::string lFileB = lDir + "\\bank_b.txt";

    BehaviourParameterBank* lpA = NewBank();
    Write(*lpA, lFileA);
    const std::string lTextA = ReadFile(lFileA);
    Check(!lTextA.empty(), "file A written");
    Check(lTextA.compare(0, 36, "Version_Number_(dont_change) : 5\nAft") == 0, "file A opens with the version line then Aftertouch");

    NamedParameters& lrA = lpA->GetNamedParameters();

    BehaviourParameterBank* lpB = NewBank();
    NamedParameters& lrB = lpB->GetNamedParameters();
    lrB.mGyroCamDefaultParams.mfSlowDistance                 = 123.0f;  // gyro (pointer-free block)
    lrB.mHeliCamDefaultParams.mfVelocityMPS                  = 77.0f;   // heli
    lrB.mFailsafe.mfSlowDistance                             = 55.0f;   // failsafe
    lrB.mAftertouchCrashParams.mfFastHeight                  = 9.0f;    // aftertouch crash
    lrB.mRigFrontQBwd.mbUseOrientationLag                    = !lrB.mRigFrontQBwd.mbUseOrientationLag;  // rig bool
    lrB.mRigRearQFwd.mPositionLagParams.mfXResponse          = 0.9f;    // rig nested lag
    lrB.mBystanderFarParameters.mfVelocityInfluenceOnPosition = 0.1f;  // bystander
    lrB.mFixedDefault.mfFOV                                  = 33.0f;   // fixed cam
    Read(*lpB, lFileA);

    Check(lrB.mGyroCamDefaultParams.mfSlowDistance == lrA.mGyroCamDefaultParams.mfSlowDistance, "gyro SlowDistance restored");
    Check(lrB.mHeliCamDefaultParams.mfVelocityMPS == lrA.mHeliCamDefaultParams.mfVelocityMPS, "helicam VelocityMPS restored");
    Check(lrB.mFailsafe.mfSlowDistance == lrA.mFailsafe.mfSlowDistance, "failsafe SlowDistance restored");
    Check(lrB.mAftertouchCrashParams.mfFastHeight == lrA.mAftertouchCrashParams.mfFastHeight, "aftertouch crash FastHeight restored");
    Check(lrB.mRigFrontQBwd.mbUseOrientationLag == lrA.mRigFrontQBwd.mbUseOrientationLag, "rig UseOrientationLag restored");
    Check(lrB.mRigRearQFwd.mPositionLagParams.mfXResponse == lrA.mRigRearQFwd.mPositionLagParams.mfXResponse, "rig position-lag X restored");
    Check(lrB.mBystanderFarParameters.mfVelocityInfluenceOnPosition == lrA.mBystanderFarParameters.mfVelocityInfluenceOnPosition, "bystander velocity influence restored");
    Check(lrB.mFixedDefault.mfFOV == lrA.mFixedDefault.mfFOV, "fixed cam FOV restored");

    Write(*lpB, lFileB);
    const std::string lTextB = ReadFile(lFileB);
    Check(lTextA == lTextB, "file B (read A, write) == file A");

    Check(lrA.mRigRearQFwd.GetDebugName() != NULL && std::strcmp(lrA.mRigRearQFwd.GetDebugName(), "Rig Rear Q Fwd") == 0,
          "naming pass: Rig Rear Q Fwd");
    Check(lrA.mFixedDefault.GetDebugName() != NULL && std::strcmp(lrA.mFixedDefault.GetDebugName(), "Fixed Cam Default") == 0,
          "naming pass: Fixed Cam Default");
    Check(lrA.mPassengerDefault.GetDebugName() == NULL, "naming pass: Passenger (not in the version-5 walk) stays unnamed");
    Check(lrA.mRoadRunnerDefault.GetType() == 16u, "road runner tag 16");
    Check(lrA.mFailsafe.meType == eBehaviourFailsafe, "failsafe tag 12");
    Check(lrA.mHeliCamDefaultParams.meType == eBehaviourHeliCam, "helicam tag 6");

    size_t luLines = 0;
    for (char lc : lTextA)
        luLines += lc == '\n';
    std::printf("file A: %u bytes, %u lines\n", static_cast<unsigned>(lTextA.size()), static_cast<unsigned>(luLines));
    std::printf("RESULT %s (%d failures)\n", giFailures == 0 ? "PASS" : "FAIL", giFailures);
    return giFailures == 0 ? 0 : 1;
}
