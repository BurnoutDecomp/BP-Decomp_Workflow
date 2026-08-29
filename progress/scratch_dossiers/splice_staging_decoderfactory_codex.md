# Splice voice staging and DecoderRegistry::DecoderFactory

Corrections first: the FLAG is stale about registration readiness, and it is imprecise about the first configuration field. Rsp0, Pn21, and Sen0 are live. Only SnP1 remains unregistered. The first word of a console PlugInConfig is not intrinsically a const f32 pointer; it is the generic void * constructor-parameter/context field. In these two helpers, stage zero points it at a one-float SndPlayer1::ConstructorParams object. Part B's stated 24-byte host DecoderRequest is also stale against the current header: the second console word is now correctly typed as the real mpSeekData pointer, so the measured x64 size is 32 bytes.

Evidence policy: all X360 claims below come from assembly fields, except DecoderRegistry::DecoderFactory at 0x82B6C778 and the corroborating Decoder::Feed at 0x82B67920, for which no dossiers exist. Those functions were read from IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex at file offsets 0x00B6F778 and 0x00B6A920 and hand-disassembled from the raw big-endian PPC words. No Hex-Rays pseudocode is used as evidence.

## 1. VERDICT TABLE — Part A

Corrections and refutations are deliberately listed before confirmations.

