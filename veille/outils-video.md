# Veille outils vidéo (relevé du 26/09/2026)

Trois familles d'outils qui se suivent dans une chaîne de production sans se remplacer :
**générer** (Higgsfield, Arcads) → **monter et traiter** (DaVinci, FFmpeg) →
**habiller** (HyperFrames, Remotion, Canva).

## Verdicts

| Outil | Famille | Pilotable par Claude | Coût | Verdict |
|---|---|---|---|---|
| [HyperFrames](https://github.com/heygen-com/hyperframes) | Habillage par code (HTML → MP4) | Oui, 21 skills fournis | Gratuit, Apache 2.0 | **Tester en premier** |
| [DaVinci Resolve Studio](https://www.blackmagicdesign.com/products/davinciresolve/studio) + [MCP](https://github.com/samuelgursky/davinci-resolve-mcp) | Montage, étalonnage, upscale Super Scale, Magic Mask | Oui via MCP, **Studio uniquement** | 295 $ une fois | Si poste local avec GPU |
| Higgsfield (MCP déjà branché) | Génération + upscale, reframe, détourage, dubbing | Oui, déjà en place | Crédits | Garder |
| [Arcads](https://www.arcads.ai/) | Pubs UGC avec avatars IA | API seulement au plan le plus cher | ~110-550 $/mois (sources tierces) | Seulement pour des pubs UGC en volume |
| [lottiefiles/motion-design-skill](https://github.com/lottiefiles/motion-design-skill) | Règles d'animation (Markdown, aucun rendu) | Skill Claude | Gratuit, MIT | En complément de HyperFrames |
| [Remotion](https://github.com/remotion-dev/remotion) + [skills](https://github.com/remotion-dev/skills) | Habillage par code (React) | Oui | Gratuit jusqu'à 3 salariés | Si HyperFrames ne suffit pas |
| [Easymotion](https://easymotion.io/) | Motion graphics en SaaS : cartes, datavisualisation, MOV transparent | Non (pas d'API) | 0-60 $/mois | Tester en gratuit pour les cartes |
| [Motionify](https://motionify-17875809-3883c.web.app/) | Reels 9:16 animés (Gemini + GSAP) | Non | Gratuit + clé Gemini | Bêta, auteur inconnu : pas en production |

## Briques libres utiles en ligne de commande

- FFmpeg : coupe, LUT, sous-titres, encodage (déjà utilisé dans `03_etalonnage/`, `04_montage/`)
- [auto-editor](https://github.com/WyattBlue/auto-editor) : coupe les silences, exporte vers Resolve ou Premiere
- Whisper / faster-whisper : transcription et sous-titres (déjà dans le skill `reels-templates`)
- [Video2X](https://github.com/k4yt3x/video2x) : upscale local (GPU requis)
- [rembg](https://github.com/danielgatis/rembg) : détourage
- [VectCutAPI](https://github.com/sun-guannan/VectCutAPI) : brouillons CapCut par API (CGU de CapCut à vérifier)

## Points durs

- DaVinci Resolve n'est pas sur GitHub (logiciel propriétaire). Depuis la 21.1, la version
  gratuite n'a plus de scripting Python : pour piloter Resolve, il faut Studio. Resolve ne
  tourne pas dans un conteneur cloud : Claude Code doit tourner sur la même machine.
- Le reel « Claude Edit » (@mr.paidsocial) : le montage y est fait par Claude Code en
  8 itérations, Arcads ne sert qu'à générer les plans. C'est un reel d'appât à commentaires
  (3 785 commentaires pour 978 likes).
