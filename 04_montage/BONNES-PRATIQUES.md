# Bonnes pratiques de montage — reportages verticaux (Reels, TikTok, Shorts)

Règles appliquées aux montages de Franck Monod (premier cas : `10_cern/`). Elles viennent des demandes de Franck
et des pratiques courantes des formats courts. Chaque règle renvoie à l'outil ou au code qui l'applique.

## 1. Ce que Franck a demandé (à garder pour les prochains montages)

- **La voix est libre, pas lue.** La voix off s'enregistre en mode « Repères » (`10_cern/enregistrer.html`) :
  quelques mots-pistes par séquence, on parle naturellement. Le texte intégral est une option, pas la règle.
- **On garde l'essentiel.** Les reprises, faux départs et phrases dites deux fois sont coupés
  (`tools/couper-voix.py`, listes `EXCLURE` et `RETIRER`). Quand Franck se reprend (« 140… 140 organismes »),
  on garde la deuxième fois.
- **Les erreurs de fond sont retirées**, même au milieu d'une phrase (« Alcotra » : le projet est Interreg
  France – Suisse). Coupe franche, sans respiration.
- **La vidéo filmée avec la voix sert au montage.** Chaque prise est filmée à la webcam en même temps que le son ;
  les plans face caméra viennent de cette prise, montée exactement comme la voix (`tools/face-voix.py`).
- **L'image est corrigée, pas détourée.** Lumière éclaircie et réchauffée automatiquement sur le VPS
  (`ops/vps/traiter-prises.sh`) ; pas de fond vert virtuel.
- **Un article ancien est présenté comme ancien.** En fin de vidéo, on ne dit pas « à lire » mais
  « Relisez l'article sur le projet », avec sa date et son contexte (« publié le 15 mai 2026, quatre mois avant la
  journée »). La page réelle défile à l'écran (capture de l'article, `tools/preparer-medias.sh`).
- **Pas de zoom pour faire apparaître un titre sur une image** : on retouche l'image (titre effacé) et on enchaîne
  deux plans (cas du « Grant-marci »).
- **Un son n'entre dans le montage que s'il est pertinent pour ce montage**, même s'il est dans la bibliothèque.
- **Une bibliothèque de montage validée à la main.** Effets sonores, musiques et effets graphiques sont proposés
  en sélection ; Franck garde ou rejette. Seul ce qui est validé entre dans la bibliothèque (section 6).

## 2. Sous-titres

Outil : `10_cern/tools/sous-titres.py` (depuis `voix-mots.json`), style dans `10_cern/index.html` (`.st`).

- **Des groupes de mots, jamais la phrase.** 1 à 3 mots, une seule ligne, 20 caractères au plus. Coupe aux
  pauses (plus de 0,4 s), à la ponctuation et aux changements de plan.
- **Pas de petit mot en fin de groupe** (de, du, la, à, et, un…) : il passe au début du groupe suivant.
- **Les expressions restent entières** : Grand Genève, Pays de Gex, Cé qu'è lainô, Laetitia Picard…
- **Un mot-clé au plus par groupe, et peu de mots-clés en tout** (environ un groupe sur trois) : noms propres,
  chiffres, idées fortes. Il est plus gros (1,3×) et posé sur un bloc bleu Savoie. Si tout est souligné,
  rien ne ressort.
- **Le mot prononcé s'allume**, les autres restent légèrement atténués.
- **Chaque groupe apparaît avec un petit « pop »** (échelle 0,86 → 1 en 0,14 s).
- **Pas de ponctuation affichée**, sauf ? et !
- **Lisibilité** : 66 px, gras, blanc avec ombre sur les images ; texte sombre sur les plans clairs (`CLAIRS`).
- **Zone sûre** : entre 1400 et 1620 px de haut (sur 1920), au-dessus de l'interface des Reels ;
  descendue (`BAS`) quand le bas de l'image porte déjà du texte.
- **Pas de sous-titres pendant un titre déjà à l'écran qui dit la même chose** (le hook).

## 3. Rythme visuel

Code : bloc `cadrages` dans `10_cern/index.html`.