| FLAG/banner claim | Verdict | Authoritative proof |
|---|---|---|
| The first field is “&1.0f” / “&2.0f”, implying a const f32 * field. | **CORRECTED.** The 12-byte console record is DecFIGS PlugInConfig {void *pConstructorParams, PlugInHandle plugInHandle, u8 outputChannels}; see references/DecFIGS/dwarfdump/SDKs/EATech/include/rw/audio/core/pluginregistry.h:187-195. Mono stores the float at stack +0x50, then stores its address at config[0]+0x00 (0x826A3308, 0x826A3314, 0x826A332C-0x826A3330). Stereo does the same at 0x826A33E8, 0x826A33F4, 0x826A3404-0x826A3408. The current host equivalent is VoiceStageConfig::mpContext, a void *, at b5-decomp/vendor/renderware/include/rw/audio/core/Voice.h:103-118. The pointed-to object is SndPlayer1::ConstructorParams {f32 maxRequests}, confirmed by DecFIGS sndplayer1.h:39-43 and the host header at plugins/SndPlayer1.h:77-80. |
| “SnP1/Rsp0/Pn21 handles are still null”; “light the staging when the three plug-ins register.” | **CORRECTED.** The staging needs four descriptor handles: SnP1, Rsp0, Pn21, Sen0. The retail registration sequence calls Pan2D1 as registration 14 (getter/call 0x826C18F4/0x826C1900), Resample as 18 (0x826C1934/0x826C1940), Send as 20 (0x826C1954/0x826C1960), and SndPlayer1 as 21 (0x826C1964/0x826C1970). The current host registers Pan2D1, Resample, and Send at CgsGenericRwacFactory.cpp:297,301,303, but leaves SndPlayer1 commented at line 304. Only SnP1 remains absent. |
| “SndPlayer1 has no PC home.” | **REFUTED as stated.** The host class and bodies now exist in vendor/renderware/include and src/rw/audio/core/plugins/SndPlayer1.*. What is still missing is a publishable runtime descriptor: SndPlayer1::GetPlugInDescRunTime returns 0 at SndPlayer1.cpp:448-454, and registration 21 remains omitted at CgsGenericRwacFactory.cpp:304. The X360 getter itself returns off_82F901C4 at 0x82B9BE60-0x82B9BE68. |
| “Resample::Process / Pan2D1::CreateInstance decode in flight.” | **REFUTED.** Both host descriptor records are live with non-null create/process callbacks: Resample.cpp:56-80 and plugins/Pan2D1.cpp:95-121. Their X360 getters return the descriptor records at 0x82B9A850-0x82B9A858 and 0x82B98748-0x82B98750. |
| “The two pool count words [are] zeroed, the voice staging, and the two pool Prepares.” | **CORRECTED for ordering.** Neither count is zeroed before staging. Both voice-building loops finish first (mono 0x826C3294-0x826C32AC; stereo 0x826C32C4-0x826C32DC). Mono count is then zeroed immediately before mono Prepare (0x826C32E4, call 0x826C32F0). Stereo count is zeroed only after mono Prepare and immediately before stereo Prepare (0x826C32FC, call 0x826C3304). |
| The current parked host pools remain empty with free indices -1, so allocations return null. | **CONFIRMED only as a description of the current deferred host body, not retail behavior.** SpliceManager.cpp currently assigns both free indices -1 and discards both counts. The retail constructor instead always calls Prepare at 0x826C32F0 and 0x826C3304; Prepare stores count and count-1 at 0x8268AD4C and 0x8268AD54, while AllocateVoicePluginPairToSpliceSample branches to its null return on a negative index at 0x8268AD78-0x8268ADDC. This parked state must disappear when staging lands. |
| Constructor address is 0x826C30C8. | **CONFIRMED.** The dossier assembly begins at 0x826C30C8 and returns at 0x826C3318. |
| Eight inlined SpliceContainer zero constructions precede the manager setup. | **CONFIRMED.** The zero stores cover the eight 20-byte records at manager +0x614 through +0x6B3 in the store block 0x826C310C-0x826C31FC. |
| Assert sink +0x610 is cleared, Environment & is saved at +0x6C4, and the global is published. | **CONFIRMED.** 0x826C3204 stores zero at +0x610; 0x826C3200/0x826C3208 reload and save incoming r4 at +0x6C4; 0x826C320C-0x826C3214 stores this into off_82FFB9F0. DecFIGS names the final member const Environment & mEnvironment at SpliceManager.h:127-128. |
| The constructor locks the system and gets the plug-in registry before the four lookups. | **CONFIRMED.** System::Lock is called at 0x826C3218 and System::GetPlugInRegistry at 0x826C3220; Unlock is called only after both Prepare calls at 0x826C330C. |
| Handle lookup/store order is SnP1 +0x6B4, Rsp0 +0x6B8, Sen0 +0x6C0, then Pn21 +0x6BC. | **CONFIRMED.** SnP1 0x536E5031 is formed at 0x826C3224-0x826C322C, looked up at 0x826C3230, and stored at 0x826C3244. Rsp0 0x52737030 is formed at 0x826C3238-0x826C3240, looked up at 0x826C3248, and stored at 0x826C325C. Sen0 0x53656E30 is formed at 0x826C3250-0x826C3258, looked up at 0x826C3260, and stored at 0x826C3274. Pn21 0x506E3231 is formed at 0x826C3268-0x826C3270, looked up at 0x826C3278, and stored at 0x826C3280. |
| The four exact tags are SnP1, Rsp0, Pn21, Sen0. | **CONFIRMED.** In addition to the constructor immediates above, the descriptor GUID words read directly from the XEX are: SnP1 at VA 0x82F901EC/file 0x00F931EC = bytes 53 6E 50 31; Rsp0 at 0x82F8F908/0x00F92908 = 52 73 70 30; Pn21 at 0x82F8F168/0x00F92168 = 50 6E 32 31; Sen0 at 0x82F8FF88/0x00F92F88 = 53 65 6E 30. |
| auMonoVoiceCount drives repeated CreateMonoVoice calls and each output pair advances by 8 console bytes. | **CONFIRMED.** Incoming r5 is saved at 0x826C30E0 and reloaded into r25 at 0x826C327C. The loop passes r4 = stack pair address, calls at 0x826C329C, decrements its count at 0x826C32A0, and advances the pair by 8 at 0x826C32A4. The 8 is console sizeof(VoicePluginPair), whose two fields are pointers per DecFIGS SpliceManager.h:47-54. Host code must use VoicePluginPair array indexing; the measured x64 sizeof is 16. |
| Mono uses four stages in order {&1.0f, SnP1, 1}, {0, Rsp0, 1}, {0, Pn21, 6}, {0, Sen0, 6}. | **CONFIRMED after the first-field type correction above.** Stage count r4=4 is set at 0x826A3318. Config[0] is written at 0x826A3314 and 0x826A3324-0x826A3330; config[1] at 0x826A3334-0x826A3344; config[2] at 0x826A3348-0x826A3358; config[3] at 0x826A335C-0x826A3368. The 12-byte console stride is visible in these stack offsets and independently in Voice::CreateInstance at 0x82B6EC68/0x82B6ECB8. |
| auStereoVoiceCount drives repeated CreateStereoVoice calls and each output pair advances by 8 console bytes. | **CONFIRMED.** Incoming r6 is saved at 0x826C30E4 and reloaded into r26 at 0x826C32B0. The loop calls at 0x826C32CC, decrements at 0x826C32D0, and advances by 8 at 0x826C32D4. Host code must again use typed array indexing. |
| Stereo uses three stages in order {&2.0f, SnP1, 2}, {0, Rsp0, 2}, {0, Sen0, 2}. | **CONFIRMED after the first-field type correction.** Stage count r4=3 is set at 0x826A33EC. Config[0] is written at 0x826A33F4 and 0x826A3400-0x826A3410; config[1] at 0x826A3414-0x826A3424; config[2] at 0x826A3428-0x826A3434. There is no Pn21 stage in the stereo helper. |
| The constructor then calls VoicePool::Prepare @0x8268AC40 for each pool. | **CONFIRMED.** Mono passes this, stack mono-pair base, and r25 count at 0x826C32E0-0x826C32F0. Stereo passes this+0x308, stack stereo-pair base, and r26 at 0x826C32F4-0x826C3304. Both branch targets resolve to SpliceManager::VoicePool::Prepare at 0x8268AC40. |
| Retail counts are 64 mono and 24 stereo. | **CONFIRMED and located exactly.** CgsSound::Playback::SplicerFactory::SplicerFactory hard-codes r5=0x40 at 0x826DB0B4 and r6=0x18 at 0x826DB0B0, sets r4 to the Environment at 0x826DB0B8, and calls SpliceManager::SpliceManager at 0x826DB0BC. These values do not come from SplicerFactorySpec. The host call matches at CgsSplicerFactory.cpp:166-167. |
| flt_82001C98 is 1.0f and flt_82001D9C is 2.0f. | **CONFIRMED directly from rodata.** With file_offset = 0x3000 + VA - 0x82000000, VA 0x82001C98 maps to file 0x4C98 and contains BE bytes 3F 80 00 00 = IEEE-754 1.0f. VA 0x82001D9C maps to file 0x4D9C and contains 40 00 00 00 = 2.0f. The helper loads are 0x826A3308 and 0x826A33E8. |
| Voice::CreateInstance is called with the stage array and writes the returned VoicePluginPair. | **CONFIRMED.** Mono sets r3=0 priority, r4=4 stages, r5=&config[0], r6=&outPair->mppPlugIn, r7=System at 0x826A3304-0x826A3374, then stores returned r3 to outPair->mpVoice at 0x826A337C. Stereo sets the analogous r3=0, r4=3, r5, r6, r7 at 0x826A33E0-0x826A3440 and stores r3 at 0x826A3448. No floating-point argument register is prepared for either call; f0 is used only to store the local constructor parameter. Therefore there are no Hex-Rays-style trailing float parameters. |
| A failed Voice allocation invokes the manager assertion callback. | **CONFIRMED.** Mono tests the returned pointer at 0x826A3378, loads the global manager callback at 0x826A3384-0x826A338C, and calls it with “failed to create mono voice” at 0x826A3394-0x826A33A0. Stereo does the same at 0x826A3444 and 0x826A3450-0x826A346C with “Failed to create stereo voice”. |
| Voice::CreateInstance dereferences the descriptor resolved by each handle. | **CONFIRMED, with no null guard.** Its first sizing pass loads config[i]+0x04 at 0x82B6EC98, then immediately loads the GetSize callback at descriptor+0x04 at 0x82B6ECA0 and calls it at 0x82B6ECA8. A null handle therefore faults before Voice::CreateInstance can return null. |

### What CreateMonoVoice and CreateStereoVoice actually create

The exact original signatures are member void functions with only the implicit this and one output pointer:

- void SpliceManager::CreateMonoVoice(VoicePluginPair *), confirmed by DecFIGS SpliceManager.h:191-192 and X360 use of r4 as the output pair at 0x826A3300/0x826A330C.
- void SpliceManager::CreateStereoVoice(VoicePluginPair *), confirmed by DecFIGS SpliceManager.h:194-195 and X360 use of r4 at 0x826A33DC/0x826A33E4.

