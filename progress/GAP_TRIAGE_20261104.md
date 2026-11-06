# Triage des manques déclarés — 2026-11-04

**Conclusion :** la grande majorité des manques déclarés dans les commentaires sont périmés. Tous les points prioritaires du brief le sont, ou ne sont pas des manques. Les vrais manques restants ayant un impact sur le joueur sont peu nombreux : les modes (Face Off, overrides online), le son de slipstream, et quelques bras « parqués ».

- **État lu :** branche b5 `claude/night-8-gap-triage-62941e`, partie de `work/audit-20261104` (`3ae8053b5`), plus le commit de commentaires `025631d0a`. Les lignes citées sont celles de ce commit.
- **Chemins :** sauf mention contraire, ils partent de `b5-decomp/src/GameSource/`.
- **Ce que cet audit ne prouve pas :** le jeu n'a pas été lancé et rien n'a été recompilé. « Périmé » signifie que le corps existe (`tools/re/hasbody.py`) et, pour les points cités, qu'il est monté (`tools/build/build_game_exe.bat`) et appelé. Cela ne certifie pas que le corps est fidèle à l'asm : seuls les points qui citent une adresse ont été confrontés à l'asm ARTIST.

## Volume

| Relevé | Occurrences |
|---|---|
| Motifs stricts, sensibles à la casse | 71 |
| Mêmes motifs, insensibles à la casse | 137 |

Le brief annonçait environ 88 occurrences. Ni l'un ni l'autre des relevés ne redonne ce nombre, et sa méthode de comptage n'est pas connue. Les 137 sont classés ci-dessous ou en annexe.

## A. Vrais manques, classés par impact joueur

« Divergence PC ? » indique si le traitement demande une décision de divergence PC marquée `// FLAG PC-platform leaf:`.

