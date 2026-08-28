This report is a read-only decode of the three stage-3 playback-factory creates. Instruction, offset, and register claims below come from the `assembly` field of the cited BURNOUT_X360_ARTIST dossier. Pseudocode was not used as behavioral authority. C++ spellings are the recovered symbol/DWARF spellings; each signature is paired with the lowered PPC register shape visible in assembly.

# RWAC

## Create function: `GenericRwacFactory::Create` @ `0x826C7AD0`

### Signature and lowered ABI

Semantic signature:

```cpp
static Handle<GenericRwacFactory>
GenericRwacFactory::Create(Environment& arEnvironment,
                           GenericRwacFactorySpec aSpec);
```

The X360 lowering is:

- `r3` = hidden return-storage pointer (`Handle<GenericRwacFactory>*`), preserved in `r29`.
- `r4` = `Environment*`, preserved in `r30`.
- the 16-byte by-value spec arrives packed in `r5:r6`; the two `std` instructions at `0x826C7ADC` and `0x826C7AEC` materialize it on the caller frame as four words: `+0 mpSystem`, `+4 entityCount`, `+8 dataBytes`, `+0xC stringBytes`.
- return value is the original hidden return-storage pointer in `r3`. [X360 `0x826C7AD0`]

This by-value lowering is materially different from the pointer-to-spec lowering used by the other two creates.

### Default-system resolution and allocation

The create loads `spec.mpSystem` from the first word. If it is null, it loads `off_83271928`, writes that pointer back into the local spec, and asserts `"lSpec.mpSystem"` if the global is also null. The derived constructor therefore always sees the resolved system pointer in `spec+0`. [X360 `0x826C7AD0`]

The requested byte count is computed register-for-register as:

```text
r11 = spec.entityCount + 0x100F
r11 = r11 << 2
r10 = r11 + spec.dataBytes
r10 = r10 + spec.stringBytes

bytes = 4 * (entityCount + 4111) + dataBytes + stringBytes
```

The allocation request passed to the allocator contains five `(size, alignment)` pairs in stack order: `(bytes, 4)`, then four `(0, 1)` pairs. The allocator object is loaded from `Environment+0x30`; its vtable slot `+0x10` is invoked with `r3=&allocationResult`, `r4=allocator`, `r5=&request`, and `r6="GenericRwacFactory"`. The returned allocation is read from word zero of the result object. [X360 `0x826C7AD0`]

For Prepare stage 3, `Module::Prepare` supplies `entityCount=0x80`, `dataBytes=0x7E80`, `stringBytes=0`, and `mpSystem=off_83271928`. Thus the exact request is:

```text
4 * (0x80 + 0x100F) + 0x7E80 = 0xC0BC = 49,340 bytes
alignment = 4
```

The four spec words are built at `0x826E92B8..0x826E92D8`, packed back into `r5:r6` at `0x826E92E4..0x826E92EC`, and passed to this create. [X360 `0x826E90C0`; size arithmetic X360 `0x826C7AD0`]

### Construction, registration, and returned handle

If allocation succeeds, the create calls `GenericRwacFactory::GenericRwacFactory` @ `0x826C17A0` with `r3=allocation`, `r4=Environment*`, `r5=&resolvedLocalSpec`. It writes the resulting object pointer to the hidden handle storage and, when non-null, increments the word at object `+0x04`. That is the `Factory`/`Object` reference count. [X360 `0x826C7AD0`]

`Module::Prepare` assigns the returned temporary handle into `Module+0x225C`, releases the temporary with `Object::Release`, and asserts that the stored handle is non-null. [X360 `0x826E90C0`]

The recursive constructor shape is:

```text
GenericRwacFactory::Create                         0x826C7AD0
└─ GenericRwacFactory::GenericRwacFactory         0x826C17A0
   ├─ Factory::Factory                            0x826AD340
   │  └─ Environment::AddFactory                  0x826AD130
   ├─ Registry::Registry at this+0x4020           0x82692C38
   ├─ RwacLock::RwacLock stack guard              0x826810F8
   └─ System::GetDecoderRegistry                  0x82B6DD78
      └─ DecoderRegistry::CreateInstance (lazy)   0x82B6C728
         └─ System::New2<DecoderRegistry>         0x82B6C248
            └─ STOP: exact dossier file unavailable
```

No constructor edge is omitted below. `Factory`, `Registry`, and `RwacLock` contain no further constructor calls in their `xrefs_from` lists. The lazy decoder-registry path is walked until `System::New2<DecoderRegistry>` @ `0x82B6C248`, whose exact dossier file is unavailable. [X360 `0x826C17A0`, `0x826AD340`, `0x82692C38`, `0x826810F8`, `0x82B6DD78`, `0x82B6C728`]

## Constructor cascade

### `Factory::Factory` @ `0x826AD340` — base subobject at `this+0x00`

Lowered arguments are `r3=this`, `r4=const Name*`, `r5=Environment*`. Its complete member-store order is:

| Order | Overall offset | Stored value | Assembly derivation |
|---:|---:|---|---|
| 1 | `+0x00` | `off_820B0DA0` | `lis/addi r10`; `stw r10,0(r31)` |
| 2 | `+0x04` | `0` | `li r9,0`; `stw r9,4(r31)` |
| 3 | `+0x08` | `*(u32*)NameArg` | `lwz r11,0(r4)`; `stw r11,8(r31)` |
| 4 | `+0x0C` | `Environment*` from `r5` | `stw r5,0xC(r31)` |

[X360 `0x826AD340`]

It then calls `Environment::AddFactory(environment, this)` and asserts `"lbResult"` if that returns false. `AddFactory` scans the pointer array at `Environment+0x40` for the first null entry, bounded by the count at `Environment+0x34`. When it finds a slot it performs two explicit `+1` reference-count increments around the slot assignment and one `Object::Release`, leaving one net environment-owned reference, stores `this` in the selected table word, and returns 1; if no slot exists it returns 0. [X360 `0x826AD340`, `0x826AD130`]

For RWAC the base is at offset zero, so the environment table receives the same pointer returned by the create.

### `GenericRwacFactory::GenericRwacFactory` @ `0x826C17A0`

Lowered arguments are `r3=this`, `r4=Environment*`, `r5=const GenericRwacFactorySpec*`. Before the base call it loads `dword_83008650`, copies the word to a stack `Name`, and passes that `Name` plus the environment to `Factory::Factory`. The writer for that global is static initializer `sub_82C654A8`, which computes `Name::MakeHash("~GenericRwacFactory::SK_NAME~")` and stores the result at `dword_83008650`. [X360 `0x826C17A0`, `0x82C654A8`]

After the base returns, the derived member stores occur in this exact order:

| Order | Offset | Stored value | Derivation / role |
|---:|---:|---|---|
| 1 | `+0x00` | `off_820B2E04` | final derived vtable address |
| 2 | `+0x10` | `spec.mpSystem` | `lwz r11,0(r31)` where `r31=spec`; then `stw` |
| 3 | `+0x4014` | `0` | first explicit `RwacCommandQueue` control word |
| 4 | `+0x4018` | `0` | second explicit `RwacCommandQueue` control word |
| 5 | `+0x401C` | `this+0x4020` | nested-registry pointer |
| 6 | `+0x4020...` | nested `Registry` | call `Registry::Registry(this+0x4020, spec+4)` |

