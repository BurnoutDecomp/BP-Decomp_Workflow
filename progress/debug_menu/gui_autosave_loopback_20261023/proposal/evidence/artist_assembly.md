# ARTIST evidence excerpts

All excerpts below are copied from the local `BURNOUT_X360_ARTIST.XEX` IDA exports. Hashes are SHA-256 of the complete JSON export, not the excerpt. The X360 assembly is the behavior authority.

## BrnGui::OnlineGameOptionsSummary::HandleControllerInputSaveOptions

- Export: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x824A8C58.json`
- SHA-256: `D050066CC5564AE392C7DFCF6100982A7F8BBCB95800B75671DD177CDF07291A`
- IDA name: `BrnGui::OnlineGameOptionsSummary::HandleControllerInputSaveOptions`

Addresses `0x824A8C6C..0x824A8C6C`:

```asm
0x824A8C6C  li        r27, 0
```

Addresses `0x824A8D84..0x824A8DA8`:

```asm
0x824A8D84  addis     r6, r5, 1
0x824A8D88  addis     r3, r5, 1
0x824A8D8C  addi      r6, r6, -0x5800
0x824A8D90  addi      r3, r3, -0x4788
0x824A8D94  bl        BrnGui__OptionsDataProfile__SetCreatedOnlineGameOptions
0x824A8D98  addi      r4, r1, 0x300+var_2B0
0x824A8D9C  lwz       r3, 0x1C(r31)
0x824A8DA0  stb       r27, 0x300+var_2B0(r1)
0x824A8DA4  bl        ___OutputGuiEvent_VGuiAutosaveRequestEvent_BrnGui___StateInterface_CgsGui__QAAXAAVGuiAutosaveRequestEvent_BrnGui___Z# CgsGui::StateInterface::OutputGuiEvent<BrnGui::GuiAutosaveRequestEvent>(BrnGui::GuiAutosaveRequestEvent &)
0x824A8DA8  mr        r3, r31
```

## StateInterface::OutputGuiEvent<GuiAutosaveRequestEvent>

- Export: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x824937E0.json`
- SHA-256: `04AB40DB88BEDB623B604058EA6D7B87854CD75A44A6069B055B349BFA93C29D`
- IDA name: `??$OutputGuiEvent@VGuiAutosaveRequestEvent@BrnGui@@@StateInterface@CgsGui@@QAAXAAVGuiAutosaveRequestEvent@BrnGui@@@Z`

Addresses `0x824937E0..0x8249382C`:

```asm
0x824937E0  mflr      r12
0x824937E4  stw       r12, var_8(r1)
0x824937E8  stwu      r1, back_chain(r1)
0x824937EC  lbz       r11, 0(r4)
0x824937F0  li        r6, 0x10
0x824937F4  li        r5, 0x28 # '('
0x824937F8  addi      r4, r1, 0x70+var_20
0x824937FC  addi      r3, r3, 0xC
0x82493800  stb       r11, 0x70+var_14(r1)
0x82493804  li        r11, 0xC
0x82493808  stw       r11, 0x70+var_18(r1)
0x8249380C  li        r11, 1
0x82493810  stw       r11, 0x70+var_20(r1)
0x82493814  li        r11, 0x164
0x82493818  stw       r11, 0x70+var_1C(r1)
0x8249381C  bl        CgsModule__VariableEventQueue_65536_16___AddEvent
0x82493820  addi      r1, r1, 0x70
0x82493824  lwz       r12, var_8(r1)
0x82493828  mtlr      r12
0x8249382C  blr
```

## EventInterpreterModule::ProcessOutEvents

- Export: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8285E1D0.json`
- SHA-256: `D308729091EECFDF0F3840E8EB93EB145908EA1DB210BB3695C910A87649CB3F`
- IDA name: `CgsGui::EventInterpreterModule::ProcessOutEvents`

Addresses `0x8285E568..0x8285E57C`:

```asm
0x8285E568  lwz       r11, 8(r22)
0x8285E56C  mr        r3, r23
0x8285E570  lwz       r6, 0(r22)
0x8285E574  add       r4, r11, r22
0x8285E578  lwz       r5, 4(r22)
0x8285E57C  bl        CgsModule__VariableEventQueue_18432_16___AddEvent
```

## CgsGui::GuiModule::Update

- Export: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x828602C8.json`
- SHA-256: `B13179A2D58CE508E75A1FE324E6529459F88262870F633EFCF72EFC86A748C0`
- IDA name: `CgsGui::GuiModule::Update`

Addresses `0x82860568..0x82860578`:

```asm
0x82860568  bl        CgsGui__CgsGuiModuleIO__OutputBuffer__GetOutEventQueu
0x8286056C  mr        r4, r3
0x82860570  addis     r3, r28, 2
0x82860574  addi      r3, r3, -0x4BE4
0x82860578  bl        ___Append__0EIAA__0BA____VariableEventQueue__0EIAA__0BA__CgsModule__QAA_NABV01__Z# CgsModule::VariableEventQueue<18432,16>::Append<18432,16>(CgsModule::VariableEventQueue<18432,16> const &)
```

## BrnGui::GuiModule::Update

