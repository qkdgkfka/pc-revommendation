import {
  builderSpecs,
  socketCompatibility,
  BUILDER_SPEED_RANGES,
  BUILDER_WATT_RANGES,
  builderRange,
} from "./specs.js";
import { numeric, storageTbValue } from "./performance.js";
export function money(v) {
  const n = Number(v);
  return (!v && v !== 0) || isNaN(n) ? "-" : "₩" + n.toLocaleString("ko-KR");
}
export function escapeHtml(v) {
  return String(v ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[ch],
  );
}
export function shopSearchUrl(name) {
  const q = String(name || "")
    .trim()
    .replace(/\s+/g, " ");
  return q
    ? `https://search.danawa.com/dsearch.php?query=${encodeURIComponent(q)}`
    : "#";
}
export function queryString(params) {
  return Object.entries(params)
    .map(
      ([key, value]) =>
        `${encodeURIComponent(key)}=${encodeURIComponent(value ?? "")}`,
    )
    .join("&");
}
export function partUrl(part) {
  return (
    part?.source_url ||
    part?.url ||
    part?.shop_url ||
    part?.product_url ||
    shopSearchUrl(part?.name)
  );
}
export function gpuBrand(item) {
  const value = String(
    item?.brand || item?.vendor || item?.name || "",
  ).toLowerCase();
  if (
    value.includes("nvidia") ||
    value.includes("geforce") ||
    value.includes("rtx") ||
    value.includes("gtx")
  )
    return "nvidia";
  if (value.includes("amd") || value.includes("radeon") || value.includes("rx"))
    return "amd";
  return value || "unknown";
}
export function withPartType(items, type) {
  return (items || []).map((item) => {
    const specs = builderSpecs(item, type);
    return {
      ...item,
      ...(type === "psu" && specs.watt ? { watt: specs.watt } : {}),
      ...(["cpu", "mb"].includes(type) && specs.socket !== "unknown"
        ? { socket: specs.socket }
        : {}),
      ...(type === "mb" && specs.memoryTypes.length === 1
        ? { ram_type: specs.memoryTypes[0] }
        : {}),
      type: type === "ram" ? specs.memoryTypes[0] || "" : type,
      part_type: type,
      component_type: type,
      brand: type === "gpu" ? gpuBrand(item) : item.brand,
    };
  });
}
export function fullProductName(item) {
  const name = String(item?.product_name || item?.name || "-");
  const brand = String(item?.brand || "").trim();
  if (
    !brand ||
    brand.toLowerCase() === "nvidia" ||
    brand.toLowerCase() === "amd"
  )
    return name;
  return name.toLowerCase().includes(brand.toLowerCase())
    ? name
    : `${brand} ${name}`;
}
export function productManufacturer(item) {
  const fullName = fullProductName(item);
  const makers = [
    ["GIGABYTE", /gigabyte|기가바이트/i],
    ["ASUS", /asus|아수스|에이수스/i],
    ["MSI", /\bmsi\b/i],
    ["ZOTAC", /zotac|조텍/i],
    ["GALAX", /galax|갤럭시/i],
    ["이엠텍", /emtek|이엠텍/i],
    ["PALIT", /palit|팰릿/i],
    ["COLORFUL", /colorful|컬러풀/i],
    ["SAPPHIRE", /sapphire|사파이어/i],
    ["PowerColor", /powercolor|파워컬러/i],
    ["XFX", /\bxfx\b/i],
    ["삼성", /samsung|삼성/i],
    ["SK하이닉스", /sk\s*hynix|하이닉스/i],
    ["마이크론", /micron|crucial|마이크론/i],
    ["WD", /western digital|\bwd\b|웨스턴디지털/i],
    ["Seagate", /seagate|씨게이트/i],
    ["G.SKILL", /g\.?skill|지스킬/i],
    ["CORSAIR", /corsair|커세어/i],
    ["TeamGroup", /teamgroup|팀그룹/i],
    ["ESSENCORE KLEVV", /(?:essencore\s+)?klevv|essencore|에센코어|클레브/i],
    ["Kingston", /kingston|킹스톤/i],
    ["Lexar", /lexar|렉사/i],
    ["ADATA", /adata|에이데이타/i],
    ["KIOXIA", /kioxia|키오시아/i],
    ["PATRIOT", /patriot|패트리어트/i],
    ["Toshiba", /toshiba|도시바/i],
    ["GeIL", /geil|게일/i],
    ["OLOy", /oloy|올로와이/i],
    ["마이크로닉스", /micronics|마이크로닉스/i],
    ["FSP", /\bfsp\b/i],
    ["Seasonic", /seasonic|시소닉/i],
    ["SuperFlower", /superflower|슈퍼플라워/i],
    ["ASRock", /asrock|애즈락/i],
    ["Intel", /intel|인텔/i],
    ["AMD", /\bamd\b|라이젠|ryzen/i],
  ];
  const makerText = [item.manufacturer, item.maker, fullName, item.brand]
    .filter(Boolean)
    .join(" ");
  const maker =
    makers.find(([, pattern]) => pattern.test(makerText))?.[0] ||
    String(item.manufacturer || item.maker || item.brand || "").replace(
      /^(nvidia|amd)$/i,
      "",
    );
  return {
    label: maker || "",
    pattern: makers.find(([label]) => label === maker)?.[1],
  };
}
export function displayName(item) {
  const fullName = fullProductName(item);
  if (!item || /추가 안 함|직접 선택/.test(fullName)) return fullName;
  const manufacturer = productManufacturer(item);
  const maker = manufacturer.label;
  const gpu = fullName.match(
    /\b(RTX|GTX|RX)\s*[- ]?\s*(\d{4})\s*(TI\s*SUPER|TI|SUPER|XTX|XT|GRE)?/i,
  );
  if (gpu) {
    const suffix = (gpu[3] || "")
      .toUpperCase()
      .replace("TI", "Ti")
      .replace("SUPER", "Super");
    const vramVariant =
      /5060\s*ti|4060\s*ti/i.test(gpu[0]) && item.vram ? ` ${item.vram}GB` : "";
    return `${maker || (gpu[1].toUpperCase() === "RX" ? "AMD" : "NVIDIA")} - ${gpu[1].toUpperCase()} ${gpu[2]}${suffix ? ` ${suffix}` : ""}${vramVariant}`;
  }
  const type = item.part_type || item.component_type || item.type || "";
  const intel = fullName.match(
    /(?:i[3579]\s*[- ]?\s*|코어\s*i[3579]\s*)?(\d{4,5}(?:KF|KS|K|F|T|HX|H|U)?)\b/i,
  );
  if (/intel|인텔|core\s*i[3579]/i.test(fullName) && intel)
    return `Intel - ${intel[1].toUpperCase()}`;
  const ultra = fullName.match(
    /(?:ultra|울트라)\s*([3579])?\s*[- ]?\s*(\d{3}[A-Z]*)/i,
  );
  if (ultra)
    return `Intel - Ultra ${ultra[1] ? `${ultra[1]} ` : ""}${ultra[2].toUpperCase()}`;
  const ryzen = fullName.match(
    /(?:ryzen|라이젠)[^\d]*(?:[3579]\s+)?(\d{4}(?:X3D|XT|X|G|F|GE)?)/i,
  );
  if (ryzen) return `AMD - Ryzen ${ryzen[1].toUpperCase()}`;
  if ((type === "ram" || /^DDR[345]$/i.test(type)) && item.gb) {
    const memoryType =
      item.ram_type ||
      (/^DDR[345]$/i.test(item.type)
        ? item.type
        : fullName.match(/DDR[345]/i)?.[0]);
    return `${maker ? `${maker} - ` : ""}${[memoryType, `${item.gb}GB`, item.speed].filter(Boolean).join(" ")}`;
  }
  let shortName = fullName
    .replace(/\([^)]*\)|\[[^\]]*\]/g, "")
    .replace(/벌크|정품|병행수입|해외구매|공식인증|당일발송|무료배송/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (manufacturer.pattern)
    shortName = shortName.replace(manufacturer.pattern, "").trim();
  if (maker && shortName.toLowerCase().startsWith(maker.toLowerCase()))
    shortName = shortName.slice(maker.length).trim();
  const label = `${maker ? `${maker} - ` : ""}${shortName}`;
  return label.length > 46 ? `${label.slice(0, 43).trim()}…` : label;
}
export function partMeta(part, type = "") {
  const items = [];
  const brand = String(part?.brand || "").trim();
  const typeText = String(part?.type || "").toUpperCase();
  if (type === "cpu" || part?.cores || part?.threads) {
    const cpuBits = [];
    if (part?.vendor) cpuBits.push(part.vendor);
    if (part?.socket) cpuBits.push(part.socket);
    if (part?.cores) cpuBits.push(`${part.cores}코어`);
    if (part?.threads) cpuBits.push(`${part.threads}스레드`);
    if (cpuBits.length) items.push(cpuBits.join(" · "));
  }
  if (type === "gpu" || part?.vram) {
    const gpuBits = [];
    if (part?.vendor) gpuBits.push(part.vendor);
    if (part?.vram) gpuBits.push(`VRAM ${part.vram}GB`);
    if (part?.tdp) gpuBits.push(`${part.tdp}W`);
    if (gpuBits.length) items.push(gpuBits.join(" · "));
  }
  if (brand && !["nvidia", "amd"].includes(brand.toLowerCase()))
    items.push(brand);
  if (
    type === "ram" ||
    part?.gb ||
    part?.speed ||
    ["DDR4", "DDR5"].includes(typeText)
  ) {
    const ramBits = [];
    if (part?.gb) ramBits.push(`${part.gb}GB`);
    if (part?.type) ramBits.push(part.type);
    if (part?.speed) ramBits.push(`${part.speed}MHz`);
    if (ramBits.length) items.push(ramBits.join(" · "));
  }
  if (type === "psu" || part?.watt || part?.recommendedWatt) {
    const watt = part?.watt || part?.recommendedWatt;
    if (watt) items.push(`${watt}W`);
  }
  if (
    (type === "mb" || part?.socket || part?.ram_type) &&
    (part?.socket || part?.ram_type)
  ) {
    items.push([part?.socket, part?.ram_type].filter(Boolean).join(" · "));
  }
  if (
    (type === "storage" || type === "hdd" || part?.capacity) &&
    part?.capacity
  ) {
    items.push(
      `${part.capacity >= 1000 ? part.capacity / 1000 + "TB" : part.capacity + "GB"}`,
    );
  }
  if (type === "hdd" && part?.rpm) items.push(`${part.rpm}RPM`);
  if (type === "case") {
    const caseBits = [part?.form_factor, part?.color].filter(Boolean);
    if (caseBits.length) items.push(caseBits.join(" · "));
  }
  if (type === "software" && part?.license && part.license !== "none")
    items.push(part.license);
  return [...new Set(items.filter(Boolean))].join(" · ");
}
export function catalogKey(name) {
  return String(name || "")
    .toLowerCase()
    .replace(
      /\b(nvidia|amd|intel|geforce|radeon|core|graphics|processor)\b/g,
      "",
    )
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}
export function catalogMatchScore(a, b) {
  if (!a || !b) return 0;
  if (a === b) return 2;
  const at = new Set(a.split(/\s+/).filter(Boolean));
  const bt = new Set(b.split(/\s+/).filter(Boolean));
  const inter = [...at].filter((x) => bt.has(x)).length;
  const union = new Set([...at, ...bt]).size || 1;
  let score = inter / union;
  if (a.includes(b) || b.includes(a)) score += 0.5;
  return score;
}
export function mergeCatalogPrices(localItems, remoteItems) {
  const remoteList = remoteItems || [];
  const remoteByKey = new Map(
    remoteList.map((item) => [catalogKey(item.name), item]),
  );
  return localItems.map((item) => {
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
      shop: remote?.shop || item.shop || "Danawa",
      url: remote?.url || item.url || shopSearchUrl(item.name),
      price_source:
        remote?.price_source || item.price_source || "catalog_search",
    };
  });
}
export function seedCatalogItems(items) {
  return (items || []).map((item) => ({
    ...item,
    base_price: Number.isFinite(Number(item?.base_price))
      ? Number(item.base_price)
      : Number.isFinite(Number(item?.price))
        ? Number(item.price)
        : null,
    price:
      item.price_source &&
      !["catalog_fallback", "catalog_search", "danawa_search"].includes(
        item.price_source,
      )
        ? item.price
        : Number(item.price) === 0
          ? 0
          : null,
    price_source: item.price_source || "catalog_fallback",
    url: item.url || shopSearchUrl(item.name),
    image_url: item.image_url || "",
    shop: item.shop || "Danawa",
    currency: item.currency || "KRW",
  }));
}
export function effectivePrice(item) {
  const live = Number(item?.price);
  if (
    item?.price !== null &&
    item?.price !== undefined &&
    Number.isFinite(live) &&
    live >= 0
  )
    return live;
  const base = Number(item?.base_price);
  if (
    item?.base_price !== null &&
    item?.base_price !== undefined &&
    Number.isFinite(base) &&
    base >= 0
  )
    return base;
  return null;
}
export function marketName(source) {
  const text = String(source || "").toLowerCase();
  if (text.includes("compuzone") || text.includes("컴퓨존")) return "컴퓨존";
  if (text.includes("danawa") || text.includes("다나와")) return "다나와";
  return "다나와 + 컴퓨존";
}
export function priceProvenance(item) {
  const price = effectivePrice(item);
  if (price === 0 && /none$/.test(item?.id || ""))
    return { status: "optional", text: "추가 안 함" };
  if (price == null)
    return { status: "unavailable", text: "가격 미확인 · 판매처 확인 필요" };
  const source = String(item?.price_source || "");
  const shop = marketName(item?.shop || source);
  const checked =
    item?.price_checked_at || item?.scraped_at || item?.checked_at;
  const date = checked ? new Date(checked) : null;
  const checkedText =
    date && Number.isFinite(date.getTime())
      ? date.toLocaleString("ko-KR", {
          month: "numeric",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
  const status =
    item?.price_status === "stale" || item?.price_stale || item?.stale
      ? "stale"
      : item?.price_status === "cached"
        ? "cached"
        : item?.price_status === "verified" && item?.price != null
          ? "verified"
          : /(?:danawa|compuzone).*(?:live|browse)/.test(source) &&
              item?.price != null &&
              checkedText
            ? "verified"
            : "estimated";
  if (status === "verified")
    return {
      status,
      text: `${shop} 확인가${checkedText ? " · " + checkedText : ""}`,
    };
  if (status === "cached")
    return {
      status,
      text: `${shop} 저장된 확인가${checkedText ? " · " + checkedText : ""}`,
    };
  if (status === "stale")
    return {
      status,
      text: `${shop} 이전 확인가${checkedText ? " · " + checkedText : ""} · 재확인 필요`,
    };
  return { status, text: "참고가 · 현재 판매가 미확인" };
}
export function priceProvenanceHtml(item) {
  const provenance = priceProvenance(item);
  return `<span class="price-provenance ${provenance.status}">${escapeHtml(provenance.text)}</span>`;
}
export function catalogPriceLabel(item) {
  const price = effectivePrice(item);
  return `${displayName(item)} — ${price != null ? money(price) : "가격 미확인"} · ${priceProvenance(item).text}`;
}
export function uniqueProducts(items) {
  const seen = new Set();
  return (items || []).filter((item) => {
    const id = String(item?.id || "");
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}
export function bestProductImageUrl(current, candidate) {
  const realImage = (value) =>
    /^https?:\/\//i.test(value || "") &&
    !String(value).includes("/api/part-image");
  return realImage(candidate)
    ? candidate
    : realImage(current)
      ? current
      : candidate || current || "";
}
export function normSpecValue(v) {
  return String(v || "")
    .trim()
    .toLowerCase();
}
export function cpuVendor(part) {
  const text = String(
    part?.vendor || part?.brand || part?.name || "",
  ).toLowerCase();
  if (text.includes("amd") || text.includes("ryzen")) return "amd";
  if (text.includes("intel") || text.includes("core") || text.includes("ultra"))
    return "intel";
  return "other";
}
export function cpuCores(part) {
  const direct = numeric(part?.cores);
  if (direct != null) return direct;
  const name = String(part?.name || "").toLowerCase();
  if (name.includes("i9-13900") || name.includes("i9-14900")) return 24;
  if (name.includes("i7-14700")) return 20;
  if (name.includes("i7-13700")) return 16;
  if (name.includes("13600") || name.includes("14600") || name.includes("245k"))
    return 14;
  if (
    name.includes("13400") ||
    name.includes("14400") ||
    name.includes("1365u") ||
    name.includes("1335u")
  )
    return 10;
  if (name.includes("7950")) return 16;
  if (name.includes("7900")) return 12;
  if (
    name.includes("7800") ||
    name.includes("7700") ||
    name.includes("9700") ||
    name.includes("5700")
  )
    return 8;
  if (name.includes("5600") || name.includes("7600") || name.includes("1315u"))
    return 6;
  if (name.includes("i3")) return 4;
  return 0;
}
export function cpuThreads(part) {
  const direct = numeric(part?.threads);
  if (direct != null) return direct;
  const cores = cpuCores(part);
  if (!cores) return 0;
  return String(part?.name || "")
    .toLowerCase()
    .includes("ultra")
    ? cores
    : cores * 2;
}
export function gpuModelToken(part) {
  const pattern =
    /\b(RTX|GTX|RX)\s*[- ]?\s*(\d{4})\s*(Ti\s*Super|Ti|Super|XTX|XT|GRE)?\b/i;
  const match = [
    part?.chipset,
    part?.gpu_model,
    part?.model,
    part?.product_name,
    part?.name,
  ]
    .map((value) => String(value || "").match(pattern))
    .find(Boolean);
  if (!match) return "";
  const suffix = (match[3] || "")
    .toUpperCase()
    .replace(/TI\s*SUPER/, "Ti Super")
    .replace("TI", "Ti")
    .replace("SUPER", "Super");
  return `${match[1].toUpperCase()} ${match[2]}${suffix ? ` ${suffix}` : ""}`;
}
export function gpuSeriesToken(part) {
  const model = gpuModelToken(part);
  if (!model) return "";
  const [family, number] = model.split(" ");
  if (family === "RTX" && Number(number[2]) < 5) return "";
  const structured = String(part?.series || "")
    .replace(/\s+Series$/i, "")
    .trim()
    .toUpperCase();
  return /^(?:RTX|GTX) \d{2}$|^RX \d000$/.test(structured)
    ? structured
    : `${family} ${family === "RX" ? number[0] + "000" : number.slice(0, 2)}`;
}
export function gpuSeriesGroups(items) {
  const groups = new Map();
  for (const item of items) {
    const model = gpuModelToken(item);
    if (!model) continue;
    const [family, number] = model.split(" ");
    // Workstation RTX 4500/6000-style numbers are not GeForce generation models.
    if (family === "RTX" && Number(number[2]) < 5) continue;
    const vendor = family === "RX" ? "AMD" : "NVIDIA";
    const label = `${gpuSeriesToken(item)} Series`;
    if (!groups.has(label)) groups.set(label, { vendor, label, models: [] });
    if (!groups.get(label).models.includes(model))
      groups.get(label).models.push(model);
  }
  return [...groups.values()]
    .sort((a, b) =>
      a.vendor === b.vendor
        ? a.label.localeCompare(b.label, "en", { numeric: true })
        : a.vendor === "NVIDIA"
          ? -1
          : 1,
    )
    .map((group) => ({
      ...group,
      models: group.models.sort((a, b) =>
        a.localeCompare(b, "en", { numeric: true }),
      ),
    }));
}
export function preferredGpuProductForModel(model, available, references) {
  const matches = available.filter((part) => gpuModelToken(part) === model);
  const reference = references.find((part) => gpuModelToken(part) === model);
  const photo = matches.find((part) =>
    /^https?:\/\//i.test(part.image_url || ""),
  );
  if (reference) {
    if (!/^https?:\/\//i.test(reference.image_url || "") && photo)
      reference.image_url = photo.image_url;
    return reference;
  }
  return photo || matches[0] || null;
}
export function psuRating(part) {
  const rating = builderSpecs(part, "psu").rating;
  return rating === "unknown" ? "" : rating;
}
export function valueSet(items, mapper) {
  return [...new Set(items.map(mapper).filter((v) => v !== "" && v != null))];
}
export function rangeLabel(value, ranges) {
  const n = numeric(value, 0);
  const found = ranges.find((r) => n >= r.min && n <= r.max);
  return found ? found.label : "";
}
export function normalizeSearchText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}
export function productBadges(part, type) {
  const specs = builderSpecs(part, type);
  const known = (value) => (value && value !== "unknown" ? value : "");
  if (type === "cpu")
    return [known(specs.socket), ...specs.memoryTypes].filter(Boolean);
  if (type === "gpu") return [];
  if (type === "ram")
    return [
      ...specs.memoryTypes,
      part.gb ? `${part.gb}GB` : "",
      part.speed ? `${part.speed}MT/s` : "",
      { White: "화이트", Black: "블랙", Silver: "실버", Red: "레드" }[
        specs.color
      ],
      { yes: "LED 포함", no: "LED 없음" }[specs.led],
    ].filter(Boolean);
  if (type === "mb")
    return [part.socket, part.ram_type, part.brand].filter(Boolean);
  if (type === "storage")
    return [
      part.capacity
        ? part.capacity >= 1000
          ? `${part.capacity / 1000}TB`
          : `${part.capacity}GB`
        : "",
      known(specs.formFactor),
      known(specs.interface),
      specs.pcie !== "unknown" ? `PCIe ${specs.pcie}.0` : "",
      specs.readSpeed
        ? `읽기 ${specs.readSpeed.toLocaleString("ko-KR")} MB/s`
        : "읽기 미확인",
      specs.writeSpeed
        ? `쓰기 ${specs.writeSpeed.toLocaleString("ko-KR")} MB/s`
        : "쓰기 미확인",
    ].filter(Boolean);
  if (type === "hdd")
    return [
      part.capacity ? `${part.capacity / 1000}TB` : "추가 안 함",
      part.rpm ? `${part.rpm}RPM` : "",
      part.brand,
    ].filter(Boolean);
  if (type === "psu")
    return [
      specs.watt ? `${specs.watt}W` : "",
      psuRating(part) ? `80 PLUS ${psuRating(part)}` : "인증 미확인",
      { Full: "풀모듈러", Semi: "세미모듈러", Fixed: "고정 케이블" }[
        specs.modular
      ],
      specs.atx !== "unknown" ? `ATX ${specs.atx}` : "",
    ].filter(Boolean);
  if (type === "case")
    return [part.form_factor, part.color, part.brand].filter(Boolean);
  if (type === "software")
    return [
      part.license === "none" ? "추가 안 함" : part.license,
      part.brand,
    ].filter(Boolean);
  return [];
}
export function workFillClass(score) {
  return score >= 75
    ? "work-great"
    : score >= 55
      ? "work-good"
      : score >= 35
        ? "work-ok"
        : "work-poor";
}
export function compatibilityHtml(cpu, mb) {
  const result = socketCompatibility(cpu, mb);
  if (result.status === "incomplete") return "";
  if (result.status === "compatible") {
    return `<div class="build-compatibility compatible"><strong>✓ CPU · 메인보드 소켓 호환</strong><p>${escapeHtml(result.cpuSocket)} · BIOS와 CPU 지원 목록은 제조사에서 확인해주세요.</p></div>`;
  }
  const title =
    result.status === "incompatible"
      ? "⚠ 선택한 CPU와 메인보드의 소켓이 호환되지 않습니다."
      : "CPU · 메인보드 소켓 확인 필요";
  const detail =
    result.status === "incompatible"
      ? "CPU 또는 메인보드를 같은 소켓의 제품으로 변경해주세요."
      : "소켓 정보가 부족해 호환 여부를 판단할 수 없습니다. 제조사 상세 사양을 확인해주세요.";
  const socketLabel = (socket) => (socket === "unknown" ? "미확인" : socket);
  return `<div class="build-compatibility ${result.status}">
    <strong>${escapeHtml(title)}</strong>
    <dl class="compatibility-parts">
      <div><dt>CPU</dt><dd>${escapeHtml(fullProductName(cpu))}<span>CPU 소켓: ${escapeHtml(socketLabel(result.cpuSocket))}</span></dd></div>
      <div><dt>메인보드</dt><dd>${escapeHtml(fullProductName(mb))}<span>메인보드 소켓: ${escapeHtml(socketLabel(result.motherboardSocket))}</span></dd></div>
    </dl><p>${escapeHtml(detail)}</p>
  </div>`;
}
export const BUILDER_PARTS = [
  { key: "cpu", label: "CPU", select: "csCpu", cart: "CPU" },
  { key: "mb", label: "메인보드", select: "csMb", cart: "MB" },
  { key: "gpu", label: "GPU", select: "csGpu", cart: "GPU" },
  { key: "ram", label: "RAM", select: "csRam", cart: "RAM" },
  { key: "storage", label: "SSD", select: "csStorage", cart: "SSD" },
  { key: "hdd", label: "HDD", select: "csHdd", cart: "HDD" },
  { key: "psu", label: "파워", select: "csPsu", cart: "PSU" },
  { key: "case", label: "케이스", select: "csCase", cart: "CASE" },
  { key: "software", label: "소프트웨어", select: "csSoftware", cart: "SW" },
];
export const BUILDER_META = Object.fromEntries(
  BUILDER_PARTS.map((item) => [item.key, item]),
);

export function applyPriceObservation(target, result) {
  if (result.price != null) target.price = Number(result.price);
  if (result.url) target.url = result.url;
  if (result.shop) target.shop = result.shop;
  if (result.currency) target.currency = result.currency;
  if (result.price_source) target.price_source = result.price_source;
  if (result.product_name) target.product_name = result.product_name;
  if (result.image_url)
    target.image_url = bestProductImageUrl(target.image_url, result.image_url);
  ["price_status", "price_checked_at", "scraped_at", "source_url"].forEach(
    (key) => {
      if (result[key] != null) target[key] = result[key];
    },
  );
  const observedAt = result.price_checked_at || result.scraped_at;
  if (observedAt) target.price_checked_at = observedAt;
  if (result.price_status === "verified" || result.price_status === "cached") {
    target.stale = false;
    target.price_stale = false;
  } else if (result.price_status === "stale") {
    target.stale = true;
    target.price_stale = true;
  }
  target.lookup_name = result.name || target.lookup_name || target.name;
  return target;
}
