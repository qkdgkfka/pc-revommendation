export function normalizeCpuSocket(value) {
  const raw = String(value ?? "")
    .trim()
    .toUpperCase()
    .replace(/^(?:CPU\s*)?(?:SOCKET|소켓)\s*[:：]?\s*/, "")
    .replace(/[ -]/g, "");
  const key = /^\d{3,4}$/.test(raw) ? `LGA${raw}` : raw;
  return /^(?:(?:LGA|BGA)\d{3,4}|(?:AM|FM)\d\+?|S?TRX?\d|SP\d)$/.test(key)
    ? key
    : "";
}

// A tri-state check, plus an incomplete state until both parts are selected.
// Socket compatibility is separate from BIOS support and other component checks.
export function socketCompatibility(cpu, motherboard) {
  const cpuSocket = cpu ? builderSpecs(cpu, "cpu").socket : "unknown";
  const motherboardSocket = motherboard
    ? builderSpecs(motherboard, "mb").socket
    : "unknown";
  const status =
    !cpu || !motherboard
      ? "incomplete"
      : cpuSocket === "unknown" || motherboardSocket === "unknown"
        ? "unknown"
        : cpuSocket === motherboardSocket
          ? "compatible"
          : "incompatible";
  return { status, cpuSocket, motherboardSocket };
}

