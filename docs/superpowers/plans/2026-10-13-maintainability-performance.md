# Maintainability and Performance Implementation Plan

> Execution: native, in the current clean checkout; existing regression coverage protects behavior-preserving extraction. Keep changes uncommitted for review.

**Goal:** Refactor application state responsibilities and remove avoidable product lookup work while preserving API, UI, prices, recommendation policy and FPS calculations.

**Architecture:** Compose focused state controllers through the existing `getState`/`publish` boundary. Preserve request cancellation and deduplication. Optimize price matching without changing candidate scores, tie order or validation, and validate SQLite cache revisions against committed WAL changes.

**Tech Stack:** React 18.3.1, Vite, Python 3.9+, SQLite; no new dependencies.

**Spec:** User request: “전체적으로 코드를 리펙토링하고 최적화해줘”. Existing tests and README define current behavior.

## Constraints and review focus

- Preserve late-response cancellation, retry, pagination and independent screen state.
- Preserve browse → pinned → reference precedence, duplicate handling and missing IDs.
- Preserve fuzzy-match exact priority, first tie, invalid-quote rejection and price freshness.
- Invalidate SQLite cache on WAL commits, replacement and deletion; unchanged reads reuse data.
- Do not refresh production data or change recommendation/FPS policy.

## Tasks

1. [x] Repair pre-existing budget-test fixtures to use an explicit compatible Gold PSU. Prove the three failing tests pass without changing production policy.
2. [x] Split `src/state/store.js` into product browsing, build selection, manual FPS and recommendation controllers. Move JSON transport into `requests.js`; preserve the public store methods. Verify Node regression suite.
3. [x] Remove full-list reconstruction from product ID lookups and repeated key parsing inside sort comparators. Add behavior/performance regression coverage and benchmark the lookup path.
4. [x] Score price-name candidates before expensive validation; preserve matching semantics. Add differential and rejected-candidate tests. Fix retail DB cache invalidation with WAL/inode stamps, backed by real temporary SQLite tests.
5. [x] Run full Python/Node suites, production build, existing browser flows and before/after benchmarks. Request a fresh independent code review and address material findings.

## Progress

- Baseline: Node 74/74; Python 377 tests, three existing budget fixture failures and two sandbox socket errors. Socket tests pass when local bind is permitted.
- Fixture root cause: tests use the first PSU (Standard), while `psu_candidates_for` requires Gold or better.
- Workspace decision: edits remain in the user's clean checkout to make the authorized changes directly reviewable; no branch, commit, publish or data refresh.
- Browser plugin not available; use repository Playwright scripts for existing desktop/mobile flows.

- Completed state extraction: store 672 → 167 lines; existing public methods and asynchronous latest-state reads retained.
- Optimization regression tests RED→GREEN: browse ID early exit; sort price property reads 1,299 → 150 for 50 products; fuzzy quote validation 202 → 2 for 201 candidates.
- SQLite WAL commit and same-size/same-mtime inode replacement tests reproduced stale reads before the fix and pass afterward.
- Independent review found exact-name lookup had lost its dictionary fast path. Restored it, added a failing-before/passing-after iteration guard, and reran the full suite. No other material findings; nothing declined or deferred.
- Final verification: Python 385/385; Node 77/77; production build and changed-JS formatting pass. Existing Chrome UI and real FPS API suites pass at desktop and mobile sizes.
- Browser timing note: two runs under concurrent validation timed out waiting for UI/timer transitions; isolated rerun passed unchanged. No production or test timeout changes were made.
- Same-data catalog responses have identical SHA-256 across ten runs; recommendation parts, totals and FPS match. Five paired catalog samples show cold medians 676.410 → 664.017 ms and warm 5.458 → 5.503 ms, so no material end-to-end speedup is claimed.
- All work remains uncommitted in the current checkout. Production data and dependencies are unchanged.
