// Browser plugin unavailable: Playwright checks the production rendering API.
// Retail product lists are fixtures; FPS requests use the running Python server.
import { chromium, expect } from "@playwright/test";
import { gameCategoryFor } from "../src/state/store.js";

const origin = process.env.FRONTEND_URL || "http://127.0.0.1:4000";
const catalog = await (await fetch(origin + "/api/catalog?compact=1")).json();
let gpuId = "gpu_rtx5070";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});
await page.route("**/api/products?**", async (route) => {
  const type = new URL(route.request().url()).searchParams.get("type");
  const key = { cpu: "cpus", gpu: "gpus", ram: "rams" }[type];
  const id = { cpu: "cpu_r7_9800x3d", gpu: gpuId, ram: "ram_32_ddr5" }[type];
  const part = catalog[key]?.find((row) => row.id === id);
  await route.fulfill({
    json: {
      ok: true,
      status: "live",
      items: part ? [part] : [],
      has_more: false,
    },
  });
});
await page.route("**/api/part-image?**", (route) =>
  route.fulfill({
    contentType: "image/svg+xml",
    body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#dbeafe"/></svg>',
  }),
);
await page.route("**/api/price-lookup", (route) =>
  route.fulfill({ json: { results: [] } }),
);

async function selectPart(label) {
  await page
    .locator(".pc-categories button")
    .filter({ hasText: new RegExp("^" + label + "$") })
    .click();
  await expect(page.locator(".pc-product-row")).toHaveCount(1);
  await page.locator(".pc-product-row .pc-add").click();
}
async function selectGame(id) {
  await page
    .locator("#csGameCategorySelect")
    .selectOption(gameCategoryFor(id, catalog.games));
  await page.locator("#csGameSelect").click();
  await page.locator('.game-picker-options [data-value="' + id + '"]').click();
}
async function details() {
  await expect(page.locator("#csGameChart")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  const toggle = page.locator("#csGameChart .graphics-toggle");
  await expect(toggle).toBeVisible();
  if ((await toggle.getAttribute("aria-expanded")) !== "true")
    await toggle.click();
  await expect(page.locator(".graphics-panel")).toBeVisible();
  return page.locator(".graphics-panel");
}
try {
  await page.goto(origin);
  await selectPart("CPU");
  await selectPart("GPU");
  await selectPart("RAM");
  await page.locator('#csResRow [data-res="1440"]').click();
  await selectGame("expedition33");
  let panel = await details();
  await expect(
    panel.locator(".graphics-mode").filter({ hasText: "DLSS Quality" }).first(),
  ).toContainText("74 FPS");
  await expect(panel.locator(".graphics-mode").first()).toContainText("실측");
  await expect(panel).toContainText("131.8 FPS");
  await expect(panel).toContainText("237.1 FPS");
  await expect(
    panel.getByRole("link", { name: "측정 출처", exact: true }).first(),
  ).toHaveAttribute(
    "href",
    "https://www.thefpsreview.com/2025/11/17/overclocking-nvidia-geforce-rtx-5070/3/",
  );
  await panel.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "/tmp/site2-rendering-dlss.png",
    fullPage: true,
  });
  gpuId = "gpu_rx7800xt";
  // Changing category reuses its last page; force a fresh fixture query.
  await page
    .locator(".pc-categories button")
    .filter({ hasText: /^GPU$/ })
    .click();
  await page.locator("#productSearchInput").fill("AMD Radeon RX 7800 XT");
  await page.locator("#productSearchInput").press("Enter");
  await expect(page.locator(".pc-product-row")).toContainText("7800 XT");
  await page.locator(".pc-product-row .pc-add").click();
  await selectGame("starfield");
  panel = await details();
  await expect(panel).toContainText("FSR 3 Quality");
  await expect(panel).toContainText("123.4 FPS");
  await expect(panel).toContainText("220.2 FPS");
  await expect(panel).not.toContainText("MFG 4");
  await page.setViewportSize({ width: 390, height: 844 });
  await panel.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "/tmp/site2-rendering-fsr-mobile.png",
    fullPage: false,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  expect(errors).toEqual([]);
  console.log(
    JSON.stringify(
      {
        passed: true,
        api: "live",
        errors,
        checks: [
          "reviewed 74 FPS DLSS Quality observation",
          "separate FG2 and MFG4 estimates",
          "FSR3 uses AMD evidence",
          "FSR has no NVIDIA MFG option",
          "mobile details and source links",
        ],
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
