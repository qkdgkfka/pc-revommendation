
// ─────────────────────────────────────────────────────────────
// Local catalog fallback. The server catalog replaces it when available.
// ─────────────────────────────────────────────────────────────


// Games are populated from the server catalog when available.
const GAME_CATEGORIES = [
  { id:'fps', label:'FPS / 경쟁' },
  { id:'openworld', label:'오픈월드' },
  { id:'aaa', label:'AAA 게임' },
  { id:'game', label:'일반 게임' },
];

let GAME_OPTIONS = [
  { id:'valorant', label:'발로란트', group:'FPS / 경쟁형', category:'fps' },
  { id:'csgo2', label:'CS2', group:'FPS / 경쟁형', category:'fps' },
  { id:'csgo', label:'CS:GO', group:'FPS / 경쟁형', category:'fps' },
  { id:'overwatch2', label:'오버워치 2', group:'FPS / 경쟁형', category:'fps' },
  { id:'apex', label:'에이펙스 레전드', group:'FPS / 경쟁형', category:'fps' },
  { id:'rainbow6', label:'레인보우 식스 시즈', group:'FPS / 경쟁형', category:'fps' },
  { id:'pubg', label:'배틀그라운드', group:'FPS / 경쟁형', category:'fps' },
  { id:'fortnite', label:'포트나이트', group:'FPS / 경쟁형', category:'fps' },
  { id:'marvel_rivals', label:'마블 라이벌즈', group:'FPS / 경쟁형', category:'fps' },
  { id:'cod_black_ops6', label:'콜 오브 듀티: 블랙 옵스 6', group:'FPS / 경쟁형', category:'fps' },
  { id:'cyberpunk2077', label:'사이버펑크 2077', group:'AAA / GOTY', category:'aaa' },
  { id:'baldurs_gate3', label:'발더스 게이트 3', group:'AAA / GOTY', category:'aaa' },
  { id:'god_of_war_ragnarok', label:'갓 오브 워 라그나로크', group:'AAA / GOTY', category:'aaa' },
  { id:'black_myth_wukong', label:'검은 신화: 오공', group:'AAA / GOTY', category:'aaa' },
  { id:'resident_evil4', label:'바이오하자드 RE:4', group:'AAA / GOTY', category:'aaa' },
  { id:'alan_wake2', label:'앨런 웨이크 2', group:'AAA / GOTY', category:'aaa' },
  { id:'witcher3', label:'더 위쳐 3', group:'오픈월드', category:'openworld' },
  { id:'elden_ring', label:'엘든 링', group:'오픈월드', category:'openworld' },
  { id:'ghost_of_tsushima', label:'고스트 오브 쓰시마', group:'오픈월드', category:'openworld' },
  { id:'red_dead_redemption2', label:'레드 데드 리뎀션 2', group:'오픈월드', category:'openworld' },
  { id:'horizon_forbidden_west', label:'호라이즌 포비든 웨스트', category:'openworld' },
  { id:'hogwarts_legacy', label:'호그와트 레거시', category:'openworld' },
  { id:'starfield', label:'스타필드', category:'openworld' },
  { id:'dragons_dogma2', label:'드래곤즈 도그마 2', group:'오픈월드', category:'openworld' },
  { id:'dying_light2', label:'다잉 라이트 2', group:'오픈월드', category:'openworld' },
  { id:'genshin_impact', label:'원신', group:'일반 게임', category:'game' },
  { id:'wuthering_waves', label:'명조: 워더링 웨이브', group:'일반 게임', category:'game' },
  { id:'zenless_zone_zero', label:'젠레스 존 제로', group:'일반 게임', category:'game' },
  { id:'lostark', label:'로스트아크', group:'일반 게임', category:'game' },
  { id:'wow', label:'WoW', group:'일반 게임', category:'game' },
  { id:'ffxiv', label:'파이널 판타지 XIV', group:'일반 게임', category:'game' },
  { id:'cities_skylines2', label:'시티즈 스카이라인 2', group:'일반 게임', category:'game' },
  { id:'msfs2024', label:'MS 플라이트 시뮬레이터 2024', group:'일반 게임', category:'game' },
  { id:'farming_sim', label:'파밍 시뮬레이터', group:'일반 게임', category:'game' },
];

let WORK_PROFILES = {
  video_1080p: { name:'FHD 영상 편집', group:'영상 편집', w:{ gpu:0.22, cpu:0.42, ram:0.22, storage:0.14 }, req:{ gpu:35, cpu:45, ramGb:16, storageTb:1 } },
  video_4k: { name:'4K 영상 편집', group:'영상 편집', w:{ gpu:0.32, cpu:0.34, ram:0.24, storage:0.10 }, req:{ gpu:58, cpu:64, ramGb:32, storageTb:2 } },
  video_8k: { name:'8K/RAW 영상 편집', group:'영상 편집', w:{ gpu:0.36, cpu:0.34, ram:0.24, storage:0.06 }, req:{ gpu:78, cpu:82, ramGb:64, storageTb:2 } },
  motion_graphics: { name:'모션그래픽/After Effects', group:'영상 편집', w:{ gpu:0.28, cpu:0.38, ram:0.28, storage:0.06 }, req:{ gpu:55, cpu:68, ramGb:32, storageTb:1 } },
  graphic_design: { name:'그래픽 디자인', group:'그래픽', w:{ gpu:0.24, cpu:0.34, ram:0.32, storage:0.10 }, req:{ gpu:35, cpu:45, ramGb:16, storageTb:1 } },
  large_canvas_design: { name:'대형 캔버스/인쇄 디자인', group:'그래픽', w:{ gpu:0.24, cpu:0.30, ram:0.38, storage:0.08 }, req:{ gpu:42, cpu:55, ramGb:32, storageTb:1 } },
  modeling_3d: { name:'3D 모델링/뷰포트', group:'3D 모델링', w:{ gpu:0.46, cpu:0.28, ram:0.18, storage:0.08 }, req:{ gpu:55, cpu:55, ramGb:32, storageTb:1 } },
  rendering_3d: { name:'3D 렌더링/GPU 렌더', group:'3D 모델링', w:{ gpu:0.58, cpu:0.22, ram:0.16, storage:0.04 }, req:{ gpu:74, cpu:62, ramGb:32, storageTb:1 } },
  cad_archviz: { name:'CAD/건축 시각화', group:'3D 모델링', w:{ gpu:0.38, cpu:0.34, ram:0.22, storage:0.06 }, req:{ gpu:55, cpu:62, ramGb:32, storageTb:1 } },
  music_prod: { name:'음악 제작/DAW', group:'음악/개발', w:{ gpu:0.04, cpu:0.58, ram:0.32, storage:0.06 }, req:{ gpu:15, cpu:60, ramGb:32, storageTb:1 } },
  coding: { name:'코딩/개발', group:'음악/개발', w:{ gpu:0.05, cpu:0.52, ram:0.34, storage:0.09 }, req:{ gpu:15, cpu:55, ramGb:32, storageTb:1 } },
  ai_dev: { name:'AI 개발/로컬 추론', group:'AI/개발', w:{ gpu:0.62, cpu:0.18, ram:0.16, storage:0.04 }, req:{ gpu:72, cpu:55, ramGb:32, storageTb:1 } },
};

const MAX_GPU_PERF = 3000, MAX_CPU_PERF = 1720, MAX_RAM_PERF = 680;
function numeric(v, fallback = null) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function parseGbFromName(name) {
  const m = String(name || '').match(/(\d+)\s*GB/i);
  return m ? Number(m[1]) : null;
}

function gpuPerfValue(gpu, res = '1080') {
  const local = numeric(gpu?.perf);
  if (local != null && local > 120) return local;
  const serverPerf = res === '2160'
    ? numeric(gpu?.perf_2160)
    : res === '1440'
      ? numeric(gpu?.perf_1440)
      : numeric(gpu?.perf_1080);
  if (serverPerf != null && serverPerf > 0) return (serverPerf / 100) * MAX_GPU_PERF;
  if (local != null && local > 0) return (local / 100) * MAX_GPU_PERF;
  return 0;
}

function cpuPerfValue(cpu) {
  const perf = numeric(cpu?.perf, 0);
  return perf <= 120 ? (perf / 100) * MAX_CPU_PERF : perf;
}

