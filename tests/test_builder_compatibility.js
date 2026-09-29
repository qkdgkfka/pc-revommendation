const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function setup() {
  const ctx = vm.createContext({document:{addEventListener(){}},window:{addEventListener(){}},st:{builderFilters:{}},danawaBrowseByType:{}});
  for (const file of ['builder_specs.js','app_utils.js']) vm.runInContext(fs.readFileSync(file,'utf8'),ctx);
  return ctx;
}
test('socket compatibility normalizes structured specs independently of model names',()=>{
  const c=setup();
  assert.equal(c.socketCompatibility({name:'CPU',socket:' lga 1700 '},{name:'Board',socket:'1700'}).status,'compatible');
  assert.equal(c.socketCompatibility({name:'CPU',socket:'LGA1851'},{name:'Board',socket:'AM5'}).status,'incompatible');
  assert.equal(c.socketCompatibility({name:'AM5 marketing title',socket:'LGA1700'},{socket:'LGA1700'}).status,'compatible');
});
test('missing socket data never becomes a mismatch or false confirmation',()=>{
  const c=setup();
  for(const missing of [undefined,'','unknown','N/A','미확인','-',0]) {
    assert.equal(c.socketCompatibility({socket:missing},{socket:'AM5'}).status,'unknown');
    assert.equal(c.socketCompatibility({socket:missing},{socket:missing}).status,'unknown');
  }
  assert.equal(c.socketCompatibility(null,{socket:'AM5'}).status,'incomplete');
});
test('explicit retailer socket descriptions work without structured socket fields',()=>{
  const c=setup();
  const r=c.socketCompatibility({spec_text:'인텔(소켓1700)'},{spec_text:'LGA-1700'});
  assert.equal(r.status,'compatible'); assert.equal(r.cpuSocket,'LGA1700');
});
test('warning reports both product names and sockets and escapes retailer content',()=>{
  const c=setup();
  const html=c.compatibilityHtml({name:'Intel i5 <script>',socket:'LGA1700'},{name:'ASUS B850',socket:'AM5'});
  assert.match(html,/호환되지 않습니다/); assert.match(html,/LGA1700/); assert.match(html,/AM5/);
  assert.match(html,/Intel i5 &lt;script&gt;/); assert.match(html,/ASUS B850/); assert.ok(!html.includes('<script>'));
  assert.match(c.compatibilityHtml({name:'CPU'},{name:'Board',socket:'AM5'}),/확인 필요/);
  assert.equal(c.compatibilityHtml(null,{socket:'AM5'}),'');
});
test('changing CPU does not clear the previously selected incompatible motherboard',()=>{
  const c=setup(); const sel={innerHTML:'',value:''};
  c.document.getElementById=()=>sel;
  c.allKnownProductsFor=()=>[{id:'amd-board',name:'AMD board',socket:'AM5'},{id:'intel-board',name:'Intel board',socket:'LGA1700'}];
  c.catalogPriceLabel=p=>p.name;
  c.populateMbs({socket:'LGA1700'},null,'amd-board');
  assert.equal(sel.value,'amd-board'); assert.match(sel.innerHTML,/amd-board/); assert.match(sel.innerHTML,/intel-board/);
});
test('manual motherboard browsing includes incompatible boards for inspection and selection',()=>{
  const c=setup();
  c.builderCatalogFor=()=>[{id:'amd-board',socket:'AM5'},{id:'intel-board',socket:'LGA1700'}];
  c.selectedCustomParts=()=>({cpu:{socket:'LGA1700'}});
  assert.deepEqual(Array.from(c.rawCatalogFor('mb'),p=>p.id),['amd-board','intel-board']);
});
