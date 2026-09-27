# Studio vidéo — spécifications à valider

Version 1.2, 27 septembre 2026. Page de décision : https://claude.ai/artifact/4hNsiGBoGukLUoBq8Qu9NK Chaque point est numéroté pour que la validation puisse dire « tout sauf le 3.2 ».

`✔` existe et testé · `◐` existe, à vérifier sur de vrais fichiers · `○` proposé, pas encore fait

---

## 1. Principe

| # | Spécification | État |
|---|---|---|
| 1.1 | Le studio vidéo suit le processus du studio journalistique : matière → brief → **plan proposé** → validation humaine → réalisation → retours → finalisation. | ✔ |
| 1.2 | **Rien ne se monte ni ne se génère avant un plan validé.** C'est la gate principale. | ✔ (règle écrite) |
| 1.3 | Aucune sortie ne part sans validation humaine (équivalent de la règle 117 du studio). | ✔ (règle écrite) |
| 1.4 | Tout reste sur l'ordinateur : aucun fichier n'est envoyé en ligne sans action explicite. | ✔ · **à réécrire après 8.1** (si 8.5 = Drive : « les rushes restent dans Drive, le studio ne garde que le léger ») |
| 1.5 | Le studio journalistique n'est pas modifié. Un portage éventuel viendra après. | ✔ |

## 2. Matière : le dossier de rushes

| # | Spécification | État |
|---|---|---|
| 2.1 | Un seul dossier (local ou Google Drive synchronisé) contient photos, vidéos **et notes vocales**, sous-dossiers compris. | ✔ |
| 2.2 | Formats photo : jpg, png, heic, webp, tiff, dng. Vidéo : mp4, mov, m4v, webm, mkv, avi, 3gp, mts. Audio : m4a, mp3, wav, aac, ogg, opus, amr, flac, caf. | ✔ |
| 2.3 | Pour chaque fichier, on lit : heure de prise de vue, appareil, GPS, durée, format, rotation. | ✔ |
| 2.4 | L'heure est prise dans cet ordre : EXIF/QuickTime → nom du fichier horodaté → date du fichier. Chaque rush affiche la **fiabilité** de son heure (haute / moyenne / basse) et sa source. | ✔ |
| 2.5 | Les vidéos horodatées en temps universel (Android, exports) sont ramenées à l'heure de Paris. | ✔ |
| 2.6 | Un rush sans heure fiable n'entre pas dans la chronologie : il est mis à part, « à placer à la main ». | ✔ |
| 2.7 | Les rushes sont regroupés en **moments** : un nouveau moment commence après N minutes sans prise de vue (20 par défaut, réglable). | ✔ |
| 2.8 | Alertes automatiques : fichiers passés par WhatsApp (métadonnées effacées), plusieurs appareils (horloges à comparer), doublons, aperçus impossibles. | ✔ |
| 2.9 | Correction d'horloge par appareil (`--decalage`) quand deux appareils ne sont pas à la même heure. | ✔ (script) ○ (atelier) |

## 3. Notes vocales

| # | Spécification | État |
|---|---|---|
| 3.1 | Une note vocale est un rush comme un autre : horodatée, elle se range dans le moment qu'elle commente. | ✔ |
| 3.2 | Transcription **sur l'ordinateur** (faster-whisper), jamais en ligne. Modèle `small` par défaut. | ✔ |
| 3.3 | Les noms propres du lieu peuvent être donnés d'avance (`--mots`) pour être bien reconnus. | ✔ |
| 3.4 | Le texte est écrit dans un `.txt` à côté de la note. Corrigé à la main, il n'est plus écrasé. | ✔ |
| 3.5 | Un `carnet-de-bord.md` rassemble toutes les notes dans l'ordre, avec leur heure. | ✔ |
| 3.6 | Une note est un **témoignage**, pas une source : les noms, chiffres et dates qu'elle cite sont à vérifier. | ✔ (règle écrite) |
| 3.7 | Les notes ne vont jamais d'office dans le montage ; elles nourrissent l'angle, le script, et peuvent devenir voix off. | ✔ |
| 3.8 | Lancement de la transcription depuis l'atelier, sans ligne de commande. | ○ |