function ramGbValue(ram) {
  return numeric(ram?.gb) ?? parseGbFromName(ram?.name) ?? 16;
}

function ramPerfValue(ram) {
  const perf = numeric(ram?.perf);
  if (perf != null && perf > 0) return perf;
  const gb = ramGbValue(ram);
  const type = String(ram?.type || ram?.name || '').toUpperCase();
  const speed = numeric(ram?.speed, 0);
  let score = Math.min(MAX_RAM_PERF, (gb / 64) * MAX_RAM_PERF);
  if (type.includes('DDR5')) score *= speed >= 5600 ? 1.08 : 1.04;
  else if (speed >= 3200) score *= 1.02;
  return Math.min(MAX_RAM_PERF, score);
}

function storageTbValue(storage) {
  const cap = numeric(storage?.capacity);
  if (cap != null && cap > 0) return cap / 1000;
  const m = String(storage?.name || '').match(/(\d+(?:\.\d+)?)\s*TB/i);
  if (m) return Number(m[1]);
  const g = String(storage?.name || '').match(/(\d+)\s*GB/i);
  return g ? Number(g[1]) / 1000 : 1;
}

function componentPerformanceIndex(part, type) {
  if (!part) return 0;
  if (type === 'gpu') return Math.min(100, (gpuPerfValue(part, st.csRes || '1440') / MAX_GPU_PERF) * 100);
  if (type === 'cpu') return Math.min(100, (cpuPerfValue(part) / MAX_CPU_PERF) * 100);
  if (type === 'ram') return Math.min(100, (ramPerfValue(part) / MAX_RAM_PERF) * 100);
  if (Number.isFinite(Number(part.performance_index))) return Math.max(0, Math.min(100, Number(part.performance_index)));

  const name = String(part.name || '').toLowerCase();
  const tier = String(part.tier || '').toLowerCase();
  if (type === 'mb') {
    return Math.min(100, 46 + (String(part.ram_type || '').toLowerCase() === 'ddr5' ? 18 : 0)
      + (['am5','lga1851'].includes(String(part.socket || '').toLowerCase()) ? 16 : String(part.socket || '').toLowerCase() === 'lga1700' ? 10 : 4)
      + ({high:16,mid:9,low:3}[tier] || 0));
  }
  if (type === 'storage') {
    const capacity = Number(part.capacity || 0);
    return Math.min(100, Math.min(55, capacity / 4000 * 55) + (name.includes('gen5') ? 42 : name.includes('gen4') || name.includes('nvme') ? 30 : name.includes('sata') ? 12 : 20));
  }
  if (type === 'hdd') return Math.min(100, Math.min(78, Number(part.capacity || 0) / 12000 * 78) + (Number(part.rpm || 0) >= 7200 ? 18 : Number(part.rpm || 0) ? 10 : 0));
  if (type === 'psu') return Math.min(100, Math.min(78, Number(part.watt || part.recommendedWatt || 0) / 1200 * 78) + (name.includes('platinum') ? 22 : name.includes('gold') ? 16 : name.includes('bronze') ? 8 : 0));
  if (type === 'case') return Math.min(100, ({low:48,mid:66,high:82}[tier] || 52) + (name.includes('flow') || name.includes('mesh') || name.includes('air') ? 8 : 0));
  if (type === 'software') {
    if (String(part.license || '').toLowerCase() === 'none') return 0;
    return Math.min(100, 48 + (name.includes('pro') || name.includes('business') ? 28 : 0) + (name.includes('adobe') ? 20 : 0));
  }
  return 0;
}

function componentMetricName(part, type) {
  if (part?.performance_metric) return String(part.performance_metric);
  return {
    gpu:'QHD 래스터 지수', cpu:'CPU 처리 지수', ram:'메모리 용량·대역폭 지수',
    mb:'확장성·전원부 지수', storage:'저장공간·속도 지수', hdd:'저장공간·회전수 지수',
    psu:'출력·효율 지수', case:'냉각·확장성 지수', software:'소프트웨어 구성 지수',
  }[type] || '성능 지수';
}

function componentValueMetric(part, type) {
  const price = effectivePrice(part);
  const index = componentPerformanceIndex(part, type);
  if (!Number.isFinite(price) || price < 0) return { index, ratio:null, grade:'계산 대기', metric:componentMetricName(part, type) };
  if (price === 0) return { index, ratio:null, grade:'추가 비용 없음', metric:componentMetricName(part, type) };
  const ratio = index / Math.max(1, price / 10000);
  const ratios = rawCatalogFor(type)
    .map(item => {
      const itemPrice = effectivePrice(item);
      return itemPrice > 0 ? componentPerformanceIndex(item, type) / Math.max(1, itemPrice / 10000) : null;
    })
    .filter(value => Number.isFinite(value) && value > 0)
    .sort((a, b) => a - b);
  const median = ratios.length ? ratios[Math.floor(ratios.length / 2)] : ratio;
  const grade = ratio >= median * 1.24 ? '매우 좋음'
    : ratio >= median * 1.08 ? '좋음'
    : ratio >= median * 0.88 ? '보통'
    : '낮음';
  return { index, ratio, grade, metric:componentMetricName(part, type) };
}

function componentValueText(part, type, compact = false) {
  const metric = componentValueMetric(part, type);
  if (metric.ratio == null) return metric.grade;
  const prefix = compact ? '' : `${metric.metric} ${metric.index.toFixed(0)} · `;
  return `${prefix}1만원당 ${metric.ratio.toFixed(2)} 지수 · ${metric.grade}`;
}

// FPS values and evidence are supplied by the server benchmark engine.
function suitabilityFromScore(score) {
  const value = Number(score) || 0;
  if (value >= 85) return { label:'매우 적합', level:'excellent' };
  if (value >= 70) return { label:'적합', level:'good' };
  if (value >= 50) return { label:'보통', level:'normal' };
  if (value >= 35) return { label:'부적합', level:'poor' };
  return { label:'매우 부적합', level:'bad' };
}

function workScore(gpu, cpu, ram, storage, wtKey) {
  const wt = WORK_PROFILES[wtKey] || WORK_PROFILES.video_4k;
  const gs = Math.min(100, (gpuPerfValue(gpu, '1440') / MAX_GPU_PERF) * 100);
  const cs = Math.min(100, (cpuPerfValue(cpu) / MAX_CPU_PERF) * 100);
  const rs = Math.min(100, (ramPerfValue(ram) / MAX_RAM_PERF) * 100);
  const ss = Math.min(100, (storageTbValue(storage) / 2) * 100);
  let score = (wt.w.gpu || 0) * gs + (wt.w.cpu || 0) * cs + (wt.w.ram || 0) * rs + (wt.w.storage || 0) * ss;
  const req = wt.req || {};
  const ramGb = ramGbValue(ram);
  const storageTb = storageTbValue(storage);
  if (req.gpu && gs < req.gpu) score -= Math.min(22, (req.gpu - gs) * 0.36);
  if (req.cpu && cs < req.cpu) score -= Math.min(18, (req.cpu - cs) * 0.30);
  if (req.ramGb && ramGb < req.ramGb) score -= ramGb >= req.ramGb * 0.5 ? 8 : 16;
  if (req.storageTb && storageTb < req.storageTb) score -= 4;
  return Math.max(0, Math.min(100, Math.round(score)));
}

// ─────────────────────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────────────────────

const st = {
  activeView: 'ai',
  budget: 2000000, budgetMin: 1000000, budgetMax: 2000000, resolution: '1080', refresh: 60, gpu_pref: 'nopref', gpu_brands: [],
  game: 'cyberpunk2077',
  gameCategory: 'aaa',
  panelMode: 'game',   // 'game' | 'work'
  panelWork: 'video_4k',
  csMode: 'game',      // custom spec mode
  csRes: '1080',
  csGame: 'cyberpunk2077',
  csGameCategory: 'aaa',
  csWork: 'video_4k',
  csGpuMakers: [],
  builderPart: 'cpu',
  builderFilters: {},
  productQuery: '',
  productSource: 'all',
  productSort: 'popular',
  lastRecommendation: null,
};
let isLoading = false;
let customFpsToken = 0;
const customFpsCache = new Map();
const danawaBrowseByType = Object.create(null);
const pinnedBrowseProducts = Object.create(null);
let danawaBrowseRequestToken = 0;
let productSearchTimer = 0;

