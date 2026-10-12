import { test } from "node:test";
import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { transformSync } from "rolldown/utils";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

registerHooks({
  load(url, context, nextLoad) {
    if (url.endsWith(".css"))
      return { format: "module", source: "", shortCircuit: true };
    if (url.endsWith(".jsx")) {
      const path = fileURLToPath(url);
      return {
        format: "module",
        source: transformSync(path, readFileSync(path, "utf8"), {
          jsx: { runtime: "classic" },
        }).code,
        shortCircuit: true,
      };
    }
    return nextLoad(url, context);
  },
});
const { FpsChart } = await import("../src/components/Charts.jsx");
const { default: Results } =
  await import("../src/components/fps/FpsPredictionResults.jsx");
const { AppContext } = await import("../src/state/context.jsx");
const { default: RecommendationCard } =
  await import("../src/components/recommendation/RecommendationCard.jsx");
const { default: Performance } =
  await import("../src/components/Performance.jsx");
const { createAppStore } = await import("../src/state/store.js");
const fpsFor = (low, method, extra = {}) => ({
  game: "cyberpunk2077",
  fps_by_option: { low: 160, medium: 140, high: 100, ultra: 80 },
  low1_by_option: { low: null, medium: null, high: low, ultra: null },
  option_evidence: {
    high: { low1_method: method, ...extra },
  },
});
const render = (component, props) =>
  renderToStaticMarkup(React.createElement(component, props));

test("both shared chart layouts preserve missing lows without detailed evidence", () => {
  const fps = fpsFor(null, "unavailable", {
    low1_unavailable_reason: "선택 옵션의 검증된 1% Low 측정 자료가 없습니다.",
  });
  for (const compact of [false, true]) {
    const html = render(FpsChart, {
      fps,
      compact,
      game: "Test",
      resolution: "1440",
    });
    assert.match(html, /1% Low/);
    assert.match(html, /자료 없음/);
    assert.doesNotMatch(html, /선택 옵션의 검증된 1% Low|pc-low1-evidence/);
    assert.doesNotMatch(html, />0(?:\.0)?\s*(?:<[^>]+>)*FPS/);
    assert.doesNotMatch(html, /NaN/);
  }
});

test("calculator keeps measured and interpolated values without detailed labels", () => {
  const measured = render(Results, {
    fps: fpsFor(0, "measured"),
    resolution: "1080",
  });
  assert.doesNotMatch(measured, /1% Low · 실측 참고/);
  assert.match(measured, /0 <small>FPS<\/small>/);
  const interpolated = render(Results, {
    fps: fpsFor(54, "interpolated", { low1_range: { min: 43, max: 65 } }),
    resolution: "1440",
  });
  assert.match(interpolated, /54 <small>FPS<\/small>/);
  assert.doesNotMatch(interpolated, /1% Low · 실측 기반 추정|43–65 FPS/);
});

test("unavailable evidence suppresses stale low values in calculator summaries and table", () => {
  const fps = fpsFor(73, "unavailable", {
    low1_unavailable_reason: "검증된 보정 관계가 없습니다.",
  });
  const html = render(Results, { fps, resolution: "1440" });
  assert.match(html, /자료 없음/);
  assert.doesNotMatch(html, /검증된 보정 관계가 없습니다/);
  assert.doesNotMatch(html, /73 <small>FPS/);
});

test("low source and conditions stay hidden while average evidence remains available", () => {
  const fps = fpsFor(54, "interpolated", {
    source_url: "https://average.example/review",
    source_title: "Average review",
    low1_source_url: "https://low.example/measurement",
    low1_source_title: "Separate low measurement",
    low1_reference_resolution: "2160",
    low1_reference_preset: "High",
    low1_confidence: "low",
  });
  const html = render(Results, { fps, resolution: "1440" });
  assert.match(html, /href="https:\/\/average.example\/review"/);
  assert.doesNotMatch(html, /href="https:\/\/low.example\/measurement"/);
  assert.doesNotMatch(html, /Separate low measurement/);
  assert.doesNotMatch(html, /1% Low 기준 자료|신뢰 수준 낮음|pc-low1-evidence/);
});

test("AI recommendation and manual performance render null lows through their actual components", () => {
  const fps = fpsFor(null, "unavailable");
  const store = createAppStore();
  const parts = {
    gpu: { id: "gpu_rtx5070", name: "RTX 5070", price: 800000 },
    cpu: { id: "cpu_r5_7600", name: "Ryzen 7600", price: 200000 },
    ram: { id: "ram_32_ddr5", name: "DDR5 32GB", gb: 32, price: 100000 },
  };
  store.update({
    selected: parts,
    fps: { data: fps, loading: false, error: "" },
  });
  const children = [
    React.createElement(RecommendationCard, {
      tier: "mid",
      result: { parts, fps },
      input: { mode: "game", game: "cyberpunk2077", resolution: "1440" },
    }),
    React.createElement(Performance),
  ];
  for (const child of children) {
    const html = renderToStaticMarkup(
      React.createElement(AppContext.Provider, { value: store }, child),
    );
    assert.match(html, /1% Low/);
    assert.match(html, /자료 없음/);
    assert.doesNotMatch(html, /NaN/);
  }
});
