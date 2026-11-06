# Son haché à l'ouverture du menu de pause en course online — 2026-11-05

## Résolu par le signal audio de pause du HUD (2026-11-05, 06 h 45)

Le défaut ne venait pas du son, mais du HUD. Avant `PAUSE`, la console envoie `OutputGuiEvent<GuiAudioEvent>` {type 2, action 0, info -1} (`0x824807C0` pour `RaceMainHudState`, `0x82481178` pour `FBurnMainHudState`), et notre arbre ne le faisait pas. La session « Audit de décompilation » l'a ajouté : b5 `7c3f3189d`, sur `work/polish-20261105`.

- **Côté son :** GUI 456 devient le message 5 (`SoundLogicModule::ProcessGuiEvents`), puis `HUDEffect::Notify` (`0x826F5F68`). Le type 2 joue un splice fixe de la banque de présentation : 1 à l'ouverture (action 0), 2 à la fermeture (action 1), sur l'entrée de mixer 3. Il réclame aussi l'entrée HUD du mixer (`SetMixerInputValue(0, 0x7FFF)`).
- **Mesure, run `20261105_064351`** (`7c3f3189d` appliqué en cherry-pick sur cette branche, puis retiré pour ne pas dupliquer le commit) :
  - `[hud-sound-msg] type=2 action=0 ... -> PLAY splice=1` à l'ouverture du menu, et `action=1 ... splice=2` à la fermeture ;
  - **0 seconde battante pendant la pause**, contre 6 à 9 sans le signal ; une seule au démarrage (43 s) ;
  - niveau moyen sous le menu d'environ -14,5 dB, contre environ -19,5 dB sans le signal : le son de pause recouvre le ralenti du moteur.
- **Limites :** un seul run, sur une machine chargée (au moins 2 autres instances du jeu). Le moteur au ralenti reste présent sous le menu, mais il n'est plus au premier plan, comme sur console.

## Mise à jour : c'est le moteur au ralenti (2026-11-05, 03 h 15)

**Conclusion révisée :** le battement de 40 ms est le régime du moteur de la voiture du joueur. Le run `20261105_031200` (`BP_PAUSE_REVS=1` : 6 s d'accélération juste avant la pause) le montre : la période de l'enveloppe suit le régime. Elle est de 20 à 30 ms pendant l'accélération, puis s'allonge (20, 30, 35 ms) quand la voiture ralentit, et se fixe à 40 ms au ralenti. Le nombre de secondes battantes tombe de 6 à 9 à 2.

- **Pourquoi on l'entend surtout dans le menu :** en online, la simulation continue sous la pause (pas d'action 86, pas de bit `0x1` côté son). La caméra de pause (`BehaviourRoadRunner`, `[RoadRunner] lane seated`, `[flyby]`) tourne près de la voiture, qui tourne au ralenti, et le niveau moyen du mix ne baisse pas.
- **Ce que la logique son voit pendant la pause** (témoin `[snd-frame]`, b5 `1848b23d8`, run `20261105_030611`) : un pas de simulation constant de 0,016667, une échelle de temps de 1, aucun état « temps d'impact » ou « ralenti », aucune bascule, aucune pause de simulation. Le bit `0x800` (stall du streaming) n'est levé que pendant environ 54 images, d'un bloc, à l'ouverture du menu. **Écarté :** une bascule pause/stall ou ralenti à chaque image.
- **`GinsuPause`** (`BrnDualGinsuEffect.cpp:984`, `:1019`) est toujours envoyé à 0. Écarté : le moteur figé sur un grain.
- **Encore ouvert :**
  - est-ce que la console laisse elle aussi le moteur à ce niveau sous le menu en online ? Il faudrait l'asm de ce que l'écran de pause envoie au son, ou un enregistrement console ;
  - est-ce que les remplissages trop lents du callback XAudio2 (sujet à part, voir plus bas) rendent ce ralenti plus « haché » que sur console.

Rien ne justifie un correctif à ce stade : le moteur au ralenti est un son légitime.


**Conclusion :** le battement est reproduit et mesuré. Il ne vient d'aucun commit son de la nuit, et ce n'est ni une coupure de la sortie ni un trou de silence dans le mix. Pendant le menu de pause, le mix est modulé en amplitude avec une période de 40 ms (environ 25 Hz). La même période existe, plus faible, hors de la pause. La cause n'est pas encore établie.

À part, et sans lien démontré avec la pause : le callback XAudio2 met régulièrement plus de temps à produire un buffer que la marge disponible. Ça ne se voit pas dans la capture, mais ça doit s'entendre comme des clics, partout.

- **Branche :** worktree `.claude/worktrees/night-2-online-modes-bf4a2c`, b5 `claude/night-2-online-modes-bf4a2c` à `0743b1fa7`, au-dessus de `work/integration-20261104` (`511e8995e`).
- **Machine pendant les mesures :** 4 instances du jeu (2 de la session « Audit de décompilation » et ma paire sur les slots 12 et 22), builds en `BRN_EXE_JOBS=4`. Les durées du callback en sont gonflées.

## Méthode

