# Repository cleanup implementation plan

**Goal:** Simplify the current application while preserving its UI, API responses, recommendation results, and data.

**Architecture:** Keep the existing Python HTTP server and static frontend. Extract pure product metadata and identical retailer parsing helpers into focused modules, isolate frontend image rendering, and retain the current entry point and public imports.

**Tech stack:** Python standard library, optional BeautifulSoup, vanilla JavaScript, isolated React GPU selector.

**Spec:** User-provided cleanup request, 2026-09-23. Baseline source and existing Git changes are preserved at `/tmp/site2-cleanup-baseline-9xiv2111`.

## Constraints

- Preserve pre-existing uncommitted changes and application/data-generation behavior.
- Keep uncertain artifacts, import functionality, public API routes, and offline fallback catalogs.
- Do not merge differing crawler and server matching/price policies.
- Do not change CSS, recommendation rules, FPS formulas, or component compatibility.
- Remove generated files from Git tracking without deleting active local sessions.

## Execution

- [x] Preserve the working source and Git diffs; run Python/JavaScript baseline tests.
- [x] Start a separate baseline server and inspect desktop rendering.
- [x] Record deterministic catalog, metadata, FPS, and recommendation outputs for comparison.
- [x] Extract pure product metadata helpers; retain their existing server import surface.
- [x] Share the identical Danawa block/price parsers between crawler and server, with fixtures for both paths.
- [x] Extract shared image markup, preview, and fallback handling from frontend utilities without changing markup or event behavior.
- [x] Measure catalog work and optimize only a demonstrated repeated operation, with freshness/invalidation checks.
- [x] Remove obsolete extraction scripts, duplicate FPS fragment, empty files, and backup; stop tracking generated session/dependency files.
- [x] Document the retained entry point, module boundaries, dependencies, and test commands.
- [x] Run full tests, deterministic before/after comparisons, real API/browser smoke tests, and review the diff against the preserved working tree.

## Review focus

- All six major component categories retain product IDs, names, metadata, image URLs, and purchase URLs.
- GPU series/model selection still reaches the selected-component summary and price/FPS updates.
- Image errors retain the existing clean fallback in both manual and recommendation views.
- Cache reuse never hides file changes, changes price-age labels, or leaks caller mutations.
- Data files, model artifacts, incomplete product-import code, and pre-existing changes remain intact.

## Verification results

- Baseline: 82 Python tests and 7 JavaScript tests passed.
- Final: 86 Python tests and 7 JavaScript tests passed; syntax and CLI checks passed.
- Deterministic catalog, 12 FPS requests, and 3 recommendation requests match the baseline exactly.
- All 194 original server function/class bodies are unchanged across their retained/extracted locations.
- Saved-product responses match across all nine categories, including per-call price-age handling.
- Median of five runs of 100 warm GPU catalog reads: 439.39 ms before, 70.35 ms after.
- Headless Chrome checked six component selections, all available GPU series, totals/FPS, three recommendation tiers, images/fallbacks, product search/sort/purchase links, and a 390 px viewport.
- No unexpected browser JavaScript or HTTP errors; one cancelled superseded search and the deliberate fallback 404 were observed.
- Data/model files, CSS, GPU selector, and pre-existing image backend changes match the preserved working-tree baseline.
- Removed 16 obsolete source/backup/scaffold files; untracked 202 session files and 615 installed dependency files while retaining their local copies.

Remaining boundaries: the current server entry-point name and recommendation/FPS global state are retained; crawler-specific policies, dormant imports, offline catalogs, historical artifacts, and diagnostic utilities remain intentionally separate.
