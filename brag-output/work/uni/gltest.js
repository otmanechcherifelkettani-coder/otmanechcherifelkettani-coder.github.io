const { chromium } = require('playwright');
(async()=>{ const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']}); const p=await b.newPage();
 const r=await p.evaluate(()=>{const c=document.createElement('canvas');const g=c.getContext('webgl2');return g?g.getParameter(g.RENDERER):'none'}); console.log(r); await b.close();})();