## 4. L'atelier (page locale)

| # | Spécification | État |
|---|---|---|
| 4.1 | S'ouvre dans Chrome, Edge ou Safari, sans installation. Ouverture d'un dossier par bouton ou par glisser-déposer. | ✔ |
| 4.2 | **Vue d'ensemble** : tous les rushes, par moment, avec vignette, heure, fiabilité, durée. | ✔ |
| 4.3 | Vignette vidéo = première image. Vignette note vocale = extrait de la transcription. | ✔ (webm) ◐ (mp4/mov, non lisibles dans mon navigateur de test) |
| 4.4 | **Lecteur** : clic sur un rush → lecture de la vidéo, de la photo ou de l'audio, avec métadonnées et transcription. Flèches ← → pour passer au suivant. | ✔ ◐ (m4a) |
| 4.5 | Photos HEIC : aperçu dans Safari seulement. | ◐ |
| 4.6 | **Mode « Je choisis »** : ajout au montage par « + » ou par glisser-déposer ; réordonnancement par glisser-déposer. | ✔ |
| 4.7 | **Bouton « Ordre chronologique »** : trie le montage selon l'heure de prise de vue ; les rushes sans heure fiable passent en fin. | ✔ |
| 4.8 | **Mode « Confiance à Claude »** : tri automatique d'abord (doublons, vidéos < 1 s, rafales écartés), puis export d'un fichier pour Claude, puis import de sa réponse. | ✔ |
| 4.9 | Le mode Claude est direct : la page interroge Claude elle-même, sans aller-retour de fichiers. | ○ (nécessite le studio ou une clé API) |
| 4.10 | **Export du plan** (`plan.json`) au format de l'étape 5. | ✔ |
| 4.11 | L'ordre du montage est conservé d'une ouverture à l'autre (dans le navigateur). | ✔ |
| 4.12 | Fonctionne sur téléphone (largeur 390 px), thème clair et sombre. | ✔ |

## 5. Le plan (la gate)

| # | Spécification | État |
|---|---|---|
| 5.1 | Format : titre, accroche, angle, **ancrage** (par quoi on entre), **chute** (ce qui reste), séquences (titre, description, durée, rushes utiles, manquants), avertissements. | ✔ |
| 5.2 | Ordre chronologique : le plan est déduit des moments. Autre ordre : Claude propose **2 ou 3 directions réellement différentes**. | ✔ (règle) ○ (outil) |
| 5.3 | Règle de l'escalier : pas de plan sans ancrage ni chute. | ✔ (règle) |
| 5.4 | Les avertissements sont en tête : rushes sans heure, trous, séquence sans rush. | ✔ |
| 5.5 | Le plan est **validé** par une mention explicite avant tout montage. | ✔ (règle) |

## 6. Réalisation, retours, finalisation

