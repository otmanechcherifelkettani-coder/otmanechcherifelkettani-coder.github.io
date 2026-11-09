const { chromium } = require('playwright'); const { spawn } = require('child_process');
(async()=>{ const [,, url, out, dur, w='1920', h='1080'] = process.argv; const FPS=30, N=Math.round(FPS*+dur);
 const b=await chromium.launch(); const p=await b.newPage({viewport:{width:+w,height:+h}}); p.on('pageerror',e=>console.log('ERR',e.message));
 await p.goto('http://localhost:8765/'+url); await p.waitForFunction(()=>window.done===true,{timeout:60000});
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','png','-i','-','-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',out],{stdio:['pipe','inherit','inherit']});
 for(let i=0;i<N;i++){ await p.evaluate(t=>window.render(t),i/FPS); const buf=await p.screenshot({type:'png'}); if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r)); }
 ff.stdin.end(); await new Promise(r=>ff.on('close',r)); await b.close(); console.log('ok',N); })();
