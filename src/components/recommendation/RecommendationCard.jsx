import React from "react";
import { useApp } from "../../state/context.jsx";
import { BUILDER_PARTS, money, effectivePrice } from "../../domain/products.js";
import { pricePerFrame } from "../../domain/performance.js";
import { Compatibility } from "../Compatibility.jsx";
import { FpsChart, WorkChart } from "../Charts.jsx";
import RecommendationPart from "./RecommendationPart.jsx";

const TIERS = {
  low: { title: "실속 구성", description: "필요한 성능을 합리적인 가격으로" },
  mid: { title: "균형 구성", description: "가격과 성능을 균형 있게" },
  high: { title: "고성능 구성", description: "더 여유로운 성능을 원한다면" },
};

export default function RecommendationCard({ tier, result, input }) {
  const { state, store } = useApp([
    "games",
    "panelWork",
    "workProfiles",
    "recommendation",
  ]);
  const presentation = TIERS[tier];
  if (!result?.parts || !Object.keys(result.parts).length)
    return (
      <article
        className={"card ai-result-card " + tier}
        aria-label={presentation.title}
      >
        <h4 className="tier-name">{presentation.title}</h4>
        <p className="chart-note" style={{ marginTop: 8 }}>
          {result?.note ||
            "판매가와 제품 사진이 확인된 부품으로 조건에 맞는 구성을 찾지 못했습니다. 예산이나 선호 조건을 조정해주세요."}
        </p>
      </article>
    );
  const parts = result.parts,
    buildParts = Object.values(parts).filter((p) => p && typeof p === "object"),
    summedTotal = buildParts.reduce(
      (sum, p) => sum + (effectivePrice(p) || 0),
      0,
    ),
    missing = buildParts.some((p) => effectivePrice(p) == null),
    responseTotal = Number(
      result.totalPrice || result.total_price || result.debug?.total_price,
    ),
    total =
      Number.isFinite(responseTotal) && responseTotal > 0
        ? responseTotal
        : summedTotal,
    fps = result.fps || {},
    gameId = fps.game || input.game,
    gameName = state.games.find((g) => g.id === gameId)?.label || gameId,
    frameValue = missing ? null : pricePerFrame(total, fps.fps_by_option?.high),
    selected = input.work_profile || state.panelWork,
    entry = result.work_scores?.[selected] || {},
    score = typeof entry === "number" ? entry : Number(entry.score || 0),
    workValue = score / Math.max(1, total / 10000);
  return (
    <article
      className={"card ai-result-card " + tier}
      aria-label={presentation.title}
    >
      <header className="card-hdr">
        <h4 className="tier-name">{presentation.title}</h4>
        <p className="ai-tier-description">{presentation.description}</p>
        <strong className="tier-badge">{money(total)}</strong>
        <span className="ai-price-caption">
          부품 합계{missing ? " · 미확인 가격 제외" : ""}
        </span>
        {input.budget_mode === "unlimited" ? (
          <p className="ai-hint">금액 설정 안함 · 사양 우선 추천</p>
        ) : result.budget_overrun > 0 ? (
          <p className="ai-hint">
            목표 예산보다 {money(result.budget_overrun)} 초과
          </p>
        ) : null}
      </header>
      <div className="ai-parts">
        {BUILDER_PARTS.filter((meta) => parts[meta.key]).map((meta) => (
          <RecommendationPart
            key={meta.key}
            label={meta.cart}
            part={parts[meta.key]}
            type={meta.key}
          />
        ))}
      </div>
      <Compatibility parts={parts} />
      {result.same_configuration ? (
        <p className="chart-note">
          추가 업그레이드 후보가 없어 앞 등급과 동일한 구성입니다.
        </p>
      ) : null}
      <div className="ai-performance">
        {input.mode === "work" ? (
          <>
            <WorkChart
              profiles={state.workProfiles}
              selected={selected}
              parts={parts}
              scores={result.work_scores}
              compact
            />
            <div className="val-row">
              <div className="val-info">
                <div className="val-lbl">작업 가성비</div>
                <div className="val-sub">
                  작업 성능 1만원당 {workValue.toFixed(2)} 지수 ·{" "}
                  {workValue >= 3.5 ? "좋음" : workValue >= 2 ? "보통" : "낮음"}
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            <FpsChart
              fps={fps}
              game={gameName}
              resolution={input.resolution}
              compact
            />
            {fps.target_fps > 0 && fps.fps_by_option?.high != null ? (
              <p className="chart-note">
                목표 {fps.target_fps}fps · 풀옵 추정 기준{" "}
                {fps.fps_by_option.high >= fps.target_fps
                  ? "목표 충족"
                  : "목표 미달 · 옵션 조정이 필요할 수 있어요"}
              </p>
            ) : null}
            <div className="frame-value" aria-live="polite">
              <span className="frame-value-label">1프레임당 가격</span>
              <strong>
                {frameValue == null
                  ? "계산 대기"
                  : Math.round(frameValue).toLocaleString("ko-KR") + "원"}
              </strong>
              <span className="frame-value-detail">
                {gameName} · {input.resolution}p · 풀옵
              </span>
            </div>
          </>
        )}
      </div>
      <button
        type="button"
        className="tier-import-btn"
        data-import-tier={tier}
        disabled={state.recommendation.loading}
        onClick={() => store.importRecommendation(tier)}
      >
        직접 사양 선택
      </button>
    </article>
  );
}
