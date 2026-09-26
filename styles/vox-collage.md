# Style « Vox — collage éditorial » (`mixed`)

Style d'explication animée à la Vox : collage éditorial en mouvement. Skill : `.claude/skills/vox-animation/`
(référence : `references/vox-prompts.md`). Studio de travail : `11_vox/`.

**En une phrase :** une idée expliquée en 60 s par un collage vivant, découpages photo, aplats de couleur,
annotations au feutre, porté par une narration documentaire précise.

## Quand l'utiliser

Un sujet sans tournage possible, ou une explication plus qu'un reportage : histoire de la Savoie, pourquoi une
langue est « commune », une donnée surprenante, un concept. Ton curieux, précis, un peu malicieux.

## Identité visuelle

| | |
|---|---|
| Couleurs | jaune chaud, blanc papier, bleu marine, rouge corail (une couleur dominante par scène) |
| Matières | grain papier, trame de points, bords déchirés, ruban adhésif, ombres portées légères |
| Dispositifs | découpages photo à bord blanc, cercles et flèches au feutre, graphiques sans chiffres, cartes plates, barres de caviardage, comparaisons d'échelle |
| Mouvement | entrées vives avec léger dépassement, poussées lentes, filés entre les idées ; une seule chose « forte » à la fois |
| Texte à l'image | aucun texte lisible dans les plans générés |

## Fabrication

Scènes de 10 s générées dans le générateur de Franck (Higgsfield, Veo, Kling…) à partir d'une image de
référence (« style key ») ; narration lue par une voix de synthèse gratuite (edge-tts) ; montage final par
`scripts/assemble.sh`. Le studio n'envoie jamais de génération payante lui-même.

## Adaptation au studio de Franck

- Narration en français : voix edge-tts `fr-FR-HenriNeural` (homme) ou `fr-FR-DeniseNeural` (femme), ou la voix
  de Franck enregistrée sur la page du studio.
- Format 9:16 par défaut ; sous-titres, musique et métriques du style reportage réutilisables (`04_montage/`).
- Les couleurs Vox peuvent céder la place au bleu Savoie pour rester dans l'identité de la chaîne.