- **Case :** `tools/tests/cases/net_lan_pause_sound.ps1`. C'est la course online du mode 10 de `net_lan_start_mode`. Le `MenuScript` de l'hôte attend le `mode-start` d'OnlineRace et son `E_GMS_IN_PROGRESS`, attend 5 s, appuie sur Start (action 46 : `ENTER 'ON_PAUSE'`, puis `GUI 191 activate=0`, puis l'événement de jeu 93 avec la valeur 1), garde le menu 8 s, puis rappuie sur Start.
- **Capture :** `BRN_AUDIO_CAPTURE` écrit le mix soumis de chaque instance dans `scratch/audio/net_lan_pause_sound_<Role>.wav`, avant la mise en sourdine du harness, qui ne touche que le mastering voice. L'invité n'ouvre pas la pause et sert de témoin.
- **Mesure du battement :** enveloppe en dB par fenêtres de 10 ms. Une seconde est notée « battante » si l'enveloppe s'autocorrèle au-dessus de 0,7 à un décalage de 30 à 50 ms, avec plus de 15 sauts de 6 dB. Scripts dans le scratchpad de la session : `flutter.py`, `audio_gating.py`, `cb_stats.py`.
- **Témoin de timing (b5 `0743b1fa7`, `[FLAG PC witness]`) :** la ligne `[audio-output] prelimit` donne désormais `produce-max-us` (le remplissage `OnBufferEnd` le plus long), `gap-max-us` (le plus long écart entre deux remplissages) et `slow` (le nombre de remplissages plus longs qu'un buffer de 256 images, 5,3 ms). Le témoin n'est actif que si une variable de capture est posée.

## Résultats

| Build | Run | Secondes battantes (hôte) | Où |
|---|---|---|---|
| intégration + témoin | `20261105_023615` | non mesuré, la WAV a été écrasée par le run suivant | — |
| sans `d12539503` | `20261105_024210` | 10 | 123 à 131 s, la pause, plus une à 51 s |
| sans `d302181d6` | `20261105_024837` | 10 | 140 à 147 s, la pause, plus 52 et 130 s |
| sans les 7 commits son de la nuit (`b34cd6bba`, `c69c8ca80`, `706966542`, `065dbcaac`, `c7940cea0`, `d12539503`, `d302181d6`) | `20261105_025425` | 8 | 129 à 133 s, la pause, plus 47, 49 et 57 s au boot |
| invité (témoin sans pause), dans chaque run | — | 0 ou 1 | — |

- **Pas un commit de la nuit :** le battement reste, au même endroit, quand on retire `d12539503`, `d302181d6`, ou les sept commits son ensemble. Il existait donc avant la nuit.
- **Pas un trou dans le mix :** aucun bloc de 256 images silencieux (crête < 64) entre 115 et 145 s de la WAV sans les commits son. La sortie est continue.
- **Une modulation :** pendant la pause, la corrélation à 40 ms monte à 0,79 à 0,90, avec 16 à 30 sauts de 6 dB par seconde. Hors pause, on garde la même période, plus faible (0,4 à 0,7, 10 à 20 sauts). Le niveau moyen bouge peu (de 1 à 2 dB).
- **Callback trop lent, mais pas propre à la pause :** côté hôte du run `023615`, on compte en moyenne environ 8 remplissages trop longs par demi-seconde, avec un maximum de 15 à 20 ms, avant, pendant et après la pause. Avec 3 buffers en file (16 ms de latence), un remplissage de plus d'environ 10,7 ms vide la voix. Ces trous ne figurent pas dans la WAV, qui ne garde que ce qui est produit. Ils doivent donner des clics, en jeu comme dans le menu.

## Pistes non vérifiées

1. **Le moteur au ralenti.** 25 Hz, c'est la fréquence d'allumage d'un 4 cylindres vers 750 tr/min. La voiture est arrêtée sur la grille et la même période existe hors pause. Le menu pourrait faire ressortir le ralenti : caméra de survol (`[flyby]`) proche de la voiture, autre mix, simulation qui continue en online. Pour trancher, il faut séparer le bus moteur du reste (`BRN_AUDIO_CAPTURE_ENGINE`, `BRN_ENGINE_MIX_DIAG`) ou faire le même essai voiture en mouvement.
2. **Le stall de streaming en online.** Pendant la pause, l'ensemble de mise à jour alterne entre `0x888` et `0x88`. Le bit `0x800` est `mbStreamingStalled` (`BrnGameModule.cpp:1339`). En online, un stall demandé par le monde lève ce bit sans arrêter la simulation et sans envoyer `PlayerPauseStateChanged`. Aucun lecteur de `0x800` n'a été trouvé côté son, donc aucun lien n'est établi.
3. **Le callback lent.** À mesurer seul sur la machine (une paire, rien d'autre), puis entre l'attente de `ExecuteCommandsLock` et `Dac::Mix` dans `DacOutputPC::EngineFill`. Si l'attente du verrou domine, le thread du jeu tient le verrou trop longtemps.

Aucune divergence PC ni aucun correctif n'est proposé tant qu'une de ces pistes n'est pas prouvée.
