
function baseUrl() {
  return (location.protocol==='file:'||location.hostname==='') ? 'http://127.0.0.1:4000' : '';
}
function money(v) {
  const n = Number(v);
  return (!v && v!==0)||isNaN(n) ? '-' : '₩'+n.toLocaleString('ko-KR');
}
function escapeHtml(v) {
  return String(v ?? '').replace(/[&<>"']/g, ch => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[ch]));
}
function shopSearchUrl(name) {
  const q = String(name || '').trim().replace(/\s+/g, ' ');
  return q ? `https://search.danawa.com/dsearch.php?query=${encodeURIComponent(q)}` : '#';
}
function queryString(params) {
  return Object.entries(params)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value ?? '')}`)
    .join('&');
}
function partUrl(part) {
  return part?.source_url || part?.url || part?.shop_url || part?.product_url || shopSearchUrl(part?.name);
}

function gpuBrand(item) {
  const value = String(item?.brand || item?.vendor || item?.name || '').toLowerCase();
  if (value.includes('nvidia') || value.includes('geforce') || value.includes('rtx') || value.includes('gtx')) return 'nvidia';
  if (value.includes('amd') || value.includes('radeon') || value.includes('rx')) return 'amd';
  return value || 'unknown';
}
function withPartType(items, type) {
  return (items || []).map(item => ({
    ...item,
    type: type === 'ram' ? (item.ram_type || (/^DDR[345]$/i.test(item.type || '') ? item.type : '')) : type,
    part_type: type,
    component_type: type,
    brand: type === 'gpu' ? gpuBrand(item) : item.brand,
  }));
}
function fullProductName(item) {
  const name = String(item?.product_name || item?.name || '-');
  const brand = String(item?.brand || '').trim();
  if (!brand || brand.toLowerCase() === 'nvidia' || brand.toLowerCase() === 'amd') return name;
  return name.toLowerCase().includes(brand.toLowerCase()) ? name : `${brand} ${name}`;
}
function productManufacturer(item) {
  const fullName = fullProductName(item);
  const makers = [
    ['GIGABYTE', /gigabyte|기가바이트/i], ['ASUS', /asus|아수스|에이수스/i],
    ['MSI', /\bmsi\b/i], ['ZOTAC', /zotac|조텍/i], ['GALAX', /galax|갤럭시/i],
    ['이엠텍', /emtek|이엠텍/i], ['PALIT', /palit|팰릿/i], ['COLORFUL', /colorful|컬러풀/i],
    ['SAPPHIRE', /sapphire|사파이어/i], ['PowerColor', /powercolor|파워컬러/i], ['XFX', /\bxfx\b/i],
    ['삼성', /samsung|삼성/i], ['SK하이닉스', /sk\s*hynix|하이닉스/i], ['마이크론', /micron|crucial|마이크론/i],
    ['WD', /western digital|\bwd\b|웨스턴디지털/i], ['Seagate', /seagate|씨게이트/i],
    ['G.SKILL', /g\.?skill|지스킬/i], ['CORSAIR', /corsair|커세어/i], ['TeamGroup', /teamgroup|팀그룹/i],
    ['마이크로닉스', /micronics|마이크로닉스/i], ['FSP', /\bfsp\b/i],
    ['Seasonic', /seasonic|시소닉/i], ['SuperFlower', /superflower|슈퍼플라워/i],
    ['ASRock', /asrock|애즈락/i], ['Intel', /intel|인텔/i], ['AMD', /\bamd\b|라이젠|ryzen/i],
  ];
  const makerText = [item.manufacturer, item.maker, fullName, item.brand].filter(Boolean).join(' ');
  const maker = makers.find(([, pattern]) => pattern.test(makerText))?.[0]
    || String(item.manufacturer || item.maker || item.brand || '').replace(/^(nvidia|amd)$/i, '');
  return { label:maker || '', pattern:makers.find(([label]) => label === maker)?.[1] };
}
function displayName(item) {
  const fullName = fullProductName(item);
  if (!item || /추가 안 함|직접 선택/.test(fullName)) return fullName;
  const manufacturer = productManufacturer(item);
  const maker = manufacturer.label;
  const gpu = fullName.match(/\b(RTX|GTX|RX)\s*[- ]?\s*(\d{4})\s*(TI\s*SUPER|TI|SUPER|XTX|XT|GRE)?/i);
  if (gpu) {
    const suffix = (gpu[3] || '').toUpperCase().replace('TI', 'Ti').replace('SUPER', 'Super');
    const vramVariant = /5060\s*ti|4060\s*ti/i.test(gpu[0]) && item.vram ? ` ${item.vram}GB` : '';
    return `${maker || (gpu[1].toUpperCase() === 'RX' ? 'AMD' : 'NVIDIA')} - ${gpu[1].toUpperCase()} ${gpu[2]}${suffix ? ` ${suffix}` : ''}${vramVariant}`;
  }
  const type = item.part_type || item.component_type || item.type || '';
  const intel = fullName.match(/(?:i[3579]\s*[- ]?\s*|코어\s*i[3579]\s*)?(\d{4,5}(?:KF|KS|K|F|T|HX|H|U)?)\b/i);
  if (/intel|인텔|core\s*i[3579]/i.test(fullName) && intel) return `Intel - ${intel[1].toUpperCase()}`;
  const ultra = fullName.match(/(?:ultra|울트라)\s*([3579])?\s*[- ]?\s*(\d{3}[A-Z]*)/i);
  if (ultra) return `Intel - Ultra ${ultra[1] ? `${ultra[1]} ` : ''}${ultra[2].toUpperCase()}`;
  const ryzen = fullName.match(/(?:ryzen|라이젠)[^\d]*(?:[3579]\s+)?(\d{4}(?:X3D|XT|X|G|F|GE)?)/i);
  if (ryzen) return `AMD - Ryzen ${ryzen[1].toUpperCase()}`;
  if ((type === 'ram' || /^DDR[345]$/i.test(type)) && item.gb) {
    const memoryType = item.ram_type || (/^DDR[345]$/i.test(item.type) ? item.type : fullName.match(/DDR[345]/i)?.[0]);
    return `${maker ? `${maker} - ` : ''}${[memoryType, `${item.gb}GB`, item.speed].filter(Boolean).join(' ')}`;
  }
  let shortName = fullName.replace(/\([^)]*\)|\[[^\]]*\]/g, '').replace(/벌크|정품|병행수입|해외구매|공식인증|당일발송|무료배송/g, '').replace(/\s+/g, ' ').trim();
  if (manufacturer.pattern) shortName = shortName.replace(manufacturer.pattern, '').trim();
  if (maker && shortName.toLowerCase().startsWith(maker.toLowerCase())) shortName = shortName.slice(maker.length).trim();
  const label = `${maker ? `${maker} - ` : ''}${shortName}`;
  return label.length > 46 ? `${label.slice(0, 43).trim()}…` : label;
}
function partLink(part) {
  const name = escapeHtml(displayName(part));
  const href = partUrl(part);
  return href === '#'
    ? name
    : `<a class="part-link" href="${escapeHtml(href)}" title="${escapeHtml(fullProductName(part))}" target="_blank" rel="noopener noreferrer">${name}</a>`;
}
function partMeta(part, type = '') {
  const items = [];
  const brand = String(part?.brand || '').trim();
  const typeText = String(part?.type || '').toUpperCase();
  if (type === 'cpu' || part?.cores || part?.threads) {
    const cpuBits = [];
    if (part?.vendor) cpuBits.push(part.vendor);
    if (part?.socket) cpuBits.push(part.socket);
    if (part?.cores) cpuBits.push(`${part.cores}코어`);
    if (part?.threads) cpuBits.push(`${part.threads}스레드`);
    if (cpuBits.length) items.push(cpuBits.join(' · '));
  }
  if (type === 'gpu' || part?.vram) {
    const gpuBits = [];
    if (part?.vendor) gpuBits.push(part.vendor);
    if (part?.vram) gpuBits.push(`VRAM ${part.vram}GB`);
    if (part?.tdp) gpuBits.push(`${part.tdp}W`);
    if (gpuBits.length) items.push(gpuBits.join(' · '));
  }
  if (brand && !['nvidia','amd'].includes(brand.toLowerCase())) items.push(brand);
  if (type === 'ram' || part?.gb || part?.speed || ['DDR4','DDR5'].includes(typeText)) {
    const ramBits = [];
    if (part?.gb) ramBits.push(`${part.gb}GB`);
    if (part?.type) ramBits.push(part.type);
    if (part?.speed) ramBits.push(`${part.speed}MHz`);
    if (ramBits.length) items.push(ramBits.join(' · '));
  }
  if (type === 'psu' || part?.watt || part?.recommendedWatt) {
    const watt = part?.watt || part?.recommendedWatt;
    if (watt) items.push(`${watt}W`);
  }
  if ((type === 'mb' || part?.socket || part?.ram_type) && (part?.socket || part?.ram_type)) {
    items.push([part?.socket, part?.ram_type].filter(Boolean).join(' · '));
  }
  if ((type === 'storage' || type === 'hdd' || part?.capacity) && part?.capacity) {
    items.push(`${part.capacity >= 1000 ? part.capacity / 1000 + 'TB' : part.capacity + 'GB'}`);
  }
  if (type === 'hdd' && part?.rpm) items.push(`${part.rpm}RPM`);
  if (type === 'case') {
    const caseBits = [part?.form_factor, part?.color].filter(Boolean);
    if (caseBits.length) items.push(caseBits.join(' · '));
  }
  if (type === 'software' && part?.license && part.license !== 'none') items.push(part.license);
  return [...new Set(items.filter(Boolean))].join(' · ');
}
function partCell(part, type = '') {
  return `<span class="part-title" title="${escapeHtml(fullProductName(part))}">${partLink(part)}</span>`;
}
function partRowHtml(label, part, type = '') {
  if (!part?.name && !part?.product_name) return '';
  const price = effectivePrice(part);
  return `
    <div class="part-row" ${previewAttrs(part, type)}>
      <span class="part-lbl">${escapeHtml(label)}</span>
      ${partThumb(part, type, 'part-thumb')}
      <span class="part-name">${partCell(part, type)}${priceProvenanceHtml(part)}</span>
      <span class="part-price">${price != null ? money(price) : '가격 미확인'}</span>
    </div>`;
}
function buyChip(label, part) {
  if (!part?.name) return '';
  if (effectivePrice(part) === 0) return '';
  return `<a class="buy-chip" href="${escapeHtml(partUrl(part))}" title="${escapeHtml(fullProductName(part))}" target="_blank" rel="noopener noreferrer"><span>${escapeHtml(label)}</span><b>${escapeHtml(displayName(part))}</b></a>`;
}
function catalogKey(name) {
  return String(name || '')
    .toLowerCase()
    .replace(/\b(nvidia|amd|intel|geforce|radeon|core|graphics|processor)\b/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}
function catalogMatchScore(a, b) {
  if (!a || !b) return 0;
  if (a === b) return 2;
  const at = new Set(a.split(/\s+/).filter(Boolean));
  const bt = new Set(b.split(/\s+/).filter(Boolean));
  const inter = [...at].filter(x => bt.has(x)).length;
  const union = new Set([...at, ...bt]).size || 1;
  let score = inter / union;
  if (a.includes(b) || b.includes(a)) score += 0.5;
  return score;
}
function mergeCatalogPrices(localItems, remoteItems) {
  const remoteList = remoteItems || [];
  const remoteByKey = new Map(remoteList.map(item => [catalogKey(item.name), item]));
  return localItems.map(item => {
    const key = catalogKey(item.name);
    let remote = remoteByKey.get(key);
    if (!remote) {
      let bestScore = 0;
      for (const candidate of remoteList) {
        const score = catalogMatchScore(key, catalogKey(candidate.name));
        if (score > bestScore) {
          bestScore = score;
          remote = candidate;
        }
      }
      if (bestScore < 0.45) remote = null;
    }
    return {
      ...item,
      price: remote?.price ?? item.price,
      shop: remote?.shop || item.shop || 'Danawa',
      url: remote?.url || item.url || shopSearchUrl(item.name),
      price_source: remote?.price_source || item.price_source || 'catalog_search',
    };
  });
}

function seedCatalogItems(items) {
  return (items || []).map(item => ({
    ...item,
    base_price: Number.isFinite(Number(item?.base_price))
      ? Number(item.base_price)
      : (Number.isFinite(Number(item?.price)) ? Number(item.price) : null),
    price: item.price_source && !['catalog_fallback','catalog_search','danawa_search'].includes(item.price_source) ? item.price : (Number(item.price) === 0 ? 0 : null),
    price_source: item.price_source || 'catalog_fallback',
    url: item.url || shopSearchUrl(item.name),
    image_url: item.image_url || '',
    shop: item.shop || 'Danawa',
    currency: item.currency || 'KRW',
  }));
}

function effectivePrice(item) {
  const live = Number(item?.price);
  if (item?.price !== null && item?.price !== undefined && Number.isFinite(live) && live >= 0) return live;
  const base = Number(item?.base_price);
  if (item?.base_price !== null && item?.base_price !== undefined && Number.isFinite(base) && base >= 0) return base;
  return null;
}

function marketName(source) {
  const text = String(source || '').toLowerCase();
  if (text.includes('compuzone') || text.includes('컴퓨존')) return '컴퓨존';
  if (text.includes('danawa') || text.includes('다나와')) return '다나와';
  return '다나와 + 컴퓨존';
}

function priceProvenance(item) {
  const price = effectivePrice(item);
  if (price === 0 && /none$/.test(item?.id || '')) return { status:'optional', text:'추가 안 함' };
  if (price == null) return { status:'unavailable', text:'가격 미확인 · 판매처 확인 필요' };
  const source = String(item?.price_source || '');
  const shop = marketName(item?.shop || source);
  const checked = item?.price_checked_at || item?.scraped_at || item?.checked_at;
  const date = checked ? new Date(checked) : null;
  const checkedText = date && Number.isFinite(date.getTime())
    ? date.toLocaleString('ko-KR', { month:'numeric', day:'numeric', hour:'2-digit', minute:'2-digit' }) : '';
  const status = item?.price_status === 'stale' || item?.price_stale || item?.stale ? 'stale'
    : item?.price_status === 'cached' ? 'cached'
    : item?.price_status === 'verified' && item?.price != null ? 'verified'
    : /(?:danawa|compuzone).*(?:live|browse)/.test(source) && item?.price != null && checkedText ? 'verified'
    : 'estimated';
  if (status === 'verified') return { status, text:`${shop} 확인가${checkedText ? ' · ' + checkedText : ''}` };
  if (status === 'cached') return { status, text:`${shop} 저장된 확인가${checkedText ? ' · ' + checkedText : ''}` };
  if (status === 'stale') return { status, text:`${shop} 이전 확인가${checkedText ? ' · ' + checkedText : ''} · 재확인 필요` };
  return { status, text:'참고가 · 현재 판매가 미확인' };
}

function priceProvenanceHtml(item) {
  const provenance = priceProvenance(item);
  return `<span class="price-provenance ${provenance.status}">${escapeHtml(provenance.text)}</span>`;
}

function catalogPriceLabel(item) {
  const price = effectivePrice(item);
  return `${displayName(item)} — ${price != null ? money(price) : '가격 미확인'} · ${priceProvenance(item).text}`;
}

const SELECTOR_PART_TYPES = {
  csGpu:'gpu', csCpu:'cpu', csRam:'ram', csMb:'mb', csStorage:'storage',
  csHdd:'hdd', csPsu:'psu', csCase:'case', csSoftware:'software',
};

function baseCatalogFor(type) {
  if (type === 'gpu') return GPUS_ALL;
  if (type === 'cpu') return CPUS;
  if (type === 'ram') return RAMS;
  if (type === 'mb') return MBS;
  if (type === 'storage') return STORAGES;
  if (type === 'hdd') return HDDS;
  if (type === 'psu') return PSUS;
  if (type === 'case') return CASES;
  if (type === 'software') return SOFTWARES;
  return [];
}

function uniqueProducts(items) {
  const seen = new Set();
  return (items || []).filter(item => {
    const id = String(item?.id || '');
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

function browseStateFor(type) {
  if (!danawaBrowseByType[type]) {
    danawaBrowseByType[type] = {
      items: [], page: 0, query: '', hasMore: false, loading: false,
      source: 'catalog', requestedSource:'all', status:'idle', total:null,
      sortLabel: '검색처 기본순', error: '', loaded:false, controller:null,
    };
  }
  return danawaBrowseByType[type];
}

function activeDanawaProducts(type) {
  return browseStateFor(type).items || [];
}

function browseProductsFor(type) {
  const browse = browseStateFor(type);
  const matches = browse.query === st.productQuery.trim() && browse.requestedSource === st.productSource;
  if (matches && browse.loaded && browse.status !== 'unavailable') return browse.items;
  return baseCatalogFor(type);
}

function allKnownProductsFor(type) {
  const pinned = Object.values(pinnedBrowseProducts[type] || {});
  return uniqueProducts([...activeDanawaProducts(type), ...pinned, ...baseCatalogFor(type)]);
}

function rememberBrowseProduct(type, part) {
  if (!type || !part?.id) return;
  if (!pinnedBrowseProducts[type]) pinnedBrowseProducts[type] = {};
  pinnedBrowseProducts[type][part.id] = part;
}

function findPartById(type, id) {
  const wanted = String(id || '');
  return allKnownProductsFor(type).find(item => item.id === wanted);
}

function findCatalogItemById(id) {
  return ['gpu','cpu','ram','mb','storage','hdd','psu','case','software']
    .map(type => findPartById(type, id))
    .find(Boolean);
}

function bestProductImageUrl(current, candidate) {
  const realImage = value => /^https?:\/\//i.test(value || '') && !String(value).includes('/api/part-image');
  return realImage(candidate) ? candidate : realImage(current) ? current : candidate || current || '';
}

function applyPriceResult(result) {
  if (!result) return;
  const target = findCatalogItemById(result.id);
  if (!target) return;
  if (result.price != null) target.price = Number(result.price);
  if (result.url) target.url = result.url;
  if (result.shop) target.shop = result.shop;
  if (result.currency) target.currency = result.currency;
  if (result.price_source) target.price_source = result.price_source;
  if (result.product_name) target.product_name = result.product_name;
  if (result.image_url) target.image_url = bestProductImageUrl(target.image_url, result.image_url);
  ['price_status','price_checked_at','scraped_at','source_url'].forEach(key => {
    if (result[key] != null) target[key] = result[key];
  });
  const observedAt = result.price_checked_at || result.scraped_at;
  if (observedAt) target.price_checked_at = observedAt;
  if (result.price_status === 'verified' || result.price_status === 'cached') {
    target.stale = false;
    target.price_stale = false;
  } else if (result.price_status === 'stale') {
    target.stale = true;
    target.price_stale = true;
  }
  target.lookup_name = result.name || target.lookup_name || target.name;
}

function normSpecValue(v) {
  return String(v || '').trim().toLowerCase();
}

function compatibleMbs(cpu, ram, pool = allKnownProductsFor('mb')) {
  const socket = normSpecValue(cpu?.socket);
  const ramType = normSpecValue(ram?.type || ram?.ram_type);
  const filtered = (pool || []).filter(mb => {
    const mbSocket = normSpecValue(mb.socket);
    const mbRam = normSpecValue(mb.ram_type);
    const socketOk = !socket || !mbSocket || socket === mbSocket;
    const ramOk = !ramType || !mbRam || ramType === mbRam;
    return socketOk && ramOk;
  });
  return filtered;
}

const BUILDER_PARTS = [
  { key:'cpu', label:'CPU', select:'csCpu', cart:'CPU' },
  { key:'mb', label:'메인보드', select:'csMb', cart:'MB' },
  { key:'gpu', label:'GPU', select:'csGpu', cart:'GPU' },
  { key:'ram', label:'RAM', select:'csRam', cart:'RAM' },
  { key:'storage', label:'SSD', select:'csStorage', cart:'SSD' },
  { key:'hdd', label:'HDD', select:'csHdd', cart:'HDD' },
  { key:'psu', label:'파워', select:'csPsu', cart:'PSU' },
  { key:'case', label:'케이스', select:'csCase', cart:'CASE' },
  { key:'software', label:'소프트웨어', select:'csSoftware', cart:'SW' },
];
const BUILDER_META = Object.fromEntries(BUILDER_PARTS.map(item => [item.key, item]));

function rawCatalogFor(type) {
  const browseItems = browseProductsFor(type);
  if (type === 'gpu' && filterValues('gpu', 'model').length) return uniqueProducts([...browseItems, ...allKnownProductsFor('gpu')]);
  if (type === 'gpu' || type === 'cpu' || type === 'ram') return browseItems;
  if (type === 'mb') {
    const { cpu, ram } = selectedCustomParts();
    return compatibleMbs(cpu, ram, browseItems);
  }
  if (['storage','hdd','psu','case','software'].includes(type)) return browseItems;
  return [];
}

function cpuVendor(part) {
  const text = String(part?.vendor || part?.brand || part?.name || '').toLowerCase();
  if (text.includes('amd') || text.includes('ryzen')) return 'amd';
  if (text.includes('intel') || text.includes('core') || text.includes('ultra')) return 'intel';
  return 'other';
}

function cpuCores(part) {
  const direct = numeric(part?.cores);
  if (direct != null) return direct;
  const name = String(part?.name || '').toLowerCase();
  if (name.includes('i9-13900') || name.includes('i9-14900')) return 24;
  if (name.includes('i7-14700')) return 20;
  if (name.includes('i7-13700')) return 16;
  if (name.includes('13600') || name.includes('14600') || name.includes('245k')) return 14;
  if (name.includes('13400') || name.includes('14400') || name.includes('1365u') || name.includes('1335u')) return 10;
  if (name.includes('7950')) return 16;
  if (name.includes('7900')) return 12;
  if (name.includes('7800') || name.includes('7700') || name.includes('9700') || name.includes('5700')) return 8;
  if (name.includes('5600') || name.includes('7600') || name.includes('1315u')) return 6;
  if (name.includes('i3')) return 4;
  return 0;
}

function cpuThreads(part) {
  const direct = numeric(part?.threads);
  if (direct != null) return direct;
  const cores = cpuCores(part);
  if (!cores) return 0;
  return String(part?.name || '').toLowerCase().includes('ultra') ? cores : cores * 2;
}

function gpuModelToken(part) {
  const name = String(part?.product_name || part?.name || '');
  const match = name.match(/\b(RTX|GTX|RX)\s*[- ]?\s*(\d{4})\s*(Ti\s*Super|Ti|Super|XTX|XT|GRE)?\b/i);
  if (!match) return '';
  const suffix = (match[3] || '').toUpperCase().replace(/TI\s*SUPER/, 'Ti Super').replace('TI', 'Ti').replace('SUPER', 'Super');
  return `${match[1].toUpperCase()} ${match[2]}${suffix ? ` ${suffix}` : ''}`;
}

function gpuSeriesGroups(items) {
  const groups = new Map();
  for (const item of items) {
    const model = gpuModelToken(item);
    if (!model) continue;
    const [family, number] = model.split(' ');
    // Workstation RTX 4500/6000-style numbers are not GeForce generation models.
    if (family === 'RTX' && Number(number[2]) < 5) continue;
    const vendor = family === 'RX' ? 'AMD' : 'NVIDIA';
    const generation = family === 'RX' ? `${number[0]}000` : number.slice(0, 2);
    const label = `${family} ${generation} Series`;
    if (!groups.has(label)) groups.set(label, { vendor, label, models:[] });
    if (!groups.get(label).models.includes(model)) groups.get(label).models.push(model);
  }
  return [...groups.values()].sort((a, b) => (a.vendor === b.vendor ? a.label.localeCompare(b.label, 'en', { numeric:true }) : a.vendor === 'NVIDIA' ? -1 : 1))
    .map(group => ({ ...group, models:group.models.sort((a, b) => a.localeCompare(b, 'en', { numeric:true })) }));
}

function preferredGpuProductForModel(model, available, references) {
  const matches = available.filter(part => gpuModelToken(part) === model);
  const reference = references.find(part => gpuModelToken(part) === model);
  const photo = matches.find(part => /^https?:\/\//i.test(part.image_url || ''));
  if (reference) {
    if (!/^https?:\/\//i.test(reference.image_url || '') && photo) reference.image_url = photo.image_url;
    return reference;
  }
  return photo || matches[0] || null;
}

function selectGpuModel(model) {
  if (st.builderPart !== 'gpu') return;
  st.builderFilters.gpu = { ...(st.builderFilters.gpu || {}), model:[model] };
  const selected = preferredGpuProductForModel(model, allKnownProductsFor('gpu'), baseCatalogFor('gpu'));
  if (selected) selectBuilderProduct('gpu', selected.id);
  else {
    renderBuilderFilters();
    renderProductList();
  }
}

function psuRating(part) {
  const name = String(part?.name || '').toLowerCase();
  if (name.includes('platinum')) return 'Platinum';
  if (name.includes('gold')) return 'Gold';
  if (name.includes('bronze')) return 'Bronze';
  return '';
}

function valueSet(items, mapper) {
  return [...new Set(items.map(mapper).filter(v => v !== '' && v != null))];
}

function rangeLabel(value, ranges) {
  const n = numeric(value, 0);
  const found = ranges.find(r => n >= r.min && n <= r.max);
  return found ? found.label : '';
}

function builderFilterDefs(type) {
  const items = rawCatalogFor(type);
  if (type === 'cpu') {
    return [
      { key:'vendor', label:'제조사', options:[['amd','AMD'],['intel','Intel']] },
      { key:'socket', label:'소켓', options:valueSet(items, p => p.socket).map(v => [v, v]) },
      { key:'cores', label:'코어 수', options:[['4-6','4-6코어'],['8-10','8-10코어'],['12-16','12-16코어'],['20-32','20코어 이상']] },
      { key:'threads', label:'스레드 수', options:[['8-12','8-12스레드'],['14-20','14-20스레드'],['24-32','24스레드 이상']] },
    ];
  }
  if (type === 'gpu') {
    return [
      { key:'vendor', label:'제조사', options:[['nvidia','NVIDIA'],['amd','AMD']] },
      { key:'model', label:'GPU 모델', options:valueSet(items, gpuModelToken).map(v => [v, v]) },
      { key:'vram', label:'VRAM', options:valueSet(items, p => p.vram ? `${p.vram}` : '').sort((a,b)=>Number(a)-Number(b)).map(v => [v, `${v}GB`]) },
      { key:'maker', label:'그래픽카드 브랜드', options:[['msi','MSI'],['gigabyte','Gigabyte'],['palit','Palit'],['colorful','Colorful'],['asus','ASUS'],['zotac','ZOTAC'],['galax','GALAX'],['emtek','Emtek']] },
    ];
  }
  if (type === 'mb') {
    return [
      { key:'socket', label:'소켓', options:valueSet(items, p => p.socket).map(v => [v, v]) },
      { key:'ramType', label:'메모리 규격', options:valueSet(items, p => p.ram_type).map(v => [v, v]) },
      { key:'brand', label:'브랜드', options:valueSet(items, p => p.brand).map(v => [v, v]) },
    ];
  }
  if (type === 'ram') {
    return [
      { key:'type', label:'규격', options:valueSet(items, p => p.type).map(v => [v, v]) },
      { key:'gb', label:'용량', options:valueSet(items, p => p.gb).sort((a,b)=>Number(a)-Number(b)).map(v => [String(v), `${v}GB`]) },
      { key:'speed', label:'속도', options:valueSet(items, p => p.speed).sort((a,b)=>Number(a)-Number(b)).map(v => [String(v), `${v}MHz`]) },
      { key:'brand', label:'브랜드', options:valueSet(items, p => p.brand).map(v => [v, v]) },
    ];
  }
  if (type === 'storage') {
    return [
      { key:'capacity', label:'용량', options:valueSet(items, p => p.capacity || storageTbValue(p) * 1000).sort((a,b)=>Number(a)-Number(b)).map(v => [String(v), Number(v) >= 1000 ? `${Number(v)/1000}TB` : `${v}GB`]) },
      { key:'tier', label:'등급', options:valueSet(items, p => p.tier).map(v => [v, v.toUpperCase()]) },
    ];
  }
  if (type === 'hdd') {
    return [
      { key:'capacity', label:'용량', options:valueSet(items, p => p.capacity).sort((a,b)=>Number(a)-Number(b)).map(v => [String(v), Number(v) >= 1000 ? `${Number(v)/1000}TB` : `${v}GB`]) },
      { key:'rpm', label:'회전수', options:valueSet(items, p => p.rpm).sort((a,b)=>Number(a)-Number(b)).map(v => [String(v), v ? `${v}RPM` : '추가 안 함']) },
      { key:'brand', label:'브랜드', options:valueSet(items, p => p.brand).map(v => [v, v]) },
    ];
  }
  if (type === 'psu') {
    return [
      { key:'watt', label:'용량', options:[['0-699','650W급'],['700-849','750W급'],['850-999','850W급'],['1000-2000','1000W 이상']] },
      { key:'rating', label:'인증', options:valueSet(items, psuRating).map(v => [v, v]) },
      { key:'brand', label:'브랜드', options:valueSet(items, p => p.brand).map(v => [v, v]) },
    ];
  }
  if (type === 'case') {
    return [
      { key:'formFactor', label:'규격', options:valueSet(items, p => p.form_factor).map(v => [v, v]) },
      { key:'brand', label:'브랜드', options:valueSet(items, p => p.brand).map(v => [v, v]) },
      { key:'color', label:'색상', options:valueSet(items, p => p.color).map(v => [v, v]) },
    ];
  }
  if (type === 'software') {
    return [
      { key:'brand', label:'제조사', options:valueSet(items, p => p.brand).map(v => [v, v]) },
      { key:'license', label:'라이선스', options:valueSet(items, p => p.license).map(v => [v, v === 'none' ? '추가 안 함' : v]) },
    ];
  }
  return [];
}

function filterValues(type, key) {
  return ((st.builderFilters[type] || {})[key] || []);
}

function filterHas(type, key, value) {
  return filterValues(type, key).includes(String(value));
}

function toggleBuilderFilter(type, key, value) {
  const current = new Set(filterValues(type, key));
  const str = String(value);
  if (current.has(str)) current.delete(str);
  else current.add(str);
  st.builderFilters[type] = { ...(st.builderFilters[type] || {}), [key]: [...current] };
  if (type === 'gpu' && key === 'maker') st.csGpuMakers = [...current];
  renderBuilderFilters();
  renderProductList();
}

function productMatchesFilters(type, part) {
  const f = st.builderFilters[type] || {};
  const has = key => Array.isArray(f[key]) && f[key].length > 0;
  const includes = (key, value) => !has(key) || f[key].includes(String(value));
  if (type === 'cpu') {
    if (!includes('vendor', cpuVendor(part))) return false;
    if (!includes('socket', part.socket)) return false;
    if (has('cores') && !f.cores.includes(rangeLabel(cpuCores(part), [
      {label:'4-6', min:4, max:6}, {label:'8-10', min:8, max:10}, {label:'12-16', min:12, max:16}, {label:'20-32', min:20, max:64},
    ]))) return false;
    if (has('threads') && !f.threads.includes(rangeLabel(cpuThreads(part), [
      {label:'8-12', min:8, max:12}, {label:'14-20', min:14, max:20}, {label:'24-32', min:24, max:64},
    ]))) return false;
  }
  if (type === 'gpu') {
    if (!includes('vendor', gpuBrand(part))) return false;
    if (!includes('model', gpuModelToken(part))) return false;
    if (!includes('vram', part.vram)) return false;
    if (has('maker')) {
      const makerNames = { msi:['msi'], gigabyte:['gigabyte','기가바이트'], palit:['palit','팰릿'], colorful:['colorful','컬러풀'], asus:['asus','아수스'], zotac:['zotac','조텍'], galax:['galax','갤럭시'], emtek:['emtek','이엠텍'] };
      const productName = String([part.name, part.product_name, part.brand, part.manufacturer].filter(Boolean).join(' ')).toLowerCase();
      if (!f.maker.some(maker => (makerNames[maker] || [maker]).some(name => productName.includes(name)))) return false;
    }
  }
  if (type === 'mb') {
    if (!includes('socket', part.socket)) return false;
    if (!includes('ramType', part.ram_type)) return false;
    if (!includes('brand', part.brand)) return false;
  }
  if (type === 'ram') {
    if (!includes('type', part.type)) return false;
    if (!includes('gb', part.gb)) return false;
    if (!includes('speed', part.speed)) return false;
    if (!includes('brand', part.brand)) return false;
  }
  if (type === 'storage') {
    const capacity = part.capacity || storageTbValue(part) * 1000;
    if (!includes('capacity', capacity)) return false;
    if (!includes('tier', part.tier)) return false;
  }
  if (type === 'hdd') {
    if (!includes('capacity', part.capacity)) return false;
    if (!includes('rpm', part.rpm)) return false;
    if (!includes('brand', part.brand)) return false;
  }
  if (type === 'psu') {
    if (has('watt') && !f.watt.includes(rangeLabel(part.watt, [
      {label:'0-699', min:0, max:699}, {label:'700-849', min:700, max:849}, {label:'850-999', min:850, max:999}, {label:'1000-2000', min:1000, max:2000},
    ]))) return false;
    if (!includes('rating', psuRating(part))) return false;
    if (!includes('brand', part.brand)) return false;
  }
  if (type === 'case') {
    if (!includes('formFactor', part.form_factor)) return false;
    if (!includes('brand', part.brand)) return false;
    if (!includes('color', part.color)) return false;
  }
  if (type === 'software') {
    if (!includes('brand', part.brand)) return false;
    if (!includes('license', part.license)) return false;
  }
  const q = normalizeSearchText(st.productQuery);
  const browse = browseStateFor(type);
  // Once the server has returned a live result page for this exact query,
  // Danawa has already performed the text search.  Re-filtering it locally
  // would incorrectly hide Korean/English model-name variants.
  const queryAlreadyApplied = q && browse.loaded && browse.status !== 'unavailable' && browse.requestedSource === st.productSource && normalizeSearchText(browse.query) === q;
  if (q && !queryAlreadyApplied) {
    const haystack = normalizeSearchText([part.name, displayName(part), partMeta(part, type), gpuModelToken(part)].join(' '));
    if (!q.split(' ').every(term => haystack.includes(term))) return false;
  }
  return true;
}

function normalizeSearchText(value) {
  return String(value || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function filteredProducts(type = st.builderPart) {
  const products = rawCatalogFor(type).filter(part => productMatchesFilters(type, part));
  if (st.productSort === 'name') products.sort((a, b) => displayName(a).localeCompare(displayName(b), 'ko'));
  if (['price_asc','price_desc'].includes(st.productSort)) {
    products.sort((a, b) => {
      const aPrice = effectivePrice(a), bPrice = effectivePrice(b);
      if (aPrice == null) return bPrice == null ? 0 : 1;
      if (bPrice == null) return -1;
      return st.productSort === 'price_asc' ? aPrice - bPrice : bPrice - aPrice;
    });
  }
  return products;
}

function selectedIdForType(type) {
  const selectId = BUILDER_META[type]?.select;
  return selectId ? document.getElementById(selectId)?.value : '';
}

function renderBuilderFilters() {
  const type = st.builderPart;
  const box = document.getElementById('builderFilters');
  if (!box) return;
  const existingGpuHost = box.querySelector('[data-gpu-selector-root]');
  if (existingGpuHost && type === 'gpu') existingGpuHost.remove();
  else if (existingGpuHost) window.GpuModelSelector?.unmount(existingGpuHost);
  box.innerHTML = builderFilterDefs(type).map(group => `
    <div class="filter-group ${type === 'gpu' && group.key === 'model' ? 'gpu-model-filter' : ''}">
      <div class="filter-label">${escapeHtml(group.label)}</div>
      <div class="filter-options">
        ${type === 'gpu' && group.key === 'model' ? '<div data-gpu-selector-root></div>' : group.options.map(([value,label]) => `
          <button type="button" class="filter-check ${filterHas(type, group.key, value) ? 'selected' : ''}" aria-pressed="${filterHas(type, group.key, value)}"
            data-filter-key="${escapeHtml(group.key)}" data-filter-value="${escapeHtml(value)}">${escapeHtml(label)}</button>
        `).join('') || '<span class="product-source">선택 가능한 옵션 없음</span>'}
      </div>
    </div>
  `).join('');
  if (type === 'gpu') {
    const placeholder = box.querySelector('[data-gpu-selector-root]');
    if (existingGpuHost) placeholder.replaceWith(existingGpuHost);
    const host = existingGpuHost || placeholder;
    const vendors = filterValues('gpu', 'vendor');
    window.GpuModelSelector?.render(host, {
      groups:gpuSeriesGroups(allKnownProductsFor('gpu'))
        .filter(group => !vendors.length || vendors.includes(group.vendor.toLowerCase())),
      selectedModel:filterValues('gpu', 'model')[0] || '',
      onSelectModel:selectGpuModel,
    });
  }
  box.querySelectorAll('.filter-check').forEach(btn => {
    btn.addEventListener('click', () => toggleBuilderFilter(type, btn.dataset.filterKey, btn.dataset.filterValue));
  });
}

function renderProductList() {
  const type = st.builderPart;
  const meta = BUILDER_META[type];
  const browse = browseStateFor(type);
  const products = filteredProducts(type);
  const selectedId = selectedIdForType(type);
  const title = document.getElementById('builderCategoryTitle');
  const listTitle = document.getElementById('productListTitle');
  const orderLabel = document.getElementById('productOrderLabel');
  const count = document.getElementById('productCount');
  const list = document.getElementById('productList');
  const footer = document.getElementById('productListFooter');
  const moreButton = document.getElementById('loadMoreProductsBtn');
  const note = document.getElementById('productBrowseNote');
  const currentResults = browse.query === st.productQuery.trim() && browse.requestedSource === st.productSource;
  const usingMarket = currentResults && browse.loaded && browse.status !== 'unavailable';
  const shop = marketName(st.productSource);
  if (title) title.textContent = meta?.label || '제품';
  if (listTitle) listTitle.textContent = usingMarket ? `${shop} 검색 결과` : '부품 카탈로그';
  if (orderLabel) {
    if (browse.loading) orderLabel.textContent = `${shop} 검색 중…`;
    else if (usingMarket) orderLabel.textContent = st.productSort === 'popular' ? (browse.sortLabel || '검색처 기본순') : '불러온 제품 기준';
    else orderLabel.textContent = '카탈로그 기준';
  }
  if (count) count.textContent = `${products.length}개 표시${usingMarket && browse.total != null ? ` / 검색 ${Number(browse.total).toLocaleString('ko-KR')}개` : ''}`;
  if (note) {
    const failures = usingMarket ? Object.entries(browse.sourceStatus || {}).filter(([, value]) => ['unavailable','error'].includes(typeof value === 'string' ? value : value?.status)).map(([key]) => marketName(key)) : [];
    note.textContent = browse.loading ? '판매처의 제품과 가격을 불러오고 있습니다.'
      : !usingMarket && browse.error ? `${browse.error} 카탈로그의 이전 확인가·참고가를 표시합니다. 가격 갱신으로 다시 시도할 수 있어요.`
      : usingMarket && browse.status === 'stale' ? '이전에 확인한 검색 결과입니다. 각 가격의 확인 시각을 확인해주세요.'
      : failures.length ? `${failures.join(', ')} 연결이 지연되어 응답한 판매처의 결과를 표시합니다.`
      : '필터와 정렬은 불러온 제품에 적용됩니다. 마우스를 올리거나 키보드로 선택하면 대표 이미지를 볼 수 있어요.';
  }
  if (footer) footer.hidden = !(usingMarket && browse.hasMore);
  if (moreButton) {
    moreButton.disabled = !!browse.loading;
    moreButton.textContent = browse.loading ? '제품 불러오는 중…' : '제품 더 보기';
  }
  if (!list) return;
  list.setAttribute('aria-busy', String(browse.loading));
  hidePartPreview();
  if (!products.length) {
    list.innerHTML = browse.loading
      ? '<div class="product-empty">판매처에서 제품을 검색하고 있습니다…</div>'
      : '<div class="product-empty">조건에 맞는 제품이 없습니다. 필터를 줄이거나 검색어를 지워보세요.</div>';
    return;
  }
  list.innerHTML = products.map(part => {
    const price = effectivePrice(part);
    const selected = part.id === selectedId;
    const badges = productBadges(part, type);
    return `
      <button type="button" class="product-card ${selected ? 'selected' : ''}" aria-pressed="${selected}" data-part-id="${escapeHtml(part.id)}" ${previewAttrs(part, type)}>
        <div class="product-card-body">
          ${partThumb(part, type, 'product-thumb')}
          <div class="product-info">
            <div class="product-top">
              <div class="product-name" title="${escapeHtml(fullProductName(part))}">${escapeHtml(displayName(part))}</div>
              <div class="product-price">${price != null ? money(price) : '가격 미확인'}</div>
            </div>
            ${badges.length ? `<div class="product-badges">${badges.map(b => `<span class="product-badge">${escapeHtml(b)}</span>`).join('')}</div>` : ''}
            <div class="product-source">${priceProvenanceHtml(part)}</div>
          </div>
        </div>
      </button>`;
  }).join('');
  list.querySelectorAll('.product-card').forEach(card => {
    card.addEventListener('click', () => selectBuilderProduct(type, card.dataset.partId));
  });
  bindPreviewTargets(list);
}

function productBadges(part, type) {
  if (type === 'cpu' || type === 'gpu') return [];
  if (type === 'ram') return [part.type, part.gb ? `${part.gb}GB` : '', part.speed ? `${part.speed}MHz` : ''].filter(Boolean);
  if (type === 'mb') return [part.socket, part.ram_type, part.brand].filter(Boolean);
  if (type === 'storage') return [part.capacity ? (part.capacity >= 1000 ? `${part.capacity/1000}TB` : `${part.capacity}GB`) : '', part.tier?.toUpperCase()].filter(Boolean);
  if (type === 'hdd') return [part.capacity ? `${part.capacity/1000}TB` : '추가 안 함', part.rpm ? `${part.rpm}RPM` : '', part.brand].filter(Boolean);
  if (type === 'psu') return [part.watt ? `${part.watt}W` : '', psuRating(part), part.brand].filter(Boolean);
  if (type === 'case') return [part.form_factor, part.color, part.brand].filter(Boolean);
  if (type === 'software') return [part.license === 'none' ? '추가 안 함' : part.license, part.brand].filter(Boolean);
  return [];
}

function selectBuilderProduct(type, id) {
  const selectId = BUILDER_META[type]?.select;
  const sel = selectId ? document.getElementById(selectId) : null;
  if (!sel) return;
  const part = rawCatalogFor(type).find(item => item.id === id) || findPartById(type, id);
  if (part) rememberBrowseProduct(type, part);
  if (!Array.from(sel.options).some(option => option.value === id) && part) {
    sel.add(new Option(catalogPriceLabel(part), part.id));
  }
  sel.value = id;
  if (type === 'cpu' || type === 'ram') {
    const { cpu, ram, mb } = selectedCustomParts();
    populateMbs(cpu, ram, mb?.id);
  }
  updateCustomChart();
  renderBuilderFilters();
  renderProductList();
  refreshSelectedPrices();
}

function setBuilderPart(type) {
  clearTimeout(productSearchTimer);
  invalidateProductRequest(st.builderPart);
  st.builderPart = BUILDER_META[type] ? type : 'cpu';
  document.querySelectorAll('#builderTabs .builder-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.part === st.builderPart);
    btn.setAttribute('aria-pressed', String(btn.dataset.part === st.builderPart));
  });
  renderBuilderFilters();
  renderProductList();
  void refreshProductBrowserPrices();
}

function clearBuilderProduct(type) {
  const select = document.getElementById(BUILDER_META[type]?.select);
  if (!select) return;
  select.value = '';
  if (type === 'cpu' || type === 'ram') {
    const { cpu, ram, mb } = selectedCustomParts();
    populateMbs(cpu, ram, mb?.id);
  }
  updateCustomChart();
  renderBuilderFilters();
  renderProductList();
  void refreshSelectedPrices();
}

function renderBuildCart() {
  const box = document.getElementById('buildCart');
  if (!box) return;
  const parts = selectedCustomParts();
  box.innerHTML = BUILDER_PARTS.map(meta => {
    const part = parts[meta.key];
    const price = part ? effectivePrice(part) : null;
    const active = st.builderPart === meta.key;
    const manufacturer = part ? productManufacturer(part).label || part.vendor || part.brand || '제조사 정보 없음' : '';
    const specs = part ? partMeta(part, meta.key) || part.spec_text || '상세 사양 정보 없음' : '';
    return `
      <div class="cart-item ${part ? 'has-selection' : ''}">
        <button type="button" class="cart-row ${active ? 'active' : ''}" data-cart-part="${meta.key}" ${previewAttrs(part, meta.key)}>
          <span class="cart-label">${meta.cart}</span>
          ${partThumb(part, meta.key, 'cart-thumb')}
          <span class="cart-main">
            ${part ? `<span class="cart-maker">${escapeHtml(manufacturer)}</span>` : ''}
            <span class="cart-name">${escapeHtml(part ? fullProductName(part) : '선택 필요')}</span>
            ${part ? `<span class="cart-meta">${escapeHtml(specs)}</span>${priceProvenanceHtml(part)}` : ''}
          </span>
          <span class="cart-price">${price != null ? money(price) : '-'}</span>
        </button>
        ${part ? `<button type="button" class="cart-remove" data-remove-part="${meta.key}" aria-label="${meta.label} 선택 해제">선택 해제</button>` : ''}
      </div>`;
  }).join('');
  box.querySelectorAll('[data-cart-part]').forEach(row => {
    row.addEventListener('click', () => setBuilderPart(row.dataset.cartPart));
  });
  box.querySelectorAll('[data-remove-part]').forEach(button => {
    button.addEventListener('click', () => clearBuilderProduct(button.dataset.removePart));
  });
  bindPreviewTargets(box);
}

function invalidateProductRequest(type) {
  const browse = browseStateFor(type);
  browse.requestId = ++danawaBrowseRequestToken;
  browse.controller?.abort();
  browse.controller = null;
  browse.loading = false;
}

async function loadDanawaProducts(type = st.builderPart, options = {}) {
  if (!BUILDER_META[type]) return;
  const browse = browseStateFor(type);
  const query = String(options.query ?? st.productQuery ?? '').trim();
  const source = options.source || st.productSource;
  const append = Boolean(options.append && browse.loaded && browse.query === query && browse.requestedSource === source);
  if (append && (browse.loading || !browse.hasMore)) return;
  invalidateProductRequest(type);
  const page = append ? Math.max(1, Number(browse.page || 0) + 1) : 1;
  const requestId = ++danawaBrowseRequestToken;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  browse.requestId = requestId;
  browse.controller = controller;
  browse.loading = true;
  browse.error = '';
  if (type === st.builderPart) renderProductList();
  try {
    const params = new URLSearchParams({ type, query, source, page:String(page), limit:'40' });
    if (options.force) params.set('refresh', '1');
    const response = await fetch(baseUrl() + '/api/products?' + params.toString(), { signal:controller.signal });
    const data = await response.json();
    if (!response.ok || data?.ok === false) throw new Error(data?.error || 'product browse failed');
    if (browse.requestId !== requestId) return;
    // Selected SKUs survive a new search, page replacement, or source switch.
    Object.entries(selectedCustomParts()).forEach(([key, part]) => rememberBrowseProduct(key, part));
    const items = withPartType(data.items || [], type);
    browse.items = append ? uniqueProducts([...browse.items, ...items]) : uniqueProducts(items);
    browse.page = page;
    browse.query = query;
    browse.requestedSource = source;
    browse.hasMore = Boolean(data.has_more);
    browse.total = data.total == null ? null : Number(data.total);
    browse.status = data.status || (items.length ? 'live' : 'empty');
    browse.sourceStatus = data.source_status || {};
    browse.source = source;
    browse.sortLabel = data.sort_label || '검색처 기본순';
    browse.loaded = true;
    browse.loadedAt = Date.now();
    browse.error = browse.status === 'unavailable' ? `${marketName(source)} 검색에 연결하지 못했습니다.` : '';
    syncCatalogSelectors();
    updateCustomPrice();
  } catch (error) {
    if (browse.requestId !== requestId) return;
    browse.error = `${marketName(source)} 검색에 연결하지 못했습니다.`;
    if (!append) {
      browse.items = [];
      browse.query = query;
      browse.requestedSource = source;
      browse.status = 'unavailable';
      browse.source = 'catalog';
      browse.loaded = false;
      browse.hasMore = false;
    }
  } finally {
    clearTimeout(timeout);
    if (browse.requestId === requestId) {
      browse.loading = false;
      browse.controller = null;
      if (type === st.builderPart) {
        renderBuilderFilters();
        renderProductList();
      }
    }
  }
}

function refreshProductBrowserPrices(options = {}) {
  const type = options.type || st.builderPart;
  const browse = browseStateFor(type);
  const query = String(options.query ?? st.productQuery ?? '').trim();
  const source = options.source || st.productSource;
  if (!options.force && !options.append && browse.loaded && browse.status !== 'unavailable' && browse.query === query && browse.requestedSource === source && Date.now() - browse.loadedAt < 300000) {
    return Promise.resolve();
  }
  return loadDanawaProducts(type, { ...options, query, source });
}

function populateMbs(cpu, ram, keepId = '') {
  const sel = document.getElementById('csMb');
  if (!sel) return;
  const items = compatibleMbs(cpu, ram, allKnownProductsFor('mb'));
  sel.innerHTML = '<option value="">선택 필요</option>' + items.map(it =>
    `<option value="${it.id}">${catalogPriceLabel(it)}</option>`
  ).join('');
  if (keepId && items.some(it => it.id === keepId)) sel.value = keepId;
}

function syncCatalogSelectors() {
  const activeBrand = document.querySelector('#brandFilter .brand-btn.active')?.dataset.brand || 'all';
  const selected = selectedCustomParts();
  populateGpus(activeBrand, false);
  populateDropdown('csCpu', CPUS);
  populateDropdown('csRam', RAMS);
  populateMbs(selected.cpu, selected.ram, selected.mb?.id);
  populateDropdown('csStorage', STORAGES);
  populateDropdown('csHdd', HDDS);
  populateDropdown('csPsu', PSUS);
  populateDropdown('csCase', CASES);
  populateDropdown('csSoftware', SOFTWARES);
  if (selected.gpu) document.getElementById('csGpu').value = selected.gpu.id;
  if (selected.cpu) document.getElementById('csCpu').value = selected.cpu.id;
  if (selected.ram) document.getElementById('csRam').value = selected.ram.id;
  if (selected.mb && Array.from(document.getElementById('csMb').options).some(opt => opt.value === selected.mb.id)) {
    document.getElementById('csMb').value = selected.mb.id;
  }
  if (selected.storage) document.getElementById('csStorage').value = selected.storage.id;
  if (selected.hdd) document.getElementById('csHdd').value = selected.hdd.id;
  if (selected.psu) document.getElementById('csPsu').value = selected.psu.id;
  if (selected.case) document.getElementById('csCase').value = selected.case.id;
  if (selected.software) document.getElementById('csSoftware').value = selected.software.id;
  renderBuildCart();
  renderBuilderFilters();
  renderProductList();
}

let priceLookupToken = 0;

async function lookupLivePrices(items, options = {}) {
  const payloadItems = (items || [])
    .filter(Boolean)
    .map(item => ({
      id: item.id,
      type: item.component_type || item.part_type || item.type || '',
      name: item.name,
      base_price: item.base_price ?? item.price ?? null,
    }))
    .filter(item => item.name);

  if (!payloadItems.length) return [];

  const ctrl = new AbortController();
  const timeout = setTimeout(() => ctrl.abort(), 20000);
  try {
    const r = await fetch(baseUrl() + '/api/price-lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: payloadItems, gpu_brands: options.gpu_brands || [], source:st.productSource }),
      signal: ctrl.signal
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'price lookup failed');
    return Array.isArray(data.results) ? data.results : [];
  } finally {
    clearTimeout(timeout);
  }
}

async function refreshSelectedPrices() {
  const token = ++priceLookupToken;
  const selected = selectedCustomParts();
  const liveDanawa = part => ['verified','stale','cached'].includes(priceProvenance(part).status);
  const wanted = [
    selected.gpu && !liveDanawa(selected.gpu) ? { id: selected.gpu.id, type: 'gpu', name: selected.gpu.name, base_price: selected.gpu.base_price } : null,
    selected.cpu && !liveDanawa(selected.cpu) ? { id: selected.cpu.id, type: 'cpu', name: selected.cpu.name, base_price: selected.cpu.base_price } : null,
    selected.ram && !liveDanawa(selected.ram) ? { id: selected.ram.id, type: 'ram', name: selected.ram.name, base_price: selected.ram.base_price } : null,
    selected.mb && !liveDanawa(selected.mb) ? { id: selected.mb.id, type: 'mb', name: selected.mb.name, base_price: selected.mb.base_price } : null,
    selected.storage && !liveDanawa(selected.storage) ? { id: selected.storage.id, type: 'storage', name: selected.storage.name, base_price: selected.storage.base_price } : null,
    selected.hdd && !liveDanawa(selected.hdd) && effectivePrice(selected.hdd) !== 0 ? { id: selected.hdd.id, type: 'hdd', name: selected.hdd.name, base_price: selected.hdd.base_price } : null,
    selected.psu && !liveDanawa(selected.psu) ? { id: selected.psu.id, type: 'psu', name: selected.psu.name, base_price: selected.psu.base_price } : null,
    selected.case && !liveDanawa(selected.case) ? { id: selected.case.id, type: 'case', name: selected.case.name, base_price: selected.case.base_price } : null,
    selected.software && !liveDanawa(selected.software) && effectivePrice(selected.software) !== 0 ? { id: selected.software.id, type: 'software', name: selected.software.name, base_price: selected.software.base_price } : null,
  ].filter(Boolean);

  if (!wanted.length) {
    updateCustomPrice();
    return;
  }

  try {
    const results = await lookupLivePrices(wanted, { gpu_brands: st.csGpuMakers });
    if (token !== priceLookupToken) return;
    results.forEach(applyPriceResult);
    syncCatalogSelectors();
    updateCustomPrice();
  } catch {
    if (token !== priceLookupToken) return;
    updateCustomPrice();
  }
}
function workFillClass(score) {
  return score >= 75 ? 'work-great' : score >= 55 ? 'work-good' : score >= 35 ? 'work-ok' : 'work-poor';
}
function selectSingle(nodes, target) {
  nodes.forEach(n => n.classList.remove('selected'));
  target.classList.add('selected');
}

function selectedMakerValues(containerId) {
  return Array.from(document.querySelectorAll(`#${containerId} [data-maker].selected, #${containerId} [data-maker].active`))
    .map(node => node.dataset.maker)
    .filter(Boolean);
}

