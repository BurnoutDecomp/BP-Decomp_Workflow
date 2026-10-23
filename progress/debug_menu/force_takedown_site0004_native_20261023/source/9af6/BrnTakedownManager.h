#pragma once

#include "types.hpp"
#include "GameSource/GameState/TakedownManager/BrnTakedownManagerTypes.h"           // TakedownEvent, EActiveRaceCarIndex, ETakedownType
#include "GameSource/GameState/TakedownManager/BrnTakedownManagerDebugComponent.h"  // embedded by value (DWARF :248)
#include "GameSource/GameState/BrnGameStateModuleIO.h"                               // PreWorldInputBuffer / OutputBuffer / GameActionQueue, CgsModule::EventQueue
#include "GameSource/World/EntityModules/TrafficEntityModule/SharedIO/BrnTrafficTypeInterface.h" // BrnTraffic::BrnTrafficIO::TrafficTypeResponse

// ============================================================================
// BrnGameState::TakedownManager -- the game-state side takedown CLASSIFIER.
//
// Shape: DecFIGS DWARF BrnTakedownManager.h:50-248, reproduced member for member and method for
// method (this header was written from that outline on 2026-09-02, takedown wave). Behaviour: the
// 22 X360 bodies listed below, reconstructed in BrnTakedownManager.cpp (lifecycle / timers / camera
// / reset) and BrnTakedownManager_Detect.cpp (Update and the detect / process chain).
//
// WHAT IT DOES. Every pre-world tick (GameStateModule::PreWorldUpdate @0x823A5328, inside the
// !IsSimPaused arm) Update() walks the race-car crash-event queue the physics side posted
// (VehicleManager::SetRaceCarCrashing -> AddRaceCarCrashEvent), decides which crashes are
// TAKEDOWNS (aggressor == player, victim a rival, the timing / speed / contact rules), builds a
// TakedownEvent per takedown onto OutputBuffer::GetTakedownEventOutputQueue() (+0x4040), drives
// the takedown camera and the post-takedown player reset, and keeps the per-car revenge /
// chain / multiple-takedown bookkeeping in maRaceCarData. GameStateModule::ProcessTakedownEvents
// (GameStateModule_gRR_00.cpp) then drains that queue into ScoringSystem::OnPlayerDoesATakedown.
//
// X360 layout (asm-attested, for the reconstructors -- NOT asserted on the host, the embedded
// debug component carries a vtable pointer that widens):
//   +0     maRaceCarData[8]              (stride 80: RaceCarData is 80 B on X360 AND here)
//   +640   mfTakedownCameraTimer         (-1.0f == not in a takedown camera; IsInTakedownCamera)
//   +644   mfTakedownCameraEarlyOutTimer
//   +648   meCurrentVictimActiveRaceCarIndex (-1)
//   +652   mpModeManager                 (Update reads mode type at mm+3476 through it)
//   +656   mpProgressionManager
//   +660   mfPlayerSpeedAtTakedown
//   +664   mfTimeWithWheelsOffGround
//   +668   mfPlayerControlTimer
//   +672   mbPlayerWaitingForControl
//   +673   mbDoneResetThisTakedown
//   +676   mTakedownManagerDebugComponent
// Prepare @0x823595B8 seeds exactly +640..+673 (see BrnTakedownManager.cpp).
//
// The console's callers: GameStateModule::Construct (inlined Construct: the two manager pointers),
// GameStateModule::Prepare (Prepare), PreWorldUpdate (Update), ProcessGameEvents case 27 and
// ModeManager (ClearRaceCarData / ClearAllTakedowns), ModeManager::UpdateCurrentMode
// (IsInTakedownCamera). The manager is embedded in GameStateModule at gsm+568 (0x238).
// ============================================================================

namespace BrnProgression { class ProgressionManager; }
namespace BrnPhysics { namespace Vehicle { struct RaceCarState; struct RaceCarCrashEvent; struct CrashingRaceCarInterface; } }
namespace BrnWorld { namespace RaceCarEntityModuleIO { class RCEntityActiveRaceCarOutputInterface; } }

