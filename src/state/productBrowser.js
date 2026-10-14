import {
  BUILDER_META,
  withPartType,
  uniqueProducts,
  gpuSeriesToken,
  marketName,
} from "../domain/products.js";
import { RequestError, errorMessage, runRequest } from "./requests.js";
export function createProductBrowser({
  getState,
  publish,
  update,
  domain,
  requests,
  json,
  timeout,
}) {
  const patchBrowse = (type, patch, extra = {}) =>
    publish({
      ...extra,
      browse: {
        ...getState().browse,
        [type]: { ...(getState().browse[type] || {}), ...patch },
      },
    });
  function loadProducts(type = getState().builderPart, opts = {}) {
    if (!BUILDER_META[type]) return Promise.resolve();
    const query = String(opts.query ?? getState().productQuery).trim(),
      source = opts.source || getState().productSource;
    const requestKey = domain().builderSearchKey(type, query, source),
      browse = getState().browse[type] || {};
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
      sort: getState().productSort || "popular",
    });
    if (append && browse.cursor) params.set("cursor", browse.cursor);
    if (type !== "gpu")
      params.set(
        "filters",
        JSON.stringify(getState().builderFilters[type] || {}),
      );
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
      timeout ?? 30000,
    );
    return runRequest(entry, {
      onStart: () =>
        patchBrowse(type, {
          loading: true,
          error: "",
          errorKind: "",
          pendingKey: requestKey,
          ...(!append ? { items: [], loaded: false, hasMore: false } : {}),
        }),
      onSuccess: (data) => {
        const items = withPartType(data.items || [], type),
          unavailable = data.status === "unavailable";
        patchBrowse(
          type,
          {
            items:
              append && !data.reset
                ? uniqueProducts([
                    ...(getState().browse[type]?.items || []),
                    ...items,
                  ])
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
          },
          data.facets && type !== "gpu"
            ? {
                productFacets: {
                  ...getState().productFacets,
                  [type]: data.facets,
                },
              }
            : {},
        );
      },
      onError: (error) =>
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
        }),
    });
  }
  function setPart(type) {
    if (!BUILDER_META[type]) return;
    if (type === getState().builderPart) {
      void loadProducts(type);
      return;
    }
    const previous = getState().builderPart,
      productQueries = {
        ...getState().productQueries,
        [previous]: getState().productQuery,
      },
      productDrafts = {
        ...getState().productDrafts,
        [previous]: getState().productDraft,
      };
    requests.cancel("products:" + previous);
    if (getState().browse[previous]?.loading)
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
        ...getState().builderFilters,
        [type]: {
          ...(getState().builderFilters[type] || {}),
          [key]: [...current],
        },
      },
      ...(type === "gpu" && key === "maker"
        ? { csGpuMakers: [...current] }
        : {}),
    });
    void loadProducts(type);
  }
  function selectGpuSeries(label) {
    if (getState().builderPart !== "gpu") return;
    update({
      builderFilters: {
        ...getState().builderFilters,
        gpu: {
          ...(getState().builderFilters.gpu || {}),
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
        ...getState().builderFilters,
        gpu: {
          ...(getState().builderFilters.gpu || {}),
          model: [model],
          series: [gpuSeriesToken({ chipset: model })],
        },
      },
    });
    void loadProducts("gpu");
  }
  function resetFilters() {
    update({
      builderFilters: {
        ...getState().builderFilters,
        [getState().builderPart]: {},
      },
      ...(getState().builderPart === "gpu" ? { csGpuMakers: [] } : {}),
    });
    void loadProducts();
  }
  return {
    loadProducts,
    setPart,
    toggleFilter,
    selectGpuSeries,
    selectGpuModel,
    resetFilters,
  };
}