// ─────────────────────────────────────────────────────────────
// UTILITIES
// ─────────────────────────────────────────────────────────────

// Utilities are in app_utils.js
// ─────────────────────────────────────────────────────────────
// POPULATE DROPDOWNS (custom spec section)
// ─────────────────────────────────────────────────────────────


function populateGpus(brand = 'all', refreshChart = true) {
  const sel = document.getElementById('csGpu');
  const all = allKnownProductsFor('gpu');
  const pool = brand === 'nvidia'
    ? all.filter(item => gpuBrand(item) === 'nvidia')
    : brand === 'amd'
      ? all.filter(item => gpuBrand(item) === 'amd')
      : all;
  const previous = sel.value;
  sel.innerHTML = '<option value="">선택 필요</option>' + pool.map(g =>
    `<option value="${g.id}">${catalogPriceLabel(g)}</option>`
  ).join('');
  if (pool.some(item => item.id === previous)) sel.value = previous;
  if (refreshChart) updateCustomChart();
}

function populateDropdown(id, items) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const type = SELECTOR_PART_TYPES[id];
  const pool = type ? allKnownProductsFor(type) : items;
  const previous = sel.value;
  sel.innerHTML = '<option value="">선택 필요</option>' + pool.map(it =>
    `<option value="${it.id}">${catalogPriceLabel(it)}</option>`
  ).join('');
  if (pool.some(item => item.id === previous)) sel.value = previous;
}

