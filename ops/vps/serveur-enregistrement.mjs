// Petit serveur du VPS, derriere Caddy (mot de passe) sous /enregistrement/ :
// - sert les fichiers du depot (pages d'enregistrement, montages rendus, polices), avec les requetes
//   partielles (Range) pour que la video du montage se deplace sans tout telecharger ;
// - recoit les prises de voix off : POST /<projet>/televerser?nom=<fichier> les ecrit dans
//   <depot>/<projet>/voix-off/, puis les copie aussitot dans Google Drive (rclone) ;
// - la bibliotheque de montage (/bibliotheque/) : catalogue, choix (garder / ecarter) et fichiers
//   televerses, gardes dans <depot>/bibliotheque/donnees et fichiers/, copies dans Drive ;
// - les rendus sans terminal (/rendu/) : etat des rendus, et demande de rendu lancee par synchro.sh.
// Sans dependance. Variables : DEPOT (chemin du depot), PORT (8090), DRIVE (ex. drive:Videos).
import { createServer } from 'node:http';
import { createReadStream, createWriteStream, mkdirSync, statSync, watchFile, readFileSync, writeFileSync, renameSync, unlinkSync, existsSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { join, normalize, extname, basename, resolve, sep } from 'node:path';

const DEPOT = process.env.DEPOT || '/srv/studio/depot';
const PORT = +(process.env.PORT || 8090);
const DRIVE = process.env.DRIVE || '';

const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.mp4': 'video/mp4', '.webm': 'video/webm', '.m4a': 'audio/mp4', '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.svg': 'image/svg+xml', '.woff': 'font/woff', '.woff2': 'font/woff2', '.md': 'text/plain; charset=utf-8',
  '.pdf': 'application/pdf', '.zip': 'application/zip' };

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
  if (!projet || projet.startsWith('.') || !/\.(webm|m4a|mp4|wav|json)$/i.test(nom)) { res.writeHead(400); return res.end('Nom invalide'); }
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

// --- Rendus sans terminal (page /rendu/) : une demande deposee ici est lancee par synchro.sh ---
const projets = () => readdirSync(DEPOT, { withFileTypes: true })
  .filter((d) => d.isDirectory() && !d.name.startsWith('.') && existsSync(join(DEPOT, d.name, 'index.html'))
    && readFileSync(join(DEPOT, d.name, 'index.html'), 'utf8').includes('data-composition-id'))
  .map((d) => d.name);
function etatRendu(p) {
  const r = join(DEPOT, p, 'renders');
  const lire = (f) => { try { return readFileSync(join(r, f), 'utf8'); } catch { return ''; } };
  let etat = null; try { etat = JSON.parse(lire('etat-rendu.json')); } catch {}
  const journal = lire('rendu.log');
  const pourcents = [...journal.slice(-6000).matchAll(/(\d{1,3})%/g)];
  const fichier = etat?.fichier || (p === '10_cern' ? 'cern-reportage.mp4' : `${p}.mp4`);
  let video = null; try { const st = statSync(join(r, fichier)); video = { chemin: `${p}/renders/${fichier}`, taille: st.size, date: st.mtime }; } catch {}
  const metriques = (() => { try { return readFileSync(join(DEPOT, p, 'metriques.md'), 'utf8'); } catch { return ''; } })();
  const alertes = [...metriques.matchAll(/^- (.+)$/gm)].map((m) => m[1]).slice(0, 20);
  const etape = [...journal.matchAll(/^== (\w+)/gm)].map((m) => m[1]).pop() || null;
  return { projet: p, demande: existsSync(join(r, 'demande-rendu.json')), etat, etape,
    progression: pourcents.length ? +pourcents[pourcents.length - 1][1] : null,
    fin_journal: journal.split('\n').filter((l) => /ECHEC|Error|error/.test(l)).slice(-5), video, alertes,
    metriques_ok: /Aucune alerte/.test(metriques), metriques: !!metriques };
}
function rendu(req, res, route) {
  if (req.method === 'GET' && route === 'etat') return json(res, 200, { projets: projets().map(etatRendu) });
  if (req.method === 'POST' && route === 'demander') {
    const p = new URL(req.url, 'http://x').searchParams.get('projet');
    if (!projets().includes(p)) return json(res, 400, { erreur: 'projet inconnu' });
    const e = etatRendu(p);
    if (e.demande || e.etat?.etat === 'en cours') return json(res, 409, { erreur: 'un rendu est deja demande ou en cours' });
    mkdirSync(join(DEPOT, p, 'renders'), { recursive: true });
    writeFileSync(join(DEPOT, p, 'renders', 'demande-rendu.json'), JSON.stringify({ date: new Date().toISOString() }));
    return json(res, 200, { ok: true });
  }
  json(res, 404, { erreur: 'inconnu' });
}

// --- Bibliotheque de montage ---
const BIBLIO = join(DEPOT, 'bibliotheque');
const ETAT = join(BIBLIO, 'donnees', 'etat.json');
const TYPES_BIBLIO = { son: /\.(mp3|wav|m4a|aac|ogg|flac)$/i, musique: /\.(mp3|wav|m4a|aac|ogg|flac)$/i,
  graphique: /\.(mp4|webm|mov|png|jpe?g|gif|webp|svg)$/i, style: /\.(zip|md|pdf|png|jpe?g|webp)$/i };
