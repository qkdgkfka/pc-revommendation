import React, { useEffect, useRef, useState } from "react";
import { Icon } from "../Controls.jsx";
import "./recommendation-progress.css";

const INSIGHTS = [
  {
    icon: "mb",
    label: "부품 호환성",
    title: "좋은 부품도, 서로 잘 맞아야 하니까",
    description: "CPU와 메인보드, 메모리 규격까지 함께 살펴봐요.",
  },
  {
    icon: "gpu",
    label: "예상 성능",
    title: "내가 쓰는 용도에 맞는 성능으로",
    description: "선택한 용도와 목표에 맞춰 CPU·GPU의 균형을 살펴봐요.",
  },
  {
    icon: "search",
    label: "가격 비교",
    title: "성능은 든든하게, 선택은 합리적으로",
    description: "부품 가격과 예산을 함께 고려해 세 가지 구성을 추천해요.",
  },
];

export default function RecommendationProgress({
  hasPrevious,
  startedAt,
  onCancel,
}) {
  const panel = useRef(null);
  const secondsSinceStart = () =>
    Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
  const [elapsed, setElapsed] = useState(secondsSinceStart);
  useEffect(() => {
    const update = () => setElapsed(secondsSinceStart());
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [startedAt]);
  useEffect(() => {
    const bounds = panel.current?.getBoundingClientRect();
    if (bounds && (bounds.top < 0 || bounds.top > window.innerHeight / 2)) {
      panel.current.scrollIntoView({
        block: "start",
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
      });
    }
  }, []);
  // These rotate through useful context, not purported server completion stages.
  const active = Math.floor(elapsed / 5) % INSIGHTS.length;
  const insight = INSIGHTS[active];
  return (
    <div className="ai-progress" ref={panel}>
      <div className="analysis-illustration" aria-hidden="true">
        <div className="analysis-orbit analysis-orbit-outer" />
        <div className="analysis-orbit analysis-orbit-inner" />
        <div className="analysis-core">
          <div className="analysis-core-face">
            <Icon name="case" size={64} />
            <span className="analysis-core-led" />
          </div>
        </div>
        <div className="analysis-satellite analysis-satellite-cpu">
          <Icon name="cpu" size={30} />
          <span>CPU</span>
        </div>
        <div className="analysis-satellite analysis-satellite-gpu">
          <Icon name="gpu" size={32} />
          <span>GPU</span>
        </div>
        <div className="analysis-satellite analysis-satellite-ram">
          <Icon name="ram" size={28} />
          <span>RAM</span>
        </div>
        <div className="analysis-signal analysis-signal-one" />
        <div className="analysis-signal analysis-signal-two" />
        <div className="analysis-signal analysis-signal-three" />
      </div>
      <div className="analysis-heading" role="status">
        <h4>
          {hasPrevious
            ? "견적을 다시 분석하고 있어요"
            : "조건에 맞는 견적을 분석하고 있어요"}
        </h4>
        <p>
          {elapsed >= 8
            ? "판매처 응답에 따라 시간이 조금 더 걸릴 수 있어요."
            : "내게 맞는 부품들이 하나의 PC로 모이고 있어요."}
        </p>
      </div>
      <div className="analysis-insights">
        <div className="analysis-topics" aria-label="분석에서 고려하는 항목">
          {INSIGHTS.map((item, index) => (
            <span
              key={item.label}
              className={index === active ? "is-active" : ""}
            >
              <Icon name={item.icon} size={20} />
              {item.label}
            </span>
          ))}
        </div>
        <div className="analysis-tip" key={active}>
          <strong>{insight.title}</strong>
          <p>{insight.description}</p>
        </div>
      </div>
      <div className="analysis-waiting">
        <span className="analysis-live-dot" aria-hidden="true" />
        <span>분석 중</span>
        <span className="ai-progress-time" aria-hidden="true">
          {elapsed}초 경과
        </span>
      </div>
      <div
        className="analysis-track"
        role="progressbar"
        aria-label="견적 분석 중"
      >
        <span />
      </div>
      {hasPrevious ? (
        <p className="analysis-previous">
          아래는 이전 분석 결과예요. 새 결과가 준비되면 바뀝니다.
        </p>
      ) : null}
      <button type="button" className="ai-cancel" onClick={onCancel}>
        분석 취소
      </button>
    </div>
  );
}
