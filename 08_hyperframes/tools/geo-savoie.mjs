// Geometrie partagee des cartes des Etats de Savoie.
// Fonctions reprises a l'identique de 09_charte/export-cartes/carte-etats-de-savoie-social.html.
import { readFileSync } from 'node:fs';
import * as topojson from 'topojson-client';

export const root = new URL('../', import.meta.url);
export const read = p => JSON.parse(readFileSync(new URL(p, root), 'utf8'));

export function ringPoints(ring) {
  const pts = ring.slice();
  const f = pts[0], l = pts[pts.length - 1];
  if (pts.length > 1 && f[0] === l[0] && f[1] === l[1]) pts.pop();
  return pts;
}
export function keyOf(p) { return Math.round(p[0] * 1e5) + '_' + Math.round(p[1] * 1e5); }
export function mergeTwoRings(ringA, ringB) {
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
export function largestRing(geometry) {
  const rings = geometry.type === 'Polygon' ? geometry.coordinates : geometry.coordinates.flat();
  return rings.sort((a, b) => b.length - a.length)[0];
}
export function thin(points, target) {
  if (points.length <= target) return points;
  const step = Math.max(1, Math.floor(points.length / target));
  return points.filter((_, i) => i % step === 0);
}


// Les 5 entites des Etats de Savoie, sources dans assets/data/.
export function loadTerritoires() {
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
  const savoie = mergeTwoRings(largestRing(savoie73.geometry), largestRing(savoie74.geometry)) || largestRing(savoie73.geometry);
  return {
    fc,
    rings: {
      'Savoie': savoie,
      'Nice': largestRing(nice.geometry),
      'Piémont': largestRing(piemonte.geometry),
      "Vallée d'Aoste": largestRing(valleAosta.geometry),
    },
  };
}

// Arrondit les coordonnees d'un trace SVG au dixieme de pixel.
export const round = s => s.replace(/-?\d+\.\d+/g, n => (+n).toFixed(1));