- Export: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82527A58.json`
- SHA-256: `E6DD401B6E921876D669F7BA8FB5931EAFEA44BDFF4945ED20F7D4720B9B8FAA`
- IDA name: `BrnGui::GuiModule::Update`

Addresses `0x82529054..0x82529078`:

```asm
0x82529054  lbz       r11, 0(r30)# jumptable 82528C5C case 0  ; jumptable 82528C5C case 0
0x82529058  lbz       r10, 0x490+var_430(r1)
0x8252905C  or        r11, r11, r10
0x82529060  stb       r11, 0x490+var_430(r1)
0x82529064  li        r11, 1
0x82529068  stbx      r11, r26, r15
0x8252906C  b         def_82528154# jumptable 82528154 default case, cases 1-4,7-12,14,16-20,22-26,28,30-41,43-49,51-91,93,95-107,109-126
0x82529070  lwz       r9, 0(r30)# jumptable 82528C5C case 2  ; jumptable 82528C5C case 2
0x82529074  addi      r11, r1, 0x490+var_330
0x82529078  li        r10, 1
```

Addresses `0x825295CC..0x82529700`:

```asm
0x825295CC  add       r30, r26, r15
0x825295D0  lbz       r11, 0(r30)
0x825295D4  cmplwi    cr6, r11, 1
0x825295D8  lis       r11, 0xF
0x825295DC  bne       cr6, loc_825296AC
0x825295E0  ori       r11, r11, 0xA288 # 0xFA288
0x825295E4  lis       r10, 0x18
0x825295E8  ori       r31, r10, 0xD840 # 0x18D840
0x825295EC  lbzx      r11, r26, r11
0x825295F0  cmplwi    cr6, r11, 0
0x825295F4  bne       cr6, loc_82529620
0x825295F8  addis     r3, r26, 0xF
0x825295FC  addi      r3, r3, 0x5740
0x82529600  bl        BrnGui__GuiCache__GetTime
0x82529604  lis       r11, flt_82004C6C@ha
0x82529608  lfsx      f13, r26, r31
0x8252960C  lfs       f0, flt_82004C6C@l(r11)
0x82529610  li        r11, 1
0x82529614  fadds     f0, f13, f0
0x82529618  fcmpu     cr6, f1, f0
0x8252961C  bgt       cr6, loc_82529624
0x82529620  li        r11, 0
0x82529624  lbz       r10, 0x490+var_430(r1)
0x82529628  or        r11, r10, r11
0x8252962C  clrlwi    r11, r11, 24
0x82529630  cmplwi    cr6, r11, 1
0x82529634  bne       cr6, loc_82529704
0x82529638  lbz       r11, 0x490+var_428(r1)
0x8252963C  cmplwi    cr6, r11, 1
0x82529640  bne       cr6, loc_82529654
0x82529644  addi      r4, r1, 0x490+var_330
0x82529648  mr        r3, r26
0x8252964C  bl        BrnGui__GuiModule__AutosaveProfile
0x82529650  b         loc_82529704
0x82529654  lwz       r11, 0x490+var_39C(r1)
0x82529658  lwz       r11, 0(r11)
0x8252965C  cmpwi     cr6, r11, 1
0x82529660  bne       cr6, loc_82529704
0x82529664  lis       r11, 0xA
0x82529668  ori       r11, r11, 0x78C8 # 0xA78C8
0x8252966C  lbzx      r11, r26, r11
0x82529670  cmplwi    cr6, r11, 0
0x82529674  beq       cr6, loc_82529704
0x82529678  addis     r4, r26, 0xA
0x8252967C  li        r6, 0
0x82529680  addi      r4, r4, 0x66D0
0x82529684  li        r5, 0
0x82529688  addi      r3, r4, 0x10
0x8252968C  bl        BrnGui__ProfileManager__Autosave
0x82529690  li        r11, 0
0x82529694  addis     r3, r26, 0xF
0x82529698  addi      r3, r3, 0x5740
0x8252969C  stb       r11, 0(r30)
0x825296A0  bl        BrnGui__GuiCache__GetTime
0x825296A4  stfsx     f1, r26, r31
0x825296A8  b         loc_82529704
0x825296AC  ori       r11, r11, 0x979C # 0xF979C
0x825296B0  lwzx      r11, r26, r11
0x825296B4  cmpwi     cr6, r11, 0
0x825296B8  beq       cr6, loc_82529704
0x825296BC  lis       r10, 0
0x825296C0  ori       r10, r10, 0xA615 # 0xA615
0x825296C4  lbzx      r11, r11, r10
0x825296C8  cmplwi    cr6, r11, 1
0x825296CC  bne       cr6, loc_82529704
0x825296D0  addis     r3, r26, 0xF
0x825296D4  addi      r3, r3, 0x5740
0x825296D8  bl        BrnGui__GuiCache__GetTime
0x825296DC  lis       r11, 0x18
0x825296E0  ori       r11, r11, 0xD840 # 0x18D840
0x825296E4  lfsx      f13, r26, r11
0x825296E8  lis       r11, flt_8201A258@ha
0x825296EC  lfs       f0, flt_8201A258@l(r11)
0x825296F0  fadds     f0, f13, f0
0x825296F4  fcmpu     cr6, f1, f0
0x825296F8  ble       cr6, loc_82529704
0x825296FC  li        r11, 1
0x82529700  stb       r11, 0(r30)
```
