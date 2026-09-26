# Vox Animation — studio project

This folder is a self-contained studio for making narrated motion-graphics
explainer videos in the Vox style, driven entirely by the `vox-animation`
skill in `.claude/skills/`.

When the user greets you, asks to start, or says anything about making a
video — invoke the `vox-animation` skill and follow its staged flow
exactly: welcome → topic → settings → voice → brief → style key → scenes →
clips → cut. One stage per message; wait between stages.

Presentation matters here as much as function: follow the skill's Global
UI rules in every message (tables, dividers, no internal/technical
chatter, clean pasteable blocks).

State lives on disk: each video is a folder under `projects/` (pack.md,
clips/, voice/, final.mp4). `EXPLAINER.md` is the one-page intro the user
received with this folder.

This studio writes prompts and generates local audio only. Never submit
paid generations to any platform from here — the user runs the video
prompts in their own generator and brings the clips back.

## Adaptation au dépôt de Franck Monod

- Ce dossier (`11_vox/`) est le studio Vox du dépôt ; le skill est dans `.claude/skills/vox-animation/`
  (`scripts/assemble.sh` s'y trouve). Fiches en français : `styles/vox-collage.md`, `styles/vox-diorama.md`.
- Parler à Franck en français. Narration en français par défaut : voix edge-tts `fr-FR-HenriNeural` ou
  `fr-FR-DeniseNeural`, ou la voix de Franck enregistrée sur la page du studio (proposer les trois).
- Format 9:16 par défaut. Les sous-titres, la musique, les effets et les métriques peuvent reprendre ceux du
  style reportage (`04_montage/BONNES-PRATIQUES.md`, `04_montage/metriques.py`).
- Dépôt public : clips, voix et `final.mp4` restent hors git (copiés dans Drive).
