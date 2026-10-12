import { test } from "node:test";
import assert from "node:assert/strict";
import { createAppStore } from "../src/state/store.js";
const catalogs = {
  cpu: [
    { id: "cpu-am4", name: "AMD Ryzen 5 5600", socket: "AM4" },
    { id: "cpu-am5", name: "AMD Ryzen 5 7600", socket: "AM5" },
  ],
  gpu: [{ id: "gpu", name: "NVIDIA RTX 5070" }],
  ram: [
    { id: "ddr4", name: "DDR4 32GB", type: "DDR4", gb: 32, speed: 3200 },
    { id: "ddr5", name: "DDR5 32GB", type: "DDR5", gb: 32, speed: 5600 },
  ],
};
const fps = {
  fps_by_option: { low: 140, medium: 120, high: 100, ultra: 80 },
  low1_by_option: { low: 100, medium: 90, high: 70, ultra: 55 },
};
const response = () => ({ ok: true, json: async () => ({ fps }) });
function configured(fetch, timeout) {
  const store = createAppStore({ catalogs, fetch, timeout });
  store.updateFpsCalculator({
    cpuId: "cpu-am4",
    gpuId: "gpu",
    game: "cyberpunk2077",
    resolution: "1440",
  });
  return store;
}
test("calculator requires CPU and GPU without a retailer or FPS request", async () => {
  let calls = 0;
  const store = createAppStore({
    catalogs,
    fetch: () => {
      calls++;
      return response();
    },
  });
  await store.calculateFps();
  assert.equal(calls, 0);
  assert.match(store.getState().fpsCalculator.error, /CPU.*GPU/);
});
test("calculator uses the shared API with compatible 32GB RAM and all option lows", async () => {
  let sent;
  const store = configured(async (url, options) => {
    sent = { url, body: JSON.parse(options.body) };
    return response();
  });
  const selected = store.getState().selected;
  await store.calculateFps();
  assert.equal(sent.url, "/api/estimate-fps");
  assert.equal(sent.body.resolution, "1440");
  assert.equal(sent.body.cpu.id, "cpu-am4");
  assert.equal(sent.body.ram.gb, 32);
  assert.equal(sent.body.ram.type, "DDR4");
  assert.deepEqual(
    store.getState().fpsCalculator.data.fps.low1_by_option,
    fps.low1_by_option,
  );
  assert.equal(store.getState().selected, selected);
  assert.equal(store.getState().fps.data, null);
  store.updateFpsCalculator({ cpuId: "cpu-am5" });
  await store.calculateFps();
  assert.equal(sent.body.ram.type, "DDR5");
});
test("changing calculator inputs cancels a request and ignores late results", async () => {
  let resolve, signal;
  const store = configured((_, options) => {
    signal = options.signal;
    return new Promise((r) => (resolve = r));
  });
  const pending = store.calculateFps();
  store.updateFpsCalculator({ resolution: "2160" });
  assert.equal(signal.aborted, true);
  resolve(response());
  await pending;
  assert.equal(store.getState().fpsCalculator.data, null);
  assert.equal(store.getState().fpsCalculator.loading, false);
});
test("calculator selections and results survive tab changes without replacing builder input", async () => {
  const store = configured(async () => response());
  await store.calculateFps();
  const previous = store.getState().fpsCalculator;
  store.setView("custom");
  store.setView("fps");
  assert.equal(store.getState().fpsCalculator, previous);
  assert.deepEqual(store.getState().selected, {});
  store.updateFpsCalculator({ game: "valorant" });
  assert.equal(store.getState().fpsCalculator.data, null);
});
test("calculator errors finish loading and retry can succeed", async () => {
  let fails = true;
  const store = configured(async () => {
    if (fails) throw new Error("연결 실패");
    return response();
  });
  await store.calculateFps();
  assert.match(store.getState().fpsCalculator.error, /연결 실패/);
  assert.equal(store.getState().fpsCalculator.loading, false);
  fails = false;
  await store.calculateFps();
  assert.ok(store.getState().fpsCalculator.data);
});
