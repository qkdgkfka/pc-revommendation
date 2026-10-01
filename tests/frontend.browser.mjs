// Browser plugin not available. Playwright validates unchanged UI flows with deterministic HTTP fixtures.
import { chromium, expect } from "@playwright/test";
const origin = process.env.FRONTEND_URL || "http://127.0.0.1:5173";
const observed = "2026-09-24T14:00:00Z";
const product = (id, name, specs = {}, extra = {}) => ({
  id,
  name,
  product_name: name,
  price: 100000,
  price_status: "verified",
  price_source: "danawa_live",
  scraped_at: observed,
  image_url: "https://images.example/" + id + ".jpg",
  url: "https://prod.danawa.com/info/?pcode=123",
  specs,
  ...extra,
});
const inventory = {
  cpu: [
    product(
      "cpu-am5",
      "AMD Ryzen 7 7800X3D",
      { socket: "AM5", platform: "AMD", memory_type: ["DDR5"] },
      { perf: 80, performance_ref_id: "cpu_ry7_7800x3d" },
    ),
  ],
  mb: [
    product("mb-lga", "ASUS B760 DDR5", {
      socket: "LGA1700",
      platform: "Intel",
      chipset: "B760",
      memory_type: ["DDR5"],
      form_factor: "ATX",
    }),
  ],
  gpu: [
    product(
      "gpu-super",
      "ASUS RTX 4070 Super 12GB",
      { chipset: "RTX 4070 Super", vram_gb: 12 },
      {
        perf_1080: 75,
        perf_1440: 70,
        vram: 12,
        performance_ref_id: "gpu_4070s",
      },
    ),
  ],
  ram: [
    product(
      "ram32",
      "Samsung DDR5 32GB 6000",
      {
        memory_type: ["DDR5"],
        capacity_gb: 32,
        speed: 6000,
        led: "no",
        color: "Black",
      },
      { gb: 32, type: "DDR5", speed: 6000 },
    ),
  ],
  storage: [
    product(
      "ssd",
      "Samsung SSD M.2 NVMe 1TB",
      {
        interface: "PCIe 4.0",
        protocol: "NVMe",
        form_factor: "M.2",
        capacity_gb: 1000,
        read_speed: 7000,
      },
      { capacity: 1000 },
    ),
  ],
  hdd: [
    product(
      "hdd",
      "Seagate HDD 2TB",
      { capacity_gb: 2000, rpm: 7200 },
      { capacity: 2000, rpm: 7200 },
    ),
  ],
  psu: [
    product(
      "psu",
      "FSP 850W 80 PLUS Gold",
      {
        watt: 850,
        rating: "Gold",
        modular: "Full",
        atx_version: "3.1",
        form_factor: "ATX",
      },
      { watt: 850 },
    ),
  ],
  case: [
    product("case", "NZXT H5 Flow", { form_factor: "ATX", color: "Black" }),
  ],
  software: [
    product("software", "Microsoft Windows 11 Home", { license: "FPP" }),
  ],
};
const gpuRefs = [
  "RTX 5070 Ti",
  "RTX 4070 Super",
  "RTX 3060 Ti",
  "RX 9070 XT",
  "RX 7900 XTX",
  "RX 6800 XT",
].map((name, index) => product("ref" + index, name, {}, { chipset: name }));
const facets = {
  mb: [
    {
      key: "socket",
      label: "소켓",
      options: [
        ["AM5", "AM5"],
        ["LGA1700", "LGA1700"],
      ],
    },
    {
      key: "chipset",
      label: "칩셋",
      options: [
        ["B760", "B760"],
        ["B650", "B650"],
      ],
    },
    {
      key: "memory_type",
      label: "메모리 규격",
      options: [
        ["DDR5", "DDR5"],
        ["DDR4", "DDR4"],
      ],
    },
    {
      key: "form_factor",
      label: "폼팩터",
      options: [
        ["ATX", "ATX"],
        ["mATX", "mATX"],
      ],
    },
  ],
  ram: [
    {
      key: "memory_type",
      label: "메모리 규격",
      options: [
        ["DDR5", "DDR5"],
        ["DDR4", "DDR4"],
      ],
    },
    {
      key: "capacity_gb",
      label: "용량",
      options: [
        ["32", "32GB"],
        ["16", "16GB"],
      ],
    },
  ],
};
const fps = {
  game: "cyberpunk2077",
  fps_by_option: { low: 160, medium: 120, high: 80 },
  graphics_modes: [
    {
      id: "upscale",
      supported: true,
      label: "DLSS 품질",
      technology: "DLSS",
      avg_fps: 100,
      method: "mode_estimate",
      range: { min: 90, max: 110 },
    },
    {
      id: "fg2",
      supported: true,
      label: "프레임 생성",
      avg_fps: 180,
      render_fps: 100,
      generated: true,
      method: "workload_estimate",
      source_url:
        "https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5090-test.91081/seite-8",
      calibration_sources: [
        "https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5090-test.91081/seite-8",
      ],
      calibration_basis: "다른 게임의 실측 기준 · 오차가 클 수 있음",
    },
  ],
};
let fpsResult = fps;
const parts = {
  gpu: inventory.gpu[0],
  cpu: inventory.cpu[0],
  ram: inventory.ram[0],
  mb: product("mb-am5", "MSI B650 AM5", {
    socket: "AM5",
    memory_type: ["DDR5"],
  }),
  storage: inventory.storage[0],
  psu: inventory.psu[0],
};
const recommendation = {
  results: Object.fromEntries(
    ["low", "mid", "high"].map((tier, i) => [
      tier,
      {
        parts,
        total_price: 600000 + i * 100000,
        fps,
        work_scores: { video_4k: { score: 72, label: "적합", level: "good" } },
      },
    ]),
  ),
};
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  }),
  page = await context.newPage(),
  errors = [],
  requests = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});