[X360 `0x826C17A0`]

There are no constructor stores into the queue payload range `this+0x14..this+0x4013`; only the two control words at `+0x4014/+0x4018` are explicitly zeroed by this constructor. [X360 `0x826C17A0`]

The fixed portion through the nested `Registry` header is `0x4020 + 0x1C = 0x403C`, which is the `0x100F`-word fixed term used by the create. [X360 `0x826C17A0`, `0x82692C38`, `0x826C7AD0`]

### `Registry::Registry` @ `0x82692C38` — nested at factory `+0x4020`

The spec pointer passed by the derived constructor is its factory spec `+4`, so RegistrySpec word offsets are `+0 entityCapacity`, `+4 dataBytes`, `+8 stringBytes`. The nested constructor's complete member initialization, in executed store order, is:

| Order | Registry-relative offset | Stored value |
|---:|---:|---|
| 1 | `+0x00` | `0` |
| 2 | `+0x04` | `spec.entityCapacity` |
| 3 | `+0x08` | `spec.dataBytes` |
| 4 | `+0x10` | `spec.stringBytes` |
| 5 | `+0x1C + 4*i`, `i=[0,capacity)` | `0` for every entity-table word, in ascending order |
| 6 | `+0x0C` | `this + 4*(capacity+7)` = first byte after the `0x1C` header and entity table |
| 7 | `+0x14` | if `stringBytes != 0`, `this + 4*(capacity+7) + dataBytes`; otherwise `0` |
| 8 | `+0x18` | `capacity-1` |

The pointer formula follows the `addi capacity,7; slwi,2; add this` sequence. The constructor asserts that the pointer written to `+0x0C` is four-byte aligned and that capacity is nonzero and a power of two (`capacity & (capacity-1) == 0`). It makes no nested constructor call. [X360 `0x82692C38`]

### `RwacLock::RwacLock` @ `0x826810F8` — stack temporary

The derived constructor reuses its stack `Name` slot as a four-byte lock guard and calls this constructor with the system from factory `+0x10`. The complete object store behavior is:

1. store incoming `System*` at guard `+0x00`;
2. if null, load `off_83271928` and overwrite guard `+0x00`;
3. if still null, assert `"mpSystem"`;
4. load guard `+0x00` into `r3` and call `System::Lock` @ `0x82B6BCC8`.

[X360 `0x826810F8`; call site X360 `0x826C17A0`]

The tail of the derived constructor reloads that saved pointer and calls `System::Unlock` @ `0x82B6BCF0`. There is no separate destructor call in this optimized body. [X360 `0x826C17A0`]

## Registration performed by the RWAC constructor

After locking, the constructor calls `System::GetPlugInRegistry` @ `0x82B6DDC0` and passes each returned descriptor to `PlugInRegistry::RegisterPlugInRunTime` @ `0x82B6A938`, strictly in this order: [X360 `0x826C17A0`]

| Order | Descriptor source | Address |
|---:|---|---:|
| 1 | `AiffWriter::GetPlugInDescRunTime` | `0x82B968B0` |
| 2 | `BandPassIir2::GetPlugInDescRunTime` | `0x82B96A40` |
| 3 | `Dac::GetPlugInDescRunTime` | `0x82B96DB8` |
| 4 | `Gain::GetPlugInDescRunTime` | `0x82B97350` |
| 5 | `GainFader::GetPlugInDescRunTime` | `0x82B97368` |
| 6 | `HighPassIir2::GetPlugInDescRunTime` | `0x82B978B0` |
| 7 | `HighPassButterworth::GetPlugInDescRunTime` | `0x82B976D0` |
| 8 | `HighShelfIir2::GetPlugInDescRunTime` | `0x82B97978` |
| 9 | `Limiter1::GetPlugInDescRunTime` | `0x82B97AA0` |
| 10 | `LowPassIir2::GetPlugInDescRunTime` | `0x82B97DB0` |
| 11 | `LowPassButterworth::GetPlugInDescRunTime` | `0x82B97BF0` |
| 12 | `LowShelfIir2::GetPlugInDescRunTime` | `0x82B97E70` |
| 13 | `Pan2D::GetPlugInDescRunTime` | `0x82B984E8` |
| 14 | `Pan2D1::GetPlugInDescRunTime` | `0x82B98748` |
| 15 | `Pause::GetPlugInDescRunTime` | `0x82B9A130` |
| 16 | `PeakingIir2::GetPlugInDescRunTime` | `0x82B9A460` |
| 17 | `Rechannel::GetPlugInDescRunTime` | `0x82B9A718` |
| 18 | `Resample::GetPlugInDescRunTime` | `0x82B9A850` |
| 19 | `ReverbModel1::GetPlugInDescRunTime` | `0x82B9AD98` |
| 20 | `Send::GetPlugInDescRunTime` | `0x82B9B798` |
| 21 | `SndPlayer1::GetPlugInDescRunTime` | `0x82B9BE60` |
| 22 | `SubMix::GetPlugInDescRunTime` | `0x82B9C370` |
| 23 | descriptor global labeled `"GinsuPlayer"` | `off_82F2D094` |
| 24 | descriptor global labeled `"SndPlayer1_CgsStreamMod"` | `off_82F2E124` |
| 25 | descriptor global labeled `"GainArray"` | `off_82F2E664` |

The last three are not accessor calls: their addresses are formed directly with `lis/addi` and passed to `RegisterPlugInRunTime`. [X360 `0x826C17A0`]

It then calls `System::GetDecoderRegistry` @ `0x82B6DD78`, calls `DecoderRegistry::RegisterStandardRunTimeDecoders` @ `0x82B6B538`, and registers `Pcm16BigDec::GetDecoderDesc` @ `0x82B91E38` directly. The standard-registration callee itself registers, in order, `Xas1Dec` @ `0x82B91E90`, `XasDec` @ `0x82B91E80`, and `EaXmaDec` @ `0x82B93B88`, each through `DecoderRegistry::RegisterDecoder` @ `0x82B67CB0`. [X360 `0x826C17A0`, `0x82B6B538`]

The getter is a lazy nested-create edge. It reads `this+0x2C`; if null, it loads the default System from `off_83271928`, calls `DecoderRegistry::CreateInstance(defaultSystem)` @ `0x82B6C728`, stores the returned registry at the original System's `+0x2C`, and finally returns `this+0x2C`. [X360 `0x82B6DD78`]

`DecoderRegistry::CreateInstance` passes `r3=System*`, `r4=&localResult`, `r5=0`, `r6=0`, `r7=0x10`, and `r8=0` to `System::New2<DecoderRegistry>` @ `0x82B6C248`; if the returned pointer is non-null it stores the input System at registry `+0x0C`, then returns the pointer. No other registry member store is visible at this level. The exact `0x82B6C248.json` dossier is absent, so allocation-internal initialization below that call is not inferred. [X360 `0x82B6C728`]

