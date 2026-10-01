import React from "react";
const display = (value) =>
  Number.isFinite(Number(value))
    ? Number(value).toLocaleString("ko-KR", { maximumFractionDigits: 1 })
    : "—";
/** Loaded only after the user expands graphics details. */
export default function GraphicsDetails({ fps, id }) {
  const rows = (fps.graphics_modes || []).filter(
    (row) => row.supported && ["upscale", "fg2", "mfg4"].includes(row.id),
  );
  const unavailable = (fps.graphics_modes || []).filter(
    (row) =>
      !row.supported &&
      ["upscale_unavailable", "fg2_unavailable", "mfg4_unavailable"].includes(
        row.id,
      ),
  );
  return (
    <div id={id} className="graphics-panel">
      {rows.length ? (
        rows.map((row) => (
          <div className="graphics-mode" key={row.id}>
            <div className="graphics-mode-heading">
              <strong>{row.label}</strong>
              <span className="graphics-method">
                {row.method === "mode_measurement" ? "실측" : "예상"}
              </span>
            </div>
            <div className="graphics-mode-value">
              <strong>{display(row.avg_fps)} FPS</strong>
              {row.generated && row.render_fps != null ? (
                <span>렌더링 예상 {display(row.render_fps)} FPS</span>
              ) : null}
            </div>
            {row.method !== "mode_measurement" && row.range ? (
              <p>
                예상 범위 {display(row.range.min)}–{display(row.range.max)} FPS
              </p>
            ) : null}
            {row.preset_label || row.reference_resolution ? (
              <p>
                {row.preset_label ? row.preset_label + " · " : ""}기준 자료{" "}
                {row.reference_resolution}p
              </p>
            ) : null}
            {row.calibration_basis ? <p>{row.calibration_basis}</p> : null}
            {row.calibration_workload_note ? (
              <p>{row.calibration_workload_note}</p>
            ) : null}
            {row.support_note ? <p>{row.support_note}</p> : null}
            {[
              ...new Set(
                row.calibration_sources?.length
                  ? row.calibration_sources
                  : [row.source_url],
              ),
            ]
              .filter(
                (url) => typeof url === "string" && /^https:\/\//.test(url),
              )
              .map((url, index) => (
                <a
                  key={url}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  측정 출처{index ? " " + (index + 1) : ""}
                </a>
              ))}
          </div>
        ))
      ) : !unavailable.length ? (
        <p>
          이 게임·GPU에서 지원이 확인된 DLSS/FSR·프레임 생성 옵션이 없습니다.
        </p>
      ) : null}
      {unavailable.map((row) => (
        <p key={row.id}>{row.note}</p>
      ))}
      {rows.some((row) => row.method !== "mode_measurement") ? (
        <p className="graphics-footnote">
          예상값은 구성과 렌더링 부하를 반영한 계산값이며 실측값이 아닙니다.
        </p>
      ) : null}
    </div>
  );
}
