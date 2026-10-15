# Métriques du montage (15_decidia)

Seuils et raisons : `04_montage/BONNES-PRATIQUES.md`, section 8 (branche HyperFrames).

**1 alerte(s)**

- plan_sans_coupe = 5.2 s (attendu ≤ 4.0) de 19.4 à 24.6 s

| métrique | valeur | attendu | état | détail |
|---|---|---|---|---|
| st_mots | 5 mots | voulu | ok | « ça veut dire la rioule ? » à 32.2 s : question dite d'une traite (24 car. en 1 s) : coupée, un groupe clignoterait à plus de 25 car./s |
| st_cps | 25 car./s | ≤ 25 | ok | « Exactement, bravo ! » à 35.0 s |
| st_cles | 0.22  | 0.15 - 0.4 | ok | 6 groupes sur 27 |
| duree_video | 45.5 s | 15 - 90 | ok |  |
| plan_sans_coupe | 5.2 s | ≤ 4.0 | ALERTE | de 19.4 à 24.6 s |
| plan_sans_coupe | 4.3 s | voulu | ok | de 41.2 à 45.5 s : carton final à lire |
| coupes détectées | 36 | | | une toutes les 1.3 s en moyenne |
| lufs | -15.1 LUFS | -16.5 - -13.5 | ok |  |
| crete_dbtp | -1.2 dBTP | ≤ -1.0 | ok |  |
| musique_sous_voix | 16.4 dB | 12 - 22 | ok |  |
| zones_masquees | 0 texte | aucun | ok | haut 250 px, bas 480 px, colonne de droite 140 px |
