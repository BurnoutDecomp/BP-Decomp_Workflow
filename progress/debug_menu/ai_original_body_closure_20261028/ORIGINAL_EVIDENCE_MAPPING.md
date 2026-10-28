# Original ARTIST and DecFIGS mapping

## AICar speed-match readout

ARTIST RaceBalancingDebugComponent::RenderHUD is export 0x82796C08. Its pseudocode checks the car state at AICar+0x14C8, selects the guest driver pointer from AICar+0x14B0 only for IN_RANGE, then checks driver+0x1D66 before loading driver+0x1D18 for the text output. The exact instructions are retained in evidence/artist/0x82796C08.json.

ARTIST AIDriver::Construct at 0x82792B70 initializes the driver words at +0x1D18 and +0x1D66. AIDriver::CheckForSpeedMatch at 0x82793020 stores the selected forced speed at +0x1D18 and sets the bool byte at +0x1D66 to its result. These two exports are retained with full assembly and pseudocode.

DecFIGS BrnAICar.h identifies the guest AICar driver member mpDriver (line 670). DecFIGS BrnAIDriver.h declares UseForcedSpeed / GetForcedSpeed and names the backing fields mbUseForcedSpeed (line 612) and mfForcedSpeed (line 579). The corresponding B5 source AIDriver layout comments and static assertions pin +0x1D66 and +0x1D18. The new AICar wrappers use those typed getters and the existing host-pointer bridge. The HUD callsite already gates both on IN_RANGE; the bool accessor also preserves the original null-driver false path.

## Difficulty value

ARTIST AIModule::OnModeStart at 0x82791DB8 loads GameModeParams::mfProgressionRankAsRatio from +4 and stores it at AIModule+0x4EB64. The assembly sequence is 0x82791E28–0x82791E40. ARTIST RaceBalancingDebugComponent::RenderHUD at 0x82796C08 loads a float from AIModule+0x4EB64 before multiplying it by 100. Both exports are retained.

DecFIGS BrnAIModule.h line 119 names the member mfProgressionRankAsRatio with type float32_t. The source header’s old hex comment said 0x4EBA4 while its decimal offset 322404 equals 0x4EB64; ARTIST confirms the corrected hexadecimal value. GetDifficulty returns that member directly.

## Graph background

ARTIST DrawGraphFrame at 0x827747F8 computes the endpoint (origin.x+width, origin.y-height) and calls sub_8281C3E0 with start and endpoint. The helper at 0x8281C3E0 subtracts start from endpoint, builds position/size vectors with zero z/w, and calls Debug2DImmediateRender::DrawBox with the r8 colour 0x40FFFFFF. Its li r9,0 instruction only clears the vector lanes. DecFIGS BrnRaceBalancingDebugComponent.h line 97 declares DrawGraphBackground with the exact pointer and four float32_t parameters; CgsDebug2DImmediateRender.h declares the scalar and Vector2/Vector2/RGBA DrawBox overloads. The unchanged c467 CgsDebug2DImmediateRender.cpp scalar wrapper subtracts the start from the computed endpoint before dispatching to the Vector2 overload, preserving the original f32 rounding and colour.
