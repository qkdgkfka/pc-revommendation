
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),os=require('os');
const output=process.env.QA_OUTPUT || path.join(os.tmpdir(),'pc-game-qa');
fs.mkdirSync(output,{recursive:true});
const base=process.env.QA_URL || 'http://127.0.0.1:4000';
(async()=>{
 const b=await chromium.launch({headless:true,...(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {})});
 const p=await b.newPage({viewport:{width:1440,height:1000}});
 const errors=[],failed=[];p.on('pageerror',e=>errors.push(e.message));
 p.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 p.on('response',r=>{if(r.status()>=400)failed.push({url:r.url(),status:r.status()});});
 await p.goto(base+'/');
 await p.waitForFunction(()=>document.querySelectorAll('#gameSelect option').length>1);
 await p.locator('#gameCategorySelect').selectOption('aaa');
 await p.locator('#gameSelect-options').locator('..').locator('.game-picker-trigger').click();
 await p.locator('#gameSelect-options [data-value="expedition33"]').click();
 await p.locator('#gpuPrefChoices [data-gpu="nvidia"]').click();
 await p.locator('#submitBtn').click();
 await p.waitForSelector('#resultsContainer .graphics-toggle',{timeout:90000});
 const result={errors,failed,checks:[],games:(await (await p.request.get(base+'/api/catalog')).json()).games.length};
 for(const width of [1440,390]){
   await p.setViewportSize({width,height:950});
   await p.locator('#viewAiBtn').click();
   const button=p.locator('#resultsContainer .graphics-toggle').first();
   if(await button.getAttribute('aria-expanded')!=='false')throw Error('not collapsed');
   if(await p.locator('#resultsContainer .graphics-panel').count())throw Error('hidden DOM still rendered');
   await button.click();await p.waitForSelector('#resultsContainer .graphics-panel');
   await button.scrollIntoViewIfNeeded();
   const aiText=await p.locator('#resultsContainer .graphics-panel').first().innerText();
   await p.screenshot({path:path.join(output,`graphics-ai-${width}.jpg`),type:'jpeg',quality:60});
   if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('AI overflow');
   await button.click();
   // Import an actual verified recommendation into the direct builder.
   await p.locator('[data-import-tier="low"]').click();
   try {await p.waitForSelector('#csGameChart .graphics-toggle',{timeout:45000});}catch(e){
 console.log('CUSTOM DEBUG',await p.locator('#csGameChart').innerText(),await p.locator('#csGameChart').isVisible(),errors,failed);
 console.log(await p.evaluate(()=>({state:st.csMode,game:st.csGame,ids:['csGpu','csCpu','csRam'].map(id=>[id,document.getElementById(id).value])})));
 await p.screenshot({path:'C:\\Users\\Public\\Documents\\ESTsoft\\CreatorTemp\\custom-failure.jpg',fullPage:true});
 throw e;}
   const custom=p.locator('#csGameChart .graphics-toggle');
   await custom.focus();await p.keyboard.press('Enter');await p.waitForSelector('#csGameChart .graphics-panel');
   await custom.scrollIntoViewIfNeeded();
   const customText=await p.locator('#csGameChart .graphics-panel').innerText();
   await p.screenshot({path:path.join(output,`graphics-custom-${width}.jpg`),type:'jpeg',quality:60});
   if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('custom overflow');
   await custom.click();
   // Changing the game must replace the old React root and its contents.
   await p.locator('#csGameCategorySelect').selectOption('fps');
   await p.locator('#csGameSelect-options').locator('..').locator('.game-picker-trigger').click();
   await p.locator('#csGameSelect-options [data-value="csgo2"]').click();
   await p.waitForFunction(()=>document.querySelector('#csGameChart .chart-context')?.textContent.includes('CS2')&&document.querySelector('#csGameChart .graphics-toggle'));
   await p.locator('#csGameChart .graphics-toggle').click();
   await p.waitForFunction(()=>document.querySelector('#csGameChart .graphics-panel')?.textContent.includes('지원이 확인된'));
   result.checks.push({width,aiText,customText,unsupported:true,overflow:false});
 }
 result.images=[];
 for(const game of (await (await p.request.get(base+'/api/catalog')).json()).games){
   const ok=await p.evaluate(id=>new Promise(resolve=>{const i=new Image();i.onload=()=>resolve(i.naturalWidth>0);i.onerror=()=>resolve(false);i.src='/assets/game-icons/'+id+'.jpg';}),game.id);
   if(!ok)throw Error('broken game image '+game.id);
   result.images.push(game.id);
 }
 fs.writeFileSync(path.join(output,'graphics-browser-report.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));await b.close();
})().catch(e=>{console.error(e);process.exit(1)});

