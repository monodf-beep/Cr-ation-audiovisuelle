# Étalonnage — plans macro tirés des photos réelles

## État : les 15 plans sont produits

| Plans | Source | Fidélité |
|---|---|---|
| 01, 02, 03, 05, 06, 07, 08, 11, 12, 13, 14, 15 | photos réelles réétalonnées | exacte |
| 04, 09 | génération 4:5, Nano Banana Pro | packshots, ~1 s d'écran chacun |
| 10 | génération 9:16, Nano Banana Pro | paysage, aucun enjeu de détail |

Les deux plans de matière (01, 02) ont finalement été tirés eux aussi des photos réelles plutôt que générés : ils ne portent aucun texte, mais les générer les aurait rendus étrangers à la texture des dix autres.

**Sur le plan 10 :** l'image est une vallée alpine crédible, cadrée et étalonnée dans l'esprit de la vallée de l'Arve. Ce n'est pas une vue documentée de Cluses. Elle tient son rôle de respiration au montage, mais elle ne doit pas être présentée comme une photographie du lieu.

## Principe

Dix des quinze plans du film sont des macros : l'écusson, TARIM, la couronne, le patch R2, FORZAFC, le 26, CHAMPIONS, FC CLUSA, la Croix de Savoie, le plan de fin. Pour ces dix plans, **on ne génère rien**. Les photos du vrai maillot sont déjà les images du film ; elles sont seulement remontées en résolution, recadrées et éclairées.

Conséquence directe : sur ces plans, aucun texte ne peut être faux. `LAuRAFoot`, `UNIS DANS TOUS NOS DÉFIS`, `1961`, `FC CLUSA` sont les vrais flocages photographiés, pas une reconstitution.

La génération ne sert plus que là où il n'y a aucun texte critique en jeu : la matière (01, 02), les deux packshots du maillot entier (04, 09) et le paysage (10).

## Chaîne

```
photo réelle (511×1080)
  → upscale 4K Bytedance via Higgsfield        → 04_sources/*.png (1926×4096)
  → 03_etalonnage/grade.py                      → 05_plans/*.png
```

L'upscale est un agrandissement, pas une génération : il n'invente aucun contenu. Vérifié plan par plan — maille perforée, ballon de l'écusson à gauche, `1961` à droite, tout est conservé.

## Recette d'étalonnage

`grade.py` applique dans l'ordre : rotation, recadrage normalisé, courbe en S tempérée, lumière rasante directionnelle, vignette, saturation retenue du rouge, correction chromatique de l'or.

Deux réglages ont demandé une correction après le premier tirage :

- **Courbe trop dure** — elle délavait le bronze des flocages vers un crème pâle. Mélange 42 % linéaire / 58 % courbe en S, gamma 1.24.
- **Saturation trop forte** — elle poussait le rouge sublimé vers le magenta. Gain ramené de 0.40 à 0.16, avec retenue du canal bleu pour tenir le rouge du côté orangé.

## Sorties

| Type | Usage |
|---|---|
| `PLAN-XX.png` | cadre 9:16 prêt à monter — plans fixes ou push-in |
| `PLATE-XX.png` | plaque large au format natif — travellings latéraux en pan-and-scan au montage |

**Sur les travellings :** les plans 05, 08 et 12 sont des mouvements de caméra latéraux sur une surface plane imprimée. Ils ne passent pas par un modèle vidéo — un pan-and-scan sur la plaque haute définition donne un travelling parfait, et strictement fidèle. Le modèle vidéo n'est nécessaire que là où la matière bouge vraiment.

## Résolutions

Les sources sont des photos de téléphone recompressées à 511×1080. Après upscale 4K et recadrage macro, les plans sortent entre 991×1761 et 1751×3113 — suffisant pour un master 1080p, et pour la plupart pour un 2K.

Pour une livraison en 4K, les plans les plus serrés (`PLAN-03`, `PLAN-13`, `PLAN-14`) demandent une seconde passe d'upscale sur le recadrage. Si vous retrouvez les photos originales du téléphone avant compression, elles rendront cette passe inutile — c'est la meilleure amélioration possible sur ce projet.

## Assets

Les fichiers image ne sont pas versionnés (86 Mo). Le dépôt porte le script et la recette, qui suffisent à tout régénérer depuis les médias Higgsfield listés dans `02_prompts/prompts-nano-banana-pro.md`.
