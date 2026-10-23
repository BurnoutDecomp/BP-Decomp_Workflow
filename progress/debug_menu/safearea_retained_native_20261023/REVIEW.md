# Independent packed-colour and retained safe-area review

Source contract VERDICT: pass

Retained `BrnGui::GuiDebugComponent::OnActivate#0018`: pass.
Retained `BrnGui::GuiDebugComponent::OnActivate#0019`: pass.

These are proposed dispositions for exactly these two sites. They do not update an inventory or authorize publication. The original aggregate 62049 verdict remains **FAIL**.

## Packed-colour contract

The direct frame evidence supports the colour audit independently of its author's conclusion. No channel correction or safe-area literal change is supported.

ARTIST `GuiDebugComponent::RenderHUD` constructs `r5 = 0xFF00FF00` at `824FD0F0..824FD0FC` and `r5 = 0xFF0000FF` at `824FD180/824FD204`, then calls `DrawDebugFrame1280`. That helper copies `r5` to `r8` at `824F7D10` and calls scalar `DrawFrame` at `824F7F08`. SatNav's original `RenderHUD` independently loads `r8 = 0xFFFF0000` at `824F7FD8` and calls the same scalar helper at `824F8048`.

`DrawFrame` retains the packed colour with `mr r29,r8` at `8281C990` and supplies `r4 = r29` to each of its four `DrawBox` calls. `DrawBox` saves incoming `r4` in `r30` at `8281C2D4`, restores `r4` at `8281C370`, and calls `AddQuad` at `8281C3B0`. This is a word-preserving ABI chain; the float arguments do not overwrite the colour argument.

In the bounded original `AddQuad` body, incoming `r4` becomes `r30` at `8281BFA8`. Re-deriving the raw rotate/insert fields with PPC bit 0 as the MSB gives masks `MASK(16,23) = 0x0000FF00` and `MASK(0,23) = 0xFFFFFF00`. For an arbitrary input `AABBCCDD`, the sequence forms `r8 = DDCC`, then `r11 = 00DDCCBB`, shifts that left eight bits and ORs in `AA`, producing **DDCCBBAA**. This derivation was also evaluated on all 32 independent input bit positions, not merely the symmetric red word. The four colour stores at `8281C058`, `8281C0CC`, `8281C138`, and `8281C1A4` therefore store `bswap32(input)`.

The vertex address arithmetic is `this + 20*head + 0x44` for colour; `DispatchVertices` identifies the array start as `this + 0x3C`. Thus the colour is at vertex offset 8 with stride 20. The original constructor at `827F8BA8` writes element offset 8, format word `0x14C86`, usage 10 and usage index 0. The sealed DecFIGS vertex declaration places `RGBA8 mv4Colour` between the two-float position and UV members; its `renderengine::RGBA8` declaration names red/green/blue shifts 24/16/8 in the big-endian packed representation. The partial DecFIGS AddQuad outline confirms the RGBA-to-RGBA8 construction role but does not supply its argument values.

The pinned PC source explicitly declares four bytes `r,g,b,a`, stores the original `u32` directly at `mv4Colour`, and maps `0x014C86` to `D3DDECLTYPE_UBYTE4N`. Its descriptor builder propagates offset 8 and COLOR0 usage into the native declaration. This consumes normalized components in memory order. Combining this declaration/type evidence with the original stores establishes the named channels:

| Input word | Original word before big-endian store | Original and PC memory bytes, RGBA | Result |
|---|---|---|---|
| `FF0000FF` | `FF0000FF` | `FF 00 00 FF` | opaque red |
| `FF00FF00` | `00FF00FF` | `00 FF 00 FF` | opaque green |
| `FFFF0000` | `0000FFFF` | `00 00 FF FF` | opaque blue |

The original byte reversal compensates for its big-endian store; the PC little-endian raw store yields the same four bytes. Interpreting the input integer as ARGB would reverse the red/blue conclusion incorrectly.

The full 320,888,599-byte original image matches its pinned SHA-256. Independently reading its ID1 byte flags reproduces the sealed 620-byte AddQuad window and all 155 printed instruction words through its `blr`. The two calibration prefixes reproduce their 12 and 15 pinned raw words; the known exports corroborate their addresses, prologues, register copies, loads and branch targets. The working reader and decoder differ from their committed snapshots, as the packet discloses; both versions are sealed, and the colour-critical rotate fields were decoded independently from the raw words here. No IDA session or program under review was executed.

The ordinary text path is corroboration only. The actual export copies `r6` to `r27` at **82823E00**, constructs its local TextObject at `sp+0x70`, and stores the word at `sp+0x84`, object offset `+0x14`. It supplies that object in `r5` to `RenderString`; the wrapper moves `r5` to `r4`, which `RenderStringInternal` retains in `r27`. Its ordinary branch loads `0x14(r27)`, explicitly reverses the bytes, and stores the six glyph colours at offsets 8/1C/30/44/58/6C. The packet's text-chain note incorrectly locates the `r6 -> r27` instruction at 82823DFC; that address actually copies `r4` to `r28`. This is a nonblocking citation typo, not a channel discrepancy. Alternate text-colour paths were not reviewed as a separate contract.

## Retained native evidence

