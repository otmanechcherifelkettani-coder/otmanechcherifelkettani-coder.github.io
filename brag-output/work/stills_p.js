const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  pg.on('pageerror', e => console.log('ERR', e.message));
  await pg.goto('file://' + __dirname + '/personal.html'); await pg.evaluate(() => document.fonts.ready);
  const ts = process.env.TS.split(',').map(Number); require('fs').mkdirSync('stills/p', { recursive: true });
  for (const t of ts) { await pg.evaluate(t => window.render(t), t); await pg.screenshot({ path: `stills/p/${t.toFixed(2)}.png` }); }
  await b.close();
})();
