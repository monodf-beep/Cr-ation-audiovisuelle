# Le drapeau du Faucigny — spécification verrouillée

**Mesurée** sur le fichier de référence du club — `a6852625` dans Higgsfield,
copié en `21_savoie/faucigny.jpg`. Pas relevée à l'œil : le script compte les
transitions de couleur sur une ligne au milieu du drapeau.

```
6 bandes :
  1  OR      17,6 % de la largeur
  2  ROUGE   16,5 %
  3  OR      15,8 %
  4  ROUGE   17,1 %
  5  OR      16,0 %
  6  ROUGE   17,1 %
```

Six bandes égales à un sixième chacune, **or à la hampe, rouge au bord
libre**. C'est ce que dit aussi le blason du Faucigny — d'or à trois pals
de gueules — mais c'est la mesure qui fait foi ici.

**À coller telle quelle dans toute génération où le drapeau apparaît.**

## Ce qui était faux

Les drapeaux du film avaient **7 à 9 bandes étroites**, et sur le plan du
grillage elles couraient **en travers** de la barre au lieu d'être
parallèles à elle. L'erreur ne venait pas des clips : elle était déjà dans
les images sources — `TRIBUNE-DEBOUT`, `ULTRAS-FIN`, `FLAG-01` — et les
clips en ont hérité.

Les couleurs, elles, étaient bonnes.

## Le bloc à coller

```
FLAG OF THE FAUCIGNY — EXACT SPECIFICATION, DO NOT REINTERPRET:
- EXACTLY SIX vertical bands of equal width. Six. Not seven, not eight.
- Each band is one sixth of the flag's width — BOLD and WIDE, never thin stripes.
- The bands run PARALLEL to the pole or hoist, from top edge to bottom edge.
- Order, starting at the pole: GOLD, RED, GOLD, RED, GOLD, RED.
  The band touching the pole is GOLD. The band at the free edge is RED.
- Deep warm gold (#F2C230) and strong red (#D8262C).
- No other colour. No border, no fringe, no emblem, no lettering, no crest.
```

## Rappel de méthode

Le modèle vidéo ne prend qu'une image de départ et pas de seconde
référence : lui écrire « six bandes » dans un prompt de mouvement dérive,
et un drapeau qui claque se plie, donc l'erreur se cache dans les plis.

On corrige donc **l'image fixe d'abord**, on compte les bandes à plat, et
on anime seulement ensuite.

## Vérification

Sur une image candidate, chercher une position où le tissu est **à plat**
et compter. Si on ne trouve aucune image à plat, l'image n'est pas
vérifiable et ne doit pas être validée.

## Ne pas confondre

| | |
|---|---|
| **Faucigny** | six bandes verticales, or et rouge alternés, or à la hampe |
| **Savoie** | croix blanche pleine sur fond rouge, sans bordure ni emblème |

Les deux sont dans le film, à deux endroits différents. La Croix de Savoie
est aussi sur le maillot, au dos, sous la nuque.
