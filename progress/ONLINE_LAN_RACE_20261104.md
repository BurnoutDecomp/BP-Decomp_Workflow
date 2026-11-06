# Course online LAN : de `OnlineLoading` à `IN_PROGRESS` — 2026-11-04/05

**Conclusion :** la course (mode 10), le road rage (mode 11) et le burning home run (mode 13) atteignent `E_GMS_IN_PROGRESS` sur l'hôte et l'invité, sans GUI 281 posté par le harness. Les modes 11 et 13 sont verts. Le mode 10 ne reste rouge que pour un assert de debug pendant le chargement, dont la séquence est identique à la console sur tout ce qui a été vérifié.

- **Branches :** b5 `claude/night-2-online-modes-bf4a2c` (commits `f2259c23e` à `62d4a87f4`), parent `claude/night-2-online-modes-bf4a2c` (`23a5e271` et ce rapport). Rien n'est fusionné dans `work/integration-20261104`, rien n'est poussé.
- **Exe :** `build\game\Burnout_PC.exe` du worktree, construit depuis `62d4a87f4`.

## Chaîne de correctifs

| Commit b5 | Défaut | Preuve |
|---|---|---|
| `f2259c23e` (session 2) | `findInst` faisait correspondre par nom un nœud vivant : le second `ChevronsColour` d'`ON_LOAD` prenait la place du premier, et `OnlineLoading` attendait pour toujours en `LOADING_COMPONENTS`. | `0x82AD9A2C` teste `mbIsDefined` |
| `726778def` | Crash `GetDebugFullName` (`strnlen` sur `0x0000000200000000`) au début de l'intro online. Le bloc `+0x194` d'`ArbStateOnlineRaceIntro` était un POD `{0, 8, 0, 2}` décalé d'un mot, relu comme `BehaviourInterpolate::Parameters` ; sur x64 le nom de debug tombait sur les deux derniers mots. L'appel `SetInterpolationMode` venait d'une mauvaise lecture de ce même chargement du nom. | `Construct` `0x8225AE98` : `+0x194 = 8`, `+0x198 = 0`, `+0x19C = 0`, `+0x1A0 = 2`. Trois sites `SetParameters` (`0x822737F4`, `0x82273970`, `0x82273B10`) sans écriture à `+0x04`. |
| `245a049c2` | Assert `luTeam < 2` en road rage dès qu'une voiture est bleue. | DWARF `:500` : `Time maTotalTimeInTeam[3]`. `UpdateTeamStats` `0x8231F308` indexe sans assert. L'ancien `mTimeAsRunner` à `+0x84` est l'élément `[2]`. |
| `f6d1236a3` | Crash du road rage : lecture de `mbEliminated` sur un `CarData` nul (voir plus bas). Divergence PC validée par l'utilisateur. | `0x823952D4`, `0x8239546C`, `0x82395618` ; `li r3, 0` à `0x8231DD68` |
| `62d4a87f4` | Intro online : handles de rivale indexés par le curseur de plan, que `Prepare` ne remet pas à zéro (débordement dès la deuxième intro) ; fondus pris sur des caméras figées, et à l'envers. | `SetupRivalMovie` `0x8226EC18` ; `Setup(durée, from, to, manager)` = `sub_8224EE58`, sites `0x82273850`, `0x822739E0`, `0x82273B6C` |
| `f44b700ea`, `f1c422b21` | Témoins `[net] opponents`, `[net] above-car`, `[net] scoring-bind`. Bornés, LAN ou harness seulement. | — |

Le case `net_lan_start_mode` (parent `23a5e271`) ne poste plus GUI 281 et n'envoie le lancement qu'une fois.

## Tests, exe du worktree (`62d4a87f4`)

Tous valides : `TITLESTART requested=True ready-observed=True`, aucun VOID.

