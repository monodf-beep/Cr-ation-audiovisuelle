// Precalcule les traces de la carte des Etats de Savoie (version reseaux sociaux)
// et les injecte dans index.html entre les marqueurs <!-- carte:start --> / <!-- carte:end -->.
// Le rendu HyperFrames interdit le reseau : la carte doit etre un SVG statique.
// Geometrie reprise a l'identique de 09_charte/export-cartes/carte-etats-de-savoie-social.html.
//
// Usage : node tools/build-carte.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';

const root = new URL('../', import.meta.url);
const read = p => JSON.parse(readFileSync(new URL(p, root), 'utf8'));

const W = 1080, H = 1080;
const projection = d3.geoMercator();

function ringPoints(ring) {
  const pts = ring.slice();
  const f = pts[0], l = pts[pts.length - 1];
  if (pts.length > 1 && f[0] === l[0] && f[1] === l[1]) pts.pop();
  return pts;
}
function keyOf(p) { return Math.round(p[0] * 1e5) + '_' + Math.round(p[1] * 1e5); }
function mergeTwoRings(ringA, ringB) {
  const ptsA = ringPoints(ringA), ptsB = ringPoints(ringB);
  const nA = ptsA.length;
  const keysB = new Map();
  ptsB.forEach((p, i) => keysB.set(keyOf(p), i));
  const matchedA = ptsA.map(p => keysB.has(keyOf(p)));
  let bestLen = 0, bestStart = -1;
  for (let s = 0; s < nA; s++) {
    if (!matchedA[s] || matchedA[(s - 1 + nA) % nA]) continue;
    let len = 0, i = s;
    while (matchedA[i] && len <= nA) { len++; i = (i + 1) % nA; }
    if (len > bestLen) { bestLen = len; bestStart = s; }
  }
  if (bestStart === -1 || bestLen < 2) return null;
  const s = bestStart, e = (bestStart + bestLen - 1) % nA;
  const firstShared = ptsA[s], lastShared = ptsA[e];
  function sliceCirc(arr, from, to) {
    const n = arr.length, out = [];
    let i = from;
    while (true) { out.push(arr[i]); if (i === to) break; i = (i + 1) % n; }
    return out;
  }
  const midA = sliceCirc(ptsA, (e + 1) % nA, (s - 1 + nA) % nA);
  const outerA = [lastShared, ...midA, firstShared];
  const idxFirstB = keysB.get(keyOf(firstShared));
  const idxLastB = keysB.get(keyOf(lastShared));
  const sharedSet = new Set();
  for (let k = 0; k < bestLen; k++) sharedSet.add(keyOf(ptsA[(s + k) % nA]));
  const cand1 = sliceCirc(ptsB, idxFirstB, idxLastB);
  const cand2 = sliceCirc(ptsB, idxLastB, idxFirstB);
  const nonSharedCount = arr => arr.filter(p => !sharedSet.has(keyOf(p))).length;
  let outerB = nonSharedCount(cand1) > nonSharedCount(cand2) ? cand1 : cand2;
  if (keyOf(outerB[0]) !== keyOf(firstShared)) outerB = outerB.slice().reverse();
  return [...outerA, ...outerB.slice(1)];
}
function largestRing(geometry) {
  const rings = geometry.type === 'Polygon' ? geometry.coordinates : geometry.coordinates.flat();
  return rings.sort((a, b) => b.length - a.length)[0];
}
function thin(points, target) {
  if (points.length <= target) return points;
  const step = Math.max(1, Math.floor(points.length / target));
  return points.filter((_, i) => i % step === 0);
}

const savoie73 = read('assets/data/departement-73-savoie.geojson');
const savoie74 = read('assets/data/departement-74-haute-savoie.geojson');
const arr = read('assets/data/arrondissements-06-alpes-maritimes.geojson');
const itTopo = read('assets/data/limits_IT_regions.topo.json');

const nice = arr.features.find(f => f.properties.code === '06002');
const itKey = Object.keys(itTopo.objects)[0];
const itRegions = topojson.feature(itTopo, itTopo.objects[itKey]).features;
const piemonte = itRegions.find(f => f.properties.reg_istat_code === '01');
const valleAosta = itRegions.find(f => f.properties.reg_istat_code === '02');

const fc = { type: 'FeatureCollection', features: [savoie73, savoie74, nice, piemonte, valleAosta] };
projection.fitExtent([[70, 340], [W - 70, H - 90]], fc);

const mergedSavoieRaw = mergeTwoRings(largestRing(savoie73.geometry), largestRing(savoie74.geometry)) || largestRing(savoie73.geometry);
const byName = {
  'Savoie': mergedSavoieRaw,
  'Nice': largestRing(nice.geometry),
  'Piémont': largestRing(piemonte.geometry),
  "Vallée d'Aoste": largestRing(valleAosta.geometry),
};

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

const round = s => s.replace(/-?\d+\.\d+/g, n => (+n).toFixed(1));
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
