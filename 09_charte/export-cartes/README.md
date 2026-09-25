# Handoff : Cartes des États de Savoie

## Présentation
Cartes des États de Savoie : Savoie (73 + 74 fusionnés), arrondissement de Nice, Piémont et Vallée d'Aoste. Elles servent aux publications de Franck Monod (franckmonod.eu).

## À propos des fichiers
Ce sont des **références de design en HTML**. Il ne s'agit pas de code de production. Il faut les recréer dans l'environnement cible, par exemple un export SVG/PNG ou un composant React/D3, ou les servir telles quelles depuis un serveur local (`npx serve .`) : les données sont chargées par `fetch`, donc `file://` ne fonctionne pas.

## Fidélité
Haute fidélité : couleurs, typographie et tracés sont définitifs.

## Fichiers
- `carte-etats-de-savoie.html` : carte 1, territoires remplis en bleu. Carte 2, contours seuls avec les provinces du Piémont en pointillés, les villes, et les étiquettes décalées pour éviter les chevauchements.
- `carte-etats-de-savoie-tweaks.html` : carte unique avec un panneau de tweaks (React), qui réunit toutes les variantes.
- `carte-etats-de-savoie-social.html` : post carré 1080×1080 pour les réseaux sociaux, contours lissés.
- `tweaks-panel.jsx` : l'interface du panneau de tweaks.
- `departements/` : GeoJSON 73, 74 et des arrondissements du 06 (source france-geojson, gregoiredavid).
- `topojson/` : régions et provinces d'Italie (source ISTAT via guglielmo/geojson-italy).
- `assets/fonts/` : Semplicità Pro (woff).

## Tweaks (carte-etats-de-savoie-tweaks.html)
Les options s'activent ou se désactivent indépendamment :
- Remplir les territoires : fond #0a36af ou contours seuls
- Fusionner Savoie / Haute-Savoie : la frontière 73/74 est dissoute
- Provinces du Piémont : pointillés 0,5 px, opacité 0,6
- Villes principales : points de 3 px et étiquettes de 11 px
- Aires urbaines : cercles proportionnels (échelle racine carrée, rayon de 4 à 34 px)
- Noms des territoires
- Contexte France / Italie / Suisse

## Rendu
- Projection : Mercator (d3.geoMercator), `fitExtent` sur les 5 entités
- Lissage (version réseaux sociaux) : `d3.curveCatmullRomClosed.alpha(0.5)` sur des anneaux simplifiés
- Frontières communes tracées une seule fois : déduplication en coordonnées géographiques, seuil de 0,02°

## Tokens
- Bleu Savoie : #0a36af
- Texte : #171719 / #45454c / #64646c / #8c8c94
- Fonds : #ffffff / #f7f7f8, lignes de contexte #d9d9dc
- Police : Semplicità Pro, graisses 400 / 500 / 600 / 700
- Titre : 44–52 px, 700, letter-spacing -0.01em
- Étiquettes des territoires : 13 px (web) / 20 px (post), 600, halo blanc de 3 à 5 px

## Dépendances (CDN)
d3@7.9.0, topojson-client@3.1.0, world-atlas@2.0.2 (contexte), React 18.3.1 et Babel standalone (tweaks uniquement).
