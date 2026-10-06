import { test } from "node:test";
import assert from "node:assert/strict";
import { createAppStore } from "../src/state/store.js";

const response = (data) => ({ ok: true, json: async () => data });

test("FPS history stays bounded while recent estimates are reused", async () => {
  let calls = 0;
  const store = createAppStore({
    catalogs: {},
    fetch: async () => response({ fps: { sequence: ++calls } }),
  });
  store.update({
    selected: { cpu: { id: "cpu" }, gpu: { id: "gpu" }, ram: { id: "ram" } },
  });
  for (let i = 0; i < 65; i++) {
    store.update({ csGame: `game-${i}` });
    await store.estimateFps();
  }
  store.update({ csGame: "game-64" });
  await store.estimateFps();
  assert.equal(calls, 65);
  store.update({ csGame: "game-0" });
  await store.estimateFps();
  assert.equal(calls, 66);
});

test("no-op edits preserve the snapshot and do not notify subscribers", () => {
  const store = createAppStore({ catalogs: {} });
  const initial = store.getState();
  let notifications = 0;
  store.subscribe(() => notifications++);
  store.update({ productDraft: "" });
  store.setView(initial.activeView);
  assert.equal(store.getState(), initial);
  assert.equal(notifications, 0);
});

test("product results and their facets are published as one consistent snapshot", async () => {
  const facets = [{ key: "socket", options: [["AM5", "AM5"]] }];
  const store = createAppStore({
    catalogs: {},
    fetch: async () =>
      response({
        items: [{ id: "cpu", name: "Ryzen", price: 100000 }],
        facets,
        status: "live",
      }),
  });
  const snapshots = [];
  store.subscribe(() => snapshots.push(store.getState()));
  await store.loadProducts();
  assert.equal(snapshots.length, 2);
  assert.equal(snapshots[0].browse.cpu.loading, true);
  assert.equal(snapshots[1].browse.cpu.loading, false);
  assert.equal(snapshots[1].browse.cpu.items[0].id, "cpu");
  assert.equal(snapshots[1].productFacets.cpu, facets);
});

test("typing and FPS updates reuse the builder domain while filters invalidate it", () => {
  const store = createAppStore({ catalogs: {} });
  const domain = store.domain();
  store.update({ productDraft: "Ryzen" });
  assert.equal(store.domain(), domain);
  store.update({ fps: { loading: true } });
  assert.equal(store.domain(), domain);
  store.update({ builderFilters: { cpu: { socket: ["AM5"] } } });
  assert.notEqual(store.domain(), domain);
  assert.deepEqual(store.domain().filterValues("cpu", "socket"), ["AM5"]);
});

test("repeating the current FPS controls does not cancel a pending estimate", async () => {
  let finish;
  const store = createAppStore({
    catalogs: {},
    fetch: () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  });
  store.update({
    selected: {
      cpu: { id: "cpu", name: "CPU" },
      gpu: { id: "gpu", name: "GPU" },
      ram: { id: "ram", name: "RAM" },
    },
  });
  const task = store.estimateFps();
  store.update({ csRes: store.getState().csRes });
  assert.equal(store.getState().fps.loading, true);
  finish(response({ fps: { fps_by_option: { high: 60 } } }));
  await task;
  assert.equal(store.getState().fps.data.fps_by_option.high, 60);
});
