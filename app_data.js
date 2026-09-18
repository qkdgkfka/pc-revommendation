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
