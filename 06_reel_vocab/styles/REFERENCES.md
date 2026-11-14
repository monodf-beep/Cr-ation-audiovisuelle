# Styles illustrés pour le reel rugby savoyard : références (recherche nov. 2026)

Contexte : reel 9:16, Italie v Afrique du Sud (Turin). Visages vides, maillots lisibles (azur ; vert et or avec blanc), rendu épuré, pas de scintillement, traitement CPU local.
Les liens ci-dessous ont été trouvés par recherche web. Les mentions « non vérifié » signalent les cas où la page ne décrit pas précisément le rendu.

## 1. Aplat vectoriel / pictogramme (flat vector, posterisation)
- **Signature** : peu de couleurs en aplats nets, formes simplifiées, pas de texture, silhouettes de type pictogramme.
- **Adéquation** : anonymat ★★★ (le visage devient une seule couleur de peau ou un ovale neutre). Maillots ★★★ (on garde une palette réduite : azur, vert, or, blanc). Épuré ★★★. Ton associatif : sobre et institutionnel, proche des pictos olympiques.
- **Références** :
  - Pictogrammes et motion design de Paris 2024 (W, Gédéon) : https://itsnicethat.com/news/paris-2024-olympic-paralympic-pictograms-080223 et https://www.german-design-award.com/en/gallery/detail/audiovisual/paris-2024-look-of-the-games-motion-design
  - Habillage NBC Paris 2024 inspiré des pictos : https://www.newscaststudio.com/2024/08/12/nbc-olympics-2024-motion-graphics/
