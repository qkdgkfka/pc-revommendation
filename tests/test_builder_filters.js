const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({
  document:{addEventListener(){}}, window:{addEventListener(){}}, URL,
  st:{builderFilters:{}, productQuery:'', productSource:'all'}, danawaBrowseByType:{},
});
if (fs.existsSync('builder_specs.js')) vm.runInContext(fs.readFileSync('builder_specs.js','utf8'),context);
vm.runInContext(fs.readFileSync('app_utils.js','utf8'), context);
context.baseCatalogFor = () => [];
context.numeric = (v,f=null) => v !== '' && v != null && Number.isFinite(Number(v)) ? Number(v) : f;
function matches(type, filters, part) {
  context.st.builderFilters[type] = filters;
  return context.productMatchesFilters(type, type === 'storage' ? {capacity:1000,...part} : part);
}
test('SSD filters combine independent read/write speed, interface, form and manufacturer', () => {
  const part={name:'삼성전자 테스트 SSD 1TB', spec_text:'M.2 (2280) / PCIe4.0x4 / 순차읽기 : 7,450MB/s / 순차쓰기 : 6,900MB/s', capacity:1000};
  assert.equal(matches('storage',{readSpeed:['7000-9999'],writeSpeed:['3000-6999'],interface:['NVMe'],formFactor:['M.2'],brand:['삼성']},part),true);
  assert.equal(matches('storage',{writeSpeed:['7000-9999']},part),false);
  assert.equal(matches('storage',{readSpeed:['1-599']},{name:'unknown',tier:'low'}),false);
  assert.equal(matches('storage',{readSpeed:['unknown']},{name:'unknown'}),true);
});
test('M.2 SATA is not mistaken for NVMe and unspecified M.2 remains unknown', () => {
  assert.equal(matches('storage',{interface:['SATA'],formFactor:['M.2']},{name:'SSD M.2 SATA 1TB'}),true);
  assert.equal(matches('storage',{interface:['NVMe']},{name:'SSD M.2 SATA 1TB'}),false);
  assert.equal(matches('storage',{interface:['NVMe']},{name:'SSD M.2 1TB'}),false);
});
test('RAM color and explicit LED absence filter without assuming unlisted LEDs are absent', () => {
  assert.equal(matches('ram',{type:['DDR4'],color:['White'],led:['yes']},{type:'ram',name:'CORSAIR DDR4 RGB WHITE (32GB)'}),true);
  assert.equal(matches('ram',{led:['no']},{name:'DDR5',spec_text:'LED : 미포함'}),true);
  assert.equal(matches('ram',{led:['yes']},{name:'DDR5',spec_text:'LED : 미포함'}),false);
  assert.equal(matches('ram',{led:['no']},{name:'DDR5'}),false);
  assert.equal(matches('ram',{color:['White']},{name:'DDR5 BLACK'}),false);
});
test('PSU certification includes Korean Silver/Titanium and does not use Cybenetics as 80 PLUS', () => {
  assert.equal(matches('psu',{rating:['Silver'],watt:['700-799']},{name:'700W 80PLUS실버 ATX3.1',watt:700}),true);
  assert.equal(matches('psu',{rating:['Titanium']},{name:'PSU',spec_text:'80 PLUS 티타늄'}),true);
  assert.equal(matches('psu',{rating:['Gold']},{name:'PSU',spec_text:'ETA인증 : GOLD / LAMBDA인증 : STANDARD'}),false);
  assert.equal(matches('psu',{modular:['Full'],atx:['3.1']},{name:'850W 풀모듈러 ATX3.1'}),true);
});
test('explicit sockets and DDR specs survive normalization for compatibility and filtering', () => {
  const [mb]=context.withPartType([{name:'인텔 보드',spec_text:'인텔(소켓1700) / DDR4',socket:'AM5',ram_type:'DDR5'}],'mb');
  assert.equal(mb.socket,'LGA1700'); assert.equal(mb.ram_type,'DDR4');
  assert.equal(matches('mb',{platform:['intel'],socket:['LGA1700'],ramType:['DDR4']},mb),true);
  assert.equal(matches('mb',{platform:['amd']},mb),false);
});
test('filter choices do not disappear when a result page has only DDR5 / AMD products', () => {
  context.rawCatalogFor = () => [{name:'AMD AM5',socket:'AM5',type:'DDR5',capacity:1000}];
  const values=(type,key)=>context.builderFilterDefs(type).find(g=>g.key===key)?.options.map(o=>o[0]) || [];
  assert.ok(values('ram','type').includes('DDR4'));
  assert.ok(values('cpu','socket').includes('LGA1700'));
  assert.ok(values('psu','rating').includes('Titanium'));
  assert.ok(values('storage','readSpeed').includes('unknown'));
});
test('SSD badges show actual listed speeds instead of a tier', () => {
  const badges=context.productBadges({name:'SSD M.2 NVMe',tier:'high',spec_text:'순차읽기: 7,000MB/s / 순차쓰기: 5,000MB/s'},'storage');
  assert.ok(badges.some(b=>b.includes('7,000')));
  assert.ok(!badges.includes('HIGH'));
});
test('spec filters search saved catalog beyond the first live page while respecting retailer', () => {
  const originalBrowse=context.browseProductsFor, originalBase=context.baseCatalogFor;
  context.browseProductsFor=()=>[{id:'live',name:'DDR5',type:'DDR5',url:'https://prod.danawa.com/info/?pcode=1'}];
  context.baseCatalogFor=()=>[{id:'saved',name:'DDR4',type:'DDR4',url:'https://prod.danawa.com/info/?pcode=2'}, {id:'other',name:'DDR4',type:'DDR4',url:'https://www.compuzone.co.kr/product/product_detail.htm?ProductNo=3'}];
  context.st.builderFilters.ram={type:['DDR4']}; context.st.productSource='danawa';
  try {
    const products=context.builderCatalogFor('ram').filter(p=>context.productMatchesFilters('ram',p));
    assert.deepEqual(Array.from(products,p=>p.id),['saved']);
  } finally {context.browseProductsFor=originalBrowse;context.baseCatalogFor=originalBase;context.st.productSource='all';}
});
test('ATX version cannot be inferred from an unrelated decimal specification', () => {
  assert.equal(matches('psu',{atx:['3.0']},{name:'ATX 파워',spec_text:'깊이 : 13.0cm'}),false);
  assert.equal(matches('psu',{atx:['3.1']},{name:'ATX 파워',atx_version:'3.1'}),true);
});
test('retailer SATA3 and PCIeGen4 labels match interface and generation filters', () => {
  assert.equal(matches('storage',{interface:['SATA']},{name:'SSD 2.5 SATA3'}),true);
  assert.equal(matches('storage',{interface:['SATA']},{name:'SSD SATA6Gb/s'}),true);
  assert.equal(matches('storage',{pcie:['4']},{name:'SSD',spec_text:'M.2 / PCIeGen4 x4'}),true);
});
test('explicit PSU rated wattage wins over stale inferred metadata', () => {
  assert.equal(matches('psu',{watt:['800-899']},{name:'darkFlash 850W',watt:1199}),true);
  assert.equal(matches('psu',{watt:['1000-1199']},{name:'darkFlash 850W',watt:1199}),false);
});
test('AMD plus socket suffix stays distinct from AM3', () => {
  assert.equal(matches('cpu',{socket:['AM3+']},{name:'AMD CPU',spec_text:'AMD(소켓AM3+)'}),true);
  assert.equal(matches('cpu',{socket:['AM3']},{name:'AMD CPU',spec_text:'AMD(소켓AM3+)'}),false);
});
