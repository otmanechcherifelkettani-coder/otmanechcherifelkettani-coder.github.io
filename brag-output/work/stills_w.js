const { chromium } = require('playwright');
(async () => {
  const V = process.env.F === 'v'; const W = V ? 1080 : 1920, H = V ? 1920 : 1080;
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: W, height: H } });
  pg.on('pageerror', e => console.log('ERR', e.message)); pg.on('console', m => { if (m.type() === 'error') console.log('CON', m.text()); });
  await pg.goto('file://' + __dirname + '/workshop.html' + (V ? '#v' : '')); await pg.evaluate(() => document.fonts.ready);
  const dir = 'stills/w' + (V ? 'v' : 'h'); require('fs').mkdirSync(dir, { recursive: true });
  for (const t of process.env.TS.split(',').map(Number)) { await pg.evaluate(t => window.render(t), t); await pg.screenshot({ path: `${dir}/${t.toFixed(2)}.png` }); }
  await b.close();
})();
