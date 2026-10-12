import { test } from "node:test";
import assert from "node:assert/strict";
import { setup } from "./frontend-harness.js";
test("partial names, suffixes and bilingual brands match in every component category", () => {
  const c = setup();
  for (const [type, query, name, other] of [
    ["cpu", "인텔", "Intel Core i5-14600KF", "AMD Ryzen 7 9800X3D"],
    ["cpu", "14600", "Intel Core i5-14600K", "Intel Core i5-14400F"],
    [
      "cpu",
      "i5-14600",
      "인텔 코어i5-14세대 14600KF",
      "인텔 코어i5-14세대 14400F",
    ],
    ["mb", "에이수스 b650", "ASUS PRIME B650M-A", "MSI B650M"],
    ["ram", "삼성 ddr5", "Samsung DDR5 32GB", "Samsung DDR4 16GB"],
    ["ram", "삼성전", "삼성전자 DDR5 32GB", "G.SKILL DDR5 32GB"],
    [
      "ram",
      "６０００ DDR5",
      "G.SKILL DDR5 6000 32GB",
      "G.SKILL DDR5 5600 32GB",
    ],
    ["ram", "DDR5-6000", "G.SKILL DDR5 6000 32GB", "Samsung DDR5-5600 16GB"],
    ["gpu", "4070", "ASUS RTX 4070 Ti SUPER", "ASUS RTX 4060"],
    [
      "gpu",
      "지포스 RTX4070",
      "ASUS GeForce RTX 4070 SUPER",
      "ASUS GeForce RTX 4060",
    ],
    [
      "storage",
      "삼성 990",
      "Samsung 990 PRO 2TB SSD",
      "Samsung 980 PRO 1TB SSD",
    ],
    [
      "hdd",
      "씨게이트 barra",
      "Seagate Barracuda 4TB HDD",
      "Seagate IronWolf 4TB HDD",
    ],
    [
      "psu",
      "마이크로닉스 850",
      "Micronics Classic II 850W",
      "Micronics Classic II 750W",
    ],
    ["case", "h5", "NZXT H5 Flow", "NZXT H7 Flow"],
    [
      "software",
      "윈도우 11",
      "Microsoft Windows 11 Home",
      "Microsoft Windows 10 Home",
    ],
  ]) {
    c.st.productQuery = query;
    assert.equal(
      c.productMatchesFilters(type, { name }),
      true,
      `${type}: ${query}`,
    );
    assert.equal(
      c.productMatchesFilters(type, { name: other }),
      false,
      `${type}: excludes ${other}`,
    );
  }
});
test("GPU generation search remains broad while a selected model remains exact", () => {
  const c = setup();
  c.st.productQuery = "RX9000";
  assert.equal(
    c.productMatchesFilters("gpu", { name: "SAPPHIRE RX 9070 XT" }),
    true,
  );
  assert.equal(
    c.productMatchesFilters("gpu", { name: "SAPPHIRE RX 7900 XTX" }),
    false,
  );
  c.st.productQuery = "4070";
  c.st.builderFilters.gpu = { model: ["RTX 4070 Super"] };
  assert.equal(
    c.productMatchesFilters("gpu", { name: "ASUS RTX 4070 SUPER" }),
    true,
  );
  assert.equal(
    c.productMatchesFilters("gpu", { name: "ASUS RTX 4070 Ti SUPER" }),
    false,
  );
});
test("a live search page still rejects unrelated product names", () => {
  const c = setup();
  c.st.productQuery = "인텔";
  c.st.browse.cpu = {
    loaded: true,
    status: "live",
    query: "인텔",
    requestKey: c.builderSearchKey("cpu"),
  };
  assert.equal(
    c.productMatchesFilters("cpu", { name: "Intel Core i5-14600KF" }),
    true,
  );
  assert.equal(
    c.productMatchesFilters("cpu", { name: "AMD Ryzen 7 9800X3D" }),
    false,
  );
});
test("structured chipset and series override marketing name", () => {
  const c = setup();
  assert.equal(
    c.gpuModelToken({ chipset: "RTX 4070 SUPER", name: "RTX 5070 giveaway" }),
    "RTX 4070 Super",
  );
  assert.equal(c.gpuSeriesToken({ chipset: "RTX 4070 SUPER" }), "RTX 40");
  assert.equal(c.gpuSeriesToken({ name: "RTX 4500 Ada" }), "");
  assert.equal(
    c.gpuModelToken({ model: "unknown", name: "ASUS RTX 4070 SUPER" }),
    "RTX 4070 Super",
  );
});
test("six series compose with maker filters and exact chipsets", () => {
  const c = setup();
  for (const [series, chipset, maker] of [
    ["RTX 50", "RTX 5070 Ti", "asus"],
    ["RTX 40", "RTX 4070 Super", "asus"],
    ["RTX 30", "RTX 3060 Ti", "asus"],
    ["RX 9000", "RX 9070 XT", "sapphire"],
    ["RX 7000", "RX 7900 XTX", "sapphire"],
    ["RX 6000", "RX 6800 XT", "sapphire"],
  ]) {
    c.st.builderFilters.gpu = { series: [series], maker: [maker] };
    assert.equal(
      c.productMatchesFilters("gpu", { name: `${maker} ${chipset}` }),
      true,
    );
    assert.equal(
      c.productMatchesFilters("gpu", { name: `MSI ${chipset}` }),
      false,
    );
    assert.equal(
      c.productMatchesFilters("gpu", { name: `${maker} RTX 2080` }),
      false,
    );
    c.st.builderFilters.gpu.model = [chipset];
    assert.equal(
      c.productMatchesFilters("gpu", { name: `${maker} ${chipset}` }),
      true,
    );
  }
});
test("series button selects generation, clears chipset and requests search", () => {
  const c = setup();
  let calls = 0;
  c.st.builderPart = "gpu";
  c.fetch = async () => {
    calls++;
    return { ok: true, json: async () => ({ items: [] }) };
  };
  c.st.builderFilters.gpu = { model: ["RTX 4070 Super"], maker: ["asus"] };
  c.selectGpuSeries("RTX 50 Series");
  assert.deepEqual(Array.from(c.st.builderFilters.gpu.series), ["RTX 50"]);
  assert.equal(c.st.builderFilters.gpu.model.length, 0);
  assert.equal(c.st.builderFilters.gpu.maker[0], "asus");
  assert.equal(calls, 1);
});
test("requests fifty, persists GPU filters and sorting, and deduplicates page two", async () => {
  const c = setup();
  c.st.builderPart = "gpu";
  const urls = [];
  let page = 0;
  c.st.builderFilters.gpu = {
    series: ["RTX 40"],
    model: ["RTX 4070 Super"],
    maker: ["asus"],
  };
  c.st.productSort = "price_asc";
  c.fetch = async (url) => {
    urls.push(new URL(url));
    page++;
    return {
      ok: true,
      json: async () => ({
        ok: true,
        items:
          page === 1
            ? [{ id: "one", name: "ASUS RTX 4070 Super" }]
            : [
                { id: "one", name: "ASUS RTX 4070 Super" },
                { id: "two", name: "ASUS RTX 4070 Super" },
              ],
        has_more: true,
        status: "live",
      }),
    };
  };
  c.baseUrl = () => "http://localhost:4001";
  await c.loadDanawaProducts("gpu");
  await c.loadDanawaProducts("gpu", { append: true });
  assert.equal(urls[0].searchParams.get("limit"), "50");
  assert.equal(urls[1].searchParams.get("page"), "2");
  for (const u of urls) {
    assert.equal(u.searchParams.get("series"), "RTX 40");
    assert.equal(u.searchParams.get("model"), "RTX 4070 Super");
    assert.equal(u.searchParams.get("maker"), "asus");
    assert.equal(u.searchParams.get("sort"), "price_asc");
  }
  assert.equal(c.browseStateFor("gpu").items.length, 2);
});
test("server facets drive non-GPU filters and every page keeps the composed query", async () => {
  const c = setup();
  c.st.builderPart = "mb";
  c.st.productFacets = {
    mb: [{ key: "socket", label: "소켓", options: [["AM5", "AM5"]] }],
  };
  c.st.builderFilters.mb = {
    socket: ["AM5"],
    chipset: ["B650"],
    memory_type: ["DDR5"],
    form_factor: ["ATX"],
  };
  c.st.productSort = "price_asc";
  const urls = [];
  c.baseUrl = () => "http://localhost:4001";
  c.fetch = async (url) => {
    urls.push(new URL(url));
    return {
      ok: true,
      json: async () => ({
        ok: true,
        items: [
          {
            id: String(urls.length),
            name: "ASUS B650",
            specs: {
              socket: "AM5",
              chipset: "B650",
              memory_type: ["DDR5"],
              form_factor: "ATX",
            },
          },
        ],
        has_more: true,
        status: "live",
        cursor: "stable",
      }),
    };
  };
  await c.loadDanawaProducts("mb");
  await c.loadDanawaProducts("mb", { append: true });
  for (const u of urls)
    assert.deepEqual(
      JSON.parse(u.searchParams.get("filters")),
      c.st.builderFilters.mb,
    );
  assert.equal(urls[1].searchParams.get("cursor"), "stable");
  assert.equal(
    c.productMatchesFilters("mb", c.browseStateFor("mb").items[0]),
    true,
  );
  assert.equal(
    c.productMatchesFilters("mb", { specs: { socket: "AM4" } }),
    false,
  );
  assert.equal(c.expandedBuilderCatalog("mb"), false);
  const previous = c.builderSearchKey("mb");
  c.st.builderFilters.mb.socket = ["AM4"];
  assert.notEqual(previous, c.builderSearchKey("mb"));
});
