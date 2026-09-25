// Aire linguistique, commune a la maquette et a la carte du reportage.
// Pas de contour : des taches de lumiere (lon, lat, rayon) qui se fondent les unes dans les autres
// et debordent les frontieres administratives. Approximation a la main : Savoie, Aoste, Geneve, Vaud,
// Ain, Valais francophone, nord de l'Isere avec Grenoble, Lyonnais, vallees alpines du Piemont
// (Orco, Soana, Lanzo, Suse moyenne). Nice et le reste du Piemont restent dehors.
// Les rayons sont en pixels de la maquette (cadrage de reference ci-dessous) : les autres cartes les
// ramenent a leur echelle avec echelleLangue().
import * as d3 from 'd3';

export const taches = [
  [6.35, 45.55, 230], [6.4, 46.0, 220], [6.13, 46.22, 170], [6.6, 46.6, 210], [7.0, 46.85, 170],
  [7.1, 46.15, 130], [6.0, 46.35, 140], [5.6, 45.95, 190], [5.2, 46.25, 190], [5.0, 45.95, 170],
  [4.85, 45.7, 170], [5.4, 45.55, 180], [5.72, 45.2, 170], [7.35, 45.72, 190], [7.2, 45.38, 110]];

// Le degrade d'ensemble part du coeur savoyard et s'eteint vers les marges de l'aire.
export const CENTRE = [6.3, 45.85];
export const PORTEE = 660;

// Cadrage de la maquette 1080 x 1920 : fitExtent([[40, 560], [1040, 1640]]) sur 73, 74, Geneve, Aoste, Ain.
export function echelleLangue(projection, { savoie, hauteSavoie, geneve, aoste, ain }) {
  const ref = d3.geoMercator().fitExtent([[40, 560], [1040, 1640]],
    { type: 'FeatureCollection', features: [savoie, hauteSavoie, geneve, aoste, ain] });
  return projection.scale() / ref.scale();
}

// Defs SVG et calque de lueur. ids : prefixe pour eviter les collisions.
export function lueurSvg(projection, k, { opacite = 0.55, flou = 45, id = 'langue' } = {}) {
  const P = ll => projection(ll).map(v => +v.toFixed(1));
  const [cx, cy] = P(CENTRE);
  const defs = `<filter id="${id}-flou" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="${(flou * k).toFixed(1)}"/></filter>
<radialGradient id="${id}-tache"><stop offset="0" stop-color="#0a36af"/><stop offset="0.4" stop-color="#0a36af" stop-opacity="0.5"/><stop offset="1" stop-color="#0a36af" stop-opacity="0"/></radialGradient>
<radialGradient id="${id}-grad" gradientUnits="userSpaceOnUse" cx="${cx}" cy="${cy}" r="${(PORTEE * k).toFixed(1)}"><stop offset="0" stop-color="#fff"/><stop offset="0.35" stop-color="#fff" stop-opacity="0.9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<mask id="${id}-fondu" maskUnits="userSpaceOnUse" x="-2000" y="-2000" width="6000" height="6000"><rect x="-2000" y="-2000" width="6000" height="6000" fill="url(#${id}-grad)"/></mask>`;
  const cercles = taches.map(([lon, lat, r]) => { const [x, y] = P([lon, lat]); return `<circle cx="${x}" cy="${y}" r="${(r * k).toFixed(1)}" fill="url(#${id}-tache)"/>`; }).join('');
  const calque = `<g id="${id}" mask="url(#${id}-fondu)"><g filter="url(#${id}-flou)" opacity="${opacite}"><g id="${id}-taches">${cercles}</g></g></g>`;
  return { defs, calque, centre: [cx, cy] };
}