The helpers allocate no separate pair or configuration storage. Both configurations and SndPlayer1::ConstructorParams are stack locals. Voice::CreateInstance performs the allocation. Its X360 sizing pass uses a 12-byte config stride (0x82B6EC68, 0x82B6ECB8), sizes the Voice header, inline PlugIn * array, inline VoiceStageData array, and each descriptor-sized plug-in instance (0x82B6EC64-0x82B6ECC0), then makes one 16-aligned System::New2<Voice> allocation at 0x82B6ECC4-0x82B6ECDC. The existing host implementation already expresses that pointer-bearing carve with offsetof/sizeof at Voice.cpp:71-89.

On success Voice::CreateInstance writes the address of the Voice's inline PlugIn * array through the supplied PlugIn *** at 0x82B6EE54-0x82B6EE64. Thus VoicePluginPair contains:

- mpVoice: the allocated Voice *, stored by the helper at 0x826A337C or 0x826A3448.
- mppPlugIn: a PlugIn ** pointing at stage zero of that Voice's inline plug-in pointer array, not a separately allocated plug-in array. This is written inside Voice::CreateInstance at 0x82B6EE64.

Channel propagation is also exact. Voice::CreateInstance starts the per-stage input-channel byte at zero (0x82B6ED5C), passes it as r7 to PlugIn::CreateInstance at 0x82B6EDF8-0x82B6EE14, then loads the current config's outputChannels byte for the next stage at 0x82B6EE4C. PlugIn::CreateInstance stores incoming r7 at PlugIn+0x20 and config+0x08 at PlugIn+0x21 (0x82B6A854-0x82B6A860). The mono chain therefore transitions 0→1, 1→1, 1→6, 6→6; stereo transitions 0→2, 2→2, 2→2.

No fcmpu instruction occurs in either helper, the manager constructor, Voice::CreateInstance, or DecoderFactory. The NaN-polarity hazard is therefore not applicable to these two requested implementations.

## 2. Faithful C++ for the staging

This uses only types that exist now: SpliceManager::VoicePluginPair, rw::audio::core::VoiceStageConfig, PlugInDescRunTime, and SndPlayer1::ConstructorParams. The implementation needs one existing-type include:

~~~cpp
#include "rw/audio/core/plugins/SndPlayer1.h"
~~~

SpliceManager.h currently declares CreateStereoVoice but omits CreateMonoVoice. Add the assembly- and DWARF-attested declaration beside it:

~~~cpp
void CreateMonoVoice( VoicePluginPair* apOutPair );
~~~

The two helper bodies are:

~~~cpp
void SpliceManager::CreateMonoVoice( VoicePluginPair* apOutPair )
{
    rw::audio::core::SndPlayer1::ConstructorParams lConstructorParams = { 1.0f };
    rw::audio::core::VoiceStageConfig laPlugInChain[4];

    laPlugInChain[0].mpContext       = &lConstructorParams;
    laPlugInChain[0].mpDesc          =
        reinterpret_cast<rw::audio::core::PlugInDescRunTime*>(
            gpSpliceManager->sndplayerHandle );
    laPlugInChain[0].mFlagAndField8  = 1u;

    laPlugInChain[1].mpContext       = 0;
    laPlugInChain[1].mpDesc          =
        reinterpret_cast<rw::audio::core::PlugInDescRunTime*>(
            gpSpliceManager->resampleHandle );
    laPlugInChain[1].mFlagAndField8  = 1u;

    laPlugInChain[2].mpContext       = 0;
    laPlugInChain[2].mpDesc          =
        reinterpret_cast<rw::audio::core::PlugInDescRunTime*>(
            gpSpliceManager->pannerHandle );
    laPlugInChain[2].mFlagAndField8  = 6u;

    laPlugInChain[3].mpContext       = 0;
    laPlugInChain[3].mpDesc          =
        reinterpret_cast<rw::audio::core::PlugInDescRunTime*>(
            gpSpliceManager->sendHandle );
    laPlugInChain[3].mFlagAndField8  = 6u;

    apOutPair->mpVoice = rw::audio::core::Voice::CreateInstance(
        0u,
        4,
        laPlugInChain,
        &apOutPair->mppPlugIn,
        CgsSound::Playback::GetDefaultRwacSystem() );

    if ( apOutPair->mpVoice == 0 )
    {
        AssertCallbackFunc lpfnAssert = gpSpliceManager->mAssertCallbackFunc;
        if ( lpfnAssert != 0 )
            lpfnAssert( "failed to create mono voice" );
    }
}

void SpliceManager::CreateStereoVoice( VoicePluginPair* apOutPair )
{
    rw::audio::core::SndPlayer1::ConstructorParams lConstructorParams = { 2.0f };
    rw::audio::core::VoiceStageConfig laPlugInChain[3];

    laPlugInChain[0].mpContext       = &lConstructorParams;
    laPlugInChain[0].mpDesc          =
        reinterpret_cast<rw::audio::core::PlugInDescRunTime*>(
            gpSpliceManager->sndplayerHandle );
    laPlugInChain[0].mFlagAndField8  = 2u;

    laPlugInChain[1].mpContext       = 0;
    laPlugInChain[1].mpDesc          =
        reinterpret_cast<rw::audio::core::PlugInDescRunTime*>(
            gpSpliceManager->resampleHandle );
    laPlugInChain[1].mFlagAndField8  = 2u;

    laPlugInChain[2].mpContext       = 0;
    laPlugInChain[2].mpDesc          =
        reinterpret_cast<rw::audio::core::PlugInDescRunTime*>(
            gpSpliceManager->sendHandle );
    laPlugInChain[2].mFlagAndField8  = 2u;

    apOutPair->mpVoice = rw::audio::core::Voice::CreateInstance(
        0u,
        3,
        laPlugInChain,
        &apOutPair->mppPlugIn,
        CgsSound::Playback::GetDefaultRwacSystem() );

    if ( apOutPair->mpVoice == 0 )
    {
        AssertCallbackFunc lpfnAssert = gpSpliceManager->mAssertCallbackFunc;
        if ( lpfnAssert != 0 )
            lpfnAssert( "Failed to create stereo voice" );
    }
}
~~~

Using gpSpliceManager for the handles and callback is intentional: both helpers ignore incoming this for those loads and read off_82FFB9F0 instead (mono 0x826A3310 and 0x826A3384; stereo 0x826A33F0 and 0x826A3450). Also intentionally absent is an assignment of apOutPair->mppPlugIn on failure; the X360 helper passes its address to Voice::CreateInstance but does not initialize it itself.

Replace the currently parked count-discard/free-index block in the locked constructor scope with the following exact staging and Prepare sequence:

~~~cpp
SpliceManager::VoicePluginPair
    laMonoVoicePluginPairs[SpliceManager::KU_MAX_POOLED_VOICES];