| Case | Résultat | Run |
|---|---|---|
| `net_lan_start_mode` mode 10 | Rouge, seul échec : ~2150 asserts `Invalid rival position`. `IN_PROGRESS` sur les deux, aucune exception. | `20261105_001050` |
| `net_lan_start_mode` mode 11, `BP_START_LAUNCH_GUI=54` | Vert, `IN_PROGRESS` sur les deux | `20261105_001506` |
| `net_lan_start_mode` mode 13 | Vert, `IN_PROGRESS` sur les deux (rouge sur l'exe assemblé) | `20261105_001910` |
| `net_lan_pair` | Vert | `20261105_002330` |
| `net_lan_see` | Vert | `20261105_002610` |
| `baseline_boot_drive` | Vert | `20261105_002854` |

Les runs sont sous `scratchugtest
uns\` du worktree. Les modes 10 et 11 étaient verts avec le stand-in GUI 281 parce qu'ils s'arrêtaient au `mode-start`. Le mode 13 passe désormais ; l'envoi unique de GUI 56 a pu y contribuer, sans preuve isolée.

## Défaut restant 1 : `Invalid rival position`, mode 10

**Où :** `AboveCarRenderer::UpdateCachedInfoForRival`. La rivale (voiture 1) a la position 8, avec 1 adversaire.

**Pourquoi :** 2148 occurrences tombent pendant `ONLINE_LOADING`, sim en pause (action 86), les 2 dernières juste après la reprise (action 87). Le témoin `scoring-bind` montre que les deux voitures ne sont liées au scoring qu'après la reprise. Tant qu'elles ne le sont pas, le scoring publie la position par défaut de `ClearData` (8), alors que `mabValid` est déjà vrai, car il vient de la liste des voitures en course.

**Vérifié contre la console, sans écart :**
- La boucle online de `RenderComponent` `0x82462A38` a les mêmes conditions.
- La voiture réseau de la grille n'est pas `CONNECTING` (`0x823010A0` : seulement si lobby free-burn et non locale).
- La table de slots est copiée avant le saut de pause (`0x823075F8`).
- `GameStateModule::PostWorldUpdate` saute `ModeManager::PostWorldUpdate` en pause (`0x8238F468`).

**Lecture :** probablement un assert de debug qui partait aussi sur console pendant ce chargement. Non prouvé, et non corrigé. Aucune piste de code n'a été trouvée ; masquer l'assert ou l'exclure du case reviendrait à cacher le symptôme.

## Road rage : lecture `0xD9` — divergence PC appliquée (`f6d1236a3`)

**Où :** `GenerateOnlineBlueTeamEscapingMessage` `0x82395218`, `GenerateOnlineBlueTeamAreBehindYouMessage` `0x823953B0` et `GenerateOnlineLeaderMilestoneMessage` `0x82395548`. Les trois parcourent les 8 index actifs. Pour chacun, ils appellent `GetCarData` const (`sub_8231DCD0`) puis lisent `mbEliminated` (`lbz 0xD9(r3)`) sans tester le retour.

**Pourquoi ça plantait :** ce `GetCarData` renvoie NULL pour un index sans voiture (2 à 7 à deux joueurs, `li r3, 0` à `0x8231DD68`). La console fait la même lecture et n'en meurt manifestement pas ; Windows la refuse.

**Correctif, validé par l'utilisateur :** `// FLAG PC-platform leaf:`. Un index sans voiture se lit « non éliminé », la valeur que la console tire de sa page basse. Les tests suivants (équipe, distance, position) s'appliquent toujours à cet index, comme sur la console.

## Points du handoff refermés

- `SCREEN apt components: 5 of 5 still unloaded` : sans objet. La ligne est émise une fois au boot pour `SaveLoadComponent`, juste avant que ses 5 composants se chargent (`AddNewAptComponent` puis `ONLOAD`). Rien à voir avec l'online.
- Le correctif `findInst` ne fait régresser aucun des cases relancés.

## Après fusion (2026-11-05)

- **Fusion :** b5 `3639c4ac9`, parent `5fc974c9` dans `work/integration-20261104`. `build\game\Burnout_PC.exe` reconstruit. L'exe précédent est gardé dans `build\exe_avant_fusion_night2_20261105`.
- **Cadre POSITION vide en course online :** `EventInfoComponent::UpdateOnlineRace` (`0x824296B0`) n'était qu'un report qui écrivait dans le log. Reconstruit en b5 `e8dee9374`. Le run `20261105_005533` affiche « POSITION 2 / 2 » côté hôte, « 1 / 2 » côté invité, avec la distance.
- **Paires dans le checkout principal :** utiliser `-SlotA 3 -SlotB 4`. `build\game_slots\config.ini` active le serveur en ligne : l'hôte passe alors par le relais, et l'invité, resté en LAN, ne le trouve jamais.

## Clôture (2026-11-05)

- **Assert du mode 10 :** dernier maillon vérifié, `ScoringSystem::WriteDataToOutput` (`0x8232AE98`) publie aussi un `CarScoreData` passé par `ClearData()` (position 8) pour un slot non lié. C'est donc l'assert de debug de la console elle-même. Il est déclaré dans `tools/tests/known_asserts_net_race.txt` : la liste partagée, recopiée telle quelle, plus cette seule famille. Le case vérifie aussi qu'il n'y en a **aucun** après `E_GMS_IN_PROGRESS` du mode testé, ce qui garde aussi l'objectif « la course atteint `IN_PROGRESS` ».
- **GUI 483 :** b5 `511e8995e`.
- **Résultat final, exe fusionné :** `net_lan_start_mode` vert en modes 10 (`20261105_013116`), 11 (`004053`) et 13 (`004511`) ; `net_lan_pair` (`011854`), `net_lan_see` (`011610`) et `baseline_boot_drive` (`013021`) verts. Les runs des modes 11 et 13 précèdent `511e8995e` (envoi réseau inatteignable à deux joueurs) et ont été réévalués avec `-NoRun` sur le case final.

## Non fait

- Aucune fusion dans `work/integration-20261104`.
