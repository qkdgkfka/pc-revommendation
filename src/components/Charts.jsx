import React, { lazy, Suspense, useId, useState } from "react";
import { suitabilityFromScore, workScore } from "../domain/performance.js";
import { workFillClass } from "../domain/products.js";
const GraphicsDetails = lazy(() => import("./GraphicsDetails.jsx"));
function GraphicsToggle({ fps }) {
  const [open, setOpen] = useState(false),
    id = useId(),
    technology =
      (fps.graphics_modes || []).find((row) => row.technology)?.technology ||
      "업스케일링";
  return (
    <div className="graphics-details">
      <button
        type="button"
        className="graphics-toggle"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
      >
        {technology + " · 프레임 생성 " + (open ? "접기 −" : "보기 +")}
      </button>
      {open ? (
        <Suspense
          fallback={
            <p role="status" className="chart-note">
              그래픽 옵션을 불러오는 중…
            </p>
          }
        >
          <GraphicsDetails fps={fps} id={id} />
        </Suspense>
      ) : null}
    </div>
  );
}
export function FpsChart({ fps, game, resolution, compact = false }) {
  const values = fps?.fps_by_option,
    max = Math.max(
      ...Object.values(values || {})
        .map(Number)
        .filter(Number.isFinite),
      60,
    );
  if (!values)
    return (
      <p className="chart-note">해당 구성의 FPS 자료를 확인하지 못했습니다.</p>
    );
  return (
    <>
      <div className={compact ? "fps-section" : "chart-wrap"}>
        {compact ? (
          <div className="fps-hdr">
            <span className="fps-title">예상 FPS · {resolution}p</span>
            <span className="fps-tag">{game}</span>
          </div>
        ) : (
          <div className="chart-context">
            {game} · {resolution}p
          </div>
        )}
        {[
          ["low", "저옵"],
          ["medium", "중옵"],
          ["high", "풀옵"],
        ].map(([key, label]) => {
          const value = Number(values[key]);
          return (
            <div key={key} className={compact ? "fb-row" : "chart-row"}>
              <span className={compact ? "fb-lbl" : "chart-lbl"}>{label}</span>
              {values[key] != null && Number.isFinite(value) && value >= 0 ? (
                <>
                  <div className={compact ? "fb-bg" : "chart-bg"}>
                    <div
                      className={compact ? "fb-fill" : "chart-fill fps"}
                      style={{
                        width: Math.min(100, (value / max) * 100) + "%",
                      }}
                    />
                  </div>
                  <span className={compact ? "fb-val" : "chart-val"}>
                    {value}
                    {compact ? "fps" : " fps"}
                  </span>
                </>
              ) : (
                <span className="chart-note">측정 정보 없음</span>
              )}
            </div>
          );
        })}
        {fps.frame_cap ? (
          <div className="chart-note">
            게임 기본 {fps.frame_cap}fps 제한 반영
          </div>
        ) : null}
      </div>
      <GraphicsToggle key={fps.game + "-" + resolution} fps={fps} />
    </>
  );
}
export function WorkChart({
  profiles,
  selected,
  parts,
  scores,
  compact = false,
}) {
  return (
    <div className={compact ? "work-section" : "chart-wrap"}>
      {compact ? (
        <div className="work-hdr">
          작업 적합도 · {profiles[selected]?.name || "선택 작업"}
        </div>
      ) : null}
      {Object.entries(profiles).map(([key, profile]) => {
        const entry = scores?.[key],
          score =
            entry == null
              ? workScore(parts.gpu, parts.cpu, parts.ram, parts.storage, key)
              : typeof entry === "number"
                ? entry
                : Number(entry.score || 0),
          fit = entry?.label
            ? {
                label: entry.label,
                level: entry.level || suitabilityFromScore(score).level,
              }
            : suitabilityFromScore(score);
        return (
          <div className={compact ? "wb-row" : "chart-row"} key={key}>
            <span
              className={compact ? "wb-lbl" : "chart-lbl wide"}
              style={
                key === selected ? { fontWeight: 800, color: "#0d1b3e" } : {}
              }
            >
              {profile.name}
            </span>
            <div className={compact ? "wb-bg" : "chart-bg"}>
              <div
                className={
                  (compact ? "wb-fill " : "chart-fill ") + workFillClass(score)
                }
                style={{ width: score + "%" }}
              />
            </div>
            <span
              className={
                (compact ? "wb-val " : "chart-val fit-label ") + fit.level
              }
            >
              {fit.label}
            </span>
          </div>
        );
      })}
      <div className="chart-note">
        * 내부 점수를 5단계 적합도로 변환한 추정치입니다
      </div>
    </div>
  );
}
