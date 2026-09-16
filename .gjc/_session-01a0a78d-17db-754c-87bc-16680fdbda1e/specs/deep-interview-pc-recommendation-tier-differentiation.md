# Deep Interview Spec: PC Recommendation Tier Differentiation

## Metadata
- Interview ID: 574a7a53-e5d1-4e7b-b409-9126f1b1ff7e
- Rounds: 12
- Final Ambiguity Score: 3.3%
- Type: brownfield
- Generated: 2026-09-16T00:00:00Z
- Threshold: 0.05
- Threshold Source: default
- Initial Context Summarized: no
- Status: PASSED
- Auto-Answered Rounds: []
- Architect Failures: 0
- Lateral Reviews: 3 (initial→progress, progress→refined, refined→ready)
- Lateral Panel Failures: 0
- Refined Rounds: []
- Closure Overrides: none
- Restated Goal: 기존 Python 서버 구조를 유지하면서 PC 부품 추천 웹앱의 LOW/MID/HIGH 추천이 대표 3개 입력(90만원/1080p/60Hz, 150만원/1440p/144Hz, 250만원/4K/144Hz)에서 해상도·주사율 목표를 우선 반영하고, 성능 수치 비감소·등급별 설명·예산 초과 및 1프레임당 가격 악화 경고를 `/api/recommend`, UI 카드, 회귀 테스트로 검증 가능하게 개선한다.

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.97 | 0.35 | 0.34 |
| Constraint Clarity | 0.97 | 0.25 | 0.24 |
| Success Criteria | 0.97 | 0.25 | 0.24 |
| Context Clarity | 0.96 | 0.15 | 0.14 |
| **Total Clarity** | | | **0.97** |
| **Ambiguity** | | | **0.033** |

## Topology
| Component | Status | Description | Coverage / Deferral Note |
|-----------|--------|-------------|--------------------------|
| 추천 등급 차별화 | active | LOW/MID/HIGH가 같은 구성이나 체감상 비슷한 구성으로 수렴하지 않고 등급별로 명확히 다른 CPU/GPU/FPS/가격 특성을 갖게 한다. | Covered by pass rule: performance metrics are nondecreasing LOW→MID→HIGH, UI shows tier-difference explanation, and price-per-frame regression is warned. |
| 입력 조건 반영 강화 | active | CPU/GPU 성능, 예산 범위, 해상도, 주사율이 추천 후보 점수와 등급 선택에 실질적으로 영향을 주게 한다. | Covered by representative cases: 90만원/1080p/60Hz, 150만원/1440p/144Hz, 250만원/4K/144Hz. |
| 기존 구조 내 통합과 회귀 안전성 | active | 현재 Python 서버 구조와 기존 추천 API/UI 흐름을 유지하면서 추천 엔진과 관련 테스트 중심으로 변경한다. | Covered by `/api/recommend`, UI card, and regression-test acceptance; crawler/catalog/framework rewrite are excluded. |

Locked intent IDs preserved: artifact:recommendation-spec, artifact:regression-tests, surface:recommendation-results, surface:recommend-api, integration:python-server, integration:local-data, constraint:preserve-python-structure, constraint:no-direct-execution-during-interview.

| Locked ID | Category | Preserved statement |
|-----------|----------|---------------------|
| artifact:recommendation-spec | artifact | 추천 개선 요구사항 명세를 산출한다. |
| artifact:regression-tests | artifact | 등급 차별화와 입력 조건 반영을 검증하는 회귀 테스트 범위를 산출한다. |
| constraint:no-direct-execution-during-interview | constraint | deep-interview 중에는 구현하지 않고 명세만 확정한다. |
| constraint:preserve-python-structure | constraint | 기존 Flask/Python으로 표현한 Python 서버 구조를 유지한다. |
| integration:local-data | integration | 로컬 부품 카탈로그·벤치마크·가격 데이터를 추천 판단에 사용한다. |
| integration:python-server | integration | 기존 Python 서버 추천 엔진(`server_fixed.py`) 안에서 통합한다. |
| surface:recommend-api | surface | `/api/recommend` 추천 응답의 등급별 후보 선택이 개선 대상이다. |
| surface:recommendation-results | surface | LOW/MID/HIGH 추천 결과와 설명이 사용자에게 명확히 달라져 보이게 한다. |

