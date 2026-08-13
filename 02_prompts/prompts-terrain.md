# Prompts terrain — « CHAMPIONS 26 »

**Modèle :** `nano_banana_pro` (Google), `4k`, `9:16`
**Aucune référence image** — ces plans ne reproduisent rien, ils fabriquent un lieu.

Les huit plans de terrain sont le seul décor du film. Un terrain municipal, une nuit d'hiver, des projecteurs, de la brume. Une seule source lumineuse pour tout le film : c'est elle qui allume l'herbe, le banc, le filet, et c'est elle qui allumera le maillot.

---

## Les deux blocs à coller dans chaque prompt

### Bloc pellicule

```
FILM LOOK: shot on 35mm motion picture film, heavy organic grain, strong
halation blooming around every light source, crushed blacks with a cold
blue-green cast in the shadows, warm sodium-amber cores in the highlights.
Telephoto compression, shallow depth of field, anamorphic horizontal flare.
No digital sharpness, no clean CGI look, no HDR flatness.
```

### Bloc visages

```
NO FACE, no visible head, no profile, no facial features anywhere in frame.
People appear only as backlit silhouettes, seen from behind, cropped below
the neck, or reduced to hands, legs and boots.
```

C'est le bloc le plus important du fichier. Sur les trois plans qui portent un corps (05, 06, 07), il faut en plus **nommer explicitement la coupe** — « cadré sous le genou », « le bras coupé à l'avant-bras par le bord du cadre » — parce qu'une consigne négative seule ne suffit pas : le modèle a une forte tendance à recadrer large pour inclure un visage.

---

## Les huit plans

| Asset | Plan | Interdits spécifiques |
|---|---|---|
| `TERRAIN-01` | Un seul projecteur s'allume au loin dans le noir total, brume froide, halation longue. On devine à peine une cage et le haut d'une clôture. | aucune personne |
| `TERRAIN-02` | Contre-plongée sur le mât entier, toutes lampes allumées, cônes solides dans le brouillard, treillis d'acier en silhouette. | aucune personne |
| `TERRAIN-03` | Macro au ras du sol : herbe mouillée en contre-jour rasant, gouttes qui brûlent, ligne de craie fraîche en diagonale. | aucune personne |
| `TERRAIN-04` | L'abri de touche, sièges plastique usés et trempés, un sac au sol, désert. | aucune personne, aucun panneau sponsor |
| `TERRAIN-05` | Crampons plantés dans l'herbe boueuse, **cadré sous le genou**, contre-jour dur, buée basse. | pas de torse, pas de tête, aucune marque sur les chaussures |
| `TERRAIN-06` | Une main serre le cordage du filet, **bras coupé à l'avant-bras par le cadre**, gouttes en contre-jour. | pas d'épaule, pas de torse, pas de tête |
| `TERRAIN-07` | Silhouette **de dos** qui s'éloigne vers les projecteurs, sac à l'épaule, quasi entièrement dans l'ombre. | aucun visage, aucun numéro sur les vêtements |
| `TERRAIN-08` | Le ballon immobile sur le point de penalty, projecteurs derrière, ombre longue vers la caméra. | aucune personne, aucune marque sur le ballon |

---

## Deux choses vues à la production

**Le filtre bloque `TERRAIN-04`.** La première formulation du banc des remplaçants — avec « bench », « towel » et « abandoned water bottle » — est revenue en `nsfw`, faux positif évident. Reformulée en « row of empty worn plastic seats in the covered dugout shelter », elle passe sans problème. Si un plan revient bloqué, il ne sert à rien de relancer tel quel : c'est le vocabulaire qu'il faut changer, pas la chance.

**`TERRAIN-07` garde sa tête dans le cadre.** Le prompt demandait de la couper au bord supérieur ; le modèle a rendu une silhouette entière, tête comprise. Aucun trait de visage n'est visible — c'est une masse noire à contre-jour — donc le plan est conforme à l'intention et il est même plus beau ainsi. À garder en l'état, mais à vérifier si le plan est regénéré.

---

## Ce qui vient après

Les huit plans passent ensuite par `03_etalonnage/filmlook.py`, exactement comme les douze plans de maillot. C'est cette passe commune — même grain, même halation, même bascule froid/chaud — qui fait que des photographies de téléphone et des images fabriquées finissent par appartenir au même tournage.
