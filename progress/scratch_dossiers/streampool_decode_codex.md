# `rw::audio::core::StreamPool` — decode, and why `SndPlayer1`'s stream path is DEAD CODE in retail

2026-08-29. Two sources, kept separate on purpose:

* **codex (gpt-5.5, xhigh)** completed this decode but its sandbox was mounted read-only, so it
  could not write its report. Its headline findings survive in the job log and are marked
  **[codex]** below.
* **Everything marked [verified here]** was re-derived independently from the raw XEX in the
  main session, instruction by instruction, precisely because the load-bearing conclusion
  (below) is strong enough that it should not rest on a single unreviewed source.

Method for everything below: `file_off = 0x3000 + vaddr - 0x82000000`, big-endian PPC, from
`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`.

---

## THE HEADLINE

> **`StreamPool::GetInstance` returns null for every guid, always, in the ARTIST build — and
> `AcquireStream` dereferences its `this` with no null guard. Therefore
> `SndPlayer1::PlayHandler`'s stream-open path would FAULT ON THE REAL CONSOLE if it were ever
> reached. It is compiled-in dead code: retail only ever hands 'SnP1' resident requests.**

That single fact retires the blocker this whole phase was stuck behind. The streaming half of
`SndPlayer1` does **not** need a working stream pool, because on the console it never gets one.
It needs a *faithful* one: an empty registry whose lookup fails, exactly as shipped.

### The evidence chain

**1. `GetInstance` @0x82B6BA68 walks an intrusive list off one global.** [verified here]

```
82B6BA68: 3D608327   addis r11, r0, 0x8327
82B6BA6C: 816B1C7C   lwz   r11, 0x1C7C(r11)   ; r11 = *(0x83271C7C)  -- the list head
82B6BA70: 48000024   b     check
loop:
82B6BA74: 2B0B0000   cmplwi cr6, r11, 0
82B6BA78: 394BFFD4   addi  r10, r11, -0x2C    ; node -> owner  (link sits 0x2C into StreamPool)
82B6BA7C: 409A0008   bne   cr6, +8
82B6BA80: 39400000   li    r10, 0
82B6BA84: 812A0024   lwz   r9, 0x24(r10)      ; pool->muGuid
82B6BA88: 7F091840   cmplw cr6, r9, r3        ; == the requested guid?
82B6BA8C: 419A0018   beq   cr6, found
82B6BA90: 816B0000   lwz   r11, 0(r11)        ; node = node->next
check:
82B6BA94: 280B0000   cmplwi cr0, r11, 0
82B6BA98: 4082FFDC   bne   cr0, loop
82B6BA9C: 38600000   li    r3, 0              ; NOT FOUND -> null
82B6BAA0: 4E800020   blr
found:
82B6BAA4: 7D435378   mr    r3, r10
82B6BAA8: 4E800020   blr
```

**2. Nothing in the entire image ever writes that list head.** [verified here — three ways]

* A full scan of every instruction word with displacement `0x1C7C` finds **five** hits. Only
  one is real: `0x82B6BA6C`, the `lwz` above. Of the rest, `0x82665B08` pairs with
  `addis r11, r0, 0x820A` and so addresses `0x820A1C7C` (rodata), `0x82B1A9A4` adds to a
  running pointer in r29, and two more (`0x827E1B50`, `0x82F3209C`) are data words that merely
  decode like instructions. **There is no `stw` to it anywhere.**
* The literal `0x83271C7C` appears **zero** times as a data word in the image, so no pointer
  table hands its address to a generic list helper.
* `0x83271C7C` maps to file offset `0x1274C7C`, past the end of the 0x105B000-byte image — it
  is **`.bss`**, zero-filled at load. So its value at every lookup is 0, and the walk exits
  immediately down the `li r3, 0` path.

**3. [codex]** ARTIST contains no `StreamPool` constructor, no `CreateInstance`, no registry
writer and no boot-time pool creation. Independently consistent with (2).

**4. `AcquireStream` @0x82B6BAB0 dereferences `this` immediately.** [verified here]

```
82B6BAC0: 7C7E1B78   mr   r30, r3          ; r30 = this (the pool)
82B6BAC4: FFE00890   fmr  f31, f1          ; the priority
82B6BAC8/CC:          mr   r28, r5 / r29, r6 ; lost-callback, context
82B6BAD0: 39400000   li   r10, 0
82B6BAD4: 897E0028   lbz  r11, 0x28(r30)   ; *** UNGUARDED LOAD FROM `this` ***
```

**5. `PlayHandler` passes the pool straight through, checking only the RESULT.** [verified here]

```
82BA42E4: 897F0049   lbz  r11, 0x49(r31)   ; RequestExternal::playType
82BA42E8: 2B0B0001   cmplwi cr6, r11, 1
82BA42EC: 419A000C   beq  cr6, streamopen  ;   1 = streamed  -> open
82BA42F0: 2B0B0002   cmplwi cr6, r11, 2
82BA42F4: 409A01AC   bne  cr6, commit      ;   2 = hybrid    -> open;  0 = resident -> skip
streamopen:
82BA42F8: 807D0020   lwz  r3, 0x20(r29)    ; cmd->muStreamPoolGuid
82BA42FC: 4BFC776D   bl   GetInstance      ; -> r3 = NULL, always
82BA4304: 907F0020   stw  r3, 0x20(r31)    ; ext->mpStreamPool = NULL, stored anyway
82BA430C: 38AB4100   addi r5, r11, 0x4100  ; &SndPlayer1::StreamLostCallback
82BA4310: 817E0008   lwz  r11, 8(r30)      ; self->mpVoice
82BA4314: C02B0038   lfs  f1, 0x38(r11)    ; voice->mfPriority
82BA4318: 4BFC7799   bl   AcquireStream    ; r3 STILL the null pool -> faults at +0x28
82BA431C: 28030000   cmplwi cr0, r3, 0     ; only the RESULT is ever tested
```

