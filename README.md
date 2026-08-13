# Création audiovisuelle

Projets vidéo et contenus visuels.

## Projet en cours — FC CLUSA « CHAMPIONS 26 »

Publicité de présentation du maillot commémoratif du titre R2 LAuRAFoot du FC Cluses.
Un terrain municipal, une nuit d'hiver, des projecteurs. Aucun visage.
Chaîne : script → plans fixes → animation plan par plan → montage.

| Dossier | Contenu |
|---|---|
| `01_script/` | Script, découpage 22 plans sur 36 s, voix off, sound design, déclinaisons |
| `02_prompts/` | Bible de détails du maillot, prompts packshots, prompts terrain |
| `03_etalonnage/` | `grade.py` (recadrage + étalonnage des photos réelles), `filmlook.py` (passe pellicule commune) |
| `04_sources/` | photos réelles du maillot upscalées 4K *(hors dépôt)* |
| `05_plans/` | plans maillot étalonnés *(hors dépôt)* |
| `06_terrain/` | plans terrain générés *(hors dépôt)* |
| `07_film/` | **les 22 plans finaux, après passe pellicule** *(hors dépôt)* |

### Deux principes qui tiennent le projet

**Les plans qui portent un texte sont des photographies, pas des générations.** Douze des vingt-deux plans sont le vrai maillot photographié puis réétalonné. Aucun risque de dérive sur `LAuRAFoot`, `UNIS DANS TOUS NOS DÉFIS`, `1961` ou `FC CLUSA` : ce sont les vrais flocages.

**Le grain est le liant.** Le film mélange des photos de téléphone et des images fabriquées. `filmlook.py` applique à tous les plans le même grain 35 mm, la même halation rouge-orangée et la même bascule ombres froides / hautes lumières chaudes. C'est ce qui fait que deux origines différentes deviennent un seul tournage.
