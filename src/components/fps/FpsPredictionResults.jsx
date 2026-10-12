import React, { useId, useState } from "react";
import { lowOneDetails } from "../../domain/lowOne.js";
import { nonNegativeNumber as numeric } from "../../domain/numbers.js";
import { safeExternalUrl as externalLink } from "../../domain/urls.js";
import "./fps-results.css";
import FpsValue from "./FpsValue.jsx";
import BottleneckHelp from "./BottleneckHelp.jsx";
import RayTracingPanel from "./RayTracingPanel.jsx";

const OPTIONS = [
  ["low", "저옵", "Low"],
  ["medium", "중옵", "Medium"],
  ["high", "고옵", "High"],
  ["ultra", "최고옵", "Ultra"],
];
const METHODS = {
  measured_benchmark: "동일 CPU·GPU 실측 참고",
  benchmark_calibrated: "실측 기반 보정 추정",
  model_estimate: "모델 추정 · 실측 자료 없음",
  mode_measurement: "해당 렌더링 모드 실측 참고",
  mode_calibrated_estimate: "실측 기반 렌더링 보정 추정",
  workload_estimate: "실측 처리 비용을 반영한 추정",
};
const CONFIDENCE = { high: "높음", medium: "보통", low: "낮음" };
const FORMAT = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1 });

