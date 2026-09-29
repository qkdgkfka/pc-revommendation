const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function setup(){
 const c=vm.createContext({document:{addEventListener(){},getElementById(){return null;}},window:{addEventListener(){}},
 URL,URLSearchParams,AbortController,setTimeout,clearTimeout,location:{protocol:'http:',hostname:'localhost'},
 st:{builderPart:'gpu',builderFilters:{},productQuery:'',productSource:'all',productSort:'popular'},danawaBrowseByType:{},danawaBrowseRequestToken:0,pinnedBrowseProducts:{}});
 for(const f of ['builder_specs.js','app_utils.js'])vm.runInContext(fs.readFileSync(f,'utf8'),c);
 for(const f of ['renderBuilderFilters','renderProductList','syncCatalogSelectors','updateCustomPrice'])c[f]=()=>{};
 c.selectedCustomParts=()=>({});return c;
}
test('structured chipset and series override marketing name',()=>{
 const c=setup(); assert.equal(c.gpuModelToken({chipset:'RTX 4070 SUPER',name:'RTX 5070 giveaway'}),'RTX 4070 Super');
 assert.equal(c.gpuSeriesToken({chipset:'RTX 4070 SUPER'}),'RTX 40');
 assert.equal(c.gpuSeriesToken({name:'RTX 4500 Ada'}),'');
 assert.equal(c.gpuModelToken({model:'unknown',name:'ASUS RTX 4070 SUPER'}),'RTX 4070 Super');
});
test('six series compose with maker filters and exact chipsets',()=>{
 const c=setup();
 for(const [series,chipset,maker] of [['RTX 50','RTX 5070 Ti','asus'],['RTX 40','RTX 4070 Super','asus'],['RTX 30','RTX 3060 Ti','asus'],['RX 9000','RX 9070 XT','sapphire'],['RX 7000','RX 7900 XTX','sapphire'],['RX 6000','RX 6800 XT','sapphire']]){
 c.st.builderFilters.gpu={series:[series],maker:[maker]};
 assert.equal(c.productMatchesFilters('gpu',{name:`${maker} ${chipset}`}),true);
 assert.equal(c.productMatchesFilters('gpu',{name:`MSI ${chipset}`}),false);
 assert.equal(c.productMatchesFilters('gpu',{name:`${maker} RTX 2080`}),false);
 c.st.builderFilters.gpu.model=[chipset];
 assert.equal(c.productMatchesFilters('gpu',{name:`${maker} ${chipset}`}),true);
 }
});
test('series button selects generation, clears chipset and requests search',()=>{
 const c=setup();let calls=0;c.refreshProductBrowserPrices=()=>{calls++;};
 c.st.builderFilters.gpu={model:['RTX 4070 Super'],maker:['asus']};
 c.selectGpuSeries('RTX 50 Series');
 assert.deepEqual(Array.from(c.st.builderFilters.gpu.series),['RTX 50']);
 assert.equal(c.st.builderFilters.gpu.model.length,0);assert.equal(c.st.builderFilters.gpu.maker[0],'asus');assert.equal(calls,1);
});
test('requests fifty, persists GPU filters and sorting, and deduplicates page two',async()=>{
 const c=setup();const urls=[];let page=0;
 c.st.builderFilters.gpu={series:['RTX 40'],model:['RTX 4070 Super'],maker:['asus']};c.st.productSort='price_asc';
 c.fetch=async url=>{urls.push(new URL(url));page++;return {ok:true,json:async()=>({ok:true,items:page===1?[{id:'one',name:'ASUS RTX 4070 Super'}]:[{id:'one',name:'ASUS RTX 4070 Super'},{id:'two',name:'ASUS RTX 4070 Super'}],has_more:true,status:'live'})};};
 c.baseUrl=()=> 'http://localhost:4001';
 await c.loadDanawaProducts('gpu');await c.loadDanawaProducts('gpu',{append:true});
 assert.equal(urls[0].searchParams.get('limit'),'50');assert.equal(urls[1].searchParams.get('page'),'2');
 for(const u of urls){assert.equal(u.searchParams.get('series'),'RTX 40');assert.equal(u.searchParams.get('model'),'RTX 4070 Super');assert.equal(u.searchParams.get('maker'),'asus');assert.equal(u.searchParams.get('sort'),'price_asc');}
 assert.equal(c.browseStateFor('gpu').items.length,2);
});
test('server facets drive non-GPU filters and every page keeps the composed query',async()=>{
 const c=setup();c.st.builderPart='mb'; c.st.productFacets={mb:[{key:'socket',label:'소켓',options:[['AM5','AM5']]}]};
 c.st.builderFilters.mb={socket:['AM5'],chipset:['B650'],memory_type:['DDR5'],form_factor:['ATX']};
 c.st.productSort='price_asc';const urls=[];
 c.baseUrl=()=> 'http://localhost:4001';
 c.fetch=async url=>{urls.push(new URL(url));return {ok:true,json:async()=>({ok:true,items:[{id:String(urls.length),name:'ASUS B650',specs:{socket:'AM5',chipset:'B650',memory_type:['DDR5'],form_factor:'ATX'}}],has_more:true,status:'live',cursor:'stable'})};};
 await c.loadDanawaProducts('mb');await c.loadDanawaProducts('mb',{append:true});
 for(const u of urls) assert.deepEqual(JSON.parse(u.searchParams.get('filters')),c.st.builderFilters.mb);
 assert.equal(urls[1].searchParams.get('cursor'),'stable');
 assert.equal(c.productMatchesFilters('mb',c.browseStateFor('mb').items[0]),true);
 assert.equal(c.productMatchesFilters('mb',{specs:{socket:'AM4'}}),false);
 assert.equal(c.expandedBuilderCatalog('mb'),false);
 const previous=c.builderSearchKey('mb');c.st.builderFilters.mb.socket=['AM4'];assert.notEqual(previous,c.builderSearchKey('mb'));
});