function groupedOptionsHtml(items, labelKey = 'label') {
  const groups = new Map();
  (items || []).forEach(item => {
    const group = item.group || '기타';
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push(item);
  });
  return [...groups.entries()].map(([group, rows]) => `
    <optgroup label="${escapeHtml(group)}">
      ${rows.map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item[labelKey] || item.name || item.id)}</option>`).join('')}
    </optgroup>
  `).join('');
}

function gameCategoryFor(gameId) {
  const item = GAME_OPTIONS.find(game => game.id === gameId);
  if (item?.category && GAME_CATEGORIES.some(category => category.id === item.category)) return item.category;
  const group = String(item?.group || '').toLowerCase();
  if (group.includes('fps') || group.includes('경쟁')) return 'fps';
  if (group.includes('오픈월드') || group.includes('서브컬쳐')) return 'openworld';
  if (group.includes('aaa') || group.includes('goty')) return 'aaa';
  return 'game';
}

function gamesForCategory(category) {
  return GAME_OPTIONS.filter(game => gameCategoryFor(game.id) === category);
}

function populateGamePair(categoryId, gameId, category, game) {
  const categorySelect = document.getElementById(categoryId);
  const gameSelect = document.getElementById(gameId);
  const validCategory = GAME_CATEGORIES.some(item => item.id === category) ? category : 'aaa';
  const options = gamesForCategory(validCategory);
  const selectedGame = options.some(item => item.id === game) ? game : (options[0]?.id || GAME_OPTIONS[0]?.id || 'cyberpunk2077');
  if (categorySelect) {
    categorySelect.innerHTML = GAME_CATEGORIES
      .filter(item => gamesForCategory(item.id).length)
      .map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}</option>`).join('');
    categorySelect.value = validCategory;
  }
  if (gameSelect) {
    gameSelect.innerHTML = options.map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}</option>`).join('');
    gameSelect.value = selectedGame;
  }
  return { category:validCategory, game:selectedGame };
}

function populateGameSelects() {
  const ai = populateGamePair('gameCategorySelect', 'gameSelect', st.gameCategory || gameCategoryFor(st.game), st.game);
  st.gameCategory = ai.category;
  st.game = ai.game;
  const custom = populateGamePair('csGameCategorySelect', 'csGameSelect', st.csGameCategory || gameCategoryFor(st.csGame), st.csGame);
  st.csGameCategory = custom.category;
  st.csGame = custom.game;
}

function workProfileList() {
  return Object.entries(WORK_PROFILES).map(([id, item]) => ({ id, label:item.name, group:item.group }));
}

function populateWorkSelects() {
  const items = workProfileList();
  const html = groupedOptionsHtml(items, 'label');
  [
    ['panelWorkSelect', st.panelWork],
    ['csWorkSelect', st.csWork],
  ].forEach(([id, value]) => {
    const sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = html;
    sel.value = WORK_PROFILES[value] ? value : 'video_4k';
  });
}

function initDropdowns() {
  GPUS_NVIDIA = seedCatalogItems(GPUS_NVIDIA);
  GPUS_AMD = seedCatalogItems(GPUS_AMD);
  GPUS_ALL = [...GPUS_NVIDIA, ...GPUS_AMD];
  CPUS = seedCatalogItems(CPUS);
  RAMS = seedCatalogItems(RAMS);
  MBS = seedCatalogItems(MBS);
  STORAGES = seedCatalogItems(STORAGES);
  HDDS = seedCatalogItems(HDDS);
  PSUS = seedCatalogItems(PSUS);
  CASES = seedCatalogItems(CASES);
  SOFTWARES = seedCatalogItems(SOFTWARES);

  populateGpus('all');
  populateDropdown('csCpu', CPUS);
  populateDropdown('csRam', RAMS);
  populateMbs(selectedCustomParts().cpu, selectedCustomParts().ram);
  populateDropdown('csStorage', STORAGES);
  populateDropdown('csHdd', HDDS);
  populateDropdown('csPsu', PSUS);
  populateDropdown('csCase', CASES);
  populateDropdown('csSoftware', SOFTWARES);
  populateGameSelects();
  populateWorkSelects();
  renderBuildCart();
  renderBuilderFilters();
  renderProductList();
}

async function loadServerCatalog() {
  try {
    const r = await fetch(baseUrl()+'/api/catalog', { signal:AbortSignal.timeout(5000) });
    if (!r.ok) throw new Error('catalog unavailable');
    const d = await r.json();

    const serverGpus = withPartType(d.gpus || [], 'gpu');
    GPUS_NVIDIA = seedCatalogItems(serverGpus.filter(g => g.brand === 'nvidia'));
    GPUS_AMD = seedCatalogItems(serverGpus.filter(g => g.brand === 'amd'));
    GPUS_ALL = [...GPUS_NVIDIA, ...GPUS_AMD];
    CPUS = seedCatalogItems(withPartType(d.cpus || CPUS, 'cpu'));
    RAMS = seedCatalogItems(withPartType(d.rams || RAMS, 'ram'));
    MBS = seedCatalogItems(withPartType(d.mbs || MBS, 'mb'));
    STORAGES = seedCatalogItems(withPartType(d.storages || STORAGES, 'storage'));
    HDDS = seedCatalogItems(withPartType(d.hdds || HDDS, 'hdd'));
    PSUS = seedCatalogItems(withPartType(d.psus || PSUS, 'psu'));
    CASES = seedCatalogItems(withPartType(d.cases || CASES, 'case'));
    SOFTWARES = seedCatalogItems(withPartType(d.software || SOFTWARES, 'software'));
    if (Array.isArray(d.games) && d.games.length) {
      GAME_OPTIONS = d.games.map(g => ({
        id:g.id,
        label:g.label || g.name || g.id,
        group:g.group || '기타',
        category:g.category || gameCategoryFor(g.id),
      }));
    }
    if (Array.isArray(d.work_profiles) && d.work_profiles.length) {
      d.work_profiles.forEach(profile => {
        if (WORK_PROFILES[profile.id]) {
          WORK_PROFILES[profile.id].name = profile.label || WORK_PROFILES[profile.id].name;
          WORK_PROFILES[profile.id].group = profile.group || WORK_PROFILES[profile.id].group;
        }
      });
    }

    const activeBrand = document.querySelector('#brandFilter .brand-btn.active')?.dataset.brand || 'all';
    populateGpus(activeBrand);
    populateDropdown('csCpu', CPUS);
    populateDropdown('csRam', RAMS);
    populateMbs(selectedCustomParts().cpu, selectedCustomParts().ram);
    populateDropdown('csStorage', STORAGES);
    populateDropdown('csHdd', HDDS);
    populateDropdown('csPsu', PSUS);
    populateDropdown('csCase', CASES);
    populateDropdown('csSoftware', SOFTWARES);
    populateGameSelects();
    populateWorkSelects();
    renderBuildCart();
    renderBuilderFilters();
    renderProductList();
    await refreshSelectedPrices();
    refreshProductBrowserPrices();
  } catch {
    GPUS_NVIDIA = seedCatalogItems(GPUS_NVIDIA);
    GPUS_AMD = seedCatalogItems(GPUS_AMD);
    GPUS_ALL = [...GPUS_NVIDIA, ...GPUS_AMD];
    CPUS = seedCatalogItems(CPUS);
    RAMS = seedCatalogItems(RAMS);
    MBS = seedCatalogItems(MBS);
    STORAGES = seedCatalogItems(STORAGES);
    HDDS = seedCatalogItems(HDDS);
    PSUS = seedCatalogItems(PSUS);
    CASES = seedCatalogItems(CASES);
    SOFTWARES = seedCatalogItems(SOFTWARES);
    syncCatalogSelectors();
    populateGameSelects();
    populateWorkSelects();
    await refreshSelectedPrices();
    refreshProductBrowserPrices();
  }
}

function selectedCustomParts() {
  const gpuId = document.getElementById('csGpu').value;
  const cpuId = document.getElementById('csCpu').value;
  const ramId = document.getElementById('csRam').value;
  const mbId = document.getElementById('csMb').value;
  const strId = document.getElementById('csStorage').value;
  const hddId = document.getElementById('csHdd').value;
  const psuId = document.getElementById('csPsu').value;
  const caseId = document.getElementById('csCase').value;
  const softwareId = document.getElementById('csSoftware').value;
  return {
    gpu:     findPartById('gpu', gpuId),
    cpu:     findPartById('cpu', cpuId),
    ram:     findPartById('ram', ramId),
    mb:      findPartById('mb', mbId),
    storage: findPartById('storage', strId),
    hdd:     findPartById('hdd', hddId),
    psu:     findPartById('psu', psuId),
    case:    findPartById('case', caseId),
    software:findPartById('software', softwareId),
  };
}

function pricePerFrame(totalPrice, fps) {
  const price = Number(totalPrice), frames = Number(fps);
  return Number.isFinite(price) && price > 0 && Number.isFinite(frames) && frames > 0
    ? price / frames : null;
}

function pricePerFrameHtml(totalPrice, fps, game, resolution, missing = false) {
  const value = missing ? null : pricePerFrame(totalPrice, fps);
  const gameName = GAME_OPTIONS.find(item => item.id === game)?.label || game || '선택 게임';
  const result = value == null ? '계산 대기' : `${Math.round(value).toLocaleString('ko-KR')}원 / 프레임`;
  return `<div class="frame-value" aria-live="polite">
    <span class="frame-value-label">1프레임당 가격</span><strong>${result}</strong>
    <span class="frame-value-detail">${escapeHtml(gameName)} · ${escapeHtml(resolution)}p · 고옵</span>
    <span class="frame-value-formula">${value == null ? '전체 부품 가격과 FPS 확인 후 계산합니다.' : `${money(totalPrice)} ÷ ${Number(fps).toLocaleString('ko-KR')} FPS · 낮을수록 좋은 가성비`}</span>
  </div>`;
}

function renderCustomBuildValue(parts, totalPrice, missing) {
  const box = document.getElementById('csBuildValue');
  if (!box) return;
  if (missing || totalPrice <= 0 || !parts.gpu || !parts.cpu || !parts.ram) {
    box.textContent = '전체 부품 가격과 게임 FPS가 확인되면 1프레임당 가격을 계산합니다.';
    return;
  }
  if (st.csMode === 'game') {
    const game = document.getElementById('csGameSelect')?.value || st.csGame || 'cyberpunk2077';
    const benchmark = customFpsCache.get(customFpsKey(parts.gpu, parts.cpu, parts.ram, game, st.csRes, st.refresh));
    box.innerHTML = pricePerFrameHtml(totalPrice, benchmark?.fps_by_option?.high, game, st.csRes, missing);
    return;
  }
  const profile = document.getElementById('csWorkSelect')?.value || st.csWork;
  const workIndex = workScore(parts.gpu, parts.cpu, parts.ram, parts.storage, profile);
  const value = workIndex / Math.max(1, totalPrice / 10000);
  box.innerHTML = `<strong>작업 성능 1만원당 ${value.toFixed(2)} 지수</strong> · ${value >= 3.5 ? '좋음' : value >= 2 ? '보통' : '낮음'}<br><span>선택한 작업 프로필과 전체 부품 합계를 함께 반영</span>`;
}

function updateCustomPrice() {
  const { gpu, cpu, ram, mb, storage, hdd, psu, case:pcCase, software } = selectedCustomParts();
  const parts = [gpu, cpu, ram, mb, storage, hdd, psu, pcCase, software].filter(Boolean);
  const totalPrice = parts.reduce((sum, part) => sum + (effectivePrice(part) || 0), 0);
  const missing = parts.some(part => effectivePrice(part) == null);

  const priceEl = document.getElementById('csTotalPrice');
  priceEl.textContent = missing ? `${money(totalPrice)} + 미확인` : money(totalPrice);
  const priceNote = document.getElementById('csPriceNote');
  if (priceNote) {
    const statuses = parts.map(part => priceProvenance(part).status);
    priceNote.textContent = missing ? '가격 미확인 부품을 제외한 합계입니다.'
      : statuses.includes('estimated') ? '참고가가 포함된 예상 합계입니다. 판매처에서 현재 가격을 확인해주세요.'
      : statuses.includes('stale') ? '이전 확인가가 포함된 합계입니다. 구매 전 가격을 다시 확인해주세요.'
      : '판매처 확인가 기준 · 배송비 및 조립비 별도';
  }
  renderCustomBuildValue({ gpu, cpu, ram, mb, storage, hdd, psu, case:pcCase, software }, totalPrice, missing);

  const links = document.getElementById('csBuyLinks');
  if (links) {
    links.innerHTML = [
      buyChip('GPU', gpu),
      buyChip('CPU', cpu),
      buyChip('RAM', ram),
      buyChip('MB', mb),
      buyChip('SSD', storage),
      buyChip('HDD', hdd),
      buyChip('PSU', psu),
      buyChip('CASE', pcCase),
      buyChip('SW', software),
    ].join('');
  }
  renderBuildCart();
}

// ─────────────────────────────────────────────────────────────
// CUSTOM SPEC CHART (game fps or work suitability)
// ─────────────────────────────────────────────────────────────

function updateCustomChart() {
  updateCustomPrice();
  const { gpu, cpu, ram, storage } = selectedCustomParts();
  if (!gpu || !cpu || !ram) {
    customFpsToken += 1;
    ['csGameChart', 'csWorkChart'].forEach(id => {
      const chart = document.getElementById(id);
      chart.setAttribute('aria-busy', 'false');
      chart.innerHTML = '<div class="no-spec"><div class="no-spec-text">CPU, GPU, RAM을 선택해주세요</div></div>';
    });
    return;
  }

  if (st.csMode === 'game') {
    const game = document.getElementById('csGameSelect')?.value || st.csGame || 'cyberpunk2077';
    const key = customFpsKey(gpu, cpu, ram, game, st.csRes, st.refresh);
    const token = ++customFpsToken;
    const cached = customFpsCache.get(key);
    renderCustomGameChart(gpu, cpu, ram, cached || null, !cached);
    if (!cached) void fetchCustomBenchmark(gpu, cpu, ram, game, st.csRes, st.refresh, key, token);
  } else {
    customFpsToken += 1;
    renderCustomWorkChart(gpu, cpu, ram, storage);
  }
}

function customFpsKey(gpu, cpu, ram, game, resolution, refresh) {
  return [gpu?.id, cpu?.id, ram?.id, game, resolution, refresh].join('|');
}

function fpsSourceLabel(fps) {
  const labels = {
    measured_benchmark: '동일 구성 실측 벤치마크',
    benchmark_calibrated: '실측 벤치마크 보정 추정',
    model_estimate: '성능 모델 추정 · 실측 자료 없음',
    game_db_benchmark: '수집된 게임별 실측 벤치마크',
    tpu_reference_calibrated: '공개 실측 벤치마크 앵커 보정',
    crawled_gpu_hierarchy: '수집된 GPU 벤치마크 기반 보정',
    embedded_hierarchy: 'GPU 벤치마크 기반 보정',
  };
  return fps?.fps_source_label || labels[fps?.fps_source] || '성능 모델 추정';
}

function benchmarkOptionHtml(option, label) {
  if (!option) return '';
  const method = option.method === 'measured_benchmark' ? '동일 CPU·GPU 실측 참고'
    : option.method === 'model_estimate' ? '실측 자료 없음 · 계산 모델 추정' : '실측 자료에서 보정한 추정값';
  const average = Number(option.reference_avg_fps);
  const observed = Number.isFinite(average) && average > 0 ? ` · 원문 ${average.toLocaleString('ko-KR')} FPS` : '';
  const conditions = option.conditions || [option.reference_resolution ? `${option.reference_resolution}p` : '', option.reference_preset].filter(Boolean).join(' · ');
  const source = /^https?:\/\//i.test(option.source_url || '') ? `<a href="${escapeHtml(option.source_url)}" target="_blank" rel="noopener noreferrer">측정 원문</a>` : '';
  return `<p><strong>${label} · ${method}</strong>${conditions ? `<br>${escapeHtml(conditions)}${observed}` : ''}${source ? `<br>${source}` : ''}</p>`;
}

function fpsEvidenceHtml(fps) {
  if (!fps) return '';
  const confidence = { high:'높음', medium:'보통', low:'낮음' }[fps.confidence];
  const sourceUrl = /^https?:\/\//i.test(fps.benchmark_source_url || '') ? fps.benchmark_source_url : '';
  const source = sourceUrl ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(fps.benchmark_source_title || '벤치마크 원문')}</a>` : '';
  const range = fps.fps_range_by_option?.high;
  const rangeText = range && Number.isFinite(Number(range.min)) && Number.isFinite(Number(range.max))
    ? `고옵 예상 범위 ${Number(range.min).toLocaleString('ko-KR')}–${Number(range.max).toLocaleString('ko-KR')} FPS` : '';
  const notes = Array.isArray(fps.estimation_notes) ? fps.estimation_notes.filter(Boolean) : [];
  const reference = [fps.benchmark_reference_gpu, fps.benchmark_reference_cpu].filter(Boolean).join(' + ');
  const options = [['low', '저옵'], ['medium', '중옵'], ['high', '고옵']]
    .map(([key, label]) => benchmarkOptionHtml(fps.option_evidence?.[key], label)).join('');
  return `<div class="benchmark-evidence">
    <span class="evidence-label">${escapeHtml(fpsSourceLabel(fps))}${confidence ? ` · 신뢰도 ${confidence}` : ''}</span>
    ${rangeText ? `<span>${rangeText}</span>` : ''}
    ${source ? `<span>${source}</span>` : ''}
    ${fps.benchmark_conditions ? `<span>원문 측정 조건 · ${escapeHtml(fps.benchmark_conditions)}</span>` : ''}
    ${reference || notes.length || options ? `<details><summary>원문 수치·옵션별 추정 기준</summary>${reference ? `<p>기준 구성 · ${escapeHtml(reference)}</p>` : ''}${options}${notes.map(note => `<p>${escapeHtml(note)}</p>`).join('')}</details>` : ''}
  </div>`;
}

