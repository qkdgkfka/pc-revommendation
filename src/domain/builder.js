import {
  builderSpecs,
  socketCompatibility,
  BUILDER_SPEED_RANGES,
  BUILDER_WATT_RANGES,
  builderRange,
} from "./specs.js";
import { numeric, storageTbValue } from "./performance.js";
import * as productDomain from "./products.js";
const {
  money,
  escapeHtml,
  shopSearchUrl,
  queryString,
  partUrl,
  gpuBrand,
  withPartType,
  fullProductName,
  productManufacturer,
  displayName,
  partMeta,
  catalogKey,
  catalogMatchScore,
  mergeCatalogPrices,
  seedCatalogItems,
  effectivePrice,
  marketName,
  priceProvenance,
  priceProvenanceHtml,
  catalogPriceLabel,
  uniqueProducts,
  bestProductImageUrl,
  normSpecValue,
  cpuVendor,
  cpuCores,
  cpuThreads,
  gpuModelToken,
  gpuSeriesToken,
  gpuSeriesGroups,
  preferredGpuProductForModel,
  psuRating,
  valueSet,
  rangeLabel,
  normalizeSearchText,
  productBadges,
  workFillClass,
  compatibilityHtml,
  BUILDER_PARTS,
  BUILDER_META,
} = productDomain;
export function createBuilderDomain(state) {
  const baseCatalogFor = (type) => state.catalogs[type] || [];
  const browseStateFor = (type) =>
    state.browse[type] || { items: [], loaded: false };
  const activeDanawaProducts = (type) => browseStateFor(type).items || [];
  const browseProductsFor = (type) => {
    const browse = browseStateFor(type);
    return browse.loaded && browse.requestKey === builderSearchKey(type)
      ? browse.items
      : [];
  };
  const allKnownProductsFor = (type) =>
    uniqueProducts([
      ...activeDanawaProducts(type),
      ...Object.values(state.pinned[type] || {}),
      ...baseCatalogFor(type),
    ]);
  const findPartById = (type, id) =>
    allKnownProductsFor(type).find((p) => p.id === id);
  const findCatalogItemById = (id) =>
    BUILDER_PARTS.map((p) => findPartById(p.key, id)).find(Boolean);
  const expandedBuilderCatalog = () => false;
  const builderCatalogFor = browseProductsFor;
  const rawCatalogFor = builderCatalogFor;
  function compatibleMbs(cpu, ram, pool = allKnownProductsFor("mb")) {
    const socket = normSpecValue(cpu?.socket);
    const ramType = normSpecValue(ram?.type || ram?.ram_type);
    const filtered = (pool || []).filter((mb) => {
      const mbSocket = normSpecValue(mb.socket);
      const mbRam = normSpecValue(mb.ram_type);
      const socketOk = !socket || !mbSocket || socket === mbSocket;
      const ramOk = !ramType || !mbRam || ramType === mbRam;
      return socketOk && ramOk;
    });
    return filtered;
  }

  function builderSearchKey(
    type,
    query = state.productQuery,
    source = state.productSource,
  ) {
    const filters = Object.entries(state.builderFilters[type] || {})
      .filter(([, values]) => values.length)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, values]) => [key, [...values].sort()]);
    return JSON.stringify([
      type,
      String(query || "").trim(),
      source,
      state.productSort || "popular",
      filters,
    ]);
  }
  function builderFilterDefs(type) {
    if (type !== "gpu" && state.productFacets?.[type])
      return state.productFacets[type];
    const items = rawCatalogFor(type);
    const options = (values) =>
      [
        ...new Set(
          values
            .filter((v) => v != null && v !== "" && v !== "unknown")
            .map(String),
        ),
      ].map((v) => [v, v]);
    const fieldOptions = (key, defaults = []) => [
      ...options([
        ...defaults,
        ...items.map((p) => builderSpecs(p, type)[key]),
      ]),
      ["unknown", "미확인"],
    ];
    const sockets = fieldOptions("socket", [
      "AM5",
      "AM4",
      "LGA1851",
      "LGA1700",
      "LGA1200",
      "LGA1151",
      "STR5",
      "STRX4",
    ]);
    const brandNames = [...items, ...baseCatalogFor(type)].map(
      (p) => productManufacturer(p).label,
    );
    const popularBrands = [
      "삼성",
      "SK하이닉스",
      "마이크론",
      "WD",
      "Seagate",
      "ESSENCORE KLEVV",
      "G.SKILL",
      "CORSAIR",
      "TeamGroup",
      "Kingston",
      "Lexar",
      "마이크로닉스",
      "FSP",
      "Seasonic",
      "SuperFlower",
      "ASUS",
      "MSI",
      "GIGABYTE",
      "ASRock",
    ];
    const brands = options(brandNames).sort((a, b) => {
      const rank = (value) =>
        popularBrands.includes(value) ? popularBrands.indexOf(value) : 100;
      return rank(a[0]) - rank(b[0]) || a[1].localeCompare(b[1], "ko");
    });
    const memory = [
      ["DDR5", "DDR5"],
      ["DDR4", "DDR4"],
      ["DDR3", "DDR3"],
      ["unknown", "미확인"],
    ];
    if (type === "cpu") {
      return [
        {
          key: "vendor",
          label: "제조사",
          options: [
            ["amd", "AMD"],
            ["intel", "Intel"],
          ],
        },
        { key: "socket", label: "소켓", options: sockets },
        { key: "ramType", label: "메모리 규격", options: memory },
        {
          key: "cores",
          label: "코어 수",
          options: [
            ["4-6", "4-6코어"],
            ["8-10", "8-10코어"],
            ["12-16", "12-16코어"],
            ["20-32", "20코어 이상"],
          ],
        },
        {
          key: "threads",
          label: "스레드 수",
          options: [
            ["8-12", "8-12스레드"],
            ["14-20", "14-20스레드"],
            ["24-32", "24스레드 이상"],
          ],
        },
      ];
    }
    if (type === "gpu") {
      return [
        {
          key: "vendor",
          label: "GPU 칩 제조사",
          options: [
            ["nvidia", "NVIDIA"],
            ["amd", "AMD"],
          ],
        },
        {
          key: "model",
          label: "GPU 모델",
          options: valueSet(items, gpuModelToken).map((v) => [v, v]),
        },
        {
          key: "vram",
          label: "VRAM",
          options: valueSet(items, (p) => (p.vram ? `${p.vram}` : ""))
            .sort((a, b) => Number(a) - Number(b))
            .map((v) => [v, `${v}GB`]),
        },
        {
          key: "maker",
          label: "그래픽카드 브랜드",
          options: [
            ["msi", "MSI"],
            ["gigabyte", "Gigabyte"],
            ["palit", "Palit"],
            ["colorful", "Colorful"],
            ["asus", "ASUS"],
            ["zotac", "ZOTAC"],
            ["galax", "GALAX"],
            ["emtek", "Emtek"],
            ["sapphire", "SAPPHIRE"],
            ["powercolor", "PowerColor"],
            ["xfx", "XFX"],
            ["asrock", "ASRock"],
            ["inno3d", "INNO3D"],
          ],
        },
      ];
    }
    if (type === "mb") {
      return [
        {
          key: "platform",
          label: "플랫폼",
          options: [
            ["amd", "AMD"],
            ["intel", "Intel"],
          ],
        },
        { key: "socket", label: "소켓", options: sockets },
        { key: "ramType", label: "메모리 규격", options: memory },
        { key: "brand", label: "제조사", options: brands },
      ];
    }
    if (type === "ram") {
      return [
        { key: "type", label: "메모리 규격", options: memory },
        {
          key: "color",
          label: "색상",
          options: [
            ["White", "화이트"],
            ["Black", "블랙"],
            ["Silver", "실버"],
            ["Red", "레드"],
            ["unknown", "미확인"],
          ],
        },
        {
          key: "led",
          label: "LED / RGB",
          options: [
            ["yes", "LED 포함"],
            ["no", "LED 없음"],
            ["unknown", "미확인"],
          ],
        },
        {
          key: "gb",
          label: "용량",
          options: valueSet(items, (p) => p.gb)
            .sort((a, b) => Number(a) - Number(b))
            .map((v) => [String(v), `${v}GB`]),
        },
        {
          key: "speed",
          label: "속도",
          options: valueSet(items, (p) => p.speed)
            .sort((a, b) => Number(a) - Number(b))
            .map((v) => [String(v), `${v}MHz`]),
        },
        { key: "brand", label: "제조사", options: brands },
      ];
    }
    if (type === "storage") {
      return [
        {
          key: "capacity",
          label: "용량",
          options: valueSet(
            items,
            (p) => p.capacity || storageTbValue(p) * 1000,
          )
            .sort((a, b) => {
              const common = [500, 512, 1000, 2000, 4000, 8000, 250, 256];
              const rank = (v) =>
                common.includes(Number(v))
                  ? common.indexOf(Number(v))
                  : 100 + Number(v);
              return rank(a) - rank(b);
            })
            .map((v) => [
              String(v),
              Number(v) >= 1000 ? `${Number(v) / 1000}TB` : `${v}GB`,
            ]),
        },
        {
          key: "interface",
          label: "인터페이스",
          options: [
            ["NVMe", "NVMe / PCIe"],
            ["SATA", "SATA"],
            ["unknown", "미확인"],
          ],
        },
        {
          key: "formFactor",
          label: "폼팩터",
          options: [
            ["M.2", "M.2"],
            ["2.5-inch", "2.5인치"],
            ["U.2", "U.2"],
            ["AIC", "PCIe 카드"],
            ["unknown", "미확인"],
          ],
        },
        {
          key: "pcie",
          label: "PCIe 세대",
          options: [
            ["5", "PCIe 5.0"],
            ["4", "PCIe 4.0"],
            ["3", "PCIe 3.0"],
            ["unknown", "미확인 / 해당 없음"],
          ],
        },
        {
          key: "readSpeed",
          label: "순차 읽기",
          unit: "MB/s",
          options: BUILDER_SPEED_RANGES,
        },
        {
          key: "writeSpeed",
          label: "순차 쓰기",
          unit: "MB/s",
          options: BUILDER_SPEED_RANGES,
        },
        { key: "brand", label: "제조사", options: brands },
      ];
    }
    if (type === "hdd") {
      return [
        {
          key: "capacity",
          label: "용량",
          options: valueSet(items, (p) => p.capacity)
            .sort((a, b) => Number(a) - Number(b))
            .map((v) => [
              String(v),
              Number(v) >= 1000 ? `${Number(v) / 1000}TB` : `${v}GB`,
            ]),
        },
        {
          key: "rpm",
          label: "회전수",
          options: valueSet(items, (p) => p.rpm)
            .sort((a, b) => Number(a) - Number(b))
            .map((v) => [String(v), v ? `${v}RPM` : "추가 안 함"]),
        },
        { key: "brand", label: "제조사", options: brands },
      ];
    }
    if (type === "psu") {
      return [
        { key: "watt", label: "정격 출력", options: BUILDER_WATT_RANGES },
        {
          key: "rating",
          label: "80 PLUS 인증",
          options: [
            ...options([
              "Standard",
              "Bronze",
              "Silver",
              "Gold",
              "Platinum",
              "Titanium",
            ]),
            ["unknown", "미확인"],
          ],
        },
        {
          key: "modular",
          label: "케이블 연결",
          options: [
            ["Full", "풀모듈러"],
            ["Semi", "세미모듈러"],
            ["Fixed", "고정 케이블"],
            ["unknown", "미확인"],
          ],
        },
        {
          key: "atx",
          label: "ATX 버전",
          options: [
            ["3.1", "ATX 3.1"],
            ["3.0", "ATX 3.0"],
            ["2.x", "ATX 2.x"],
            ["unknown", "미확인"],
          ],
        },
        {
          key: "formFactor",
          label: "파워 규격",
          options: [
            ["ATX", "ATX"],
            ["SFX", "SFX"],
            ["SFX-L", "SFX-L"],
            ["TFX", "TFX"],
            ["unknown", "미확인"],
          ],
        },
        { key: "brand", label: "제조사", options: brands },
      ];
    }
    if (type === "case") {
      return [
        {
          key: "formFactor",
          label: "규격",
          options: valueSet(items, (p) => p.form_factor).map((v) => [v, v]),
        },
        { key: "brand", label: "제조사", options: brands },
        {
          key: "color",
          label: "색상",
          options: valueSet(items, (p) => p.color).map((v) => [v, v]),
        },
      ];
    }
    if (type === "software") {
      return [
        { key: "brand", label: "제조사", options: brands },
        {
          key: "license",
          label: "라이선스",
          options: valueSet(items, (p) => p.license).map((v) => [
            v,
            v === "none" ? "추가 안 함" : v,
          ]),
        },
      ];
    }
    return [];
  }
  function filterValues(type, key) {
    return (state.builderFilters[type] || {})[key] || [];
  }
  function filterHas(type, key, value) {
    return filterValues(type, key).includes(String(value));
  }
  function productMatchesFilters(type, part) {
    if (type !== "gpu" && part.specs && state.productFacets?.[type]) {
      return Object.entries(state.builderFilters[type] || {}).every(
        ([key, values]) => {
          if (!values.length) return true;
          const actual = Array.isArray(part.specs[key])
            ? part.specs[key]
            : [String(part.specs[key] ?? "")];
          return values.some(
            (v) =>
              actual.includes(v) ||
              (key === "protocol" &&
                v === "NVMe" &&
                actual.some((a) => a.startsWith("NVMe"))),
          );
        },
      );
    }
    const f = state.builderFilters[type] || {};
    const specs = builderSpecs(part, type);
    const has = (key) => Array.isArray(f[key]) && f[key].length > 0;
    const includes = (key, value) =>
      !has(key) || f[key].includes(String(value));
    const memoryMatches = (key) =>
      !has(key) ||
      f[key].some((v) =>
        specs.memoryTypes.length
          ? specs.memoryTypes.includes(v)
          : v === "unknown",
      );
    if (type === "cpu") {
      if (!memoryMatches("ramType")) return false;
      if (
        !includes(
          "vendor",
          specs.platform !== "unknown" ? specs.platform : cpuVendor(part),
        )
      )
        return false;
      if (!includes("socket", specs.socket)) return false;
      if (
        has("cores") &&
        !f.cores.includes(
          rangeLabel(cpuCores(part), [
            { label: "4-6", min: 4, max: 6 },
            { label: "8-10", min: 8, max: 10 },
            { label: "12-16", min: 12, max: 16 },
            { label: "20-32", min: 20, max: 64 },
          ]),
        )
      )
        return false;
      if (
        has("threads") &&
        !f.threads.includes(
          rangeLabel(cpuThreads(part), [
            { label: "8-12", min: 8, max: 12 },
            { label: "14-20", min: 14, max: 20 },
            { label: "24-32", min: 24, max: 64 },
          ]),
        )
      )
        return false;
    }
    if (type === "gpu") {
      if (!includes("vendor", gpuBrand(part))) return false;
      if (!includes("series", gpuSeriesToken(part))) return false;
      if (!includes("model", gpuModelToken(part))) return false;
      if (!includes("vram", part.vram)) return false;
      if (has("maker")) {
        const makerNames = {
          msi: ["msi"],
          gigabyte: ["gigabyte", "기가바이트"],
          palit: ["palit", "팰릿"],
          colorful: ["colorful", "컬러풀"],
          asus: ["asus", "아수스"],
          zotac: ["zotac", "조텍"],
          galax: ["galax", "갤럭시"],
          emtek: ["emtek", "이엠텍"],
          sapphire: ["sapphire", "사파이어"],
          powercolor: ["powercolor", "파워컬러"],
          xfx: ["xfx"],
          asrock: ["asrock", "애즈락"],
          inno3d: ["inno3d", "이노3d"],
        };
        const productName = String(
          [part.name, part.product_name, part.brand, part.manufacturer]
            .filter(Boolean)
            .join(" "),
        ).toLowerCase();
        if (
          !f.maker.some((maker) =>
            (makerNames[maker] || [maker]).some((name) =>
              productName.includes(name),
            ),
          )
        )
          return false;
      }
    }
    if (type === "mb") {
      if (!includes("socket", specs.socket)) return false;
      if (!includes("platform", specs.platform)) return false;
      if (!memoryMatches("ramType")) return false;
      if (!includes("brand", productManufacturer(part).label)) return false;
    }
    if (type === "ram") {
      if (!memoryMatches("type")) return false;
      if (!includes("color", specs.color) || !includes("led", specs.led))
        return false;
      if (!includes("gb", part.gb)) return false;
      if (!includes("speed", part.speed)) return false;
      if (!includes("brand", productManufacturer(part).label)) return false;
    }
    if (type === "storage") {
      const capacity = part.capacity || storageTbValue(part) * 1000;
      if (!includes("capacity", capacity)) return false;
      if (
        !includes("interface", specs.interface) ||
        !includes("formFactor", specs.formFactor) ||
        !includes("pcie", specs.pcie)
      )
        return false;
      if (
        !includes(
          "readSpeed",
          builderRange(specs.readSpeed, BUILDER_SPEED_RANGES),
        )
      )
        return false;
      if (
        !includes(
          "writeSpeed",
          builderRange(specs.writeSpeed, BUILDER_SPEED_RANGES),
        )
      )
        return false;
      if (!includes("brand", productManufacturer(part).label)) return false;
    }
    if (type === "hdd") {
      if (!includes("capacity", part.capacity)) return false;
      if (!includes("rpm", part.rpm)) return false;
      if (!includes("brand", productManufacturer(part).label)) return false;
    }
    if (type === "psu") {
      if (!includes("watt", builderRange(specs.watt, BUILDER_WATT_RANGES)))
        return false;
      if (
        !includes("rating", specs.rating) ||
        !includes("modular", specs.modular) ||
        !includes("formFactor", specs.formFactor)
      )
        return false;
      if (!includes("atx", specs.atx.startsWith("2.") ? "2.x" : specs.atx))
        return false;
      if (!includes("brand", productManufacturer(part).label)) return false;
    }
    if (type === "case") {
      if (!includes("formFactor", part.form_factor)) return false;
      if (!includes("brand", productManufacturer(part).label)) return false;
      if (!includes("color", part.color)) return false;
    }
    if (type === "software") {
      if (!includes("brand", productManufacturer(part).label)) return false;
      if (!includes("license", part.license)) return false;
    }
    const q = normalizeSearchText(state.productQuery);
    const browse = browseStateFor(type);
    // Once the server has returned a live result page for this exact query,
    // Danawa has already performed the text search.  Re-filtering it locally
    // would incorrectly hide Korean/English model-name variants.
    const queryAlreadyApplied =
      q &&
      browse.loaded &&
      browse.status !== "unavailable" &&
      browse.requestKey === builderSearchKey(type) &&
      normalizeSearchText(browse.query) === q;
    if (q && !queryAlreadyApplied) {
      const haystack = normalizeSearchText(
        [
          part.name,
          displayName(part),
          partMeta(part, type),
          gpuModelToken(part),
        ].join(" "),
      );
      if (!q.split(" ").every((term) => haystack.includes(term))) return false;
    }
    return true;
  }
  function filteredProducts(type = state.builderPart) {
    const products = rawCatalogFor(type).filter((part) =>
      productMatchesFilters(type, part),
    );
    if (state.productSort === "name")
      products.sort((a, b) =>
        displayName(a).localeCompare(displayName(b), "ko"),
      );
    if (["price_asc", "price_desc"].includes(state.productSort)) {
      products.sort((a, b) => {
        const aPrice = effectivePrice(a),
          bPrice = effectivePrice(b);
        if (aPrice == null) return bPrice == null ? 0 : 1;
        if (bPrice == null) return -1;
        return state.productSort === "price_asc"
          ? aPrice - bPrice
          : bPrice - aPrice;
      });
    }
    return products;
  }
  return {
    builderSearchKey,
    builderFilterDefs,
    filterValues,
    filterHas,
    productMatchesFilters,
    filteredProducts,
    baseCatalogFor,
    browseStateFor,
    activeDanawaProducts,
    browseProductsFor,
    allKnownProductsFor,
    findPartById,
    findCatalogItemById,
    expandedBuilderCatalog,
    builderCatalogFor,
    rawCatalogFor,
    compatibleMbs,
  };
}