function bindMakerChoices(containerId, stateKey, activeClass = 'selected') {
  document.querySelectorAll(`#${containerId} [data-maker]`).forEach(node => {
    node.addEventListener('click', () => {
      node.classList.toggle(activeClass);
      st[stateKey] = selectedMakerValues(containerId);
      if (containerId === 'csGpuMakerChoices') refreshSelectedPrices();
    });
  });
}

function setActiveView(view) {
  st.activeView = view === 'custom' ? 'custom' : 'ai';
  const isCustom = st.activeView === 'custom';
  document.getElementById('customSection').hidden = !isCustom;
  document.getElementById('recommendSection').hidden = isCustom;
  document.querySelectorAll('.view-btn').forEach(btn => {
    const active = btn.dataset.view === st.activeView;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', String(active));
  });
  if (isCustom) updateCustomChart();
}

function setCustomMode(mode) {
  const isGame = mode !== 'work';
  st.csMode = isGame ? 'game' : 'work';
  document.getElementById('csModeGame').classList.toggle('active', isGame);
  document.getElementById('csModeWork').classList.toggle('active', !isGame);
  document.getElementById('csPanelGame').style.display = isGame ? '' : 'none';
  document.getElementById('csPanelWork').style.display = isGame ? 'none' : '';
}

function setSelectValue(selectId, value) {
  const select = document.getElementById(selectId);
  if (!select || !value) return false;
  if (!Array.from(select.options).some(option => option.value === value)) return false;
  select.value = value;
  return true;
}