const lireEtat = () => { try { return JSON.parse(readFileSync(ETAT, 'utf8')); } catch { return { choix: {}, televerses: [] }; } };
const versDrive = (local, distant) => { if (DRIVE) spawn('rclone', ['copyto', local, `${DRIVE}/bibliotheque/${distant}`], { stdio: 'ignore', detached: true }).unref(); };
function ecrireEtat(etat) {
  mkdirSync(join(BIBLIO, 'donnees'), { recursive: true });
  writeFileSync(ETAT + '.tmp', JSON.stringify(etat, null, 1)); renameSync(ETAT + '.tmp', ETAT);
  versDrive(ETAT, 'donnees/etat.json');
}
const json = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }); res.end(JSON.stringify(obj)); };
const corps = (req) => new Promise((ok, ko) => { let d = ''; req.on('data', (c) => { d += c; if (d.length > 1e6) req.destroy(); }); req.on('end', () => ok(d)); req.on('error', ko); });

async function bibliotheque(req, res, route) {
  const url = new URL(req.url, 'http://x');
  if (req.method === 'GET' && route === 'catalogue') {
    let catalogue = { sons: [] };
    try { catalogue = JSON.parse(readFileSync(join(BIBLIO, 'catalogue.json'), 'utf8')); } catch {}
    const sons = catalogue.sons.map((s) => ({ ...s, fichier: `fichiers/sons/${s.id}.mp3`, present: existsSync(join(BIBLIO, 'fichiers', 'sons', s.id + '.mp3')) }));
    return json(res, 200, { sons, ...lireEtat() });
  }
  if (req.method === 'POST' && route === 'choix') {
    const { id, choix } = JSON.parse(await corps(req) || '{}');
    if (!id || !/^[\w.-]+$/.test(id) || ![null, 'garde', 'ecarte'].includes(choix ?? null)) return json(res, 400, { erreur: 'choix invalide' });
    const etat = lireEtat();
    if (choix) etat.choix[id] = choix; else delete etat.choix[id];
    ecrireEtat(etat); return json(res, 200, { ok: true });
  }
  if (req.method === 'POST' && route === 'televerser') {
    const type = url.searchParams.get('type');
    const nom = basename(url.searchParams.get('nom') || '').replace(/[^\w.,-]/g, '_');
    if (!TYPES_BIBLIO[type] || !TYPES_BIBLIO[type].test(nom)) return json(res, 400, { erreur: 'type de fichier non accepte' });
    const id = `ajout-${Date.now().toString(36)}`;
    const dossier = join(BIBLIO, 'fichiers', 'televerses');
    mkdirSync(dossier, { recursive: true });
    const f = join(dossier, `${id}-${nom}`);
    const sortie = createWriteStream(f);
    req.pipe(sortie);
    sortie.on('error', (e) => json(res, 500, { erreur: e.message }));
    return sortie.on('finish', () => {
      const champ = (k, max = 300) => (url.searchParams.get(k) || '').slice(0, max);
      const entree = { id, type, fichier: `fichiers/televerses/${id}-${nom}`, titre: champ('titre') || nom, categorie: champ('categorie'),
        usage: champ('usage', 600), source: champ('source'), licence: champ('licence'), date: new Date().toISOString().slice(0, 10) };
      const etat = lireEtat(); etat.televerses.push(entree); etat.choix[id] = 'garde'; ecrireEtat(etat);
      versDrive(f, `fichiers/televerses/${id}-${nom}`);
      json(res, 200, { ok: true, entree });
    });
  }
  if (req.method === 'POST' && route === 'retirer') {
    const { id } = JSON.parse(await corps(req) || '{}');
    const etat = lireEtat(); const e = etat.televerses.find((x) => x.id === id);
    if (!e) return json(res, 404, { erreur: 'introuvable' });
    etat.televerses = etat.televerses.filter((x) => x.id !== id); delete etat.choix[id]; ecrireEtat(etat);
    try { unlinkSync(join(BIBLIO, e.fichier)); } catch {}
    return json(res, 200, { ok: true });
  }
  json(res, 404, { erreur: 'inconnu' });
}

createServer((req, res) => {
  const r = /^\/rendu\/api\/(\w+)/.exec(req.url);
  if (r) { try { return rendu(req, res, r[1]); } catch (e) { return json(res, 500, { erreur: e.message }); } }
  const b = /^\/bibliotheque\/api\/(\w+)/.exec(req.url);
  if (b) return bibliotheque(req, res, b[1]).catch((e) => json(res, 500, { erreur: e.message }));
  const m = /^\/([^/?]+)\/televerser(\?|$)/.exec(req.url);
  if (req.method === 'POST' && m) return televerser(req, res, decodeURIComponent(m[1]));
  if (req.method === 'GET' || req.method === 'HEAD') return servir(req, res);
  res.writeHead(405); res.end();
}).listen(PORT, '127.0.0.1', () => console.log(`enregistrement : http://127.0.0.1:${PORT} (depot ${DEPOT})`));

// Mise a jour automatique : quand la synchronisation GitHub modifie ce fichier, on quitte ;
// systemd (Restart=always) relance aussitot la nouvelle version.
watchFile(fileURLToPath(import.meta.url), { interval: 5000 }, () => { console.log('nouvelle version, redemarrage'); process.exit(0); });
