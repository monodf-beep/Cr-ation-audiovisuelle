# Avant de générer — la méthode

Ce qu'on retient d'un post de veille (chase.h.ai × Higgsfield, « How to Turn GPT-6 Astra Into a Motion Designer », sept. 2026), confronté à ce que les retours de ce projet ont coûté.

## Ce que dit le post, et ce qu'on en garde

Le post lui-même ne montre qu'une couverture : « workflow en 3 étapes, zéro clic, chaque prompt à l'intérieur ». Les étapes détaillées sont réservées à ceux qui commentent « agent ». Un commentaire renvoie vers JsonCut Studio, qui décrit un montage en JSON.

Les trois idées qu'on en tire :

1. **L'agent écrit la spécification, l'outil exécute.** Le travail créatif se fait dans un texte qu'on relit. Le rendu n'est plus qu'une exécution.
2. **Tous les prompts sont dans le dépôt.** Un prompt qu'on ne peut pas retrouver ne peut pas être corrigé.
3. **Le plan est décrit par des données, pas par une phrase.** Un champ vide se voit tout de suite. Une consigne oubliée dans un paragraphe, non.

Notre journal de retours dit la même chose, mais dans l'autre sens : presque toutes les erreurs coûteuses du projet (saison, géométrie du stade, nombre de supporters, plan validé refait de zéro) sont apparues **avant** la génération, parce que le plan n'était pas entièrement décrit.

## Les trois étapes

### 1. La fiche de plan — rien ne se génère sans elle

Chaque plan a une fiche (`fiche-plan.exemple.json`). Elle se remplit **avant** d'écrire le prompt. Si un champ reste vide, on ne génère pas.

| Champ | Pourquoi il existe (retour d'origine) |
|---|---|
| `moment` : avant / pendant / après | « Tu ne racontes pas d'histoire. » Un plan qui ne se place pas dans la soirée n'a rien à faire dans le film. |
| `etat_maillot` | Le maillot sert d'horloge au film : plié, porté, trempé, puis de dos. Jamais par terre. |
| `source` : photo réelle / reprise d'un plan validé / génération | Tout texte visible vient d'une photo. **Un plan validé ne se refait jamais de zéro.** |
| `reference` | Obligatoire si la source est une reprise. On change la saison ou l'heure, jamais la composition. |
| `heure_saison` | Août, vers 21 h 30, ciel bleu profond. La neige et la buée sont sorties trois fois. |
| `axe_camera` | La règle d'axe : le sommet isolé est derrière la tribune, jamais en face. |
| `public` | Environ 150 personnes. Le kop est à gauche, et l'occupation de la tribune ne diminue jamais. |
| `visages` | Écrire la coupe (« cadré sous le genou »). Une interdiction seule ne suffit pas. |
| `texte_a_l_ecran` | Liste exacte, caractère par caractère. Vide si le plan est généré. |
| `ratio_generation` / `ratio_final` | Un plan large du maillot se génère en 4:5, sinon les manches sortent du cadre. |
| `mouvement` | Ce que fera l'animation. Si on ne peut pas le dire en une ligne, le plan ne marchera pas en vidéo. |
| `style` | Amateur, cadrage accidentel. Un joueur qui pose, c'est déjà un shooting. |

### 2. La validation sur papier — le client voit l'histoire avant les pixels

On valide l'enchaînement des fiches, en texte ou en animatique grossière à partir des images qu'on a déjà, **avant** de lancer la moindre génération. C'est là qu'on aurait attrapé le déroulé appel-réponse que personne ne comprenait, la tribune familiale mélangée au kop, ou le plan du maillot jeté au sol.

Ce qu'on vérifie à cette étape : on lit les champs `moment` et `etat_maillot` dans l'ordre, sans rien d'autre. Si la soirée ne se suit pas, on corrige là.

### 3. Une génération verrouillée — le prompt se compose, il ne se réécrit pas

Le prompt est un assemblage de blocs, toujours dans le même ordre :

```
[bible maillot]  si le maillot est à l'image   → 02_prompts/prompts-nano-banana-pro.md
[bible stade]    si le stade est à l'image     → 02_prompts/bible-stade.md
[bible drapeau]  si un drapeau est à l'image   → 02_prompts/bible-drapeau.md
[bloc visages]                                 → 02_prompts/prompts-terrain.md
[ce qui est propre au plan]                    → la fiche
```

Seule la dernière ligne s'écrit à la main. Les bibles se collent telles quelles, sans les reformuler. Le prompt final est archivé à côté de la fiche, avec l'ID de la génération retenue.

Après la génération, on passe le contrôle de cohérence de `bible-stade.md`. Un plan qui rate deux points est refait **en reprenant sa fiche**, pas en improvisant un nouveau prompt.

## Écart relevé en appliquant la méthode

`02_prompts/prompts-terrain.md` décrit encore « une nuit d'hiver, de la brume », et son bloc pellicule parle de noirs écrasés. Un plan de terrain généré depuis ce fichier reproduirait la faute de saison. Il faut le réaligner sur `bible-stade.md` avant la prochaine génération de terrain.
