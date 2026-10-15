# Décidia 2026 — « L'IA ? L'humain garde la main »

Reportage vertical (Reels, LinkedIn) de l'atelier **« Vendre mieux avec l'IA : l'humain garde la main »**,
salon Décidia, Savoiexpo (Chambéry), 15 octobre 2026, avec Rony Dray, la French Tech Alpes et Savoy IA.

**1080 × 1920 · 30 im/s · 49,1 s · voix off de Franck en savoyard, sous-titrée en français.**

Style « Reportage Franck » repris du reportage CERN (`10_cern/`, branche `claude/hyperframe-installation-o3hduz` :
`styles/reportage-franck.md`, `04_montage/BONNES-PRATIQUES.md`, `04_montage/bibliotheque.json`) : bleu Savoie
`#0a36af` seul accent, Semplicità Pro, Cormorant Garamond, sous-titres par groupes avec mot-clé en bloc bleu,
flash blanc, punch-in, poussée lente, cercle qui se dessine, bandeau nom. Montage HyperFrames (HTML + GSAP).

## Découpage

| Temps | Séquence | Image | Son |
|---|---|---|---|
| 0,0 – 1,9 | Accroche « L'IA ? L'humain garde la *main* » sur un bandeau encre | affiche officielle de Décidia (format Story du kit intervenant) | musique |
| 1,9 – 4,6 | Franck salue, Rony répond « *Arvi* ! », bandeau nom | selfie du duo | son direct |
| 4,6 – 9,4 | « Aujourd'hui, j'étais au salon Décidia avec la French Tech et Savoy IA » | allée du hall A, comptoirs Décidia, stand French Tech + logo, sphère Savoy IA | voix, pops |
| 9,4 – 16,6 | « …pour une conférence sur l'IA adaptée à l'entreprise » | programme des conférences ; la salle + titre de l'atelier, et sur « l'intelligence artificielle », *Enteligença* puis *artificèla* claquent en savoyard (lettres qui se décodent, traduction dessous) ; stand du Chambéry Savoie Mont Blanc Handball, cabine du Téléphérique du Salève (nommés) | déclencheur photo, pops |
| 16,6 – 20,1 | « C'est utiliser la capacité, les compétences métiers avant tout » | stand du traiteur, la scène | |
| 20,1 – 28,5 | « …et ajouter l'IA en plus, pour une couche supplémentaire » | motion design : la carte *Enteligença artificèla* se pose sur *Compétences métiers* ; sur « en plus », punch-in et elle se décode en *Intelligence artificielle* ; la pile s'ouvre | papier, clic |
| 28,5 – 34,0 | « Nous avons parlé de tout le cycle, marketing et communication » | motion design : l'anneau éclot, les cinq étapes du cycle de vie client (Attraction, Acquisition, Développement, Fidélisation, Réactivation, d'après clustdoc.com) claquent au centre et volent sur l'anneau, une comète les suit ; *Marketing* puis *Communication* claquent ; le cycle file vers la caméra | whoosh, clics, pops |
| 34,0 – 39,0 | « Tu sais ce que ça veut dire, la rioule ? — C'est faire la fête, la bambouche ! » | stand « Traiteur La Rioule » (image remise à l'endroit), cercle sur l'enseigne | son direct |
| 39,0 – 42,7 | « Grant-marci à Rony et à tous ! » | la scène, titre Cormorant | voix |
| 42,7 – 44,9 | « À bientôt ! », main levée | selfie de Franck | son direct |
| 44,9 – 49,1 | Carton final : titre de l'atelier, logos French Tech Alpes et Savoy IA (fond transparent, nom en encre comme sur savoy-ia.fr), hashtag *#EnteligençaArtificèla* qui se décode | | montée, musique |

Voix off : les nouvelles prises de Franck (`rushes/audio_1.aac` : phrases 1 et 2, `audio_2.aac` : phrases 3 et 4,
`audio_3.aac` : phrase 5), plus posées et plus fortes que la prise de 15 h 18, dont on garde seulement le
« Grant-marci » (phrase 6, absente des nouvelles prises). `tools/couper-voix.py` coupe chaque phrase dans sa prise,
ramène les silences à 0,42 s (0,65 s entre deux phrases), vitesse normale (`montage.json`) ; tous les temps du montage
(plans, sous-titres, motion design) sont des mots-ancres de ces prises. Traduction : celle dictée par Franck ; la
sixième phrase (« Grant-marci a Rony é a tô ») a été reconnue à la transcription et reste à confirmer.

## Chaîne

```bash
bash tools/recuperer.sh <lien du dossier Drive « Decidia »>   # rushes, logos, sons, GSAP (hors dépôt)
# + déposer la police Semplicità Pro dans assets/fonts/ (licence commerciale)
# + déposer rushes/DEC26-Kitcom-intervenant-Story.png (kit de communication intervenant, pièce jointe du mail
#   de la French Tech Alpes du 12 octobre 2026 « Votre participation à l'atelier/conférence DECIDIA »)
python3 tools/couper-voix.py      # voix montée + voix-montee.json
bash tools/voix-finale.sh         # traitement reportage allégé, -16 LUFS -> assets/voix-off.wav
python3 tools/preparer-medias.py  # plans 1080 × 1920, son direct, photos, logo Savoy IA détouré
python3 tools/monter.py           # index.html + plan.json (tous les temps viennent de la voix)
python3 tools/bande-son.py        # mixage -> assets/bande-son.wav (-15 LUFS, musique 16 dB sous la voix)
npx hyperframes@0.8.75 check
npx hyperframes@0.8.75 render -o renders/decidia-v7.mp4
python3 tools/metriques.py renders/decidia-v7.mp4   # seuils de BONNES-PRATIQUES, rapport metriques.md
```

`index.html` est écrit par `tools/monter.py` : on modifie le script, pas le fichier.

## Sons

| Son | Statut dans la bibliothèque | Où |
|---|---|---|
| musique « Curiosity » (Mixkit) | validé | tout le film, remonte sur l'accroche et le carton final |
| ambiance de foule (Mixkit) | validé (« fond sonore d'un salon ») | images du salon seulement |
| déclencheur photo, papier, riser doux (Mixkit) | validés | photos, cartes du motion design, carton final |
| whoosh doux, pop doux, clic d'interface (Mixkit) | **proposés** pour ce montage, à garder ou écarter | transitions, logos et mots savoyards qui sautent, étapes du cycle, décodages |

Licence Mixkit : fichiers hors dépôt, adresses des sources dans `tools/recuperer.sh`.

## À vérifier par Franck

- La sixième phrase : « Grant-marci a Rony é a tô » (transcription : « Grammatie à Ronny et à Thau »).
- La salutation de Franck dans le duo, laissée sans sous-titre (transcription : « Adiato ! » ou « Adyu tô ! ») ;
  celle de Rony est sous-titrée « Arvi ! ».
- « À bientôt ! » : en français ou en savoyard dans la prise ?
- Les whoosh, pops et clics, ajoutés pour le rythme demandé ; à valider dans la bibliothèque.
- L'effet « lettres qui se décodent » (nouveau, sur *Enteligença artificèla*) : à ajouter à la bibliothèque s'il plaît.
- L'orthographe *Enteligença artificèla* et le hashtag *#EnteligençaArtificèla* (repris de Franck, comme dans ses posts
  LinkedIn).
