// Carte verticale Savoie - Grand Geneve pour le reportage CERN, injectee dans index.html
// entre <!-- carte:start --> et <!-- carte:end -->. Precalculee : le rendu ne charge rien.
// Sources : france-geojson (gregoiredavid) pour 01/73/74, click_that_hood pour les cantons,
// geo.api.gouv.fr pour les 117 communes du Genevois francais, swisstopo pour Geneve et Nyon, ISTAT pour l'Italie.
// Traits : tres epais Savoie / France-Suisse et bord exterieur ; moyen Savoie / Aoste / Piemont ; leger 73/74 et provinces piemontaises.
//
// Usage : node tools/build-carte.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import * as d3 from 'd3';
import { topology } from 'topojson-server';
import { merge, mesh, feature } from 'topojson-client';

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

// Savoie historique : 73 et 74 fusionnes (remplissage) ; la limite 73/74 est tracee a part, legere.
const savoieUnie = fusion([savoie, hauteSavoie]);
const topoSav = topology({ d: { type: 'FeatureCollection', features: [savoie, hauteSavoie] } }, 1e6);
const limite7374 = mesh(topoSav, topoSav.objects.d, (a, b) => a !== b);

// Grand Geneve : Pole metropolitain du Genevois francais (8 intercommunalites) + Geneve + district de Nyon.
const ggFr = fusion(read('data/grand-geneve-fr.geojson').features);
const ggCh = fusion(read('data/grand-geneve-ch.geojson').features.map(redresse));

// Italie : regions et provinces (ISTAT). Vallee d'Aoste = 02, Piemont = 01.
const itReg = read('data/limits_IT_regions.topo.json'), itProv = read('data/limits_IT_provinces.topo.json');
const regs = feature(itReg, itReg.objects.regions).features;
const ETATS = new Set(['01', '02']);
const code = g => g.properties.reg_istat_code;
const aoste = regs.find(f => code(f) === '02'), piemont = regs.find(f => code(f) === '01');
const autresIt = regs.filter(f => !ETATS.has(code(f)));
// Moyen : Aoste - Piemont (arcs communs exacts).
const aostePiemont = mesh(itReg, itReg.objects.regions, (a, b) => a !== b && ETATS.has(code(a)) && ETATS.has(code(b)));
// Leger : entre provinces du Piemont.
const provPiemont = mesh(itProv, itProv.objects.provinces, (a, b) => a !== b && code(a) === '01' && code(b) === '01');
// Bord exterieur d'Aoste + Piemont (vers la Suisse, la France, la Lombardie, la Ligurie).
const bordItalie = mesh(itReg, itReg.objects.regions, (a, b) => (a === b && ETATS.has(code(a))) || (ETATS.has(code(a)) !== ETATS.has(code(b))));

// Proximite en lon/lat (seuil ~3 km) : les sources FR et IT ne partagent pas leurs sommets.
const THR = 0.03;
function grille(lignes) {
  const g = new Map();
  for (const l of lignes) for (const p of l) {
    const k = Math.floor(p[0] / THR) + '_' + Math.floor(p[1] / THR);
    if (!g.has(k)) g.set(k, []); g.get(k).push(p);
  }
  return p => {
    const gx = Math.floor(p[0] / THR), gy = Math.floor(p[1] / THR);
    for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (const q of g.get((gx + dx) + '_' + (gy + dy)) || [])
      if ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 <= THR * THR) return true;
    return false;
  };
}
const anneaux = geom => geom.type === 'Polygon' ? [geom.coordinates[0]] : geom.coordinates.map(pl => pl[0]);
// Decoupe des lignes en troncons selon un critere (vrai/faux) sur chaque point.
function troncons(lignes, test) {
  const oui = [], non = [];
  for (const l of lignes) {
    let cur = null, etat = null;
    for (const p of l) {
      const t = test(p);
      if (t !== etat) { if (cur && cur.length > 1) (etat ? oui : non).push(cur); cur = cur ? [cur[cur.length - 1], p] : [p]; etat = t; }
      else cur.push(p);
    }
    if (cur && cur.length > 1) (etat ? oui : non).push(cur);
  }
  return { oui, non };
}
const presItalie = grille([...anneaux(aoste.geometry), ...anneaux(piemont.geometry)]);
const presSavoie = grille(anneaux(savoieUnie.geometry));
// Savoie : moyen vers l'Italie, tres epais vers la France et la Suisse.
const bordSavoie = troncons(anneaux(savoieUnie.geometry), presItalie);
// Italie : la partie contre la Savoie est deja tracee (moyen) ; le reste est le bord exterieur.
const bordIt = troncons(bordItalie.coordinates, presSavoie);