## PC-home status

| Function / datum | Status | PC finding |
|---|---|---|
| `GenericRwacFactory::Create` `0x826C7AD0` | **absent** | No class-level create implementation in `Sound/Playback/RWAC/CgsGenericRwacFactory.*`. |
| `GenericRwacFactory::GenericRwacFactory` `0x826C17A0` | **absent** | The current RWAC file only homes `RwacLock` and default-system shims. |
| `Factory::Factory` `0x826AD340` | **exists-faithful** | `Sound/Playback/CgsFactory.cpp` reproduces base fields and environment registration. |
| `Environment::AddFactory` `0x826AD130` | **exists-faithful** | `Sound/Playback/CgsEnvironment.cpp` has the table insertion/reference ownership behavior. |
| `Registry::Registry` `0x82692C38` | **exists-faithful** | `Sound/Playback/CgsRegistry.cpp` reproduces header/table/data/string layout semantics. |
| `RwacLock::RwacLock` `0x826810F8` | **exists-faithful** | `Sound/Playback/RWAC/CgsGenericRwacFactory.cpp` reproduces fallback, assert, and lock. |
| RWAC static name writer `0x82C654A8` / `dword_83008650` | **exists-divergent** | `GameSource/BrnBaselineLinkStubs.cpp` currently returns a default `Name` and defines `gu32VoiceTypeTag=0`; the X360 computes the hash of `"~GenericRwacFactory::SK_NAME~"`. [X360 `0x82C654A8`] |
| `Dac`/`GainFader`/`LowPassButterworth`/`SndPlayer1`/`SubMix` descriptor accessors | **absent** | No exact PC definitions were found; details are in the combined worklist. |
| custom descriptor globals `off_82F2D094`, `off_82F2E124`, `off_82F2E664` | **absent** | Some plugin implementation slices exist, but no faithful runtime descriptor homes matching these three constructor operands exist. |
| `System::GetDecoderRegistry` `0x82B6DD78` | **absent** | Exact X360 body is available and decoded above, but no PC definition exists. Its callee `DecoderRegistry::CreateInstance` `0x82B6C728` is already homed faithfully; only the nested `New2<DecoderRegistry>` dossier `0x82B6C248` is unavailable. |

# AEMS

## Create function: `AemsFactory::Create` @ `0x826DAC28`

### Signature and lowered ABI

Semantic signature:

```cpp
static Handle<AemsFactory>
AemsFactory::Create(Environment& arEnvironment,
                    const AemsFactorySpec& arSpec);
```

The X360 lowering is `r3=hidden Handle<AemsFactory>* result`, `r4=Environment*`, and `r5=const AemsFactorySpec*`. The create preserves those in `r28`, `r29`, and `r31`, respectively. Unlike RWAC, no spec words are passed by value in `r5:r6`. [X360 `0x826DAC28`]

The four spec words consumed by this cascade are:

```text
+0x00 Handle<GenericRwacFactory> raw pointer
+0x04 RegistrySpec.entityCount
+0x08 RegistrySpec.dataBytes
+0x0C RegistrySpec.stringBytes
```

That layout is established by the allocation loads at `+4/+8/+0xC`, the retained-handle load at constructor `spec+0`, and the nested Registry call with `spec+4`. [X360 `0x826DAC28`, `0x826DAAD0`]

### Allocation and returned handle

The allocation size is:

```text
bytes = 4 * (spec.entityCount + 0x162)
      + spec.dataBytes
      + spec.stringBytes
```

As in RWAC, the request is `(bytes,4)` plus four `(0,1)` pairs, dispatched through the allocator at `Environment+0x30`, vtable slot `+0x10`, with tag `"AemsFactory"`. On success the create calls `AemsFactory::AemsFactory` @ `0x826DAAD0`. [X360 `0x826DAC28`]

Prepare stage 3 constructs `{rwacHandle, 0x80, 0x7E80, 0}` and passes its address in `r5`, so the exact request is:

```text
4 * (0x80 + 0x162) + 0x7E80 = 0x8608 = 34,312 bytes
alignment = 4
```

[X360 `0x826E90C0`; size arithmetic X360 `0x826DAC28`]

The create writes the overall object pointer to the hidden handle storage, but increments the word at overall object `+0x08`, not `+0x04`. That is because the first subobject is `Snd9::IAemsSamplePlayerFactory` at `+0`, while `Factory` begins at `+4` and its reference count is four bytes into that base. This one instruction (`lwz/stw 8(r30)`) is the load-bearing multiple-inheritance proof. [X360 `0x826DAC28`; base placement X360 `0x826C26B8`]

`Module::Prepare` assigns this temporary to `Module+0x2260`, then releases the temporary through the first interface vtable's `+4` slot and releases the RWAC handle held by the temporary spec. [X360 `0x826E90C0`]

The recursive constructor shape is:

```text
AemsFactory::Create                                  0x826DAC28
└─ AemsFactory::AemsFactory                          0x826DAAD0
   ├─ AemsRWSampleFactory::AemsRWSampleFactory       0x826C26B8
   │  ├─ Factory::Factory at overall this+0x04       0x826AD340
   │  │  └─ Environment::AddFactory                  0x826AD130
   │  └─ System::GetDecoderRegistry                  0x82B6DD78
   │     └─ DecoderRegistry::CreateInstance (lazy)   0x82B6C728
   │        └─ System::New2<DecoderRegistry>         0x82B6C248
   │           └─ STOP: exact dossier file unavailable
   └─ Registry::Registry at overall this+0x56C       0x82692C38
```

All constructor/nested-create edges in the relevant `xrefs_from` lists are exhausted by this graph through the unavailable `0x82B6C248` leaf dossier. [X360 `0x826DAC28`, `0x826DAAD0`, `0x826C26B8`, `0x82B6DD78`, `0x82B6C728`]

## Constructor cascade

### `Factory::Factory` @ `0x826AD340` — base subobject at overall `this+0x04`

`AemsRWSampleFactory` calls the base with `r3=overallThis+4`. Consequently the base stores land at these overall offsets, in order:

| Order | Overall offset | Stored value |
|---:|---:|---|
| 1 | `+0x04` | base vtable `off_820B0DA0` |
| 2 | `+0x08` | `0` reference count |
| 3 | `+0x0C` | copied `Name` word |
| 4 | `+0x10` | `Environment*` |

[X360 `0x826C26B8`, base stores X360 `0x826AD340`]

The base calls `Environment::AddFactory(environment, overallThis+4)`, so the environment's factory table contains the `Factory` subobject pointer, not the overall IAems interface pointer. `AddFactory` uses the same first-null-slot and net-one-reference algorithm described in RWAC. [X360 `0x826AD340`, `0x826AD130`, caller adjustment X360 `0x826C26B8`]

### `AemsRWSampleFactory::AemsRWSampleFactory` @ `0x826C26B8`

Semantic signature:

```cpp
AemsRWSampleFactory::AemsRWSampleFactory(Name aName,
                                         Environment& arEnvironment);
```

Lowered arguments are `r3=overall this`, `r4=const Name*`, `r5=Environment*`. Its complete direct member/vptr initialization in execution order is:

