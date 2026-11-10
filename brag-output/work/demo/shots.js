const { chromium } = require('playwright');
(async()=>{ const ts=process.argv.slice(2).map(Number); const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1920,height:1080}}); p.on('pageerror',e=>console.log('ERR',e.message)); p.on('console',m=>{if(m.type()==='error')console.log('CON',m.text())});
 await p.goto('http://localhost:8766/film.html'); await p.waitForFunction(()=>window.done===true,{timeout:30000});
 for(const t of ts){ await p.evaluate(t=>window.render(t),t); await p.screenshot({path:`out/s_${String(t.toFixed(2)).padStart(6,'0')}.jpg`,type:'jpeg',quality:80}); }
 await b.close(); })();
