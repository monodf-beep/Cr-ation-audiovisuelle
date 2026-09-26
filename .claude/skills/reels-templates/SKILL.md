---
name: reels-templates
description: Démonte des reels Instagram/TikTok/YouTube Shorts qui performent en modèles de montage (accroche, rythme de coupe, textes incrustés, B-roll, CTA), puis décline une idée de Franck en 5-6 reels prêts à tourner, chacun sur un modèle différent. Déclencher quand l'utilisateur colle un ou plusieurs liens de reels à analyser, demande « templatise ce reel », « ajoute ce reel à la bibliothèque », « décline cette idée en reels », « fais-moi 5 versions de reel sur… », ou parle de modèles/structures de montage de reels.
---

# Reels → modèles de montage → déclinaisons

Principe (repris d'un reel de Lucas Reverdy, puis durci) : on ne copie pas des
reels, on copie **ce qui les fait marcher**, c'est-à-dire leur montage.
Une idée tournée sur 5-6 montages différents qui ont fait leurs preuves
donne 5-6 essais au lieu d'un.

Deux modes :

- **A. Analyser** des reels pour ajouter des modèles à la bibliothèque `templates/`.
- **B. Décliner** une idée sur plusieurs modèles de la bibliothèque.

## A. Analyser des reels

### 1. Choisir quoi analyser — le filtre de performance

Un modèle n'a de valeur que si le reel a **surperformé son propre compte**.
Mesure : `score = vues du reel / médiane des vues des 10-20 derniers reels du compte`.
Garder les reels au-dessus de ×3. Un reel à 200 k vues sur un compte qui en
fait toujours 200 k ne prouve rien sur son montage ; c'est l'audience du compte.

Instagram ne donne presque jamais le nombre de vues sans être connecté
(`view_count` est vide dans `analyse.json`). Donc :

- si l'utilisateur fournit les vues (capture, relevé à la main), calculer le score ;
- sinon, demander ; ne **jamais** classer sur les likes seuls, ni inventer un chiffre ;
- un reel ajouté sans preuve de performance va dans la bibliothèque avec
  `performance: non vérifiée` et n'est pas prioritaire en mode B.

La liste des créateurs suivis est dans `createurs.md`.

### 2. Lancer l'analyse

```bash
pip install -q yt-dlp imageio-ffmpeg faster-whisper pillow   # une fois
python3 .claude/skills/reels-templates/scripts/analyse_reel.py URL [URL ...] \
    --out reels_analyses [--pas 2] [--seuil 0.3] [--cookies cookies.txt]
```

Pour chaque reel, dans `reels_analyses/<id>/` :

- `analyse.json` : métadonnées, transcription horodatée, plans détectés (coupes), rythme
  (nb de plans, durée moyenne, 1re coupe, mots/s) ;
- `planche.jpg` : une vignette par plan + une toutes les `--pas` secondes, horodatées.

La vidéo et l'audio sont téléchargés dans un dossier temporaire supprimé à la fin
de chaque reel, **y compris en cas d'erreur**. Il ne reste que le JSON et la planche.
`reels_analyses/` est ignoré par git : ce sont des images d'autres créateurs,
elles ne vont pas dans le dépôt. Les supprimer une fois le modèle écrit :
`rm -rf reels_analyses/<id>`.

Si Instagram répond `empty media response` : blocage des téléchargements anonymes
(arrive après quelques reels depuis une IP de datacenter). Solution : un
`cookies.txt` exporté d'un compte secondaire, jamais du compte principal
(risque de restriction). Le fichier de cookies ne va pas dans le dépôt.

### 3. Lire la planche, pas seulement le texte

La transcription donne le script ; **le montage est dans l'image**. Ouvrir
`planche.jpg` avec Read et relever, vignette par vignette :

- cadrage (face caméra, plan large, écran, B-roll, archive) et ses changements ;
- textes incrustés : contenu, position, style (fond, couleur, mot surligné), moment d'apparition ;
- zooms/recadrages sur un plan continu (la détection de coupes ne les voit pas :
  un face caméra sans coupe ressort en « 1 plan » alors qu'il est rythmé par
  les incrustations ou les zooms) ;
- ce qui se passe dans les 3 premières secondes (image + texte + première phrase).

Si deux vignettes à 2 s d'écart ne suffisent pas à comprendre une transition,
relancer avec `--pas 1`.

### 4. Écrire le modèle

Créer `templates/<slug>.md` avec `templates/_modele.md` comme gabarit. Règles :

- décrire la **structure** (temps, rôle de chaque bloc, procédé de montage),
  pas le texte du créateur : pas plus d'une citation courte pour illustrer l'accroche ;
- chaque bloc a une durée cible en secondes et un procédé de montage identifiable ;
- noter ce qui est **reproductible avec les moyens de Franck** (seul, téléphone,
  pas de tournage extérieur) et ce qui ne l'est pas ;
- si un modèle existant a la même structure, compléter celui-là au lieu d'en créer un.

## B. Décliner une idée

1. Reformuler l'idée en une phrase et le message à faire retenir. Si c'est flou, demander.
2. Choisir 5-6 modèles **différents entre eux** dans `templates/` (accroches et
   procédés différents), en priorité ceux dont la performance est vérifiée.
   Écarter ceux qui ne vont pas avec l'idée plutôt que de la tordre.
3. Pour chaque reel, livrer :
   - le modèle utilisé et pourquoi il va avec cette idée ;
   - le **script** mot à mot, calé sur les blocs du modèle, dans la voix de Franck
     (tutoiement, phrases courtes, pas de jargon marketing) ;
   - la **feuille de montage** : tableau `temps | image | texte à l'écran | son`,
     avec chaque plan à tourner et chaque B-roll à récupérer ;
   - la liste des plans à tourner, regroupés par décor pour tout tourner d'une traite.
4. Écrire le tout dans `reels_declinaisons/<date>-<slug-idee>.md` et donner le chemin.

## Limites à dire franchement

- Pas de veille quotidienne automatique : ce conteneur est éphémère et Instagram
  bloque le téléchargement en masse sans compte. Le fonctionnement réaliste est :
  l'utilisateur colle 5-10 liens repérés dans la semaine, on les analyse en lot.
- Un modèle tiré d'un seul reel reste une hypothèse. Un procédé qui revient chez
  plusieurs créateurs qui surperforment est un modèle solide : le noter dans le champ
  `vu chez`.
- La structure ne fait pas la performance à elle seule : sujet, moment et compte
  comptent autant. Suivre les vues des reels déclinés et noter dans le modèle
  si ça a marché pour Franck (`résultats`).