## Established Facts
- Round 1: LOW/MID/HIGH가 충분히 다르려면 총 가격대와 성능이 함께 단계적으로 올라야 한다.
- Round 2: 예산과 목표 해상도·주사율이 충돌하면 목표 해상도·주사율을 가장 엄격히 지키고 필요하면 예산 초과를 허용한다.
- Round 3: 최소 합격 기준에는 `/api/recommend` 응답, 화면 카드, 회귀 테스트가 모두 포함되어야 한다.
- Round 4: LOW/MID/HIGH의 차이는 CPU/GPU 부품 자체보다 FPS 여유, 1% Low, 예산 초과액 같은 사용자 체감 지표가 다르면 충분하다.
- Round 5: 대표 예산·해상도·주사율 조합은 기본값으로 정하지 않고 사용자가 직접 지정해야 한다.
- Round 6: 대표 검증 조합은 3개만 둔다.
- Round 7: 대표 검증 조합은 90만원/1080p/60Hz, 150만원/1440p/144Hz, 250만원/4K/144Hz 세 가지로 한다.
- Round 8: 목표 해상도·주사율 달성을 위한 예산 초과에는 고정 상한을 두지 않지만, 예산 대비 효율이 나쁜 경우 경고한다.
- Round 9: 1프레임당 가격이 이전 티어보다 악화되면 성능 향상 대비 비용 증가가 크다고 사용자에게 알린다.
- Round 10: 기존 Python 서버 구조는 유지하되 추천 엔진, API 설명 필드, UI 카드 표시까지 변경할 수 있다.
- Round 11: 대표 케이스에서 LOW→MID→HIGH 성능 수치는 비감소면 충분하고, UI에서 등급별 차이 설명이 보이면 통과한다.
- Round 12: 외부 크롤러/가격 수집 로직, 부품 카탈로그 데이터 자체, 새 프레임워크나 대규모 서버 구조 변경은 이번 범위에서 제외한다.

## Trigger Metadata
No ambiguity-raising triggers were recorded. The ready-panel contrarian review exposed implementation risk, not a requirements contradiction: current code may use `budget_max` as a hard candidate filter and may lack cross-tier price-per-frame warnings. The spec therefore requires budget to be treated as scoring/annotation and requires structured price-per-frame regression warning evidence.

## Lateral Review Panel
- Round 2, initial→progress: panel focused the interview on API/UI/test proof and acceptable similarity cases.
- Round 4, progress→refined: panel focused the interview on representative input cases and numeric-ish user-visible metrics.
- Round 12, refined→ready: panel found no user-decision blocker, but required final spec constraints for soft-budget scoring/annotation, structured price-per-frame warning, and network-free fixture/catalog regression proof.

## Goal
Improve the existing PC parts recommendation webapp so LOW/MID/HIGH recommendations differ meaningfully for representative budget/resolution/refresh inputs while preserving the current Python server structure.

## Constraints
- Keep the existing Python server structure; no new framework or major server rewrite.
- Do not change external crawler/price collection logic.
- Do not change the component catalog data itself.
- Budget must not be a hard candidate-elimination cap when it conflicts with target resolution/refresh; treat it as scoring, annotation, and warning context.
- Recommendation proof must not depend on live network calls or real-time marketplace availability; use existing fixtures/catalogs or mocks.
- Different CPU/GPU model names are not required if user-perceived metrics and explanations distinguish tiers.

