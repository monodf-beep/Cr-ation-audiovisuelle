// Deux maquettes fixes (1080 x 1920) pour comparer le rendu de la « culture savoyarde partagee » :
// A = lueur douce (flou), B = pointilles qui s'estompent. Meme base : espace sabaudo affirme.
// Usage : node tools/maquettes-diffus.mjs <dossier de sortie>
import { readFileSync, writeFileSync } from 'node:fs';
import * as d3 from 'd3';
import { topology } from 'topojson-server';
import { merge, mesh, feature } from 'topojson-client';

const root = new URL('../', import.meta.url);
const read = p => JSON.parse(readFileSync(new URL(p, root), 'utf8'));
const sortie = process.argv[2] || '.';

function redresse(f) {
  if (d3.geoArea(f) > 2 * Math.PI) {
    const rev = g => g.type === 'Polygon' ? { ...g, coordinates: g.coordinates.map(r => r.slice().reverse()) }
      : { ...g, coordinates: g.coordinates.map(p => p.map(r => r.slice().reverse())) };
    return { ...f, geometry: rev(f.geometry) };
  }
  return f;
}
function fusion(features) {
  const topo = topology({ f: { type: 'FeatureCollection', features } }, 1e6);
  return redresse({ type: 'Feature', properties: {}, geometry: merge(topo, topo.objects.f.geometries) });
}

const savoie = read('data/departement-73-savoie.geojson'), hauteSavoie = read('data/departement-74-haute-savoie.geojson');
const ain = read('data/departement-01-ain.geojson'), isere = read('data/departement-38-isere.geojson'), hautesAlpes = read('data/departement-05-hautes-alpes.geojson');
const cantons = read('data/cantons-ge-vd-vs.geojson').features;
const canton = n => cantons.find(f => f.properties.name === n);
const geneve = canton('Genève'), vaud = canton('Vaud'), valais = canton('Valais');

const savoieUnie = fusion([savoie, hauteSavoie]);
const topoSav = topology({ d: { type: 'FeatureCollection', features: [savoie, hauteSavoie] } }, 1e6);
const limite7374 = mesh(topoSav, topoSav.objects.d, (a, b) => a !== b);

const itReg = read('data/limits_IT_regions.topo.json'), itProv = read('data/limits_IT_provinces.topo.json');
const regs = feature(itReg, itReg.objects.regions).features;
const code = g => g.properties.reg_istat_code;
const ETATS = new Set(['01', '02']);
const aoste = regs.find(f => code(f) === '02'), piemont = regs.find(f => code(f) === '01');
const autresIt = regs.filter(f => !ETATS.has(code(f)));
const aostePiemont = mesh(itReg, itReg.objects.regions, (a, b) => a !== b && ETATS.has(code(a)) && ETATS.has(code(b)));
const provPiemont = mesh(itProv, itProv.objects.provinces, (a, b) => a !== b && code(a) === '01' && code(b) === '01');
const bordItalie = mesh(itReg, itReg.objects.regions, (a, b) => (a === b && ETATS.has(code(a))) || (ETATS.has(code(a)) !== ETATS.has(code(b))));

