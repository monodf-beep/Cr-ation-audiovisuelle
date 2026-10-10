# Étalonnage « Heure bleue » Ferraud

LUT : `Ferraud_HeureBleue.cube` (3D, 33 points, Rec.709 / sRGB).
Elle reproduit la couleur des vidéos Ferraud. Le débruitage et la netteté
ne sont pas dans la LUT : on les règle à part (voir plus bas).

Appliquer la LUT sur une vidéo de téléphone déjà exposée correctement
(pas sur du Log). Si le rendu est trop fort, baisser son intensité à 70-80 %.

## Importer la LUT

- **CapCut (mobile / desktop)** : Ajuster → LUT → Importer → choisir le .cube.
- **DaVinci Resolve** : copier le .cube dans le dossier LUT
  (Paramètres du projet → Color Management → Open LUT Folder), « Update Lists »,
  puis clic droit sur le nœud → LUT → Ferraud_HeureBleue.
- **Premiere Pro** : Lumetri Color → Correction de base → Entrée LUT → Parcourir.
- **Lightroom Mobile** : n'importe pas de .cube pour la vidéo, utiliser les réglages manuels ci-dessous.

## Réglages manuels équivalents (Lightroom Mobile, CapCut, VN…)

| Réglage | Valeur |
|---|---|
| Exposition | +0,1 |
| Contraste | +6 |
| Hautes lumières | −15 |
| Ombres | +15 |
| Noirs | +5 (léger relevé) |
| Blancs | −5 |
| Température | +5 (légèrement chaud) |
| Vibrance | +15 |
| Saturation | +20 |
| Étalonnage des couleurs : ombres | bleu, saturation faible (~10) |
| Étalonnage des couleurs : hautes lumières | orange/doré, saturation faible (~8) |
| Réduction du bruit | 20-30 |
| Netteté | 25-35 |

Ces valeurs sont des équivalences approximatives : chaque application a
sa propre échelle, ajuster à l'œil.
