# Vidéo de fond du hero : page d'accueil du studio journalistique

Boucle de 16 s, 1920 × 1080, sans son, composée avec HyperFrames (`index.html`).
Quatre plans réels, étalonnés aux couleurs Cultura Sabauda (voile marine en multiplication, halo terre cuite, vignette) :

| Plan | Fichier attendu dans `assets/` | Source (Pexels, licence libre) |
|---|---|---|
| Conférence de presse, porte-parole face aux micros (retourné, recadré de 90 px à gauche) | `conference.mp4` | pexels.com/video/6952253 (0,5 s → 5,1 s) |
| Prise de notes sur un carnet, dehors | `notes.mp4` | pexels.com/video/5530405 (0,3 s → 4,9 s) |
| Frappe au clavier, de nuit | `frappe.mp4` | pexels.com/video/946146 (2,5 s → 7,1 s) |
| Rotative, feuilles qui s'empilent (ralenti) | `presse.mp4` | pexels.com/video/29906414 (10,5 s → 15,1 s) |

Le plan de l'entretien sur un canapé (pexels 8454305) a été retiré : jugé peu intéressant.
Les plans sont réencodés avec une image clé par seconde (`-g 25`) pour éviter les images figées au rendu.

Préparer chaque plan :

    ffmpeg -ss <début> -t 6 -i source.mp4 -an -vf "scale=1920:1080,fps=25" -c:v libx264 -crf 18 -pix_fmt yuv420p assets/<nom>.mp4

Rendre, puis produire les versions web :

    npx hyperframes@latest lint
    npx hyperframes@latest render -o renders/hero.mp4 --fps 25
    ffmpeg -i renders/hero.mp4 -an -vf scale=1600:-2 -c:v libvpx-vp9 -b:v 0 -crf 40 -row-mt 1 hero-web.webm
    ffmpeg -i renders/hero.mp4 -an -vf scale=1600:-2 -c:v libx264 -crf 28 -movflags +faststart hero-web.mp4

La page sert le WebM d'abord (0,8 Mo), le MP4 ensuite (1,5 Mo), avec une image d'attente.
Page publiée : https://claude.ai/artifact/VYHUh78DNgtdkjxAMjccXF
