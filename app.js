
// ─────────────────────────────────────────────────────────────
// Local catalog fallback. The server catalog replaces it when available.
// ─────────────────────────────────────────────────────────────
let GPUS_NVIDIA = [
  { id:'gpu_4090',    name:'NVIDIA RTX 4090',         price:2200000, perf:3000, tdp:450, brand:'nvidia' },
  { id:'gpu_4080s',   name:'NVIDIA RTX 4080 Super',   price:1350000, perf:2450, tdp:320, brand:'nvidia' },
  { id:'gpu_4080',    name:'NVIDIA RTX 4080',         price:1200000, perf:2200, tdp:320, brand:'nvidia' },
  { id:'gpu_4070tis', name:'NVIDIA RTX 4070 Ti Super',price:950000,  perf:2000, tdp:285, brand:'nvidia' },
  { id:'gpu_4070ti',  name:'NVIDIA RTX 4070 Ti',      price:900000,  perf:1900, tdp:285, brand:'nvidia' },
  { id:'gpu_4070s',   name:'NVIDIA RTX 4070 Super',   price:800000,  perf:1750, tdp:220, brand:'nvidia' },
  { id:'gpu_4070',    name:'NVIDIA RTX 4070',         price:700000,  perf:1600, tdp:200, brand:'nvidia' },
  { id:'gpu_5070ti',  name:'NVIDIA RTX 5070 Ti',      price:1100000, perf:2350, tdp:300, brand:'nvidia', vram:16 },
  { id:'gpu_5070',    name:'NVIDIA RTX 5070',         price:830000,  perf:2050, tdp:250, brand:'nvidia', vram:12 },
  { id:'gpu_5060ti16',name:'NVIDIA RTX 5060 Ti 16GB', price:600000,  perf:1500, tdp:180, brand:'nvidia', vram:16 },
  { id:'gpu_5060',    name:'NVIDIA RTX 5060',         price:420000,  perf:1180, tdp:145, brand:'nvidia', vram:8 },
  { id:'gpu_4060ti',  name:'NVIDIA RTX 4060 Ti',      price:550000,  perf:1250, tdp:165, brand:'nvidia' },
  { id:'gpu_4060',    name:'NVIDIA RTX 4060',         price:430000,  perf:1050, tdp:115, brand:'nvidia' },
  { id:'gpu_3080',    name:'NVIDIA RTX 3080',         price:600000,  perf:1400, tdp:320, brand:'nvidia' },
  { id:'gpu_3070',    name:'NVIDIA RTX 3070',         price:380000,  perf:1000, tdp:220, brand:'nvidia' },
  { id:'gpu_3060',    name:'NVIDIA RTX 3060',         price:280000,  perf:700,  tdp:170, brand:'nvidia' },
  { id:'gpu_1660s',   name:'NVIDIA GTX 1660 Super',   price:180000,  perf:380,  tdp:125, brand:'nvidia' },
];
let GPUS_AMD = [
  { id:'gpu_rx7900xtx', name:'AMD RX 7900 XTX',  price:1200000, perf:2850, tdp:355, brand:'amd' },
  { id:'gpu_rx9070xt',  name:'AMD RX 9070 XT',   price:950000,  perf:2350, tdp:304, brand:'amd', vram:16 },
  { id:'gpu_rx9070',    name:'AMD RX 9070',      price:800000,  perf:2050, tdp:220, brand:'amd', vram:16 },
  { id:'gpu_rx7900xt',  name:'AMD RX 7900 XT',   price:900000,  perf:2400, tdp:315, brand:'amd' },
  { id:'gpu_rx7900gre', name:'AMD RX 7900 GRE',  price:700000,  perf:2000, tdp:260, brand:'amd' },
  { id:'gpu_rx7800xt',  name:'AMD RX 7800 XT',   price:580000,  perf:1500, tdp:263, brand:'amd' },
  { id:'gpu_rx7700xt',  name:'AMD RX 7700 XT',   price:460000,  perf:1200, tdp:245, brand:'amd' },
  { id:'gpu_rx7600xt',  name:'AMD RX 7600 XT',   price:380000,  perf:950,  tdp:190, brand:'amd' },
  { id:'gpu_rx7600',    name:'AMD RX 7600',       price:280000,  perf:650,  tdp:165, brand:'amd' },
  { id:'gpu_rx6800xt',  name:'AMD RX 6800 XT',   price:550000,  perf:1450, tdp:300, brand:'amd' },
  { id:'gpu_rx6700xt',  name:'AMD RX 6700 XT',   price:330000,  perf:900,  tdp:230, brand:'amd' },
  { id:'gpu_rx6600xt',  name:'AMD RX 6600 XT',   price:240000,  perf:620,  tdp:160, brand:'amd' },
  { id:'gpu_rx6600',    name:'AMD RX 6600',       price:190000,  perf:550,  tdp:132, brand:'amd' },
  { id:'gpu_rx6500xt',  name:'AMD RX 6500 XT',   price:110000,  perf:240,  tdp:107, brand:'amd' },
];
let GPUS_ALL = [...GPUS_NVIDIA, ...GPUS_AMD];

