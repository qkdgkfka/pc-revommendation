import { test } from "node:test";
import assert from "node:assert/strict";
import { money, partUrl } from "../src/domain/products.js";
import { numeric, ramGbValue } from "../src/domain/performance.js";
import { createAppStore } from "../src/state/store.js";

test("purchase links reject unsafe schemes and choose the next usable URL", () => {
  assert.equal(
    partUrl({
      source_url: "javascript:alert(1)",
      url: "https://prod.danawa.com/info/?pcode=123",
    }),
    "https://prod.danawa.com/info/?pcode=123",
  );
  for (const url of [
    "javascript:alert(1)",
    "data:text/html,unsafe",
    "//untrusted.example",
    "https://user:pass@example.com/",
    "https://example.com/\nheader",
  ]) {
    assert.equal(
      partUrl({ name: "CPU", url }),
      "https://search.danawa.com/dsearch.php?query=CPU",
    );
  }
});

test("missing and nonnumeric values are not coerced to zero", () => {
  for (const value of [
    null,
    undefined,
    "",
    " ",
    false,
    [],
    {},
    Infinity,
    "Infinity",
  ]) {
    assert.equal(numeric(value), null);
  }
  assert.equal(numeric("0"), 0);
  assert.equal(numeric("32"), 32);
  assert.equal(ramGbValue({ gb: null, name: "DDR5 32GB" }), 32);
  assert.equal(ramGbValue({ gb: null }), 16);
});

test("currency formatting never displays nonfinite prices", () => {
  assert.equal(money(Infinity), "-");
  assert.equal(money("Infinity"), "-");
  assert.equal(money(0), "₩0");
  assert.equal(money(1000000), "₩1,000,000");
});

test("malformed JSON response shapes produce a controlled error", async () => {
  for (const body of [null, [], "text", 1]) {
    const store = createAppStore({
      fetch: async () => ({ ok: true, json: async () => body }),
    });
    await store.loadCatalog();
    assert.match(store.getState().catalogError, /서버 응답 형식/);
    store.destroy();
  }
});