const THR = 0.03;
function grille(lignes) {
  const g = new Map();
  for (const l of lignes) for (const p of l) { const k = Math.floor(p[0] / THR) + '_' + Math.floor(p[1] / THR); if (!g.has(k)) g.set(k, []); g.get(k).push(p); }
  return p => { const gx = Math.floor(p[0] / THR), gy = Math.floor(p[1] / THR);
    for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (const q of g.get((gx + dx) + '_' + (gy + dy)) || [])
      if ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 <= THR * THR) return true; return false; };
}
const anneaux = geom => geom.type === 'Polygon' ? [geom.coordinates[0]] : geom.coordinates.map(pl => pl[0]);
function troncons(lignes, test) {
  const oui = [], non = [];
  for (const l of lignes) { let cur = null, etat = null;
    for (const p of l) { const t = test(p);
      if (t !== etat) { if (cur && cur.length > 1) (etat ? oui : non).push(cur); cur = cur ? [cur[cur.length - 1], p] : [p]; etat = t; } else cur.push(p); }
    if (cur && cur.length > 1) (etat ? oui : non).push(cur); }
  return { oui, non };
}
const bordSavoie = troncons(anneaux(savoieUnie.geometry), grille([...anneaux(aoste.geometry), ...anneaux(piemont.geometry)]));
const bordIt = troncons(bordItalie.coordinates, grille(anneaux(savoieUnie.geometry)));
const MLS = c => ({ type: 'MultiLineString', coordinates: c });
const contourSabaudo = MLS([...bordSavoie.non, ...bordIt.non]);
const limitesInternes = MLS([...bordSavoie.oui, ...aostePiemont.coordinates]);
const limitesLegeres = MLS([...limite7374.coordinates, ...provPiemont.coordinates]);

const projection = d3.geoMercator().fitExtent([[40, 560], [1040, 1640]],
  { type: 'FeatureCollection', features: [savoie, hauteSavoie, geneve, aoste, ain] });
const path = d3.geoPath(projection);
const P = ll => projection(ll).map(v => +v.toFixed(1));
const round = s => s.replace(/-?\d+\.\d+/g, n => (+n).toFixed(1));

// Aire de culture partagee : Geneve, Vaud, Valais (partie ouest, par le masque), Ain.
const diffus = [geneve, vaud, valais, ain];
// Centre et portee du degrade : la lueur part du nord de la Savoie et s'estompe vers l'exterieur.
const [cx, cy] = P([6.25, 46.05]);
const portee = 470;

const fonts = `
@font-face { font-family: 'Semplicita Pro'; src: url('${new URL('assets/fonts/SemplicitaPro-Semibold.woff', root)}') format('woff'); font-weight: 600; }
@font-face { font-family: 'Semplicita Pro'; src: url('${new URL('assets/fonts/SemplicitaPro-Bold.woff', root)}') format('woff'); font-weight: 700; }
@font-face { font-family: 'Cormorant Garamond'; src: url('${new URL('assets/fonts/CormorantGaramond-Italic.woff2', root)}') format('woff2'); font-weight: 500; font-style: italic; }`;

const lieuxSabaudo = [['Savoie', [6.38, 45.95]], ["Vallée d'Aoste", [7.4, 45.72]], ['Piémont', [7.55, 45.35]]];
const lieuxDiffus = [['Genève', [6.12, 46.24]], ['Pays de Vaud', [6.62, 46.62]], ['Pays de Gex', [5.98, 46.4]], ['Bugey', [5.62, 45.86]], ['Bresse', [5.2, 46.3]], ['Dombes', [5.05, 46.02]], ['Bas-Valais', [7.02, 46.27]]];

