# Veille — ce qu'on retient des autres

Chaque idée porte un verdict : `→ spec` (proposée dans `SPECS.md`, § 7), `→ déjà` (déjà dans notre processus), `✗` (écartée, avec la raison).

---

## 1. Post chase.h.ai « How to Turn GPT-6 Astra Into a Motion Designer » (sept. 2026)

Le post ne montre que sa couverture. La méthode est dans le guide de l'auteur (chaseai.io), la page Higgsfield du plugin After Effects, et un dépôt public qui applique la même méthode (`lowfatgeek/motion-graphics-skill`).

**Ce que c'est.** Un agent (Codex ou Claude Code) qui pilote After Effects par le connecteur Higgsfield : il crée les calques, les images clés, les expressions, directement dans la composition ouverte. Une variante génère la vidéo par un modèle (Seedance) au lieu d'After Effects.

### La méthode en trois étapes

| Leur étape | Ce qu'ils disent | Verdict |
|---|---|---|
| **1. Storyboard avant de construire** | « La plus grosse erreur est de sauter directement au prompt en attendant une vidéo finie. » Un storyboard visuel, sur gabarit, validé avant tout rendu. | `→ déjà` (plan validé) `→ spec 7.1` (gabarit visuel) |
| **2. L'agent écrit le prompt à partir du storyboard, découpé en *beats*** | Un beat = une scène avec sa durée. « Le storyboard est la source d'où on tire le prompt ; l'agent fait la traduction. » 15 s de film = environ 23 min de construction. | `→ déjà` (fiche de plan, prompt assemblé) `→ spec 7.2` (beat sheet avec timings) |
| **3. Corriger par prompts, pas par panneaux** | Les retouches se demandent par composant : graphisme, son, musique. Deux ou trois itérations au total. | `→ spec 7.3` |

### Le reste du dispositif

| Idée | Verdict |
|---|---|
| **Boucle d'auto-correction** : l'agent compare le rendu à l'intention et ne régénère que les sections qui dévient. | `→ spec 7.4` |
| **Bibliothèque de vidéos de référence, classée par type** (produit éclaté, typographie cinétique, explication vectorielle). | `→ spec 7.5` |
| **Brief de style avant tout code** : « 3 concepts candidats, 1 recommandation, une empreinte de structure, une palette où chaque couleur dit d'où elle vient ». | `→ spec 7.6` |
| **Structure tirée d'un menu** ; l'empreinte du projet précédent ne se répète jamais. | `→ spec 7.6` |
| **« Les exemples sont des principes, pas des scripts »** : rien n'est hérité du gabarit ni copié d'une référence. | `→ déjà` (un plan validé se reprend comme référence, jamais copié) |
| **Contrôles anti-diaporama** : pas de sections qui s'enchaînent en fondu, un sujet persistant, deux niveaux de texte maximum, transitions variées. | `→ spec 7.7` |
| **Lisible sur téléphone** : texte de 30 px minimum sur une scène de 1080. | `→ spec 7.7` |
| **Garder les calques et images clés modifiables** (ne jamais aplatir). | `→ spec 7.8` |
| **Contrôle des itérations** pour maîtriser crédits et jetons. | `→ spec 7.3` |
| Piloter After Effects par le connecteur Higgsfield. | `✗` pour l'instant : notre montage est en scripts (`04_montage/`), et le film Cluses n'a pas de motion design. À revoir si un projet en demande. |
| Génération de la vidéo entière par un modèle (Seedance). | `✗` : contraire à « les plans qui portent un texte sont des photographies ». |

## 2. Dépôt `kevinbadi/social-agents`

Prend une vidéo **déjà montée** et gère l'après : transcription, légendes, couverture, publication multi-réseaux (service payant CreatorOS), réponses aux commentaires. Il commence là où notre studio s'arrête.