const MLS = c => ({ type: 'MultiLineString', coordinates: c });
const traitEpais = MLS([...bordSavoie.non, ...bordIt.non]);
const traitMoyen = MLS([...bordSavoie.oui, ...aostePiemont.coordinates]);
const traitLeger = MLS([...limite7374.coordinates, ...provPiemont.coordinates]);

// Globe du CERN, position relevee sur l'orthophoto swisstopo.
const GLOBE = [6.05573, 46.23402];

const projection = d3.geoMercator().fitExtent([[80, 640], [1000, 1560]],
  { type: 'FeatureCollection', features: [savoie, hauteSavoie, geneve, aoste] });
const path = d3.geoPath(projection);
const P = ll => projection(ll).map(v => +v.toFixed(1));
const round = s => s.replace(/-?\d+\.\d+/g, n => (+n).toFixed(1));

const zones = [
  { id: 'ain', f: ain, cls: 'contexte' },
  { id: 'isere', f: read('data/departement-38-isere.geojson'), cls: 'contexte' },
  { id: 'hautes-alpes', f: read('data/departement-05-hautes-alpes.geojson'), cls: 'contexte' },
  { id: 'vaud', f: vaud, cls: 'contexte' },
  { id: 'valais', f: valais, cls: 'contexte' },
  ...autresIt.map((f, i) => ({ id: 'it' + i, f, cls: 'contexte' })),
  { id: 'aoste', f: aoste, cls: 'etats' },
  { id: 'piemont', f: piemont, cls: 'etats' },
  { id: 'savoie', f: savoieUnie, cls: 'savoie' },
  { id: 'geneve', f: geneve, cls: 'geneve' },
];

// Etiquettes (lon, lat) placees a la main.
const etiquettes = [
  { id: 'savoie', t: 'Savoie', ll: [6.38, 46.0] },
  { id: 'geneve', t: 'Genève', ll: [6.13, 46.19], cls: 'fort' },
  { id: 'aoste', t: "Vallée d'Aoste", ll: [7.4, 45.72] },
  { id: 'piemont', t: 'Piémont', ll: [7.5, 45.45] },
  { id: 'ain', t: 'Ain', ll: [5.55, 46.05], cls: 'contexte' },
  { id: 'suisse', t: 'SUISSE', ll: [7.2, 46.42], cls: 'pays' },
  { id: 'france', t: 'FRANCE', ll: [5.78, 45.45], cls: 'pays' },
];

const globe = P(GLOBE);
const box = d3.geoBounds({ type: 'FeatureCollection', features: [geneve] });
const g = [P(box[0]), P(box[1])];

const out = [
  '<svg id="carte" viewBox="0 0 1080 1920">',
  ...zones.map(z => `  <path class="zone ${z.cls} zone-${z.id}" d="${round(path(z.f))}"/>`),
  `  <path class="bord leger" d="${round(path(traitLeger))}"/>`,
  `  <path class="bord moyen" d="${round(path(traitMoyen))}"/>`,
  `  <path class="bord epais" d="${round(path(traitEpais))}"/>`,
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