function page(variante) {
  const couche = variante === 'A'
    ? `<g mask="url(#fondu)"><g filter="url(#flou)">${diffus.map(f => `<path d="${round(path(f))}" fill="#0a36af" fill-opacity="0.34"/>`).join('')}</g></g>`
    : `<g mask="url(#fondu)">${diffus.map(f => `<path d="${round(path(f))}" fill="url(#points)"/>`).join('')}</g>`;
  const pastille = variante === 'A'
    ? `<span class="sw" style="background: radial-gradient(circle, rgba(10,54,175,.45), rgba(10,54,175,0))"></span>`
    : `<span class="sw" style="background-image: radial-gradient(#0a36af 1.6px, transparent 1.9px); background-size: 9px 9px"></span>`;
  return `<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>${fonts}
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { width: 1080px; height: 1920px; background: #fff; font-family: 'Semplicita Pro', sans-serif; color: #171719; position: relative; overflow: hidden; }
  svg { position: absolute; inset: 0; }
  .ctx { fill: #f5f5f7; stroke: #cfcfd4; stroke-width: 1.4; }
  .sab { fill: #dfe5f5; }
  .contour { fill: none; stroke: #0a36af; stroke-width: 4; stroke-linejoin: round; }
  .interne { fill: none; stroke: #0a36af; stroke-width: 1.8; stroke-opacity: .55; stroke-linejoin: round; }
  .leger { fill: none; stroke: #0a36af; stroke-width: 1.1; stroke-opacity: .35; stroke-dasharray: 2 4; }
  .n-sab { font: 700 34px 'Semplicita Pro'; fill: #0a36af; text-anchor: middle; paint-order: stroke; stroke: #fff; stroke-width: 6px; }
  .n-dif { font: italic 500 40px 'Cormorant Garamond'; fill: #1b2f6e; text-anchor: middle; paint-order: stroke; stroke: #fff; stroke-width: 6px; }
  .tete { position: absolute; left: 70px; top: 150px; right: 70px; }
  .eyebrow { font-size: 24px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: #0a36af; }
  h1 { margin-top: 14px; font-size: 64px; font-weight: 700; line-height: 1.08; }
  .variante { position: absolute; right: 40px; top: 40px; font-size: 24px; font-weight: 700; color: #fff; background: #171719; padding: 8px 16px; }
  .legende { position: absolute; left: 70px; bottom: 150px; display: flex; flex-direction: column; gap: 14px; font-size: 28px; font-weight: 600; background: rgba(255,255,255,.9); padding: 18px 22px; }
  .legende div { display: flex; align-items: center; gap: 16px; }
  .legende em { font-family: 'Cormorant Garamond'; font-style: italic; font-weight: 500; font-size: 34px; }
  .sw { width: 54px; height: 34px; display: inline-block; }
  </style></head><body>
  <svg viewBox="0 0 1080 1920">
    <defs>
      <filter id="flou" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="38"/></filter>
      <radialGradient id="grad" gradientUnits="userSpaceOnUse" cx="${cx}" cy="${cy}" r="${portee}">
        <stop offset="0" stop-color="#fff"/><stop offset="0.45" stop-color="#fff" stop-opacity="0.85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
      </radialGradient>
      <mask id="fondu" maskUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920"><rect width="1080" height="1920" fill="url(#grad)"/></mask>
      <pattern id="points" width="11" height="11" patternUnits="userSpaceOnUse"><circle cx="5.5" cy="5.5" r="2.2" fill="#0a36af"/></pattern>
    </defs>
    ${[ain, isere, hautesAlpes, vaud, valais, geneve, ...autresIt].map(f => `<path class="ctx" d="${round(path(f))}"/>`).join('\n')}
    ${couche}
    ${[aoste, piemont, savoieUnie].map(f => `<path class="sab" d="${round(path(f))}"/>`).join('\n')}
    <path class="leger" d="${round(path(limitesLegeres))}"/>
    <path class="interne" d="${round(path(limitesInternes))}"/>
    <path class="contour" d="${round(path(contourSabaudo))}"/>
    ${lieuxSabaudo.map(([t, ll]) => { const [x, y] = P(ll); return `<text class="n-sab" x="${x}" y="${y}">${t}</text>`; }).join('')}
    ${lieuxDiffus.map(([t, ll]) => { const [x, y] = P(ll); return `<text class="n-dif" x="${x}" y="${y}">${t}</text>`; }).join('')}
  </svg>
  <div class="variante">${variante === 'A' ? 'A · lueur douce' : 'B · pointillés qui s’estompent'}</div>
  <div class="tete"><div class="eyebrow">Reportage · 24 septembre 2026</div><h1>Au CERN, pour la langue savoyarde</h1></div>
  <div class="legende">
    <div><span class="sw" style="background:#dfe5f5; border: 3px solid #0a36af"></span>Espace sabaudo</div>
    <div>${pastille}<em>culture savoyarde partagée</em></div>
  </div>
  </body></html>`;
}
for (const v of ['A', 'B']) writeFileSync(`${sortie}/maquette-${v}.html`, page(v));
console.log('maquettes ecrites dans', sortie);
