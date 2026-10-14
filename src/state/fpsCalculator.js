import { RequestError, errorMessage, runRequest } from "./requests.js";

export function initialFpsCalculator() {
  return {
    input: { cpuId: "", gpuId: "", game: "cyberpunk2077", resolution: "1080" },
    data: null,
    loading: false,
    error: "",
  };
}

export function calculatorRam(cpu, catalogs) {
  const type = cpu?.socket === "AM4" ? "DDR4" : "DDR5";
  return (
    catalogs.ram?.find(
      (part) => Number(part.gb) === 32 && part.type === type,
    ) || {
      id: "fps_ram_32_" + type.toLowerCase(),
      name: type + " 32GB",
      gb: 32,
      type,
      speed: type === "DDR4" ? 3200 : 5600,
    }
  );
}

export function createFpsCalculator({
  getState,
  publish,
  requests,
  json,
  timeout = 20000,
}) {
  const set = (patch) =>
    publish({ fpsCalculator: { ...getState().fpsCalculator, ...patch } });
  function updateFpsCalculator(patch) {
    const current = getState().fpsCalculator;
    const changes = Object.fromEntries(
      Object.entries(patch).filter(
        ([key, value]) => key in current.input && current.input[key] !== value,
      ),
    );
    if (!Object.keys(changes).length) return;
    requests.cancel("fps-calculator");
    set({
      input: { ...current.input, ...changes },
      data: null,
      loading: false,
      error: "",
    });
  }
  function cancelFpsCalculator() {
    requests.cancel("fps-calculator");
    if (getState().fpsCalculator.loading)
      set({ loading: false, error: "FPS 예측을 취소했습니다." });
  }
  function calculateFps() {
    const { input } = getState().fpsCalculator;
    const { catalogs, games } = getState();
    const cpu = catalogs.cpu?.find((p) => p.id === input.cpuId);
    const gpu = catalogs.gpu?.find((p) => p.id === input.gpuId);
    if (!cpu || !gpu) {
      set({ loading: false, error: "CPU와 GPU를 모두 선택해 주세요." });
      return Promise.resolve();
    }
    const ram = calculatorRam(cpu, catalogs);
    const reference = (part) => ({
      id: part.id,
      name: part.name,
      performance_ref_id: part.performance_ref_id,
    });
    const payload = {
      cpu: reference(cpu),
      gpu: reference(gpu),
      ram: { ...reference(ram), gb: ram.gb, type: ram.type, speed: ram.speed },
      game: input.game,
      resolution: input.resolution,
      refresh: 60,
      tier: "mid",
    };
    const entry = requests.start(
      "fps-calculator",
      JSON.stringify(payload),
      (signal) => json("/api/estimate-fps", signal, payload),
      timeout,
    );
    return runRequest(entry, {
      onStart: () => set({ loading: true, error: "", data: null }),
      onSuccess: (response) => {
        if (!response.fps?.fps_by_option)
          throw new RequestError(
            "empty",
            "해당 구성의 FPS 자료를 확인하지 못했습니다.",
          );
        set({
          loading: false,
          error: "",
          data: {
            fps: response.fps,
            resolution: input.resolution,
            cpuName: cpu.name,
            gpuName: gpu.name,
            gameName:
              games.find((g) => g.id === input.game)?.label || input.game,
            ramLabel: `${ram.type} ${ram.gb}GB · ${ram.speed}MT/s`,
          },
        });
      },
      onError: (error) =>
        set({ loading: false, error: errorMessage(error), data: null }),
    });
  }
  return { updateFpsCalculator, calculateFps, cancelFpsCalculator };
}
