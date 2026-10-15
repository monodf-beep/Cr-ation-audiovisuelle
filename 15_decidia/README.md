# Décidia 2026 — « L'IA ? L'humain garde la main »

Reportage vertical (Reels, LinkedIn) de l'atelier **« Vendre mieux avec l'IA : l'humain garde la main »**,
salon Décidia, Savoiexpo (Chambéry), 15 octobre 2026, avec Rony Dray, la French Tech Alpes et Savoy IA.

**1080 × 1920 · 30 im/s · 45,5 s · voix off de Franck en savoyard, sous-titrée en français.**

Style « Reportage Franck » repris du reportage CERN (`10_cern/`, branche `claude/hyperframe-installation-o3hduz` :
`styles/reportage-franck.md`, `04_montage/BONNES-PRATIQUES.md`, `04_montage/bibliotheque.json`) : bleu Savoie
`#0a36af` seul accent, Semplicità Pro, Cormorant Garamond, sous-titres par groupes avec mot-clé en bloc bleu,
flash blanc, punch-in, poussée lente, cercle qui se dessine, bandeau nom. Montage HyperFrames (HTML + GSAP).

## Découpage

| Temps | Séquence | Image | Son |
|---|---|---|---|
| 0,0 – 1,9 | Accroche « L'IA ? L'humain garde la *main* » | accueil exposants Décidia | musique, salon |
| 1,9 – 4,2 | Franck et Rony saluent, bandeau nom | selfie du duo | son direct |
| 4,2 – 9,3 | « Aujourd'hui, j'étais au salon Décidia avec la French Tech et Savoy IA » | allée du hall A (punch-in sur *Décidia*), stand French Tech + logo, sphère Savoy IA | voix, pops |
| 9,3 – 15,6 | « …pour une conférence sur l'IA adaptée à l'entreprise » | programme des conférences, la salle + titre de l'atelier, stands d'entreprises | déclencheur photo |
| 15,6 – 18,4 | « Les compétences métiers avant tout » | stand du traiteur, la scène | |
| 18,4 – 24,6 | « …et ajouter l'IA en plus, pour une couche supplémentaire » | motion design : la carte *IA* se pose sur *Compétences métiers*, la pile s'ouvre | papier |
| 24,6 – 30,8 | « Nous avons parlé de tout le cycle, marketing et communication » | le public, puis motion design : l'anneau éclot, les cinq étapes du cycle de vie client (Attraction, Acquisition, Développement, Fidélisation, Réactivation, d'après clustdoc.com) claquent au centre et volent sur l'anneau, une comète les suit ; *Marketing* puis *Communication* claquent ; le cycle file vers la caméra | whoosh, clics, pops |
| 30,8 – 35,8 | « Tu sais ce que ça veut dire, la rioule ? — C'est faire la fête, la bambouche ! » | stand « Traiteur La Rioule » (image remise à l'endroit), cercle sur l'enseigne | son direct |
| 35,8 – 39,1 | « Grant-marci à Rony et à tous ! » | la scène, titre Cormorant | voix |
| 39,1 – 41,3 | « À bientôt ! », main levée | selfie de Franck | son direct |
| 41,3 – 45,5 | Carton final : titre de l'atelier, logos French Tech Alpes et Savoy IA | | montée, musique |

Voix off : prise de 15 h 18, six phrases (`tools/couper-voix.py`), silences ramenés à 0,3 s, accélérée ×1,1
(`montage.json`). Traduction : celle dictée par Franck ; la sixième phrase (« Grant-marci a Rony é a tô »)
a été reconnue à la transcription et reste à confirmer.

## Chaîne

```bash
bash tools/recuperer.sh <lien du dossier Drive « Decidia »>   # rushes, logos, sons, GSAP (hors dépôt)
# + déposer la police Semplicità Pro dans assets/fonts/ (licence commerciale)
python3 tools/couper-voix.py      # voix montée + voix-montee.json
bash tools/voix-finale.sh         # traitement reportage, ×1,1, -16 LUFS -> assets/voix-off.wav
python3 tools/preparer-medias.py  # plans 1080 × 1920, son direct, photos, logo Savoy IA détouré
python3 tools/monter.py           # index.html + plan.json (tous les temps viennent de la voix)
python3 tools/bande-son.py        # mixage -> assets/bande-son.wav (-15 LUFS, musique 16 dB sous la voix)
npx hyperframes@0.8.75 check
npx hyperframes@0.8.75 render -o renders/decidia-v3.mp4
python3 tools/metriques.py renders/decidia-v3.mp4   # seuils de BONNES-PRATIQUES, rapport metriques.md
```

`index.html` est écrit par `tools/monter.py` : on modifie le script, pas le fichier.

## Sons

| Son | Statut dans la bibliothèque | Où |
|---|---|---|
| musique « Curiosity » (Mixkit) | validé | tout le film, remonte sur l'accroche et le carton final |
| ambiance de foule (Mixkit) | validé (« fond sonore d'un salon ») | images du salon seulement |
| déclencheur photo, papier, riser doux (Mixkit) | validés | photos, cartes du motion design, carton final |
| whoosh doux, pop doux, clic d'interface (Mixkit) | **proposés** pour ce montage, à garder ou écarter | transitions, logos qui sautent, étapes du cycle |

Licence Mixkit : fichiers hors dépôt, adresses des sources dans `tools/recuperer.sh`.

## À vérifier par Franck

- La sixième phrase : « Grant-marci a Rony é a tô » (transcription : « Grammatie à Ronny et à Thau »).
- La salutation du duo, laissée sans sous-titre (transcription : « Adiato ! »).
- « À bientôt ! » : en français ou en savoyard dans la prise ?
- Les whoosh, pops et clics, ajoutés pour le rythme demandé ; à valider dans la bibliothèque.
- Métriques (`metriques.md`) : une alerte reste, la séquence « couche IA » tient 5,2 s sans coupe franche
  (les cartes bougent en continu) ; un punch-in sur « en plus » la ferait passer sous 4 s.
