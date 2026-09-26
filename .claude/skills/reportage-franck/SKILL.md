---
name: reportage-franck
description: >
  House style and workflow for Franck Monod's vertical field reports (Reels, TikTok, Shorts; Enstitut de la
  Lengoua Savoyârda, Nos Alpes): free voice-over recorded on the studio page, cut to the essentials, face-cam
  from the filmed take, grouped subtitles with keywords, sober sound, HyperFrames montage, metrics with alerts.
  Use for any "reportage", "montage", new video project of Franck built from real footage, or when editing
  10_cern/ or a similar project folder. For animated explainers without footage, use vox-animation.
---

# Reportage Franck — style maison et chaîne de fabrication

Fiche du style : `styles/reportage-franck.md`. Règles, seuils et raisons : `04_montage/BONNES-PRATIQUES.md`
(à relire avant chaque montage : ce sont les demandes de Franck). Projet de référence : `10_cern/`.

## Principes non négociables

1. La voix de Franck est libre (mode « Repères ») ; on coupe les reprises et les erreurs, on ne réécrit pas.
2. La prise filmée avec la voix sert au montage (face caméra synchrone).
3. Chaque image prouve la voix ; un effet (visuel ou sonore) n'entre que s'il est pertinent pour ce plan.
4. Sobriété : bleu Savoie comme seul accent, pas d'effet voyant, pas de ton publicitaire.
5. Les faits sont exacts (vérifier noms de projets, dates, chiffres) ; un contenu ancien est présenté comme ancien.
6. Dépôt public : jamais de police commerciale, rushes, photos, voix brutes ni sons sous licence dans git.

## Chaîne (dans le dossier du projet)

1. **Voix** : Franck enregistre sur `https://<studio>/enregistrement/<projet>/enregistrer.html` (prise filmée +
   repères, copiée dans Drive). Transcrire (`npx hyperframes transcribe`, modèle medium, `-l fr`), repérer
   reprises et erreurs, régler `PASSAGES` / `EXCLURE` / `RETIRER` dans `tools/couper-voix.py`, couper, vérifier par
   une nouvelle transcription.
2. **Réglages** : `montage.json` (vitesse, durées) ; `python3 tools/vitesse.py`.
3. **Voix finale** : `bash tools/voix-finale.sh` (traitement reportage, -16 LUFS).
4. **Mots** : `voix-mots.json` depuis la transcription, orthographe corrigée à la main (noms propres, savoyard).
5. **Montage** : `index.html` (HyperFrames ; charger d'abord le skill `hyperframes`). Séquences recalées sur la
   voix (`ANCIEN` / `NOUVEAU`), face caméra, punch-in, cartes, titres.
6. **Sous-titres** : `python3 tools/sous-titres.py`.
7. **Médias hors dépôt** : `bash tools/preparer-medias.sh` (face caméra, capture d'article, musique, effets).
8. **Contrôle** : `npx hyperframes check`, instantanés aux moments clés, rendu, puis
   `python3 04_montage/metriques.py <projet>` ; traiter chaque ALERTE ou expliquer pourquoi elle reste.
9. **Livraison** : version allégée envoyée à Franck ; commandes VPS pour refaire le rendu sur le studio.

## Bibliothèque

Sons, musiques et effets graphiques validés : `04_montage/bibliotheque.json` et la page du studio
(`/enregistrement/bibliotheque/`). Ne proposer que des éléments gardés ; les écartés ne reviennent pas.
Styles et skills disponibles : `styles/README.md`.