## Non-Goals
- Rebuilding the app in another framework.
- Refreshing or expanding product catalogs.
- Modifying external price crawlers or benchmark crawlers.
- Guaranteeing every tier uses different physical parts.
- Changing recommendation scope beyond the recommendation engine, API explanation fields, UI tier cards, and regression tests.

## Acceptance Criteria
- [ ] For `90만원 / 1080p / 60Hz`, `/api/recommend` returns LOW/MID/HIGH with user-visible performance metrics nondecreasing from LOW to MID to HIGH.
- [ ] For `150만원 / 1440p / 144Hz`, `/api/recommend` returns LOW/MID/HIGH with user-visible performance metrics nondecreasing from LOW to MID to HIGH.
- [ ] For `250만원 / 4K / 144Hz`, `/api/recommend` returns LOW/MID/HIGH with user-visible performance metrics nondecreasing from LOW to MID to HIGH.
- [ ] UI tier cards show an explanation of how each tier differs, even when CPU/GPU model names repeat.
- [ ] If price-per-frame worsens versus the previous tier, `/api/recommend` exposes a structured warning/explanation and the UI displays that the performance gain costs disproportionately more.
- [ ] If target resolution/refresh requires budget overrun, the recommendation remains eligible and shows budget overrun explicitly instead of being silently filtered out.
- [ ] Regression tests cover the three representative cases without network access.

## Deferrals
- Convergence pacing deferral: no min-round floor, score-drop cap, or dampening was used; bidirectional scoring was the pacing mechanism.
- No topology component was deferred.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| Tiers must use different parts. | Different parts can be artificial and reduce value. | Tiers may share parts if user-visible metrics and explanations distinguish them. |
| Budget should cap recommendations. | User wants resolution/refresh target to be stricter than budget. | Budget is scoring/annotation; no hard overrun cap. |
| Efficiency warning means overrun. | Overrun alone is not efficiency. | Warn when price-per-frame worsens versus the previous tier. |
| Success can be proved only in backend. | User asked for app-level improvement. | Proof includes API, UI cards, and regression tests. |

## Technical Context
- `server_fixed.py` exposes `/api/recommend` and contains the main recommendation pipeline: `tier_budget_for_user`, `build_tier_candidates`, `select_ordered_tier_plans`, `complete_recommendation_tiers`, and `recommend`.
- Relevant existing tests include `tests/test_recommendation_ordering.py`, `tests/test_tier_ordering.py`, `tests/test_recommendation_constraints.py`, and `tests/test_fps_and_fallback.py`.
- `README.md` already documents LOW→MID→HIGH ordering, same-configuration explanation, budget overrun display, and price-per-frame calculation.
- Ready-panel review highlighted that implementation should remove or bypass hard `budget_max` candidate filtering when it conflicts with target resolution/refresh and should add cross-tier price-per-frame regression warnings after final price refresh.

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| RecommendationTier | core domain | low, mid, high, totalPrice, performance | contains PCBuild |
| PCBuild | core domain | cpu, gpu, budget, fps, resolution, refresh | belongs to RecommendationTier |
| RecommendationInput | supporting | budget, resolution, refresh, cpu, gpu | influences tier selection |
| PerformanceTarget | constraint | resolution, refresh, targetFps | outranks Budget when they conflict |
| VerificationSurface | supporting | api, ui, regressionTests | proves recommendation success |
| UserPerceivedMetric | success metric | fpsHeadroom, onePercentLow, budgetOverrun, pricePerFrame | differentiates tiers |
| RepresentativeCase | test fixture | 900000/1080p/60Hz, 1500000/1440p/144Hz, 2500000/4K/144Hz | validates input sensitivity |
| EfficiencyWarning | user-facing signal | pricePerFrameRegression, message | appears on VerificationSurface |
| ChangeBoundary | constraint | recommendationEngine, apiExplanationFields, uiCards, tests | limits implementation scope |
| PassRule | acceptance rule | nonDecreasingPerformance, tierExplanationVisible | validates RecommendationTier |
| NonGoal | constraint | crawlerLogic, catalogData, frameworkRewrite | limits ChangeBoundary |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 3 | 3 | - | - | - |
| 2 | 4 | 1 | 0 | 3 | 75% |
| 3 | 5 | 1 | 0 | 4 | 80% |
| 4 | 6 | 1 | 0 | 5 | 83.33% |
| 5 | 7 | 1 | 0 | 6 | 85.71% |
| 6 | 7 | 0 | 0 | 7 | 100% |
| 7 | 7 | 0 | 0 | 7 | 100% |
| 8 | 7 | 0 | 0 | 7 | 100% |
| 9 | 8 | 1 | 0 | 7 | 87.5% |
| 10 | 9 | 1 | 0 | 8 | 88.89% |
| 11 | 10 | 1 | 0 | 9 | 90% |
| 12 | 11 | 1 | 0 | 10 | 90.91% |