function Evidence({ evidence }) {
  if (!evidence) return <p>이 옵션의 계산 근거 자료가 없습니다.</p>;
  const source = externalLink(evidence.source_url);
  const minimum = numeric(evidence.range?.min);
  const maximum = numeric(evidence.range?.max);
  const notes = Array.isArray(evidence.notes)
    ? [...new Set(evidence.notes.filter((note) => typeof note === "string"))]
    : [];
  return (
    <div className="fpr-evidence-body">
      <p className="fpr-evidence-method">
        {METHODS[evidence.method] || "예측 근거 확인 필요"}
        {CONFIDENCE[evidence.confidence]
          ? ` · 신뢰 수준 ${CONFIDENCE[evidence.confidence]}`
          : ""}
      </p>
      {evidence.conditions ? <p>{evidence.conditions}</p> : null}
      {evidence.reference_cpu || evidence.reference_gpu ? (
        <p>
          기준 구성 ·{" "}
          {[evidence.reference_cpu, evidence.reference_gpu]
            .filter(Boolean)
            .join(" / ")}
        </p>
      ) : null}
      {minimum !== null && maximum !== null ? (
        <p>
          참고 예상 범위 {FORMAT.format(minimum)}–{FORMAT.format(maximum)} FPS
          <span className="fpr-range-note">
            {" "}
            · 환경 차이를 고려한 범위이며 통계적 신뢰구간은 아닙니다.
          </span>
        </p>
      ) : null}
      {source ? (
        <a href={source} target="_blank" rel="noopener noreferrer">
          {evidence.source_title || "벤치마크 출처 확인"} ↗
        </a>
      ) : null}
      {notes.length ? (
        <ul>
          {notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function RenderingModes({ fps }) {
  const [chosen, setChosen] = useState("native");
  const headingId = useId();
  const modeRows = Array.isArray(fps?.graphics_modes) ? fps.graphics_modes : [];
  const technology =
    modeRows.find((row) => row.technology)?.technology || "DLSS / FSR";
  const modes = [
    ["native", "기본 · Native"],
    ["upscale", `${technology} Quality`],
    ["fg2", "프레임 생성 · FG 2×"],
    ["mfg4", "다중 프레임 생성 · MFG 4×"],
  ].map(([id, label]) => {
    const row =
      modeRows.find((item) => item.id === id) ||
      (id === "native"
        ? {
            id,
            label,
            supported: true,
            avg_fps: fps?.fps_by_option?.high,
            render_fps: fps?.fps_by_option?.high,
            method: fps?.fps_source,
          }
        : null);
    const unavailable = modeRows.find(
      (item) => item.id === `${id}_unavailable`,
    );
    return {
      id,
      label:
        id === "upscale" ? row?.label || unavailable?.label || label : label,
      row,
      available: Boolean(row?.supported && numeric(row.avg_fps) !== null),
      reason:
        unavailable?.note ||
        row?.note ||
        "이 게임·GPU 조합의 기능 지원 또는 검증 자료가 확인되지 않아 예측값을 제공하지 않습니다.",
    };
  });
  const selected =
    modes.find((mode) => mode.id === chosen && mode.available) ||
    modes.find((mode) => mode.available);
  const row = selected?.row;
  const generated = Boolean(row?.generated);
  const low =
    selected?.id === "native" ? lowOneDetails(fps).value : row?.low1_fps;
  const sources = [
    ...new Set(
      [
        ...(Array.isArray(row?.calibration_sources)
          ? row.calibration_sources
          : []),
        row?.source_url,
      ]
        .map(externalLink)
        .filter(Boolean),
    ),
  ];
  const minimum = numeric(row?.range?.min),
    maximum = numeric(row?.range?.max);
  return (
    <section
      className="fpr-extra-section fpr-rendering"
      aria-labelledby={headingId}
    >
      <div className="fpr-options-heading">
        <h3 id={headingId}>DLSS / FSR · 프레임 생성</h3>
        <span className="fpr-section-tag">고옵 · High 기준</span>
      </div>
      <p className="fpr-section-description">
        위 표는 원본 해상도 기준입니다. 아래에서 지원되는 렌더링 모드를 따로
        비교할 수 있어요.
      </p>
      <div
        className="fpr-mode-buttons"
        role="group"
        aria-label="렌더링 모드 선택"
      >
        {modes.map((mode) => (
          <button
            key={mode.id}
            type="button"
            disabled={!mode.available}
            aria-pressed={selected?.id === mode.id}
            onClick={() => setChosen(mode.id)}
          >
            {mode.label}
          </button>
        ))}
      </div>
      {row ? (
        <div className="fpr-mode-panel">
          <div className="fpr-mode-heading">
            <h4>{row.label || selected.label}</h4>
            <span>{METHODS[row.method] || "예측 근거 확인 필요"}</span>
          </div>
          <div className="fpr-mode-values">
            <div>
              <span>
                {generated ? "생성 프레임 포함 · 표시 FPS" : "평균 FPS"}
              </span>
              <FpsValue value={row.avg_fps} />
            </div>
            {generated ? (
              <div>
                <span>게임이 실제 렌더링하는 FPS</span>
                <FpsValue value={row.render_fps} />
              </div>
            ) : null}
            <div>
              <span>1% Low</span>
              <FpsValue value={low} />
            </div>
          </div>
          {numeric(low) === null ? (
            <p className="fpr-footnote">
              이 렌더링 모드의 1% Low 자료가 없어 별도로 계산하지 않습니다.
            </p>
          ) : null}
          {generated ? (
            <p className="fpr-footnote">
              생성된 프레임을 포함한 표시 FPS는 입력 반응 속도나 실제 렌더링
              성능과 다릅니다.
            </p>
          ) : null}
          {minimum !== null && maximum !== null ? (
            <p className="fpr-footnote">
              참고 예상 범위 {FORMAT.format(minimum)}–{FORMAT.format(maximum)}{" "}
              FPS · 통계적 신뢰구간이 아닙니다.
            </p>
          ) : null}
          {row.calibration_basis ? (
            <p className="fpr-mode-basis">{row.calibration_basis}</p>
          ) : null}
          {row.calibration_workload_note ? (
            <p className="fpr-footnote">{row.calibration_workload_note}</p>
          ) : null}
          {row.support_note ? (
            <p className="fpr-footnote">{row.support_note}</p>
          ) : null}
          {row.note ? <p className="fpr-footnote">{row.note}</p> : null}
          {sources.length ? (
            <div className="fpr-source-links">
              {sources.map((source, index) => (
                <a
                  key={source}
                  href={source}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  측정 출처 {index + 1} ↗
                </a>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <p className="fpr-notice">렌더링 모드별 예상 성능 자료가 없습니다.</p>
      )}
      {modes.some((mode) => !mode.available) ? (
        <details className="fpr-unavailable">
          <summary>선택할 수 없는 모드와 사유</summary>
          <ul>
            {modes
              .filter((mode) => !mode.available)
              .map((mode) => (
                <li key={mode.id}>
                  <strong>{mode.label}</strong> · {mode.reason}
                </li>
              ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

function BottleneckPanel({ fps }) {
  const [option, setOption] = useState("high");
  const headingId = useId();
  const row =
    fps?.bottleneck_by_option?.[option] ||
    (option === "high" ? fps?.bottleneck : null);
  const cap = numeric(fps?.frame_cap),
    average = numeric(fps?.fps_by_option?.[option]);
  const capped = cap !== null && cap > 0 && average !== null && average >= cap;
  const compared = row?.method === "matched_hardware_comparison";
  const limits = [
    {
      key: "cpu",
      label: "CPU",
      value: row?.cpu_percent ?? row?.cpu_penalty_pct,
      ceiling: compared ? row?.cpu_reference_fps : row?.cpu_fps_ceiling,
    },
    {
      key: "gpu",
      label: "GPU",
      value: row?.gpu_percent ?? row?.gpu_penalty_pct,
      ceiling: compared ? row?.gpu_reference_fps : row?.gpu_fps_ceiling,
    },
  ];
  const limiting = {
    cpu: "CPU 처리 성능의 제한 영향이 더 큽니다.",
    gpu: "GPU 렌더링 성능의 제한 영향이 더 큽니다.",
    balanced: "CPU와 GPU의 성능 여유가 비교적 균형을 이룹니다.",
    frame_cap: "게임의 FPS 상한에 도달했습니다.",
    unknown: "병목을 판단할 비교 자료가 부족합니다.",
  }[row?.limiting_component];
  return (
    <section
      className="fpr-extra-section fpr-bottleneck"
      aria-labelledby={headingId}
    >
      <div className="fpr-options-heading">
        <h3 id={headingId}>CPU / GPU 병목 예측</h3>
        <span className="fpr-section-tag">
          {compared ? "Native · 실측 구성 비교" : "Native · 추정값"}
        </span>
      </div>
      <div
        className="fpr-option-buttons"
        role="group"
        aria-label="병목 계산 그래픽 옵션"
      >
        {OPTIONS.map(([key, label]) => (
          <button
            type="button"
            key={key}
            aria-pressed={option === key}
            onClick={() => setOption(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {row ? (
        <>
          {limiting ? (
            <p className="fpr-bottleneck-summary">{limiting}</p>
          ) : null}
          <div className="fpr-bottleneck-values">
            {limits.map((limit) => {
              const percent = numeric(limit.value);
              return (
                <div className="fpr-limit" key={limit.key}>
                  <div className="fpr-limit-heading">
                    <strong>{limit.label} 제한 영향</strong>
                    <span>
                      {percent === null
                        ? "자료 없음"
                        : FORMAT.format(percent) + "%"}
                    </span>
                  </div>
                  <div
                    className={`fpr-bar${limit.key === "gpu" ? " fpr-bar-low" : ""}`}
                    aria-hidden="true"
                  >
                    <span
                      style={{ width: `${Math.min(100, percent ?? 0)}%` }}
                    />
                  </div>
                  <div className="fpr-ceiling">
                    <span>
                      {compared ? "비교 구성 FPS" : "단독 처리 상한 추정"}
                    </span>
                    <FpsValue value={limit.ceiling} />
                  </div>
                  <BottleneckHelp
                    component={limit.label}
                    compared={compared}
                    capped={capped}
                  />
                </div>
              );
            })}
          </div>
          {capped ? (
            <p className="fpr-notice">
              현재 예상 FPS는 게임의 {FORMAT.format(cap)} FPS 상한에
              도달했습니다. 현재 표시 성능은 게임의 상한에 제한됩니다.
            </p>
          ) : null}
          <p className="fpr-footnote">
            {compared
              ? "같은 테스트에서 해당 부품을 바꾼 최상위 실측 구성과의 차이입니다."
              : "선택한 게임·해상도·옵션의 처리 상한으로 추정한 값입니다."}{" "}
            실제 사용률이 아니며, DLSS / FSR·프레임 생성은 포함하지 않습니다.
          </p>
        </>
      ) : (
        <p className="fpr-notice">선택한 옵션의 병목 추정 자료가 없습니다.</p>
      )}
    </section>
  );
}

/** Independent calculator output; all values come from the shared FPS service. */
export default function FpsPredictionResults({
  fps,
  gameName,
  resolution,
  cpuName,
  gpuName,
  ramLabel,
}) {
  const headingId = useId();
  const rows = OPTIONS.map(([key, label, english]) => ({
    key,
    label,
    english,
    average: numeric(fps?.fps_by_option?.[key]),
    low: lowOneDetails(fps, key).value,
    evidence: fps?.option_evidence?.[key],
  }));
  const maximum = Math.max(
    1,
    ...rows.flatMap((row) => [row.average ?? 0, row.low ?? 0]),
  );
  const frameCap = numeric(fps?.frame_cap);
  const high = rows.find((row) => row.key === "high");
  const sourceLabel = fps?.fps_source_label || METHODS[high.evidence?.method];
  const displayResolution =
    resolution === "2160" ? "4K 2160p" : `${resolution}p`;
  return (
    <section className="fpr-results" aria-labelledby={headingId}>
      <header className="fpr-heading">
        <div>
          <p className="fpr-eyebrow">예측 결과</p>
          <h2 id={headingId}>{gameName || "선택한 게임"}</h2>
          <p className="fpr-context">
            {displayResolution} · 원본 해상도 · 레이 트레이싱 / 프레임 생성 OFF
          </p>
        </div>
        {sourceLabel ? (
          <span className="fpr-source-tag">{sourceLabel}</span>
        ) : null}
      </header>

      <div className="fpr-hardware">
        <span>
          <b>CPU</b> {cpuName || "선택 정보 없음"}
        </span>
        <span>
          <b>GPU</b> {gpuName || "선택 정보 없음"}
        </span>
        {ramLabel ? (
          <span>
            <b>RAM</b> {ramLabel} 기준
          </span>
        ) : null}
      </div>

      <div className="fpr-high-summary">
        <div className="fpr-summary-item">
          <span>고옵 · 평균 FPS</span>
          <FpsValue value={high.average} large />
          <p>일반적인 플레이 성능</p>
        </div>
        <div className="fpr-summary-item fpr-summary-low">
          <span>고옵 · 1% Low</span>
          <FpsValue value={high.low} large />
          <p>느린 1% 구간의 성능 · 높을수록 프레임 저하가 적어요</p>
        </div>
      </div>

      <div className="fpr-options-heading">
        <h3>그래픽 옵션별 예상 성능 · Native</h3>
        <div className="fpr-legend" aria-hidden="true">
          <span>
            <i />
            평균 FPS
          </span>
          <span>
            <i />
            1% Low
          </span>
        </div>
      </div>
      <table className="fpr-table">
        <caption className="fpr-sr-only">
          그래픽 옵션별 평균 FPS 및 1% Low 비교
        </caption>
        <thead>
          <tr>
            <th scope="col">옵션</th>
            <th scope="col">평균 FPS</th>
            <th scope="col">1% Low</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.key}
              className={row.key === "high" ? "fpr-row-high" : ""}
            >
              <th scope="row">
                {row.label}
                <small>{row.english}</small>
              </th>
              <td>
                <FpsValue value={row.average} />
                <div className="fpr-bar" aria-hidden="true">
                  <span
                    style={{
                      width: `${((row.average ?? 0) / maximum) * 100}%`,
                    }}
                  />
                </div>
              </td>
              <td>
                <FpsValue value={row.low} />
                <div className="fpr-bar fpr-bar-low" aria-hidden="true">
                  <span
                    style={{ width: `${((row.low ?? 0) / maximum) * 100}%` }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {frameCap !== null && frameCap > 0 ? (
        <p className="fpr-notice">
          이 게임의 기본 {FORMAT.format(frameCap)} FPS 제한을 반영했습니다.
        </p>
      ) : null}
      {fps?.preset_comparison_note ? (
        <p className="fpr-notice">{fps.preset_comparison_note}</p>
      ) : null}
      <p className="fpr-footnote">
        실제 성능은 게임 패치, 플레이 장면, 메모리와 드라이버에 따라 달라질 수
        있습니다. 1% Low는 순간 최저 FPS와 다릅니다.
      </p>

      <RayTracingPanel
        key={`rt-${fps?.game}-${resolution}-${cpuName}-${gpuName}`}
        fps={fps}
      />
      <RenderingModes
        key={`rendering-${fps?.game}-${resolution}-${cpuName}-${gpuName}`}
        fps={fps}
      />
      <BottleneckPanel
        key={`bottleneck-${fps?.game}-${resolution}-${cpuName}-${gpuName}`}
        fps={fps}
      />

      <details className="fpr-evidence">
        <summary>예측 근거와 옵션별 출처</summary>
        <div className="fpr-evidence-options">
          {rows.map((row) => (
            <section className="fpr-evidence-option" key={row.key}>
              <h4>
                {row.label} · {row.english}
              </h4>
              <Evidence evidence={row.evidence} />
            </section>
          ))}
        </div>
      </details>
    </section>
  );
}
