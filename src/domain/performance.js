import { WORK_PROFILES } from "./options.js";
import { effectivePrice } from "./products.js";
const MAX_GPU_PERF = 3000,
  MAX_CPU_PERF = 1720,
  MAX_RAM_PERF = 680;
export function numeric(v, fallback = null) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}
export function parseGbFromName(name) {
  const m = String(name || "").match(/(\d+)\s*GB/i);
  return m ? Number(m[1]) : null;
}
export function gpuPerfValue(gpu, res = "1080") {
  const local = numeric(gpu?.perf);
  if (local != null && local > 120) return local;
  const serverPerf =
    res === "2160"
      ? numeric(gpu?.perf_2160)
      : res === "1440"
        ? numeric(gpu?.perf_1440)
        : numeric(gpu?.perf_1080);
  if (serverPerf != null && serverPerf > 0)
    return (serverPerf / 100) * MAX_GPU_PERF;
  if (local != null && local > 0) return (local / 100) * MAX_GPU_PERF;
  return 0;
}
export function cpuPerfValue(cpu) {
  const perf = numeric(cpu?.perf, 0);
  return perf <= 120 ? (perf / 100) * MAX_CPU_PERF : perf;
}
export function ramGbValue(ram) {
  return numeric(ram?.gb) ?? parseGbFromName(ram?.name) ?? 16;
}
export function ramPerfValue(ram) {
  const perf = numeric(ram?.perf);
  if (perf != null && perf > 0) return perf;
  const gb = ramGbValue(ram);
  const type = String(ram?.type || ram?.name || "").toUpperCase();
  const speed = numeric(ram?.speed, 0);
  let score = Math.min(MAX_RAM_PERF, (gb / 64) * MAX_RAM_PERF);
  if (type.includes("DDR5")) score *= speed >= 5600 ? 1.08 : 1.04;
  else if (speed >= 3200) score *= 1.02;
  return Math.min(MAX_RAM_PERF, score);
}
export function storageTbValue(storage) {
  const cap = numeric(storage?.capacity);
  if (cap != null && cap > 0) return cap / 1000;
  const m = String(storage?.name || "").match(/(\d+(?:\.\d+)?)\s*TB/i);
  if (m) return Number(m[1]);
  const g = String(storage?.name || "").match(/(\d+)\s*GB/i);
  return g ? Number(g[1]) / 1000 : 1;
}
export function componentPerformanceIndex(part, type, resolution = "1080") {
  if (!part) return 0;
  if (type === "gpu")
    return Math.min(100, (gpuPerfValue(part, resolution) / MAX_GPU_PERF) * 100);
  if (type === "cpu")
    return Math.min(100, (cpuPerfValue(part) / MAX_CPU_PERF) * 100);
  if (type === "ram")
    return Math.min(100, (ramPerfValue(part) / MAX_RAM_PERF) * 100);
  if (Number.isFinite(Number(part.performance_index)))
    return Math.max(0, Math.min(100, Number(part.performance_index)));

  const name = String(part.name || "").toLowerCase();
  const tier = String(part.tier || "").toLowerCase();
  if (type === "mb") {
    return Math.min(
      100,
      46 +
        (String(part.ram_type || "").toLowerCase() === "ddr5" ? 18 : 0) +
        (["am5", "lga1851"].includes(String(part.socket || "").toLowerCase())
          ? 16
          : String(part.socket || "").toLowerCase() === "lga1700"
            ? 10
            : 4) +
        ({ high: 16, mid: 9, low: 3 }[tier] || 0),
    );
  }
  if (type === "storage") {
    const capacity = Number(part.capacity || 0);
    return Math.min(
      100,
      Math.min(55, (capacity / 4000) * 55) +
        (name.includes("gen5")
          ? 42
          : name.includes("gen4") || name.includes("nvme")
            ? 30
            : name.includes("sata")
              ? 12
              : 20),
    );
  }
  if (type === "hdd")
    return Math.min(
      100,
      Math.min(78, (Number(part.capacity || 0) / 12000) * 78) +
        (Number(part.rpm || 0) >= 7200 ? 18 : Number(part.rpm || 0) ? 10 : 0),
    );
  if (type === "psu")
    return Math.min(
      100,
      Math.min(
        78,
        (Number(part.watt || part.recommendedWatt || 0) / 1200) * 78,
      ) +
        (name.includes("platinum")
          ? 22
          : name.includes("gold")
            ? 16
            : name.includes("bronze")
              ? 8
              : 0),
    );
  if (type === "case")
    return Math.min(
      100,
      ({ low: 48, mid: 66, high: 82 }[tier] || 52) +
        (name.includes("flow") || name.includes("mesh") || name.includes("air")
          ? 8
          : 0),
    );
  if (type === "software") {
    if (String(part.license || "").toLowerCase() === "none") return 0;
    return Math.min(
      100,
      48 +
        (name.includes("pro") || name.includes("business") ? 28 : 0) +
        (name.includes("adobe") ? 20 : 0),
    );
  }
  return 0;
}
export function componentMetricName(part, type) {
  if (part?.performance_metric) return String(part.performance_metric);
  return (
    {
      gpu: "QHD 래스터 지수",
      cpu: "CPU 처리 지수",
      ram: "메모리 용량·대역폭 지수",
      mb: "확장성·전원부 지수",
      storage: "저장공간·속도 지수",
      hdd: "저장공간·회전수 지수",
      psu: "출력·효율 지수",
      case: "냉각·확장성 지수",
      software: "소프트웨어 구성 지수",
    }[type] || "성능 지수"
  );
}
export function componentValueMetric(
  part,
  type,
  catalog = [],
  resolution = "1080",
) {
  const price = effectivePrice(part);
  const index = componentPerformanceIndex(part, type, resolution);
  if (!Number.isFinite(price) || price < 0)
    return {
      index,
      ratio: null,
      grade: "계산 대기",
      metric: componentMetricName(part, type),
    };
  if (price === 0)
    return {
      index,
      ratio: null,
      grade: "추가 비용 없음",
      metric: componentMetricName(part, type),
    };
  const ratio = index / Math.max(1, price / 10000);
  const ratios = catalog
    .map((item) => {
      const itemPrice = effectivePrice(item);
      return itemPrice > 0
        ? componentPerformanceIndex(item, type, resolution) /
            Math.max(1, itemPrice / 10000)
        : null;
    })
    .filter((value) => Number.isFinite(value) && value > 0)
    .sort((a, b) => a - b);
  const median = ratios.length ? ratios[Math.floor(ratios.length / 2)] : ratio;
  const grade =
    ratio >= median * 1.24
      ? "매우 좋음"
      : ratio >= median * 1.08
        ? "좋음"
        : ratio >= median * 0.88
          ? "보통"
          : "낮음";
  return { index, ratio, grade, metric: componentMetricName(part, type) };
}
export function componentValueText(
  part,
  type,
  compact = false,
  catalog = [],
  resolution,
) {
  const metric = componentValueMetric(part, type, catalog, resolution);
  if (metric.ratio == null) return metric.grade;
  const prefix = compact
    ? ""
    : `${metric.metric} ${metric.index.toFixed(0)} · `;
  return `${prefix}1만원당 ${metric.ratio.toFixed(2)} 지수 · ${metric.grade}`;
}

