// Run with node --test tests/test_builder_ui.js. No browser dependency required.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({
  document: { addEventListener() {} }, window: { addEventListener() {} },
  location: { protocol: 'http:', hostname: 'localhost' }, URL, URLSearchParams,
  st: { builderFilters: {}, csGpuMakers: [] },
  danawaBrowseByType: {},
});
for (const file of ['app_utils.js', 'product_images.js']) {
  vm.runInContext(fs.readFileSync(file, 'utf8'), context);
}

test('GPU models preserve generation and Ti/Super/XT variants', () => {
  for (const [name, expected] of [
    ['MSI RTX 3060 Ti 8GB', 'RTX 3060 Ti'],
    ['RTX 4070 Ti SUPER', 'RTX 4070 Ti Super'], ['RTX 4070 SUPER', 'RTX 4070 Super'],
    ['RTX 4080', 'RTX 4080'], ['RTX 4080 Super', 'RTX 4080 Super'],
    ['RTX 5050 8GB', 'RTX 5050'], ['AMD RX 9060 XT', 'RX 9060 XT'],
    ['RX 7900 XTX', 'RX 7900 XTX'], ['RX 6800 XT', 'RX 6800 XT'],
  ]) assert.equal(context.gpuModelToken({ name }), expected);
});

test('GPU hierarchy contains only models present in data', () => {
  const groups = context.gpuSeriesGroups([
    { name: 'RTX 3060 Ti' }, { name: 'RTX 4070 Super' },
    { name: 'RTX 5070 Ti' }, { name: 'RX 6800 XT' }, { name: 'RX 9070 XT' },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(groups)).map(g => [g.label, g.models]), [
    ['RTX 30 Series', ['RTX 3060 Ti']], ['RTX 40 Series', ['RTX 4070 Super']],
    ['RTX 50 Series', ['RTX 5070 Ti']], ['RX 6000 Series', ['RX 6800 XT']],
    ['RX 9000 Series', ['RX 9070 XT']],
  ]);
});

test('workstation RTX model numbers do not create false gaming generations', () => {
  const groups = context.gpuSeriesGroups([
    { name:'NVIDIA GeForce RTX 4070' }, { name:'NVIDIA RTX 4500 Ada' },
    { name:'NVIDIA RTX 6000 Ada' }, { name:'NVIDIA GeForce RTX 5070' },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(groups)).map(group => group.label),
    ['RTX 40 Series', 'RTX 50 Series']);
});

test('GPU model selection keeps the reference model and borrows only an exact model photo', () => {
  const retailer = { id: 'shop-4070', name: 'MSI RTX 4070 Super 12GB', price: 900000,
    image_url:'https://img.danuri.io/4070.jpg', url:'https://prod.danawa.com/info/?pcode=123' };
  const reference = { id: 'reference-4070', name: 'NVIDIA GeForce RTX 4070 Super', price: 820000 };
  assert.equal(context.preferredGpuProductForModel('RTX 4070 Super', [retailer, reference], [reference]).id,
    'reference-4070');
  assert.equal(reference.image_url, 'https://img.danuri.io/4070.jpg');
  assert.equal(context.preferredGpuProductForModel('RTX 4060', [retailer], []), null);
});

test('model filter excludes adjacent variants and manufacturers', () => {
  context.st.builderFilters.gpu = { model: ['RTX 4070 Ti Super'] };
  assert.equal(context.productMatchesFilters('gpu', { name: 'ASUS RTX 4070 Ti SUPER 16GB' }), true);
  assert.equal(context.productMatchesFilters('gpu', { name: 'ASUS RTX 4070 Ti 12GB' }), false);
});

test('all images retain product URL for recovery and use a local fallback', () => {
  const url = context.partImageUrl({ name: 'Samsung SSD', product_name: '삼성전자 SSD',
    image_url: '/api/part-image?type=storage&name=Samsung', url: 'https://prod.danawa.com/info/?pcode=123' }, 'storage');
  assert.equal(new URL(url, 'http://localhost').searchParams.get('product_url'), 'https://prod.danawa.com/info/?pcode=123');
  assert.equal(new URL(url, 'http://localhost').searchParams.get('name'), '삼성전자 SSD');
  assert.match(context.imageFallbackUrl({ image_url: 'https://blocked.test/image.jpg' }), /^data:image\/svg\+xml/);
});

test('a price lookup endpoint placeholder does not erase a real product photo', () => {
  assert.equal(context.bestProductImageUrl('https://img.danuri.io/4070.jpg', '/api/part-image?name=RTX4070'),
    'https://img.danuri.io/4070.jpg');
});
