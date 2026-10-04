# Carte des États de Savoie : règles de Franck

Tout ce qui a été décidé pour les cartes, du CERN (25 septembre 2026) à Terra Madre (4 octobre 2026).
**À relire avant toute carte**, quel que soit le reportage. On ne redessine pas une carte : on part de
celle du CERN (`10_cern/tools/build-carte.mjs`, avec `10_cern/tools/langue.mjs`) et on change seulement
le cadrage et les repères du reportage.

Sources : `08_hyperframes/brand/DESIGN.md` (charte), `09_charte/export-cartes/` (export Claude Design),
`10_cern/tools/build-carte.mjs` et `langue.mjs` (carte vidéo de référence), historique git du 25/09.

## 1. Ce que montre la carte

- **Les États de Savoie, ce sont cinq entités** : Savoie (73) et Haute-Savoie (74), **fusionnées en une
  seule Savoie**, la **Vallée d'Aoste**, le **Piémont** et l'**arrondissement de Nice** (comté de Nice).
  - Il ne faut jamais en oublier une. Les deux oublis à ne pas refaire : la Vallée d'Aoste et le comté de Nice.
  - Nice compte même quand le cadrage du reportage ne l'atteint pas : on recadre ou on recule la caméra
    pour le montrer au moins une fois.