## Interview Transcript
<details>
<summary>Full Q&A (12 rounds)</summary>

### Round 1
**Q:** LOW/MID/HIGH가 충분히 다르다의 기준은 무엇인가?
**A:** 총 가격대와 성능이 함께 단계적으로 올라야 한다.
**Ambiguity:** 64%

### Round 2
**Q:** 예산, 해상도, 주사율이 충돌할 때 무엇을 가장 엄격히 지켜야 하는가?
**A:** 목표 해상도·주사율을 가장 엄격히 지키고 필요하면 예산 초과를 허용한다.
**Ambiguity:** 51.9%

### Round 3
**Q:** 최소 합격 기준은 어디까지인가?
**A:** API·화면·회귀 테스트까지 모두 필요하다.
**Ambiguity:** 39.25%

### Round 4
**Q:** 일부 티어가 비슷해질 때 무엇이 충분한 차이인가?
**A:** 부품 차이보다 FPS 여유, 1% Low, 예산 초과액 같은 사용자 체감 지표가 다르면 충분하다.
**Ambiguity:** 29.5%

### Round 5
**Q:** 대표 입력과 합격 판정은 어느 형태로 고정할까?
**A:** 사용자가 직접 예산·해상도·주사율 조합을 지정해야 한다.
**Ambiguity:** 28.4%

### Round 6
**Q:** 대표 검증 조합은 몇 개인가?
**A:** 대표 케이스는 3개만 둔다.
**Ambiguity:** 27.5%

### Round 7
**Q:** 3개 대표 검증 조합 값은 무엇인가?
**A:** 90만원/1080p/60Hz, 150만원/1440p/144Hz, 250만원/4K/144Hz.
**Ambiguity:** 22.1%

### Round 8
**Q:** 예산 초과 허용 폭은 어디까지인가?
**A:** 초과 상한은 두지 않지만 예산 대비 효율이 나쁘면 경고한다.
**Ambiguity:** 18.3%

### Round 9
**Q:** 효율이 나쁘다는 경고는 무엇을 말해야 하는가?
**A:** 1프레임당 가격이 이전 티어보다 악화되면 성능 향상 대비 비용 증가가 크다고 알린다.
**Ambiguity:** 15.9%

### Round 10
**Q:** 변경 허용 범위는 어디까지인가?
**A:** 추천 엔진·API 설명 필드·UI 카드 표시까지 바꿔도 된다.
**Ambiguity:** 11.8%

### Round 11
**Q:** 대표 3개 케이스의 LOW→MID→HIGH 합격 규칙은 무엇인가?
**A:** 성능 수치는 비감소면 충분하고 UI에서 등급별 차이 설명이 보이면 통과한다.
**Ambiguity:** 7.8%

### Round 12
**Q:** 명시적으로 제외할 범위는 무엇인가?
**A:** 외부 크롤러/가격 수집 로직, 부품 카탈로그 데이터 자체, 새 프레임워크나 대규모 서버 구조 변경을 모두 제외한다.
**Ambiguity:** 3.3%

</details>
