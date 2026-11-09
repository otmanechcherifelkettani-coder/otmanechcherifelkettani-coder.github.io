const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  pg.on('pageerror', e => console.log('ERR', e.message)); pg.on('console', m => console.log('LOG', m.text()));
  await pg.goto('file://' + __dirname + '/film.html');
  await pg.evaluate(() => document.fonts.ready);
  const ts = (process.env.TS || '1.5,4.6,7.2,9.6,12.2,14.2,16.5,18.2,21,24.8,28.4,31.8,34.3,36.8,39.3,41.8,48.8,51.5,54.2,58.5').split(',').map(Number);
  require('fs').mkdirSync('stills/film', { recursive: true });
  for (const t of ts) { await pg.evaluate(t => window.render(t), t); await pg.screenshot({ path: `stills/film/t${t.toFixed(2)}.png` }); }
  await b.close();
})();
