# Intro video event repair

Review only candidate `post/GameSource/Gui/BrnGuiVideoEvents.h` against base
`pre/GameSource/Gui/BrnGuiVideoEvents.h`. The one-path patch is
`intro-video-events.patch`. No shared source was modified.

Normal shipped game log `build/game/BrnGame.log` records EAFranchise play then
`[GUI_OUT_UNEXPECTED] outer_type=508 bytes=56 pre_world=0`. Later skip requests
likewise fail with outer_type509 bytes16. ProcessOutEvents correctly accepts
boxed GUI output on channel40; it asserts/drops these raw channels after world
update. The failure happens before MovieManager can request/decode the video.

ARTIST original assembly is the authority:

- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82476C68.json`:
  OutputGuiEvent<GuiEventPlayVideo> loads vector16 at caller+0, id64+16,
  sound32+24, crossfade32+28/+32, bool bytes+36/+37/+38. It writes wrapper
  `{48,508,16}`, calls AddEvent channel40 bytes64, and returns void (QAAX).
- `0x82476CF8.json`: stop event copies exactly the same full definition,
  wrapper `{48,509,16}`, channel40 bytes64. The existing one-bool event is wrong.
- `0x824F17C0.json`: HandleStopVideoEvent does not inspect event payload.
- DecFIGS `references/DecFIGS/dwarfdump/GameSource/Gui/BrnGuiEventTypeDefs.h`
  lines8444-8464 corroborates both named events carrying VideoDefinition mVideo.
  DecFIGS event ids498/499 are older; ARTIST508/509 arbitrate.

Candidate preserves the existing flattened named-field API, removes the spurious
embedded GUI wrapper, restores raw payload order/alignment/size and specializes
only the two video OutputGuiEvent instances to box once on channel40. It leaves
the unrelated generic event population untouched. Stop shares the same field
representation as play, with event509. Static assertions pin every meaningful
field and both wrapper sizes.

Regression `video_event_regression.cpp` compiles actual StateInterface.cpp and
actual inline VariableEventQueue, CgsStrStream.cpp, and only test assert/log sinks.
Base compilePASS then runtime exit17: channel508 bytes56 instead of40/64.
Candidate compilePASS/runtimePASS: play508 and stop509 both channel40, raw48,
offset16,64 bytes, EA zero-extended high-bit id, sound hash and keep flag preserved.
`regression_results.json` contains exact outputs.

Seven actual producers/consumers compile with canonical shipping flags/includes
and candidate overlay: BootVideos, BootLegal, PostTitleScreenLoad, Intro, Video,
MovieManager, GuiModule. `consumer-gates/compile.log` and results.json record PASS.

Limit: no normal game was launched; true intro decode/render/audio/end-to-end
advance still requires the coordinated rebuilt-executable runtime witness.

Return explicit `VERDICT: pass` or `VERDICT: fail` with concrete findings.