- **Faisabilité** : **facile**. Quantification sur une palette fixe (k-means appris sur l'ensemble du plan, puis figé), filtre bilatéral ou mean-shift, et lissage temporel des labels. Très stable si la palette est verrouillée.

## 2. Ligne claire BD (contour noir régulier + aplats)
- **Signature** : contour noir d'épaisseur constante, aplats sans ombrage, lisibilité « Hergé ».
- **Adéquation** : anonymat ★★★ (visage = aplat chair sans traits). Maillots ★★★. Épuré ★★★. Ton patrimonial ★★★ : la BD franco-belge est un registre familier et chaleureux, et la BD rugby existe déjà (*Les Rugbymen*).
- **Références** :
  - La ligne claire comme l'un des 7 grands styles graphiques (Cité internationale de la BD, 2025) : https://www.citebd.org/sites/default/files/2025-11/dossier-pedagogique-exposition-les-tresors-des-collections_0.pdf
  - Le rugby en BD (*Les Rugbymen*, Poupard) : https://leclaireur.fnac.com/article/cp15799-les-rugbymen-et-le-monde-de-lovalie/
  - Retour du « fait main » dans le rugby : première œuvre officielle du Tournoi des Six Nations 2026 par Tanguy Bourhis (ODITI), style non décrit dans l'article : https://hypebeast.com/2026/4/oditi-six-nations-rugby-artwork-collaboration-announcement
- **Faisabilité** : **facile à moyen**. On combine le style 1 (aplats) avec des contours issus des frontières de segments ou d'un Canny/XDoG sur une image lissée. Les contours sont la principale source de scintillement : il faut un seuil d'hystérésis et un lissage temporel (EMA ou flux optique) de la carte de bords.

## 3. Comic / Spider-Verse (halftone, trames, décalage d'encres)
- **Signature** : trames de points (Ben-Day), hachures, léger décalage des couches CMJN, traits de vitesse, pas de flou de bouge.
- **Adéquation** : anonymat ★★ (il faut quand même aplatir le visage). Maillots ★★ (les trames modifient la perception du vert et de l'or). Épuré ★ : c'est chargé et très « pop US ». Ton associatif ★ : dynamique, mais peu patrimonial. Le style est aussi très associé à Sony, ce qui a valu une polémique à la NBA en 2024.
- **Références** :
  - Mode « Spider-Verse » de la NBA par IA (All-Star 2024), critiqué par les réalisateurs : https://insidethemagic.net/2024/02/spider-man-across-the-spider-verse-nba-nb-ai-basketball-phil-lord-christopher-miller-miles-morales-jh1/ et https://deadspin.com/nba-ai-spiderman-wemby-adam-silver-nfl-baker-mayfield-1851266446/
  - Techniques du look (halftone, décalage d'encres, traits de vitesse) : https://view.ceros.com/editorial-content/spider-verse-desktop
  - Nike AJ1 x Across the Spider-Verse (OOH 3D à New York) : https://billups.com/success-stories/nikes-3d-ooh-experience-across-the-spider-verse-in-nyc
- **Faisabilité** : **moyen**. Le halftone procédural est simple, mais la trame doit rester fixe dans l'écran (screen-space). Une trame qui suit les pixels scintille ; une trame fixe donne un effet « shower door ». C'est acceptable en BD.

## 4. Rotoscopie peinte / croquis (Swarbrick, frame-by-frame texturé)
- **Signature** : mouvement réel reproduit à la main, coups de pinceau ou de crayon visibles, fonds souvent effacés ou papier.
- **Adéquation** : anonymat ★★★ (les visages sont naturellement esquissés). Maillots ★★ (couleurs en lavis). Épuré ★★ si le fond est blanc ou papier. Ton patrimonial ★★★ : artisanal, « carnet de croquis », très adapté à une association.
- **Références** :
  - Richard Swarbrick, rotoscopie peinte sur le football (El Clásico, Bale, Ronaldo) : https://cartoonbrew.com/shorts/el-clasico-by-richard-swarbrick-41466.html , https://lbbonline.com/news/richard-swarbrick-goes-back-to-basics-with-ronaldo et https://presence.team/directors/richard-swarbrick
  - Fern & Friends, « Draw the Line », spots NCAA March Madness 2026, image par image peint et texturé : https://www.stashmedia.tv/?p=118772
  - Dossier rotoscopie : https://shots.net/news/view/rotoscope-the-dark-art-of-animation
- **Faisabilité** : **difficile** pour un rendu authentique. Une texture de papier ou de crayon procédurale varie à chaque image. Il faut figer la texture (papier statique) et animer seulement le trait. Le « boiling » (2 à 3 variantes en boucle, image tenue sur 2) peut devenir un choix assumé plutôt qu'un défaut.

## 5. Papier découpé / papercraft
- **Signature** : formes découpées en aplats, ombres portées douces entre les couches, grain de papier.
- **Adéquation** : anonymat ★★★. Maillots ★★★ (une couleur par couche). Épuré ★★★. Ton patrimonial ★★★ (artisanat, chaleur, proche de l'imagerie populaire alpine).
- **Références** :
  - BBC Sport, ouverture de Wimbledon 2025 en stop-motion papier (A+C Studios, réal. Jess Deacon) : https://www.animationuk.org/?p=12882 et https://www.creativebloq.com/3d/3d-animation/the-bbcs-magical-wimbledon-animation-used-a-delightfully-old-school-technique
  - BBC, bande-annonce de la Coupe du monde 2026 en techniques mixtes (stop-motion, 2D, artisanat, Nicos Livesey / Blinkink) : https://www.stashmedia.tv/nicos-livesey-animates-on-everything-in-buildup-to-bbcs-world-cup-coverage/
- **Faisabilité** : **moyen**. On part du style 1 (aplats) en ajoutant une ombre portée décalée par couche (dilatation du masque, flou, décalage), une texture papier statique et des bords légèrement érodés. La stabilité est bonne si la texture reste fixe.

## 6. Anime / cel-shading
- **Signature** : 2 ou 3 tons d'ombre nets, contours fins, ciels et effets de vitesse typés manga.
- **Adéquation** : anonymat ★★ (on attend des yeux, et un visage vide fait « bizarre »). Maillots ★★★. Épuré ★★. Ton associatif ★ : codes japonais éloignés du patrimoine savoyard.
- **Références** :
  - ITV, bande-annonce « Rise » de la Coupe du monde de rugby 2019 (Golden Wolf / Stink), passage du live au monde anime : https://shots.net/news/view/keith-mccarthy-and-golden-wolf-bring-rugby-dreams-to-life et https://www.newscaststudio.com/2019/10/30/itv-rugby-world-cup-open-2019/
  - Tendance « AI football filter » sur TikTok (pages éditeurs uniquement, sans source indépendante) : https://dreamina.capcut.com/create/ai-football-trend
- **Faisabilité** : **moyen** en procédural (cel-shading = quantification de la luminance en 2 ou 3 paliers sur des aplats). Un vrai rendu anime demande un modèle génératif, donc GPU et instabilité temporelle : hors contraintes.

(Risographie / duotone : je n'ai trouvé aucun exemple sportif fiable. C'est faisable très facilement en variante du style 1 avec 2 encres et un grain fixe, mais la bichromie détruit la distinction azur / vert-or. À déconseiller ici.)

## Top 3 recommandé
1. **Ligne claire BD (n° 2)** : le meilleur compromis. Visages en aplats chair sans traits, maillots dans leurs vraies couleurs, rendu très épuré, registre BD franco-belge cohérent avec une association de langue régionale. Faisable en moins de 1,5 s par image avec palette verrouillée et lissage temporel des contours.
2. **Papier découpé (n° 5)** : le plus « patrimonial » et chaleureux, avec une référence sport 2025 (BBC Wimbledon). C'est la ligne claire sans contour noir, plus une ombre portée et une texture papier fixe. Coût CPU à peine supérieur.
3. **Aplat vectoriel / pictogramme (n° 1)** : le plus robuste et le plus stable (zéro contour qui scintille). Solution de repli sûre, avec une esthétique Paris 2024 sobre.

À éviter pour ce projet : Spider-Verse (chargé, connoté Sony, couleurs de maillot altérées), anime (visage vide incongru, ton hors sujet) et rotoscopie peinte authentique (scintillement des textures difficile à maîtriser sur CPU).
