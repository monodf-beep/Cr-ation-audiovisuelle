# Bible du stade — Parc des Sports, Cluses

Ce fichier fait pour le lieu ce que `prompts-nano-banana-pro.md` fait pour le maillot : il fige la géométrie. Sans lui, chaque plan réinvente le stade, et l'incohérence se voit d'une image à l'autre bien plus qu'un défaut isolé.

**À coller dans chaque prompt qui montre le stade.**

---

## Ce qu'il y a vraiment

D'après les photographies du club, du sol et depuis les gradins.

### Implantation

Un **stade d'athlétisme**, pas un stade de football. Ça change tout : le terrain est au centre d'un ovale, et **rien n'est collé au terrain**.

- **Piste d'athlétisme** rose-saumon, six à huit couloirs, **ovale complet** autour du terrain. Un aplat rouge-brique plus foncé dans un angle (aire de saut ou de lancer).
- **Le terrain** au centre de l'ovale, en herbe à bandes de tonte.
- **La tribune est en retrait, derrière la piste** — huit couloirs séparent le premier rang du bord du terrain. Aucun supporter n'est jamais à moins de vingt mètres de la touche.

### Les projecteurs

**Quatre mâts, aux quatre angles de l'ovale, très à l'écart du terrain et de la tribune.**

- Poteau **rond, lisse, gris clair**, très haut et fin.
- Au sommet, **une seule tête rectangulaire** de lampes en grille, montée sur une petite plateforme à garde-corps.
- **Jamais** un pylône en treillis, jamais un mât à bras multiples écartés, jamais une tête en pyramide.
- Ils se dressent dans l'herbe ou le bitume qui entoure la piste, **pas derrière la tribune, pas au bord de la touche**.

### La tribune

Une seule, sur un grand côté.

- **Longue, basse, ouverte sur les côtés**, toit plat sombre porté par des poteaux fins.
- **Gradins en bancs bruns**, pente faible, huit à dix rangs.
- **Derrière et au-dessus, un bâtiment** avec une longue rangée de fenêtres — vestiaires et club-house intégrés.
- Capacité modeste : quelques centaines de places.

### Les clôtures

- **Derrière chaque but : de hauts filets pare-ballons blancs** tendus sur des poteaux. C'est du filet à mailles larges, souple, pas du grillage rigide.
- **Pas de grillage type chantier autour du terrain.** Une simple barrière basse borde la piste par endroits.

### Le décor

- **Une grande montagne arrondie, isolée, occupe tout le fond** derrière la tribune. Sommet vert, flancs boisés, forme massive et reconnaissable. Ce n'est pas une crête dentelée ni une paroi verticale.
- Entre la tribune et la montagne : **les toits de tuiles de la ville**, des maisons basses, quelques immeubles.
- Des arbres sur les côtés.

### Le matériel qui traîne

Ce sont les détails qui rendent le lieu vrai : des **buts blancs mobiles** rangés sur la piste, une **structure grise sur roues** (podium ou tour de juge) posée en bord de piste, des **bâches vertes** sur du matériel empilé, des **plots orange**.

---

## Bloc à coller dans les prompts

```
STADIUM SPEC — an ATHLETICS stadium, not a football-only ground:
- A full oval PINK-SALMON ATHLETICS TRACK, six to eight lanes, surrounds the
  pitch. A darker brick-red throwing/jumping apron in one corner.
- The grass pitch sits inside the oval. NOTHING is close to the touchline.
- ONE long low covered stand on one side only, set BACK BEHIND THE TRACK, so
  eight lanes separate the front row from the pitch. Dark flat roof on slim
  posts, BROWN BENCH TIERS, eight to ten shallow rows, open sides, and behind
  it a building with a long row of windows.
- FOUR FLOODLIGHT PYLONS at the FOUR CORNERS OF THE OVAL, far from both the
  pitch and the stand. Each is a tall SLIM ROUND PALE-GREY POLE topped by ONE
  RECTANGULAR LAMP ARRAY on a small railed platform. NEVER a lattice tower,
  NEVER a splayed multi-arm mast, NEVER a pyramid head.
- Behind each goal: TALL WHITE BALL-STOP NETTING on poles — soft wide-mesh
  net, NOT rigid chain-link fence. There is no site fencing around the pitch,
  only a low barrier rail in places.
- Backdrop: ONE large rounded isolated green mountain filling the horizon
  behind the stand, wooded flanks, massive and smooth — NOT a jagged ridge,
  NOT a vertical cliff. Between stand and mountain, the tiled roofs of a small
  town. Trees at the sides.
- Scattered kit: white mobile goals parked on the track, a grey wheeled
  officials' platform, green tarpaulins over stacked equipment, orange cones.
```

---

## Erreurs déjà commises, à ne plus reproduire

| Erreur | Ce qu'il faut |
|---|---|
| Grillage type chantier autour du terrain | Filets pare-ballons blancs derrière les buts, barrière basse ailleurs |
| Mâts en treillis, ou à bras multiples écartés | Poteau rond fin, une seule tête rectangulaire au sommet |
| Mâts plantés au bord de la touche ou derrière la tribune | Aux quatre angles de l'ovale, loin de tout |
| Tribune collée au terrain | Huit couloirs de piste entre le premier rang et la touche |
| Crêtes dentelées, parois verticales, vallée encaissée | Une seule montagne arrondie et massive, boisée |
| Pas de piste d'athlétisme du tout | La piste est visible dans presque tous les plans larges |

---

## Contrôle de cohérence

Avant de valider un plan large, vérifier dans l'ordre :

1. **La piste est-elle là**, et rose-saumon ?
2. **Le mât** est-il un poteau rond à tête rectangulaire unique, et loin du terrain ?
3. **La tribune** est-elle en retrait derrière la piste, avec des bancs bruns et un toit plat sombre ?
4. **Derrière les buts** : du filet blanc, pas du grillage ?
5. **La montagne** est-elle une masse arrondie unique, pas une crête ?

Un plan qui rate deux de ces cinq points est à refaire : l'œil ne relève pas le détail isolé, mais il sent immédiatement que deux plans ne sont pas le même endroit.
