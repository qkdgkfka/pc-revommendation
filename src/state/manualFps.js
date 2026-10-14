import { customFpsKey, fpsRequestPart } from "../domain/performance.js";
import { RequestError, errorMessage, runRequest } from "./requests.js";
const FPS_CACHE_LIMIT = 64;
export function createManualFps({
  getState,
  publish,
  requests,
  json,
  timeout,
}) {
  const fpsCache = new Map();
  const cancelFps = () => {
    requests.cancel("fps");
    if (getState().fps.loading)
      publish({ fps: { ...getState().fps, loading: false } });
  };
  function estimateFps(force = false) {
    const { gpu, cpu, ram } = getState().selected;
    if (getState().csMode !== "game" || !gpu || !cpu || !ram) {
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
      getState().csGame,
      getState().csRes,
      getState().refresh,
    );
    if (!force && fpsCache.has(key)) {
      const cached = fpsCache.get(key);
      fpsCache.delete(key);
      fpsCache.set(key, cached);
      publish({
        fps: {
          key,
          data: cached,
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
      game: getState().csGame,
      resolution: getState().csRes,
      refresh: getState().refresh,
      tier: "mid",
    };
    const entry = requests.start(
      "fps",
      key,
      (signal) => json("/api/estimate-fps", signal, payload),
      timeout ?? 20000,
    );
    return runRequest(entry, {
      onStart: () =>
        publish({
          fps: { key, data: null, loading: true, error: "", kind: "" },
        }),
      onSuccess: (data) => {
        if (!data.fps)
          throw new RequestError("empty", "해당 구성의 FPS 자료가 없습니다.");
        fpsCache.delete(key);
        fpsCache.set(key, data.fps);
        if (fpsCache.size > FPS_CACHE_LIMIT)
          fpsCache.delete(fpsCache.keys().next().value);
        publish({
          fps: { key, data: data.fps, loading: false, error: "", kind: "" },
        });
      },
      onError: (error) =>
        publish({
          fps: {
            key,
            data: null,
            loading: false,
            error: errorMessage(error),
            kind: error.kind || "upstream",
          },
        }),
    });
  }
  return { estimateFps, cancelFps };
}