I directly viewed all five actual pinned BMPs with the image viewer. All are 1280 by 720, 32-bit top-down BMPs; their hashes and stored mtimes match. Independent read-only BMP byte measurements corroborate the visual observations below. Coordinates are inclusive pixel bounds. Some 85% border pixels are covered by other debug text/bars; the matching bounds and visible edges remain clear.

| Phase | Frame | Independent observation | Candidate age before note |
|---|---|---|---:|
| `g017_restored` | `bb_008160.bmp` | No safe-area rectangle; zero pure-red pixels | 1.281904 s |
| `g018_visible` | `bb_008520.bmp` | Red rectangle, `(96,54)..(1183,665)`, 1088 by 612 | 1.397707 s |
| `g019_70` | `bb_008880.bmp` | Red rectangle contracts to `(192,108)..(1087,611)`, 896 by 504 | 0.297078 s |
| `g019_85` | `bb_009120.bmp` | Red rectangle returns to `(96,54)..(1183,665)` | 0.875476 s |
| `g018_restored` | `bb_009480.bmp` | Safe-area rectangle absent again; zero pure-red pixels | 1.167205 s |

The dimensions equal 85% and 70% of the 1280 by 720 frame. The pinned source's centred safe-area formula and its one-pixel DrawDebugFrame/DrawFrame boundary convention explain these pixel bounds. The neighbouring off images and the repeated 85% image distinguish this overlay from red scene content. Ordinary gameplay HUD remains absent in these five images; no whole-HUD restoration is inferred.

The original OnActivate export at `8252A58C..8252A5A4` binds “Show/Hide Safe Area” to `ToggleShowSafeAreaCallback`, passing the same component as user data. At `8252A5A8..8252A5D8` it registers the float at component `+0x24` and applies its original 70..100 range. Exact 91a source snapshot lines 483..485 mirror those registrations. Lines 715..727 forward the callback's user data to the component toggle, lines 613..615 invert `mbShowSafeArea`, and lines 864..875 consume that flag and `mfSafePercent` to draw `FF0000FF`. The callback's full original body is not separately supplied in this packet; the reviewed original registration, pinned source chain and actual native off/on/off effect establish the binding in this bounded review.

The archived activation script binds F5 to `call "Gui/Gui Module/Show/Hide Safe Area"`. The helper records key 116 at steps 40 and 51. F2's operation chain advances through scripts 008, 009, 010 and 011: 008/011 only advance the next binding, 009 sets Safe Area to 70, and 010 restores 85. All 26 archived scripts and the helper-step script match their manifest hashes. The visible contrast follows the held states in that order.

I checked the exact raw-log definition/value/closing-definition triples, including the spaces in the control path:

| Alias | Raw log lines | Value |
|---|---|---|
| `b003` | 17078..17080 | `85.000` |
| `r006` | 29930..29932 | `70.000` |
| `r007` | 31107..31109 | `85.000` |
| `f003` | 49109..49111 | `85.000` |

The helper's five note times and pinned file mtimes independently reproduce the listed ages. These values and images are **phase-adjacent, not proven same-frame**. Site #0018 is callback-only: its off/on/off evidence is visual, not a fabricated boolean readback. Site #0019 combines the actual 85/70/85 readbacks with the corresponding visible geometry and final 85 readback. Local restoration is supported only for these safe-area states.

## Preserved limits and provenance

The original aggregate 62049 **FAIL** is unchanged: raw lines 17087..17089 show `b006` as `TRUE` against expected `FALSE`. All 40 archived readback triples match their recorded actual values; 39 match the original expectations and this one does not. Its reporting errors remain: an empty `--run-error` argument was dropped by PowerShell, and the archive code called undefined `terminal(args)`. Those reporting paths receive no evidence-completion credit.

The retained run is source `91a0ed564f9c9e3dec915bfb416c0467650084ef`, executable SHA-256 `6fa903ebd3200ec46104b47bda8eb0e81d835d0ce6e003da370c11deb14c203a`. All 15 original native source snapshots match both their SHA-256 and Git blob IDs. The colour packet's comparison source is separately bound to b9e6a93; its GuiDebug source is byte-identical to the retained 91a GuiDebug snapshot. The colour packet's SatNav source already uses `FFFF0000`, whereas retained 91a SatNav uses `FFFFFFFF`. The static original blue contract therefore grants **no new SatNav outline colour/parity credit** to that older run.

The sealed historical restoration receipt records 24 normal protected paths, four private paths and 12 payloads verified for the original run. I reviewed that receipt and its integrity, without requiring today's user files to equal a historical snapshot. It is not a new protection/restoration run.

No new credit is given to SatNav alpha, isolated override-mode behaviour, peer races, speed/counter accuracy, any other menu site, or the missing ordinary HUD. No new game, harness, C++, fixture, CI or IDA execution occurred. No source, index, Git state, inventory, roster or original evidence was changed. Only this new sibling review was written. Root retains publication ownership.

`REVIEWED_EVIDENCE.json` contains the verified input hashes, raw-word derivation, exact readbacks, image measurements and preserved provenance. `SOURCE_CONTRACT.json` and `SITE_DISPOSITIONS.json` hold the separate machine-readable conclusions. `INTEGRITY.sha256` seals this review; `INTEGRITY.sha256.sha256` seals that manifest.