| # | Emplacement | Verdict | Preuve | Effort | Divergence PC ? |
|---|---|---|---|---|---|
| 1 | `GameState/ModeManager/GameModes/BrnFaceOffMode.h:15` | **Vrai manque, joueur.** `Start`, `PreWorldUpdate` et `FillInGameModeSpecificResults` manquent ; le mode retombe sur la base. | `hasbody` : aucune définition. ARTIST `0x82330440` (139 lignes d'asm), `0x82330670` (2), `0x82315CC0` (32). | Moyen | Non |
| 2 | `Sound/Global/BrnHUDEffect.cpp:444` (commentaire sur `UpdateSlipStreaming`) | **Vrai manque, joueur.** Aucun son de slipstream. La bannière `:417-420` est périmée pour les quatre autres fonctions qu'elle dit absentes (corps `:578` à `:743`). | `hasbody` : aucune définition. ARTIST `0x82701BA8` (255 lignes). | Moyen | Non |
| 3 | `GameState/ModeManager/GameModes/BrnOnlineRaceMode.h:13`, `BrnOnlineRoadRageMode.h:12` | **Vrai manque sur ce commit, online.** Déjà traité sur la branche de la session 2 (voir section E). | `hasbody` sur ce commit : aucune définition. ARTIST `0x82338EB8` (358), `0x823394A0` (305). | Moyen | Non |
| 4 | `Gui/Flow/HUD/States/BrnRaceMainHudState.cpp:1153` | **Vrai manque d'alimentation.** `RoadRuleShotComponent::SetupComponent` a un corps, mais le bras est parqué tant que `GuiCache_RoadRuleShotPending` n'est pas réel : les champs `+0xAC50/58/59/5B` restent dans `mPad_AC4C`. | Commentaire du site, `Gui/BrnGuiCache.h:2189`. Asm non relu. | Moyen | Non |
| 5 | `Network/Managers/BrnNetworkAggressiveDrivingManager.cpp:884` | **Vrai manque, raison périmée.** L'événement GUI 483 n'est jamais posté ; son type existe pourtant (`Gui/BrnGuiEventTypeDefs.h:2511`). | Lecture du corps ; adresse ARTIST non relue. | Faible | Non |
| 6 | `Network/Managers/BrnNetworkAggressiveDrivingManager.cpp:644` | **Vrai manque partiel, online.** La réinitialisation du menu est modélisée par un simple booléen. | Commentaire et corps. | Moyen | Non |
| 7 | `Game/BrnGameModule.cpp:2303` | **Vrai manque, directeur.** La branche score de `BridgeGameStateToDirector` est absente : la destination reste opaque. | ARTIST `0x823CD170` cité sur le site, non relu ici. | Moyen | Non |
| 8 | `Resource/BrnGameDataModule.cpp:2217`, `:2272`, `:2274`, `:2324`, `:2326`, `:2333`, `:2342`, `:2344` | **Vrais bras différés, atteignabilité non établie.** `DeferredGameDataRequest` libère le slot sans réponse. Le GET `TRK_PVS_` est différé alors que son handler existe (`:3366`). | ARTIST `ProcessUnloadGameDataEvent` `0x826733F8` appelle ces handlers (`0x82670F50`, `0x82670E40`, `0x826712A0`, `0x82671420`). Dans l'arbre, seul `World/BrnBaseStreamer.cpp` poste des `UnloadGameDataEvent`. | Faible à moyen | Non |
| 9 | `Effects/EffectsModule.cpp:4919`, `:4925` | **Vrai manque, éditeur de développement.** `JunkyardVfxStart/Stop` se contentent de journaliser. | ARTIST `0x82291AE8`, `0x82292028`, cités sur le site. | Moyen | Non |
| 10 | `Effects/Particles/ParticleModule_Lifecycle.cpp:323` | **Vrai manque, profilage seulement.** `LionPerfMon::Construct` a un corps mais n'est pas appelé : la classe est locale à son TU. | `Effects/Particles/LionPerfMon.cpp:108`. | Faible | Non |
| 11 | `World/EntityModules/RaceCarEntityModule/BrnRaceCarEntityModuleIO.h:247` | **Vrai manque, sans effet observé.** `PlayerVehicleControls::Construct` n'a pas de corps et le seed de `+496` manque. `Camera::Construct` n'a pas été recherché. | `hasbody`. | Faible | Non |
| 12 | `Gui/Flow/Screen/Components/BrnGuiNetworkPlayerStats.h:100` | **Vrai manque, UI online.** `SetPlayerImageIndex` n'a pas de corps (`SetInfo` en a un). | `hasbody`. | Faible | Non |

### Vrais écarts sans impact joueur, à laisser en l'état

| Emplacement | Verdict | Preuve |
|---|---|---|
| `Director/Camera/Behaviours/BrnBehaviourGameplayBumper.h:170` | `SetupTweaker` absent ; le no-op de la base s'applique (réglage de debug). | `hasbody` |
| `Physics/PropManager/PropPhysics/BrnPropInstance.h:93` | `PropInstance::Construct/Prepare` absents ; les stores sont écrits dans l'appelant. | `hasbody`, commentaire du site |
| `Gui/Flow/HUD/States/BrnRaceMainHudState.cpp:3045` | `EventInfoComponent::HandleTrigger` absent ; le commentaire indique un corps console vide. | `hasbody` ; vide non revérifié dans l'asm |
| `Gui/Flow/Screen/States/BrnCrashNavMap.h:201` | `UpdateGuiCache` et `SetMapPanelState` : le commentaire indique aucun symbole X360. Ne rien inventer. | `hasbody` ; commentaire du site |
| `Physics/PropManager/BrnPropManager.h:285` | Seul le nom d'une constante manque ; la valeur (-1000.0) est retrouvée. | Commentaire du site |
| `AttribSys/Generated/classes/iceanim.cpp:45` | Comparaison sur 32 bits au lieu de 64, dans un assert de diagnostic uniquement. | Commentaire du site |
| `World/EntityModules/RaceCarEntityModule/BrnRaceCarEntityModule.cpp:4784` | Action 222 : le commentaire indique aucun producteur dans ARTIST. | Commentaire du site |
| `GameState/ModeManager/Scoring/BrnScoringSystem.h:143` | Enum logé ici : le fichier d'origine `BrnScoringSystemMedals.h` n'existe pas. Dette de forme. | Fichier absent |

## B. Points prioritaires du brief

| Emplacement | Verdict | Preuve |
|---|---|---|
| `Graphics/BrnRendererModule.cpp:143`, `:3030` (`EndRenderAntiAliased`) | **Périmé.** Corps `:3696` ; appel `:6721`. | ARTIST `0x82408B00` |
| `Graphics/BrnRendererModule.cpp:5566` (rendu direct au back buffer) | **Périmé.** `BeginRenderAntiAliased` est appelé `:6380` ; le composite réel suit. | Lecture de `Render` |
| `Graphics/BrnRendererModule.cpp:4736` (pas de masque stencil) | **Périmé.** `PCStampMotionBlurMask` est appelé `:6548`. Le masque passe par le canal alpha, car D3D9 ne peut pas échantillonner le stencil : c'est une divergence PC déjà en place. | Lecture du site |
| `Physics/VehicleManager/VehiclePhysics/VehiclePhysics.h:872` (« LOUD TRAP ») | **Périmé.** `Engine::Update` : `Engine.cpp:396`, monté (`.bat:2025`), appelé `VehiclePhysics.cpp:7031`. | `hasbody`, `.bat` |
| `Physics/PropManager/BrnPropManager.cpp:819` (contacts prop/monde) | **Périmé.** Corps présents, appel `:6506`, fichier monté (`.bat:2374`). | `hasbody` |
| `Game/BrnGameModule.cpp:2973` | **Périmé.** `BrnCarSelectManager.cpp` est monté (`.bat:2885`) et poste l'action 73 (`:419`, `:446`). | `.bat`, lecture |
| `GameFlowController/TopLevel/BrnGameMainFlowStates.cpp:582` | **Périmé.** `ProcessCreateEvents` a un corps et est appelé. | `Physics/VehicleManager/BrnVehicleManager_MaintenanceEvents.cpp:207` |
| `Director/Arbitrator/States/BrnArbStateCarSelect.cpp:66` | **Périmé pour le montage** (`.bat:4058`). L'avertissement `ShotReference` du même bloc n'a **pas** été revérifié. | `.bat` |
| `World/EntityModules/PropEntityModule/BrnPropEntityModule_Streaming.cpp:479` | **Pas un manque.** « Still missing » désigne les zones restant à charger. | Lecture |
| `GameState/BrnGameStateModuleIO.cpp:618` | **Périmé.** Les quatre entrées de la liste sont marquées faites. | Lecture |
| `Gui/BrnGuiCache.cpp:3844` | **Périmé.** Écriture `:270` ; `Gui/BrnGuiModule.cpp:645` passe `&mGuiTracker`. Les gardes PC peuvent être réexaminées. | Lecture, asm `0x82505934` cité sur le site |

**Faux signalement trouvé :** `GameState/Progression/BrnProfile.cpp:1954` annonçait une discordance de signature. L'asm montre deux CgsID de 64 bits à `0x82359C90` (`r4` et `r5`), et `EnterJunkyard` passe `ldx r5` puis `mr r4, r5` à `0x823986AC`. Le renvoi avec base == choisi est donc exact.

## C. Audio : les 15 points Tier 1 de `AUDIT_2026-08-25.md`

Bilan : 10 corrigés, 1 devenu sans objet, 4 corrigés avec un reste à traiter. Chemins relatifs à `b5-decomp/src/`, avec `S = GameShared/GameClasses/Sound`.

| # | Point | État | Fichier:ligne actuel |
|---|---|---|---|
| 1 | Offsets guest dans `CgsVoice` | Corrigé : accès par nom. | `S/Logic/CgsVoice.cpp:27`, `:56` |
| 2 | ODR `SndPlayer1_CgsStreamMod` | Corrigé : une seule définition, dans un en-tête partagé. | `S/Playback/Plugins/Streaming/internal/sndplayer1shared.h:64` |
| 3 | Sous-objet `+0x4C90` | Corrigé : passage par le type concret. | `GameSource/Sound/Module/LogicModule/BrnStateManager.cpp:134` |
| 4 | Adresses X360 dans `mpVtable` | Corrigé : plus aucune occurrence. | `GameSource/Sound/BrnDebugComponent.cpp` |
| 5 | Faux `rw::Resource` | Corrigé. **Reste :** `VoiceHierarchyNode` est toujours local au TU, sans en-tête. | `S/Logic/CgsVoiceHierarchy.cpp:54`, `:78` |
| 6 | `FixUp` SNR sur 64 bits | Corrigé d'après le commentaire, qui annonce un champ de la largeur d'un pointeur sur PC. **Reste :** le format produit par le porteur n'a pas été confirmé. | `S/Playback/RWAC/CgsSnrResourceType.cpp:29` |
| 7 | Faux `SplicerFactory` | Corrigé. | `S/Playback/Splicer/CgsSplicerFactory.cpp:60` |
| 8 | `SelectBin` | Corrigé. La table n'a qu'une entrée d'après l'asm (`cmplwi r10, 1` à `0x826A05CC`) : le remède de l'audit, qui parlait d'une table à récupérer, ne s'applique pas. | `GameSource/Sound/Collision/BrnCollisionStateManager.cpp:3131` |
| 9 | `baseTypeInfo` à 0 | Corrigé. | `GameSource/Sound/Module/LogicModule/BrnEmitterStateManager.cpp:157` |
| 10 | Faux `DataPoint` | Corrigé. | `S/Logic/CgsMicrophone.h:5`, `:120` |
| 11 | Détails NFSMix/Nicotine | Trois sur quatre corrigés. **Reste :** la borne de 66 est gardée mais sans ancrage dans l'asm. | `SDKs/EATech/include/NFSMix/NFSMixMapState.cpp:65`, `:213` ; `SDKs/EATech/include/Nicotine/IDynamicMixer.cpp:122` ; `SDKs/EATech/include/Nicotine/SnapshotMixer.cpp:327` |
| 12 | Corps dans `AptRenderLinkStubs` | Corrigé : ce fichier n'existe plus et les corps sont à leur place. | `SDKs/EATech/include/Nicotine/SnapshotMixer.cpp`, `SDKs/EATech/include/NFSMix/NFSMixMap.cpp` |
| 13 | Docs périmées | Largement corrigé. **Reste :** une mention « out of the build ». | `S/Logic/CgsStateManager.cpp:451` |
| 14 | `StreamHeadersPC::Preload` | Sans objet : plus aucune occurrence de `StreamHeadersPC` ni de `Preload` dans ce module. | `GameSource/Sound/Module/` |
| 15 | Pas de 16 octets en dur | Corrigé : type complet, taille vérifiée par `static_assert`. | `SharedClasses/Sound/World/BrnStaticSoundMap.cpp:87`, `BrnStaticSoundMap.h:55` |

## D. À faire ensuite : les 10 meilleurs candidats

Ordre : impact joueur d'abord, puis effort.

1. **`FaceOffMode`** : `Start`, `PreWorldUpdate`, `FillInGameModeSpecificResults` (`0x82330440`, `0x82330670`, `0x82315CC0`). La branche de la session 4 n'a aucun commit à l'heure du relevé.
2. **`HUDEffect::UpdateSlipStreaming`** (`0x82701BA8`). La branche de la session 1 n'a aucun commit à l'heure du relevé.
3. **Revue et fusion de `OnlineRaceMode::Start` et `OnlineRoadRageMode::Start`**, déjà reconstruits sur la branche de la session 2.
4. **`RoadRuleShotComponent`** : typer `mPad_AC4C`, puis rétablir le bras parqué (`BrnRaceMainHudState.cpp:1153`).
5. **`BrnArbStateCarSelect` : vérifier `ShotReference`.** Le TU est monté : si l'avertissement tient encore, ce n'est plus un défaut latent mais un défaut actif sur les plans caméra de la sélection de voiture.
6. **Bridge score du directeur** (`BrnGameModule.cpp:2303`, `0x823CD170`) : typer la zone de l'input buffer, puis écrire la branche.
7. **Déchargements de `GameDataModule`** : établir qui les poste sur console, puis reconstruire `0x82670F50`, `0x82670E40`, `0x826712A0`, `0x82671420`. Brancher au passage le GET `TRK_PVS_` sur son handler existant.
8. **Événement GUI 483** (`BrnNetworkAggressiveDrivingManager.cpp:884`) : petit correctif, le type existe.
9. **`GuiCache` : réexaminer les gardes `mpGuiTracker`** (`BrnGuiCache.cpp:3844`), devenues inutiles si le pointeur est toujours lié. Ce sont des ajouts PC absents de la console.
10. **Reliquats audio** : ancrer la borne de 66 dans l'asm (`SnapshotMixer.cpp:327`), loger `VoiceHierarchyNode` dans un en-tête, confirmer le format SNR du porteur.

**Décision de divergence PC à prendre :** aucune pour ces candidats. Deux divergences déjà en place méritent seulement une relecture : le masque de motion blur dans le canal alpha, et la position du flare solaire (`BrnRendererModule.cpp:6681`, bloc « THE FLARE STAYS WHERE IT IS »).

## E. Sujets des autres sessions : signalés, non retravaillés

Relevé des branches b5 à la rédaction de ce rapport (l'état peut avoir changé depuis) :

| Session | Sujet | Branche | Commits au-dessus de `3ae8053b5` |
|---|---|---|---|
| 1 | `UpdateSlipStreaming` | `claude/night-1-slipstream-d69bd6` | 0 |
| 2 | `Start` des modes online | `claude/night-2-online-modes-bf4a2c` | 1 (`a189f4863`) |
| 4 | Face Off | `claude/night-4-faceoff-ec5d2b` | 0 |
| 5 | Petits manques audio | `claude/night-5-audio-small-c5584c` | 0 |
| 6 | Interface | `claude/night-6-ui-gaps-186e7a` | 0 |
| 7 | Sweep | `claude/night-7-silent-sweep-66876e` | 0 |

Le commit `a189f4863` n'a pas été relu. Je n'ai pas modifié les commentaires des fichiers qu'une de ces sessions pourrait reprendre : `BrnHUDEffect.cpp`, `BrnFaceOffMode.h`, `BrnOnlineRaceMode.h`, `BrnOnlineRoadRageMode.h`.

## F. Annexe : commentaires périmés, ou sans manque

Ces occurrences ont été tranchées en lisant le contexte du commentaire, complété par `hasbody` ou une recherche de fichier lorsque indiqué. L'asm n'a pas été relu pour elles.

**Périmés : le corps ou le type annoncé comme absent existe désormais.**

| Emplacement (ligne du relevé initial, avant `025631d0a`) | Preuve |
|---|---|
| `Physics/PropManager/BrnPropManager.cpp:7714` | Globals définis dans le fichier (`KVF_LEAN_PROP_LERP_SPEED` `:378`) ; fichier monté |
| `Game/BrnGameModule.cpp:1806` | `Game/GameBridgeGUIToX_wBT_01.cpp:66`, appel `BrnGameMainFlowStates.cpp:676` |
| `GameState/Progression/BrnProgressionManager.h:986` | `UpdatePlayerMedals` a un corps. Le seam reste, pour une autre raison (`BrnProgressionManager.cpp:352`) |
| `GameState/StreetData/BrnGameStateStreetManager_Prepare.cpp:23` | `GameState/BrnGameStateModule.cpp:335` |
| `World/EntityModules/RaceCarEntityModule/BrnActiveRaceCar.h:1109` | `BrnActiveRaceCar.cpp:2518` |
| `World/EntityModules/RaceCarEntityModule/BrnRaceCarEntityModule.cpp:8195` | Appel présent juste après |
| `Resource/BrnGameDataModule.cpp:737` | `KB_PC_ATTRIB_SCHEMA_FILES = true` ; branche `RegisterSchema` présente |
| `Graphics/PostFx/BrnPostFx.cpp:527` | `SetBloom` et `SetDepthOfField` sont appelés depuis `BrnRendererModule.cpp` |
| `Graphics/PostFx/BrnPostFxShader.cpp:53` | Composite actif (`BRN_POSTFX_COMPOSITE_AVAILABLE` à 1) |
| `GameShared/GameClasses/Sound/Logic/CgsStateManager.cpp:80` | Constructeur `ObjectPool()` présent (`CgsObjectPool.h:23`) ; effet sur le remplissage du pool non vérifié |
| `Physics/DeformationManager/DeformationPhysics/BrnDeformableObject.h:680` | Les TU cités sont montés (`.bat:2230`, `:2267`) ; le nom du champ reste à revoir |
| `Physics/PhysicsUtilities/ExternalPhysicsBody_ReadPropertiesFromRenderware.cpp:21` | `BrnPhysicalBodyPart.cpp` est monté (`.bat:2271`) |
| `World/EntityModules/TrafficEntityModule/BrnTrafficEntityModule.cpp:3880` | `PreSceneUpdate` a un corps |
| `World/AI/BrnAIModule_Drive.cpp:143` | `BRNAI_AIWAVE_A3_LANDED` vaut 1 |
| `World/AI/BrnAIDriver.h:68` | Les deux gates valent 1 (`BrnRacingLineGenerator.h:85`, `:88`) |
| `Gui/BrnChallengeListComponent.h:59` | `HighlightPrevious/Next` ont un corps |
| `Gui/Flow/Screen/BrnScreenFlow.cpp:139` | `BrnBaseFlow::PrintSingleSize` a un corps |
| `Gui/Flow/Permanent/Components/BrnEATraxInGameComponent.cpp:39`, `Gui/Flow/Screen/States/BrnCrashNavColourCalibrate.cpp:66` | `BrnGuiEventTypeDefs.h` existe ; la présence des types précis n'a pas été vérifiée |
| `Gui/BrnGuiMovieManager.cpp:23` | Aucun `[STUB]` restant dans le fichier |
| `Gui/Flow/HUD/States/BrnFBurnMainHudState.cpp:33`, `:211`, `.h:35` | Aucun appel à `LogDeferredComponent` dans ce TU |
| `GameState/ModeManager/GameModes/BrnGameMode.cpp:20` | `GameState/BrnGameStateSharedIO.h:179` |
| `World/EntityModules/RaceCarEntityModule/Boost/BrnBoostStrategy.h:86` | `GameState/BrnGameActions.h` définit `CompletedStuntAction` |
| `World/BrnBaseStreamer.h:15`, `:38` | `Resource/SharedIO/BrnGameDataEvents.h`, `World/BrnWorldGraphicsStreamer.h` |
| `Replays/BrnReplayRequestInterface.h:36` | `Replays/BrnReplayBaseSerialiser.h` existe |
| `World/AI/SharedIO/BrnAICarOutputInterface.h:26`, `:49` | `World/AI/Route/BrnRoute.h` existe ; la tranche reste une dette de forme |
| `World/EntityModules/RaceCarEntityModule/BrnRaceCarStreamer.h:47` | `SharedClasses/World/BrnVehicleGraphicsSpec.h` existe |
| `World/EntityModules/RaceCarEntityModule/NearMisses/BrnNearMissManager.h:23` | `Update` et `SetSpeed` ont un corps |
| `Physics/VehicleManager/SharedIO/BrnVehicleOutputInterface.h:17`, `:219` | `VariableEventQueue` est utilisé ailleurs dans l'arbre ; la mémoire opaque reste une dette de forme |
| `GameState/ModeManager/GameModes/BrnGameModeParams.h:74` | Bannière ancienne ; le remplacement des stubs n'a pas été vérifié un par un |
| `Director/DirectorModule/BrnDirectorModuleIO.h:93`, `World/AI/BrnAIDebugComponent.h:28`, `World/DebugComponents/BrnPVSDebugComponent.h:37`, `World/AI/BrnAIAggression.h:12` | Mêmes bannières anciennes de type ; non vérifiées une par une, à relire sans urgence |

**Sans manque : récit d'un travail terminé, journal d'un diagnostic, note de mesure, ou « until then » au sens ordinaire.**

- **Director :** `BrnArbStateCrashing.cpp:768`, `BrnArbStateRoaming.cpp:369`, `BrnMainDirector.cpp:4187`, `BrnBehaviourAftertouchCrash.cpp:15`, `BrnBehaviourSpirallingDeathcam.h:24`, `BrnCollisionPolicy.h:423`, `:595`, `BrnDirectorEffectTrigger.h:97`.
- **Effects et Game :** `ParticleModule_SparkEvents.cpp:18`, `GameBridgeControllerToX.cpp:124`.
- **GameState :** `BrnGameStateModule.h:1930`, `BrnGameStateModuleIO.cpp:476`, `:511`, `:542`, `BrnGameStateModuleIO.h:798`, `BrnCrashMode.h:15`, `BrnFaceOffMode.h:28`, `BrnPursuitMode.h:17`, `BrnRoadRageMode.h:32`, `BrnGameStateToGuiIOInterfaces.cpp:8`, `:43`.
- **Graphics :** `BrnRendererMemory.cpp:316`, `BrnRendererModule.cpp:3848`, `:5919`.
- **Gui :** `BrnGuiCache.cpp:1759`, `BrnGuiDebugComponent.cpp:135`, `BrnInGameMessagesComponent.cpp:535`.
- **Network** (notes de layout, sans effet à l'exécution) : `BrnNetworkAggressiveDrivingManager.h:129`, `BrnNetworkImageManager.h:277`, `BrnNetworkLaunchManager.cpp:456`, `BrnNetworkLiveRevengeManager.h:250`, `BrnNetworkMarkedManManager.h:94`, `BrnNetworkSelectedRoutesManager.h:130`, `BrnNetworkStandingsManager.h:214`.
- **Physics :** `BrnDeformationManager_Output.cpp:15`, `ExternallySimulatedBody.h:99`, `ExternalPhysicsBody.cpp:1375`, `BrnPropManager.h:274`, `BrnPhysicalTrafficManager.h:66`, `:379`, `:487`, `BrnVehicleManager.h:1860`, `:2034`, `BrnVehicleManager_MaintenanceEvents.cpp:121`, `BrnVehicleManager_RaceCarTrafficContact.cpp:187`, `BrnVehicleManager_ValidateRaceCarWorldContact.cpp:257`, `BrnVehicleManager_WriteOutVehicleStats.cpp:239`, `BrnArticulatedJointPool.cpp:371`, `VehiclePhysics.cpp:8834`.
- **World et Resource :** `BrnGameDataModule.h:157` (décrit la section A, ligne 8), `BrnAIAggression.cpp:90`, `BrnAICar.h:9`, `BrnAIModule.h:480`, `BrnAIModule_Events.cpp:1304`, `BrnRacingLineGenerator.cpp:156`, `BrnRacingLineGenerator_Curve.cpp:60`, `BrnRacingLineGenerator_Extrapolate.cpp:102`, `WorldBridgePropModule.cpp:555`, `BrnEntityTypes.h:8`, `BrnPlaceOnTrackManager.cpp:47`, `:497`, `BrnActiveRaceCar.cpp:3602`, `BrnRaceCarEntityModule.cpp:1813`, `:3099`, `BrnRaceCarEntityModule.h:1402`, `BrnWorldEntityModule.h:344`.

Deux de ces notes restent à relire sans urgence, leur classement étant moins sûr : `BrnAIModule.h:480` (valeurs de repos de cinq drapeaux) et `WorldBridgePropModule.cpp:555` (moniteur CPU non modélisé). `EffectsModule.h:474` renvoie à la section A, ligne 9.

## G. Décisions prises

- **Commentaires :** corrections dans un commit b5 séparé (`025631d0a`), sous forme de notes insérées à côté du texte existant plutôt que de réécritures, pour garder l'historique lisible. Le diff a été contrôlé automatiquement : aucune ligne hors commentaire.
- **Numéros de ligne :** ces notes décalent les numéros de ligne des macros `__LINE__` dans les fichiers concernés, sans effet sur la logique.
- **Non corrigés :** les commentaires périmés hors liste prioritaire qui exigeaient un jugement, et ceux des fichiers des autres sessions.
- **Risque de fusion :** si la session 6 modifie `BrnGuiCache.cpp` près des mêmes lignes, un conflit mineur de commentaires est possible.
