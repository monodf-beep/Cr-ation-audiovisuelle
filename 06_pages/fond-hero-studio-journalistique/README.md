# Vidéo de fond du hero : page d'accueil du studio journalistique

Boucle de 16 s, 1920 × 1080, sans son, composée avec HyperFrames (`index.html`).
Quatre plans réels, étalonnés aux couleurs Cultura Sabauda (voile marine en multiplication, halo terre cuite, vignette) :

| Plan | Fichier attendu dans `assets/` | Source (Pexels, licence libre) |
|---|---|---|
| Entretien, prise de notes | `terrain.mp4` | pexels.com/video/8454305 (20 s → 26 s) |
| Lecture des documents | `sources.mp4` | pexels.com/video/8512938 (0,5 s → 6,5 s) |
| Écriture, pénombre | `ecriture.mp4` | pexels.com/video/946146 (1 s → 7 s) |
| Frappe au clavier | `frappe.mp4` | pexels.com/video/3114534 (1 s → 7 s) |

Préparer chaque plan :

    ffmpeg -ss <début> -t 6 -i source.mp4 -an -vf "scale=1920:1080,fps=25" -c:v libx264 -crf 18 -pix_fmt yuv420p assets/<nom>.mp4

Rendre, puis produire les versions web :

    npx hyperframes@latest lint
    npx hyperframes@latest render -o renders/hero.mp4 --fps 25
    ffmpeg -i renders/hero.mp4 -an -vf scale=1600:-2 -c:v libvpx-vp9 -b:v 0 -crf 40 -row-mt 1 hero-web.webm
    ffmpeg -i renders/hero.mp4 -an -vf scale=1600:-2 -c:v libx264 -crf 28 -movflags +faststart hero-web.mp4

La page sert le WebM d'abord (0,8 Mo), le MP4 ensuite (1,5 Mo), avec une image d'attente.
Page publiée : https://claude.ai/artifact/VYHUh78DNgtdkjxAMjccXF
