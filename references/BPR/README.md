# BPR — Burnout Paradise Remastered / PC module map

Hand-recovered structure of the top-level engine object graph for the PC / Remastered
build, derived from analyzing `BurnoutPR.exe` (see
[`../../IDA Files/BurnoutPR.exe.i64`](../../IDA%20Files/BurnoutPR.exe.i64)).

## What's in here

- **`bpr_pc_module_offsets.cpp`** — the nested layout of `BrnGame::BrnGameModule`
  (the root game object, `gpBurnoutGame`, at `0x013FC8E0`) and its sub-modules. Each
  member is annotated with its **byte offset inside the parent module**, e.g.

  ```cpp
  class WorldModule {
    /* 0x280 */    BrnWorld::RaceCarEntityModule mRaceCarEntityModule;
    /* 0x195C40 */ BrnPhysics::PhysicsModule     mPhysicsModule;
    ...
  };
  ```

## Why it's useful for the decomp

- It is the **skeleton of the engine's runtime object tree**: which module owns which
  sub-module, and exactly where each lives in memory. That lets you turn a raw pointer
  seen in the disassembler into a named, typed module field.
- The offsets let you **walk from `gpBurnoutGame` to any subsystem** (renderer, world,
  physics, AI, GUI, sound, network…) when reading PC-build pseudocode.
- It records **version deltas** worth knowing: e.g. the replay module was removed, and
  an `UnknownModule` (global model dictionary) was added after 1.6 — so the layout
  here is specific to the analyzed PC revision.
