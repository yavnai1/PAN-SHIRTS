// node render.js <page.html> <states.json> <outdir> <W> <H>
// Screenshots one transparent PNG per overlay state (+ intro.png / end.png, opaque).
const path = require('path'), fs = require('fs');
let pw; for (const p of ['playwright', '/opt/node22/lib/node_modules/playwright',
  path.join(process.env.ZN_CACHE || path.join(process.env.HOME, '.cache/zan-nadir-video'), 'node_modules/playwright')]) {
  try { pw = require(p); break; } catch (e) {} }
if (!pw) { console.error('playwright not found, run setup.sh'); process.exit(1); }
(async () => {
  const [page, statesFile, out, W, H] = process.argv.slice(2);
  const st = JSON.parse(fs.readFileSync(statesFile));
  fs.mkdirSync(out, { recursive: true });
  const b = await pw.chromium.launch();
  const p = await b.newPage({ viewport: { width: +W, height: +H } });
  await p.goto('file://' + path.resolve(page));
  await p.waitForFunction(() => window.ready);
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(300);
  for (const [name, s] of [['intro', { intro: 1 }], ['end', { end: 1 }]]) {
    await p.evaluate(s => show(s), s); await p.waitForTimeout(80);
    await p.screenshot({ path: path.join(out, name + '.png') });
  }
  let list = '';
  for (let i = 0; i < st.length; i++) {
    await p.evaluate(s => show(s), st[i].s); await p.waitForTimeout(40);
    const f = path.join(out, `s${String(i).padStart(3, '0')}.png`);
    await p.screenshot({ path: f, omitBackground: true });
    list += `file '${path.resolve(f)}'\nduration ${(st[i].b - st[i].a).toFixed(3)}\n`;
  }
  list += `file '${path.resolve(path.join(out, `s${String(st.length - 1).padStart(3, '0')}.png`))}'\n`;
  fs.writeFileSync(path.join(out, 'overlay.txt'), list);
  await b.close();
})();