- **Quelque chose change toutes les 2 à 4 secondes** : un plan, un zoom, un titre, un chiffre qui compte.
- **Jamais d'image figée** : chaque plan a un mouvement lent (poussée de 3 à 5 % sur toute sa durée ;
  cartes et photos en travelling lent).
- **Face caméra : le « punch-in ».** À chaque nouvelle idée ou mot fort, zoom sec de 15 à 20 % cadré sur le visage
  (comme une deuxième caméra), puis retour au plan large quand l'idée change. Une question se pose serrée,
  la réponse commence large.
- **Face caméra en petites doses** (4 à 6 s) : le visage installe la parole, les images la prouvent.
- **Les titres d'un plan arrivent après le visage**, jamais cachés dessous.
- **Transition sobre** : flash blanc bref (0,07 s d'entrée, 0,35 s de sortie) sur les changements de plan.
- **Accroche en moins de 2 s** : le sujet en une phrase, sur une image forte.

## 4. Voix

Outil : `10_cern/tools/voix-finale.sh`. Style reportage : voix proche, naturelle, intelligible sur un téléphone ;
aucun effet voyant (pas de réverbération, pas de voix radio saturée).

1. Passe-haut 80 Hz : souffle, bruits de pied de micro.
2. Réduction de bruit légère (8 dB) : on garde le grain de la pièce.
3. −2 dB vers 250 Hz : moins de « boue ».
4. +2,5 dB vers 3,5 kHz : présence ; +1 dB au-dessus de 10 kHz : air.
5. De-esser : adoucit les « s ».
6. Compression douce 3:1 : voix régulière sans effet de pompe.
7. Volume final −16 LUFS, crête −1,5 dB (niveau des réseaux sociaux).

Au montage : respirations ramenées à 0,35 s, pauses un peu plus longues entre deux idées (`couper-voix.py`).

## 5. Musique et effets sonores

- **Musique de fond instrumentale** (pas de paroles sous une voix). Environ −32 LUFS sous la voix (16 dB
  en dessous), elle remonte sur le carton final quand la voix s'arrête, fondu d'entrée et de sortie
  (`tools/preparer-medias.sh`).
- **Un effet sonore doit être justifié par l'image** : il accompagne quelque chose qu'on voit (une photo qui
  apparaît → déclencheur ; une page qui glisse → papier ; une révélation → montée). Pas d'ambiance de foule sur un
  plan où l'on est seul : un son qui ne correspond pas à l'image sonne faux. (Demande de Franck.)
- **Effets sonores rares et doux** : un « whoosh » léger sur une vraie transition, un « pop » discret sur un
  titre, un compteur sur des chiffres. Jamais sur chaque coupe. Style reportage, pas dessin animé.
- **Licences** : seulement des sons libres pour la publication (Mixkit, Freesound CC0). La bibliothèque de CapCut
  ne peut pas être récupérée ni réutilisée hors de CapCut. Les fichiers restent hors du dépôt public
  (la licence Mixkit interdit de les redistribuer seuls) : on garde l'adresse de la source.

## 6. Bibliothèque de montage

- Les candidats (sons, musiques, effets graphiques) sont proposés sur une page de sélection ; Franck écoute,
  garde ou rejette.
- Ce qui est validé est noté dans `04_montage/bibliotheque.json` (nom, catégorie, source, licence, usage).
  Les fichiers eux-mêmes vont dans Google Drive (`Vidéos/bibliotheque/`), pas dans le dépôt.

## 7. Chaîne de fabrication (10_cern)

```bash
python3 tools/couper-voix.py voix-off/<prise>.wav voix-off/voix-montee.wav voix-montee.json
bash tools/voix-finale.sh                 # voix traitée -> assets/voix-off.mp3
npx hyperframes transcribe ...            # mots -> voix-mots.json (orthographe corrigée à la main)
python3 tools/sous-titres.py              # sous-titres dans index.html
bash tools/preparer-medias.sh             # face caméra, capture de l'article, musique (hors dépôt)
npx hyperframes check && npx hyperframes render -o renders/cern-reportage.mp4
```
