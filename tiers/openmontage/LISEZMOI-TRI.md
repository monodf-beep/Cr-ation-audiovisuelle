# OpenMontage : copie de travail et tri

Copie de https://github.com/calesthio/OpenMontage, commit `08e2151` (5 septembre 2026),
rangée ici pour choisir ce qu'on reprend dans le studio vidéo. **Rien ici n'est branché
au studio** : c'est une bibliothèque de lecture.

## Ce qui a été changé par rapport à l'original

- **Retirés (trop lourds, inutiles au tri)** : 4 fichiers de démonstration de plus de 1 Mo
  (`assets/signal-from-tomorrow-demo.mp4`, et trois fichiers d'exemple dans
  `.agents/skills/hyperframes-animation/examples/assets/`).
- **Mis à l'écart dans `_consignes-agents-amont/`** : `CLAUDE.md`, `AGENTS.md`, `CODEX.md`,
  `COPILOT.md`, `CURSOR.md`, `.windsurfrules`, `.claude/`, `.cursor/`, `.codex/`. Ces fichiers
  ordonnent à tout assistant de code de suivre le guide d'OpenMontage avant toute réponse ;
  laissés à leur place, ils auraient piloté nos propres sessions dans ce dépôt.
- Aucun fichier de code n'est modifié.

## Licence

AGPL-3.0 (fichier `LICENSE`). Décision du 2 octobre 2026 : on passe outre la contrainte
et on reprend librement. À garder en tête : un code AGPL modifié et utilisé par des
journalistes via notre serveur oblige, en principe, à leur proposer le code source modifié.

## Le tri

Légende : **Reprendre l'idée** = on réécrit le principe dans notre pont ;
**Lire** = utile comme référence ; **Écarter** = pas notre usage.

| Module OpenMontage | Ce qu'il fait | Notre équivalent | Tri |
|---|---|---|---|
| `tools/video/auto_reframe.py` + `tools/analysis/face_tracker.py` | Recadrage qui **suit le visage** dans le temps (lissage, ffmpeg `sendcmd`) | `ops/pont/cadrer.py` : un seul centre de visage par plan | **Reprendre l'idée** (priorité 1) |
| `tools/video/silence_cutter.py` | Coupe ou accélère les silences (`silencedetect`) | Rien | **Reprendre l'idée** (option du plan) |
| `tools/analysis/visual_qa.py` | Contrôle automatique : sous-titres qui cachent un visage, images noires | `revue()` dans `video-rendu.mjs` | **Reprendre l'idée** (sous-titres / visages) |
| `tools/analysis/scene_detect.py` | Repère les changements de plan (PySceneDetect) | Rien | **Reprendre l'idée** pour les longs rushes |
| `tools/audio/audio_mixer.py`, `audio_enhance.py` | Ducking musique sous la voix, normalisation, réduction de bruit | À vérifier dans `video-rendu.mjs` | **Lire**, reprendre ce qui manque |
| `tools/analysis/transcriber.py` | faster-whisper, option WhisperX (qui parle) | `transcrire.py` | **Lire** : seule l'identification des voix est en plus |
| `tools/enhancement/color_grade.py` | LUT et préréglages | LUT + grain dans `video-rendu.mjs` | Écarter (doublon) |
| `tools/subtitle/*`, `remotion_caption_burn.py` | Sous-titres SRT/VTT, mot à mot via Remotion | `video-sous-titres.mjs` (ffmpeg) | Écarter (Remotion a sa propre licence payante au-delà d'une taille d'entreprise) |
| `tools/video/hyperframes_compose.py`, `.agents/skills/hyperframes-*` | Compositions HyperFrames, règles et gabarits | Nos gabarits HyperFrames | **Lire** : idées de transitions et de palettes |
| `lib/checkpoint.py` | Points de validation humaine | Validation du plan et de la sortie | Lire (même principe, déjà chez nous) |
| `tools/cost_tracker.py` | Plafond de dépense, accord avant un nouvel outil payant | Plafonds par projet | **Reprendre l'idée** : demander l'accord avant tout nouveau service payant |
| `pipeline_defs/*.yaml` (talking-head, clip-factory, podcast-repurpose…) | Recettes de production étape par étape | Notre plan + montage JSON | **Lire** : la recette « clip-factory » (un long entretien → plusieurs courts) peut inspirer un format |
| `tools/video/*` (Kling, Veo, Sora, Runway, HeyGen…), `tools/audio/*tts*` | Génération par IA dans le cloud | Higgsfield / fal en option | Écarter (les données partent dans le cloud) |
| `tools/analysis/video_downloader.py` (yt-dlp) | Télécharge des vidéos en ligne | — | Écarter (question de droits) |
| `backlot/`, `ink-theater/`, `remotion-composer/` | Serveur de storyboard local, thème, rendu Remotion | — | Écarter |

## Les principes qu'on reprend

1. **Le cadrage suit la personne** : on échantillonne le visage plusieurs fois par seconde,
   on lisse, et le cadre ne bouge que si le visage sort d'une zone centrale.
2. **Les silences se coupent sur demande** : option du plan, jamais automatique.
3. **La machine se relit** : avant de montrer une version, contrôle des sous-titres sur les
   visages, des noirs, du son trop bas.
4. **Pas de nouveau service payant sans accord** : chaque appel à un outil payant non encore
   utilisé dans le projet demande une validation.
5. **Une recette par format** : un long entretien peut donner plusieurs formats courts,
   chacun validé par un humain.

## Où on en est (2 octobre 2026)

- **Fait** (dépôt du studio, `ops/pont/`) :
  - principe 1, le cadre suit le visage : `cadrer.py` (option `suivi`), `expressionTrajet` dans `video-rendu.mjs` ;
  - principe 3, la relecture automatique : `analyserSortie` et `relectureAuto`, qui repèrent les écrans noirs,
    les silences de plus de 1,5 s, le son trop bas et les sous-titres sur un visage.
    Tests : `ops/pont/tests/test-relecture.mjs`.
- **Déjà là avant** :
  - principe 2, la coupe des silences sur demande : outil `chercher_silences` de Claude au montage ;
  - le son : la musique baisse sous la voix et le volume est égalisé (loudnorm).
- **À faire** :
  - principe 4, un accord avant tout nouveau service payant ;
  - principe 5, une recette par format ;
  - le repérage des changements de plan dans les longs rushes.
- **À vérifier sur de vrais rushes** : le suivi a été testé sur une image qui se déplace,
  pas encore sur un tournage réel.
