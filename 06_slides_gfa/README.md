# Slides verticales — Identité de club : le business case

Dix slides 9:16 pour présenter le business case « club de l'Albanais » aux dirigeants du GFA Rumilly-Vallières (des chefs d'entreprise). Une idée par slide, texte ancré en bas, visuel plein cadre.

- `index.html` : le deck. Défilement vertical par accroche (scroll-snap), flèches / espace au clavier, swipe sur téléphone. Sur écran large, le deck s'affiche dans un cadre 9:16 centré.
- `assets/` : 8 visuels générés sur Higgsfield (GPT Image 2, 2K, redimensionnés en 1080×1920 JPEG) et les logos officiels.
- `prompts.md` : prompts, identifiants de job Higgsfield et provenance des logos, pour tout régénérer.

Source du contenu : `businesscaseidentiteGFA.html` (version longue, format document).

## Choix de design

| Élément | Choix |
|---|---|
| Palette | Navy nuit du club (`#0B1226`, `#182047`), rouge de Savoie (`#D40000`) comme seul accent, neige `#F2F0EA`, acier `#9AA3B2` |
| Typo | Barlow Condensed (titres, esprit signalétique de stade) + Barlow (texte), embarquées dans `assets/fonts.css` pour un rendu identique partout |
| Structure | 01 couverture · 02 thèse · 03 cycle de vie · 04 le signal (savoyard) · 05 la chaîne sponsor · 06 preuves (Wrexham, Le Puy) · 07 agrandir le gâteau · 08 méthode en 4 étapes · 09 le réseau (logos) · 10 clôture |

## Export en images

Pour livrer les slides en JPEG/PNG (stories, WhatsApp, impression), ouvrir `index.html` dans Chrome à 1080×1920 et capturer chaque slide, ou utiliser Playwright :

```bash
node -e "
const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
await p.goto('file://'+process.cwd()+'/index.html');await p.waitForTimeout(2000);
for(let i=0;i<10;i++){await p.evaluate(i=>phone.scrollTo({top:i*phone.clientHeight}),i);await p.waitForTimeout(400);await p.screenshot({path:'slide-'+String(i+1).padStart(2,'0')+'.png'});}
await b.close();})()"
```

## Mise à l'échelle

Toutes les dimensions du deck sont exprimées en `cqw` (1 % de la largeur du cadre 9:16), pas en pixels ni en unités de fenêtre. Le deck se comporte donc comme une image 1080×1920 mise à l'échelle, quel que soit l'écran. Un garde-fou en JavaScript réduit encore l'échelle d'une slide si son contenu dépasse la hauteur disponible (police de secours, cadre inhabituel).
