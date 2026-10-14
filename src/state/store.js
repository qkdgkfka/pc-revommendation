import { catalogPatch } from "./catalog.js";
import { createFpsCalculator } from "./fpsCalculator.js";
import {
  initialState,
  recommendationDefaults,
  gameCategoryFor,
} from "./initialState.js";
export { initialState, gameCategoryFor } from "./initialState.js";
import { createBuilderDomain } from "../domain/builder.js";
import {
  createRequestManager,
  createJsonClient,
  errorMessage,
  runRequest,
} from "./requests.js";
import { createProductBrowser } from "./productBrowser.js";
import { createBuildSelection } from "./buildSelection.js";
import { createManualFps } from "./manualFps.js";
import { createRecommendations } from "./recommendations.js";
export function createAppStore(options = {}) {
  let state = initialState(options.catalogs),
    listeners = new Set();
  const requests = createRequestManager();
  const fetcher = options.fetch || ((...args) => globalThis.fetch(...args));
  const json = createJsonClient(fetcher, options.baseUrl || "");
  const getState = () => state;
  const domainKeys = [
    "browse",
    "builderFilters",
    "builderPart",
    "catalogs",
    "pinned",
    "productFacets",
    "productQuery",
    "productSort",
    "productSource",
  ];
  let domainState, builderDomain;
  const domain = () => {
    if (
      !domainState ||
      domainKeys.some((key) => domainState[key] !== state[key])
    ) {
      domainState = state;
      builderDomain = createBuilderDomain(state);
    }
    return builderDomain;
  };
  const publish = (patch) => {
    if (!Object.keys(patch).some((key) => !Object.is(state[key], patch[key])))
      return;
    state = { ...state, ...patch };
    listeners.forEach((listener) => listener());
  };
  function update(patch) {
    patch = Object.fromEntries(
      Object.entries(patch).filter(
        ([key, value]) => !Object.is(state[key], value),
      ),
    );
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
    if (["csGame", "csRes", "csMode", "refresh"].some((k) => k in patch)) {
      requests.cancel("fps");
      if (state.fps.loading) patch.fps = { ...state.fps, loading: false };
    }
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
  const services = {
    getState,
    publish,
    update,
    domain,
    requests,
    json,
    timeout: options.timeout,
  };
  const manualFps = createManualFps(services);
  const { cancelFps } = manualFps;
  const browser = createProductBrowser(services);
  const { loadProducts } = browser;
  const build = createBuildSelection({ ...services, cancelFps });
  const recommendations = createRecommendations({
    ...services,
    cancelFps,
    loadProducts,
  });
  function loadCatalog() {
    const entry = requests.start(
      "catalog",
      "compact",
      (signal) => json("/api/catalog?compact=1", signal),
      5000,
    );
    return runRequest(entry, {
      onSuccess: (data) => publish(catalogPatch(data, state)),
      onError: (error) => publish({ catalogError: errorMessage(error) }),
    });
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
    ...createFpsCalculator({
      getState,
      publish,
      requests,
      json,
      timeout: options.timeout,
    }),
    getState,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    domain,
    update,
    setView: (activeView) => update({ activeView }),
    ...browser,
    retryProducts: (type = state.builderPart) =>
      loadProducts(type, { force: true }),
    ...build,
    ...manualFps,
    ...recommendations,
    loadCatalog,
    chooseGameCategory,
    destroy: () => {
      requests.cancelAll();
      listeners.clear();
    },
  };
}
