# Original event-337 and event-143 producer chains

These are separate from the PC loopback boundary: ARTIST emits each through the canonical channel-40 wrapper, and the existing consumers are on the GUI module INPUT side.

## Event 337 — `GuiEventRoadRuleFail`

- The exported ARTIST template is `CgsGui::StateInterface::OutputGuiEvent<BrnGui::GuiEventRoadRuleFail> @0x82436950`; its only xref is `BrnGui::RoadRuleComponent::UpdateCurrentTime @0x8243F540`.
- Template pseudocode copies six 8-byte chunks (48 bytes) from its argument, sets wrapper words `(48, 337, 16)`, and calls `VariableEventQueue<65536,16>::AddEvent(queue, 40, 64)`. Assembly confirms size `0x30`, id `0x151`, payload offset `0x10`, channel `0x28`, record size `0x40`.
- Caller pseudocode fills the `GuiEventRoadRuleFail` payload only after the time-rule transitions from safe to dangerous: road id, time-score type, local/AI ruler booleans and the 32-byte ruler name, then calls the instantiation. This is a real guarded producer; no extra failure condition is inferred here.
- DecFIGS names the twin `GuiEventRoadRuleFail : GuiEvent<333>` and its fields; X360 ARTIST/source pin the target id to 337 and the console payload to 48 bytes. The current PC `GuiEventRoadRuleFail` layout is X360 reordered with `mRoadID` at payload+0, type at +8, name +12, booleans +44/+45 (`BrnGuiEventTypeDefs.h:2226–2236`).
- The current PC body at `BrnRoadRuleComponent.cpp:524–536` constructs the same payload and calls generic `OutputGuiEvent(lFail)`. ARTIST caller asm at `0x8243F834..0x8243F840` finishes the 32-byte rule-name copy, passes the state interface and local event, then calls the 337 template. A proposed channel-40 wrapper can repair the raw flow queue encoding; after the flow drain, however, the analyzer must still receive the type-keyed event on the GUI module input.

Original caller asm around that site:

```text
0x8243F824  li r5,0x20
0x8243F828  addi r4,r1,...var_100   ; source rule-name string
0x8243F82C  addi r3,r1,...var_134   ; destination rule-name array
0x8243F830  bl strncpy
0x8243F834  addi r4,r1,...var_140   ; GuiEventRoadRuleFail object
0x8243F838  lwz r3,0(r25)          ; StateInterface
0x8243F83C  stb r24,...            ; final caller payload flag
0x8243F840  bl OutputGuiEvent<GuiEventRoadRuleFail>
```

The template body at `0x82436950` copies 6 qwords, writes words 48/337/16, then calls AddEvent with r5=40 and r6=64.

## Event 143 — `GuiEventSetPlayer0ControllerPort`

- The exported ARTIST template is `CgsGui::StateInterface::OutputGuiEvent<BrnGui::GuiEventSetPlayer0ControllerPort> @0x82476D88`; its only xref is `BrnGui::BootLegal::Update @0x82477270`.
- Template pseudocode/assembly writes `(4, 143, 12)` plus the 4-byte controller port and calls `AddEvent(queue, 40, 16)`.
- The caller is the invite-soft-reboot branch: it reads the soft-reboot data word, calls `OutputGuiEvent<...>`, clears BootLegal's input queue, and returns. The code path is guarded by `HasGameBeenRebootedDueToInvite`.
- DecFIGS names `GuiEventSetPlayer0ControllerPort : GuiEvent<141>` with a 32-bit `miPort`; ARTIST is the arbitration authority for X360 id143. The PC semantic sink is `BrnGui::GuiModule::DispatchInboundGuiEvents` case143 (`BrnGuiModule.cpp:2533`): read the 32-bit index, call `SystemUserProfile::SetUserIndex`, then `UpdateUserSigninState`.
- The current PC `BrnBootLegal.cpp` invokes generic `OutputGuiEvent` at line713. ARTIST caller asm at `0x82477CC0..0x82477CD8` loads the soft-reboot port word, calls the 143 template with the BootLegal state interface, then clears the state's input queue. The separate frozen BootLegal proposal reconstructs the event's original payload and channel-40 wrapper; this packet establishes that the existing module-input case still cannot execute until the general module output→next-input path is restored.

Original caller asm:

```text
0x82477CC0  lwz r11,0(r30)          ; soft-reboot port word
0x82477CC4  addi r4,r1,...var_178   ; payload word
0x82477CC8  lwz r3,0x1C(r31)        ; StateInterface
0x82477CCC  stw r11,...var_178
0x82477CD0  bl OutputGuiEvent<GuiEventSetPlayer0ControllerPort>
0x82477CD4  lwz r3,0x18(r31)        ; BootLegal input queue
0x82477CD8  bl VariableEventQueue<18432,16>::Clear
```

The template body at `0x82476D88` writes words 4/143/12, then calls AddEvent with r5=40 and r6=16.

## Consumer boundary

At this base, `HudMessageAnalyzer::Update` runs over the current `mpGuiEventInputBuffer` queue (`BrnGuiModule.cpp:4287`); its case337 calls `HandleRoadRuleFailed` (`BrnGuiHudMessageAnalyzer.cpp:1882–1883`). `DispatchInboundGuiEvents` case143 reads the same module input stream. `DrainFlowOutputQueue` runs after the flows and places unwrapped channel-40 output on `mGuiOutQueue` while directly fanning to flow observers, but neither that drain nor the current frame output bridges append the event to the next `mpGuiEventInputBuffer` on this selected PC path.

The ARTIST module-level store/append/clear proof and PC lifetime/duplicate constraints are in `loopback_chain.md`. These two producers should remain unresolved end-to-end until that whole queue owner/dispatch route is composed; no direct event-specific bridge is proposed here.