function bottleneckHtml(fps) {
  const estimate = fps?.bottleneck;
  if (!estimate || estimate.estimated !== true) return '';
  const labels = { cpu:'CPU', gpu:'GPU', balanced:'균형 범위' };
  const percent = Number(estimate.percent);
  const display = Number.isFinite(percent) ? `약 ${Math.min(100, Math.max(0, percent)).toFixed(1)}%` : '자료 부족';
  return `<div class="bottleneck-summary">
    <div class="build-check-heading"><strong>예상 병목 · ${labels[estimate.limiting_component] || '분석 중'}</strong><b>${display}</b></div>
    <small>선택 게임 · 해상도 · 고옵 기준 추정</small>
    <details><summary>계산 기준</summary><p>${escapeHtml(estimate.note || '게임별 벤치마크와 CPU·GPU 성능 차이로 보정한 추정치입니다.')}</p><a href="https://pc-builds.com/ko/bottleneck-calculator/" target="_blank" rel="noopener noreferrer">PC-Builds 표시 방식 참고</a></details>
  </div>`;
}

function compatibilityHtml(compatibility) {
  if (!compatibility || typeof compatibility !== 'object') return '';
  const ok = compatibility.compatible === true;
  const bios = compatibility.status === 'bios_check_required' ? ' · 출고 BIOS 확인' : '';
  return `<div class="build-compatibility ${ok ? 'compatible' : 'incompatible'}"><div class="build-check-heading"><strong>CPU · 메인보드</strong><span class="compatibility-badge">${ok ? '✓ 플랫폼 호환' : '호환 정보 부족'}${bios}</span></div></div>`;
}

function graphicsModesHtml(fps) {
  if (!Array.isArray(fps?.graphics_modes) || !fps.graphics_modes.length) return '';
  const rows = fps.graphics_modes.map(mode => {
    const value = Number(mode.avg_fps);
    const available = mode.supported && mode.avg_fps != null && Number.isFinite(value) && value > 0;
    const range = mode.range;
    const rangeText = range && Number.isFinite(Number(range.min)) && Number.isFinite(Number(range.max)) ? `예상 ${Math.round(range.min)}–${Math.round(range.max)} FPS` : '';
    const source = /^https?:\/\//i.test(mode.source_url || '') ? `<a href="${escapeHtml(mode.source_url)}" target="_blank" rel="noopener noreferrer">${mode.method === 'workload_estimate' ? '기능 지원 정보' : '측정 출처'}</a>` : '';
    const measured = ['mode_measurement', 'measured_benchmark'].includes(mode.method) ? '원문 구성 실측' : '추정';
    return `<div class="graphics-mode"><div><strong>${escapeHtml(mode.label)}</strong><b>${available ? `${value.toLocaleString('ko-KR')} FPS` : '자료 없음'}</b></div><small>${available ? `${measured}${mode.generated ? ' · 생성 프레임 포함' : ''}${rangeText ? ` · ${rangeText}` : ''}` : ''}${mode.generated && Number(mode.render_fps) > 0 ? ` · 실제 렌더 약 ${Math.round(mode.render_fps)} FPS` : ''}</small><p>${escapeHtml(mode.note || '')}${source ? ` · ${source}` : ''}</p></div>`;
  }).join('');
  return `<details class="graphics-modes"><summary>RT · DLSS/FSR · 프레임 생성 FPS 비교</summary>${rows}<small>생성 프레임은 표시를 부드럽게 하며 입력 응답성은 실제 렌더 FPS에 따라 달라집니다.</small></details>`;
}

function fpsRequestPart(part) {
  if (!part?.performance_ref_id) return part?.id || '';
  return {
    id: part.id,
    performance_ref_id: part.performance_ref_id,
    name: part.name,
    // The server only reads these fields for RAM, where the retail kit's
    // capacity/speed is relevant to the estimate.
    gb: part.gb,
    type: part.type,
    speed: part.speed,
  };
}

async function fetchCustomBenchmark(gpu, cpu, ram, game, resolution, refresh, key, token) {
  try {
    const response = await fetch(baseUrl() + '/api/estimate-fps', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gpu: fpsRequestPart(gpu),
        cpu: fpsRequestPart(cpu),
        ram: fpsRequestPart(ram),
        game,
        resolution,
        refresh,
        tier: 'mid',
      }),
      signal: AbortSignal.timeout(20000),
    });
    const data = await response.json();
    if (!response.ok || !data?.fps) throw new Error(data?.error || 'fps estimate failed');
    customFpsCache.set(key, data.fps);
    if (token !== customFpsToken || st.csMode !== 'game') return;
    const current = selectedCustomParts();
    const currentGame = document.getElementById('csGameSelect')?.value || st.csGame || 'cyberpunk2077';
    if (customFpsKey(current.gpu, current.cpu, current.ram, currentGame, st.csRes, st.refresh) !== key) return;
    renderCustomGameChart(current.gpu, current.cpu, current.ram, data.fps, false);
    updateCustomPrice();
  } catch {
    if (token !== customFpsToken || st.csMode !== 'game') return;
    renderCustomGameChart(gpu, cpu, ram, null, false);
    updateCustomPrice();
  }
}

