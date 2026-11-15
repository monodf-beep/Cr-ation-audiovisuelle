# Charte graphique — version 0 (relevé, pas encore décidé)

Source : `Carte — États de Savoie` fournie par Franck le 15/11/2026, qui ne contient **que des cartes**. Les valeurs ci-dessous sont mesurées dans ce fichier (rendu navigateur), pas tirées d'un document de charte. Il n'existe pas encore de charte complète : l'artifact « Design System » de Franck est vide.

## Ce que la carte fixe

### Typographie
- **Semplicita Pro** — 400, 500, 600, 700, embarquée en woff.
  - Titre : 600, ~44 px, interlettrage légèrement serré.
  - Sous-titre : 400, ~17 px, gris foncé.
  - Libellés de carte : régions 500 13 px ; villes 500 11 px ; provinces 400 italique 10 px.
- C'est la même famille que franckmonod.eu (Butti, Nebiolo, Turin 1930). **C'est le fil commun à garder.**

### Couleurs

| Rôle | Hex | Contraste sur `#FFFFFF` | sur `#F7F7F8` | Verdict |
|---|---|---|---|---|
| Encre (titres, texte) | `#171719` | 17,9 | 16,7 | OK |
| Texte secondaire | `#45454C` | 9,5 | 8,9 | OK |
| Libellés | `#64646C` | 5,9 | 5,5 | OK |
| Légende / source | `#8C8C94` | 3,3 | **3,1** | **échoue** (texte < 18 px) |
| **Bleu de marque** | `#0A36AF` | 9,7 | 9,1 | OK, blanc dessus : 9,7 |
| Fond de page | `#F7F7F8` | | | |
| Fond de carte | `#FFFFFF` | | | |

À noter : ce bleu `#0A36AF` est déjà celui de ia.franckmonod.eu. Le rouge brique `#931E1E` de franckmonod.eu n'apparaît pas dans la carte.

### Style cartographique
- Frontières d'États en trait plein bleu, provinces en pointillé bleu clair.
- Villes : point bleu plein + nom en encre.
- Pas de relief, pas de fond de couleur, pas de mer : la silhouette seule.
- Sources citées en pied (Natural Earth, France-GeoJSON, ISTAT) : bonne pratique, à garder.

## Pourquoi la carte est un actif de marque, pas une illustration

franckmonod.eu vend « l'espace Savoie-Piémont ». La silhouette des États de Savoie **est** ce produit, dessinée. Aucun consultant IA ni aucune agence d'attractivité ne peut la reprendre sans se mettre sur ton terrain. Usages possibles :
- signature visuelle (silhouette seule, en bleu, en ouverture et en fin de reel) ;
- localisateur de ville sur les couvertures de reels et de carrousels (le point bleu sur la silhouette dit « où » en un coup d'œil) ;
- fond de slide pour tout carrousel Savoie-Piémont.

## Erreurs à corriger avant toute diffusion

1. **« Torino » est posé du mauvais côté de la frontière**, à l'intérieur de la Savoie (voir `etat-actuel-carte-zoom-torino.jpg`). Pour un public d'élus et d'acteurs culturels des deux côtés, c'est l'erreur qui décrédibilise tout le reste.
2. **Le titre promet plus que la carte.** Avant 1860, les États de Savoie comprenaient aussi la Ligurie (Gênes, depuis 1815) et la Sardaigne, absentes ici. Soit on les ajoute, soit on titre ce qui est montré (« Savoie, Piémont, Vallée d'Aoste, Comté de Nice ») ou « les États de terre ferme ». À faire valider par un historien de l'Enstitut avant publication.
3. **Langue des noms incohérente** : « Turin » mais « Torino », « Aoste » mais « Valle d'Aosta/Vallée d'Aoste », « Savoie » mais « Piemonte ». Il faut une règle (ex. : nom français en principal, italien en second, partout).
4. **Doublons** : Nice ×2, Cuneo ×2, Asti, Alessandria, Novara, Vercelli, Biella ×2 (province + ville). À cette taille, un seul libellé par lieu suffit.
5. Le libellé « Valle d'Aosta/Vallée d'Aoste » chevauche la frontière.
6. La ligne de sources (`#8C8C94` sur `#F7F7F8`) n'atteint pas le contraste minimal : passer à `#64646C`.
7. **Licence** : Semplicita Pro est embarquée en base64 dans un fichier partageable. Vérifier que la licence web couvre ce cas (diffusion de la police à quiconque ouvre le fichier).

## Ce qui reste à décider (bloquant pour la v1)

- **Bleu seul, ou bleu + rouge brique ?** Les deux sites divergent. Recommandation : bleu `#0A36AF` comme couleur unique de marque (il porte la carte, il est déjà sur le site IA), rouge brique réservé à un usage d'accent ou abandonné. À trancher par Franck.
- Fond : `#F7F7F8` (gris froid de la carte) ou `#F9F8F6` (crème chaud des sites) ? Un seul.
- Le monogramme `fm` : fichier source vectoriel à fournir.
- Règles photo (aujourd'hui : gélatine violette sur un site, bois naturel sur l'autre).

La v1 (palette complète, gabarits carrousel 1080×1350 et reel 1080×1920, `tokens.css`) sera produite par l'agent `directeur-artistique` une fois ces points tranchés.
