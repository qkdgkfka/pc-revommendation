# Performance refactor implementation plan

> **For agentic workers:** Use superpowers:executing-plans; execute the authorized refactor in this session.

**Goal:** Preserve existing PC recommendation, manual selection, pricing, compatibility and FPS behavior while reducing initial downloads, repeated rendering and server work.

**Architecture:** Keep the current React external store and Python service APIs. Extract focused presentation modules, select only relevant store fields, defer manual resources, and reuse immutable derived data and prepared HTTP representations.

**Tech Stack:** React 18, Vite, Python 3.9+, SQLite, Node test runner, unittest, Playwright.

**Spec:** User request: refactor the whole project for clean code and loading performance while preserving functionality.

## Global constraints

- Preserve API routes, response shapes, price provenance, 24-hour freshness and recommendation/FPS policy.
- Preserve Korean copy, visual design, keyboard interactions and state across screen switches.
- No live data refresh, deployment or dependency upgrades.
- Existing checkout was clean at 491fbf1; implement in the attached isolated worktree, then apply verified changes to the user's checkout.

## Review focus

- Switching screens during pending requests must preserve selections and ignore stale responses.
- A store selector must return a stable snapshot without hiding relevant changes.
- Cached derived products must refresh after catalog, filter, selection or browse changes.
- Asset validators must update when file contents change and retain gzip/304 semantics.
- Font splitting must retain every original supported character and variable font weights.

### Task 1: Baseline and client state

- [x] Run baseline Node/Python suites and production build; record bundle and request timings outside the repository.
- [ ] Add regressions for no-op publications, atomic product responses and derived-domain reuse; observe failures.
- [ ] Extract initial state/catalog normalization, add stable field selectors, batch state publications and bound FPS cache.
- [ ] Run Node suite.

### Task 2: Screen modules and loading

- [ ] Extract shared controls, product image, work selector and manual categories/filters/search/results/cart components.
- [ ] Subscribe components to their own relevant fields, memoize stable screen boundaries, defer manual screen and CSS.
- [ ] Load product browsing only on first manual entry; verify no initial product request and preserved subsequent behavior in browser test.
- [ ] Split local font into Unicode subsets with full original character coverage and document reproducible generation.
- [ ] Build and compare initial downloaded resources.

### Task 3: Server response preparation

- [ ] Add regressions for validator reuse and cache invalidation during in-flight computation; observe failures.
- [ ] Extract HTTP representation/static asset handling from routing, cache validators, guard invalidated cache generations.
- [ ] Profile cold/warm catalog and recommendation paths; optimize demonstrated repeated work without changing results.
- [ ] Run Python suite and deterministic benchmarks.

### Task 4: Verification and delivery

- [ ] Run complete suites, production build, fixture browser tests on desktop/mobile and real API HTTP/rendering checks.
- [ ] Get an independent review of the final diff and fix material findings.
- [ ] Apply verified changes to the original checkout, verify unchanged user data and final build/tests, update maintenance documentation.

## Progress and decisions

- Baseline: 48 JavaScript and 229 Python tests pass. Initial JS 226.05 kB (gzip 76.59 kB), initial CSS 35.26 kB, variable font 2057.68 kB.
- Authorization: user explicitly requested implementation; execute directly without a redundant plan approval checkpoint.
- Browser plugin not available; use existing Playwright suites.