namespace BrnGameState
{
    class ModeManager;

    struct TakedownManager
    {
        // ---- the DWARF's typedef spellings, so the bodies read like the console source ----
        typedef BrnWorld::RaceCarEntityModuleIO::RCEntityActiveRaceCarOutputInterface     RCEntityActiveRaceCarOutputInterface;
        typedef CgsModule::EventQueue<BrnPhysics::Vehicle::RaceCarCrashEvent, 8>           RaceCarCrashEventQueue;   // == VehicleManagerOutputInterface::RaceCarCrashEventQueue
        typedef CgsModule::EventQueue<BrnTraffic::BrnTrafficIO::TrafficTypeResponse, 32>   TrafficTypeResponseQueue; // == OutputBuffer_PostPhysics::TrafficTypeResponseQueue (BrnTakedownManagerTypes.h:98)
        typedef BrnPhysics::Vehicle::RaceCarState                                          RaceCarState;
        typedef BrnPhysics::Vehicle::RaceCarCrashEvent                                     RaceCarCrashEvent;
        typedef BrnPhysics::Vehicle::CrashingRaceCarInterface                              CrashingRaceCarInterface;

        // DWARF BrnTakedownManager.h:56 -- one active race car's takedown bookkeeping (80 B).
        struct RaceCarData
        {
            bool          mabRevengeRelationships[8];   // :61
            f32           mfTimeSinceLastTakenDown;     // :62
            f32           mfTimeSinceVictimCrashed;     // :64
            bool          mbWaitingOnTakedown;          // :65
            TakedownEvent mPendingTakedownEvent;        // :66
            f32           mfTimeSinceLastTakedown;      // :67
            s32           miTakedownChainLength;        // :68
            s32           miMultipleTakedownLength;     // :69

            void Clear();                               // :59  X360 0x82355CE8 (BrnTakedownManagerRaceCarData.cpp)
        };

        // ---- the tunables (DWARF :203-227; class-static consts, values recovered from the image
        //      in BrnTakedownManager.cpp) ----
        static const f32 KF_POST_TAKEDOWN_INVULNERABLE_TIME;        // :203
        static const f32 KF_DOUBLE_TAKEDOWN_TIME_LIMIT;             // :204
        static const f32 KF_TAKEDOWN_TIME_CONTACT;                  // :206
        static const f32 KF_TAKEDOWN_TIME_CONTACT_ONLINE;           // :207
        static const f32 KF_TAKEDOWN_IGNORE_TIME;                   // :209
        static const f32 KF_ONLINE_TAKEDOWN_IGNORE_TIME;            // :210
        static const f32 KF_TAKEDOWN_CONFIRMATION_TIME;             // :211
        static const f32 KF_ONLINE_TAKEDOWN_CONFIRMATION_TIME;      // :212
        static const f32 KF_SPEED_DROP_FOR_PLAYER_RESET;            // :214
        static const f32 KF_MIN_SPEED_FOR_PLAYER_RESET;             // :215
        static const f32 KF_MAX_SPEED_FOR_PLAYER_RESET;             // :216
        static const f32 KF_MIN_ANGLE_FOR_PLAYER_RESET;             // :217
        static const f32 KF_MAX_ANGULAR_VELOCITY_FOR_PLAYER_RESET;  // :218
        static const f32 KF_MIN_TIME_IN_AIR_FOR_PLAYER_RESET;       // :219
        static const s32 KI_WHEELS_OFF_GROUND_FOR_PLAYER_RESET;     // :220
        static const f32 KF_TAKEDOWN_CHAIN_TIMEOUT_SECONDS;         // :222
        static const f32 KF_INVALID_TIME;                           // :224
        static const f32 KF_MIN_TAKEDOWN_SPEED;                     // :225
        static const f32 KF_FRONT_CONTACT_TOLERANCE;                // :227

