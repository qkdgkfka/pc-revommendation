# Readability Refactor Implementation Plan

> Execution: independent backend/UI edits in parallel, with request lifecycle work and integration in the current clean checkout. Keep changes uncommitted for review.

**Goal:** Reduce repeated application code and clarify responsibilities while preserving existing behavior.

**Architecture:** Reuse existing React presentation components; centralize the shared request completion lifecycle; use explicit field mappings and one price-result formatter in Python.

**Tech Stack:** React 18, ES modules, Python 3.9+, SQLite; existing dependencies only.

**Spec:** User request: “전체적으로 코드 구조를 보고 리펙토링하고, 코드를 줄일 수 있으면 줄이면서 가독성을 좋게 하고, 리펙토링 해줘”. Existing public APIs and tests define behavior.

## Constraints and review focus

- Preserve UI markup, accessibility, labels and filter selection.
- Preserve request deduplication, synchronous loading publication and returned task identity.
- Ignore both success and failure of superseded or cancelled requests.
- Preserve validation failures, timeout messages and silent price lookup failures.
- Preserve price matching priority, result keys, None values and PSU field aliases.
- Keep catalogs, recommendation/FPS policy, dependencies and production data unchanged.

## Tasks

- [x] Reuse GameArtwork in GamePicker and consolidate filter chip markup in manual/Filters.jsx. Verify Node and identical rendered markup.
- [x] Consolidate repeated summary field mapping in pricing.py and price lookup result assembly in database.py. Verify exact/fuzzy paths and sparse summaries.
- [x] Add a shared request completion helper in requests.js and use it in the six state controllers. Verify duplicate, stale, failed and timed-out requests with meaningful regression tests.
- [x] Run full Node/Python suites, production build and existing desktop/mobile browser flows; request an independent review and resolve material findings.

## Progress

- Initial working tree clean; Node baseline 77/77 passed. Python baseline: 385 tests, only two local socket checks blocked by sandbox permissions.
- Existing architecture already separates domain, state, UI and server modules; retain these boundaries.
- Current checkout selected so authorized edits are directly reviewable; no branch, commit or publication.
- Browser plugin not available; use the repository's existing Playwright scripts.
- Existing tests cover behavior-preserving extractions; new tests target shared request lifecycle risks and payload shape, not implementation details.
- New request lifecycle tests: five failed before the shared helper existed, then all five passed; integrated Node suite 82/82 passed.
- Existing/current React markup identical for seven fixtures. Existing/current Python values and key order identical for 154 summaries and nine URL/exact/fuzzy price lookups; 59 focused tests passed.
- Full Python suite passed 385/385 with local socket permission. Production build passed. Chrome initially blocked by sandbox process permissions; rerun with permission passed.
- Existing frontend browser suite passed at 1440×1000 and 390×844 with no page/console errors. Real FPS calculator suite passed at 1440×1100 and 390×844, including API values, retry, tab persistence, ray tracing and keyboard help. Screenshots inspected; local verification server stopped afterward.
- Independent review found no production regression. It identified a test assertion swallowed by the intentional error handler; assertions now observe callbacks from outside the handler. Removing the success validity guard in a temporary module makes the strengthened test fail, while the actual implementation passes all 82 Node tests.
- Final production code delta: 164 lines added, 215 removed (51 fewer lines). Five focused lifecycle tests and maintenance documentation added. Changes remain uncommitted.
