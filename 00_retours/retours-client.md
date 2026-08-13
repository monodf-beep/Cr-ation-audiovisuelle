# Retours client — journal complet

Tous les retours de Franck Monod sur le projet, consignés par thème plutôt que dans l'ordre où ils sont arrivés. Chacun porte son état.

`✔` appliqué · `⏳` en cours · `○` ouvert

---

## 1. Ce qui est non négociable

| | Retour | État |
|---|---|---|
| ✔ | **Le moindre détail du maillot doit être exact.** Utiliser le modèle le plus précis. | Bible de flocage + vérification au zoom sur chaque plan |
| ✔ | **Le film finit sur `FC CLUSA` et la Croix de Savoie** au verso. | Plans 20-21 |
| ✔ | **Aucun visage.** Ou alors cachés, pour ne pas avoir à travailler dessus. | Silhouettes de dos, cadres coupés sous le cou, têtes hors champ, drapeau qui masque |
| ✔ | **Pas de faits inventés.** Refus explicite d'une ligne du type « le 12 mars, à Rumilly ». | Aucune date, aucun score, aucun adversaire dans le film |
| ✔ | **Pas de voix off.** | Supprimée ; le son de la tribune la remplace |

## 2. Le style — la demande la plus structurante

> « Ça fait très intelligence artificielle. Trop propre, trop pro. J'aimerais un community manager d'un petit club avec ses moyens, avec son appareil photo qui ne soit pas d'une grande qualité. Il faut qu'il y ait des imperfections. »

| | Retour | État |
|---|---|---|
| ✔ | Le problème n'est pas le grain, c'est la perfection. | Diagnostic posé : exposition, cadrage et profondeur de champ parfaits sont le vrai *tell* |
| ✔ | Filtre et grain marquant l'amateurisme. | `amateur.py` : bruit de capteur, dérive de balance des blancs, hautes lumières cramées, aberration chromatique, banding, double compression JPEG, cadrage penché |
| ✔ | Premier calibrage trop violent (confettis colorés). | Amplitude divisée par deux, chrominance désaturée, lissage renforcé |
| ✔ | Les plans du maillot porté « pas dans le style ». | Cause identifiée : un joueur posé est un shooting. Refaits en cadrage accidentel |
| ✔ | Vos photos du stade « pas le style souhaité ». | Preset de dégradation dédié, le plus dur du projet |
| ✔ | Plans jugés « trop IA » : la main sur le filet, la silhouette générique. | Écartés |

## 3. Le lieu — la série d'erreurs la plus longue

Aucune bible du stade n'existait au départ, donc chaque plan réinventait la géométrie.

| | Retour | Règle inscrite |
|---|---|---|
| ✔ | Les projecteurs ne sont pas placés comme ça. | Quatre mâts aux **angles de l'ovale**, loin du terrain et de la tribune. Poteau rond, une seule tête rectangulaire sur plateforme à garde-corps |
| ✔ | Ce ne sont pas des grilles blanches, ce sont des **filets derrière les buts**. | Filets pare-ballons blancs souples ; aucun grillage de chantier |
| ✔ | La piste d'athlétisme n'est pas cohérente. | Piste **large**, six à huit couloirs, lignes blanches — jamais un liseré rouge collé à la touche |
| ✔ | Les abords du terrain ne correspondent pas. | Stade d'athlétisme : la tribune est en retrait derrière huit couloirs |
| ✔ | La montagne est à la fois derrière et en face de la tribune. | **Règle d'axe** : sommet isolé uniquement derrière la tribune ; crête plus longue et moins caractéristique dans l'autre sens |
| ✔ | Ce n'est pas Le Môle. | Toponyme retiré — c'était une déduction de ma part, pas une vérification. **Nom à confirmer par le club** |
| ✔ | Deux tribunes dans le plan 05 alors qu'il n'y en a qu'une. | Une seule tribune, les trois autres côtés sont nus |
| ✔ | Cohérence à vérifier sur **toutes** les images. | Procédure de contrôle en huit points dans `bible-stade.md` |

## 4. La saison

> « On est le 13 août actuellement. Attention à la saison sur l'ensemble des visuels. »

| | Retour | État |
|---|---|---|
| ✔ | Neige, boue, buée, doudounes : hors saison. | Interdits inscrits. Sol sec, feuillage vert, t-shirts et bras nus |
| ✔ | Le ciel noir est faux. | Ciel **bleu profond de fin de soirée d'août**, projecteurs allumés vers 21 h 30 |
| ✔ | « Tu l'écris mais tu ne fais rien encore. » | Reproche fondé : six plans refaits d'un coup au lieu d'être annotés une fois de plus |
| ○ | **Jour / nuit incohérent.** | Vos trois photos du stade sont en plein jour couvert. La conversion crépuscule testée ne tient pas — elle se lit comme un filtre chaud. **Trois photos reprises au stade vers 21 h 30 régleraient le problème en dix minutes** |