| Idée | Verdict |
|---|---|
| **Pack de marque par interview**, huit questions une à une (de quoi il s'agit, ce qu'on propose, voix en trois adjectifs, *ce que ça ne doit jamais être*, emojis, hashtags, audience, concurrents), écrit dans `BRAND.md`, relu, signé. Rien ne s'écrit avant. | `→ spec 7.9` |
| **Couverture 9:16 avec la règle du recadrage 3:4** : les grilles Instagram et TikTok coupent un Reel au centre (fenêtre 1080×1440, y = 240 à 1680). La photo va dans la fenêtre, le texte d'accroche uniquement dans les 240 px du bas. Image réelle par défaut, génération en repli. | `→ spec 7.10` |
| **Relire la couverture** : orthographe des accroches, rien de coupé dans la fenêtre 3:4 ; le mot-clé prononcé est relu avec l'humain car Whisper entend mal les noms de marque. | `→ déjà` (`--mots`) `→ spec 7.10` |
| **Discipline de programmation** : un fuseau par lot, jamais de date passée corrigée en silence, arrêt si plus de la moitié des lignes sont invalides, jamais de légende inventée. | `→ spec 7.11` |
| **Index des tutoriels** consulté avant de faire une chose jamais faite. | `→ spec 7.12` |
| Automatisations cron (post quotidien, balayage des commentaires). | `✗` : contredit « rien ne part sans validation ». |
| Entonnoirs commentaire → message privé. | `✗` : marketing d'influence, hors sujet. |
| Couvertures générées avec le visage du créateur. | `✗` : « aucun visage ». |
| Publication via CreatorOS. | `✗` : service payant ; à reconsidérer si une étape diffusion est voulue. |

## Sources

- chaseai.io/blog/gpt-6-astra-after-effects-motion-design · chaseai.io/blog/gpt-6-astra-motion-design-skill
- higgsfield.ai/mcp/use-after-effects · higgsfield.ai/ai-motion-designer
- github.com/lowfatgeek/motion-graphics-skill
- github.com/kevinbadi/social-agents


---

## Lecture approfondie des dépôts (27/09)

### cth9191/motion-design (skill publique de Chase AI, sans licence)

Adapte des prompts de référence et envoie **un seul prompt découpé en séquences** à Seedance via le MCP Higgsfield. Pas de montage de rushes ni de rendu local. Le dépôt « storyboard » du post reste réservé à la communauté payante de l'auteur.

À retenir : « establish what the viewer should understand, believe or want » avant les séquences ; format du prompt (monde visuel, règles de mouvement, plans minutés, ambiance, musique) ; **inventaire des textes exacts** (→ 13.7) ; **test de sens** (sans le titre, qu'est-ce qui relie le plan à l'affirmation ?) ; **tableau de revue** exigence / plan / résultat observé au timecode / réussi, échoué, non vérifié (→ 13.8) ; une seule tentative de correction et un journal de ce qui a été soumis (→ 7.3).
Écarté : vidéo générée en entier ; fichiers non réutilisables (aucune licence, prompts de tiers).

### lowfatgeek/motion-graphics-skill (MIT)

Animations HTML/GSAP exportées en MP4 image par image (Puppeteer + ffmpeg, sans GPU).

À retenir : brief de style bloquant avant tout code (→ 7.6) ; **empreinte de structure** (concept, nombre de scènes, objets héros, accroche, chute) : deux livrables diffèrent sur 3 paramètres sur 5 ; contrôles anti-diaporama mesurables (→ 7.7) ; rendu déterministe ; **planche contact** `scripts/snap.mjs` pour que l'IA « voie » un rendu (→ 13.8) ; voix off calée sur les pauses (`silencedetect`) ; **effets sonores ajoutés après rendu** sans réencoder l'image, sidechain sous la voix, limiteur −1 dBFS, contrôle `ebur128` (→ 13.9).
Réutilisable (MIT) : `scripts/export-frames.mjs`, `scripts/snap.mjs`, `scripts/sfx-mix.mjs`, `scripts/sfx-cues.mjs`, `scripts/vo-pauses.html`. Les 20 WAV de `assets/sfx/` : usage commercial déclaré par l'auteur, à vérifier.

