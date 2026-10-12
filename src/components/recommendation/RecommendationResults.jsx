import React, { lazy, Suspense, useEffect } from "react";
import { useApp } from "../../state/context.jsx";
import { Icon } from "../Controls.jsx";
import RecommendationProgress from "./RecommendationProgress.jsx";
const loadRecommendationCard = () => import("./RecommendationCard.jsx");
const RecommendationCard = lazy(loadRecommendationCard);

const TIERS = ["low", "mid", "high"];
function Placeholder() {
  return (
    <div className="ai-empty" id="placeholder">
      <div className="ai-empty-icon">
        <Icon name="cpu" size={36} />
      </div>
      <h4>어떤 PC가 필요하세요?</h4>
      <p>
        예산과 사용 목적을 선택하면
        <br />
        나에게 맞는 세 가지 구성을 비교할 수 있어요.
      </p>
      <span className="ai-empty-note">
        조건을 고른 뒤 ‘견적 분석하기’를 눌러주세요
      </span>
    </div>
  );
}
function LoadingResults() {
  return (
    <div className="cards ai-cards" aria-hidden="true">
      {TIERS.map((tier) => (
        <div
          className={`card ai-result-card ${tier}`}
          key={tier}
          aria-hidden="true"
        >
          <div className="skel ai-skeleton-title" />
          <div className="skel ai-skeleton-price" />
          {Array.from({ length: 6 }, (_, row) => (
            <div className="skel ai-skeleton-row" key={row} />
          ))}
        </div>
      ))}
    </div>
  );
}
export default function RecommendationResults() {
  const { state, store } = useApp(["recommendation", "lastRecommendation"]);
  const { loading, error, kind } = state.recommendation;
  const recommendation = state.lastRecommendation;
  useEffect(() => {
    if (loading) void loadRecommendationCard().catch(() => {});
  }, [loading]);
  return (
    <section
      className="ai-results ui-panel"
      id="resultsWrap"
      aria-labelledby="ai-results-heading"
    >
      <header className="ai-results-heading">
        <h3 id="ai-results-heading">추천 견적</h3>
        <p>
          {loading
            ? "조건에 맞는 부품과 성능을 확인하고 있어요"
            : "같은 조건으로 세 가지 구성을 비교해 보세요"}
        </p>
      </header>
      {loading ? (
        <RecommendationProgress
          hasPrevious={Boolean(recommendation)}
          startedAt={state.recommendation.startedAt}
          onCancel={store.cancelRecommendation}
        />
      ) : null}
      <div id="statusBox" aria-live="polite">
        {error ? (
          <div
            className={`ai-notice${kind === "cancelled" ? "" : " is-error"}`}
            role="status"
          >
            {error}
            {recommendation ? <p>아래는 이전에 완료한 분석 결과예요.</p> : null}
          </div>
        ) : !loading && recommendation?.warning ? (
          <div className="ai-notice" role="status">
            {recommendation.warning}
          </div>
        ) : null}
      </div>
      <div id="resultsContainer" aria-busy={loading}>
        {recommendation ? (
          <Suspense fallback={<LoadingResults />}>
            <div className="cards ai-cards">
              {TIERS.map((tier) => (
                <RecommendationCard
                  key={tier}
                  tier={tier}
                  result={recommendation.results?.[tier]}
                  input={recommendation.input}
                />
              ))}
            </div>
          </Suspense>
        ) : loading ? null : (
          <Placeholder />
        )}
      </div>
    </section>
  );
}
