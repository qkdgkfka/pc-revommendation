// Test access uses the same ES modules and store as production, without globals or VM evaluation.
import * as products from "../src/domain/products.js";
import * as specs from "../src/domain/specs.js";
import * as images from "../src/domain/images.js";
import * as performance from "../src/domain/performance.js";
import { createAppStore } from "../src/state/store.js";
export function setup() {
  const context = {
    fetch: async () => ({
      ok: true,
      json: async () => ({ items: [], status: "empty" }),
    }),
  };
  const store = createAppStore({
    catalogs: {},
    baseUrl: "http://localhost:4001",
    fetch: (...args) => context.fetch(...args),
  });
  Object.assign(context, products, specs, images, performance, {
    store,
    selectGpuSeries: store.selectGpuSeries,
    loadDanawaProducts: store.loadProducts,
  });
  Object.defineProperty(context, "st", { get: store.getState });
  return new Proxy(context, {
    get(target, key) {
      return key in target ? target[key] : store.domain()[key];
    },
  });
}