| Order | Overall offset | Stored value | Derivation |
|---:|---:|---|---|
| 1 | `+0x00` | `off_820AB168` | provisional `IAemsSamplePlayerFactory` vptr before base construction |
| 2–5 | `+0x04,+0x08,+0x0C,+0x10` | `Factory` base stores listed above | nested base call with `r3=this+4` |
| 6 | `+0x00` | `off_820B2F84` | final AemsRW interface vptr |
| 7 | `+0x04` | `off_820B2F70` | final `Factory`-subobject vptr |
| 8 | `+0x38` | plugin registry returned by `System::GetPlugInRegistry` | system is loaded directly from `off_83271928` and locked first |
| 9 | `+0x3C` | result of registering Gain descriptor | `Gain` getter then `RegisterPlugInRunTime` |
| 10 | `+0x40` | result of registering Pan2D descriptor | same call shape |
| 11 | `+0x44` | result of registering Route descriptor | same call shape |
| 12 | `+0x4C` | result of registering SndPlayer1 descriptor | same call shape |
| 13 | `+0x50` | result of registering Rechannel descriptor | same call shape |
| 14 | `+0x54` | result of registering Resample descriptor | same call shape |
| 15 | `+0x48` | `GetPlugInHandle(0x53656E30)` result | ID is synthesized by `lis 0x5365; ori 0x6E30` |
| 16 | `+0x58` | `GetPlugInHandle(0x53756230)` result | ID is synthesized by `lis 0x5375; ori 0x6230` |

[X360 `0x826C26B8`]

The registration operations used for orders 9–14 are, in order:

| Member result | Descriptor getter | Getter address |
|---|---|---:|
| `+0x3C` | `Gain::GetPlugInDescRunTime` | `0x82B97350` |
| `+0x40` | `Pan2D::GetPlugInDescRunTime` | `0x82B984E8` |
| `+0x44` | `Route::GetPlugInDescRunTime` | `0x82B9B258` |
| `+0x4C` | `SndPlayer1::GetPlugInDescRunTime` | `0x82B9BE60` |
| `+0x50` | `Rechannel::GetPlugInDescRunTime` | `0x82B9A718` |
| `+0x54` | `Resample::GetPlugInDescRunTime` | `0x82B9A850` |

Every getter result is passed to `PlugInRegistry::RegisterPlugInRunTime` @ `0x82B6A938`. The two opaque IDs are passed to `PlugInRegistry::GetPlugInHandle` @ `0x82B6A908`. [X360 `0x826C26B8`]

Next it calls `System::GetDecoderRegistry` @ `0x82B6DD78`, registers `XasDec::GetDecoderDesc` @ `0x82B91E80`, then `Xas1Dec::GetDecoderDesc` @ `0x82B91E90`, both through `DecoderRegistry::RegisterDecoder` @ `0x82B67CB0`, and unlocks the system. [X360 `0x826C26B8`]

The getter first reads System `+0x2C`. On null it calls `DecoderRegistry::CreateInstance` @ `0x82B6C728` using `off_83271928`, writes the result back to the original System `+0x2C`, and returns that member. The create calls missing-dossier `System::New2<DecoderRegistry>` @ `0x82B6C248` with requested alignment `0x10`; on success it stores its System argument at registry `+0x0C`. This is the same lazy nested-create branch reached by RWAC, and it terminates at the unavailable `0x82B6C248` dossier rather than at the getter. [X360 `0x82B6DD78`, `0x82B6C728`]

Finally, it initializes the three 12-byte plugin-config records in this exact store order:

| Order | Offset | Stored value |
|---:|---:|---|
| 17 | `+0x18` | value loaded from handle `+0x58` |
| 18 | `+0x24` | value loaded from handle `+0x40` |
| 19 | `+0x14` | `0` |
| 20 | `+0x20` | `0` |
| 21 | byte `+0x1C` | `1` |
| 22 | byte `+0x28` | `6` |
| 23 | `+0x30` | value loaded from handle `+0x48` |
| 24 | `+0x2C` | `0` |
| 25 | byte `+0x34` | `6` |

[X360 `0x826C26B8`]

The assembly does not write the other bytes of the three records here; no values should be inferred for them from this constructor alone.

### `AemsFactory::AemsFactory` @ `0x826DAAD0`

Lowered arguments are `r3=overall this`, `r4=Environment*`, `r5=const AemsFactorySpec*`. It loads `dword_83008664` into a stack `Name` and invokes the AemsRW base with that name and environment. Static initializer `sub_82C65788` writes this global by hashing `"~AemsFactory::SK_NAME~"`. [X360 `0x826DAAD0`, `0x82C65788`]

After the base completes, direct stores occur in this order:

| Order | Overall offset | Stored value | Derivation / role |
|---:|---:|---|---|
| 1 | `+0x00` | `off_820B2ED0` | final AemsFactory interface vptr |
| 2 | `+0x04` | `off_820B2EBC` | final Factory-subobject vptr |
| 3 | `+0x64` | raw RWAC pointer from `spec+0` | retained handle member |
| 4 | pointee `+0x04` | old count + 1, if pointer non-null | retain of RWAC factory handle |
| 5 | `+0x464` | `0` | command-queue control word |
| 6 | `+0x468` | `0` | command-queue control word |
| 7 | `+0x60` | `this+0x56C` | registry pointer |
| 8 | `+0x56C...` | nested `Registry` | `Registry(this+0x56C, spec+4)` |
| 9 | `+0x5C` | `0` | patch-monitor count, after the CSIS initialized check |

[X360 `0x826DAAD0`]

The fixed term in the create follows directly: nested Registry starts at `0x56C`, and its fixed header is `0x1C`, totaling `0x588 = 4*0x162`. [X360 `0x826DAAD0`, `0x82692C38`, `0x826DAC28`]

The nested `Registry::Registry` has the same complete store order and formulas documented in RWAC: `+0=0`, `+4=capacity`, `+8=dataBytes`, `+0x10=stringBytes`, clear all `+0x1C+4*i` table words, write data pointer at `+0x0C`, conditional string pointer at `+0x14`, and mask `capacity-1` at `+0x18`. [X360 `0x82692C38`; AEMS call site X360 `0x826DAAD0`]

After member construction, the constructor:

1. calls `Csis::System::IsInited` @ `0x82B10040` and asserts if its low byte is zero;
2. materializes the address of `AemsFactory::CsisPrint` @ `0x8268A018` in `r3` and calls `0x82B0F1B8`;
3. calls `Snd9::Aems::SetSamplePlayerFactory(this)` @ `0x82B6FCD0`.

The exact dossier for `0x82B0F1B8` is a two-instruction leaf (`li r3,0; blr`), despite its unrelated ICF label `MassiveAdClient3::CMassiveAdObject::GetBestImpression`; it neither reads the callback address nor writes state. Therefore this particular X360 call has no observable registration effect and must not be promoted into an invented CSIS callback registry. [X360 `0x826DAAD0`, callee X360 `0x82B0F1B8`]

