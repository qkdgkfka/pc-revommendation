// Browser plugin not available; Playwright checks the real shared FPS API.
import { chromium, expect } from "@playwright/test";
const origin = process.env.FRONTEND_URL || "http://127.0.0.1:4000";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
try {
  for (const viewport of [
    { width: 1440, height: 1100 },
    { width: 390, height: 844 },
  ]) {
    const page = await browser.newPage({ viewport });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(origin);
    await expect(page).toHaveTitle("PC 견적 도우미");
    await page
      .getByRole("button", { name: "게임별 FPS 예측", exact: true })
      .click();
    await expect(page.locator("#fpsCalculatorSection")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "FPS 예측하기", exact: true }),
    ).toBeDisabled();
    const cpu = page.getByRole("combobox", { name: "CPU", exact: true });
    await cpu.fill("인텔");
    await expect(page.getByRole("option").first()).toContainText("Intel");
    await cpu.dispatchEvent("keydown", { key: "Enter", isComposing: true });
    await expect(cpu).toHaveValue("인텔");
    await expect(cpu).toHaveAttribute("aria-expanded", "true");
    const cpuMatches = page
      .getByRole("listbox", { name: "CPU 목록" })
      .getByRole("option");
    const intelMatches = await cpuMatches.count();
    await cpu.press("End");
    await expect(cpu).toHaveAttribute(
      "aria-activedescendant",
      await cpuMatches.last().getAttribute("id"),
    );
    await cpu.press("Home");
    await expect(cpu).toHaveAttribute(
      "aria-activedescendant",
      await cpuMatches.first().getAttribute("id"),
    );
    await cpu.press("Escape");
    await expect(cpu).toHaveValue("");
    await expect(cpu).toHaveAttribute("aria-expanded", "false");
    await expect(cpuMatches).toHaveCount(0);
    await cpu.press("ArrowDown");
    await expect.poll(() => cpuMatches.count()).toBeGreaterThan(intelMatches);
    await expect(cpu).toHaveAttribute(
      "aria-activedescendant",
      await cpuMatches.first().getAttribute("id"),
    );
    await cpu.fill("9800");
    await expect(
      page.getByRole("option", { name: "AMD Ryzen 7 9800X3D", exact: true }),
    ).toBeVisible();
    await cpu.press("ArrowDown");
    await cpu.press("Enter");
    await expect(cpu).toHaveValue(/9800X3D/);
    const gpu = page.getByRole("combobox", { name: "GPU", exact: true });
    await gpu.fill("5070");
    await page
      .getByRole("option", { name: "NVIDIA GeForce RTX 5070", exact: true })
      .click();
    await page
      .getByRole("group", { name: "FPS 예측 해상도" })
      .getByRole("button", { name: "QHD · 1440p" })
      .click();
    const response = page.waitForResponse("**/api/estimate-fps");
    await page
      .getByRole("button", { name: "FPS 예측하기", exact: true })
      .click();
    const api = await response;
    expect(api.status()).toBe(200);
    const { fps } = await api.json();
    await expect(page.locator(".fpr-table tbody tr")).toHaveCount(4);
    const rows = page.locator(".fpr-table tbody tr");
    for (const [index, preset] of [
      "low",
      "medium",
      "high",
      "ultra",
    ].entries()) {
      const cells = rows.nth(index).locator("td");
      const number = (n) =>
        new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1 }).format(n);
      await expect(cells.nth(0)).toContainText(
        number(fps.fps_by_option[preset]),
      );
      await expect(cells.nth(1)).toContainText(
        fps.low1_by_option[preset] == null
          ? "자료 없음"
          : number(fps.low1_by_option[preset]),
      );
    }
    await expect(page.locator(".fpr-hardware")).toContainText("DDR5 32GB");
    await expect(
      page.locator(".fps-select-control.with-artwork img"),
    ).toHaveAttribute("src", /cyberpunk2077/);
    const rt = fps.graphics_modes.find((row) => row.id === "rt");
    expect(rt.avg_fps).toBe(44.9);
    const rtPanel = page.locator(".fpr-rt");
    await expect(rtPanel.locator(".fpr-mode-values")).toContainText("105.9");
    await rtPanel.getByRole("button", { name: "RT 켬", exact: true }).click();
    await expect(rtPanel.locator(".fpr-mode-values")).toContainText("44.9");
    await expect(rtPanel.locator(".fpr-mode-values")).toContainText("37.3");
    await expect(rtPanel).toContainText("세부 강도는 원문에 적혀 있지 않아요");
    await rtPanel.screenshot({ path: `/tmp/site2-rt-${viewport.width}.png` });
    await rtPanel.getByRole("button", { name: "RT 끔", exact: true }).click();
    await expect(rtPanel.locator(".fpr-mode-values")).toContainText("105.9");
    for (const component of ["CPU", "GPU"]) {
      const help = page.getByRole("button", {
        name: `${component} 제한 영향이란?`,
      });
      const content = page.locator(
        `[id="${await help.getAttribute("aria-controls")}"]`,
      );
      await expect(content).toBeHidden();
      await help.focus();
      await help.press("Enter");
      await expect(help).toHaveAttribute("aria-expanded", "true");
      await expect(content).toContainText(
        component === "CPU" ? "다음 장면을 준비" : "그림으로 그리는",
      );
      await expect(content).toContainText("사용률");
      await page.locator(".fpr-bottleneck").screenshot({
        path: `/tmp/site2-help-${component}-${viewport.width}.png`,
      });
      await help.click();
      await expect(content).toBeHidden();
    }
    const modes = page.getByRole("group", { name: "렌더링 모드 선택" });
    for (const id of ["upscale", "fg2", "mfg4"]) {
      const mode = fps.graphics_modes.find(
        (row) => row.id === id && row.supported,
      );
      expect(mode).toBeTruthy();
      const button =
        id === "upscale"
          ? modes.getByRole("button", { name: /DLSS.*Quality/ })
          : modes.getByRole("button", {
              name:
                id === "fg2"
                  ? "프레임 생성 · FG 2×"
                  : "다중 프레임 생성 · MFG 4×",
              exact: true,
            });
      await button.click();
      await expect(
        page.locator(".fpr-rendering .fpr-mode-values"),
      ).toContainText(String(mode.avg_fps));
      if (mode.generated) {
        await expect(
          page.locator(".fpr-rendering .fpr-mode-values"),
        ).toContainText("게임이 실제 렌더링하는 FPS");
        await expect(
          page.locator(".fpr-rendering .fpr-mode-values"),
        ).toContainText(String(mode.render_fps));
        await expect(
          page.locator(".fpr-rendering .fpr-mode-values"),
        ).toContainText("자료 없음");
      }
    }
    await page
      .getByRole("group", { name: "병목 계산 그래픽 옵션" })
      .getByRole("button", { name: "저옵", exact: true })
      .click();
    await expect(page.locator(".fpr-bottleneck-values")).toContainText(
      fps.bottleneck_by_option.low.cpu_percent + "%",
    );
    await page
      .getByRole("button", { name: "AI 자동 추천", exact: true })
      .click();
    await page
      .getByRole("button", { name: "게임별 FPS 예측", exact: true })
      .click();
    await expect(cpu).toHaveValue(/9800X3D/);
    await expect(rows).toHaveCount(4);
    // A new input must hide the old calculation before another request.
    await page
      .getByRole("group", { name: "FPS 예측 해상도" })
      .getByRole("button", { name: "4K · 2160p" })
      .click();
    await expect(rows).toHaveCount(0);
    // A failed API response must leave a visible retry path.
    await page.route(
      "**/api/estimate-fps",
      (route) =>
        route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ error: "테스트 연결 오류" }),
        }),
      { times: 1 },
    );
    await page
      .getByRole("button", { name: "FPS 예측하기", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText("테스트 연결 오류");
    await page.getByRole("button", { name: "다시 계산하기" }).click();
    await expect(rows).toHaveCount(4);
    // A capped model-estimate game exercises another game and DDR4 CPU.
    const game = page.getByRole("combobox", { name: "게임", exact: true });
    await game.fill("LoL");
    await expect(
      page.getByRole("option", { name: "리그 오브 레전드", exact: true }),
    ).toBeVisible();
    await game.fill("엘든");
    await page.getByRole("option", { name: "엘든 링", exact: true }).click();
    await cpu.fill("5600");
    await page
      .getByRole("option", { name: "AMD Ryzen 5 5600", exact: true })
      .click();
    await page
      .getByRole("button", { name: "FPS 예측하기", exact: true })
      .click();
    await expect(rows).toHaveCount(4);
    await expect(page.locator(".fpr-hardware")).toContainText("DDR4 32GB");
    await expect(page.locator(".fpr-notice").first()).toContainText("60 FPS");
    await expect(
      modes.getByRole("button", { name: "프레임 생성 · FG 2×", exact: true }),
    ).toBeDisabled();
    await page.locator(".fpr-evidence summary").click();
    await expect(page.locator(".fpr-evidence-option")).toHaveCount(4);
    await page.locator(".fpr-evidence summary").click();
    // Controlled CPU/GPU review comparisons use the actual paired FPS values.
    await game.fill("젠레스");
    await page
      .getByRole("option", { name: "젠레스 존 제로", exact: true })
      .click();
    await cpu.fill("14400F");
    await page
      .getByRole("option", { name: "Intel Core i5-14400F", exact: true })
      .click();
    await page
      .getByRole("group", { name: "FPS 예측 해상도" })
      .getByRole("button", { name: "FHD · 1080p" })
      .click();
    const measuredResponse = page.waitForResponse("**/api/estimate-fps");
    await page
      .getByRole("button", { name: "FPS 예측하기", exact: true })
      .click();
    const measured = (await (await measuredResponse).json()).fps;
    expect(measured.bottleneck.method).toBe("matched_hardware_comparison");
    expect(measured.bottleneck.cpu_percent).toBe(52.9);
    expect(measured.bottleneck.gpu_percent).toBe(2.6);
    await expect(page.locator(".fpr-bottleneck .fpr-section-tag")).toHaveText(
      "Native · 실측 구성 비교",
    );
    await expect(page.locator(".fpr-bottleneck-values")).toContainText("52.9%");
    await expect(page.locator(".fpr-bottleneck-values")).toContainText("2.6%");
    await expect(page.locator(".fpr-bottleneck-values")).toContainText(
      "비교 구성 FPS",
    );
    await expect(page.locator(".fpr-rt")).toContainText(
      "비교 측정 자료가 부족합니다",
    );
    await page.getByRole("button", { name: "CPU 제한 영향이란?" }).click();
    await expect(page.locator(".fpr-help-content").first()).toContainText(
      "바꿔 테스트한",
    );
    await expect(page.locator(".pc-low1-evidence")).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.locator(".fpr-heading").scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `/tmp/site2-fps-calculator-${viewport.width}.png`,
      fullPage: viewport.width > 720,
    });
    await game.fill("CS2");
    await page.getByRole("option", { name: "CS2", exact: true }).click();
    await page
      .getByRole("button", { name: "FPS 예측하기", exact: true })
      .click();
    await expect(page.locator(".fpr-table tbody tr")).toHaveCount(4);
    await expect(page.locator(".fpr-rt")).toHaveCount(0);
    expect(errors).toEqual([]);
    console.log(
      JSON.stringify({
        viewport,
        options: 4,
        averageAndLow: "API matched",
        retry: "passed",
        tabPersistence: "passed",
        measuredBottleneck: "API and paired review matched",
        rayTracing: "RT off/on API matched",
        help: "keyboard toggle and explanations passed",
        overflow: false,
        pageErrors: errors,
      }),
    );
    await page.close();
  }
} finally {
  await browser.close();
}
