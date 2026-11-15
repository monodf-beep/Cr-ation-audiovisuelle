# Branding — Franck Monod

Objectif : une marque personnelle lisible, nourrie par une veille concurrentielle réelle, et un maximum d'automatisation avec validation humaine avant publication.

## Ordre de lecture

1. `00_questions.md` — **à remplir en premier.** Sans ces réponses, tout le reste n'est qu'hypothèse.
2. `01_audit-critique.md` — ce qui ne va pas aujourd'hui, du plus grave au moins grave.
3. `02_outils.md` — outils retenus (scraping, planification, skills) et pourquoi.
4. `profil.md` — la source de vérité que lisent tous les agents.

## Les agents (`.claude/agents/`)

Lance Claude Code à la racine du dépôt sur ton ordinateur ; les agents sont chargés automatiquement.

| Agent | Rôle | Écrit dans |
|---|---|---|
| `veilleur` | Une fiche par concurrent depuis ses données téléchargées | `veille/fiches/` |
| `stratege` | Positionnement, offres, piliers éditoriaux | `livrables/strategie.md` |
| `directeur-artistique` | Charte, tokens CSS, gabarits carrousel / reel | `charte/` |
| `redacteur` | Calendrier et brouillons de posts | `calendrier/` |
| `avocat-du-diable` | Attaque chaque livrable avant validation | (réponse seule) |

Exemple : « Utilise l'agent veilleur sur donnees/compte_x, puis l'avocat-du-diable sur la fiche. »

## Veille Instagram — sur ton ordinateur

Le scraping tourne **chez toi**, avec ta session Instagram. Pas depuis le cloud : Instagram bloque les IP de serveurs, et c'est ton compte qui porte le risque. Utilise un **compte secondaire** connecté dans Firefox.

### Installation (Mac)

```bash
brew install ffmpeg gallery-dl yt-dlp
pip3 install faster-whisper pillow
```

### Utilisation

```bash
cd 10_branding/veille
# 1. lister les comptes dans concurrents.txt
./telecharger.sh                       # 30 dernières publications par compte, puis incrémental
./stats.sh donnees/compte_x            # optionnel : commentaires et vues via yt-dlp
python3 traiter.py donnees/compte_x    # transcriptions + planches d'images + rythme de montage
python3 indexer.py donnees/compte_x    # index.csv + resume.md triés par engagement relatif
```

Puis dans Claude Code : « agent veilleur sur donnees/compte_x ».

### Ce que produit la chaîne, par compte

- `index.csv` — une ligne par publication : format, durée, secondes par plan, likes, commentaires, accroche, hashtags, **score** (engagement / médiane du compte).
- `resume.md` — rythme de publication, score moyen par format, top 10 / flop 5.
- `transcriptions/` — ce qui est dit dans chaque reel, horodaté.
- `planches/` — 12 images par reel (la 1re = l'accroche), toutes les slides de chaque carrousel.

### Prudence

- Un compte à la fois, pauses par défaut, quelques centaines de publications par jour maximum.
- Au premier **429**, `feedback_required` ou checkpoint : on arrête, on valide le compte dans le navigateur, on attend 24 h.
- `donnees/` n'est **jamais versionné** (`.gitignore`) : ce sont les œuvres des autres. Analyse interne uniquement, aucune republication.
- Si les outils libres sont bloqués : Apify `instagram-scraper`, ~2 $ / 1 000 publications, sans risque pour ton compte.

## Publication

Postiz (voir `02_outils.md`) : l'agent `redacteur` prépare, Postiz reçoit en **brouillon**, tu valides, Postiz publie. Prérequis : compte Instagram en mode Professionnel.