function renderCustomGameChart(gpu, cpu, ram, benchmark = null, loading = false) {
  const gameKey = document.getElementById('csGameSelect').value;
  const res = st.csRes;
  const benchmarkFps = benchmark?.fps_by_option;
  const chart = document.getElementById('csGameChart');
  chart.setAttribute('aria-busy', String(loading));
  if (!benchmarkFps) {
    chart.innerHTML = `<div class="fps-empty ${loading ? 'is-loading' : ''}" role="status">${loading ? '<span class="spinner"></span> 선택 구성의 벤치마크를 확인하고 있습니다.' : 'FPS 정보를 불러오지 못했습니다. 아래 버튼으로 다시 확인해주세요.'}${loading ? '' : '<button type="button" class="mini-btn ghost" id="retryFpsBtn">FPS 다시 확인</button>'}</div>`;
    chart.querySelector('#retryFpsBtn')?.addEventListener('click', updateCustomChart);
    return;
  }
  const fps = {
    low: Number(benchmarkFps.low),
    medium: Number(benchmarkFps.medium),
    high: Number(benchmarkFps.high),
  };
  const low = fps.low, med = fps.medium, high = fps.high;
  const maxFps = Math.max(...[low, med, high].filter(Number.isFinite), 60);

  const rows = [
    { label:'저옵', fps:low },
    { label:'중옵', fps:med },
    { label:'고옵', fps:high },
  ];

  const html = rows.map(r => {
    if (!Number.isFinite(r.fps) || r.fps < 0) return `<div class="chart-row"><span class="chart-lbl">${r.label}</span><span class="chart-note">측정 정보 없음</span></div>`;
    const pct = Math.min(100, (r.fps/maxFps)*100);
    const cls = r.fps >= 144 ? 'fps-over' : r.fps >= 60 ? '' : 'fps-low';
    return `
      <div class="chart-row">
        <span class="chart-lbl">${r.label}</span>
        <div class="chart-bg"><div class="chart-fill fps" style="width:${pct}%"></div></div>
        <span class="chart-val ${cls}">${r.fps} fps</span>
      </div>`;
  }).join('');

  const capNote = benchmark?.frame_cap ? ` · 게임 기본 ${benchmark.frame_cap}fps 제한 반영` : '';
  chart.innerHTML = `<div class="chart-wrap">${html}<div class="chart-note">${res}p · 네이티브 예상 FPS · RT / 프레임 생성 끔${capNote}</div>${fpsEvidenceHtml(benchmark)}${bottleneckHtml(benchmark)}${graphicsModesHtml(benchmark)}</div>`;
}

function renderCustomWorkChart(gpu, cpu, ram, storage) {
  const selected = st.csWork;
  const scores = Object.entries(WORK_PROFILES).map(([key, wt]) => {
    const score = workScore(gpu, cpu, ram, storage, key);
    const fit = suitabilityFromScore(score);
    return { key, name: wt.name, score, label: fit.label, level: fit.level };
  });

  const html = scores.map(s => {
    const fill = workFillClass(s.score);
    const selected_style = s.key === selected ? 'font-weight:800;color:#0d1b3e;' : '';
    return `
      <div class="chart-row">
        <span class="chart-lbl wide" style="${selected_style}">${s.name}</span>
        <div class="chart-bg"><div class="chart-fill ${fill}" style="width:${s.score}%"></div></div>
        <span class="chart-val fit-label ${s.level}">${s.label}</span>
      </div>`;
  }).join('');

  document.getElementById('csWorkChart').innerHTML =
    `<div class="chart-wrap">${html}<div class="chart-note">* 내부 점수를 5단계 적합도로 변환한 추정치입니다</div></div>`;
}

// ─────────────────────────────────────────────────────────────
// CUSTOM SPEC EVENT LISTENERS
// ─────────────────────────────────────────────────────────────

// Brand filter
document.querySelectorAll('.view-btn').forEach(btn => {
  btn.addEventListener('click', () => setActiveView(btn.dataset.view));
});

document.querySelectorAll('#brandFilter .brand-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#brandFilter .brand-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    populateGpus(btn.dataset.brand);
    refreshSelectedPrices();
  });
});

bindMakerChoices('csGpuMakerChoices', 'csGpuMakers', 'active');

document.querySelectorAll('#builderTabs .builder-tab').forEach(btn => {
  btn.addEventListener('click', () => setBuilderPart(btn.dataset.part));
});

const productSearchInput = document.getElementById('productSearchInput');
if (productSearchInput) {
  productSearchInput.addEventListener('input', e => {
    st.productQuery = e.target.value;
    invalidateProductRequest(st.builderPart);
    renderProductList();
    clearTimeout(productSearchTimer);
    productSearchTimer = setTimeout(() => {
      void refreshProductBrowserPrices({ query: st.productQuery, force:true });
    }, 350);
  });
}

document.getElementById('productSourceSelect')?.addEventListener('change', event => {
  st.productSource = event.target.value;
  clearTimeout(productSearchTimer);
  invalidateProductRequest(st.builderPart);
  renderBuilderFilters();
  renderProductList();
  void refreshProductBrowserPrices({ force:true });
});

document.getElementById('productSortSelect')?.addEventListener('change', event => {
  st.productSort = event.target.value;
  renderProductList();
});

document.getElementById('resetProductFiltersBtn')?.addEventListener('click', () => {
  st.builderFilters[st.builderPart] = {};
  if (st.builderPart === 'gpu') st.csGpuMakers = [];
  renderBuilderFilters();
  renderProductList();
});

const refreshProductsBtn = document.getElementById('refreshProductsBtn');
if (refreshProductsBtn) {
  refreshProductsBtn.addEventListener('click', () => {
    clearTimeout(productSearchTimer);
    void refreshProductBrowserPrices({ force:true });
  });
}

const loadMoreProductsBtn = document.getElementById('loadMoreProductsBtn');
if (loadMoreProductsBtn) {
  loadMoreProductsBtn.addEventListener('click', () => {
    void refreshProductBrowserPrices({ append:true });
  });
}

const clearBuildBtn = document.getElementById('clearBuildBtn');
if (clearBuildBtn) {
  clearBuildBtn.addEventListener('click', () => {
    ['csGpu','csCpu','csRam','csMb','csStorage','csHdd','csPsu','csCase','csSoftware'].forEach(id => {
      const sel = document.getElementById(id);
      if (sel) sel.value = '';
    });
    const { cpu, ram } = selectedCustomParts();
    populateMbs(cpu, ram);
    updateCustomChart();
    renderBuilderFilters();
    renderProductList();
    refreshSelectedPrices();
    refreshProductBrowserPrices();
  });
}

// Dropdowns change
['csGpu','csCpu','csRam','csMb','csStorage','csHdd','csPsu','csCase','csSoftware'].forEach(id => {
  document.getElementById(id).addEventListener('change', () => {
    if (id === 'csCpu' || id === 'csRam') {
      const { cpu, ram, mb } = selectedCustomParts();
      populateMbs(cpu, ram, mb?.id);
    }
    updateCustomChart();
    renderBuilderFilters();
    renderProductList();
    refreshSelectedPrices();
  });
});

// Resolution chips
document.querySelectorAll('#csResRow .res-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('#csResRow .res-chip').forEach(c => c.classList.remove('selected'));
    chip.classList.add('selected');
    st.csRes = chip.dataset.res;
    updateCustomChart();
    renderProductList();
  });
});

// Game select
document.getElementById('csGameCategorySelect').addEventListener('change', e => {
  st.csGameCategory = e.target.value;
  st.csGame = gamesForCategory(st.csGameCategory)[0]?.id || 'cyberpunk2077';
  populateGameSelects();
  updateCustomChart();
});
document.getElementById('csGameSelect').addEventListener('change', e => {
  st.csGame = e.target.value;
  updateCustomChart();
});
document.getElementById('csWorkSelect').addEventListener('change', e => {
  st.csWork = e.target.value;
  updateCustomChart();
});

