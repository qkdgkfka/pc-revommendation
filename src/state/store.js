import { createBuilderDomain } from "../domain/builder.js";
import { referenceCatalogs } from "../domain/referenceCatalog.js";
import {
  GAME_OPTIONS,
  WORK_PROFILES,
  GAME_CATEGORIES,
} from "../domain/options.js";
import {
  BUILDER_META,
  BUILDER_PARTS,
  withPartType,
  seedCatalogItems,
  uniqueProducts,
  priceProvenance,
  effectivePrice,
  applyPriceObservation,
  gpuSeriesToken,
  marketName,
} from "../domain/products.js";
import { customFpsKey, fpsRequestPart } from "../domain/performance.js";
import {
  createRequestManager,
  RequestError,
  errorMessage,
} from "./requests.js";
const recommendationDefaults = {
  budget: 2000000,
  budgetMin: 1000000,
  budgetMax: 2000000,
  resolution: "1080",
  refresh: 60,
  gpu_pref: "nopref",
  gpu_brands: [],
  game: "cyberpunk2077",
  gameCategory: "aaa",
  panelMode: "game",
  panelWork: "video_4k",
};
export function initialState(catalogs = referenceCatalogs) {
  return {
    activeView: "ai",
    ...recommendationDefaults,
    csMode: "game",
    csRes: "1080",
    csGame: "cyberpunk2077",
    csGameCategory: "aaa",
    csWork: "video_4k",
    csGpuMakers: [],
    builderPart: "cpu",
    builderFilters: {},
    productQuery: "",
    productDraft: "",
    productQueries: {},
    productDrafts: {},
    productSource: "all",
    productSort: "popular",
    selected: {},
    pinned: {},
    browse: {},
    productFacets: {},
    catalogs: Object.fromEntries(
      Object.entries(catalogs).map(([type, items]) => [
        type,
        seedCatalogItems(withPartType(structuredClone(items), type)),
      ]),
    ),
    games: structuredClone(GAME_OPTIONS),
    workProfiles: structuredClone(WORK_PROFILES),
    lastRecommendation: null,
    recommendation: { loading: false, error: "", kind: "" },
    fps: { key: "", loading: false, data: null, error: "", kind: "" },
    catalogError: "",
  };
}
export function gameCategoryFor(gameId, games = GAME_OPTIONS) {
  const item = games.find((game) => game.id === gameId);
  if (item?.category && GAME_CATEGORIES.some((c) => c.id === item.category))
    return item.category;
  const group = String(item?.group || "").toLowerCase();
  return /fps|경쟁/.test(group)
    ? "fps"
    : /오픈월드|서브컬쳐/.test(group)
      ? "openworld"
      : /aaa|goty/.test(group)
        ? "aaa"
        : "game";
}
export function createAppStore(options = {}) {
  let state = initialState(options.catalogs),
    listeners = new Set();
  const requests = createRequestManager(),
    fpsCache = new Map();
  const fetcher = options.fetch || ((...args) => globalThis.fetch(...args));
  const base = options.baseUrl || "";
  const getState = () => state,
    domain = () => createBuilderDomain(state);
  const publish = (patch) => {
    state = { ...state, ...patch };
    listeners.forEach((listener) => listener());
  };
  const patchBrowse = (type, patch) =>
    publish({
      browse: {
        ...state.browse,
        [type]: { ...(state.browse[type] || {}), ...patch },
      },
    });
  const cancelFps = () => {
    requests.cancel("fps");
    publish({ fps: { ...state.fps, loading: false } });
  };
  function update(patch) {
    if (
      ["productQuery", "productSource", "productSort", "builderFilters"].some(
        (k) => k in patch,
      )
    ) {
      for (const [type, browse] of Object.entries(state.browse))
        if (browse.loading) {
          requests.cancel("products:" + type);
          patch.browse = {
            ...(patch.browse || state.browse),
            [type]: { ...browse, loading: false },
          };
        }
    }
    if (["csGame", "csRes", "csMode", "refresh"].some((k) => k in patch))
      cancelFps();
    if (
      Object.keys(recommendationDefaults).some((k) => k in patch) &&
      state.recommendation.loading
    ) {
      requests.cancel("recommendation");
      patch.recommendation = {
        loading: false,
        error: "요청을 취소했습니다.",
        kind: "cancelled",
      };
    }
    publish(patch);
  }
  async function json(url, signal, body) {
    const response = await fetcher(base + url, {
      signal,
      ...(body
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        : {}),
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new RequestError(
        "upstream",
        "서버 응답 형식을 확인하지 못했습니다.",
      );
    }
    if (!response.ok || data?.ok === false)
      throw new RequestError(
        data?.error_kind === "timeout" ? "timeout" : "upstream",
        data?.error ||
          `판매처 연결에 실패했습니다 (HTTP ${response.status || "오류"}).`,
      );
    return data;
  }
  function loadProducts(type = state.builderPart, opts = {}) {
    if (!BUILDER_META[type]) return Promise.resolve();
    const query = String(opts.query ?? state.productQuery).trim(),
      source = opts.source || state.productSource;
    const requestKey = domain().builderSearchKey(type, query, source),
      browse = state.browse[type] || {};
    const append = Boolean(
      opts.append && browse.loaded && browse.requestKey === requestKey,
    );
    if (append && !browse.hasMore) return Promise.resolve();
    const page = append ? Math.max(1, Number(browse.page || 0) + 1) : 1;
    const params = new URLSearchParams({
      type,
      query,
      source,
      page: String(page),
      limit: "50",
      sort: state.productSort || "popular",
    });
    if (append && browse.cursor) params.set("cursor", browse.cursor);
    if (type !== "gpu")
      params.set("filters", JSON.stringify(state.builderFilters[type] || {}));
    else
      ["series", "model", "maker", "vendor", "vram"].forEach((key) => {
        const values = domain().filterValues(type, key);
        if (values.length) params.set(key, values.join(","));
      });
    if (opts.force) params.set("refresh", "1");
    const entry = requests.start(
      "products:" + type,
      params.toString(),
      (signal) => json("/api/products?" + params, signal),
      options.timeout ?? 30000,
    );
    if (entry.task) return entry.task;
    patchBrowse(type, {
      loading: true,
      error: "",
      errorKind: "",
      pendingKey: requestKey,
      ...(!append ? { items: [], loaded: false, hasMore: false } : {}),
    });
    entry.task = entry.promise
      .then((data) => {
        if (!entry.current()) return;
        const items = withPartType(data.items || [], type),
          unavailable = data.status === "unavailable";
        if (data.facets && type !== "gpu")
          publish({
            productFacets: { ...state.productFacets, [type]: data.facets },
          });
        patchBrowse(type, {
          items:
            append && !data.reset
              ? uniqueProducts([...(state.browse[type]?.items || []), ...items])
              : uniqueProducts(items),
          page: data.reset ? 1 : page,
          cursor: data.cursor || "",
          requestKey,
          query,
          requestedSource: source,
          hasMore: Boolean(data.has_more),
          partial: Boolean(data.partial),
          total: data.total == null ? null : Number(data.total),
          status: data.status || (items.length ? "live" : "empty"),
          sourceStatus: data.source_status || {},
          source,
          sortLabel: data.sort_label || "검색처 기본순",
          loaded: true,
          loadedAt: Date.now(),
          error: unavailable
            ? data.error_kind === "timeout"
              ? errorMessage(new RequestError("timeout", ""))
              : `${marketName(source)} 검색에 연결하지 못했습니다.`
            : "",
          errorKind: unavailable
            ? data.error_kind === "timeout"
              ? "timeout"
              : "upstream"
            : "",
          loading: false,
        });
      })
      .catch((error) => {
        if (entry.current())
          patchBrowse(type, {
            loading: false,
            error: errorMessage(error),
            errorKind: error.kind || "upstream",
            ...(!append
              ? {
                  items: [],
                  loaded: false,
                  status: "unavailable",
                  hasMore: false,
                }
              : {}),
          });
      });
    return entry.task;
  }
  function setPart(type) {
    if (!BUILDER_META[type]) return;
    if (type === state.builderPart) {
      void loadProducts(type);
      return;
    }
    const previous = state.builderPart,
      productQueries = {
        ...state.productQueries,
        [previous]: state.productQuery,
      },
      productDrafts = {
        ...state.productDrafts,
        [previous]: state.productDraft,
      };
    requests.cancel("products:" + previous);
    if (state.browse[previous]?.loading)
      patchBrowse(previous, { loading: false });
    update({
      builderPart: type,
      productQueries,
      productDrafts,
      productQuery: productQueries[type] || "",
      productDraft: productDrafts[type] ?? productQueries[type] ?? "",
    });
    void loadProducts(type);
  }
  function toggleFilter(type, key, value) {
    const current = new Set(domain().filterValues(type, key)),
      v = String(value);
    current.has(v) ? current.delete(v) : current.add(v);
    update({
      builderFilters: {
        ...state.builderFilters,
        [type]: { ...(state.builderFilters[type] || {}), [key]: [...current] },
      },
      ...(type === "gpu" && key === "maker"
        ? { csGpuMakers: [...current] }
        : {}),
    });
    void loadProducts(type);
  }
  function selectGpuSeries(label) {
    if (state.builderPart !== "gpu") return;
    update({
      builderFilters: {
        ...state.builderFilters,
        gpu: {
          ...(state.builderFilters.gpu || {}),
          series: [label.replace(/\s+Series$/i, "")],
          model: [],
        },
      },
    });
    void loadProducts("gpu");
  }
  function selectGpuModel(model) {
    update({
      builderFilters: {
        ...state.builderFilters,
        gpu: {
          ...(state.builderFilters.gpu || {}),
          model: [model],
          series: [gpuSeriesToken({ chipset: model })],
        },
      },
    });
    void loadProducts("gpu");
  }
  function resetFilters() {
    update({
      builderFilters: { ...state.builderFilters, [state.builderPart]: {} },
      ...(state.builderPart === "gpu" ? { csGpuMakers: [] } : {}),
    });
    void loadProducts();
  }
  function selectProduct(type, partOrId) {
    const part =
      typeof partOrId === "string"
        ? domain().findPartById(type, partOrId)
        : withPartType([partOrId], type)[0];
    if (!part) return;
    if (["cpu", "gpu", "ram"].includes(type)) cancelFps();
    requests.cancel("prices");
    publish({
      selected: { ...state.selected, [type]: part },
      pinned: {
        ...state.pinned,
        [type]: { ...(state.pinned[type] || {}), [part.id]: part },
      },
    });
    void refreshSelectedPrices();
  }
  function clearProduct(type) {
    if (["cpu", "gpu", "ram"].includes(type)) cancelFps();
    requests.cancel("prices");
    publish({ selected: { ...state.selected, [type]: null } });
    void refreshSelectedPrices();
  }
  function clearBuild() {
    cancelFps();
    requests.cancel("prices");
    publish({ selected: {} });
  }
  function refreshSelectedPrices() {
    const wanted = Object.entries(state.selected)
      .filter(
        ([, part]) =>
          part &&
          !["verified", "cached", "stale"].includes(
            priceProvenance(part).status,
          ) &&
          effectivePrice(part) !== 0,
      )
      .map(([type, p]) => ({
        id: p.id,
        type,
        name: p.name,
        base_price: p.base_price ?? p.price ?? null,
      }));
    if (!wanted.length) return Promise.resolve();
    const payload = {
      items: wanted,
      gpu_brands: state.csGpuMakers,
      source: state.productSource,
    };
    const entry = requests.start(
      "prices",
      JSON.stringify(payload),
      (signal) => json("/api/price-lookup", signal, payload),
      options.timeout ?? 20000,
    );
    if (entry.task) return entry.task;
    entry.task = entry.promise
      .then((data) => {
        if (!entry.current()) return;
        const selected = { ...state.selected },
          pinned = { ...state.pinned };
        for (const result of data.results || []) {
          const type = Object.keys(selected).find(
            (key) => selected[key]?.id === result.id,
          );
          if (!type) continue;
          const part = applyPriceObservation({ ...selected[type] }, result);
          selected[type] = part;
          pinned[type] = { ...(pinned[type] || {}), [part.id]: part };
        }
        publish({ selected, pinned });
      })
      .catch(() => {});
    return entry.task;
  }
  function estimateFps(force = false) {
    const { gpu, cpu, ram } = state.selected;
    if (state.csMode !== "game" || !gpu || !cpu || !ram) {
      cancelFps();
      publish({
        fps: { key: "", data: null, loading: false, error: "", kind: "" },
      });
      return Promise.resolve();
    }
    const key = customFpsKey(
      gpu,
      cpu,
      ram,
      state.csGame,
      state.csRes,
      state.refresh,
    );
    if (!force && fpsCache.has(key)) {
      publish({
        fps: {
          key,
          data: fpsCache.get(key),
          loading: false,
          error: "",
          kind: "",
        },
      });
      return Promise.resolve();
    }
    const payload = {
      gpu: fpsRequestPart(gpu),
      cpu: fpsRequestPart(cpu),
      ram: fpsRequestPart(ram),
      game: state.csGame,
      resolution: state.csRes,
      refresh: state.refresh,
      tier: "mid",
    };
    const entry = requests.start(
      "fps",
      key,
      (signal) => json("/api/estimate-fps", signal, payload),
      options.timeout ?? 20000,
    );
    if (entry.task) return entry.task;
    publish({ fps: { key, data: null, loading: true, error: "", kind: "" } });
    entry.task = entry.promise
      .then((data) => {
        if (!entry.current()) return;
        if (!data.fps)
          throw new RequestError("empty", "해당 구성의 FPS 자료가 없습니다.");
        fpsCache.set(key, data.fps);
        publish({
          fps: { key, data: data.fps, loading: false, error: "", kind: "" },
        });
      })
      .catch((error) => {
        if (entry.current())
          publish({
            fps: {
              key,
              data: null,
              loading: false,
              error: errorMessage(error),
              kind: error.kind || "upstream",
            },
          });
      });
    return entry.task;
  }
  function recommend() {
    const payload = {
      budget: state.budget,
      budget_min: state.budgetMin,
      budget_max: state.budgetMax,
      resolution: state.resolution,
      refresh: state.refresh,
      gpu_pref: state.gpu_pref,
      gpu_brands: state.gpu_brands,
      game: state.panelMode === "game" ? state.game : "cyberpunk2077",
      mode: state.panelMode,
      work_profile: state.panelWork,
    };
    const entry = requests.start(
      "recommendation",
      JSON.stringify(payload),
      (signal) => json("/api/recommend", signal, payload),
      options.timeout ?? 30000,
    );
    if (entry.task) return entry.task;
    publish({
      recommendation: { loading: true, error: "", kind: "" },
      lastRecommendation: null,
    });
    entry.task = entry.promise
      .then((data) => {
        if (!entry.current()) return;
        if (!data.results)
          throw new RequestError("empty", "서버 응답에 추천 결과가 없습니다.");
        publish({
          lastRecommendation: { ...data, input: data.input || payload },
          recommendation: { loading: false, error: "", kind: "" },
        });
      })
      .catch((error) => {
        if (entry.current())
          publish({
            recommendation: {
              loading: false,
              error: errorMessage(error),
              kind: error.kind || "upstream",
            },
          });
      });
    return entry.task;
  }
  function resetRecommendation() {
    requests.cancel("recommendation");
    requests.cancel("fps");
    publish({
      ...recommendationDefaults,
      gpu_brands: [],
      lastRecommendation: null,
      recommendation: { loading: false, error: "", kind: "" },
      fps: { ...state.fps, loading: false },
    });
  }
  function importRecommendation(tier) {
    const recommendation = state.lastRecommendation?.results?.[tier],
      parts = recommendation?.parts;
    if (
      !["gpu", "cpu", "ram", "mb", "storage", "psu"].every(
        (type) => parts?.[type]?.id,
      )
    ) {
      publish({
        recommendation: {
          loading: false,
          error: "가져올 추천 사양을 찾지 못했습니다.",
          kind: "empty",
        },
      });
      return false;
    }
    requests.cancel("prices");
    cancelFps();
    const input = state.lastRecommendation.input || {};
    const selected = {},
      pinned = { ...state.pinned };
    for (const meta of BUILDER_PARTS) {
      const part = parts[meta.key];
      if (part?.id) {
        selected[meta.key] = withPartType([part], meta.key)[0];
        pinned[meta.key] = {
          ...(pinned[meta.key] || {}),
          [part.id]: selected[meta.key],
        };
      }
    }
    update({
      selected,
      pinned,
      csGpuMakers: [],
      builderFilters: { ...state.builderFilters, gpu: {} },
      productQuery: "",
      productDraft: "",
      csRes: input.resolution || state.resolution,
      refresh: Number(input.refresh) || state.refresh,
      csGame: input.game || state.game,
      csGameCategory: gameCategoryFor(input.game || state.game, state.games),
      csWork: input.work_profile || state.panelWork,
      csMode: input.mode || state.panelMode,
      builderPart: "gpu",
      activeView: "custom",
    });
    void loadProducts("gpu");
    return true;
  }
  function loadCatalog() {
    const entry = requests.start(
      "catalog",
      "compact",
      (signal) => json("/api/catalog?compact=1", signal),
      5000,
    );
    if (entry.task) return entry.task;
    entry.task = entry.promise
      .then((data) => {
        if (!entry.current()) return;
        const mappings = {
          gpu: "gpus",
          cpu: "cpus",
          ram: "rams",
          mb: "mbs",
          storage: "storages",
          hdd: "hdds",
          psu: "psus",
          case: "cases",
          software: "software",
        };
        const catalogs = { ...state.catalogs };
        for (const [type, key] of Object.entries(mappings))
          if (data[key])
            catalogs[type] = seedCatalogItems(withPartType(data[key], type));
        const games = data.games?.length
          ? data.games.map((g) => ({
              id: g.id,
              label: g.label || g.name || g.id,
              group: g.group || "기타",
              category: g.category || gameCategoryFor(g.id, state.games),
            }))
          : state.games;
        const workProfiles = structuredClone(state.workProfiles);
        for (const profile of data.work_profiles || [])
          if (workProfiles[profile.id])
            workProfiles[profile.id] = {
              ...workProfiles[profile.id],
              name: profile.label || workProfiles[profile.id].name,
              group: profile.group || workProfiles[profile.id].group,
            };
        publish({
          catalogs,
          games,
          workProfiles,
          productFacets: {
            ...state.productFacets,
            ...(data.filter_facets || {}),
          },
          catalogError: "",
        });
      })
      .catch((error) => {
        if (entry.current()) publish({ catalogError: errorMessage(error) });
      });
    return entry.task;
  }
  function chooseGameCategory(category, manual = false) {
    const games = state.games.filter(
      (g) => gameCategoryFor(g.id, state.games) === category,
    );
    update(
      manual
        ? { csGameCategory: category, csGame: games[0]?.id || state.csGame }
        : { gameCategory: category, game: games[0]?.id || state.game },
    );
  }
  return {
    getState,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    domain,
    update,
    setView: (activeView) => update({ activeView }),
    setPart,
    toggleFilter,
    selectGpuSeries,
    selectGpuModel,
    resetFilters,
    loadProducts,
    retryProducts: (type = state.builderPart) =>
      loadProducts(type, { force: true }),
    selectProduct,
    clearProduct,
    clearBuild,
    refreshSelectedPrices,
    estimateFps,
    cancelFps,
    recommend,
    resetRecommendation,
    importRecommendation,
    loadCatalog,
    chooseGameCategory,
    destroy: () => {
      requests.cancelAll();
      listeners.clear();
    },
  };
}