| # | Spécification | État |
|---|---|---|
| 6.1 | Le montage respecte exactement les séquences du plan. Un manque devient `[rush manquant]`, jamais une improvisation. | ✔ (règle) |
| 6.2 | Ordre de préférence pour un manque : photo/vidéo réelle → reprise d'un plan validé → génération avec fiche de plan. | ✔ |
| 6.3 | Fiche de plan obligatoire avant toute génération (`fiche-plan.exemple.json`). Prompt assemblé à partir des bibles, jamais réécrit. | ✔ |
| 6.4 | Chaque retour est noté avec son état ; chaque correction est une version comparée à la précédente. | ✔ (règle) |
| 6.5 | Relecture en 8 points avant livraison (ordre, faits, textes à l'écran, saison, lieu, visages, public, ancrage/chute). | ✔ |
| 6.6 | Un retour qui revient deux fois devient une règle dans la bible concernée. | ✔ (règle) |

## 9. Comptes et collaboration (votre demande du 27/09)

Tous `○`. Calqué sur le studio journalistique (comptes sur invitation, rôles, journalistes rattachés à un média), avec en plus le projet partagé.

| # | Spécification | État |
|---|---|---|
| 9.1 | Chaque journaliste a son compte, sur invitation, comme dans le studio articles (les mêmes comptes si 8.6 = module). | ○ |
| 9.2 | Un projet vidéo appartient à un média ; son créateur peut y ajouter d'autres journalistes. | ○ |
| 9.3 | Rushes, notes vocales, plan et versions sont partagés entre les membres du projet. | ○ |
| 9.4 | Un seul journaliste édite à la fois ; les autres voient qui édite et peuvent commenter. | ○ |
| 9.5 | Prendre le relais : un bouton qui prévient l'éditeur en cours ; la main passe sans rien perdre. | ○ |
| 9.6 | Chaque version porte son auteur : on sait qui a changé quoi, et on peut revenir à une version. | ○ |
| 9.7 | Les voix (VOIX.md) et les bibles appartiennent au média : tous ses journalistes les partagent. | ○ |

## 10. Traitements sur le serveur (DaVinci écarté le 27/09)

Resolve ne tourne que sur un ordinateur avec une bonne carte graphique, hors du studio en ligne, et Claude ne peut pas le piloter. Les traitements se font donc sur le serveur du studio : un navigateur suffit, et ils marchent aussi en mode « Je fais confiance ».

| # | Spécification | État |
|---|---|---|
| 10.1 | Look commun en LUT (`03_etalonnage/look-pellicule.cube`, généré par `lut.py` depuis `filmlook.split_tone`) : écart avec le script ≤ 3/255, lu par ffmpeg (`lut3d`). | ✔ |
| 10.2 | Couleurs accordées entre appareils : balance des blancs et exposition corrigées plan par plan, sur un plan de référence. | ○ |
| 10.3 | Visages floutés automatiquement là où le cadrage ne suffit pas. | ○ |
| 10.4 | Voix des notes vocales nettoyée (bruit de fond) et volume mis à niveau. | ○ |
| 10.5 | Stabilisation des images de téléphone. | ○ |
| 10.6 | Grain, halation et vignettage appliqués après le LUT, comme dans `filmlook.py` (un LUT ne porte que la couleur pixel par pixel). | ○ |

## 7. Ajouts proposés après veille (voir `VEILLE.md`)

Tous `○`. À valider un par un.

| # | Spécification | Origine |
|---|---|---|
| 7.1 | **Storyboard visuel sur gabarit**, produit à partir du plan validé et avant tout rendu : une case par séquence, avec la vignette du rush ou un cadre vide pour un manque. `05_storyboard/gen.py` sert de base. | Chase AI |
| 7.2 | **Beat sheet** : le plan porte, par séquence, le time-code de début et de fin, l'action en une ligne et le mouvement. C'est ce qui nourrit le prompt d'animation. Notre découpage 22 plans / 36 s en est déjà un ; on en fait le format standard. | Chase AI |
| 7.3 | **Retouches par composant** : un retour vise le graphisme, le son ou la musique, jamais « refais tout ». Budget de **deux ou trois itérations** par version, annoncé d'avance. | Chase AI, motion-graphics-skill |
| 7.4 | **Contrôle après rendu** : comparer chaque séquence rendue à sa ligne du beat sheet ; ne refaire que celles qui dévient, en reprenant leur fiche. | Chase AI |
| 7.5 | **Bibliothèque de références classée par type de film** (présentation produit, ambiance de lieu, événement, typographie), avec ce qu'on retient de chacune. Un plan cite sa référence. | Chase AI, motion-graphics-skill |
| 7.6 | **Brief de style avant tout rendu** : 3 directions candidates réellement différentes, 1 recommandation, une palette où chaque couleur dit d'où elle vient (maillot, drapeau, stade). La direction retenue de chaque film est notée pour ne pas la répéter au suivant. | motion-graphics-skill |
| 7.7 | **Contrôles anti-diaporama** ajoutés à la relecture : pas de suite de fondus, un sujet qui persiste, deux niveaux de texte maximum, transitions variées, texte lisible sur téléphone (≥ 30 px sur 1080). | motion-graphics-skill |
| 7.8 | **Le montage reste modifiable** : `plan.json` et `coupes.json` sont la source, jamais un export aplati. Toute correction repart d'eux. | Higgsfield |
| 7.9 | **`VOIX.md` par client**, collecté par interview (une question à la fois, huit questions), relu et signé avant tout script. Contient « ce que ça ne doit jamais être ». | social-agents |
| 7.10 | **Étape couverture** dans la finalisation : image réelle du film, texte uniquement dans les 240 px du bas, contrôle de la fenêtre 3:4 et de l'orthographe. | social-agents |
| 7.11 | **Discipline de diffusion** si une étape publication est ajoutée : un fuseau par lot, jamais de date passée corrigée en silence, jamais de légende inventée. | social-agents |
| 7.12 | **`INDEX.md` des bibles et règles**, à consulter avant toute tâche jamais faite. | social-agents |

## 8. Questions ouvertes

| # | Question | Ma proposition |
|---|---|---|
| 8.1 | Où vit l'atelier à terme : page locale, ou écran dans le studio ? | **Tranché le 27/09 : dans le studio.** La plateforme doit être utilisable par d'autres personnes, comme le studio journalistique. La page locale reste comme prototype. |
| 8.2 | Comment le studio fait appel à Claude, et combien ça coûte ? | Les deux : l'API du studio par défaut (même clé et même facture que les articles ; environ 0,30 à 0,50 $ par vidéo, un plan à 0,12 $ puis 3 à 5 corrections à 0,06 $, estimation à mesurer), et l'export gratuit « Préparer l'envoi à Claude » gardé en secours, via le forfait de chacun. Un forfait personnel ne peut pas servir de moteur à une plateforme multi-comptes. |
| 8.3 | Faut-il un vrai montage (export vidéo) depuis l'atelier, ou seulement le plan ? | Seulement le plan pour l'instant ; le montage reste dans les scripts `04_montage/`. |
| 8.5 | Où restent les rushes : dans Google Drive, ou envoyés dans le stockage du studio ? | Dans Drive. Le studio lit le dossier et ne garde que le léger (vignettes, heures, transcriptions) : aucun envoi de Go depuis le terrain. |
| 8.6 | Un module « Vidéo » dans le studio existant, ou une application séparée ? | Un module dans le studio : mêmes comptes, mêmes voix, mêmes fonctions Claude, parcours articles inchangé. |
| 8.7 | Deux modes de travail ? | **Proposé par vous le 27/09 : deux modes.** « Je maîtrise » : toutes les étapes, vous validez le plan. « Je fais confiance » : Claude fait brief, plan et montage, vous corrigez la vidéo en texte (« plus court », « retire le plan 7 »). Dans les deux modes, le plan existe (Claude applique vos demandes dessus, vous pouvez reprendre la main) et rien ne sort sans votre accord final (1.3). |
| 8.8 | Qui voit un projet vidéo : tout le média, ou le créateur et les journalistes qu'il ajoute ? | Le créateur et les membres ajoutés, les admins du média voient tout. C'est le modèle des articles, qui appartiennent à leur auteur. |
| 8.9 | Deux journalistes sur la même vidéo : un à la fois avec passage de relais, ou en même temps ? | Un à la fois : « Marie édite en ce moment », bouton « Prendre le relais » qui la prévient. Aucun conflit, bien plus simple que l'édition simultanée. |
| 8.10 | DaVinci Resolve pour l'étalonnage ? | **Tranché le 27/09 : non.** Traitements sur le serveur du studio (§ 10). |
| 8.4 | Transcription : modèle `small` (rapide, quelques fautes) ou `medium` (plus juste, 3 fois plus lent) ? | `small` par défaut, `medium` pour les notes importantes. |

---

## Ce qu'il faut pour valider

1. Cochez ou barrez les lignes ci-dessus.
2. Tranchez les questions du § 8.
3. **Testez l'atelier avec de vrais rushes** (dossier Terra Madre) et dites-moi ce qui ne s'affiche pas : c'est le seul point que je n'ai pas pu vérifier moi-même (4.3, 4.4, 4.5).