SpliceManager::VoicePluginPair
    laStereoVoicePluginPairs[SpliceManager::KU_MAX_POOLED_VOICES];

for ( u32 luVoicePluginPairIndex = 0;
      luVoicePluginPairIndex < auMonoVoiceCount;
      ++luVoicePluginPairIndex )
{
    CreateMonoVoice( &laMonoVoicePluginPairs[luVoicePluginPairIndex] );
}

for ( u32 luVoicePluginPairIndex = 0;
      luVoicePluginPairIndex < auStereoVoiceCount;
      ++luVoicePluginPairIndex )
{
    CreateStereoVoice( &laStereoVoicePluginPairs[luVoicePluginPairIndex] );
}

mMonoVoicePool.muPooledVoiceCount = 0u;
mMonoVoicePool.Prepare( laMonoVoicePluginPairs, auMonoVoiceCount );

mStereoVoicePool.muPooledVoiceCount = 0u;
mStereoVoicePool.Prepare( laStereoVoicePluginPairs, auStereoVoiceCount );
~~~

The fixed arrays are not a guess: DecFIGS gives VoicePluginPair[64] for both constructor locals at SpliceManager.cpp:204-219, and the X360 frame exposes two 0x200-byte console pair regions. Typed indexing is mandatory on x64: VoicePluginPair is two pointers and measures 16 bytes, while VoiceStageConfig measures 24 bytes under the x86_64 MSVC ABI. No console 8- or 12-byte stride belongs in host code.

## 3. DecoderRegistry::DecoderFactory @0x82B6C778

### Raw-disassembly provenance and signature

.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B6C778.json does not exist. The raw function begins at XEX file offset 0x00B6F778. Spot-checked words include:

- 0x82B6C778 / file 0x00B6F778: 7D 88 02 A6 = mflr r12.
- 0x82B6C7B0 / file 0x00B6F7B0: 1E BA 00 14 = mulli r21,r26,0x14.
- 0x82B6C7E4 / file 0x00B6F7E4: 3B AB 00 14 = addi r29,r11,0x14.
- 0x82B6C894 / file 0x00B6F894: 9B 5F 00 32 = stb r26,0x32(r31).
- 0x82B6C948 / file 0x00B6F948: 39 6B 00 14 = addi r11,r11,0x14.
- 0x82B6C960 / file 0x00B6F960: 48 09 C5 B8 = tail branch to the GPR restore helper.

The exact original member signature is:

~~~cpp
rw::audio::core::Decoder*
rw::audio::core::DecoderRegistry::DecoderFactory(
    void* apDecoderHandle,
    unsigned int auNumChannels,
    unsigned int auMaxSlots,
    rw::audio::core::System* apSystem );
~~~

This is the DecFIGS declaration at references/DecFIGS/dwarfdump/SDKs/EATech/include/rw/audio/core/decoderregistry.h:26-30. The X360 ABI independently confirms it: r3 is the unused DecoderRegistry this; entry copies r4 handle→r30 at 0x82B6C784, r5 channels→r27 at 0x82B6C788, r6 max slots→r26 at 0x82B6C78C, and r7 System→r25 at 0x82B6C790.

The concrete retail caller prepares exactly those registers at SndPlayer1::StartRequest: r4 receives GetDecoderHandle's result at 0x82BA6498, r7 gets System at 0x82BA649C, r6 gets literal 20 at 0x82BA64A0, r5 gets the request's channel byte at 0x82BA64A4, and r3 gets DecoderRegistry at 0x82BA64A8 before the call at 0x82BA64AC. There are no trailing parameters.

The tree's static-explicit-self house spelling can preserve the same ABI as:

~~~cpp
static Decoder* DecoderFactory(
    DecoderRegistry* apSelf,
    void* apDecoderHandle,
    u32 auNumChannels,
    u32 auMaxSlots,
    System* apSystem );
~~~

apSelf is not read by the function.

### DecoderDesc fields consumed

DecFIGS names the record in references/DecFIGS/dwarfdump/SDKs/EATech/include/rw/audio/core/decoder.h:45-83:

| X360 field | Meaning and proof |
|---|---|
| +0x00 | pGetSize. Loaded at 0x82B6C798 and called at 0x82B6C7A4 with r3=channel count and r4=&alignment. DecFIGS typedef is u32 (u32,u32 *) at decoder.h:47-52. |
| +0x04 | pCreateInstanceEvent. Loaded/called with Decoder * at 0x82B6C840-0x82B6C84C; the low return byte is tested at 0x82B6C84C-0x82B6C850. |
| +0x08 | pReleaseEvent. Loaded at 0x82B6C820 and stored into Decoder+0x0C at 0x82B6C830. |
| +0x0C | pDecodeEvent. Loaded at 0x82B6C85C and stored into Decoder+0x14 at 0x82B6C86C. |
| +0x10 | Intrusive list link. Not consumed by this function; named listNode by DecFIGS. |
| +0x14 | guid. Loaded at 0x82B6C870 and stored into Decoder+0x18 at 0x82B6C874. |
| +0x18 | u16 maxBlockSize. Loaded at 0x82B6C7A8 to derive mIsBlockBased, and again at 0x82B6C8D0/0x82B6C90C for storage sizing and SampleBuffer initialization. |

The current DecoderRegistry.h leaves +0x00..+0x0F opaque and does not carry maxBlockSize. DecoderFactory cannot be implemented faithfully until DecoderDesc is expanded to these DWARF-named callback fields plus u16 maxBlockSize. Do not use a local offset view. The standard records' maxBlockSize values were also read directly from the XEX: Xas1 off_82F8A544 +0x18, VA 0x82F8A55C/file 0x00F8D55C = 00 80 (128); Xas0 off_82F8A528 +0x18, VA 0x82F8A540/file 0x00F8D540 = 00 20 (32); EaXma off_82F89394 +0x18 and Pcm16Big off_82F893CC +0x18 are both 00 00. Thus Xas1/Xas0 take the block-buffer path and EaXma/Pcm16Big do not.

### Complete control/data-flow decode

