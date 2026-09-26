# Bibliothèque de styles et de skills

Un **style** fixe le rendu d'une vidéo (couleurs, typographie, mouvement, son, ton). Un **skill** apprend à Claude
comment fabriquer une vidéo dans ce style, étape par étape (`.claude/skills/<nom>/SKILL.md`, chargé
automatiquement dans les sessions Claude Code ouvertes sur ce dépôt).

La liste est aussi dans l'onglet **Styles et skills** de la bibliothèque du studio
(`/enregistrement/bibliotheque/`), où Franck garde ou écarte un style et peut téléverser le sien
(skill en .zip, fiche en .md ou .pdf, planche de référence en image).

| Style | Skill | Pour quoi | Fiche |
|---|---|---|---|
| Reportage Franck Monod | `reportage-franck` | reportage de terrain vertical, voix libre de Franck, vraies images | [reportage-franck.md](reportage-franck.md) |
| Vox — collage éditorial | `vox-animation` (look `mixed`) | explication animée sans tournage, ton curieux et précis | [vox-collage.md](vox-collage.md) |
| Vox — diorama de papier | `vox-animation` (look `diorama`) | enquête, sujet politique ou grave, ambiance documentaire | [vox-diorama.md](vox-diorama.md) |

Autres skills installés : `hyperframes*` et `media-use` (outil de montage HTML → MP4, utilisés par les deux styles).

## Ajouter un style ou un skill

1. Franck le téléverse dans l'onglet **Styles et skills** (il est copié dans Drive, `bibliotheque/`), ou le
   dépose dans la conversation avec Claude.
2. Claude l'installe dans le dépôt : le skill dans `.claude/skills/<nom>/`, une fiche en français dans `styles/`,
   une ligne dans ce tableau et dans `styles/catalogue.json`. Il vérifie qu'il ne contient ni clé, ni média sous
   licence, ni contenu privé (dépôt public).