So the guard is `playType`: **0 = resident skips the pool entirely; 1 (streamed) and 2 (hybrid)
both walk into it.** Retail works, therefore retail never gives a 'SnP1' voice a playType of 1
or 2. That is consistent with the architecture: splice voices play resident sample data, and
real streaming goes through the game's own fork `SndPlayer1_CgsStreamMod` ('JStr'), which uses
the module's `IStreamProvider` (published at `off_82FFBA0C`), not this pool.

---

## The type, as far as it is attested

⚠️ Only what the four reachable functions actually touch. Everything else is unknown and is
listed as such — see DO NOT INVENT.

### `StreamPool`

| console off | member | evidence |
|---|---|---|
| +0x24 | `muGuid` | `lwz r9, 0x24(r10)` @0x82B6BA84, compared against GetInstance's argument |
| +0x28 | `mu8EntryCount` | `lbz r11, 0x28(r30)` @0x82B6BAD4; the loop bound at `cmpw r10, r11` |
| +0x2C | `mListLink` | `addi r10, r11, -0x2C` @0x82B6BA78 — the intrusive link's offset **[codex + verified here]** |
| +0x04 | `mpEntries` | `lwz r3, 4(r30)` @0x82B6BAE0 / @0x82B6BB20, then walked at stride 0x20 |

⚠️ **`0x2C` and the `0x20` entry stride are both console constants that DO NOT SURVIVE x64.**
The link offset moves as soon as any member before it widens, and the entry record holds a
pointer and a function pointer. Host code must use a typed array and `offsetof`, never these
literals. This is the sixth appearance of this hazard class in this wave.

### The entry record (console stride 0x20)

| console off | member | evidence |
|---|---|---|
| +0x08 | `mfPriority` | seeded by AcquireStream @0x82B6BB8C; `RwacTimerClient` republishes it |
| +0x0C | `mpfnStreamLost` | `stw r28, 0xC(r3)` @0x82B6BB90 |
| +0x14 | `mpStream` | `lwz r11, 0x14(r3)` @0x82BA4328 -> `rw::core::filesys::Stream*` |
| +0x18 | `miRefCount` | **[codex] a SIGNED `short`**, correcting the earlier "u16" baseline |
| +0x1A | `mbAllocated` | **[codex]** vendor-named `allocated` (earlier baseline called it `inUse`) |

### Functions

| addr | function | note |
|---|---|---|
| 0x82B6BA68 | `GetInstance(u32 guid)` | fully decoded above; always returns null in ARTIST |
| 0x82B6BAB0 | `AcquireStream(pool, f32 priority /*f1*/, StreamLostFn, void* ctx)` | two-pass entry scan; unguarded `this` |
| 0x82B6BC48 | `ReleaseStream(...)` | **[codex]** address found here; not re-derived in this session |

### Callers — exactly three **[codex]**

`0x82BA42FC` (PlayHandler's GetInstance), `0x82BA4318` (PlayHandler's AcquireStream) and
`0x82BA0524` (RemoveRequest's ReleaseStream). All three are inside `SndPlayer1`. Nothing else
in the image uses a stream pool at all — which is itself corroboration that this is a
single-consumer, retail-dormant surface.

---

## What this means for the host

1. **Home `StreamPool` faithfully, not as a stub.** The registry list is genuinely empty on the
   console; reproducing an empty list is *exact*, not an approximation. `GetInstance` returns
   null because it walked an empty list — the same reason the console does.
2. **Reproduce `PlayHandler`'s unguarded call.** Do **not** add a null-pool check that the
   console does not have. If a PC build ever fed a 'SnP1' voice a playType of 1 or 2 it would
   fault — exactly as the console would. Adding a guard would hide a real content divergence
   behind silently different behaviour, which is the opposite of what this project wants. The
   hazard belongs in a comment at the site, and it is now in this dossier.
3. **Registration 21 is therefore safe** once the four deferred bodies land, because the path
   that needs a pool is unreachable for the same reason it is unreachable on console.

---

## DO NOT INVENT

Unattested, and to be left alone until a call site forces the issue:

* The rest of `StreamPool` (+0x00, +0x08..+0x23) — never touched by the four reachable functions.
* Entry fields +0x00..+0x07, +0x10, +0x1B..+0x1F.
* `ReleaseStream`'s body — its address is [codex]'s and was **not** re-derived here. Decode it
  before writing it.
* How a pool would have been created in a build that had one. The creation path does not exist
  in this image; do not reconstruct one from the vendor PDB and present it as ARTIST behaviour.
  ([codex] explicitly flagged that it declined to do this, which was the right call.)