`SetSamplePlayerFactory` stores the overall `this` pointer into `off_82F87DBC`. [X360 `0x82B6FCD0`; call site X360 `0x826DAAD0`]

## PC-home status

| Function / datum | Status | PC finding |
|---|---|---|
| `AemsFactory::Create` `0x826DAC28` | **absent** | No implementation in `Sound/Playback/AEMS/CgsAemsFactory.*`. |
| `AemsFactory::AemsFactory` `0x826DAAD0` | **absent** | Current class is an explicitly flagged minimal placeholder with no ctor/create. |
| `AemsRWSampleFactory::AemsRWSampleFactory` `0x826C26B8` | **absent** | Declared in `CgsAemsInterfaceImplementation.h`, not defined. |
| `AemsRWSampleFactory` PC class shape | **exists-divergent** | Current declaration derives only from `Factory`; X360 assembly proves an IAems interface at `+0` and `Factory` at `+4`, with two final vptr stores. [X360 `0x826C26B8`] |
| `Factory::Factory` `0x826AD340` | **exists-faithful** | Base field stores and environment insertion are homed. |
| `Registry::Registry` `0x82692C38` | **exists-faithful** | Registry storage semantics are homed. |
| `Csis::System::IsInited` `0x82B10040` | **exists-faithful** | `SDKs/Csis/CsisSystem.cpp`. |
| `Snd9::Aems::SetSamplePlayerFactory` `0x82B6FCD0` / `off_82F87DBC` | **exists-faithful** | `SDKs/EATech/include/snd/sndaems.cpp`. |
| `AemsFactory::CsisPrint` `0x8268A018` | **exists-divergent** | Current PC declaration is a non-static member. The constructor passes its raw code address as a one-argument callback, and the X360 function consumes the text in `r3`; a hidden `this` ABI would not match. [X360 `0x826DAAD0`, `0x8268A018`] |
| AEMS static name writer `0x82C65788` / `dword_83008664` | **absent** | No faithful `"~AemsFactory::SK_NAME~"` hash home was found. |
| `SndPlayer1::GetPlugInDescRunTime` `0x82B9BE60` | **absent** | Called directly by the base ctor; no PC definition was found. |
| `System::GetDecoderRegistry` `0x82B6DD78` | **absent** | Exact X360 lazy-create body is available; no PC definition exists. `DecoderRegistry::CreateInstance` `0x82B6C728` is already faithfully homed. |

# Splicer

## Create function: `SplicerFactory::Create` @ `0x826DB130`

### Signature and lowered ABI

Semantic signature:

```cpp
static Handle<SplicerFactory>
SplicerFactory::Create(Environment& arEnvironment,
                       const SplicerFactorySpec& arSpec);
```

The lowered ABI matches AEMS: `r3=hidden result`, `r4=Environment*`, `r5=const SplicerFactorySpec*`. Spec layout is `+0 RWAC handle`, `+4 entityCount`, `+8 dataBytes`, `+0xC stringBytes`, as shown jointly by the create loads and constructor accesses. [X360 `0x826DB130`, `0x826DB010`]

### Allocation and returned handle

The size formula is:

```text
bytes = 4 * (spec.entityCount + 0x1C0)
      + spec.dataBytes
      + spec.stringBytes
```

The allocation request again contains `(bytes,4)` plus four `(0,1)` pairs and is issued through `Environment+0x30`, vtable `+0x10`, with tag `"SplicerFactory"`. On success it calls `SplicerFactory::SplicerFactory` @ `0x826DB010`. [X360 `0x826DB130`]

Prepare stage 3 passes `{rwacHandle,0x80,0x7E80,0}`, producing:

```text
4 * (0x80 + 0x1C0) + 0x7E80 = 0x8780 = 34,688 bytes
alignment = 4
```

[X360 `0x826E90C0`; size arithmetic X360 `0x826DB130`]

The result pointer is stored into the hidden handle and its `+0x04` reference count is incremented. `Module::Prepare` assigns the temporary into `Module+0x2264`, releases the temporary, asserts non-null, releases the RWAC handle held by the spec, and finally publishes `Module+0x228` to global `off_82FFBA0C`. [X360 `0x826DB130`, `0x826E90C0`]

The recursive construction/nested-creation shape is:

```text
SplicerFactory::Create                                0x826DB130
└─ SplicerFactory::SplicerFactory                    0x826DB010
   ├─ Factory::Factory                               0x826AD340
   │  └─ Environment::AddFactory                     0x826AD130
   ├─ Registry::Registry at this+0x1C                0x82692C38
   └─ SpliceManager::SpliceManager in trailing arena 0x826C30C8
      ├─ 8 inlined SpliceContainer zero ctors
      ├─ CreateMonoVoice × monoCount (=64 here)       0x826A32E0
      │  └─ Voice::CreateInstance                     0x82B6EC50
      ├─ CreateStereoVoice × stereoCount (=24 here)   0x826A33C0
      │  └─ Voice::CreateInstance                     0x82B6EC50
      └─ VoicePool::Prepare ×2 (direct leaf)           0x8268AC40
```

`VoicePool::Prepare` has an exact dossier and no direct functional callee beyond its ABI save helper; its complete pool stores are decoded below. [X360 `0x8268AC40`]

## Constructor cascade

### `Factory::Factory` @ `0x826AD340` — base at `this+0x00`

The complete direct base stores are, in order, `+0x00=off_820B0DA0`, `+0x04=0`, `+0x08=*NameArg`, `+0x0C=Environment*`, followed by `Environment::AddFactory(environment,this)` and an assertion if insertion fails. [X360 `0x826AD340`]

`Environment::AddFactory` scans the table at environment `+0x40` up to count `+0x34`, stores the first free slot, and retains one net table-owned reference through its two-increment/one-release sequence. [X360 `0x826AD130`]

### `SplicerFactory::SplicerFactory` @ `0x826DB010`

Lowered arguments are `r3=this`, `r4=Environment*`, `r5=const SplicerFactorySpec*`. It copies `dword_83008404` to a stack `Name` and calls the base. Static initializer `sub_82C65938` computes this word from `Name::MakeHash("~SplicerFactory::SK_NAME~")`. [X360 `0x826DB010`, `0x82C65938`]

After base construction, the derived stores/calls occur in this order:

| Order | Factory-relative offset | Stored value | Derivation / role |
|---:|---:|---|---|
| 1 | `+0x00` | `off_820B3050` | final SplicerFactory vtable |
| 2 | `+0x14` | raw RWAC pointer from `spec+0` | retained handle member |
| 3 | pointee `+0x04` | old count + 1, if non-null | retain RWAC factory |
| 4 | `+0x10` | `this+0x1C` | registry pointer |
| 5 | `+0x1C...` | nested `Registry` | `Registry(this+0x1C,spec+4)` |
| 6 | `+0x18` | trailing `SpliceManager*` | formula below |
| 7 | nested manager | `SpliceManager(manager, environment, 0x40, 0x18)` | mono/stereo pool counts 64/24 |
| 8 | manager `+0x610` | code address `SplicerFactory::SplicerAssertFunc` @ `0x8268ABA0` | explicit post-construction callback store |

[X360 `0x826DB010`]

