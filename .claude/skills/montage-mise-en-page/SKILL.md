---
name: montage-mise-en-page
description: Choisir et construire la mise en page d'un plan de montage face camera ou explicatif — ecran divise, bandes empilees avec etiquettes (type TOFU / MOFU / BOFU), visage en incrustation dans un coin, texte derriere ou devant la personne, sous-titres, coupes franches, zooms et plans de coupe. A utiliser des qu'un montage met en scene une personne qui parle, avant d'ecrire le plan de montage ou d'appeler 04_montage/disposition.py, texte_derriere.py ou coupes.py.
---

# Mise en page du montage

Une mise en page sert a faire comprendre, pas a decorer. On part toujours de
la question : **qu'est-ce que le spectateur doit regarder a ce moment ?** La
personne, la chose dont elle parle, ou la comparaison entre deux choses.

## 1. Choisir la disposition

| Situation | Disposition | Outil |
|---|---|---|
| La personne raconte, rien d'autre a montrer | Plein cadre sur la personne | — |
| La personne et ce qu'elle montre comptent autant (avant / apres, deux lieux, deux interlocuteurs) | **Ecran divise** : l'un sur l'autre en 9:16, cote a cote en 16:9 | `disposition.py divise` |
| On compare 2 a 4 niveaux d'une meme idee (TOFU / MOFU / BOFU, petit / moyen / grand, 3 etapes) | **Bandes empilees**, une etiquette par bande, un chiffre dessous | `disposition.py pile` |
| Ce qu'on montre compte plus que la personne (ecran, document, carte, plan de coupe) et elle commente | **Visage en incrustation**, en bas a droite par defaut | `disposition.py incrustation` |
| Un mot-cle, un titre de chapitre, une promesse d'accroche | **Texte derriere la tete** | `texte_derriere.py` |
| Un moment fort, une emotion, une image qui se suffit | Plan de coupe plein cadre, voix par-dessus | — |

Regles de choix :
- **Une disposition par idee.** On change de disposition quand l'idee change, pas pour occuper l'oeil.
- **Ecran divise** : les deux cotes doivent avoir la meme importance. Si l'un est secondaire, c'est une incrustation. On ne garde **qu'une piste son** (`--son`), l'autre est coupee. Les deux cotes restent synchronises.
- **Bandes empilees** : la meme prise repetee avec `--decalages` marche tres bien pour une comparaison. Il faut que le visage reste lisible dans chaque bande : `--cadrage 0.3` a `0.4` garde la tete. Au-dela de 3 bandes en 9:16, le visage devient trop petit.
- **Visage en incrustation** : a partir du moment ou l'on montre quelque chose de precis. Le visage ne doit jamais cacher l'information : on change de coin plutot que de reduire sous 25 % de la largeur. On l'ouvre et on le ferme en plein cadre sur la personne (debut et fin de video).
- **Texte derriere la tete** : 1 ou 2 mots, lettres epaisses, a hauteur de tete (`--position 0.3` a `0.4`). Une ou deux fois par video, pas plus : c'est un effet d'accroche. Plan fixe ou presque, personne nette sur un decor distinct.
- **Texte devant** (`"devant": true` dans le plan) : pour une information qui doit etre lue sans ambiguite (chiffre, nom, lieu). Derriere = effet ; devant = information.

## 2. Zones a respecter

- **Zone sure des reseaux en 9:16 (1080 × 1920)** : rien d'important dans les 250 px du haut, les 420 px du bas (nom du compte, legende, bouton « Suivre ») ni les 140 px de droite (coeur, commentaires, partage). `disposition.py` deplace deja les etiquettes ; pour les autres textes, verifier a la main. Contre-exemple vu sur Instagram : l'etiquette « BOFU » de la bande du bas cachee sous le nom du compte.
- **Zone du visage** : jamais de sous-titre ni d'etiquette sur les yeux ou la bouche. En plein cadre 9:16, les sous-titres vont sous le menton (vers 62-70 % de la hauteur), jamais au milieu du visage.
- **Couverture 3:4** : les grilles Instagram coupent un Reel au centre (fenetre 1080 × 1440). Le titre de la couverture doit y tenir.

## 3. Rythme

- **Coupes franches** (`coupes.py`) : on retire les silences au-dela de 0,45 s en gardant 0,08 s de marge. Fondu son de 30 ms a chaque raccord.
- **Une coupe au meme cadre saute a l'oeil** : on alterne un leger zoom avant (`--zoom 1.08`), ou on pose un plan de coupe par-dessus le raccord.
- **Plan de coupe** : montrer ce que la personne dit, jamais une image generique. 2 a 4 s par insert. Une image generee n'illustre jamais un fait (regle du studio) et reste signalee.
- **Changement de disposition** : une fois toutes les 5 a 10 s au plus sur un format court. Chaque changement doit correspondre a une phrase du texte.

## 4. Sous-titres

- Mots courts, 1 a 3 mots a l'ecran, cales sur la voix (`00_pipeline/notes.py` donne les segments horodates).
- Un mot mis en couleur par phrase au plus, celui qui porte le sens.
- Contraste : texte blanc contour sombre, ou bloc de couleur ; jamais de texte fin sur une image chargee.

## 5. Verifier avant de rendre

1. `texte_derriere.py ... --apercu 1.5 -o apercu.png` : une image et son masque. Si le masque deborde sur le decor ou mange les cheveux, changer de plan plutot que forcer.
2. Extraire une image par disposition (`ffmpeg -ss T -i sortie.mp4 -frames:v 1 f.png`) et verifier : visage lisible, rien dans les zones interdites, etiquettes lisibles sur telephone (30 px minimum sur 1080).
3. Une seule piste son audible a la fois.

## Sources des regles

Reformulees a partir de : skill `talking-head-recut` de HeyGen HyperFrames (Apache-2.0,
github.com/heygen-com/hyperframes), `browser-use/video-use` (MIT), `kurbaitaev/ghost-editor`
(MIT, sous-titres hors visage), guides Riverside (ecran divise), TechSmith (visage en
incrustation), Adobe (texte derriere le sujet), Descript (plans de coupe). Recette du texte
derriere la personne inspiree de `luisadrianpuga/DepthCaptions` (MIT). Detail dans
`00_pipeline/VEILLE.md`, section 3.