// FPS values and evidence are supplied by the server benchmark engine.
export function suitabilityFromScore(score) {
  const value = Number(score) || 0;
  if (value >= 85) return { label: "매우 적합", level: "excellent" };
  if (value >= 70) return { label: "적합", level: "good" };
  if (value >= 50) return { label: "보통", level: "normal" };
  if (value >= 35) return { label: "부적합", level: "poor" };
  return { label: "매우 부적합", level: "bad" };
}
export function workScore(gpu, cpu, ram, storage, wtKey) {
  const wt = WORK_PROFILES[wtKey] || WORK_PROFILES.video_4k;
  const gs = Math.min(100, (gpuPerfValue(gpu, "1440") / MAX_GPU_PERF) * 100);
  const cs = Math.min(100, (cpuPerfValue(cpu) / MAX_CPU_PERF) * 100);
  const rs = Math.min(100, (ramPerfValue(ram) / MAX_RAM_PERF) * 100);
  const ss = Math.min(100, (storageTbValue(storage) / 2) * 100);
  let score =
    (wt.w.gpu || 0) * gs +
    (wt.w.cpu || 0) * cs +
    (wt.w.ram || 0) * rs +
    (wt.w.storage || 0) * ss;
  const req = wt.req || {};
  const ramGb = ramGbValue(ram);
  const storageTb = storageTbValue(storage);
  if (req.gpu && gs < req.gpu) score -= Math.min(22, (req.gpu - gs) * 0.36);
  if (req.cpu && cs < req.cpu) score -= Math.min(18, (req.cpu - cs) * 0.3);
  if (req.ramGb && ramGb < req.ramGb)
    score -= ramGb >= req.ramGb * 0.5 ? 8 : 16;
  if (req.storageTb && storageTb < req.storageTb) score -= 4;
  return Math.max(0, Math.min(100, Math.round(score)));
}

// ─────────────────────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────────────────────
export function pricePerFrame(totalPrice, fps) {
  const price = Number(totalPrice),
    frames = Number(fps);
  return Number.isFinite(price) &&
    price > 0 &&
    Number.isFinite(frames) &&
    frames > 0
    ? price / frames
    : null;
}
export function customFpsKey(gpu, cpu, ram, game, resolution, refresh) {
  return [gpu?.id, cpu?.id, ram?.id, game, resolution, refresh].join("|");
}
export function fpsRequestPart(part) {
  if (!part?.performance_ref_id) return part?.id || "";
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
