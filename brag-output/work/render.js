const { chromium } = require('playwright');
const { spawn } = require('child_process');
(async () => {
  const FPS = 30, DUR = 25.0, N = Math.round(FPS * DUR);
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await pg.goto('file://' + __dirname + '/' + (process.env.PAGE || 'video.html'));
  await pg.evaluate(() => document.fonts.ready);
  await pg.waitForFunction(() => [...document.images].every(i => i.complete));
  const ff = spawn('ffmpeg', ['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','png','-i','-',
    '-c:v','libx264','-preset','slow','-crf','16','-pix_fmt','yuv420p',(process.env.OUT || 'video_noaudio.mp4')], { stdio: ['pipe','inherit','inherit'] });
  for (let i = 0; i < N; i++) {
    await pg.evaluate(t => window.render(t), i / FPS);
    const buf = await pg.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await b.close(); console.log('frames', N);
})();