1. Call desc->pGetSize(auNumChannels, &alignment). The returned codec/derived-object size is kept in r24; the out alignment is loaded from stack at 0x82B6C7B4 (0x82B6C794-0x82B6C7A4).
2. Compute blockBased = (desc->maxBlockSize != 0). The zero-test idiom is lhz/cntlzw/rlwinm/xori at 0x82B6C7A8-0x82B6C7C0. r23 is one exactly when maxBlockSize is nonzero.
3. Compute console request bytes as auMaxSlots*0x14 at 0x82B6C7B0. Compute requestOffset = AlignUp(codecBytes,8) at 0x82B6C7C4-0x82B6C7C8. Initial instanceBytes is requestOffset+requestBytes at 0x82B6C7CC.
4. If block based, compute sampleBufferOffset = AlignUp(instanceBytes,16), then console instanceBytes = sampleBufferOffset+0x14 at 0x82B6C7D8-0x82B6C7E4. If the codec-requested allocation alignment is not greater than 16, raise it to 16 at 0x82B6C7DC-0x82B6C7EC.
5. Allocate one instance block via System::New2<Decoder>(off_83271928,&result,0,instanceBytes,alignment,0) at 0x82B6C7F0-0x82B6C808. This uses the global system for the allocation, not incoming apSystem. New2 default-constructs the base Decoder and installs its base vtable (the called specialization's 0x82B6C32C-0x82B6C338). Return null if allocation fails (0x82B6C80C-0x82B6C81C).
6. Before the codec create callback, seed Decoder+0x0C=pReleaseEvent, +0x10=0, +0x2E=(u8)channels, and +0x04=apSystem at 0x82B6C820-0x82B6C83C. Call pCreateInstanceEvent(decoder) at 0x82B6C840-0x82B6C848. If its low byte is zero, call Decoder::Release at 0x82B6C900-0x82B6C904 and return null.
7. After successful codec creation, seed Decoder+0x08=self (0x82B6C854); recompute the actual request-array address as AlignUp(decoder+codecBytes,8) (0x82B6C858-0x82B6C868); seed +0x14=pDecodeEvent and +0x18=guid (0x82B6C85C-0x82B6C874); +0x20=instanceBytes (0x82B6C87C); +0x2C=0 and +0x1C=0 (0x82B6C880-0x82B6C884); feed/prepare/decode cursors +0x2F/+0x30/+0x31=0 (0x82B6C888-0x82B6C890); +0x32=(u8)auMaxSlots (0x82B6C894); +0x33=(u8)blockBased (0x82B6C898); and +0x24=requestAddress-decoder (0x82B6C878/0x82B6C89C).
8. If not block based, skip directly to request-ring initialization at 0x82B6C8A0/0x82B6C924. Decoder+0x28 is not initialized on this path; +0x33=0 prevents its use.
9. If block based, recompute sampleBufferAddress = AlignUp(requestAddress+requestBytes,16) at 0x82B6C8A4-0x82B6C8B4. Compute its offset from decoder, explicitly keep only the low 16 bits, then store that zero-extended value into the 32-bit Decoder+0x28 field at 0x82B6C8B8-0x82B6C8CC.
10. Allocate separate sample storage from apSystem->mpAllocator via allocator vtable slot +0x04 at 0x82B6C8D4-0x82B6C8EC. The arguments are bytes=maxBlockSize*auNumChannels*4 (0x82B6C8D0-0x82B6C8DC), name="Decoder block storage" at rodata VA 0x8214AF34/file 0x0014DF34 (formed at 0x82B6C8A8-0x82B6C8B0), flags=1, alignment=0x80, alignOffset=0 (0x82B6C8B8-0x82B6C8CC). Store the result at Decoder+0x10 at 0x82B6C8F4. If null, Release and return null at 0x82B6C8F8-0x82B6C908.
11. Initialize the inline console SampleBuffer at sampleBufferAddress: +0x00=apSystem (0x82B6C910), +0x0C=0 samples (0x82B6C914), +0x10=(u8)channels (0x82B6C918), +0x04=allocated storage (0x82B6C91C), +0x0E=maxBlockSize (0x82B6C920). The +0x08 word is not seeded here.
12. Initialize the request ring at Decoder+requestOffset. The loop bound is the stored u8 max-slot field, not the full input u32 (0x82B6C92C-0x82B6C950). For each 20-byte console record, only +0x00 (source pointer) and +0x0C (end sample/busy marker) are cleared at 0x82B6C93C and 0x82B6C944; the console walk advances 0x14 at 0x82B6C948. Return Decoder at 0x82B6C958.

DecFIGS supplies the real Decoder member names in decoder.h:137-195. Crosswalk to current host spellings:

| X360 | DecFIGS name | Current host name/status |
|---|---|---|
| +0x04 | mpSystemUseGetSystemAccessor | Hidden in mPad04; must be typed as System *. |
| +0x08 | mpDecoder | Hidden in mPad04; must be typed as Decoder *. The PS3-only adjacent system-SPU declaration is not imported over the X360 store. |
| +0x0C | mpReleaseEvent | mpFinaliser. |
| +0x10 | mSampleBufferStorage | mpAllocatedBlock. |
| +0x14 | mpDecodeEvent | mpDecodeCallback. |
| +0x18 | mGuid | Hidden in mPad18; must be typed as u32. |
| +0x1C | mDecodeSlotSamplesDecoded | miCurrentSampleOffset. |
| +0x20 | mInstanceSize | Hidden in mPad20; must be typed as u32. |
| +0x24 | mRequestDescOffset | muRequestQueueOffset. |
| +0x28 | mSampleBufferOffset | muSourceBufferOffset. |
| +0x2C | mDecodedSamplesAvailable | muCarrySamples. |
| +0x2E | mNumChannels | mucChannelCount. |
| +0x2F | mFeedSlot | mucRequestWriteIndex. |
| +0x30 | mPrepareSlot | mucRequestReadIndex. |
| +0x31 | mDecodeSlot | mucRequestDecodeIndex. |
| +0x32 | mMaxSlots | mucRequestCount. |
| +0x33 | mIsBlockBased | mucUsesSourceBuffer. |

### Host size formulas

Let:

- C = desc->pGetSize(auNumChannels,&alignment), with every codec GetSize returning its host-derived footprint.
- Q = AlignUp(C,8), the request-ring offset.
- R = auMaxSlots * sizeof(DecoderRequest).
- B = AlignUp(Q+R,16), present only for a block-based decoder.

Then the host allocation is:

~~~text
non-block decoder: instanceBytes = Q + R
block decoder:     instanceBytes = B + sizeof(DecoderBuffer)
block storage:     maxBlockSize * auNumChannels * sizeof(f32)
~~~

The prompt's 24-byte assertion reflected an earlier one-pointer version of the header. The current b5-decomp/vendor/renderware/include/rw/audio/core/Decoder.h:61-107 now types both leading console words as pointers: mpFedData and mpSeekData. That second type is independently supported by DecFIGS RequestDesc::pSeekData at references/DecFIGS/dwarfdump/SDKs/EATech/include/rw/audio/core/decoder.h:15-35 and by Decoder::Feed's raw stw r8,4(r30) at 0x82B67964 (hand-disassembled from file 0x00B6A920; the same body stores incoming data r4 at +0x00 at 0x82B6795C). The x86_64 MSVC-layout compile check against the current header gives:

~~~text
sizeof(DecoderRequest) = 32, alignof = 8
mpFedData              = +0
mpSeekData             = +8
miStartSample          = +16
miEndSample            = +20
mucContinue            = +24
mucFlag11              = +25
~~~

The current host-size verdict is therefore **32, not the prompt's 24 and not the console's 20**. The implementation rule remains the requested hard correction: mulli r21,r26,0x14 at 0x82B6C7B0 and addi r11,r11,0x14 at 0x82B6C948 must both become typed sizeof(DecoderRequest) arithmetic. Twenty requests consume 640 bytes on the current x64 host, not the console's 400.

The other 0x14 at 0x82B6C7E4 is a different record: the inline console SampleBuffer/DecoderBuffer. The current DecoderBuffer happens to measure 24 on x64, but it is not yet structurally complete: DecoderFactory proves +0x00 is a System * (0x82B6C910), +0x04 is a float/storage pointer (0x82B6C91C), and +0x10 is a channel byte (0x82B6C918), while the current header calls +0x00 u32 and has no channel member. DecFIGS SampleBuffer names mpSystem, mpStorage, uintptr_t mpTempStore, mNumSamples, mMaxSamples, and mNumChannels at samplebuffer.h:13-44. A minimal faithful host record therefore has two pointers plus the pointer-sized mpTempStore and the trailing channel byte, and measures 32 bytes on x64. The factory formula must remain sizeof(DecoderBuffer), never a frozen 24 or 20, so it automatically follows that required header correction.

The Decoder fixed header has the same issue: current mPad04[8] hides two console pointers. Typing them as System * and Decoder * widens them independently. Consequently every codec pGetSize must return a host sizeof-based footprint. Current bare return 60 bodies in XasDec.cpp:58-63 and Pcm16BigDec.cpp:62-67 are console literals and must become sizeof(XasDec) and sizeof(Pcm16BigDec); Xas1's shared equivalent must do the same. EaXmaDec::GetSize already uses sizeof at EaXmaDec.cpp:278-282.

With the typed fixed header and minimal typed DecoderBuffer above, the x86_64 MSVC ABI yields sizeof(Decoder)=80, sizeof(XasDec)=sizeof(Xas1Dec)=sizeof(Pcm16BigDec)=96, and sizeof(DecoderBuffer)=32. For the retail 20-slot request count, an Xas0/Xas1 instance is therefore AlignUp(96+20*32,16)+32 = 768 bytes; Pcm16Big is 96+20*32 = 736 bytes. These are consequences of host sizeof, not new literals to embed.

### Required typed shape before implementing the body

Do not implement this with casts over opaque header bytes. The required header work is:

1. Expand DecoderDesc from its current char mHeader[0x10] into pGetSize, pCreateInstanceEvent, pReleaseEvent, pDecodeEvent, then retain mpNext/muId and append u16 muMaxBlockSize. These names/types are DecFIGS ground truth at decoder.h:45-83 and are X360-gated by 0x82B6C798-0x82B6C8D0. In particular, pGetSize takes (u32 numChannels,u32 *alignment): the factory sets r3 from incoming channels at 0x82B6C79C. XasDec/Pcm16BigDec's current unused first-parameter pointer spelling must be corrected even though those particular bodies do not read it.
2. Replace Decoder::mPad04 with System *mpSystemUseGetSystemAccessor and Decoder *mpDecoder; replace mPad18 with u32 mGuid; replace mPad20 with u32 muInstanceSize. Give DecoderRegistry friend access or an equivalent real declaration-level access path.
3. Correct DecoderBuffer by typing mpSystem, mpData/mpStorage, pointer-sized mpTempStore, sample count, max-sample/stride, and channel count. Do not import the unrelated large PS3 platform tail.
4. Populate every registered host DecoderDesc callback with host function addresses. The current Xas/Xas1/Pcm/EaXma records deliberately contain zeroed callback headers, e.g. XasDec.cpp:29-36, Xas1Dec.cpp:30-38, Pcm16BigDec.cpp:34-42, and EaXmaDec.cpp:79-91. DecoderFactory dispatches those slots immediately.
5. Change DecoderRegistry.cpp's InfoFromLink owner recovery from the console literal subtraction link-0x10 (current lines 28-32) to link - offsetof(DecoderDesc,mpNext). Once four callback pointers widen, mpNext no longer has host offset 0x10. RegisterDecoder already takes &info->mpNext by name; owner recovery must do the same.

The declaration-level target for the two records is therefore:

~~~cpp
typedef u32  (*DecoderGetSizeFn)( u32 auNumChannels, u32* apuAlignment );
typedef bool (*DecoderCreateInstanceEventFn)( Decoder* apDecoder );
typedef void (*DecoderReleaseEventFn)( Decoder* apDecoder );
typedef s32  (*DecoderDecodeEventFn)(
    Decoder* apDecoder,
    DecoderBuffer* apBuffer,
    s32 aiNumSamples );

struct DecoderDesc
{
    DecoderGetSizeFn             pGetSize;
    DecoderCreateInstanceEventFn pCreateInstanceEvent;
    DecoderReleaseEventFn        pReleaseEvent;
    DecoderDecodeEventFn         pDecodeEvent;
    void*                        mpNext;
    u32                          muId;
    u16                          muMaxBlockSize;
};

struct DecoderBuffer
{
    System*   mpSystem;
    f32*      mpData;
    uintptr_t mpTempStore;
    u16       muSampleCursor;
    u16       muStride;
    u8        mucChannelCount;
};
~~~

Those are natural host layouts; no console offset or packing pragma belongs on either. Existing decoder consumers can retain the mpData/muSampleCursor/muStride spellings while the comments record the DecFIGS mpStorage/mNumSamples/mMaxSamples names.

### Faithful host body

This body is expressed only through typed fields and sizeof. It assumes the required shape above has landed. Alignment constants 8, 16, and 128 are genuine alignment requirements, not console object sizes, and remain literals.

~~~cpp
static u32 AlignUpDecoderFactory( u32 auValue, u32 auAlignment )
{
    return ( auValue + auAlignment - 1u ) & ~( auAlignment - 1u );
}

static uintptr_t AlignUpDecoderFactoryPointer(
    uintptr_t auValue,
    uintptr_t auAlignment )
{
    return ( auValue + auAlignment - 1u ) & ~( auAlignment - 1u );
}

extern "C" rw::audio::core::System* off_83271928;

rw::audio::core::Decoder*
rw::audio::core::DecoderRegistry::DecoderFactory(
    DecoderRegistry* /*apSelf*/,
    void* apDecoderHandle,
    u32 auNumChannels,
    u32 auMaxSlots,
    System* apSystem )
{
    DecoderDesc* lpDesc = static_cast<DecoderDesc*>( apDecoderHandle );

    u32 luAlignment = 0u;
    const u32 luCodecBytes =
        lpDesc->pGetSize( auNumChannels, &luAlignment );
    const bool lbBlockBased = lpDesc->muMaxBlockSize != 0u;

    const u32 luRequestOffset =
        AlignUpDecoderFactory( luCodecBytes, 8u );
    const u32 luRequestBytes =
        auMaxSlots * static_cast<u32>( sizeof( DecoderRequest ) );

    u32 luInstanceBytes = luRequestOffset + luRequestBytes;
    u32 luSampleBufferOffset = 0u;
    if ( lbBlockBased )
    {
        luSampleBufferOffset =
            AlignUpDecoderFactory( luInstanceBytes, 16u );
        luInstanceBytes =
            luSampleBufferOffset
            + static_cast<u32>( sizeof( DecoderBuffer ) );
        if ( luAlignment <= 16u )
            luAlignment = 16u;
    }

    Decoder* lpDecoder = 0;
    System::New2<Decoder>(
        off_83271928,
        &lpDecoder,
        0,
        luInstanceBytes,
        luAlignment,
        0 );
    if ( lpDecoder == 0 )
        return 0;

    lpDecoder->mpFinaliser = lpDesc->pReleaseEvent;
    lpDecoder->mpAllocatedBlock = 0;
    lpDecoder->mucChannelCount = static_cast<u8>( auNumChannels );
    lpDecoder->mpSystemUseGetSystemAccessor = apSystem;

    if ( !lpDesc->pCreateInstanceEvent( lpDecoder ) )
    {
        lpDecoder->Release();
        return 0;
    }

    u8* const lpDecoderBytes = reinterpret_cast<u8*>( lpDecoder );
    u8* const lpRequestAddress = reinterpret_cast<u8*>(
        AlignUpDecoderFactoryPointer(
            reinterpret_cast<uintptr_t>( lpDecoderBytes + luCodecBytes ),
            8u ) );
    const u32 luActualRequestOffset =
        static_cast<u32>( lpRequestAddress - lpDecoderBytes );

    lpDecoder->mpDecoder = lpDecoder;
    lpDecoder->mpDecodeCallback = lpDesc->pDecodeEvent;
    lpDecoder->mGuid = lpDesc->muId;
    lpDecoder->miCurrentSampleOffset = 0;
    lpDecoder->muInstanceSize = luInstanceBytes;
    lpDecoder->muRequestQueueOffset = luActualRequestOffset;
    lpDecoder->muCarrySamples = 0u;
    lpDecoder->mucRequestWriteIndex = 0u;
    lpDecoder->mucRequestReadIndex = 0u;
    lpDecoder->mucRequestDecodeIndex = 0u;
    lpDecoder->mucRequestCount = static_cast<u8>( auMaxSlots );
    lpDecoder->mucUsesSourceBuffer =
        static_cast<u8>( lbBlockBased ? 1u : 0u );

    if ( lbBlockBased )
    {
        u8* const lpSampleBufferAddress = reinterpret_cast<u8*>(
            AlignUpDecoderFactoryPointer(
                reinterpret_cast<uintptr_t>(
                    lpRequestAddress + luRequestBytes ),
                16u ) );
        const u32 luActualSampleBufferOffset =
            static_cast<u32>(
                lpSampleBufferAddress - lpDecoderBytes );

        // The X360 explicitly zero-extends only the low 16 bits into this u32.
        lpDecoder->muSourceBufferOffset =
            static_cast<u32>(
                static_cast<u16>( luActualSampleBufferOffset ) );

        const u32 luStorageBytes =
            static_cast<u32>( lpDesc->muMaxBlockSize )
            * auNumChannels
            * static_cast<u32>( sizeof( f32 ) );

        f32* lpStorage = static_cast<f32*>(
            apSystem->mpAllocator->Alloc(
                luStorageBytes,
                "Decoder block storage",
                1,
                128u,
                0u ) );
        lpDecoder->mpAllocatedBlock = lpStorage;
        if ( lpStorage == 0 )
        {
            lpDecoder->Release();
            return 0;
        }

        DecoderBuffer* lpSampleBuffer =
            reinterpret_cast<DecoderBuffer*>(
                lpSampleBufferAddress );
        lpSampleBuffer->mpSystem = apSystem;
        // mpTempStore is intentionally not written by this factory.
        lpSampleBuffer->muSampleCursor = 0u;
        lpSampleBuffer->mucChannelCount =
            static_cast<u8>( auNumChannels );
        lpSampleBuffer->mpData = lpStorage;
        lpSampleBuffer->muStride = lpDesc->muMaxBlockSize;
    }

    DecoderRequest* lpRequests =
        reinterpret_cast<DecoderRequest*>( lpRequestAddress );
    for ( u32 luSlot = 0u;
          luSlot < lpDecoder->mucRequestCount;
          ++luSlot )
    {
        lpRequests[luSlot].mpFedData = 0;
        lpRequests[luSlot].miEndSample = 0;
    }

    return lpDecoder;
}
~~~

Two deliberate details should not be “cleaned up” accidentally:

- Allocation sizes use full auMaxSlots, but the field and initialization-loop bound use static_cast<u8>(auMaxSlots), matching mulli at 0x82B6C7B0 versus stb/lbz at 0x82B6C894/0x82B6C92C.
- muSourceBufferOffset receives only the low 16 bits, matching clrlwi 16 at 0x82B6C8C4 before the 32-bit store at 0x82B6C8CC. Whether to add a host assertion for overflow is a separate explicit safety decision; silently widening the binary behavior is not faithful reconstruction.

## 4. PRECONDITIONS

**Voice::CreateInstance DEREFERENCES the plug-in descriptor that a handle resolves to, so staging against a NULL handle CRASHES rather than failing guarded.** The proof is the unguarded config+0x04 descriptor load at 0x82B6EC98 followed by descriptor+0x04 at 0x82B6ECA0 and bctrl at 0x82B6ECA8. The helper's later null-Voice callback cannot catch this earlier descriptor fault.

Before either helper is called:

1. sndplayerHandle must be non-null for both mono and stereo.
2. resampleHandle must be non-null for both mono and stereo.
3. pannerHandle must be non-null for mono.
4. sendHandle must be non-null for both mono and stereo.
5. Each handle must resolve to a real host PlugInDescRunTime with a non-null pGetSize and pCreateInstance callback. Voice::CreateInstance calls pGetSize at 0x82B6ECA8 and again at 0x82B6EDEC; PlugIn::CreateInstance calls pCreateInstance at 0x82B6A864-0x82B6A870.
6. GenericRwacFactory registration must have run before SpliceManager performs its lookups. Today Rsp0, Pn21, and Sen0 meet this condition. SnP1 does not: GetPlugInDescRunTime returns 0 and registration 21 is omitted.
7. SndPlayer1's descriptor must not be published merely to make the handle non-null. Its currently deferred streaming Process/timer/event chain must be real enough for a staged voice to execute; SndPlayer1.cpp:433-453 is not ready.
8. auMonoVoiceCount and auStereoVoiceCount must each be at most KU_MAX_POOLED_VOICES (64) before writing the fixed local arrays. The retail values 64 and 24 satisfy this. VoicePool::Prepare's later assertion is too late to prevent a constructor-local overflow.
9. Every Voice::CreateInstance call must succeed before its array is handed to Prepare. The retail helper reports failure but does not initialize mppPlugIn or abort the constructor; Prepare then copies the failed pair. A safe host unpark must either make success a construction invariant or deliberately add all-or-nothing cleanup as a documented host safety deviation.
10. For actual SndPlayer1 playback, DecoderFactory, typed DecoderDesc callback records, host-sized codec GetSize functions, and the DecoderRequest/DecoderBuffer carves described in Part B must be live.

The safe check belongs immediately after the four GetPlugInHandle calls and before either voice loop. Within SpliceManager, it can be expressed without dereferencing a null handle:

~~~cpp
rw::audio::core::PlugInDescRunTime* lpSndPlayer =
    reinterpret_cast<rw::audio::core::PlugInDescRunTime*>( sndplayerHandle );
rw::audio::core::PlugInDescRunTime* lpResample =
    reinterpret_cast<rw::audio::core::PlugInDescRunTime*>( resampleHandle );
rw::audio::core::PlugInDescRunTime* lpPanner =
    reinterpret_cast<rw::audio::core::PlugInDescRunTime*>( pannerHandle );
rw::audio::core::PlugInDescRunTime* lpSend =
    reinterpret_cast<rw::audio::core::PlugInDescRunTime*>( sendHandle );

const bool lbStagingReady =
    lpSndPlayer != 0 && lpSndPlayer->pGetSize != 0
                     && lpSndPlayer->pCreateInstance != 0
    && lpResample != 0 && lpResample->pGetSize != 0
                       && lpResample->pCreateInstance != 0
    && lpPanner != 0 && lpPanner->pGetSize != 0
                     && lpPanner->pCreateInstance != 0
    && lpSend != 0 && lpSend->pGetSize != 0
                   && lpSend->pCreateInstance != 0;
~~~

Do not call CreateMonoVoice or CreateStereoVoice unless lbStagingReady is true. At the present tree state it is false only because SnP1 is not registered/publishable; Rsp0, Pn21, and Sen0 are live.

## 5. DO NOT INVENT

- No X360 dossier exists for DecoderFactory. The decode above is from raw XEX bytes at file 0x00B6F778 through 0x00B6F963; do not cite a nonexistent JSON or Hex-Rays output. Decoder::Feed is likewise raw-decoded from file 0x00B6A920; its +0/+4 stores are used only to type the two request pointers.
- No matching Feb-2007 vendor DecoderRegistry/DecoderFactory source was found under references/Feb-2007/BrnEntityModuleUnity or the wider references/Feb-2007 tree. Do not invent source variable names from that leak.
- DecoderBuffer/SampleBuffer +0x08 is not written by DecoderFactory. DecFIGS calls the corresponding field uintptr_t mpTempStore, but its precise X360 runtime role is not established by this function. Preserve it as a pointer-sized field and do not initialize or use it here without a consumer decode.
- Do not import the entire large DecFIGS PS3 SampleBuffer layout into the small X360 inline record. Only the fields gated by X360 stores and the DecFIGS names listed above are justified.
- DecoderRequest's two leading pointers, mpFedData and mpSeekData, are both attested by Decoder::Feed and by the current header. Other request semantics are outside this factory decode. The measured current host sizeof is 32; do not preserve the prompt's stale 24 or the console's 20, and do not guess additional behavior in DecoderFactory.
- The binary has no null check for apDecoderHandle before loading desc+0x00 at 0x82B6C798. Do not invent a “decoder not found” fallback and call it retail behavior. If a host guard is desired, label it explicitly as a safety deviation.
- The binary gives no overflow policy for hostile auMaxSlots/auNumChannels values. It multiplies in 32 bits, stores max slots as u8, and truncates sample-buffer offset to 16 bits. Retail passes 20 requests. Do not silently choose saturation, exceptions, or widened state.
- It is not verified that every possible host codec allocation remains below the 16-bit sample-buffer-offset limit or below SndPlayer1's later u16 instance-size copy. Measure the finalized host descriptors before deciding whether an assert or a coordinated field widening is required.
- The exact cleanup policy for a partially built splice pool is not present in the retail constructor: it continues after helper failure. Do not invent per-voice rollback inside the faithful staging without marking the deviation.
- SnP1's missing descriptor must not be filled with placeholder callbacks. The current SndPlayer1 Process and timer bodies are explicitly deferred. Registration is safe only after their required engine behavior and the DecoderFactory chain are real.
- No fcmpu occurs in the requested functions, so there is no NaN branch to translate. Do not introduce a floating comparison around the 1.0f/2.0f constructor parameters.
- No floating argument is passed to Voice::CreateInstance. The floats live in stack constructor-parameter objects and are reached through VoiceStageConfig::mpContext. Do not add trailing float parameters based on pseudocode.