let CPUS = [
  { id:'cpu_i9_14900k',  name:'Intel Core i9-14900K',   price:800000, perf:1600, tdp:125 },
  { id:'cpu_i7_14700k',  name:'Intel Core i7-14700K',   price:560000, perf:1380, tdp:125 },
  { id:'cpu_i5_14600k',  name:'Intel Core i5-14600K',   price:370000, perf:1060, tdp:125 },
  { id:'cpu_i5_14400',   name:'Intel Core i5-14400',    price:250000, perf:780,  tdp:65  },
  { id:'cpu_i3_14100',   name:'Intel Core i3-14100',    price:150000, perf:480,  tdp:58  },
  { id:'cpu_i9_13900k',  name:'Intel Core i9-13900K',   price:650000, perf:1500, tdp:125 },
  { id:'cpu_i7_13700k',  name:'Intel Core i7-13700K',   price:420000, perf:1260, tdp:125 },
  { id:'cpu_i5_13600k',  name:'Intel Core i5-13600K',   price:330000, perf:980,  tdp:125 },
  { id:'cpu_i5_13400f',  name:'Intel Core i5-13400F',   price:210000, perf:700,  tdp:65  },
  { id:'cpu_i3_13100f',  name:'Intel Core i3-13100F',   price:120000, perf:430,  tdp:58  },
  { id:'cpu_i7_1365u',   name:'Intel Core i7-1365U',    price:320000, perf:620,  tdp:15  },
  { id:'cpu_i5_1335u',   name:'Intel Core i5-1335U',    price:240000, perf:520,  tdp:15  },
  { id:'cpu_i3_1315u',   name:'Intel Core i3-1315U',    price:170000, perf:360,  tdp:15  },
  { id:'cpu_ry9_7950x',  name:'AMD Ryzen 9 7950X',      price:840000, perf:1720, tdp:170 },
  { id:'cpu_ry9_7900x',  name:'AMD Ryzen 9 7900X',      price:600000, perf:1480, tdp:170 },
  { id:'cpu_ry7_7800x3d',name:'AMD Ryzen 7 7800X3D',    price:450000, perf:1350, tdp:120 },
  { id:'cpu_ry7_7700x',  name:'AMD Ryzen 7 7700X',      price:380000, perf:1200, tdp:105 },
  { id:'cpu_ry5_7600x',  name:'AMD Ryzen 5 7600X',      price:290000, perf:960,  tdp:105 },
  { id:'cpu_ry5_5600x',  name:'AMD Ryzen 5 5600X',      price:200000, perf:720,  tdp:65  },
  { id:'cpu_ry5_5500',   name:'AMD Ryzen 5 5500',        price:130000, perf:520,  tdp:65  },
];
let RAMS = [
  { id:'ram8',    name:'Samsung 8GB DDR4 3200',       brand:'Samsung',  price:38000,  perf:100, gb:8,  type:'DDR4', speed:3200 },
  { id:'ram16',   name:'Samsung 16GB DDR4 3200',      brand:'Samsung',  price:72000,  perf:180, gb:16, type:'DDR4', speed:3200 },
  { id:'ram32',   name:'TeamGroup 32GB DDR4 3200',    brand:'TeamGroup',price:135000, perf:340, gb:32, type:'DDR4', speed:3200 },
  { id:'ram64',   name:'Corsair 64GB DDR4 3600',      brand:'Corsair',  price:255000, perf:680, gb:64, type:'DDR4', speed:3600 },
  { id:'ram16d5', name:'Samsung 16GB DDR5 5600',      brand:'Samsung',  price:90000,  perf:220, gb:16, type:'DDR5', speed:5600 },
  { id:'ram32d5', name:'G.SKILL 32GB DDR5 6000',      brand:'G.SKILL',  price:165000, perf:420, gb:32, type:'DDR5', speed:6000 },
];
let MBS = [
  { id:'mb_b550',       name:'B550 ATX',       price:150000, socket:'AM4',     ram_type:'DDR4', brand:'ASUS' },
  { id:'mb_b650',       name:'B650 ATX',       price:220000, socket:'AM5',     ram_type:'DDR5', brand:'MSI' },
  { id:'mb_b760_ddr4',  name:'B760 ATX DDR4',  price:180000, socket:'LGA1700', ram_type:'DDR4', brand:'Gigabyte' },
  { id:'mb_b760_ddr5',  name:'B760 ATX DDR5',  price:205000, socket:'LGA1700', ram_type:'DDR5', brand:'ASRock' },
  { id:'mb_z890',       name:'Z890 ATX',       price:350000, socket:'LGA1851', ram_type:'DDR5', brand:'MSI' },
];
let STORAGES = [
  { id:'nvme512', name:'NVMe SSD 512GB', price:65000  },
  { id:'nvme1tb', name:'NVMe SSD 1TB',   price:120000 },
  { id:'nvme2tb', name:'NVMe SSD 2TB',   price:240000 },
  { id:'nvme4tb', name:'NVMe SSD 4TB',   price:480000 },
];
let HDDS = [
  { id:'hdd_none', name:'HDD 추가 안 함', brand:'-', price:0, capacity:0, rpm:0 },
  { id:'hdd_1tb', name:'Seagate BarraCuda 1TB HDD', brand:'Seagate', price:65000, capacity:1000, rpm:7200 },
  { id:'hdd_2tb', name:'WD Blue 2TB HDD', brand:'Western Digital', price:85000, capacity:2000, rpm:5400 },
  { id:'hdd_4tb', name:'Toshiba P300 4TB HDD', brand:'Toshiba', price:135000, capacity:4000, rpm:7200 },
  { id:'hdd_8tb', name:'Seagate IronWolf 8TB HDD', brand:'Seagate', price:280000, capacity:8000, rpm:7200 },
];
let PSUS = [
  { id:'psu_650',  name:'Micronics 650W 80+ Bronze',       brand:'Micronics',   price:65000,  watt:650 },
  { id:'psu_750',  name:'FSP 750W 80+ Gold',               brand:'FSP',         price:105000, watt:750 },
  { id:'psu_850',  name:'SuperFlower 850W 80+ Gold',       brand:'SuperFlower', price:145000, watt:850 },
  { id:'psu_1000', name:'Seasonic 1000W 80+ Gold',         brand:'Seasonic',    price:185000, watt:1000 },
  { id:'psu_1200', name:'Corsair 1200W 80+ Platinum',      brand:'Corsair',     price:265000, watt:1200 },
];
let CASES = [
  { id:'case_none', name:'케이스 직접 선택', brand:'-', price:0, form_factor:'-', color:'-' },
  { id:'case_mini', name:'darkFlash DLM21 MESH', brand:'darkFlash', price:52000, form_factor:'mATX', color:'Black' },
  { id:'case_mid_air', name:'3RSYS L600 Quiet', brand:'3RSYS', price:78000, form_factor:'ATX', color:'Black' },
  { id:'case_mid_rgb', name:'NZXT H5 Flow RGB', brand:'NZXT', price:145000, form_factor:'ATX', color:'White' },
  { id:'case_high', name:'Fractal Design North', brand:'Fractal Design', price:210000, form_factor:'ATX', color:'Black' },
];
let SOFTWARES = [
  { id:'sw_none', name:'소프트웨어 추가 안 함', brand:'-', price:0, license:'none' },
  { id:'sw_win11_home', name:'Microsoft Windows 11 Home FPP', brand:'Microsoft', price:170000, license:'FPP' },
  { id:'sw_win11_pro', name:'Microsoft Windows 11 Pro FPP', brand:'Microsoft', price:260000, license:'FPP' },
  { id:'sw_office_home', name:'Microsoft Office Home 2024', brand:'Microsoft', price:170000, license:'perpetual' },
];

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
let productLookupToken = 0;
let customFpsToken = 0;
const customFpsCache = new Map();
const danawaBrowseByType = Object.create(null);
const pinnedBrowseProducts = Object.create(null);
let danawaBrowseRequestToken = 0;
let productSearchTimer = 0;