The manager address is derived entirely from Registry members:

```text
registry = *(this+0x10)                    // this+0x1C
manager  = registry
         + 4 * (*(registry+0x04) + 7)      // Registry header + entity table
         + *(registry+0x08)                 // data bytes
         + *(registry+0x10)                 // string bytes
```

This is the exact `lwz +4/+0x10/+8; addi 7; slwi 2; add/add/add` sequence at `0x826DB080..0x826DB0A0`. [X360 `0x826DB010`]

There is no alignment-rounding instruction in that placement sequence: the manager starts at the direct sum shown above. The enclosing allocation itself is four-byte aligned by the create. [X360 `0x826DB010`, `0x826DB130`]

Registry itself uses the same full store order described earlier: `+0=0`, `+4=capacity`, `+8=dataBytes`, `+0x10=stringBytes`, clear table words, `+0x0C=data start`, `+0x14=conditional string start`, `+0x18=capacity-1`. [X360 `0x82692C38`; call site X360 `0x826DB010`]

The fixed allocation term can be checked without guessing a class size: registry starts at factory `+0x1C`; its header/table/data/string expression leads exactly to the manager pointer above; the create reserves `0x700=4*0x1C0` fixed bytes around those variable regions. [X360 `0x826DB130`, `0x826DB010`, `0x82692C38`]

### `SpliceManager::SpliceManager` @ `0x826C30C8`

Semantic signature:

```cpp
SpliceManager::SpliceManager(const Environment& arEnvironment,
                             u32 auMonoVoiceCount,
                             u32 auStereoVoiceCount);
```

Lowered registers are `r3=this`, `r4=Environment*`, `r5=monoCount`, `r6=stereoCount`. The SplicerFactory call passes `0x40` and `0x18`. [X360 `0x826C30C8`, call site X360 `0x826DB010`]

#### Inlined construction of `SpliceContainer[8]`

The eight 20-byte records occupy manager `+0x614..+0x6B3`. The constructor zeroes every one of their 40 words. Because the compiler interleaves the inlined default constructions, the literal store order is important:

1. `+0x61C`;
2. `+0x658,+0x65C,+0x660,+0x650,+0x620,+0x654,+0x66C,+0x670,+0x674,+0x664,+0x668,+0x680,+0x684,+0x688,+0x678,+0x67C,+0x694,+0x698,+0x69C,+0x68C,+0x690,+0x6A8,+0x6AC,+0x6B0,+0x6A0,+0x6A4`;
3. `+0x624,+0x614,+0x618,+0x630,+0x634,+0x638,+0x628,+0x62C,+0x644,+0x648,+0x64C,+0x63C,+0x640`.

Every value in all three runs is zero. The first two runs use zero held in `r11/r30`; the last run reloads stack temporaries that the prologue explicitly initialized to zero. Collectively, these are exactly eight records at bases `+0x614 + 0x14*i`, each with words at `+0,+4,+8,+0xC,+0x10`. [X360 `0x826C30C8`]

#### Remaining direct member stores

After those inlined records, the direct member stores and registrations are:

| Order | Manager offset / global | Stored value | Derivation |
|---:|---:|---|---|
| 1 | `+0x610` | `0` | initial assertion callback |
| 2 | `+0x6C4` | incoming `Environment*` | saved from `r4` on entry and reloaded |
| 3 | `off_82FFB9F0` | `this` | process-global current manager |
| 4 | `+0x6B4` | `GetPlugInHandle(0x536E5031)` | registry returned after locking global system |
| 5 | `+0x6B8` | `GetPlugInHandle(0x52737030)` | same registry |
| 6 | `+0x6C0` | `GetPlugInHandle(0x53656E30)` | same registry |
| 7 | `+0x6BC` | `GetPlugInHandle(0x506E3231)` | same registry |
| 8 | `+0x300` | `0` | mono VoicePool count/control word, immediately before Prepare |
| 9 | `+0x608` | `0` | stereo VoicePool count/control word, immediately before Prepare |

[X360 `0x826C30C8`]

The apparent non-monotonic handle-store order is real: the send-like ID `0x53656E30` is stored at `+0x6C0` before the panner-like ID `0x506E3231` is stored at `+0x6BC`. [X360 `0x826C30C8`]

The manager locks `off_83271928`, retrieves the plugin registry, performs those four handle lookups, constructs `monoCount` stack `VoicePluginPair`s via `CreateMonoVoice`, constructs `stereoCount` stack pairs via `CreateStereoVoice`, calls `VoicePool::Prepare(this+0, monoPairs, monoCount)`, calls `VoicePool::Prepare(this+0x308, stereoPairs, stereoCount)`, then unlocks. [X360 `0x826C30C8`]

#### `VoicePool::Prepare` @ `0x8268AC40`

Semantic signature:

```cpp
bool SpliceManager::VoicePool::Prepare(VoicePluginPair* apaVoicePairs,
                                       u32 auVoiceCount);
```

The lowering is `r3=VoicePool*`, `r4=inputPairs`, `r5=count`. Before writing the pool, it checks three conditions and calls `off_82FFB9F0->+0x610` when that callback is non-null: `count <= 0x40` (message `"Too many voices for pool"`), `count != 0` (`"Must have at least 1 voice"`), and `inputPairs != 0` (`"No voices passed in"`). These callback checks do not introduce an assembly return branch; execution continues after each callback. [X360 `0x8268AC40`]

When `count != 0`, it initializes the pool in ascending index order. For each `i` from 0 through `count-1` it:

1. loads `inputPairs[i].word0` and, if null, calls the same manager callback with `"Null voice pointer"`;
2. stores `inputPairs[i].word0` to pool `+0x000 + 8*i`;
3. stores `inputPairs[i].word1` to pool `+0x004 + 8*i`;
4. stores the address `pool + 8*i` to the pointer stack at pool `+0x200 + 4*i`.

The address relation is explicit in `r27=inputPairs-pool`, followed by `lwzx r11,r27,r31` / `add r28,r27,r31` while `r31` advances by 8 and the destination pointer `r29=pool+0x200` advances by 4. [X360 `0x8268AC40`]

After the loop—or immediately when count is zero—the final stores are pool `+0x300=count` and pool `+0x304=count-1`, in that order; it then returns `1`. There are no further constructor or functional calls in `xrefs_from`. [X360 `0x8268AC40`]

#### `CreateMonoVoice` @ `0x826A32E0`

This helper is called with `r3=manager`, `r4=VoicePluginPair* out`, but its configuration reads the manager through global `off_82FFB9F0`. It builds four 12-byte stage-config records on the stack:

| Stage | config `+0` | config `+4` descriptor | config byte `+8` |
|---:|---|---|---:|
| 0 | pointer to a stack float loaded from `flt_82001C98` | manager `+0x6B4` | `1` |
| 1 | `0` | manager `+0x6B8` | `1` |
| 2 | `0` | manager `+0x6BC` | `6` |
| 3 | `0` | manager `+0x6C0` | `6` |

[X360 `0x826A32E0`]

