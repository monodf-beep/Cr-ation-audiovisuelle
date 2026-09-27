# Processus de création vidéo

Ce processus reprend celui du studio journalistique (`studio-cultura-sabauda`), étape par étape. Le principe est le même : **l'IA propose un plan, l'humain le valide, et rien ne se monte avant cette validation.** Ensuite, le montage suit le plan validé à la lettre.

| Studio (article) | Vidéo | Ce que l'humain valide |
|---|---|---|
| 0. Sujets proposés | **0. Rushes** : inventaire et métadonnées | ce qu'on garde, ce qu'on écarte |
| 1. Brief : voix, langue, sources | **1. Brief** : format, style, ordre souhaité | le cadre |
| 2. Plan (passe 1) | **2. Plan proposé** | **la gate principale** |
| 3. Rédaction (passe 2) | **3. Montage** sur le plan validé | — |
| 4. Retouches en diff, analyse, relecture | **4. Retours** par version, contrôle | chaque changement |
| 5. Finalisé, puis export | **5. Finalisation** | la sortie |
| Comparateur v1/v2 | **Journal de retours**, puis bibles | les règles qui restent |

---

## 0. Rushes — l'équivalent des sujets proposés

### L'atelier : la vue d'ensemble

*Si le dossier est sur Google Drive, installez « Google Drive pour ordinateur » : le dossier apparaît alors comme un dossier ordinaire, et l'atelier l'ouvre directement.*

Ouvrez `00_pipeline/atelier/index.html` dans Chrome, Edge ou Safari. Il n'y a rien à installer, et les fichiers restent sur votre ordinateur.

- **Ouvrir un dossier**, ou le glisser sur la page. Toutes les photos et vidéos apparaissent, sous-dossiers compris, regroupées en moments de tournage.
- **Aperçu** : une vignette par fichier, qui est la première image pour une vidéo, avec la durée. Un clic ouvre le lecteur ; les flèches passent au rush suivant ou précédent.
- **Métadonnées** : l'heure de prise de vue est lue dans le fichier (EXIF, QuickTime Apple, MP4), sinon dans son nom. Chaque rush affiche la fiabilité de cette heure ; la source s'affiche au survol.
- **Deux modes** :
  - **Je choisis** : vous ajoutez les rushes au montage avec « + » ou par glisser-déposer, puis vous les réordonnez à la main.
  - **Confiance à Claude** : un premier tri automatique écarte les doublons, les vidéos de moins d'une seconde et les rafales, et met le reste dans l'ordre. « Préparer l'envoi à Claude » télécharge un fichier avec une vignette et les métadonnées de chaque rush. Claude y répond par un plan, que vous réimportez avec « Importer le plan de Claude ».
- **Ordre chronologique** : un bouton trie le montage selon l'heure de prise de vue, à tout moment. Les rushes sans heure fiable passent en fin de liste.
- **Exporter le plan** : produit un `plan.json` au format de l'étape 2.

L'ordre du montage est gardé dans le navigateur d'une session à l'autre.

### Les notes vocales : le ressenti sur le moment

Sur place, on ne sent pas les choses comme derrière l'ordinateur. Une note vocale enregistrée sur le moment garde ce ressenti. Elle est horodatée, comme une photo, donc elle se range toute seule dans le moment qu'elle commente.

**Sur place**, enregistrez dans le même dossier que les rushes (Dictaphone de l'iPhone, Enregistreur Android) :

- **ce que vous ressentez**, l'ambiance, l'odeur, le bruit, ce qui vous surprend : c'est la matière du script ;
- **ce qui compte** : « là, c'est le moment fort », « ce plan-là, c'est l'ouverture » ;
- **les noms, en les épelant**, et les chiffres entendus : on les vérifiera, mais au moins on les aura.

Envoyez les notes **en fichier** (AirDrop, Drive, câble), **pas par WhatsApp**, qui efface l'heure d'enregistrement.

**De retour à l'ordinateur**, on transcrit sur la machine, sans rien envoyer en ligne :

```
pip install faster-whisper
python3 00_pipeline/notes.py DOSSIER --mots "Terra Madre, Slow Food, piémontais, tomme"
```

- `--mots` donne d'avance les noms propres du lieu, qui sont alors bien mieux reconnus.
- Le script écrit un `.txt` à côté de chaque note. Vous pouvez le corriger à la main : il ne sera plus écrasé.
- Il produit aussi un `carnet-de-bord.md` : toutes les notes dans l'ordre, avec leur heure.

**Dans l'atelier**, chaque note s'affiche dans son moment, avec son extrait. Le lecteur joue l'audio et montre le texte entier.

**À quoi elles servent :**

| Étape | Usage de la note |
|---|---|
| Plan (étape 2) | l'angle, et le choix des moments forts (« c'est le moment fort de la journée ») |
| Script | les mots de l'auteur plutôt que ceux de l'IA |
| Montage | une vraie voix off, puisque la note elle-même peut être montée : Claude signale les phrases qui s'y prêtent |

Les faits qu'une note cite (noms, chiffres, dates) sont **à vérifier**, comme une source. Une note est un témoignage, pas une preuve : c'est la règle « pas de faits inventés ».

### Le script : la même lecture, en ligne de commande

Pour le studio, la matière première, ce sont les sources. Pour une vidéo, ce sont les photos et les vidéos. On commence par les inventorier :

```
python3 00_pipeline/rushes.py CHEMIN/VERS/RUSHES --sortie 00_pipeline/rushes
```

