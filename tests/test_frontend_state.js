import { test } from "node:test";
import assert from "node:assert/strict";
import { createAppStore } from "../src/state/store.js";
const deferred = () => {
  let resolve;
  const promise = new Promise((r) => (resolve = r));
  return { promise, resolve };
};
const response = (data) => ({ ok: true, json: async () => data });
test("reanalysis retains the last result through failure and replaces it only on success", async () => {
  let pending;
  const store = createAppStore({ fetch: () => pending.promise });
  const run = async (data) => {
    pending = deferred();
    const task = store.recommend();
    pending.resolve(response(data));
    await task;
  };
  await run({ results: { low: { totalPrice: 1000000 } } });
  const previous = store.getState().lastRecommendation;
  store.update({ resolution: "1440" });
  pending = deferred();
  const retry = store.recommend();
  assert.equal(store.getState().recommendation.loading, true);
  assert.equal(store.getState().lastRecommendation, previous);
  pending.resolve(response({ ok: false, error: "일시적인 연결 오류" }));
  await retry;
  assert.equal(store.getState().lastRecommendation, previous);
  assert.equal(store.getState().recommendation.loading, false);
  assert.match(store.getState().recommendation.error, /연결 오류/);
  await run({ results: { low: { totalPrice: 1200000 } } });
  assert.equal(
    store.getState().lastRecommendation.results.low.totalPrice,
    1200000,
  );
  assert.equal(store.getState().lastRecommendation.input.resolution, "1440");
  store.resetRecommendation();
  assert.equal(store.getState().lastRecommendation, null);
});
test("cancelling recommendation preserves conditions and ignores a late response", async () => {
  const pending = deferred();
  let signal;
  const store = createAppStore({
    fetch: (_, options) => {
      signal = options.signal;
      return pending.promise;
    },
  });
  store.update({ resolution: "2160", budgetMode: "unlimited" });
  const task = store.recommend();
  store.cancelRecommendation();
  assert.equal(signal.aborted, true);
  assert.equal(store.getState().recommendation.loading, false);
  assert.equal(store.getState().resolution, "2160");
  assert.equal(store.getState().budgetMode, "unlimited");
  pending.resolve(response({ results: { low: { totalPrice: 999 } } }));
  await task;
  assert.equal(store.getState().lastRecommendation, null);
});
test("unlimited recommendation sends no stale budget and reset restores a budget", async () => {
  let payload;
  const store = createAppStore({
    fetch: async (_, options) => {
      payload = JSON.parse(options.body);
      return response({ results: {} });
    },
  });
  store.update({ budgetMode: "unlimited", resolution: "2160", refresh: 144 });
  await store.recommend();
  assert.equal(payload.budget_mode, "unlimited");
  assert.equal(payload.budget_max, null);
  assert.equal(payload.budget, null);
  assert.equal(payload.resolution, "2160");
  store.resetRecommendation();
  assert.equal(store.getState().budgetMode, "soft");
  await store.recommend();
  assert.equal(payload.budget_mode, "soft");
  assert.equal(payload.budget_max, 2000000);
});
test("initial screen is AI and saved products wait for a provider result", () => {
  const store = createAppStore({
    fetch: async () => response({ items: [] }),
    catalogs: { cpu: [{ id: "saved", name: "CPU" }] },
  });
  assert.equal(store.getState().activeView, "ai");
  assert.deepEqual(store.domain().filteredProducts("cpu"), []);
});
test("identical inflight browse requests share one fetch", async () => {
  const pending = deferred();
  let calls = 0;
  const store = createAppStore({
    fetch: () => {
      calls++;
      return pending.promise;
    },
  });
  const first = store.loadProducts("cpu"),
    second = store.loadProducts("cpu");
  assert.equal(first, second);
  assert.equal(calls, 1);
  pending.resolve(response({ ok: true, items: [], status: "empty" }));
  await first;
  assert.equal(store.getState().browse.cpu.loading, false);
});
test("a replaced query aborts and late old results cannot overwrite the latest page", async () => {
  const pending = [];
  const signals = [];
  const store = createAppStore({
    fetch: (_, options) => {
      const d = deferred();
      pending.push(d);
      signals.push(options.signal);
      return d.promise;
    },
  });
  const old = store.loadProducts("cpu");
  store.update({ productQuery: "new" });
  const latest = store.loadProducts("cpu");
  assert.equal(signals[0].aborted, true);
  pending[1].resolve(
    response({ items: [{ id: "new", name: "new" }], status: "live" }),
  );
  await latest;
  pending[0].resolve(
    response({ items: [{ id: "old", name: "old" }], status: "live" }),
  );
  await old;
  assert.equal(store.getState().browse.cpu.items[0].id, "new");
  assert.equal(store.getState().browse.cpu.loading, false);
});
test("selected SKU survives query replacement and CPU changes retain motherboard", async () => {
  const store = createAppStore({
    fetch: async () => response({ items: [], status: "empty" }),
  });
  store.selectProduct("cpu", { id: "a", name: "CPU", socket: "AM5" });
  store.selectProduct("mb", { id: "b", name: "Board", socket: "AM5" });
  store.selectProduct("cpu", { id: "c", name: "CPU", socket: "LGA1700" });
  store.update({ productQuery: "different" });
  await store.loadProducts("mb");
  assert.equal(store.getState().selected.mb.id, "b");
  assert.equal(store.domain().findPartById("mb", "b").id, "b");
});
test("reset cancels recommendation and ignores completion even if fetch ignores abort", async () => {
  const pending = deferred();
  let signal;
  const store = createAppStore({
    fetch: (_, options) => {
      signal = options.signal;
      return pending.promise;
    },
  });
  const request = store.recommend();
  store.resetRecommendation();
  assert.equal(signal.aborted, true);
  pending.resolve(
    response({ results: { low: { parts: { gpu: { id: "a" } } } } }),
  );
  await request;
  assert.equal(store.getState().lastRecommendation, null);
  assert.equal(store.getState().recommendation.loading, false);
});
test("screen switches preserve independent manual and recommendation inputs", () => {
  const store = createAppStore();
  store.update({ productQuery: "ASUS", csRes: "2160", budget: 3000000 });
  store.setView("ai");
  store.setView("custom");
  assert.equal(store.getState().productQuery, "ASUS");
  assert.equal(store.getState().csRes, "2160");
  assert.equal(store.getState().budget, 3000000);
});
test("selecting SSD during an FPS request keeps that request running", async () => {
  const pending = deferred();
  let signal;
  const store = createAppStore({
    fetch: (url, options) =>
      url.includes("estimate-fps")
        ? ((signal = options.signal), pending.promise)
        : Promise.resolve(response({ results: [] })),
  });
  for (const type of ["cpu", "gpu", "ram"])
    store.selectProduct(type, {
      id: type,
      name: type,
      price: 1,
      price_status: "verified",
    });
  const request = store.estimateFps();
  store.selectProduct("storage", {
    id: "ssd",
    name: "SSD",
    price: 1,
    price_status: "verified",
  });
  assert.equal(signal.aborted, false);
  pending.resolve(response({ fps: { fps_by_option: { high: 80 } } }));
  await request;
  assert.equal(store.getState().fps.data.fps_by_option.high, 80);
});
test("timeouts are distinguished from empty results and upstream errors", async () => {
  const timeout = createAppStore({
    fetch: () => new Promise(() => {}),
    timeout: 5,
  });
  await timeout.loadProducts();
  assert.equal(timeout.getState().browse.cpu.errorKind, "timeout");
  const empty = createAppStore({
    fetch: async () => response({ items: [], status: "empty" }),
  });
  await empty.loadProducts();
  assert.equal(empty.getState().browse.cpu.status, "empty");
  assert.equal(empty.getState().browse.cpu.error, "");
  const failure = createAppStore({
    fetch: async () => ({
      ok: false,
      status: 503,
      json: async () => ({ error: "판매처 일시 중단" }),
    }),
  });
  await failure.loadProducts();
  assert.equal(failure.getState().browse.cpu.errorKind, "upstream");
  assert.match(failure.getState().browse.cpu.error, /일시 중단/);
});
test("replacing an FPS query aborts old work and prevents stale cache or display writes", async () => {
  const pending = [];
  const signals = [];
  const store = createAppStore({
    fetch: (url, options) => {
      if (!url.includes("estimate-fps"))
        return Promise.resolve(response({ results: [] }));
      const d = deferred();
      pending.push(d);
      signals.push(options.signal);
      return d.promise;
    },
  });
  for (const type of ["cpu", "gpu", "ram"])
    store.selectProduct(type, {
      id: type,
      name: type,
      price: 1,
      price_status: "verified",
    });
  const old = store.estimateFps();
  store.update({ csRes: "2160" });
  const latest = store.estimateFps();
  assert.equal(signals[0].aborted, true);
  pending[1].resolve(response({ fps: { fps_by_option: { high: 50 } } }));
  await latest;
  pending[0].resolve(response({ fps: { fps_by_option: { high: 100 } } }));
  await old;
  assert.equal(store.getState().fps.data.fps_by_option.high, 50);
  assert.equal(store.getState().fps.loading, false);
});
test("explicit retry bypasses a cached failed provider page with refresh=1", async () => {
  const urls = [];
  const store = createAppStore({
    fetch: async (url) => {
      urls.push(url);
      return response({ items: [], status: "unavailable" });
    },
  });
  await store.loadProducts();
  await store.retryProducts("cpu");
  assert.equal(
    new URL(urls[1], "http://localhost").searchParams.get("refresh"),
    "1",
  );
});
test("part switches restore each category committed query and unsent search draft", () => {
  const store = createAppStore({
    fetch: async () => response({ items: [], status: "empty" }),
  });
  store.update({ productQuery: "Ryzen", productDraft: "Ryzen 7" });
  store.setPart("ram");
  assert.equal(store.getState().productQuery, "");
  store.update({ productQuery: "Samsung", productDraft: "Samsung DDR5" });
  store.setPart("gpu");
  assert.equal(store.getState().productDraft, "");
  store.setPart("cpu");
  assert.equal(store.getState().productQuery, "Ryzen");
  assert.equal(store.getState().productDraft, "Ryzen 7");
  store.setPart("ram");
  assert.equal(store.getState().productQuery, "Samsung");
  assert.equal(store.getState().productDraft, "Samsung DDR5");
});
test("server deadline metadata is displayed as timeout for successful and failed HTTP responses", async () => {
  for (const ok of [true, false]) {
    const store = createAppStore({
      fetch: async () => ({
        ok,
        status: ok ? 200 : 504,
        json: async () => ({
          ok,
          status: "unavailable",
          items: [],
          error_kind: "timeout",
        }),
      }),
    });
    await store.loadProducts();
    assert.equal(store.getState().browse.cpu.errorKind, "timeout");
    assert.match(store.getState().browse.cpu.error, /시간이 초과/);
  }
});
test("a current provider response may show its cached quote after a failed live fetch", async () => {
  const store = createAppStore({
    fetch: async () =>
      response({
        status: "unavailable",
        items: [
          { id: "cached", name: "CPU", price: 1, price_status: "cached" },
        ],
      }),
  });
  assert.deepEqual(store.domain().filteredProducts("cpu"), []);
  await store.loadProducts();
  assert.equal(store.domain().filteredProducts("cpu")[0].id, "cached");
});
