# RaceCar WorldMap2D provider

One source path extends private B5 `65f58d20c63dda8f351f672b5b9fc0d30f8a7af1`: `src/GameSource/World/EntityModules/RaceCarEntityModule/SharedIO/BrnRCEntityActiveRaceCarOutputInterface.cpp`. It adds the missing body of the already-declared `SetWorldMap2D`, assigning the complete named map member. The provider TU is already mounted; no workflow mount or header changes are required.

The original native build's RaceCar module object requests `?SetWorldMap2D@RCEntityActiveRaceCarOutputInterface@RaceCarEntityModuleIO@BrnWorld@@QEAAXPEBUWorldMap2D@CgsWorld@@@Z`. Its old provider object defines no such symbol. The new actual provider TU defines exactly that name. This is a missing body, rather than a class/struct tag mismatch: the canonical `CgsWorldMap2D.h` defines `struct WorldMap2D`.

ARTIST `UpdateOutputInterfaces` at `0x822F5D30..0x822F5D88` copies the module's WorldMap2D at `+0x18300` into both active output interfaces at `+0x28B0`, using six eight-byte loads/stores for each 48-byte record. The setter was inlined there; no separate ARTIST setter identity is claimed. The copied original JSON, including assembly, is in `evidence/ARTIST_0x822F5CF8.json`. Named member assignment preserves native map geometry, dimensions and the native grid pointer without introducing pointer offsets or extra behavior.

The actual full provider TU compiles against 74 opened headers. The original WorldMap2D TU and a direct real-header caller also compile. Each opened project header is checked against its exact 65f Git blob. The old native caller and provider object hashes and their setter symbol lines are retained in `CONTROL_RECEIPT.json`.

The passing link control is the actual native 3018-object link. `finalize_controls.py` copies the original response file, substitutes only this provider object, and directs all outputs to this private packet. The original seven unresolved symbols become six: exactly SetWorldMap2D disappears, and the unchanged Director/Traffic gaps remain. The complete logs and response files are retained. This directly exercises the original compiled RaceCar caller and the new actual full-TU provider, with the canonical library tail.

A preliminary standalone witness was stopped at unrelated existing assert/resource/log references and the default interface constructor's RaceCarState::Clear dependency. Its diagnostics and experimental leaf-packaging script remain visible, but supply no passing evidence and no behavior claim. No replacement engine bodies were introduced.

The full game still has six unrelated unresolved symbols at this checkpoint; resolving and integrating those belongs to the coordinator. There is no native gameplay or replay verification claim. Old sealed packets and the hardlinked native source root were read only.