// Explicit retailer specifications only: missing information stays unknown.
// Shared by filters, product badges and catalog normalization (including cached SKUs).
export function builderSpecs(part, type) {
  // Server specs are canonical for API products. The parser below supports the
  // small offline reference catalog and old locally saved builds only.
  if (part.specs) {
    const s = part.specs;
    return {
      socket: s.socket || "unknown",
      memoryTypes: s.memory_type || [],
      platform: (s.platform || "unknown").toLowerCase(),
      color: s.color || "unknown",
      led: s.led || "unknown",
      interface:
        s.protocol?.startsWith("NVMe") || s.interface?.startsWith("PCIe")
          ? "NVMe"
          : s.interface?.startsWith("SATA")
            ? "SATA"
            : "unknown",
      formFactor: s.form_factor?.startsWith("M.2")
        ? "M.2"
        : s.form_factor || "unknown",
      pcie: s.interface?.match(/PCIe ([345])/u)?.[1] || "unknown",
      readSpeed: Number(s.read_speed) || null,
      writeSpeed: Number(s.write_speed) || null,
      rating: s.rating || "unknown",
      modular: s.modular || "unknown",
      atx: s.atx_version || "unknown",
      watt: Number(s.watt) || null,
    };
  }
  const name = String(part.product_name || part.name || "");
  const spec = String(part.spec_text || "");
  const text = `${name} / ${spec}`;
  const positive = (value) => {
    const n = Number(String(value ?? "").replaceAll(",", ""));
    return Number.isFinite(n) && n > 0 ? n : null;
  };
  const socketFromText = (value) => {
    const match =
      String(value || "").match(
        /(?:소켓\s*|socket\s*|\b)(LGA[ -]*\d{3,4}|AM[345]\+?|FM[12]\+?|s?TR[45X]+|sTRX4|sTR5|SP[35])(?![a-z0-9])/i,
      ) || String(value || "").match(/소켓\s*(\d{3,4})/i);
    return normalizeCpuSocket(match?.[1]);
  };
  // Explicit detailed specifications can correct stale imported metadata.
  // Structured fields take precedence over words in a marketing title.
  const socket =
    socketFromText(spec) ||
    normalizeCpuSocket(part.socket || part.cpu_socket) ||
    socketFromText(name);
  const memoryTypes = [
    ...new Set(
      (text.match(/\bDDR\s*[345]\b/gi) || []).map((v) =>
        v.replace(/\s/g, "").toUpperCase(),
      ),
    ),
  ];
  if (!memoryTypes.length) {
    const known = String(part.ram_type || part.type || "").toUpperCase();
    if (/^DDR[345]$/.test(known)) memoryTypes.push(known);
  }
  const platform = /^(AM|STR|TR)/i.test(socket)
    ? "amd"
    : /^LGA/i.test(socket)
      ? "intel"
      : /intel|인텔/i.test(text)
        ? "intel"
        : /\bAMD\b|라이젠|ryzen/i.test(text)
          ? "amd"
          : "unknown";
  const result = { socket: socket || "unknown", memoryTypes, platform };
  if (type === "ram") {
    const colorText = `${part.color || ""} ${name}`;
    const explicitColor =
      spec.match(/(?:방열판\s*)?색상\s*:\s*([^/]+)/i)?.[1] || "";
    const color = `${colorText} ${explicitColor}`;
    result.color = /white|화이트|흰색/i.test(color)
      ? "White"
      : /black|블랙|검정/i.test(color)
        ? "Black"
        : /silver|실버|은색/i.test(color)
          ? "Silver"
          : /red|레드|빨강/i.test(color)
            ? "Red"
            : "unknown";
    const led = part.led ?? part.rgb;
    const ledText = typeof led === "string" ? led : "";
    result.led =
      led === false ||
      /^(?:no|none|false|없음|미포함)$/i.test(ledText) ||
      /(?:LED|RGB)\s*[:：]?\s*(?:미포함|없음|미지원|no|none)|non[- ]?rgb|no[- ]?led/i.test(
        text,
      )
        ? "no"
        : led === true ||
            /^(?:yes|true)$/i.test(ledText) ||
            /\b(?:A?RGB|LED)\b|LED\s*[:：]?\s*(?:포함|지원)/i.test(
              `${ledText} ${text}`,
            )
          ? "yes"
          : "unknown";
  }
  if (type === "storage") {
    const storageText = `${part.interface || ""} ${part.form_factor || ""} ${text}`;
    result.interface = /\bSATA(?:[1236]|\b)/i.test(storageText)
      ? "SATA"
      : /NVMe|PCI[- ]?e/i.test(storageText)
        ? "NVMe"
        : "unknown";
    result.formFactor = /M[.]?2\b/i.test(storageText)
      ? "M.2"
      : /2[.]5\s*(?:인치|inch|["”])|\b2[.]5\b/i.test(storageText)
        ? "2.5-inch"
        : /\bU[.]2\b/i.test(storageText)
          ? "U.2"
          : /\b(?:AIC|HHHL)\b/i.test(storageText)
            ? "AIC"
            : "unknown";
    result.pcie =
      storageText.match(/PCI[- ]?e\s*(?:Gen\s*)?([345])[.]?0?/i)?.[1] ||
      "unknown";
    for (const [key, pattern] of [
      [
        "readSpeed",
        /(?:순차\s*읽기|sequential\s*read|읽기|read)\s*(?:속도)?\s*[:：]?\s*(?:최대|up to)?\s*([\d,.]+)\s*(GB\/s|MB\/s)/i,
      ],
      [
        "writeSpeed",
        /(?:순차\s*쓰기|sequential\s*write|쓰기|write)\s*(?:속도)?\s*[:：]?\s*(?:최대|up to)?\s*([\d,.]+)\s*(GB\/s|MB\/s)/i,
      ],
    ]) {
      const m = text.match(pattern);
      result[key] =
        positive(part[key === "readSpeed" ? "read_speed" : "write_speed"]) ||
        (m ? positive(m[1]) * (/^GB/i.test(m[2]) ? 1000 : 1) : null);
    }
  }
  if (type === "psu") {
    const ratings = [
      ["Titanium", /titanium|티타늄/i],
      ["Platinum", /platinum|플래티넘|플래티늄/i],
      ["Gold", /gold|골드/i],
      ["Silver", /silver|실버/i],
      ["Bronze", /bronze|브론즈/i],
      ["Standard", /standard|스탠다드|스탠더드|white/i],
    ];
    // Cybenetics ETA/LAMBDA grades are a separate certification system.
    const cert =
      spec.match(/80\s*(?:PLUS|\+)\s*([^/]+)/i)?.[1] ||
      name.match(/80\s*(?:PLUS|\+)\s*([^/]+)/i)?.[1] ||
      part.rating ||
      part.efficiency ||
      (/(?:ETA|LAMBDA|cybenetics)/i.test(name) ? "" : name);
    result.rating =
      ratings.find(([, pattern]) => pattern.test(cert))?.[0] || "unknown";
    const cables = `${part.modular || ""} ${text}`;
    result.modular = /semi|세미/i.test(cables)
      ? "Semi"
      : /non[- ]?modular|고정|일체형/i.test(cables)
        ? "Fixed"
        : /full|풀모듈러|풀 모듈러/i.test(cables)
          ? "Full"
          : "unknown";
    result.atx =
      String(part.atx_version || "").match(/^(3[.][01]|2[.]\d+)$/)?.[1] ||
      text.match(/ATX\s*(3[.][01]|2[.]\d+)\b/i)?.[1] ||
      "unknown";
    result.formFactor = /SFX[- ]?L/i.test(text)
      ? "SFX-L"
      : /\bSFX\b/i.test(text)
        ? "SFX"
        : /\bTFX\b/i.test(text)
          ? "TFX"
          : /\bATX/i.test(text)
            ? "ATX"
            : "unknown";
    result.watt =
      positive(name.match(/\b(\d{3,4})\s*W\b/i)?.[1]) ||
      positive(spec.match(/정격\s*출력\s*[:：]?\s*(\d{3,4})\s*W/i)?.[1]) ||
      positive(spec.match(/\b(\d{3,4})\s*W\b/i)?.[1]) ||
      positive(part.watt);
  }
  return result;
}

export const BUILDER_SPEED_RANGES = [
  ["1-599", "600 미만"],
  ["600-2999", "600–2,999"],
  ["3000-6999", "3,000–6,999"],
  ["7000-9999", "7,000–9,999"],
  ["10000+", "10,000 이상"],
  ["unknown", "미확인"],
];
export const BUILDER_WATT_RANGES = [
  ["1-499", "500W 미만"],
  ["500-599", "500W대"],
  ["600-699", "600W대"],
  ["700-799", "700W대"],
  ["800-899", "800W대"],
  ["900-999", "900W대"],
  ["1000-1199", "1,000–1,199W"],
  ["1200+", "1,200W 이상"],
  ["unknown", "미확인"],
];
export function builderRange(value, options) {
  if (!(value > 0)) return "unknown";
  return (
    options.find(([key]) => {
      if (key === "unknown") return false;
      const [min, max] = key.split("-").map(Number);
      return key.endsWith("+")
        ? value >= Number(key.slice(0, -1))
        : value >= min && value <= max;
    })?.[0] || "unknown"
  );
}