        // ---- lifecycle (public in the DWARF) ----
        void Construct(ModeManager* lpModeManager, BrnProgression::ProgressionManager* lpProgressionManager); // :76  (inlined into GameStateModule::Construct on X360)
        bool Prepare();                                                                                         // :80  X360 0x823595B8
        void Update(RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface,
                    f32 lfDeltaTime,
                    RaceCarCrashEventQueue* lpRaceCarCrashEventQueue,
                    CrashingRaceCarInterface* lpCrashingVehicleInterface,
                    const GameStateModuleIO::PreWorldInputBuffer* lpInput,
                    GameStateModuleIO::OutputBuffer* lpOutput,
                    TrafficTypeResponseQueue* lpLastTrafficTypeResponseQueue);                                   // :91  X360 0x8239FAC0
        bool IsInTakedownCamera() const;                                                                        // :94  X360 0x82359620 (mfTakedownCameraTimer != -1.0f)
        void ClearRaceCarData();                                                                                // :97  X360 0x823594E0
        bool IsBeingAttacked(const RaceCarState* lpRaceCarState, EActiveRaceCarIndex* lpeAttackerIndex);         // :102 X360 0x8236F120
        bool IsValidTakedownSituation(const RaceCarState* lpAggressor, const RaceCarState* lpVictim);           // :107 (no out-of-line X360 symbol -- inlined at its sites)
        void ClearAllTakedowns(GameStateModuleIO::GameActionQueue* lpGameActionQueue);                          // :111 X360 0x82388FA8

        // ---- accessors the module / debug component use ----
        RaceCarData*       GetRaceCarData(EActiveRaceCarIndex leIndex);                                         // :117 X360 0x82359538
        const RaceCarData* GetRaceCarDataConst(EActiveRaceCarIndex leIndex) const { return &maRaceCarData[leIndex]; } // PC convenience (const twin, same bounds rule)

    private:
        f32  GetTakedownTime();                                                                                 // :120 (inlined on X360)
        void UpdateTakedownTimes(RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface, f32 lfDeltaTime);  // :125 X360 0x823660C0
        void UpdatePlayerResetStatus(RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface,
                                     GameStateModuleIO::GameActionQueue* lpGameActionQueue, f32 lfDeltaTime);   // :131 X360 0x82388AC0
        void DetectTakedowns(const GameStateModuleIO::PreWorldInputBuffer* lpInput,
                             GameStateModuleIO::OutputBuffer* lpOutput,
                             const RaceCarCrashEventQueue* lpRaceCarCrashEventQueue,
                             RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface,
                             TrafficTypeResponseQueue* lpLastTrafficTypeResponseQueue);                          // :139 X360 0x8239D808
        bool DetectInstantTakedown(const GameStateModuleIO::PreWorldInputBuffer* lpInput,
                                   GameStateModuleIO::OutputBuffer* lpOutput,
                                   RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface,
                                   const RaceCarCrashEvent* lpCrashEvent);                                       // :146 X360 0x82399638
        void DetectStandardTakedown(const GameStateModuleIO::PreWorldInputBuffer* lpInput,
                                    GameStateModuleIO::OutputBuffer* lpOutput,
                                    RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface,
                                    const RaceCarCrashEvent* lpCrashEvent,
                                    TrafficTypeResponseQueue* lpLastTrafficTypeResponseQueue);                   // :154 X360 0x8237A3C0
        void DetectNetworkTakedowns(const GameStateModuleIO::PreWorldInputBuffer* lpInput,
                                    RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface,
                                    GameStateModuleIO::OutputBuffer* lpOutput);                                  // :160 X360 0x823997A0
        void ProcessQueuedTakedowns(const GameStateModuleIO::PreWorldInputBuffer* lpInput,
                                    RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface,
                                    GameStateModuleIO::OutputBuffer* lpOutput, f32 lfDeltaTime);                // :167 X360 0x82399A98
        void ProcessTakedownEvent(const GameStateModuleIO::PreWorldInputBuffer* lpInput,
                                  RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface,
                                  GameStateModuleIO::OutputBuffer* lpOutput, TakedownEvent* lpTakedownEvent);    // :174 X360 0x82393D40
        ETakedownType GetTakedownTypeFromTrafficVehicleIndex(const TrafficTypeResponseQueue* lpQueue,
                                                             u16 luTrafficVehicleIndex);                         // :181 X360 0x82366288
        void StartTakedownCamera(GameStateModuleIO::GameActionQueue* lpGameActionQueue,
                                 EActiveRaceCarIndex leVictimIndex, ETakedownType leType);                       // :187 X360 0x82388DD8
        void EndTakedownCamera(GameStateModuleIO::GameActionQueue* lpGameActionQueue,
                               EActiveRaceCarIndex leVictimIndex);                                               // :192 X360 0x82388ED8
        void UpdateTakedownCamera(f32 lfDeltaTime, GameStateModuleIO::OutputBuffer* lpOutput,
                                  RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface);                   // :198 X360 0x82389068
        bool IsAllowedToResetPlayer();                                                                          // :201 X360 0x82359648

