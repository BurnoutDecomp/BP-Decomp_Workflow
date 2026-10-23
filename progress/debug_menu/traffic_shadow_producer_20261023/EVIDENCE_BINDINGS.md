# Evidence bindings

The six ARTIST exports below are the pinned X360 behavior evidence. `xrefs_to` in `0x823F7638.json` records the two AddShadow callers; `0x82728B08.json` records the sole direct Traffic RenderTrafficCar owner; `0x8273B280.json` records the two direct world dispatch owners.

| File | SHA-256 | Use |
|---|---|---|
| `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x823F7638.json` | `90FEFDE1D97EE81790E212B108AB74AD629A932A74D036728959EB22435F95EA` | AddShadow body, xrefs, direct call owners |
| `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x822E79F8.json` | `D3E8388CAD5390D267D4E5A79AECEE9AB9F9F43ACD1E4CE2D7FFF00996B02E72` | RaceCar call and gates |
| `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82728B08.json` | `4C16F1CBCF2A36A4459C7432C2622055DFF6CC7C922C4BCAF03DEF0478E5BF61` | Traffic call and gates |
| `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8273B280.json` | `6758758C94FB3C12FC6F05B3D11DBCEDCEEFEDBF039784C96B355C3130EF7635` | Traffic call owner, caller xrefs |
| `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x827C96D8.json` | `737A1C8311DAF4046592B2907F64F22C14D67873391DEF13A502EC26A65F78D2` | Shadow-map caller of RaceCar and Traffic |
| `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x827D1CE8.json` | `6A45F2989AA2BE22043C1D265802DD175C9A4A29D599AF6833465A19BA30532D` | Main-view caller of RaceCar and Traffic |
| `scratch/DEBUG_MENU_1011/traffic_blobby_matrix_decode_root_20261023/DECODE.md` | `3FD7DE3ECDCE5E81AABE7FFB05DD7C1267A19D01C20ADD44CF437CC5C3DCEE0F` | Root's raw-operand decode for physical matrix rows/translation |

| File | SHA-256 | Use |
|---|---|---|
| `references/DecFIGS/dwarfdump/_compile/BrnTrafficUnity.cpp` | `E37516C1F25981E8FF4E6A57E5CE30FA14960CF498D5B77CC8276DBD5281111C` | Traffic local variable names at original lines 14964, 14982, 14984, 14985 |
| `references/DecFIGS/dwarfdump/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficEntityModule.h` | `6D7878339CA51A42665DDFB0629CD0DA19110A309405A233EAFC520980EE35DE` | Nonvirtual traffic declarations |
| `references/DecFIGS/dwarfdump/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficVehicleTypeRuntime.h` | `ABEDB8348E8FFDA30AD9DE3C7C0204116EE684B8D259AD594B535FA82312A41E` | Typed box offset, half-size, and axle-vector fields |
| `references/DecFIGS/dwarfdump/GameSource/Graphics/BrnBlobbyShadowManager.cpp` | `71E04E1DA91CC1896AFCFB3433E476CC37EDDB9C79D1B3B00A17D8382E0EDF84` | AddShadow argument names and declaration shape |
| `references/DecFIGS/dwarfdump/GameSource/Graphics/BrnBlobbyShadowManager.h` | `6D07EC0AF9EC9FF91A3D57A9413DFC7B550F9F5F67215C626B0A4C5A91F5065B` | AddShadow is declared as a nonvirtual public method |

| File | SHA-256 | Use |
|---|---|---|
| `scratch/DEBUG_MENU_1011/traffic_blobby_matrix_decode_root_20261023/ARTIST_excerpt.txt` | `A3E1BCD5C51BB3203FD9F96A5B3F1D8835404F05E3BB8D00EC3DCCDDF93F66EE` | Address-pinned matrix call excerpts |
| `scratch/DEBUG_MENU_1011/traffic_blobby_matrix_decode_root_20261023/RAW.json` | `297CC21132CC16C9A5EF18B43E42716A6C12E8027FF27F5DFC38C5D33CF04F6B` | Raw PPC operand decode for the physical matrix |
| `b5-decomp/src/SDKs/EATech/include/rw/math/vpu/detail/vector3_operation_inline.h` | `11120A9728561409DCF0C012AB05BC1ACF57D0AF31A3F4C610FDCDA254592955` | Cross is the standard xyz cross product |
| `b5-decomp/src/SDKs/EATech/include/rw/math/vpu/matrix44.h` | `0F73001A5157D0AE627F251EED51554F57D199997555EFD41872D47F13CDF15C` | Matrix44Affine stores x/y/z/w rows |
| `b5-decomp/src/SDKs/EATech/include/rw/math/vpu/detail/vector4_type_inline.h` | `D138F1C9D9211520F73BCF04FF7F99C0B8A666CFD1B895C848F7344856176486` | Vector4(Vector3,w) preserves the explicit W lane |
| `b5-decomp/src/BrnCommonTypes.h` | `C8B01FE4A87A1B4A95B8600FB76907D85149E369AD0EA7C5AEB824ECF64750C2` | Vector3Plus is xyz plus a packed scalar W |

The code under review is the 9cbefd integration snapshot (`9cbefd173085312ebaee5bab4875b8492fc292cb`), whose Traffic render, traffic IO bridge, game-to-world bridge, and world-to-entity bridge files are unchanged from `b3300e0e8e61dd7dea105a901a4fdb94464f3864`. The same Traffic render source appears in the current b3300e0e8e61dd7dea105a901a4fdb94464f3864 checkout and in 9cbefd. Its SHA-256 is `AE18398E0A6856F552056D961B471B3BCB81E107A2F0E6EBA48BF88860F62EFE`.

The exact source preimage is copied to `source/pre/BrnTrafficEntityModule_Render.cpp` with that same SHA-256. The proposal postimage `source/post/BrnTrafficEntityModule_Render.cpp` has SHA-256 `22D0B153B45F54362F9D213BBC4C63DA4CA7D155DF9E9DFDBF51C6F8739C8790`; the exact unified diff is `source/traffic_addshadow.patch` (SHA-256 `B666A1362957DC2AB4489BB4D72F311F7F71F9DAB163C70280F523C710B4456A`).

The current typed `TrafficPhysicsInfo` owner is `b5-decomp/src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficEntityModule.h` (SHA-256 `9B4EB205368D5C389EF8DD598E37093BA1B33F2FD3021B6B87DE08581A1EEA94`); its `mvRoadTestNormal_HeightAboveRoad` field follows the `32 + 20*64` record span at `+0x520`. The current typed `VehicleTypeRuntime` owner is `b5-decomp/src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficVehicleTypeRuntime.h` (SHA-256 `3C52B0496E1A3B4F31F0714D325B8D07C516AFC464E405A706B351AFD9ACC74B`). The source-side external buffer setters/getters are present in `GameBridgeRendererToX.cpp`, `WorldBridgeToEntityModules.cpp`, and `TrafficEntityModuleIO_InputBuffer_Dispatch.cpp`; the old “no owner / no setter” comments in `TrafficEntityModule_Render.cpp` are stale relative to this wiring.
