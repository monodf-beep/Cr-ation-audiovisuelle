// Carte verticale Savoie - Grand Geneve pour le reportage CERN, injectee dans index.html
// entre <!-- carte:start --> et <!-- carte:end -->. Precalculee : le rendu ne charge rien.
// Sources : france-geojson (gregoiredavid) pour 01/73/74, click_that_hood pour les cantons,
// geo.api.gouv.fr pour les 117 communes du Genevois francais, swisstopo pour Geneve et Nyon.
//
// Usage : node tools/build-carte.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import * as d3 from 'd3';
import { topology } from 'topojson-server';
import { merge } from 'topojson-client';

const root = new URL('../', import.meta.url);
const read = p => JSON.parse(readFileSync(new URL(p, root), 'utf8'));

const savoie = read('data/departement-73-savoie.geojson');
const hauteSavoie = read('data/departement-74-haute-savoie.geojson');
const ain = read('data/departement-01-ain.geojson');
const cantons = read('data/cantons-ge-vd-vs.geojson').features;
const canton = n => cantons.find(f => f.properties.name === n);
const geneve = canton('Genève'), vaud = canton('Vaud'), valais = canton('Valais');

// Fusionne des polygones qui partagent leurs frontieres (meme source) : pas de trait interieur.
function fusion(features) {
  const topo = topology({ f: { type: 'FeatureCollection', features } }, 1e6);
  return redresse({ type: 'Feature', properties: {}, geometry: merge(topo, topo.objects.f.geometries) });
}
// d3 attend des anneaux dans le sens horaire : une aire > demi-sphere signale un anneau inverse.
function redresse(f) {
  if (d3.geoArea(f) > 2 * Math.PI) {
    const rev = g => g.type === 'Polygon' ? { ...g, coordinates: g.coordinates.map(r => r.slice().reverse()) }
      : { ...g, coordinates: g.coordinates.map(p => p.map(r => r.slice().reverse())) };
    return { ...f, geometry: rev(f.geometry) };
  }
  return f;
}

// Savoie historique : 73 et 74 fusionnes.
const savoieUnie = fusion([savoie, hauteSavoie]);
// Grand Geneve : Pole metropolitain du Genevois francais (8 intercommunalites) + Geneve + district de Nyon.
const ggFr = fusion(read('data/grand-geneve-fr.geojson').features);
const ggCh = fusion(read('data/grand-geneve-ch.geojson').features.map(redresse));

// Globe du CERN, position relevee sur l'orthophoto swisstopo.
const GLOBE = [6.05573, 46.23402];

const projection = d3.geoMercator().fitExtent([[110, 660], [970, 1560]],
  { type: 'FeatureCollection', features: [savoie, hauteSavoie, geneve] });
const path = d3.geoPath(projection);
const P = ll => projection(ll).map(v => +v.toFixed(1));
const round = s => s.replace(/-?\d+\.\d+/g, n => (+n).toFixed(1));

const zones = [
  { id: 'ain', f: ain, cls: 'contexte' },
  { id: 'vaud', f: vaud, cls: 'contexte' },
  { id: 'valais', f: valais, cls: 'contexte' },
  { id: 'savoie', f: savoieUnie, cls: 'savoie' },
  { id: 'geneve', f: geneve, cls: 'geneve' },
];

// Etiquettes (lon, lat) placees a la main pour rester lisibles au zoom de depart.
const etiquettes = [
  { id: 'savoie', t: 'Savoie', ll: [6.42, 45.72] },
  { id: 'geneve', t: 'Genève', ll: [6.13, 46.19], cls: 'fort' },
  { id: 'ain', t: 'Ain', ll: [5.55, 46.05], cls: 'contexte' },
  { id: 'suisse', t: 'SUISSE', ll: [7.2, 46.42], cls: 'pays' },
  { id: 'france', t: 'FRANCE', ll: [5.55, 45.72], cls: 'pays' },
];

const globe = P(GLOBE);
const box = d3.geoBounds({ type: 'FeatureCollection', features: [geneve] });
const g = [P(box[0]), P(box[1])];

const out = [
  '<svg id="carte" viewBox="0 0 1080 1920">',
  ...zones.map(z => `  <path class="zone ${z.cls} zone-${z.id}" d="${round(path(z.f))}"/>`),
  // Frontiere franco-suisse : contour des cantons, en tirets.
  `  <path id="frontiere" d="${round(path({ type: 'FeatureCollection', features: [geneve, vaud, valais] }))}"/>`,
  // Aire du Grand Geneve, revelee a la fin du reportage.
  `  <g id="gg"><path class="gg" d="${round(path(ggFr))}"/><path class="gg" d="${round(path(ggCh))}"/></g>`,
  ...etiquettes.map(e => { const [x, y] = P(e.ll); return `  <text class="lieu ${e.cls || ''} lieu-${e.id}" x="${x}" y="${y}">${e.t}</text>`; }),
  `  <g id="cern"><circle class="onde" cx="${globe[0]}" cy="${globe[1]}" r="6"/><circle class="point" cx="${globe[0]}" cy="${globe[1]}" r="6"/></g>`,
  '</svg>',
].map(l => '        ' + l).join('\n');

const htmlUrl = new URL('index.html', root);
const html = readFileSync(htmlUrl, 'utf8');
const re = /(<!-- carte:start -->)[\s\S]*?(\n\s*<!-- carte:end -->)/;
if (!re.test(html)) throw new Error('marqueurs carte:start / carte:end introuvables');
writeFileSync(htmlUrl, html.replace(re, `$1\n${out}$2`));
console.log(`index.html : globe a (${globe}), boite Geneve ${JSON.stringify(g)}`);