        friend class TakedownManagerDebugComponent;   // the console's debug menu reads the private state

    public:
        // [PC harness, not X360] see TakedownManagerDebugComponent::HarnessForceTakedown.
        void HarnessForceTakedown() { mTakedownManagerDebugComponent.HarnessForceTakedown(); }
        // [PC harness, not X360] (FX-BRIDGES CC-8 witness, 2026-09-24) the console's own "Force takedown"
        // debug action (TakedownManagerDebugComponent::ForceTakedownCallback @0x823597F8: Clear, then
        // mfTimeSinceVictimCrashed 0, mbWaitingOnTakedown 1, a STANDARD pending event) with the roles
        // swapped: the pending takedown is armed on the AGGRESSOR's slot (the slot ProcessQueuedTakedowns
        // confirms against -- active, not crashing, above KF_MIN_TAKEDOWN_SPEED) and names the player as
        // the victim. Everything after the arming is the console's code. See GameStateModule_gTD_00.cpp,
        // BRN_FORCE_PLAYER_TAKEN_DOWN. DELETE-WHEN a scripted rival ram on the player can be relied on.
        void HarnessForceTakenDown(EActiveRaceCarIndex leAggressorIndex, EActiveRaceCarIndex leVictimIndex)
        {
            RaceCarData& lrAggressor = maRaceCarData[leAggressorIndex];
            lrAggressor.Clear();
            lrAggressor.mfTimeSinceVictimCrashed         = 0.0f;
            lrAggressor.mbWaitingOnTakedown              = true;
            lrAggressor.mPendingTakedownEvent.meAggressorIndex = leAggressorIndex;
            lrAggressor.mPendingTakedownEvent.meVictimIndex    = leVictimIndex;
            lrAggressor.mPendingTakedownEvent.meType           = E_TAKEDOWN_STANDARD;
        }
    private:

        // ---- members, DWARF order (:230-248) ----
        RaceCarData                        maRaceCarData[8];                    // +0
        f32                                mfTakedownCameraTimer;               // +640
        f32                                mfTakedownCameraEarlyOutTimer;       // +644
        EActiveRaceCarIndex                meCurrentVictimActiveRaceCarIndex;   // +648
        ModeManager*                       mpModeManager;                       // +652
        BrnProgression::ProgressionManager* mpProgressionManager;               // +656
        f32                                mfPlayerSpeedAtTakedown;             // +660
        f32                                mfTimeWithWheelsOffGround;           // +664
        f32                                mfPlayerControlTimer;                // +668
        bool                               mbPlayerWaitingForControl;           // +672
        bool                               mbDoneResetThisTakedown;             // +673
        TakedownManagerDebugComponent      mTakedownManagerDebugComponent;      // +676
    };

    static_assert(sizeof(TakedownManager::RaceCarData) == 80, "TakedownManager::RaceCarData is 80 B on X360 and must stay so here (maRaceCarData stride)");
}