## 5. Le public

| | Retour | Règle inscrite |
|---|---|---|
| ✔ | Les tribunes pourraient être remplies plutôt que vides. | Le film raconte une vallée qui vient, plus la solitude |
| ✔ | Trop propre : il faut un **petit groupe ultra**, des gens dispersés, et des personnes à la rambarde au premier plan. | Noyau d'une vingtaine à la barrière, le reste par groupes de deux ou trois avec des rangs vides |
| ✔ | Incohérence entre une tribune familiale et un kop. | Un seul groupe, suivi du début à la fin |
| ✔ | Le nombre de supporters varie d'un plan à l'autre. | **Recensement fixe** : environ cent cinquante personnes, tribune jamais remplie au-delà du tiers |
| ✔ | Le kop change de côté. | **Position fixe** : contre la barrière, à gauche de la tribune vue depuis le terrain |
| ✔ | La tribune est tantôt pleine, tantôt vide. | Transformé en **progression** : vide avant, qui se garnit à l'arrivée, au tiers pendant, debout à la fin. L'occupation ne décroît jamais |

## 6. L'histoire

| | Retour | Ce qui a changé |
|---|---|---|
| ✔ | Pas de plan de montagne — ancrer sur le terrain : projecteurs, banc de touche, terrain. | Le paysage a été remplacé par le stade. Les montagnes sont revenues, mais **derrière le terrain**, pas en carte postale |
| ✔ | « Pour l'instant tu ne racontes pas d'histoire. » | Reproche fondé. Le film était une suite de beaux plans et de slogans |
| ✔ | Déroulé incompréhensible entre les plans 11-12 et 13-14. | Le dispositif appel-réponse demandait d'être décodé. Remplacé par une **chronologie** : avant, pendant, après |
| ✔ | « Jeté par terre », ce n'est pas respectueux. | Plan supprimé. Le maillot n'est jamais montré au sol : c'est le vêtement d'un titre |
| ✔ | Garder le drapeau du Faucigny, la vraie tribune, la vraie montagne. | Les trois sont dans le film |
| ✔ | L'image de l'ado qui brandit le drapeau de dos était bonne. | Reprise, plan 18 |
| ✔ | Le gros plan `TARIM` n'est pas obligatoire. | Écarté, aucun rôle narratif |
| ✔ | « J'ai jamais dit que je n'en voulais pas » (maillot porté). | Malentendu de ma part corrigé : c'était la saison et le style, pas le principe. Le dos porté est revenu au plan 15 |

## 7. Sélection image par image

Retours donnés lors du passage en revue du catalogue.

| Famille | Verdict | Suite |
|---|---|---|
| Maillot (macros) | tout bon | 9 plans au montage |
| Maillot porté | seul le vestiaire est retenu | Les autres refaits en soirée d'août et style amateur |
| Stade réel | bon, mais pas le style | Traitement durci |
| Public | tout bon | Refaits en saison |
| Corps | ne garder que `AMAT-05` et `TERRAIN-05` | Les autres écartés |
| Drapeau | ne garder que `FLAG-01` et `FLAG-02` | `DRAPEAU`, `DRAPEAU2`, `ETE-DRAPEAU` écartés |

**Plans nommément écartés :** `01` et `03` trop bruts · `11` la main sur le filet, trop IA · `13` gros plan sponsor · `15` flou · `15b` hors style · `14` sans intérêt narratif.

**Plan nommément retenu :** `08`, les crampons — « j'aime beaucoup ».

## 8. Erreur de méthode que vous avez corrigée

> « 12 c'est n'importe quoi, il fallait juste reprendre la photo qu'on avait et la mettre en été. »

Reproche exact. J'avais regénéré de zéro un plan déjà validé, au lieu de le passer en référence de composition pour n'en changer que la saison. **Règle retenue pour la suite : un plan validé ne se refait jamais de zéro, il se reprend comme référence.**

---

## Ce qui reste ouvert

1. **Les trois photos du stade en plein jour.** Seul point que je ne sais pas résoudre en post-production. À reprendre sur place vers 21 h 30.
2. **Le nom du sommet** derrière la tribune, à confirmer.
3. **L'accord du joueur** photographié, si la publicité est diffusée.
4. **La mention `CLUSES SCIONZIER FC`** sur la main courante, alors que l'écusson dit `FC CLUSES 1961` — à trancher si ce panneau doit rester lisible.