It calls `Voice::CreateInstance` @ `0x82B6EC50` with `r3=0`, `r4=4`, `r5=&configs[0]`, `r6=&outPair->wordAt+4`, and `r7=off_83271928`; it writes the returned Voice pointer to `outPair+0`. If null, it loads callback `off_82FFB9F0->+0x610` and, when non-null, calls it with `"failed to create mono voice"`. [X360 `0x826A32E0`]

#### `CreateStereoVoice` @ `0x826A33C0`

This helper similarly builds three stage configs:

| Stage | config `+0` | config `+4` descriptor | config byte `+8` |
|---:|---|---|---:|
| 0 | pointer to a stack float loaded from `flt_82001D9C` | manager `+0x6B4` | `2` |
| 1 | `0` | manager `+0x6B8` | `2` |
| 2 | `0` | manager `+0x6C0` | `2` |

[X360 `0x826A33C0`]

It calls `Voice::CreateInstance` with `r3=0`, `r4=3`, `r5=&configs[0]`, `r6=&outPair+4`, and `r7=off_83271928`; stores the returned Voice at pair `+0`; and on failure calls callback `+0x610` with `"Failed to create stereo voice"` when present. [X360 `0x826A33C0`]

The float values themselves are not encoded in either helper's instructions—only their rodata addresses are—so this report does not infer their numerical values from these two dossiers.

#### Nested vendor voice creation and recursive leaf boundary

Both helpers reach `rw::audio::core::Voice::CreateInstance` @ `0x82B6EC50`. That function computes a dynamic allocation size from the stage count, the 12-byte configs, and each descriptor's indirect size query; allocates through `System::New2<Voice>` @ `0x82B6E140`; initializes the Voice and its plugin pointer table; and calls `PlugIn::CreateInstance` @ `0x82B6A818` for each stage. On success it writes `voice+0x4C` to the caller's plugin-array output and queues the new voice in the System. On plugin failure it calls `Voice::ReleaseImmediate` @ `0x82B6DF38` and returns null. [X360 `0x82B6EC50`]

The recursive direct-call walk then terminates for construction purposes:

- `System::New2<Voice>` @ `0x82B6E140` has no direct `xrefs_from` constructor call; it selects the system/default allocator, performs an indirect allocation, writes the returned block to the out pointer, and initializes block `+0x0C=0`. [X360 `0x82B6E140`]
- `PlugIn::CreateInstance` @ `0x82B6A818` initializes the generic plugin prefix and dispatches the descriptor-specific creation indirectly; it has no named direct constructor callee in `xrefs_from`. [X360 `0x82B6A818`]
- `Voice::ReleaseImmediate` is failure cleanup, not construction. [X360 `0x82B6DF38`]

The complete direct nested-creation walk therefore terminates at the `System::New2<Voice>` and indirect plugin-creation leaves described above, plus the fully decoded direct leaf `VoicePool::Prepare` @ `0x8268AC40`. [X360 `0x82B6E140`, `0x82B6A818`, `0x8268AC40`]

## PC-home status

| Function / datum | Status | PC finding |
|---|---|---|
| `SplicerFactory::Create` `0x826DB130` | **absent** | No create implementation in `Sound/Playback/Splicer/CgsSplicerFactory.*`. |
| `SplicerFactory::SplicerFactory` `0x826DB010` | **absent** | Header has a declared-only constructor of a different public shape; no body. |
| `Factory::Factory` `0x826AD340` | **exists-faithful** | Base constructor is homed. |
| `Registry::Registry` `0x82692C38` | **exists-faithful** | Nested registry constructor is homed. |
| `SpliceManager::SpliceManager` `0x826C30C8` | **absent** | No constructor definition. The existing type is also **layout-divergent** at `+0x6C4`: it models the assembly's saved `Environment&` as a heap pointer for the already-landed allocation slice. [X360 store `0x826C3208`] |
| `SpliceManager::CreateMonoVoice` `0x826A32E0` | **absent** | No declaration/definition matching this helper was found. |
| `SpliceManager::CreateStereoVoice` `0x826A33C0` | **absent** | Declared, not defined. |
| `SpliceManager::VoicePool::Prepare` `0x8268AC40` | **absent** | Declared, not defined. Exact X360 body is available and fully decoded above. |
| `rw::audio::core::Voice::CreateInstance` `0x82B6EC50` | **exists-faithful** | Vendor audio-core home exists; the manager helpers should call it rather than duplicate its allocator/plugin cascade. |
| `off_82FFB9F0` / `gpSpliceManager` | **exists-faithful** | Defined in `SpliceManager.cpp`; constructor still needs to publish it. |
| `SplicerFactory::SplicerAssertFunc` `0x8268ABA0` | **exists-divergent** | Observable assert body exists, but current PC declaration is a non-static member. The manager stores a raw one-argument callback address and later calls it with only the message in `r3`; hidden-`this` ABI is incompatible. [X360 `0x826DB010`, callback calls X360 `0x826A32E0`/`0x826A33C0`] |
| Splicer static name writer `0x82C65938` / `dword_83008404` | **absent** | No faithful `"~SplicerFactory::SK_NAME~"` hash home was found. |
| stage-3 publish global `off_82FFBA0C` | **absent** | Current Prepare comments defer this publish; X360 stores `Module+0x228` to it after the three handles are established. [X360 `0x826E90C0`] |

# Link-Closure Worklist

This section lists the un-homed or materially divergent symbols required to land the three cascades. Already faithful shared machinery—`Factory`, `Registry`, `Environment::AddFactory`, `RwacLock`, allocator interfaces, reference release, assertions, the plugin registry core, decoder registration core, `System::Lock/Unlock/GetPlugInRegistry`, `Csis::System::IsInited`, `Snd9::Aems::SetSamplePlayerFactory`, and `Voice::CreateInstance`—is intentionally excluded.

## Factory entry points and constructor bodies

| X360 address | Symbol | Required closure |
|---:|---|---|
| `0x826E90C0` | `Module::Prepare`, stage 3 | Replace the flagged null-handle block with the three create calls, assignments to `+0x225C/+0x2260/+0x2264`, temporary/spec releases, assertions, and `off_82FFBA0C` publish decoded in the three sections. |
| `0x826C7AD0` | `GenericRwacFactory::Create` | By-value spec ABI, `off_83271928` fallback, `0xC0BC` stage-3 allocation, construct, return-handle retain. |
| `0x826C17A0` | `GenericRwacFactory::GenericRwacFactory` | Base/registry construction and complete plugin/decoder registration pass. |
| `0x826DAC28` | `AemsFactory::Create` | Ref-spec ABI, `0x8608` stage-3 allocation, overall-pointer return with refcount at overall `+8`. |
| `0x826DAAD0` | `AemsFactory::AemsFactory` | AemsRW base, RWAC retain, command controls, Registry, CSIS check, global sample-factory install. |
| `0x826C26B8` | `AemsRWSampleFactory::AemsRWSampleFactory` | Correct IAems/Factory multiple inheritance, dual vptrs, runtime handles/configs, decoder registration. |
| `0x826DB130` | `SplicerFactory::Create` | Ref-spec ABI, `0x8780` stage-3 allocation, construct, return-handle retain. |
| `0x826DB010` | `SplicerFactory::SplicerFactory` | Factory/Registry/manager placement and callback install. |
| `0x826C30C8` | `SpliceManager::SpliceManager` | Eight containers, global publish, handles, 64/24 voice staging, both pool prepares. |
| `0x826A32E0` | `SpliceManager::CreateMonoVoice` | Four-stage config and failure callback. |
| `0x826A33C0` | `SpliceManager::CreateStereoVoice` | Three-stage config and failure callback. |
| `0x8268AC40` | `SpliceManager::VoicePool::Prepare` | Implement the decoded checks, pair copies, pointer-stack fill, count, and free-index stores. |

