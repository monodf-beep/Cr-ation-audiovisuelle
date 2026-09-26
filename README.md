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
| `08_hyperframes/` | projet [HyperFrames](https://hyperframes.heygen.com) : compositions vidéo en HTML, rendu MP4. Charte vidéo dans `brand/DESIGN.md` |
| `10_cern/` | reportage vertical 9:16 au CERN (Interreg culture Savoie – Genève), script de voix off dans `SCRIPT.md`. Rushes et médias hors dépôt |
| `04_montage/BONNES-PRATIQUES.md` | **règles de montage des reportages verticaux** : sous-titres, rythme visuel, voix, musique et effets, demandes de Franck. Bibliothèque validée dans `04_montage/bibliotheque.json` |
| `09_charte/` | export Claude Design de la charte Franck Monod (cartes des États de Savoie). Polices hors dépôt |

### Deux principes qui tiennent le projet

**Les plans qui portent un texte sont des photographies, pas des générations.** Douze des vingt-deux plans sont le vrai maillot photographié puis réétalonné. Aucun risque de dérive sur `LAuRAFoot`, `UNIS DANS TOUS NOS DÉFIS`, `1961` ou `FC CLUSA` : ce sont les vrais flocages.

**Le grain est le liant.** Le film mélange des photos de téléphone et des images fabriquées. `filmlook.py` applique à tous les plans le même grain 35 mm, la même halation rouge-orangée et la même bascule ombres froides / hautes lumières chaudes. C'est ce qui fait que deux origines différentes deviennent un seul tournage.

## HyperFrames

[HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen) décrit une vidéo en HTML + GSAP et la rend en MP4. Projet dans `08_hyperframes/`, skills Claude dans `.claude/skills/`.

Compositions :
- `index.html` : carte animée des États de Savoie, post carré 1080 × 1080, 8 s (`node tools/build-carte.mjs`).
- `cartes-anciennes-16x9.html` : les États de Savoie en quatre cartes d'époque (Gallica) retraitées en bleu Savoie, 23 s (`npx hyperframes render -c cartes-anciennes-16x9.html`).
- `etats-de-savoie-16x9.html` : infographie 16:9 de 16 s, trois dates, carte en relief, itinéraire du Mont-Cenis (`node tools/build-infographie.mjs`, rendu : `npx hyperframes render -c etats-de-savoie-16x9.html`).

Les tracés sont précalculés par les scripts de `tools/` (après `npm install`).

```bash
cd 08_hyperframes
npm run dev      # studio de prévisualisation
npm run check    # lint + validation
npm run render   # MP4 dans renders/
```

Prérequis : Node ≥ 22, ffmpeg, Chrome headless (`npx hyperframes browser ensure`). Dans une session Claude Code web, `.claude/hooks/hyperframes-setup.sh` installe tout ça.
