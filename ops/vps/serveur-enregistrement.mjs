// Petit serveur du VPS, derriere Caddy (mot de passe) sous /enregistrement/ :
// - sert les fichiers du depot (pages d'enregistrement, montages rendus, polices), avec les requetes
//   partielles (Range) pour que la video du montage se deplace sans tout telecharger ;
// - recoit les prises de voix off : POST /<projet>/televerser?nom=<fichier> les ecrit dans
//   <depot>/<projet>/voix-off/, puis les copie aussitot dans Google Drive (rclone).
// Sans dependance. Variables : DEPOT (chemin du depot), PORT (8090), DRIVE (ex. drive:Videos).
import { createServer } from 'node:http';
import { createReadStream, createWriteStream, mkdirSync, statSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { join, normalize, extname, basename, resolve, sep } from 'node:path';

const DEPOT = process.env.DEPOT || '/srv/studio/depot';
const PORT = +(process.env.PORT || 8090);
const DRIVE = process.env.DRIVE || '';

const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.mp4': 'video/mp4', '.webm': 'video/webm', '.m4a': 'audio/mp4', '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.svg': 'image/svg+xml', '.woff': 'font/woff', '.woff2': 'font/woff2' };

// Chemin sur, sans sortie du depot ni fichiers caches (.git, .env...).
function chemin(url) {
  const p = normalize(decodeURIComponent(url.split('?')[0])).replace(/^([/\\])+/, '');
  if (p.split(/[/\\]/).some((s) => s.startsWith('.') || s === 'node_modules')) return null;
  const f = resolve(DEPOT, p);
  return f === resolve(DEPOT) || f.startsWith(resolve(DEPOT) + sep) ? f : null;
}

function servir(req, res) {
  let f = chemin(req.url);
  if (!f) { res.writeHead(403); return res.end(); }
  let st;
  try { st = statSync(f); if (st.isDirectory()) { f = join(f, 'index.html'); st = statSync(f); } }
  catch { res.writeHead(404); return res.end('Introuvable'); }
  const type = TYPES[extname(f).toLowerCase()] || 'application/octet-stream';
  const plage = /bytes=(\d*)-(\d*)/.exec(req.headers.range || '');
  if (plage) {
    const debut = plage[1] ? +plage[1] : st.size - +plage[2];
    const fin = plage[1] && plage[2] ? +plage[2] : st.size - 1;
    res.writeHead(206, { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Content-Length': fin - debut + 1,
      'Content-Range': `bytes ${debut}-${fin}/${st.size}`, 'Cache-Control': 'no-cache' });
    return createReadStream(f, { start: debut, end: fin }).pipe(res);
  }
  res.writeHead(200, { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Content-Length': st.size, 'Cache-Control': 'no-cache' });
  createReadStream(f).pipe(res);
}

function televerser(req, res, projet) {
  const nom = basename(new URL(req.url, 'http://x').searchParams.get('nom') || '').replace(/[^\w.,-]/g, '_');
  if (!projet || projet.startsWith('.') || !/\.(webm|m4a|mp4|wav)$/i.test(nom)) { res.writeHead(400); return res.end('Nom invalide'); }
  const dossier = join(DEPOT, projet, 'voix-off');
  mkdirSync(dossier, { recursive: true });
  const f = join(dossier, nom);
  const sortie = createWriteStream(f);
  req.pipe(sortie);
  sortie.on('finish', () => {
    if (DRIVE) spawn('rclone', ['copyto', f, `${DRIVE}/${projet}/voix-off/${nom}`], { stdio: 'ignore', detached: true }).unref();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, fichier: `${projet}/voix-off/${nom}`, drive: !!DRIVE }));
  });
  sortie.on('error', (e) => { res.writeHead(500); res.end(e.message); });
}

createServer((req, res) => {
  const m = /^\/([^/?]+)\/televerser(\?|$)/.exec(req.url);
  if (req.method === 'POST' && m) return televerser(req, res, decodeURIComponent(m[1]));
  if (req.method === 'GET' || req.method === 'HEAD') return servir(req, res);
  res.writeHead(405); res.end();
}).listen(PORT, '127.0.0.1', () => console.log(`enregistrement : http://127.0.0.1:${PORT} (depot ${DEPOT})`));
