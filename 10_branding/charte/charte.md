# Charte graphique — référence

**Source de vérité : « Charte graphique — Franck Monod », v1.0, novembre 2026** (fichier HTML hors ligne fourni par Franck le 15/11/2026, non versionné ici car il embarque la police Semplicita Pro).
Tokens relevés à l'identique dans `tokens.css`. Aperçus : `charte-v1-apercu-1.jpg`, `charte-v1-apercu-2.jpg`.

## Ce que la charte décide

**Architecture** — une identité, deux entités. franckmonod.eu = marque mère (stratégie territoriale, patrimoine, architecture). ia.franckmonod.eu = pratique IA de la même personne. Même bleu, même typo.

**Logo** — wordmark « franck monod » en minuscules, monogramme `fm`. Toujours sur fond plein, jamais sur photo chargée, jamais déformé ni recoloré.

**Couleurs** — Bleu Savoie `#0A36AF` primaire partout. Noir `#000000`, blanc `#FFFFFF`. Rouge sombre `#8B0000` : accent rare, culture & événementiel, **franckmonod.eu seulement**. Deux accents maximum par composition. Nuanciers bleu 50→900, rouge 50→800, neutres 0→900.

**Typographie** — Semplicità Pro partout. Display 96 Light −1 % ; H1 64 Medium ; H2 44 Medium ; H3 30 Semibold ; corps 17 Regular 155 % ; étiquette 12 Semibold capitales +14 %. Accent événement : Ombra (provisoire : Bungee Shade).

**Grille** — 12 colonnes, 1 200 px max, gouttière 24 px, espacement base 4. Arrondis : 2 px boutons, 4 px cartes, pilule pour les tags.

**Formes** — losanges de la Venaria (signal provisoire IA) et Punt e Mes. Monochromes bleu, en texture discrète, jamais en fond de hero.

**Photo** — deux registres : architecture (lumière naturelle, tons brique chauds, détourée ou plein cadre) et portraits sur le vif. Couleur, sans filtre lourd.

**Ton** — direct, concret, convaincu. Stratège de terrain, pas cabinet parisien ni office de tourisme. Bilingue FR/IT dans l'esprit. Première personne, livrables concrets, pas d'emoji, pas de « transformation » ni « disruption », pas de folklore, pas de majuscules dans les titres.

**À éviter** — rouge sombre sur ia.franckmonod.eu ; dégradés, glassmorphism, halos ; codes visuels « startup IA ».

**Formats prévus** — post 1080×1080, story/reel 1080×1920, miniature YouTube 1280×720, habillage vidéo 1920×1080, sous-titres (3 styles), motion titre 10 s, signal de voyage Chambéry → Turin, carte des États de Savoie.

## Écarts constatés entre la charte et l'existant (15/11)

| Point | Charte | Aujourd'hui |
|---|---|---|
| Rouge | `#8B0000` | franckmonod.eu : `#931E1E` |
| Police IA | Semplicità Pro | ia.franckmonod.eu : aucune police web (repli système) |
| Texte courant | Semplicità Pro | franckmonod.eu : Montserrat |
| Photo hero | lumière naturelle, sans filtre lourd | franckmonod.eu : gélatine violet/orange |
| Fond | `--color-bg` = noir | les deux sites : crème `#F9F8F6` |
| Carte des États de Savoie | format prévu | « Torino » placé côté Savoie, titre trop large (voir plus bas) |

## Revue UX/UI — prévue le 16/11

Franck l'a demandée pour demain. Pistes notées, à instruire à ce moment-là, pas encore des décisions :
- Feed Instagram : la charte prévoit 1080×1080, alors que le feed et la grille de profil sont passés au 4:5 / 3:4. Ajouter un gabarit **carrousel 1080×1350**, absent de la liste alors que c'est le format de veille n° 1.
- Contraste : `--neutral-400` `#8C8C94` (3,1:1 sur `#F7F7F8`) ne doit pas porter de texte courant.
- Deux rouges coexistent (charte `#8B0000`, site `#931E1E`) : en garder un.
- Fond noir par défaut dans les tokens, mais sites et charte en clair : préciser quand le noir s'applique.
- Ombra / Bungee Shade : vérifier licence et lisibilité à petite taille avant tout usage réseau.
- Carte des États de Savoie : corriger Torino, le titre (Ligurie et Sardaigne absentes), la règle de langue des noms, les doublons, le libellé qui chevauche la frontière.
- Licence Semplicità Pro : la charte hors ligne et la carte l'embarquent en base64 dans des fichiers partageables.
