// Rend generique.html image par image dans Chromium et l'assemble avec ffmpeg.
//
//   NODE_PATH=$(npm root -g) node jingle_reels/rendu.js 1080 1920 out/generique_9x16.mp4 out/generique.wav
//   ... rendu.js 1080 1920 --planche 5,20,31,45,59,66,80,92,103,118,140,200 out/planche.png
//
// FFMPEG : chemin de ffmpeg (sinon celui d'imageio-ffmpeg, sinon "ffmpeg").

const { chromium } = require('playwright');
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const FPS = 30, IMAGES = 210;
const ICI = __dirname;

function ffmpegExe() {
  if (process.env.FFMPEG) return process.env.FFMPEG;
  try { return execSync('python3 -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())"').toString().trim(); }
  catch { return 'ffmpeg'; }
}

async function page(w, h) {
  const nav = await chromium.launch({
    executablePath: fs.existsSync('/opt/pw-browsers/chromium') ? undefined : undefined,
    args: ['--allow-file-access-from-files'],
  });
  const p = await nav.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.join(ICI, 'generique.html') + `?w=${w}&h=${h}`);
  await p.evaluate(() => window.pret);
  return [nav, p];
}

async function image(p, f) {
  await p.evaluate(f => window.dessiner(f), f);
  return p.locator('canvas').screenshot({ type: 'png' });
}

(async () => {
  const [w, h] = [+process.argv[2], +process.argv[3]];
  const [nav, p] = await page(w, h);
  if (process.argv[4] === '--planche') {
    const fs_ = process.argv[5].split(',').map(Number);
    const sortie = process.argv[6];
    fs.mkdirSync(sortie, { recursive: true });
    for (const f of fs_) fs.writeFileSync(path.join(sortie, `f${String(f).padStart(3, '0')}.png`), await image(p, f));
  } else {
    const [sortie, wav] = [process.argv[4], process.argv[5]];
    const ff = spawn(ffmpegExe(), ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
      '-i', '-', ...(wav ? ['-i', wav] : []),
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
      ...(wav ? ['-c:a', 'aac', '-b:a', '256k', '-shortest'] : []),
      '-movflags', '+faststart', sortie], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = 0; f < IMAGES; f++) {
      const buf = await image(p, f);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await nav.close();
})();