// ─────────────────────────────────────────────────────────────
// UTILITIES
// ─────────────────────────────────────────────────────────────
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
function partImageUrl(part, type = '') {
  if (!part?.name && !part?.product_name) return '';
  if (String(part.image_url || '').startsWith('/api/part-image?')) return `${baseUrl()}${part.image_url}`;
  if (/^https?:\/\//i.test(part.image_url || '') && new URL(part.image_url).pathname === '/api/part-image') return part.image_url;
  const name = part.product_name || part.name;
  const params = queryString({
    name:String(name), type:String(type || part.part_type || part.type || ''),
    image_url:part.image_url || '', product_url:partUrl(part),
  });
  return `${baseUrl()}/api/part-image?${params}`;
}
function previewAttrs(part, type = '') {
  if (!part?.name && !part?.product_name) return '';
  const price = effectivePrice(part);
  const data = {
    'preview-url': partUrl(part),
    'preview-name': fullProductName(part),
    'preview-image': partImageUrl(part, type),
    'preview-fallback': imageFallbackUrl(part),
    'preview-price': price != null ? money(price) : '',
    'preview-source': priceProvenance(part).text,
  };
  return Object.entries(data)
    .map(([key, value]) => `data-${key}="${escapeHtml(value)}"`)
    .join(' ');
}
function partThumb(part, type = '', className = 'part-thumb') {
  const src = partImageUrl(part, type);
  if (!src) return `<span class="${className}"></span>`;
  return `<span class="${className} image-loading"><img src="${escapeHtml(src)}" data-image-fallback="${escapeHtml(imageFallbackUrl(part))}" alt="${escapeHtml(displayName(part))} 제품 이미지" loading="lazy" decoding="async" referrerpolicy="no-referrer"/></span>`;
}
function imageFallbackUrl(part) {
  const url = String(part?.image_url || '');
  return /^https?:\/\//i.test(url) && !url.includes('/api/part-image') ? url : '';
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
function displayName(item) {
  const fullName = fullProductName(item);
  if (!item || /추가 안 함|직접 선택/.test(fullName)) return fullName;
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
  let maker = makers.find(([, pattern]) => pattern.test(makerText))?.[0]
    || String(item.manufacturer || item.maker || item.brand || '').replace(/^(nvidia|amd)$/i, '');
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
  const makerMatch = makers.find(([label]) => label === maker);
  if (makerMatch) shortName = shortName.replace(makerMatch[1], '').trim();
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
  const checked = item?.price_checked_at || item?.checked_at;
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
  if (result.image_url) target.image_url = result.image_url;
  ['price_status','price_checked_at','source_url'].forEach(key => {
    if (result[key] != null) target[key] = result[key];
  });
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
  const name = String(part?.name || '').toLowerCase();
  const patterns = [
    ['5090','5090'], ['5080','5080'], ['5070 ti','5070 Ti'], ['5070','5070'],
    ['5060 ti','5060 Ti'], ['5060','5060'], ['4090','4090'], ['4080','4080'],
    ['4070 ti','4070 Ti'], ['4070','4070'], ['4060 ti','4060 Ti'], ['4060','4060'],
    ['9070 xt','9070 XT'], ['9070','9070'], ['7900 xtx','7900 XTX'], ['7900 xt','7900 XT'],
    ['7900','7900'], ['7800','7800'], ['7700','7700'], ['7600','7600'], ['6600','6600'],
  ];
  const found = patterns.find(([needle]) => name.includes(needle));
  return found ? found[1] : '';
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
  box.innerHTML = builderFilterDefs(type).map(group => `
    <div class="filter-group">
      <div class="filter-label">${escapeHtml(group.label)}</div>
      <div class="filter-options">
        ${group.options.map(([value,label]) => `
          <button type="button" class="filter-check ${filterHas(type, group.key, value) ? 'selected' : ''}" aria-pressed="${filterHas(type, group.key, value)}"
            data-filter-key="${escapeHtml(group.key)}" data-filter-value="${escapeHtml(value)}">${escapeHtml(label)}</button>
        `).join('') || '<span class="product-source">선택 가능한 옵션 없음</span>'}
      </div>
    </div>
  `).join('');
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

function renderBuildCart() {
  const box = document.getElementById('buildCart');
  if (!box) return;
  const parts = selectedCustomParts();
  box.innerHTML = BUILDER_PARTS.map(meta => {
    const part = parts[meta.key] || {};
    const price = effectivePrice(part);
    const active = st.builderPart === meta.key;
    return `
      <button type="button" class="cart-row ${active ? 'active' : ''}" data-cart-part="${meta.key}" ${previewAttrs(part, meta.key)}>
        <span class="cart-label">${meta.cart}</span>
        ${partThumb(part, meta.key, 'cart-thumb')}
        <span class="cart-main">
          <span class="cart-name" title="${escapeHtml(fullProductName(part))}">${escapeHtml(part.name || part.product_name ? displayName(part) : '선택 필요')}</span>
          ${priceProvenanceHtml(part)}
        </span>
        <span class="cart-price">${price != null ? money(price) : '-'}</span>
      </button>`;
  }).join('');
  box.querySelectorAll('[data-cart-part]').forEach(row => {
    row.addEventListener('click', () => setBuilderPart(row.dataset.cartPart));
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
  sel.innerHTML = items.map(it =>
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
  const timeout = setTimeout(() => ctrl.abort(), 12000);
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
function fpsClass(fps, hz) {
  return fps >= hz*1.1 ? 'over' : fps >= hz*0.85 ? 'near' : 'low_';
}
function workFillClass(score) {
  return score >= 75 ? 'work-great' : score >= 55 ? 'work-good' : score >= 35 ? 'work-ok' : 'work-poor';
}
function hzPillClass(cov) { return cov>=1.0?'hzp-great':cov>=0.7?'hzp-ok':'hzp-poor'; }
function hzPillText(cov, hz) {
  const p = Math.round(cov*100);
  return cov>=1.1?`${hz}Hz 초과 달성 (${p}%)`:cov>=1.0?`${hz}Hz 달성 (${p}%)`:cov>=0.7?`${hz}Hz의 ${p}% 충족`:`${hz}Hz에 부족 (${p}%)`;
}
function valueIcon(l) { return {'목표 성능 여유':'✅','목표 성능 충족':'✅','거의 충족':'⚖️','최상 가성비':'🏆','좋은 가성비':'✅','적정':'⚖️','다소 부족':'⚠️','매우 부족':'❌'}[l]||'📊'; }

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
  productLookupToken += 1;
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

let previewTimer = null;
let previewPopover = null;
let previewTarget = null;

function ensurePreviewPopover() {
  if (previewPopover) return previewPopover;
  previewPopover = document.createElement('div');
  previewPopover.className = 'part-preview-popover';
  previewPopover.id = 'partImagePreview';
  previewPopover.setAttribute('role', 'tooltip');
  previewPopover.setAttribute('aria-hidden', 'true');
  previewPopover.innerHTML = '<div class="preview-image-wrap"><img alt="" referrerpolicy="no-referrer"><span class="preview-image-empty" hidden>대표 이미지가 없습니다</span></div><div class="preview-caption"><strong class="preview-name"></strong><span class="preview-price"></span><span class="preview-source"></span></div>';
  const img = previewPopover.querySelector('img');
  img.addEventListener('error', () => {
    if (retryProductImage(img)) return;
    img.hidden = true;
    previewPopover.querySelector('.preview-image-empty').hidden = false;
  });
  document.body.appendChild(previewPopover);
  return previewPopover;
}

function positionPreviewPopover(target, pop) {
  const rect = target.getBoundingClientRect();
  const margin = 12;
  const width = pop.offsetWidth || 260;
  const height = pop.offsetHeight || 300;
  let left = rect.right + margin;
  if (left + width > window.innerWidth - margin) left = rect.left - width - margin;
  left = Math.max(margin, Math.min(left, window.innerWidth - width - margin));
  const top = Math.max(margin, Math.min(rect.top, window.innerHeight - height - margin));
  pop.style.left = `${left}px`;
  pop.style.top = `${top}px`;
}

function hidePartPreview() {
  clearTimeout(previewTimer);
  previewTimer = null;
  if (previewTarget) previewTarget.removeAttribute('aria-describedby');
  previewTarget = null;
  if (previewPopover) {
    previewPopover.classList.remove('show');
    previewPopover.setAttribute('aria-hidden', 'true');
  }
}

function schedulePartPreview(target) {
  hidePartPreview();
  if (!target?.dataset?.previewName) return;
  previewTimer = setTimeout(() => {
    if (!target.isConnected) return;
    const pop = ensurePreviewPopover();
    const img = pop.querySelector('img');
    const src = target.dataset.previewImage;
    img.hidden = !src;
    pop.querySelector('.preview-image-empty').hidden = Boolean(src);
    img.alt = `${target.dataset.previewName} 대표 이미지`;
    img.dataset.imageFallback = target.dataset.previewFallback || '';
    delete img.dataset.imageRetried;
    if (src) img.src = src;
    else img.removeAttribute('src');
    pop.querySelector('.preview-name').textContent = target.dataset.previewName;
    pop.querySelector('.preview-price').textContent = target.dataset.previewPrice || '가격 미확인';
    pop.querySelector('.preview-source').textContent = target.dataset.previewSource || '';
    positionPreviewPopover(target, pop);
    pop.classList.add('show');
    pop.setAttribute('aria-hidden', 'false');
    target.setAttribute('aria-describedby', pop.id);
    previewTarget = target;
  }, 220);
}

function bindPreviewTargets(root = document) {
  if (!root?.querySelectorAll) return;
  root.querySelectorAll('[data-preview-name]').forEach(node => {
    if (node.dataset.previewBound) return;
    node.dataset.previewBound = '1';
    node.addEventListener('mouseenter', () => schedulePartPreview(node));
    node.addEventListener('mouseleave', hidePartPreview);
    node.addEventListener('focusin', () => schedulePartPreview(node));
    node.addEventListener('focusout', hidePartPreview);
  });
  root.querySelectorAll('.product-thumb img, .part-thumb img, .cart-thumb img').forEach(img => {
    if (img.dataset.fallbackBound) return;
    img.dataset.fallbackBound = '1';
    const fallback = () => {
      if (retryProductImage(img)) return;
      img.hidden = true;
      img.parentElement.classList.remove('image-loading');
      img.parentElement.classList.add('image-unavailable');
      img.parentElement.setAttribute('aria-label', '대표 이미지 없음');
    };
    const loaded = () => {
      img.hidden = false;
      img.parentElement.classList.remove('image-unavailable', 'image-loading');
      img.parentElement.removeAttribute('aria-label');
    };
    img.addEventListener('error', fallback);
    img.addEventListener('load', loaded);
    if (img.complete) img.naturalWidth ? loaded() : fallback();
  });
}

function retryProductImage(img) {
  const fallback = img.dataset.imageFallback;
  if (!fallback || img.dataset.imageRetried || img.src === fallback) return false;
  img.dataset.imageRetried = '1';
  img.hidden = false;
  img.src = fallback;
  return true;
}

document.addEventListener('keydown', event => { if (event.key === 'Escape') hidePartPreview(); });
window.addEventListener('resize', hidePartPreview);
window.addEventListener('scroll', hidePartPreview, true);

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
  sel.innerHTML = pool.map(g =>
    `<option value="${g.id}">${catalogPriceLabel(g)}</option>`
  ).join('');
  if (refreshChart) updateCustomChart();
}

function populateDropdown(id, items) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const type = SELECTOR_PART_TYPES[id];
  const pool = type ? allKnownProductsFor(type) : items;
  sel.innerHTML = pool.map(it =>
    `<option value="${it.id}">${catalogPriceLabel(it)}</option>`
  ).join('');
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
  populateMbs(CPUS[0], RAMS[0]);
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
    populateMbs(CPUS[0], RAMS[0]);
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
  if (!gpu || !cpu || !ram) return;

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
    ['csGpu','csCpu','csRam','csStorage','csHdd','csPsu','csCase','csSoftware'].forEach(id => {
      const sel = document.getElementById(id);
      if (sel && sel.options.length) sel.selectedIndex = 0;
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
