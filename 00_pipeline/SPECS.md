# Studio vidéo — spécifications à valider

Version 1, 27 septembre 2026. Chaque point est numéroté pour que la validation puisse dire « tout sauf le 3.2 ».

`✔` existe et testé · `◐` existe, à vérifier sur de vrais fichiers · `○` proposé, pas encore fait

---

## 1. Principe

| # | Spécification | État |
|---|---|---|
| 1.1 | Le studio vidéo suit le processus du studio journalistique : matière → brief → **plan proposé** → validation humaine → réalisation → retours → finalisation. | ✔ |
| 1.2 | **Rien ne se monte ni ne se génère avant un plan validé.** C'est la gate principale. | ✔ (règle écrite) |
| 1.3 | Aucune sortie ne part sans validation humaine (équivalent de la règle 117 du studio). | ✔ (règle écrite) |
| 1.4 | Tout reste sur l'ordinateur : aucun fichier n'est envoyé en ligne sans action explicite. | ✔ |
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

## 7. Questions ouvertes

| # | Question | Ma proposition |
|---|---|---|
| 7.1 | Où vit l'atelier à terme : page locale, ou écran dans le studio ? | Page locale tant que les vidéos restent lourdes ; portage dans le studio quand le mode Claude direct (4.9) sera voulu. |
| 7.2 | Le mode Claude direct (4.9) : par le studio (fonctions Supabase existantes) ou par une clé API dans la page ? | Par le studio, pour ne pas mettre de clé dans une page locale. |
| 7.3 | Faut-il un vrai montage (export vidéo) depuis l'atelier, ou seulement le plan ? | Seulement le plan pour l'instant ; le montage reste dans les scripts `04_montage/`. |
| 7.4 | Transcription : modèle `small` (rapide, quelques fautes) ou `medium` (plus juste, 3 fois plus lent) ? | `small` par défaut, `medium` pour les notes importantes. |

---

## Ce qu'il faut pour valider

1. Cochez ou barrez les lignes ci-dessus.
2. Tranchez les questions du § 7.
3. **Testez l'atelier avec de vrais rushes** (dossier Terra Madre) et dites-moi ce qui ne s'affiche pas : c'est le seul point que je n'ai pas pu vérifier moi-même (4.3, 4.4, 4.5).
