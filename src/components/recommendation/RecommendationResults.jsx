import React, { lazy, Suspense, useEffect, useState } from "react";
import { useApp } from "../../state/context.jsx";
import { Icon } from "../Controls.jsx";
const RecommendationCard = lazy(() => import("./RecommendationCard.jsx"));

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
function RecommendationProgress({ hasPrevious, startedAt, onCancel }) {
  const secondsSinceStart = () =>
    Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
  const [elapsed, setElapsed] = useState(secondsSinceStart);
  useEffect(() => {
    const updateElapsed = () =>
      setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    updateElapsed();
    const timer = setInterval(updateElapsed, 1000);
    return () => clearInterval(timer);
  }, [startedAt]);
  return (
    <div className="ai-progress">
      <div className="ai-progress-message" role="status">
        <strong>
          <span className="spinner" aria-hidden="true" />
          {hasPrevious
            ? "견적을 다시 분석하고 있어요"
            : "조건에 맞는 견적을 분석하고 있어요"}
          <span className="ai-progress-time" aria-hidden="true">
            {elapsed}초
          </span>
        </strong>
        <p>
          {elapsed >= 8
            ? "판매처 응답에 따라 시간이 더 걸릴 수 있어요. 조건을 유지한 채 취소할 수 있어요."
            : "판매가와 제품 사진, 부품 호환성과 예상 성능을 확인해요."}
        </p>
        {hasPrevious ? (
          <p>아래는 이전 분석 결과예요. 새 결과가 준비되면 바뀝니다.</p>
        ) : null}
      </div>
      <button type="button" className="ai-cancel" onClick={onCancel}>
        분석 취소
      </button>
    </div>
  );
}
export default function RecommendationResults() {
  const { state, store } = useApp(["recommendation", "lastRecommendation"]);
  const { loading, error, kind } = state.recommendation;
  const recommendation = state.lastRecommendation;
  return (
    <section
      className="ai-results"
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
        ) : loading ? (
          <LoadingResults />
        ) : (
          <Placeholder />
        )}
      </div>
    </section>
  );
}