// Mode toggle (game/work) in custom section
document.getElementById('csModeGame').addEventListener('click', () => {
  st.csMode = 'game';
  document.getElementById('csModeGame').classList.add('active');
  document.getElementById('csModeWork').classList.remove('active');
  document.getElementById('csPanelGame').style.display = '';
  document.getElementById('csPanelWork').style.display = 'none';
  updateCustomChart();
});
document.getElementById('csModeWork').addEventListener('click', () => {
  st.csMode = 'work';
  document.getElementById('csModeWork').classList.add('active');
  document.getElementById('csModeGame').classList.remove('active');
  document.getElementById('csPanelWork').style.display = '';
  document.getElementById('csPanelGame').style.display = 'none';
  updateCustomChart();
});

// ─────────────────────────────────────────────────────────────
// PANEL INPUT BINDINGS (budget recommend section)
// ─────────────────────────────────────────────────────────────

document.querySelectorAll('#budgetChoices .choice').forEach(n =>
  n.addEventListener('click', () => {
    st.budgetMin = Number(n.dataset.budgetMin) || 0;
    st.budgetMax = Number(n.dataset.budgetMax) || Number(n.dataset.budget) || 0;
    st.budget = st.budgetMax || st.budgetMin;
    selectSingle(document.querySelectorAll('#budgetChoices .choice'), n);
  }));
document.querySelectorAll('#resChoices .choice').forEach(n =>
  n.addEventListener('click', () => { st.resolution = n.dataset.resolution; selectSingle(document.querySelectorAll('#resChoices .choice'), n); }));
document.querySelectorAll('#refreshChoices .choice').forEach(n =>
  n.addEventListener('click', () => { st.refresh = Number(n.dataset.refresh); selectSingle(document.querySelectorAll('#refreshChoices .choice'), n); }));
document.querySelectorAll('#gpuPrefChoices .choice').forEach(n =>
  n.addEventListener('click', () => { st.gpu_pref = n.dataset.gpu; selectSingle(document.querySelectorAll('#gpuPrefChoices .choice'), n); }));
bindMakerChoices('gpuMakerChoices', 'gpu_brands', 'selected');
document.getElementById('gameCategorySelect').addEventListener('change', e => {
  st.gameCategory = e.target.value;
  st.game = gamesForCategory(st.gameCategory)[0]?.id || 'cyberpunk2077';
  populateGameSelects();
});
document.getElementById('gameSelect').addEventListener('change', e => { st.game = e.target.value; });
document.getElementById('panelWorkSelect').addEventListener('change', e => { st.panelWork = e.target.value; });

// Panel mode toggle
document.getElementById('panelModeGame').addEventListener('click', () => {
  st.panelMode = 'game';
  document.getElementById('panelModeGame').classList.add('active');
  document.getElementById('panelModeWork').classList.remove('active');
  document.getElementById('panelGameSub').style.display = '';
  document.getElementById('panelWorkSub').style.display = 'none';
});
document.getElementById('panelModeWork').addEventListener('click', () => {
  st.panelMode = 'work';
  document.getElementById('panelModeWork').classList.add('active');
  document.getElementById('panelModeGame').classList.remove('active');
  document.getElementById('panelWorkSub').style.display = '';
  document.getElementById('panelGameSub').style.display = 'none';
});

// ─────────────────────────────────────────────────────────────
// SERVER HEALTH CHECK
// ─────────────────────────────────────────────────────────────

// STATUS / SKELETON helpers
// ─────────────────────────────────────────────────────────────
const statusBox = document.getElementById('statusBox');
const resultsContainer = document.getElementById('resultsContainer');
const placeholder = document.getElementById('placeholder');

function showStatus(type, msg) { statusBox.innerHTML = `<div class="status-msg ${type}">${msg}</div>`; }
function clearStatus() { statusBox.innerHTML = ''; }
function showSkeleton() {
  placeholder.style.display = 'none';
  const sk = `<div class="skel"><div class="sk s"></div><div class="sk m" style="margin-bottom:14px"></div><div class="sk f"></div><div class="sk f"></div><div class="sk m"></div></div>`;
  resultsContainer.innerHTML = `<div class="cards">${sk}${sk}${sk}</div>`;
}
function setLoading(v) {
  isLoading = v;
  resultsContainer.setAttribute('aria-busy', String(v));
  const btn = document.getElementById('submitBtn');
  if (!btn) return;
  btn.disabled = v;
  btn.innerHTML = v
    ? `<div class="spinner"></div><span id="submitBtnTxt">분석 중...</span>`
    : `<span id="submitBtnTxt">견적 분석하기</span>`;
}

// ─────────────────────────────────────────────────────────────
// RESULT RENDERING
// ─────────────────────────────────────────────────────────────

