# Outils — publication, calendrier, agents

Recherche du 15/11/2026 (pages GitHub et docs officielles). Les nombres d'étoiles sont arrondis.

## Ce que les plateformes permettent vraiment

**Instagram** ([doc Meta](https://developers.facebook.com/docs/instagram-platform/content-publishing))
- Publication par API **uniquement avec un compte Professionnel** (Créateur suffit). Compte perso = impossible.
- Deux voies : Facebook Login (compte lié à une Page Facebook) ou Instagram Login (pas de Page requise).
- Reels, carrousels jusqu'à 20 éléments, Stories : OK.
- La musique sous licence des Reels n'est disponible que par la voie Page Facebook.

**LinkedIn** ([doc Microsoft](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin))
- Profil perso : publication texte, lien, image, vidéo via `w_member_social` (self-serve).
- Les statistiques détaillées d'un profil perso ne sont pas accessibles par API : export manuel.

## Décision (15/11) : outil gratuit fait maison

Franck veut du gratuit. Aucun outil GitHub ne convainc à coût zéro : Postiz et BrightBean demandent un serveur à héberger, et BrightBean ne confirme ni les Reels ni les carrousels.

Solution retenue, 0 € :
- **Régie éditoriale** (https://claude.ai/artifact/K9brdqLe3WWMsxzzbCc5F2, source `10_branding/regie/regie.html`) : tableau des idées en 6 colonnes (idée → brouillon → à valider → validé → programmé → publié), calendrier mensuel, bilan des résultats (vues, enregistrements, messages, appels réservés). Contrôles de la charte intégrés (mots interdits, emoji, longueur, hashtags, éléments à fournir). Privée, hébergée sur claude.ai, les agents y écrivent directement.
- **Publication** : planificateurs natifs gratuits. Meta Business Suite pour Instagram (Reels et carrousels programmables), programmation intégrée de LinkedIn. On copie la légende depuis la régie, on programme, on passe le post en « Programmé ».
- Limite assumée : pas de publication automatique. Elle exigerait une app Meta ou un serveur ; la validation humaine reste de toute façon obligatoire.

Si un jour le volume le justifie : Postiz auto-hébergé, qui a un serveur MCP.

## Planificateur : Postiz

[gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app) — ~42k étoiles, AGPL-3.0, version du 13/11/2026.

Pourquoi lui :
- Seul outil open source très actif qui couvre Reels + carrousels 20 + LinkedIn profil perso.
- **Serveur MCP** : Claude peut y déposer des posts **en brouillon**. Tu valides dans le calendrier, Postiz publie. C'est exactement la boucle « agent rédige, humain valide ».
- Cloud à 29 $/mois (5 canaux), ou auto-hébergé gratuit (mais 9 conteneurs Docker : je déconseille pour commencer).

Second choix : [Mixpost Pro](https://mixpost.app/pricing), 299 $ une fois, auto-hébergé. La version gratuite ne gère ni Instagram ni LinkedIn.

Alternative sérieuse : [BrightBean Studio](https://github.com/brightbeanxyz/brightbean-studio) — ~2,6k étoiles, AGPL-3.0, gratuit, sans offre payante. **Tableau kanban des idées**, circuit de validation, calendrier, statistiques, boîte de réception unifiée, API + serveur MCP. LinkedIn profil perso OK. Mais Reels et carrousels Instagram non mentionnés, aucune release publiée, et auto-hébergement obligatoire (Docker + Postgres) ou version hébergée gratuite dont la pérennité est inconnue.

À écarter : Shoutify (archivé 2023), Socioboard (vieillissant).

## Skills et agents Claude Code réutilisables

Tous MIT, ils produisent des brouillons, ils ne publient rien.

| Dépôt | Utile pour |
|---|---|
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | `competitor-profiling`, `content-strategy`, `social` |
| [sergebulaev/linkedin-skills](https://github.com/sergebulaev/linkedin-skills) | rédaction LinkedIn, planning 7 jours, humanizer, audit |
| [charlie947/social-media-skills](https://github.com/charlie947/social-media-skills) | voix de marque, carrousels, scripts de reels |
| [thatrebeccarae/claude-marketing](https://github.com/thatrebeccarae/claude-marketing) | Brand DNA, calendrier éditorial |

Avis : ces skills sont pensées pour le marché anglophone des « créateurs ». Leur ton par défaut (hooks agressifs, listes, emojis) est l'opposé de ce que ta marque raconte. Je les ai lues comme sources de méthodes, et les agents de `.claude/agents/` sont écrits pour toi. À installer seulement si un besoin précis apparaît.

## Ce qui est déjà branché dans tes connecteurs

- **Canva** : pour remplir les gabarits de carrousel depuis la charte.
- **Notion / Todoist / Google Calendar** : pour afficher le calendrier éditorial si tu préfères à un CSV.
- **Higgsfield** : génération vidéo, et un prédicteur de viralité à tester sur tes reels.
- **Brevo** : déjà ta prise de RDV ; peut servir de newsletter si tu en veux une.

## Chaîne proposée

```
veille (ton ordi)            analyse (Claude Code)              publication
gallery-dl / instaloader ─▶  veilleur ─▶ stratege ─▶ redacteur ─▶ Postiz (brouillon)
traiter.py (whisper,         directeur-artistique                  │
planches) indexer.py         avocat-du-diable                      ▼
                                                              toi : valider ─▶ publié
```

Ce qui reste manuel, volontairement : choisir les concurrents, valider la stratégie, valider chaque post, répondre aux commentaires.
