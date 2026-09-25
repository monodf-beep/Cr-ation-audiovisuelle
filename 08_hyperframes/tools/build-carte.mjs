// Precalcule les traces de la carte des Etats de Savoie (version reseaux sociaux)
// et les injecte dans index.html entre les marqueurs <!-- carte:start --> / <!-- carte:end -->.
// Le rendu HyperFrames interdit le reseau : la carte doit etre un SVG statique.
// Geometrie reprise a l'identique de 09_charte/export-cartes/carte-etats-de-savoie-social.html.
//
// Usage : node tools/build-carte.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import * as d3 from 'd3';
import { root, loadTerritoires, thin, round } from './geo-savoie.mjs';

const W = 1080, H = 1080;
const projection = d3.geoMercator();

const { fc, rings: byName } = loadTerritoires();
projection.fitExtent([[70, 340], [W - 70, H - 90]], fc);

// Frontieres communes tracees une seule fois (dedup en lon/lat, seuil 0,02 deg).
const THR = 0.02;
const gridMap = new Map();
function cellKey(p) { return Math.floor(p[0] / THR) + '_' + Math.floor(p[1] / THR); }
function addRef(points) {
  for (const p of points) {
    const k = cellKey(p);
    if (!gridMap.has(k)) gridMap.set(k, []);
    gridMap.get(k).push(p);
  }
}
function isNear(p) {
  const gx = Math.floor(p[0] / THR), gy = Math.floor(p[1] / THR);
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
    const cell = gridMap.get((gx + dx) + '_' + (gy + dy));
    if (!cell) continue;
    for (const q of cell) {
      const a = p[0] - q[0], b = p[1] - q[1];
      if (a * a + b * b <= THR * THR) return true;
    }
  }
  return false;
}
function farRuns(ring) {
  const n = ring.length;
  const flag = ring.map(isNear);
  if (flag.every(f => !f)) return { closed: true, runs: [ring] };
  if (flag.every(f => f)) return { closed: false, runs: [] };
  const start = flag.indexOf(true);
  const runs = [];
  let cur = null;
  for (let k = 0; k < n; k++) {
    const i = (start + k) % n;
    if (!flag[i]) { if (!cur) { cur = []; runs.push(cur); } cur.push(ring[i]); }
    else cur = null;
  }
  return { closed: false, runs };
}

const lineClosed = d3.line().curve(d3.curveCatmullRomClosed.alpha(0.5));
const lineOpen = d3.line().curve(d3.curveCatmullRom.alpha(0.5));
const slug = { 'Savoie': 'savoie', 'Piémont': 'piemont', 'Nice': 'nice', "Vallée d'Aoste": 'aoste' };
const paths = [], labels = [];

['Savoie', 'Piémont', 'Nice', "Vallée d'Aoste"].forEach((name, idx) => {
  const ringRaw = byName[name];
  const projRing = ringRaw.map(p => projection(p));
  const push = d => paths.push({ id: slug[name], d: round(d) });
  if (idx === 0) {
    push(lineClosed(thin(projRing, 100)));
  } else {
    const { closed, runs } = farRuns(ringRaw);
    if (closed) push(lineClosed(thin(projRing, 100)));
    else runs.forEach(run => {
      if (run.length < 3) return;
      push(lineOpen(thin(run.map(p => projection(p)), 40)));
    });
  }
  addRef(ringRaw);
  const c = d3.polygonCentroid(thin(projRing, 100));
  labels.push({ id: slug[name], name, x: c[0].toFixed(1), y: c[1].toFixed(1) });
});

const esc = s => s.replace(/&/g, '&amp;').replace(/'/g, '&#39;');
const svg = [
  '<svg id="map" viewBox="0 0 1080 1080">',
  ...paths.map((p, i) => `  <path class="outline trace-${p.id}" id="trace-${i}" d="${p.d}"/>`),
  ...labels.map(l => `  <text class="label label-${l.id}" x="${l.x}" y="${l.y}">${esc(l.name)}</text>`),
  '</svg>',
].map(l => '        ' + l).join('\n');

const htmlUrl = new URL('index.html', root);
const html = readFileSync(htmlUrl, 'utf8');
const re = /(<!-- carte:start -->)[\s\S]*?(\n\s*<!-- carte:end -->)/;
if (!re.test(html)) throw new Error('marqueurs carte:start / carte:end introuvables dans index.html');
writeFileSync(htmlUrl, html.replace(re, `$1\n${svg}$2`));
console.log(`index.html : ${paths.length} traces, ${labels.length} etiquettes`);