## Required ABI corrections

| X360 address | Symbol | Divergence to correct |
|---:|---|---|
| `0x8268A018` | `AemsFactory::CsisPrint` callback | Current non-static member shape is incompatible with the raw one-argument callback address passed by the ctor. [X360 `0x826DAAD0`, `0x8268A018`] |
| `0x8268ABA0` | `SplicerFactory::SplicerAssertFunc` callback | Current non-static member shape is incompatible with manager callback calls that pass only a message pointer. [X360 `0x826DB010`, `0x826A32E0`, `0x826A33C0`] |

## Missing vendor accessors and descriptor data

| X360 function/global | Dossier state | Required by |
|---|---|---|
| `System::GetDecoderRegistry` `0x82B6DD78` | Exact dossier decoded; PC home absent. Its lazy callee `DecoderRegistry::CreateInstance` `0x82B6C728` is faithfully homed; that callee's `System::New2<DecoderRegistry>` target `0x82B6C248` has no exact dossier. | RWAC and AemsRW constructors. [X360 `0x82B6DD78`, `0x82B6C728`] |
| `Dac::GetPlugInDescRunTime` `0x82B96DB8` and descriptor `off_82F8C7A8` | Dossier exists; getter is `return &off_82F8C7A8`; PC home absent. [X360 `0x82B96DB8`] | RWAC registration. |
| `GainFader::GetPlugInDescRunTime` `0x82B97368` and descriptor `off_82F8CC50` | Dossier exists; getter is `return &off_82F8CC50`; PC home absent. [X360 `0x82B97368`] | RWAC registration. |
| `LowPassButterworth::GetPlugInDescRunTime` `0x82B97BF0` and descriptor `off_82F8D24C` | Dossier exists; getter is `return &off_82F8D24C`; PC home absent. [X360 `0x82B97BF0`] | RWAC registration. |
| `SndPlayer1::GetPlugInDescRunTime` `0x82B9BE60` and descriptor `off_82F901C4` | Dossier exists; getter returns the descriptor address; PC home absent. [X360 `0x82B9BE60`] | RWAC and AemsRW registration. |
| `SubMix::GetPlugInDescRunTime` `0x82B9C370` and descriptor `off_82F902E0` | Dossier exists; getter returns the descriptor address; PC home absent. [X360 `0x82B9C370`] | RWAC registration. |
| custom descriptor `off_82F2D094` (`"GinsuPlayer"`) | Passed directly; no PC descriptor home. [X360 `0x826C17A0`] | RWAC registration. |
| custom descriptor `off_82F2E124` (`"SndPlayer1_CgsStreamMod"`) | Passed directly; no PC descriptor home. [X360 `0x826C17A0`] | RWAC registration. |
| custom descriptor `off_82F2E664` (`"GainArray"`) | Passed directly; no PC descriptor home. [X360 `0x826C17A0`] | RWAC registration. |

The call at `0x82B0F1B8` is also not homed under a meaningful PC sound symbol, but its exact dossier is a no-op leaf (`li r3,0; blr`). A semantic implementation does not need to invent or link a callback registrar for it. [X360 `0x82B0F1B8`; caller X360 `0x826DAAD0`]

## Static names and integration globals

| Writer / X360 global | Required PC datum |
|---|---|
| `sub_82C654A8` `0x82C654A8` → `dword_83008650` | Hash/interned `Name` for `"~GenericRwacFactory::SK_NAME~"`; replace the current zero/default placeholder. [X360 `0x82C654A8`] |
| `sub_82C65788` `0x82C65788` → `dword_83008664` | Hash/interned `Name` for `"~AemsFactory::SK_NAME~"`. [X360 `0x82C65788`] |
| `sub_82C65938` `0x82C65938` → `dword_83008404` | Hash/interned `Name` for `"~SplicerFactory::SK_NAME~"`. [X360 `0x82C65938`] |
| `off_82FFBA0C` | Stage-3 publish target for `Module+0x228`. [X360 `0x826E90C0`] |

`off_83271928`, `off_82F87DBC`, and `off_82FFB9F0` already have PC homes and are not worklist items; the new constructors must consume/publish those existing symbols. [X360 uses `0x826C7AD0`/`0x826C17A0`/`0x826C26B8`/`0x826C30C8`; writes `0x82B6FCD0`, `0x826C30C8`]

Two un-homed rodata operands must also be resolved when the voice helpers land: `flt_82001C98`, whose address is loaded into mono stage 0, and `flt_82001D9C`, whose address is loaded into stereo stage 0. The helper dossiers prove the addresses and the pointer plumbing but do not encode the four data bytes, so their numeric values must come from an image/data read rather than an inference from these instructions. [X360 `0x826A32E0`, `0x826A33C0`]

## Vtable/class-surface closure implied by constructor stores

These console addresses are ABI evidence, not literal data symbols that a native PC build should define. The PC closure is to correct the class hierarchies and provide the virtual bodies so the compiler emits equivalent host vtables.

| Console vtable address(es) stored | Class surface requiring a faithful PC home |
|---:|---|
| `off_820B2E04` | `GenericRwacFactory`; its ctor is absent, as are identified virtual bodies `~GenericRwacFactory` `0x826C19F8`, `DoUpdate` `0x826D89D0`, and `DoCreateContent` `0x826E9990`. The vtable store itself is at X360 `0x826C17A0`. |
| `off_820AB168`, `off_820B2F84`, `off_820B2F70` | `AemsRWSampleFactory` with IAems primary interface and `Factory` secondary base. `CreateInstance` `0x826C28A0` is absent; the existing destructor home is ABI-divergent until the base layout is corrected. Vptr stores are at X360 `0x826C26B8`. |
| `off_820B2ED0`, `off_820B2EBC` | `AemsFactory`; identified absent virtual bodies include `DoUpdate` `0x826C2358`, `DoCreateVoice` `0x826E9AC8`, and `DoCreateContent` `0x826E9B98`. Vptr stores are at X360 `0x826DAAD0`. |
| `off_820B3050` | `SplicerFactory`; identified absent virtual bodies include `DoUpdate` `0x8268AB60`, `DoCreateContent` `0x826E9C88`, and `DoCreateVoice` `0x826FA578`. Its destructor `0x826C3040` is already homed. The vptr store is at X360 `0x826DB010`. |

No target address is assigned here to the declared `AemsRWSampleFactory::Release` slot because the current X360 identity/export does not provide a distinct per-function dossier for it. That unresolved address must not be fabricated.
