# Charte Franck Monod pour la vidéo

Base de référence pour toutes les compositions HyperFrames. On part d'ici, on n'improvise pas.
Source : l'export Claude Design « Cartes des États de Savoie » (`09_charte/export-cartes/`).
Les valeurs de ce document sont celles de la charte. Les tokens CSS sont dans `brand/tokens.css`.

## Couleurs

| Token | Valeur | Usage |
|---|---|---|
| `--fm-bleu-savoie` | `#0a36af` | couleur de marque : contours de carte, sur-titres, remplissage des territoires |
| `--fm-ink-900` | `#171719` | titres, étiquettes |
| `--fm-ink-700` | `#45454c` | sous-titres, texte courant |
| `--fm-ink-500` | `#64646c` | texte secondaire ; signature en vidéo |
| `--fm-ink-400` | `#8c8c94` | signature sur la carte web. 3,3:1 sur blanc, sous le seuil 4,5:1 : ne pas l'utiliser pour du texte en vidéo |
| `--fm-bg` | `#ffffff` | fond |
| `--fm-bg-soft` | `#f7f7f8` | fond secondaire |
| `--fm-line` | `#d9d9dc` | lignes de contexte (pays voisins) |

Un fond clair, une seule couleur d'accent. Pas de dégradé.

## Typographie

Semplicità Pro, graisses 400, 500, 600, 700. Fichiers dans `assets/fonts/` (hors dépôt, voir plus bas).

| Rôle | Taille | Graisse | Autre |
|---|---|---|---|
| Titre | 44 à 52 px | 700 | interlettrage -0,01em, interligne 1,05 |
| Sur-titre | 14 px | 600 | majuscules, interlettrage 0,14em, bleu Savoie |
| Sous-titre | 17 px | 400 | ink-700 |
| Étiquette de carte | 13 px (web) / 20 px (post) | 600 | halo blanc de 3 à 5 px |
| Signature | 13 px | 600 | majuscules, interlettrage 0,08em |

Tailles données pour un post de 1080 × 1080. En 1920 × 1080, garder les mêmes rapports.

## Mise en page du post carré

- Marge : 64 px à gauche et à droite.
- Sur-titre à 64 px du haut, titre à 92 px, sous-titre à 220 px.
- Signature « Franck Monod » en bas à droite, à 56 px du bas.
- La carte occupe la zone de 70 à 1010 px en largeur et de 340 à 990 px en hauteur.

## Cartes

- Projection Mercator, cadrée sur les 5 entités (73, 74, arrondissement de Nice, Piémont, Vallée d'Aoste).
- Savoie et Haute-Savoie fusionnées. Chaque frontière commune n'est tracée qu'une fois.
- Version réseaux sociaux : contours lissés (Catmull-Rom 0,5), trait bleu 1,8 px, sans remplissage.
- Options de la version web : remplissage bleu, provinces du Piémont en pointillés (0,5 px, opacité 0,6), villes (points de 3 px, étiquettes de 11 px), aires urbaines (cercles de 4 à 34 px).
- En vidéo, la carte est précalculée en SVG par `tools/build-carte.mjs`, car le rendu ne charge rien par le réseau.

## Mouvement (première version, à valider)

Déduit de la charte (sobre, cartographique, sans effet). À compléter avec vos références.

| Élément | Mouvement | Durée | Courbe |
|---|---|---|---|
| Sur-titre, sous-titre | montée de 12 px + fondu | 0,5 s | `power3.out` |
| Titre | révélation par masque, du bas | 0,8 s | `power4.out` |
| Contours de carte | tracé au crayon, Savoie d'abord | 1,2 à 1,6 s, décalage 0,55 s | `power2.inOut` |
| Étiquettes | fondu + montée de 6 px, après leur contour | 0,5 s | `power2.out` |
| Signature | fondu, en dernier | 0,6 s | `power1.out` |

À éviter : rebond, élasticité, rotation, zoom brusque.

## Polices hors dépôt

Le dépôt est public et Semplicità Pro est une police commerciale : les fichiers `.woff` ne sont pas versionnés.
Pour les remettre en place, dézipper l'export Claude Design dans `09_charte/`, puis :

```bash
cp 09_charte/export-cartes/assets/fonts/*.woff 08_hyperframes/assets/fonts/
```

Sans elles, le rendu retombe sur une police système.

## Ce qui manque encore

L'export ne contenait que les cartes. Il manque `base.css`, `styles.css`, `readme.md`, `SKILL.md` et `_ds_bundle.js`, ainsi que les logos, les composants et les règles de ton.