Pour chaque fichier, le script lit la **date de prise de vue** et note d'où elle vient. Il lit aussi l'appareil, le GPS, la durée, le format et la rotation. Il remet ensuite les fichiers dans l'ordre et les regroupe en **moments** : un moment s'arrête après plus de 20 minutes sans prise de vue (`--ecart`).

| Fiabilité | Source de la date | Ce qu'on en fait |
|---|---|---|
| haute | EXIF ou QuickTime, avec fuseau horaire | placée automatiquement |
| moyenne | EXIF sans fuseau, ou nom de fichier horodaté (`IMG_20260813_213012`) | placée, à vérifier |
| basse | date seule (WhatsApp), ou date de modification du fichier | laissée **hors chronologie**, dans `a_placer` |

Les pièges signalés automatiquement :

- **WhatsApp efface les métadonnées.** Il faut demander les fichiers originaux, ou un transfert par AirDrop, Drive ou câble.
- **Plusieurs appareils** : leurs horloges ne concordent jamais exactement. Filmez une même horloge avec chaque appareil, puis corrigez avec `--decalage "Canon EOS 250D=-00:04:30"`.
- **Les doublons**, repérés par une même date et une même taille.
- **Les vidéos Android et les exports** sont horodatés en UTC. Le script les ramène à l'heure locale (`--tz`, par défaut `Europe/Paris`).

Aucun outil n'est obligatoire, mais le résultat est meilleur avec `exiftool` (qui lit tout, y compris le HEIC et les RAW). Sans lui, le script utilise `ffprobe` ou `ffmpeg` pour les vidéos, Pillow pour les photos, puis le nom du fichier.

## 1. Brief

À fixer avant tout plan :

- **Sujet** et **format** : ratio, durée, plateforme.
- **Style** : c'est la « voix ». Ici, ce sont `02_prompts/` et les règles non négociables de `00_retours/retours-client.md`.
- **Ordre souhaité** :
  - **chronologique** : l'inventaire fournit directement la proposition ;
  - **narratif**, dans un ordre choisi ;
  - **thématique**.
- **Rushes retenus** : ce sont les sources. Tout ce qui n'y figure pas devra être produit.

## 2. Plan proposé — la gate

Le plan est un JSON, sur le modèle de la passe 1 du studio :

```json
{
  "titre": "", "accroche": "les 2 premières secondes", "angle": "",
  "ancrage": "le lieu ou le moment concret par lequel on entre",
  "chute": "ce qu'on voit en dernier, et ce qui reste",
  "sequences": [
    { "titre": "Avant", "description": "", "duree_s": 11,
      "rushes_utiles": ["IMG_4411.HEIC", "IMG_4415.MOV"], "manquants": ["le maillot plié sur le banc"] }
  ],
  "avertissements": []
}
```

- **Si l'ordre est chronologique**, `rushes/plan-chrono.json` est déjà le squelette. Chaque moment devient une séquence, qu'il reste à titrer, à couper et à doser.
- **Si l'ordre n'est pas chronologique**, on propose **deux ou trois directions réellement différentes**, comme le chat du studio. Par exemple : dans l'ordre, en suspens, ou en commençant par la fin.
- **La règle de l'escalier** : on entre par un ancrage concret (le mât qui s'allume) et on sort sur ce qui reste (le dos, `FC CLUSA`). Si une vidéo n'a ni ancrage ni chute, elle ne raconte rien. C'est le reproche « tu ne racontes pas d'histoire ».
- **Les avertissements vont en tête** : rushes sans date, trou dans la chronologie, séquence sans aucun rush.

Rien ne se monte ni ne se génère avant la mention **« Plan validé »**.

## 3. Montage sur le plan validé

Le montage respecte **exactement** les séquences du plan, comme la passe 2 du studio respecte les H2. Là où il n'y a pas de rush, on pose un marqueur `[rush manquant]` au lieu d'improviser. Ensuite, chaque manque devient une ligne de production, dans cet ordre de préférence :

1. **une photo ou une vidéo réelle** à prendre (c'est toujours la meilleure option) ;
2. **la reprise d'un plan déjà validé** comme référence ;
3. **une génération**, uniquement via une fiche de plan : voir [`avant-de-generer.md`](avant-de-generer.md) et [`fiche-plan.exemple.json`](fiche-plan.exemple.json).

## 4. Retours, version par version

Chaque retour est noté dans `00_retours/retours-client.md` avec son état. Chaque correction produit une nouvelle version, qu'on compare à la précédente, comme les propositions en diff du studio.

**Relecture avant de livrer**, l'équivalent de la liste en huit points du studio :

- [ ] L'ordre suit le plan validé, et la chronologie ne revient jamais en arrière sans raison.
- [ ] Aucun fait inventé : pas de date, pas de score, pas de lieu non vérifiés.
- [ ] Chaque texte visible à l'écran, vérifié au zoom, caractère par caractère.
- [ ] La saison, l'heure et la lumière sont cohérentes d'un plan à l'autre.
- [ ] Le lieu : le contrôle de cohérence de `02_prompts/bible-stade.md`.
- [ ] Aucun visage non consenti.
- [ ] Le public est cohérent : même effectif, même position, progression dans le bon sens.
- [ ] L'ancrage à l'ouverture et la chute à la fin sont bien là.

## 5. Finalisation

Comme la règle 117 du studio : **aucune sortie ne part sans validation humaine.** Un retour qui revient deux fois ne reste pas dans le journal : il devient une règle dans la bible concernée. C'est l'équivalent du comparateur v1/v2, qui nourrit la voix.
