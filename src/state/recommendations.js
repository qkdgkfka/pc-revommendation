import { BUILDER_PARTS, withPartType } from "../domain/products.js";
import { recommendationDefaults, gameCategoryFor } from "./initialState.js";
import { RequestError, errorMessage, runRequest } from "./requests.js";
export function createRecommendations({
  getState,
  publish,
  update,
  requests,
  json,
  cancelFps,
  loadProducts,
  timeout,
}) {
  function recommend() {
    const payload = {
      budget_mode: getState().budgetMode,
      budget: getState().budgetMode === "unlimited" ? null : getState().budget,
      budget_min:
        getState().budgetMode === "unlimited" ? 0 : getState().budgetMin,
      budget_max:
        getState().budgetMode === "unlimited" ? null : getState().budgetMax,
      resolution: getState().resolution,
      refresh: getState().refresh,
      gpu_pref: getState().gpu_pref,
      gpu_brands: getState().gpu_brands,
      game: getState().panelMode === "game" ? getState().game : "cyberpunk2077",
      mode: getState().panelMode,
      work_profile: getState().panelWork,
    };
    const entry = requests.start(
      "recommendation",
      JSON.stringify(payload),
      (signal) => json("/api/recommend", signal, payload),
      timeout ?? 30000,
    );
    return runRequest(entry, {
      onStart: () =>
        publish({
          recommendation: {
            loading: true,
            error: "",
            kind: "",
            startedAt: Date.now(),
          },
        }),
      onSuccess: (data) => {
        if (!data.results)
          throw new RequestError("empty", "서버 응답에 추천 결과가 없습니다.");
        publish({
          lastRecommendation: { ...data, input: data.input || payload },
          recommendation: { loading: false, error: "", kind: "" },
        });
      },
      onError: (error) =>
        publish({
          recommendation: {
            loading: false,
            error: errorMessage(error),
            kind: error.kind || "upstream",
          },
        }),
    });
  }
  function cancelRecommendation() {
    requests.cancel("recommendation");
    publish({
      recommendation: {
        loading: false,
        error: "분석을 취소했습니다. 조건을 유지했으니 다시 분석할 수 있어요.",
        kind: "cancelled",
      },
    });
  }
  function resetRecommendation() {
    requests.cancel("recommendation");
    requests.cancel("fps");
    publish({
      ...recommendationDefaults,
      gpu_brands: [],
      lastRecommendation: null,
      recommendation: { loading: false, error: "", kind: "" },
      fps: { ...getState().fps, loading: false },
    });
  }
  function importRecommendation(tier) {
    if (getState().recommendation.loading) return false;
    const recommendation = getState().lastRecommendation?.results?.[tier],
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
    const input = getState().lastRecommendation.input || {};
    const selected = {},
      pinned = { ...getState().pinned };
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
      builderFilters: { ...getState().builderFilters, gpu: {} },
      productQuery: "",
      productDraft: "",
      csRes: input.resolution || getState().resolution,
      refresh: Number(input.refresh) || getState().refresh,
      csGame: input.game || getState().game,
      csGameCategory: gameCategoryFor(
        input.game || getState().game,
        getState().games,
      ),
      csWork: input.work_profile || getState().panelWork,
      csMode: input.mode || getState().panelMode,
      builderPart: "gpu",
      activeView: "custom",
    });
    void loadProducts("gpu");
    return true;
  }
  return {
    recommend,
    cancelRecommendation,
    resetRecommendation,
    importRecommendation,
  };
}
