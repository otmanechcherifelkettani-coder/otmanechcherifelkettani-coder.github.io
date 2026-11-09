const { chromium } = require('playwright');
(async()=>{ const [,, url, out, w='1920', h='1080'] = process.argv;
 const b=await chromium.launch(); const p=await b.newPage({viewport:{width:+w,height:+h}});
 p.on('pageerror',e=>console.log('ERR',e.message)); p.on('console',m=>{ if(m.type()==='error') console.log('CON',m.text()); });
 await p.goto('http://localhost:8765/'+url); await p.waitForFunction(()=>window.done===true,{timeout:60000}); await p.screenshot({path:out}); await b.close(); })();