### kevinbadi/social-agents (MIT), lu en entier

À retenir : **interdits dans le code** (`src/client/endpoints.ts`, HARD_BLOCKS avant l'allowlist) (→ 12.8) ; un registre d'outils unique exposé par le connecteur (`src/agent/registry.ts` → `tools.ts`) (→ 12.2) ; **journal des actions** de mutation (`src/util/activityLog.ts`), à compléter avec l'utilisateur et le projet (→ 12.9) ; isolation des espaces vérifiée à l'exécution (`src/workspaces.ts`) (→ 14.6) ; **panneau « Understanding »** qui montre ce que l'agent lit, fichier par fichier (→ 14.7) ; panneau « Training » : playbooks éditables en place, compteurs d'usage (→ 14.1) ; format de skill Avant / Procédure / Règles / Vérification avec « dans le doute, escalader » (→ 12.5).
Pas d'apprentissage automatique : leur « mémoire » est faite de fichiers édités par des humains. Nous allons plus loin avec Hindsight (§ 14).
Écarté : agent aux pleins pouvoirs (`permissionMode: 'bypassPermissions'`, terminal et écriture libres) ; validations seulement écrites dans le prompt ; tableau de bord sans connexion ; pas de versions.

---

## 3. Skills et outils de montage : écran divisé, visage en incrustation, texte derrière la personne (28/09)

Aucun dépôt public ne couvre tout avec des règles « quand l'utiliser ». On a donc écrit notre propre skill (`.claude/skills/montage-mise-en-page/SKILL.md`) et trois scripts dans `04_montage/` : `disposition.py`, `texte_derriere.py`, `coupes.py`. Exemples de référence reçus : bandes empilées TOFU / MOFU / BOFU (Instagram, marineferrette_) et lettres géantes « DESIGN » derrière la tête (edwardcreates).

| Dépôt | Licence | Ce qu'on en retient | Verdict |
|---|---|---|---|
| heygen-com/hyperframes, skill `talking-head-recut` | Apache-2.0 | Règles côte à côte / empilé / incrustation / plein cadre, texte hors de la zone de la tête, transitions de 0,5 à 0,7 s | `→ repris` (reformulé dans le skill) |
| browser-use/video-use | MIT | Montage guidé par la transcription, fondus de 30 ms aux raccords | `→ repris` (fondus dans `coupes.py`) ; base possible pour la suite |
| luisadrianpuga/DepthCaptions | MIT | Recette texte derrière la personne : détourage MediaPipe, 3 calques | `→ repris` (`texte_derriere.py`, écrit par nous) |
| kurbaitaev/ghost-editor | MIT | Sous-titres qui ne couvrent jamais le visage | `→ repris` (règle du skill) |
| 6missedcalls/video-editing-skill, WyattBlue/auto-editor | MIT, domaine public | Coupes des silences | `→ repris` (`coupes.py`) ; auto-editor utile pour exporter vers Premiere / DaVinci |
| google-ai-edge/mediapipe | Apache-2.0 | Détourage de la personne sur processeur | `→ utilisé` (modèle selfie_segmenter, téléchargé au premier usage) |
| PeterL1n/RobustVideoMatting | GPL-3.0 | Meilleur détourage vidéo, sans scintillement, GPU | à brancher si le serveur a une carte graphique ; attention à la GPL |
| facebookresearch/sam2 | Apache-2.0 | Suivi d'un objet quelconque | plus tard, pour détourer autre chose qu'une personne |
| dhirajlochib/VidMcp | MIT | Serveur MCP « texte derrière le sujet » | `✗` pour l'instant : immature |
| Vincentwei1021/video-talkcraft | PolyForm Noncommercial | Écran de comparaison, zooms | `✗` : licence non commerciale |
| calesthio/OpenMontage | AGPL-3.0 | 700 fiches de savoir-faire | idées seulement, pas de code (AGPL) |

Guides : riverside.com (écran divisé), techsmith.com (visage en incrustation), adobe.com (texte derrière le sujet), descript.com (plans de coupe, coupes franches).
