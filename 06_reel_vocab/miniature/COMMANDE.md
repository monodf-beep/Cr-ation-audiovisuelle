# Miniature du reel rugby

Illustration : Higgsfield (GPT Image 2.6, 9:16, qualité haute, 2k), deux variantes
(`illustration_higgsfield_v1.png` retenue, `_v2.png`), 5,5 crédits, références de style :
deux images du reel (course de « Lo pallon », plaquage).

Composition (titre, médaillon, recadrage) :

    python3 outils/miniature_etiquette.py <selfie f_012.png> rendu/miniature_reel_rugby.png \
      --visage 364,480 --rond 0,0,180 --rond-source 268 --rond-coin bg --rond-debord=-0.32,1.0 \
      --rond-decor <rush 143456 à 8 s> --rond-decor-boite 40,420,1040,1420 \
      --fond miniature/illustration_higgsfield_v1.png --fond-decalage=0,-250 \
      --lignes "LE RUGBY|EN|SAVOYARD" --lieu "" --etiquette 375,470 --largeur 470

Contrôle grille : `python3 outils/apercu_grille.py rendu/miniature_reel_rugby.png apercu.jpg`
(recadrage 3:4 du profil, compteur de vues et icône lecture en rouge).
