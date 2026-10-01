# Refactor implementation ledger

Approved in-chat plan, 2026-10-01: full code refactor and UX optimization.
Constraints: React 18.3.1; Vite; stable HTTP API, ranking/FPS policy and design; results after retailer requests; no deployment or production data refresh.
Baseline: Node 32 pass; Python 158 tests, 9 failures caused by absent calibration data.
Tasks: fixtures; backend separation; Vite/React state migration; performance/HTTP; cleanup; browser/regression verification.
Ruling: Native worktree created but sandbox denies writes; using current checkout per using-git-worktrees fallback. All data writes in tests are redirected to temporary copies.
Ruling: Approved in-chat plan is the binding specification; no additional design approval cycle.

Task 1 complete: reviewed fixture isolates rendering calibration; Python159 pass (before extraction) and HTTP prediction persistence test RED→GREEN. Production data hashes unchanged.
Task 2 complete: service extraction into pcbuilder; Python159 pass after dependency qualification and spec-import patch adaptation.
Ruling: APIs now separate independent frontend, backend optimization and crawler work. Applying dispatching-parallel-agents instead of inline task execution; root owns integration and final verification.

Baseline assets: initial JS/CSS 387,488 bytes; sum of gzip encodings 113,896 bytes. Baseline static UI preserved in /tmp/site2-ui-baseline for visual comparison.
Cleanup: removed three unreferenced one-off source-analysis scripts; protected datasets/model artifacts retained.

Completed: shared crawler/server parsing; 19 unreachable helpers and import staging removed; Vite/explicit React state migration; cache/deadline/photo/FPS/HTTP optimizations; original icons moved without byte changes; fonts remain Pretendard with local hashed delivery.
Final verification: Python199, Node45, build and desktop/mobile production browser checks pass. Same-data catalog output hashes match. Initial JS/CSS gzip113,896→83,119B; repeated catalog194.685→4.013ms. Full results and limitations in refactor-verification.md and refactor-metrics.json.
Independent review: four important findings (unrelated-part FPS cancellation, failed-page retry, per-category query persistence, revision change during recommendation) fixed and verified; final review found no new important regressions.