page.on("request", (request) => requests.push(request.url()));
await page.route("**/api/**", async (route) => {
  const url = new URL(route.request().url());
  if (url.pathname === "/api/part-image") {
    await route.fulfill({
      contentType: "image/svg+xml",
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect x="20" y="20" width="60" height="60" rx="8" fill="#dbeafe"/></svg>',
    });
    return;
  }
  let data;
  if (url.pathname === "/api/catalog")
    data = {
      gpus: gpuRefs,
      cpus: inventory.cpu,
      rams: inventory.ram,
      mbs: inventory.mb,
      storages: inventory.storage,
      hdds: inventory.hdd,
      psus: inventory.psu,
      cases: inventory.case,
      software: inventory.software,
      filter_facets: facets,
    };
  else if (url.pathname === "/api/products") {
    const query = url.searchParams.get("query") || "";
    await new Promise((r) => setTimeout(r, query === "느린 검색" ? 400 : 100));
    const type = url.searchParams.get("type");
    data = {
      ok: true,
      items: inventory[type] || [],
      status: "live",
      has_more: url.searchParams.get("page") === "1",
      cursor: "fixed-cursor",
      facets: facets[type],
    };
    if (query === "느린 검색" || query === "최신 검색") {
      data.items = [
        product(query, query + " DDR5 32GB 6000", inventory.ram[0].specs, {
          type: "DDR5",
          gb: 32,
          speed: 6000,
        }),
      ];
    }
    if (query === "빈 결과")
      data = { ok: true, items: [], status: "empty", has_more: false };
    if (query === "판매처 오류" && !url.searchParams.has("refresh"))
      data = {
        ok: false,
        items: [],
        error: "판매처 연결 오류",
        status: "unavailable",
      };
    if (query === "시간 초과")
      data = {
        ok: false,
        items: [],
        error: "판매처 조회 제한 시간을 초과했습니다.",
        error_kind: "timeout",
        status: "unavailable",
      };
  } else if (url.pathname === "/api/estimate-fps") data = { fps: fpsResult };
  else if (url.pathname === "/api/price-lookup") data = { results: [] };
  else if (url.pathname === "/api/recommend") {
    await new Promise((r) => setTimeout(r, 150));
    data = { ...recommendation, input: route.request().postDataJSON() };
  } else data = { ok: true };
  try {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(data),
    });
  } catch {
    /* Requests cancelled by screen/reset/query replacement are expected. */
  }
});
try {
  await page.goto(origin);
  await expect(page).toHaveTitle("PC 견적 도우미");
  await expect(page.locator("#viewAiBtn")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("#placeholder")).toBeVisible();
  await page.locator("#viewCustomBtn").click();
  await expect(page.locator(".pc-page-title")).toContainText("나만의 PC");
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  await expect(page.locator(".pc-categories >button")).toHaveCount(9);
  if (requests.some((url) => /GraphicsDetails/.test(url)))
    throw new Error("Inactive detail module was loaded eagerly");
  await page.locator(".pc-product-row .pc-add").click();
  await expect(page.locator(".pc-cart-item.has-selection")).toHaveCount(1);
  await page
    .locator(".pc-categories button")
    .filter({ hasText: "메인보드" })
    .click();
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  await page.locator(".pc-product-row .pc-add").click();
  await expect(page.locator("#manualCompatibility")).toContainText(
    "호환되지 않습니다",
  );
  await page
    .locator(".pc-categories button")
    .filter({ hasText: "GPU" })
    .click();
  await expect(
    page.locator(".pc-chip").filter({ hasText: /^RTX 40$/ }),
  ).toBeVisible();
  await page
    .locator(".pc-chip")
    .filter({ hasText: /^RTX 40$/ })
    .click();
  await page
    .locator(".pc-chip")
    .filter({ hasText: /^RTX 4070 Super$/ })
    .click();
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  await page.locator(".pc-product-row .pc-add").click();
  await page
    .locator(".pc-categories button")
    .filter({ hasText: /^RAM$/ })
    .click();
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  await page.locator(".pc-product-row .pc-add").click();
  await expect(page.locator("#csGameChart")).toContainText("80 fps");
  await page.locator("#csGameSelect").focus();
  await page.keyboard.press("ArrowDown");
  await expect(page.locator(".game-picker-options")).toBeVisible();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Escape");
  await expect(page.locator(".game-picker-options")).toBeHidden();
  await expect(page.locator("#csGameSelect")).toBeFocused();
  await page.locator("#csGameChart .graphics-toggle").click();
  await expect(page.locator(".graphics-panel")).toContainText(
    "렌더링 예상 100 FPS",
  );
  await expect(page.locator(".graphics-panel")).toContainText(
    "실측값이 아닙니다",
  );
  await expect(page.locator(".graphics-panel")).toContainText(
    "다른 게임의 실측 기준",
  );
  await expect(page.locator(".graphics-panel a")).toHaveAttribute(
    "href",
    "https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5090-test.91081/seite-8",
  );
  fpsResult = {
    ...fps,
    graphics_modes: [
      {
        id: "upscale_unavailable",
        supported: false,
        method: "unavailable",
        unavailable_reason: "missing_evidence",
        note: "기능은 지원되지만 검증된 Quality 전후 측정 자료가 없습니다.",
      },
    ],
  };
  await page.locator('#csResRow [data-res="2160"]').click();
  await expect(page.locator("#csGameChart")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  await page.locator("#csGameChart .graphics-toggle").click();
  await expect(page.locator(".graphics-panel")).toContainText(
    "검증된 Quality 전후 측정 자료가 없습니다",
  );
  await expect(page.locator(".graphics-panel")).not.toContainText(
    "지원이 확인된 DLSS/FSR",
  );
  fpsResult = fps;
  await page.locator('#csResRow [data-res="1440"]').click();
  await page
    .locator(".pc-chip")
    .filter({ hasText: /^DDR5$/ })
    .click();
  await expect(
    page.locator(".pc-chip").filter({ hasText: /^DDR5$/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  await page.locator("#loadMoreProductsBtn").click();
  await expect(page.locator("#loadMoreProductsBtn")).toHaveCount(0);
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  const moreRequest = requests
    .map((url) => new URL(url))
    .find(
      (url) =>
        url.pathname === "/api/products" &&
        url.searchParams.get("type") === "ram" &&
        url.searchParams.get("page") === "2",
    );
  if (
    moreRequest?.searchParams.get("cursor") !== "fixed-cursor" ||
    moreRequest?.searchParams.get("limit") !== "50"
  )
    throw new Error("Pagination cursor or page size changed");
  await page.locator("#productSearchInput").fill("느린 검색");
  const slowRequest = page.waitForRequest(
    (request) =>
      new URL(request.url()).searchParams.get("query") === "느린 검색",
  );
  await page.locator("#refreshProductsBtn").click();
  await slowRequest;
  await page.locator("#productSearchInput").fill("최신 검색");
  await page.locator("#refreshProductsBtn").click();
  await expect(page.locator(".pc-product-row")).toContainText("최신 검색");
  await page.waitForTimeout(450);
  await expect(page.locator(".pc-product-row")).toContainText("최신 검색");
  await page.locator("#productSearchInput").fill("판매처 오류");
  await page.locator("#refreshProductsBtn").click();
  await expect(
    page.getByRole("button", { name: "판매처 다시 확인" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "판매처 다시 확인" }).click();
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  await page.locator("#productSearchInput").fill("시간 초과");
  await page.locator("#refreshProductsBtn").click();
  await expect(page.locator(".pc-product-list")).toContainText("시간");
  await page.locator("#productSearchInput").fill("빈 결과");
  await page.locator("#refreshProductsBtn").click();
  await expect(
    page.getByRole("button", { name: "선택 조건 초기화", exact: true }),
  ).toBeVisible();
  await page.locator("#productSearchInput").fill("Samsung");
  await page.locator("#refreshProductsBtn").click();
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  await page.locator("#productSearchInput").fill("Samsung");
  await page.locator("#refreshProductsBtn").click();
  await page.locator("#productSourceSelect").selectOption("danawa");
  await page.locator("#productSortSelect").selectOption("price_asc");
  await expect(page.locator("#productBrowseNote")).not.toContainText(
    "검색하고",
  );
  await page.locator("#csModeWork").click();
  await expect(page.locator("#csWorkChart")).toContainText("4K 영상 편집");
  await page.waitForTimeout(300);
  await page.screenshot({
    path: "/tmp/site2-after-desktop.png",
    fullPage: false,
  });
  await page.locator("#viewAiBtn").click();
  await expect(page.locator("#recommendSection")).toBeVisible();
  await page
    .locator("#budgetChoices button")
    .filter({ hasText: "200~300만원" })
    .click();
  await page.locator("#resChoices button").filter({ hasText: "QHD" }).click();
  await page.locator("#submitBtn").click();
  await page.locator("#resetBtn").click();
  await expect(page.locator("#placeholder")).toBeVisible();
  await page.waitForTimeout(250);
  await expect(page.locator(".card")).toHaveCount(0);
  await page
    .locator("#budgetChoices button")
    .filter({ hasText: "200~300만원" })
    .click();
  await page.locator("#submitBtn").click();
  await expect(page.locator(".cards>.card")).toHaveCount(3);
  await expect(page.locator(".card.low .tier-badge")).toHaveText("₩600,000");
  await page.locator("#viewCustomBtn").click();
  await expect(page.locator("#productSearchInput")).toHaveValue("Samsung");
  await expect(page.locator("#productSourceSelect")).toHaveValue("danawa");
  await expect(page.locator("#csModeWork")).toHaveClass(/active/);
  await page.locator("#viewAiBtn").click();
  await expect(
    page.locator("#budgetChoices button").filter({ hasText: "200~300만원" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.locator(".card.low .part-row").first().hover();
  await expect(page.locator(".part-preview-popover")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".part-preview-popover")).toHaveCount(0);
  await page.locator(".card.mid [data-import-tier]").click();
  await expect(page.locator("#viewCustomBtn")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator(".pc-cart-item.has-selection")).toHaveCount(6);
  await expect(page.locator("#manualCompatibility")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".pc-mobile-cart-bar")).toBeVisible();
  await page.waitForTimeout(300);
  const mobileBar = await page.locator(".pc-mobile-cart-bar").boundingBox();
  if (!mobileBar || mobileBar.y + mobileBar.height > 844 || mobileBar.y < 720)
    throw new Error(
      "Mobile cart bar is not anchored to the viewport " +
        JSON.stringify({
          mobileBar,
          ancestors: await page
            .locator(".pc-mobile-cart-bar")
            .evaluate((el) => {
              const result = [];
              for (let node = el; node; node = node.parentElement)
                result.push({
                  class: node.className,
                  transform: getComputedStyle(node).transform,
                  position: getComputedStyle(node).position,
                });
              return result;
            }),
        }),
    );
  await page.screenshot({
    path: "/tmp/site2-after-mobile.png",
    fullPage: false,
  });
  if (
    await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
  )
    throw new Error("Mobile overflow");
  await page.locator(".pc-mobile-cart-bar").click();
  const estimate = page.locator(".pc-estimate");
  await estimate.scrollIntoViewIfNeeded();
  await estimate.focus();
  await page.keyboard.press("End");
  await page.waitForTimeout(300);
  if (
    await estimate.evaluate(
      (element) =>
        element.scrollHeight > element.clientHeight && element.scrollTop === 0,
    )
  )
    throw new Error("Keyboard did not scroll the estimate");
  await page.keyboard.press("Home");
  await page.waitForTimeout(300);
  await page
    .getByRole("button", { name: "RAM 선택 해제", exact: true })
    .click();
  await expect(page.locator(".pc-cart-item.has-selection")).toHaveCount(5);
  await page.getByRole("button", { name: "전체 비우기", exact: true }).click();
  await expect(page.locator(".pc-cart-item.has-selection")).toHaveCount(0);
  for (const label of ["SSD", "HDD", "파워", "케이스", "소프트웨어"]) {
    await page
      .locator(".pc-categories button")
      .filter({ hasText: new RegExp("^" + label + "$") })
      .click();
    await expect(page.locator(".pc-product-row")).toHaveCount(1);
    await expect(page.locator("#builderCategoryTitle")).toHaveText(label);
  }
  if (await page.locator("vite-error-overlay").count())
    throw new Error("Vite error overlay");
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(
    JSON.stringify(
      {
        passed: true,
        url: page.url(),
        title: await page.title(),
        viewports: ["1440x1000", "390x844"],
        errors,
        checks: [
          "AI initial and manual navigation",
          "all nine categories",
          "latest product result",
          "socket warning",
          "exact GPU hierarchy",
          "FPS and lazy graphics",
          "work chart",
          "query/source/sort",
          "AI cancellation reset",
          "ordered tiers",
          "screen input preservation",
          "exact recommendation import",
          "composed filters and deduplicated cursor pagination",
          "rapid search ignores late results",
          "provider retry, deadline and empty result messages",
          "mobile keyboard scroll, deselection and clear build",
          "all remaining storage, power, case and software categories",
        ],
        screenshots: [
          "/tmp/site2-after-desktop.png",
          "/tmp/site2-after-mobile.png",
        ],
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
