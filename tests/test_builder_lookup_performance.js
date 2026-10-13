import { test } from "node:test";
import assert from "node:assert/strict";
import { createBuilderDomain } from "../src/domain/builder.js";
import { initialState } from "../src/state/initialState.js";

test("ID lookup stops at a browse match without scanning reference catalogs", () => {
  const state = initialState({});
  const first = { id: "cpu", name: "Current quote" };
  state.browse.cpu = { items: [first] };
  let reads = 0;
  Object.defineProperty(state.catalogs, "cpu", {
    get: () => {
      reads++;
      return [{ id: "cpu", name: "Reference" }];
    },
  });
  const domain = createBuilderDomain(state);
  assert.equal(domain.findCatalogItemById("cpu"), first);
  assert.equal(reads, 0);
});

test("ID lookup preserves browse, pinned and reference precedence and duplicate IDs", () => {
  const state = initialState({});
  const browse = { id: "same", name: "Browse" };
  const pinned = { id: "pinned" };
  const reference = { id: "reference" };
  state.browse.cpu = { items: [null, {}, browse, { id: 7 }] };
  state.pinned.cpu = { same: { id: "same" }, pinned };
  state.catalogs.cpu = [reference, { id: "7" }];
  const domain = createBuilderDomain(state);
  assert.equal(domain.findPartById("cpu", "same"), browse);
  assert.equal(domain.findPartById("cpu", "pinned"), pinned);
  assert.equal(domain.findPartById("cpu", "reference"), reference);
  assert.equal(domain.findPartById("cpu", "7"), undefined);
  assert.equal(domain.findPartById("cpu", 7).id, 7);
  for (const id of [null, undefined, "", 0, "missing"])
    assert.equal(domain.findPartById("cpu", id), undefined);
});

test("price sorting parses each price once and keeps missing values last", () => {
  for (const sort of ["price_asc", "price_desc"]) {
    const state = initialState({});
    state.productSort = sort;
    const domain = createBuilderDomain(state);
    let reads = 0;
    const items = Array.from({ length: 50 }, (_, i) => ({
      id: String(i),
      name: "Case",
      get price() {
        reads++;
        return (i * 17) % 50;
      },
    }));
    state.browse.case = {
      loaded: true,
      requestKey: domain.builderSearchKey("case"),
      items: [...items, { id: "missing", name: "Case" }],
    };
    const sorted = domain.filteredProducts("case");
    assert.equal(sorted[0].id, sort === "price_asc" ? "0" : "47");
    assert.equal(sorted.at(-1).id, "missing");
    assert.ok(reads <= 150, `price reads: ${reads}`);
    assert.equal(state.browse.case.items[0], items[0]);
  }
});