- **L'espace sabaudo est affirmé** : un seul aplat pour les cinq entités, avec un contour bleu Savoie marqué.
- **Les voisins** (le reste de la France, la Suisse, le reste de l'Italie) restent en contexte : fond gris
  doux et lignes `--fm-line` (#d9d9dc). Ils sont présents mais discrets. Les frontières voisines ont été
  retirées puis remises le 25/09 : on les garde.

## 2. Les traits : trois niveaux, en bleu Savoie (#0a36af)

| Niveau | Où | Rendu (vidéo 1080×1920) |
|---|---|---|
| Très épais | bord extérieur des États : Savoie contre la France et la Suisse, bord extérieur d'Aoste, du Piémont et de Nice | 5 px, plein |
| Moyen | limites intérieures entre les entités : Savoie / Aoste / Piémont (/ Nice) | 2,2 px, opacité 0,55 |
| Léger | limite 73 / 74, provinces du Piémont | 1,3 px, opacité 0,4, pointillés « 2 5 » |

- **Chaque frontière commune n'est tracée qu'une fois.** Les sources françaises et italiennes ne partagent
  pas leurs sommets : la déduplication se fait par proximité en longitude et latitude (seuil de 0,02 à 0,03°).
- Les provinces et la limite 73/74 se tracent **sans être nommées**.
- Les traits utilisent `vector-effect: non-scaling-stroke` : ils gardent leur épaisseur quand la caméra zoome.
- Abandonné le 25/09 : la frontière franco-suisse en limite régionale fine (tirets et points). Elle est
  remplacée par le trait très épais, qui marque le bord des États.

## 3. Les noms

- **Territoires des États** (Savoie, Vallée d'Aoste, Piémont, comté de Nice) : Semplicità Pro gras,
  **en bleu Savoie**, avec un halo blanc.
- **Lieux de la langue** (Genève, Pays de Vaud, Bas-Valais, Bugey, Grenoble…) : Cormorant Garamond
  **italique** fine, bleu nuit (#1b2f6e), **sans revendication** : on nomme, on ne dessine pas de frontière.
- Villes et repères du reportage : un point et une étiquette (charte web : point de 3 px, étiquette de
  11 px ; en vidéo, à l'échelle de l'écran).
- Taille web 13 px, post 20 px, gras 600, halo blanc de 3 à 5 px. Garder les mêmes rapports en vidéo.

## 4. La langue : une lueur, jamais un contour

- L'aire de la langue savoyarde est une **lueur diffuse** : des taches de lumière bleue qui se fondent,
  débordent les frontières administratives et s'éteignent vers les marges. Aucun contour.
- Les taches se trouvent dans `10_cern/tools/langue.mjs`, sous forme (longitude, latitude, rayon). Elles
  couvrent la Savoie, Aoste, Genève, Vaud, l'Ain, le Valais francophone, le nord de l'Isère avec Grenoble,
  le Lyonnais et les **vallées alpines du Piémont : Orco, Soana, Lanzo, Suse moyenne**. Ce sont les
  « vallées savoyardes » du Piémont.
- **Nice et le reste du Piémont restent hors de la lueur.**
- Chaque carte reprend la lueur à sa propre échelle avec `echelleLangue()`.
- Validé sur maquette le 25/09 : sans contour, en taches fondues avec un dégradé vers les marges, et les
  frontières voisines visibles. La lueur se répand quand la voix parle de la langue.
- Vocabulaire (directive éditoriale) : on écrit « langue savoyarde ». « Francoprovençal » a été retiré du
  script du CERN ; le savoyard est du francoprovençal, mais on précise la variante.
- Autres langues (par exemple les vallées occitanes du Piémont) : elles ne sont pas encore définies par
  Franck. À lui faire valider avant de les dessiner. Le bleu Savoie reste l'accent unique.

## 5. Projection, cadrage, rendu

- Mercator (`d3.geoMercator`). La charte cadre `fitExtent` sur les 5 entités. En vidéo, on recadre selon
  le récit, sans jamais couper une entité du propos.
- Zone de la carte dans un post 1080×1080 : de 70 à 1010 px en largeur, de 340 à 990 px en hauteur.
- **En vidéo, la carte est précalculée en SVG** : le rendu HyperFrames ne charge rien par le réseau.
- Version réseaux sociaux (charte) : contours lissés (Catmull-Rom 0,5), trait bleu de 1,8 px, sans remplissage.
- Version web (charte) : remplissage bleu en option, provinces du Piémont en pointillés (0,5 px,
  opacité 0,6), villes, aires urbaines (cercles de 4 à 34 px, échelle racine carrée).

## 6. Mouvement

- Les contours se tracent au crayon, la Savoie d'abord : 1,2 à 1,6 s, décalage de 0,55 s, `power2.inOut`.
- Les étiquettes apparaissent après leur contour : fondu et montée de 6 px, 0,5 s.
- La caméra s'approche puis recule. Le CERN zoome jusqu'à Meyrin.
- À éviter : rebond, élasticité, rotation, zoom brusque.
- Pas de zoom pour faire apparaître un titre sur une image (règle de Franck, aussi valable pour les cartes).

## 7. Données et crédits

- France : france-geojson (Grégoire David, données IGN) pour 01, 05, 38, 73, 74, et les arrondissements du
  06 dans `09_charte/export-cartes/departements/06-alpes-maritimes/`.
- Italie : ISTAT (régions et provinces) via guglielmo/geojson-italy, dans `10_cern/data/` et `09_charte/export-cartes/topojson/`.
- Suisse : click_that_hood (cantons), swisstopo (Genève, district de Nyon, vue aérienne SWISSIMAGE).
- Communes du Genevois français : geo.api.gouv.fr.
- Créditer à l'écran ce qui l'exige (« © swisstopo » sur la vue aérienne).

## 8. Cartes anciennes (deuxième piste)

- Cartes d'époque de Gallica (Sanson 1665, Jaillot 1706, Brunet 1728, Bouffard 1841), en plein cadre et
  passées en bichromie bleu Savoie sur blanc. Recette dans `08_hyperframes/tools/prepare-cartes.sh`.
- La caméra se déplace lentement. Une annotation se trace à la main (cercle ou cadre bleu avec liseré blanc).
  Une fiche blanche donne l'année, le titre d'origine en italique, l'auteur et une phrase.
- Sources et conditions de réutilisation : `08_hyperframes/assets/cartes/SOURCES.md`.

## 9. Erreurs à ne pas refaire (Terra Madre, 4 octobre 2026)

- Une carte refaite de zéro (régions ISTAT et départements 73 et 74 bruts) au lieu de celle du CERN : les trois
  niveaux de traits, l'aplat de l'espace sabaudo et la lueur de la langue avaient disparu.
- La Vallée d'Aoste et le comté de Nice absents des États de Savoie.
- Des « vallées savoyardes » placées à la main au lieu de la lueur de `langue.mjs`.
- Des « vallées occitanes » dessinées en rouge sans validation : couleur hors charte, aire non validée.
