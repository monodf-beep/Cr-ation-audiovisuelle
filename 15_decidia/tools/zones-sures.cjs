// Zones masquees par Instagram (Reels) et TikTok : cherche le texte visible du montage qui tombe dedans.
// Joue la timeline GSAP d'index.html dans Chrome (sans le moteur de rendu), toutes les 0,25 s, et mesure
// chaque texte visible. Sortie JSON sur stdout : [{texte, zone, de, a}] (temps de la video).
// Zones sur 1080 x 1920 (memes valeurs dans 10_cern/enregistrer.html et BONNES-PRATIQUES.md, section 9) :
//   haut : y < 250 · bas : y > 1440 · droite : x > 940 entre y 700 et 1440 (boutons).
// Usage : node 04_montage/zones-sures.cjs 10_cern
const path = require('path');
const { execSync } = require('child_process');
let playwright;
try { playwright = require('playwright'); } catch { playwright = require(path.join(execSync('npm root -g').toString().trim(), 'playwright')); }

const ZONES = { haut: [0, 0, 1080, 250], bas: [0, 1440, 1080, 1920], droite: [940, 700, 1080, 1440] };

(async () => {
  const projet = path.resolve(process.argv[2] || '.');
  const navigateur = await playwright.chromium.launch();
  const page = await navigateur.newPage({ viewport: { width: 1080, height: 1920 } });
  // Sans le moteur HyperFrames, la page attend un registre de timelines deja cree.
  await page.addInitScript(() => { window.__timelines = window.__timelines || {}; });
  await page.goto('file://' + path.join(projet, 'index.html'), { waitUntil: 'load' });
  await page.waitForFunction(() => !!(window.__timelines && window.__timelines.main), null, { timeout: 30000, polling: 250 });
  await page.evaluate(() => document.fonts.ready);
  const resultats = await page.evaluate((ZONES) => {
    const tl = window.__timelines.main, duree = tl.duration(), vus = {};
    const visible = (el) => {
      let o = 1;
      for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
        const s = getComputedStyle(e);
        if (s.display === 'none' || s.visibility === 'hidden') return false;
        o *= +s.opacity;
      }
      return o > 0.1;
    };
    // Feuilles de texte HTML (pas les libelles de la carte SVG, qui bougent avec la camera).
    const feuilles = [...document.querySelectorAll('#root *')].filter((el) => !(el instanceof SVGElement)
      && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()));
    for (let t = 0; t <= duree; t += 0.25) {
      tl.seek(t, false);
      for (const el of feuilles) {
        if (!visible(el)) continue;
        const r = document.createRange(); r.selectNodeContents(el); const b = r.getBoundingClientRect();
        if (!b.width || !b.height) continue;
        for (const [nom, [x1, y1, x2, y2]] of Object.entries(ZONES)) {
          const ix = Math.min(b.right, x2) - Math.max(b.left, x1), iy = Math.min(b.bottom, y2) - Math.max(b.top, y1);
          if (ix > 4 && iy > 4) {
            const texte = el.textContent.trim().replace(/\s+/g, ' ').slice(0, 60), cle = nom + '|' + texte;
            vus[cle] = vus[cle] || { texte, zone: nom, de: t, a: t }; vus[cle].a = t;
          }
        }
      }
    }
    return Object.values(vus);
  }, ZONES);
  console.log(JSON.stringify(resultats));
  await navigateur.close();
})().catch((e) => { console.error(e.message); process.exit(1); });
