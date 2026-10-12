import React, { useId, useState } from "react";
import FpsValue from "./FpsValue.jsx";
import { safeExternalUrl } from "../../domain/urls.js";

export default function RayTracingPanel({ fps }) {
  const [enabled, setEnabled] = useState(false);
  const id = useId();
  const row = fps?.graphics_modes?.find(
    (mode) => mode.id === "rt" || mode.id === "rt_unavailable",
  );
  if (!row?.game_supported) return null;
  const source = safeExternalUrl(row.source_url);
  return (
    <section className="fpr-extra-section fpr-rt" aria-labelledby={id}>
      <div className="fpr-options-heading">
        <h3 id={id}>레이 트레이싱 · RT</h3>
        <span className="fpr-section-tag">원본 해상도 · 프레임 생성 OFF</span>
      </div>
      <p className="fpr-section-description">
        빛과 그림자를 더 실제처럼 보여주는 기능이에요. 켜면 게임이 느려질 수
        있어요.
      </p>
      {row.supported ? (
        <>
          <div
            className="fpr-mode-buttons"
            role="group"
            aria-label="레이 트레이싱 선택"
          >
            <button
              type="button"
              aria-pressed={!enabled}
              onClick={() => setEnabled(false)}
            >
              RT 끔
            </button>
            <button
              type="button"
              aria-pressed={enabled}
              onClick={() => setEnabled(true)}
            >
              RT 켬
            </button>
          </div>
          <div className="fpr-mode-panel" aria-live="polite">
            <div className="fpr-mode-heading">
              <h4>{enabled ? "RT 켬" : "RT 끔"} · 원문 그래픽 설정</h4>
              <span>
                {row.method === "mode_measurement"
                  ? "실측 참고"
                  : "실측 기반 추정"}
              </span>
            </div>
            <div className="fpr-mode-values">
              <div>
                <span>평균 FPS</span>
                <FpsValue value={enabled ? row.avg_fps : row.rt_off_fps} />
              </div>
              <div>
                <span>1% Low</span>
                <FpsValue
                  value={enabled ? row.low1_fps : row.rt_off_low1_fps}
                />
              </div>
            </div>
            <p className="fpr-footnote">
              위 옵션 표와 별도로, 같은 테스트의 RT 전후를 비교해요. RT의 세부
              강도는 원문에 적혀 있지 않아요.
            </p>
            <details className="fpr-unavailable">
              <summary>RT 비교 기준 보기</summary>
              <p>
                {row.preset_label} · {row.reference_resolution}p ·
                DLSS/FSR·프레임 생성 OFF
              </p>
              <p>{row.reference_gpu} · Ryzen 7 9800X3D 기준 자료</p>
              {row.calibration_basis ? <p>{row.calibration_basis}</p> : null}
              {source ? (
                <div className="fpr-source-links">
                  <a href={source} target="_blank" rel="noopener noreferrer">
                    RT 측정 출처 ↗
                  </a>
                </div>
              ) : null}
            </details>
          </div>
        </>
      ) : (
        <p className="fpr-notice">{row.note}</p>
      )}
    </section>
  );
}
