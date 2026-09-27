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
