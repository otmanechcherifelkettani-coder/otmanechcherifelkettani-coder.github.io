const { chromium } = require('playwright');
(async()=>{ const V=process.env.F==='v'; const W=V?1080:1920,H=V?1920:1080;
 const b=await chromium.launch(); const p=await b.newPage({viewport:{width:W,height:H}}); p.on('pageerror',e=>console.log('ERR',e.message)); p.on('console',m=>{ if(m.type()==='error') console.log('CON',m.text()); });
 await p.goto('http://localhost:8765/film.html'+(V?'#v':'')); await p.waitForFunction(()=>window.done===true,{timeout:60000});
 const dir='out/st'+(V?'v':'h'); require('fs').mkdirSync(dir,{recursive:true});
 for(const t of process.env.TS.split(',').map(Number)){ await p.evaluate(t=>window.render(t),t); await p.screenshot({path:`${dir}/${t.toFixed(2)}.png`}); }
 await b.close(); })();
