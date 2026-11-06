const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await pg.goto('file://' + __dirname + '/video.html');
  await pg.evaluate(() => document.fonts.ready);
  await pg.waitForFunction(() => [...document.images].every(i => i.complete));
  const times = process.argv.slice(2).map(Number);
  require('fs').mkdirSync('stills', { recursive: true });
  for (const t of times) { await pg.evaluate(t => window.render(t), t); await pg.screenshot({ path: `stills/s-${t.toFixed(2)}.png` }); }
  await b.close();
})();
