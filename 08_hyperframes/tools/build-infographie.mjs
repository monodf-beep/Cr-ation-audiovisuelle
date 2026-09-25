// Precalcule la carte infographique 16:9 des Etats de Savoie et l'injecte dans
// etats-de-savoie-16x9.html entre <!-- carte:start --> et <!-- carte:end -->.
// Territoires pleins (avec ombre de relief), villes, itineraire du Mont-Cenis.
//
// Usage : node tools/build-infographie.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import * as d3 from 'd3';
import { root, loadTerritoires, thin, round } from './geo-savoie.mjs';

const projection = d3.geoMercator();
const { fc, rings } = loadTerritoires();
projection.fitExtent([[860, 110], [1780, 960]], fc);

const lineClosed = d3.line().curve(d3.curveCatmullRomClosed.alpha(0.5));
const lineOpen = d3.line().curve(d3.curveCatmullRom.alpha(0.5));
const P = ([lon, lat]) => projection([lon, lat]).map(v => +v.toFixed(1));

const territoires = [
  { id: 'savoie', name: 'Savoie' },
  { id: 'aoste', name: "Vallée d'Aoste" },
  { id: 'piemont', name: 'Piémont' },
  { id: 'nice', name: 'Nice', label: 'Comté de Nice' },
].map(t => {
  const proj = thin(rings[t.name].map(p => projection(p)), 120);
  // Etiquette au centroide, sauf le Piemont : son centroide tombe sur la route de Turin.
  const [x, y] = t.id === 'piemont' ? projection([8.25, 44.55]) : d3.polygonCentroid(proj);
  return { ...t, label: t.label || t.name, d: round(lineClosed(proj)), x: x.toFixed(1), y: y.toFixed(1) };
});

// Villes (lon, lat). dx/dy : decalage de l'etiquette, anchor : alignement.
const villes = [
  { id: 'chambery', name: 'Chambéry', ll: [5.9178, 45.5646], dx: -16, dy: 6, anchor: 'end' },
  { id: 'turin', name: 'Turin', ll: [7.6869, 45.0703], dx: 16, dy: 6, anchor: 'start' },
  { id: 'nice', name: 'Nice', ll: [7.2620, 43.7102], dx: 16, dy: 6, anchor: 'start' },
].map(v => ({ ...v, p: P(v.ll) }));

// Route de la Maurienne et du Mont-Cenis : Chambery, Saint-Jean-de-Maurienne,
// Lanslebourg, col du Mont-Cenis, Suse, Turin.
const route = [[5.9178, 45.5646], [6.3470, 45.2766], [6.8750, 45.2870], [6.9330, 45.2330], [7.0460, 45.1380], [7.6869, 45.0703]].map(P);
const col = P([6.9330, 45.2330]);

const esc = s => s.replace(/&/g, '&amp;').replace(/'/g, '&#39;');
const out = [
  '<svg id="map" viewBox="0 0 1920 1080">',
  '  <g id="relief">',
  ...territoires.map(t => `    <path class="relief relief-${t.id}" d="${t.d}"/>`),
  '  </g>',
  '  <g id="terres">',
  ...territoires.map(t => `    <path class="terre terre-${t.id}" d="${t.d}"/>`),
  '  </g>',
  '  <g id="contours">',
  ...territoires.map(t => `    <path class="contour contour-${t.id}" d="${t.d}"/>`),
  '  </g>',
  ...territoires.map(t => `  <text class="territoire territoire-${t.id}" x="${t.x}" y="${t.y}">${esc(t.label)}</text>`),
  // La route pointillee se revele sous un masque : un trait plein dont on anime le dashoffset.
  `  <mask id="route-masque" maskUnits="userSpaceOnUse" x="0" y="0" width="1920" height="1080"><path id="route-revele" d="${round(lineOpen(route))}"/></mask>`,
  `  <path id="route" d="${round(lineOpen(route))}" mask="url(#route-masque)"/>`,
  `  <g class="col"><circle cx="${col[0]}" cy="${col[1]}" r="4"/><text x="${col[0]}" y="${col[1] + 26}">col du Mont-Cenis</text></g>`,
  ...villes.map(v => [
    `  <g class="ville ville-${v.id}">`,
    `    <circle class="onde" cx="${v.p[0]}" cy="${v.p[1]}" r="7"/>`,
    `    <circle class="point" cx="${v.p[0]}" cy="${v.p[1]}" r="7"/>`,
    `    <text x="${v.p[0] + v.dx}" y="${v.p[1] + v.dy}" text-anchor="${v.anchor}">${esc(v.name)}</text>`,
    '  </g>',
  ].join('\n')),
  '  <circle id="voyageur" cx="0" cy="0" r="9"/>',
  '</svg>',
].map(l => l.split('\n').map(s => '          ' + s).join('\n')).join('\n');

const htmlUrl = new URL('etats-de-savoie-16x9.html', root);
const html = readFileSync(htmlUrl, 'utf8');
const re = /(<!-- carte:start -->)[\s\S]*?(\n\s*<!-- carte:end -->)/;
if (!re.test(html)) throw new Error('marqueurs carte:start / carte:end introuvables');
writeFileSync(htmlUrl, html.replace(re, `$1\n${out}$2`));
console.log(`etats-de-savoie-16x9.html : ${territoires.length} territoires, ${villes.length} villes, route ${route.length} etapes`);