function importRecommendedBuild(tier) {
  const recommendation = st.lastRecommendation?.results?.[tier];
  const parts = recommendation?.parts;
  if (!recommendation || !parts?.gpu || !parts?.cpu || !parts?.ram || !parts?.mb || !parts?.storage || !parts?.psu) {
    showStatus('error', '가져올 추천 사양을 찾지 못했습니다. 다시 견적을 분석해주세요.');
    return;
  }

  // Keep the exact price/SKU returned by the recommendation until the user
  // explicitly refreshes prices in the direct-spec product browser.
  priceLookupToken += 1;
  Object.entries(parts).forEach(([type, part]) => {
    if (part?.id) {
      rememberBrowseProduct(type, withPartType([part], type)[0]);
      applyPriceResult({ ...part, type, id:part.id });
    }
  });

  document.querySelectorAll('#brandFilter .brand-btn').forEach(button => {
    button.classList.toggle('active', button.dataset.brand === 'all');
  });
  st.csGpuMakers = [];
  st.builderFilters = { ...st.builderFilters, gpu:{} };
  st.productQuery = '';
  const productSearch = document.getElementById('productSearchInput');
  if (productSearch) productSearch.value = '';
  populateGpus('all', false);
  populateDropdown('csCpu', CPUS);
  populateDropdown('csRam', RAMS);
  populateDropdown('csStorage', STORAGES);
  populateDropdown('csHdd', HDDS);
  populateDropdown('csPsu', PSUS);
  populateDropdown('csCase', CASES);
  populateDropdown('csSoftware', SOFTWARES);

  setSelectValue('csCpu', parts.cpu.id);
  setSelectValue('csRam', parts.ram.id);
  const selectedCpu = findPartById('cpu', document.getElementById('csCpu').value);
  const selectedRam = findPartById('ram', document.getElementById('csRam').value);
  populateMbs(selectedCpu, selectedRam, parts.mb.id);
  setSelectValue('csGpu', parts.gpu.id);
  setSelectValue('csMb', parts.mb.id);
  setSelectValue('csStorage', parts.storage.id);
  setSelectValue('csPsu', parts.psu.id);
  setSelectValue('csHdd', 'hdd_none');
  setSelectValue('csCase', 'case_none');
  setSelectValue('csSoftware', 'sw_none');

  const input = st.lastRecommendation?.input || {};
  st.csRes = input.resolution || st.resolution || '1080';
  st.refresh = Number(input.refresh) || st.refresh || 60;
  st.csGame = input.game || st.game || 'cyberpunk2077';
  st.csGameCategory = gameCategoryFor(st.csGame);
  st.csWork = input.work_profile || st.panelWork || 'video_4k';
  document.querySelectorAll('#csResRow .res-chip').forEach(chip => {
    chip.classList.toggle('selected', chip.dataset.res === st.csRes);
  });
  populateGameSelects();
  populateWorkSelects();
  setCustomMode(input.mode || st.panelMode);
  st.builderPart = 'gpu';
  renderBuildCart();
  renderBuilderFilters();
  renderProductList();
  setActiveView('custom');
  window.requestAnimationFrame(() => document.getElementById('customSection').scrollIntoView({ behavior:'smooth', block:'start' }));
}