function renderResults(data) {
  const results = data.results;
  if (!results) { showStatus('error','서버 응답 형식 오류'); resultsContainer.innerHTML=''; return; }
  st.lastRecommendation = data;

  const tiers  = ['low','mid','high'];
  const labels = { low:'LOW', mid:'MID', high:'HIGH' };
  placeholder.style.display = 'none';
  const hz = st.refresh;

  const cards = tiers.map(tier => {
    const r = results[tier];
    if (!r) return `<div class="card ${tier}"><div class="tier-name">${labels[tier]}</div><p style="color:var(--muted);font-size:13px;margin-top:8px">데이터 없음</p></div>`;

    const parts   = r.parts  || {};
    const alloc   = r.allocation || {};
    const fps     = r.fps    || {};
    const ws      = r.work_scores || {};
    const gpu     = parts.gpu     || {};
    const cpu     = parts.cpu     || {};
    const ram     = parts.ram     || {};
    const mb      = parts.mb      || {};
    const stor    = parts.storage || {};
    const psu     = parts.psu     || {};
    const buildParts = Object.values(parts).filter(part => part && typeof part === 'object');
    const summedTotal = buildParts.reduce((sum, part) => sum + (effectivePrice(part) || 0), 0);
    const missingPrice = buildParts.some(part => effectivePrice(part) == null);
    const responseTotal = Number(r.totalPrice || r.total_price || r.debug?.total_price);
    const totalPrice = Number.isFinite(responseTotal) && responseTotal > 0 ? responseTotal : summedTotal;

    // ── performance section ──────────────────────
    let perfSection = '';
    if (st.panelMode === 'game') {
      const fpsByOpt = fps.fps_by_option || {};
      const frameCap = Number(fps.frame_cap || 0);
      const targetFps = Number(fps.target_fps || (frameCap ? Math.min(hz, frameCap) : hz));
      const displayTarget = frameCap ? Math.min(hz, frameCap) : hz;
      const maxFps   = Math.max(...Object.values(fpsByOpt).map(Number).filter(Number.isFinite), displayTarget*1.5, 60);
      const hzPct    = Math.min(100, (displayTarget/maxFps)*100);
      const hzCov    = Number(fps.target_coverage || fps.hz_coverage || 0);
      const vLabel   = fps.value_label || '–';
      const capacityLabel = fps.capacity_label || vLabel;
      const gameId = fps.game || st.game;
      const gameName = GAME_OPTIONS.find(game => game.id === gameId)?.label || gameId;

      const fpsRows = [
        { label:'저옵', key:'low'    },
        { label:'중옵', key:'medium' },
        { label:'고옵', key:'high'   },
      ].map(({label,key}) => {
        const val = Number(fpsByOpt[key]);
        if (fpsByOpt[key] == null || !Number.isFinite(val) || val < 0) return '';
        const pct = Math.min(100,(val/maxFps)*100);
        const cls = fpsClass(val, displayTarget);
        const badge = val>=displayTarget ? (val>=displayTarget*1.1?'✓+':'✓') : '✗';
        return `
          <div class="fb-row">
            <span class="fb-lbl">${label}</span>
            <div class="fb-bg">
              <div class="fb-fill" style="width:${pct}%"></div>
              <div class="hz-line" style="left:${hzPct}%" title="${hz}Hz 목표선"></div>
            </div>
            <span class="fb-val ${cls}">${val}fps ${badge}</span>
          </div>`;
      }).join('');

      perfSection = `
        <div class="fps-section">
          <div class="fps-hdr">
            <span class="fps-title">예상 FPS · ${st.resolution}p @ ${displayTarget}fps 목표</span>
            <span class="fps-tag">${escapeHtml(gameName)}</span>
          </div>
          <div class="fps-bars">${fpsRows || '<p class="chart-note">해당 구성의 FPS 자료를 확인하지 못했습니다.</p>'}</div>
          <div class="chart-note" style="margin-top:7px">네이티브 래스터 · RT / 프레임 생성 끔${frameCap ? ` · 게임 기본 ${frameCap}fps 제한 반영` : ''}</div>
          ${fpsEvidenceHtml(fps)}
          ${bottleneckHtml(fps)}
          ${graphicsModesHtml(fps)}
          <div class="val-row">
            <span class="val-icon">${valueIcon(capacityLabel)}</span>
            <div class="val-info">
              <div class="val-lbl">${escapeHtml(capacityLabel)}</div>
              <div class="val-sub">목표 ${targetFps.toFixed(0)}fps 대비 ${(hzCov * 100).toFixed(0)}%</div>
            </div>
            <span class="hz-pill ${hzPillClass(hzCov)}">${hzPillText(hzCov,displayTarget)}</span>
          </div>
          ${pricePerFrameHtml(totalPrice, fpsByOpt.high, st.game, st.resolution, missingPrice)}
        </div>`;
    } else {
      // Work mode
      const workScoreRows = Object.entries(WORK_PROFILES).map(([key,wt]) => {
        const entry = ws[key] || {};
        const score = typeof entry === 'number' ? entry : Number(entry.score || 0);
        const fit = typeof entry === 'object' && entry.label
          ? { label:entry.label, level:entry.level || suitabilityFromScore(score).level }
          : suitabilityFromScore(score);
        const fill  = workFillClass(score);
        const hl    = key===st.panelWork;
        return `
          <div class="wb-row">
            <span class="wb-lbl" style="${hl?'font-weight:800;color:#0d1b3e;':''}">${wt.name}</span>
            <div class="wb-bg"><div class="wb-fill ${fill}" style="width:${score}%"></div></div>
            <span class="wb-val ${fit.level}">${fit.label}</span>
          </div>`;
      }).join('');
      const selectedEntry = ws[st.panelWork] || {};
      const selectedScore = typeof selectedEntry === 'number' ? selectedEntry : Number(selectedEntry.score || 0);
      const workPerTenThousand = selectedScore / Math.max(1, totalPrice / 10000);

      perfSection = `
        <div class="work-section">
          <div class="work-hdr">작업 적합도 · ${WORK_PROFILES[st.panelWork]?.name || '선택 작업'}</div>
          ${workScoreRows}
          <div class="val-row">
            <span class="val-icon">📊</span>
            <div class="val-info">
              <div class="val-lbl">작업 가성비</div>
              <div class="val-sub">작업 성능 1만원당 ${workPerTenThousand.toFixed(2)} 지수 · ${workPerTenThousand >= 3.5 ? '좋음' : workPerTenThousand >= 2 ? '보통' : '낮음'}</div>
            </div>
          </div>
          <div class="chart-note" style="margin-top:6px">* 내부 점수를 5단계 적합도로 변환한 추정치</div>
        </div>`;
    }

    return `
      <div class="card ${tier}">
        <div class="card-hdr">
          <div class="tier-name">${labels[tier]}</div>
          <div class="tier-badge">${money(totalPrice)}</div>
        </div>
        <div class="budget-sub">부품 합계 · 목표 ${money(r.tierBudget)} &nbsp;/&nbsp; GPU ${money(alloc.gpuBudget)} · CPU ${money(alloc.cpuBudget)}</div>

        <div class="divider"></div>

        ${partRowHtml('GPU', gpu, 'gpu')}
        ${partRowHtml('CPU', cpu, 'cpu')}
        ${partRowHtml('RAM', ram, 'ram')}
        ${partRowHtml('MB', mb, 'mb')}
        ${partRowHtml('SSD', stor, 'storage')}
        ${partRowHtml('PSU', psu.name ? psu : { name: psu.recommendedWatt+'W 파워', recommendedWatt: psu.recommendedWatt }, 'psu')}
        ${compatibilityHtml(r.compatibility)}
        ${r.same_configuration ? '<p class="chart-note">추가 업그레이드 후보가 없어 앞 등급과 동일한 구성입니다.</p>' : ''}

        <div class="divider"></div>

        ${perfSection}
        <button type="button" class="tier-import-btn" data-import-tier="${tier}">직접 사양 선택</button>
      </div>`;
  }).join('');

  resultsContainer.innerHTML = `<div class="cards">${cards}</div>`;
  resultsContainer.querySelectorAll('[data-import-tier]').forEach(button => {
    button.addEventListener('click', () => importRecommendedBuild(button.dataset.importTier));
  });
  bindPreviewTargets(resultsContainer);
}

// ─────────────────────────────────────────────────────────────
// API CALL
// ─────────────────────────────────────────────────────────────

async function sendRecommend() {
  const payload = {
    budget:     st.budget,
    budget_min: st.budgetMin,
    budget_max: st.budgetMax,
    resolution: st.resolution,
    refresh:    st.refresh,
    gpu_pref:   st.gpu_pref,
    gpu_brands: st.gpu_brands,
    game:       st.panelMode==='game' ? st.game : 'cyberpunk2077',
    mode:       st.panelMode,
    work_profile: st.panelWork,
  };
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 30000);
  let res;
  try {
    res = await fetch(baseUrl()+'/api/recommend', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload), signal:ctrl.signal
    });
  } catch(fetchErr) {
    clearTimeout(t);
    throw fetchErr;
  }
  clearTimeout(t);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error('응답 파싱 실패: '+text.slice(0,120)); }
  if (!res.ok) throw new Error(data.error||('HTTP '+res.status));
  return data;
}

// ─────────────────────────────────────────────────────────────
// SUBMIT
// ─────────────────────────────────────────────────────────────

document.getElementById('submitBtn').addEventListener('click', async () => {
  if (isLoading) return;
  clearStatus(); setLoading(true); showSkeleton();
  try {
    const data = await sendRecommend();
    clearStatus();
    if (data.warning) showStatus('warn', data.warning);
    if (!data.results) { showStatus('error','서버 응답에 결과 데이터가 없습니다.'); resultsContainer.innerHTML=''; return; }
    renderResults(data);
  } catch(err) {
    let msg = err.message||'알 수 없는 오류';
    if (err.name==='AbortError') msg = '요청 시간이 초과되었습니다 (30초).';
    showStatus('error','요청 실패: '+msg);
    resultsContainer.innerHTML=''; placeholder.style.display='flex';
  } finally {
    try { setLoading(false); } catch { isLoading = false; }
  }
});

// ─────────────────────────────────────────────────────────────
// RESET
// ─────────────────────────────────────────────────────────────

document.getElementById('resetBtn').addEventListener('click', () => {
  if (isLoading) return;
  st.budget=2000000; st.budgetMin=1000000; st.budgetMax=2000000; st.resolution='1080'; st.refresh=60; st.gpu_pref='nopref'; st.gpu_brands=[]; st.game='cyberpunk2077'; st.gameCategory='aaa'; st.panelWork='video_4k';
  st.lastRecommendation = null;
  ['#budgetChoices .choice','#resChoices .choice','#refreshChoices .choice','#gpuPrefChoices .choice']
    .forEach(sel => document.querySelectorAll(sel).forEach(n => n.classList.remove('selected')));
  document.querySelectorAll('#gpuMakerChoices .choice').forEach(n => n.classList.remove('selected'));
  syncDefaults(); clearStatus(); resultsContainer.innerHTML=''; placeholder.style.display='flex';
});

// ─────────────────────────────────────────────────────────────
// SYNC DEFAULTS
// ─────────────────────────────────────────────────────────────

function syncDefaults() {
  [
    ['#budgetChoices .choice',   n => Number(n.dataset.budgetMin)===st.budgetMin && Number(n.dataset.budgetMax)===st.budgetMax],
    ['#resChoices .choice',      n => n.dataset.resolution===st.resolution],
    ['#refreshChoices .choice',  n => Number(n.dataset.refresh)===st.refresh],
    ['#gpuPrefChoices .choice',  n => n.dataset.gpu===st.gpu_pref],
  ].forEach(([sel, test]) => {
    const node = Array.from(document.querySelectorAll(sel)).find(test);
    if (node) node.classList.add('selected');
  });
  populateGameSelects();
  const workSel = document.getElementById('panelWorkSelect');
  if (workSel) workSel.value = st.panelWork;
}

// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────

initDropdowns();
syncDefaults();
setActiveView(st.activeView);
loadServerCatalog();
refreshSelectedPrices();
