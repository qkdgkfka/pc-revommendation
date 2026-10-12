import { nonNegativeNumber as numeric } from "./numbers.js";
import { safeExternalUrl } from "./urls.js";

/** Display only returned 1% Low evidence; average FPS is never a substitute. */
export function lowOneDetails(fps, option = "high") {
  const evidence = fps?.option_evidence?.[option] || {};
  const reported = numeric(fps?.low1_by_option?.[option]);
  const value = evidence.low1_method === "unavailable" ? null : reported;
  const method =
    value === null
      ? "unavailable"
      : evidence.low1_method ||
        (evidence.low1_estimated === false ? "measured" : "estimated");
  const label =
    {
      measured: "실측 참고",
      interpolated: "실측 기반 추정",
      unavailable: "자료 없음",
      estimated: "추정값 · 보정 근거 확인 필요",
    }[method] || "추정값 · 보정 근거 확인 필요";
  const minimum = numeric(evidence.low1_range?.min);
  const maximum = numeric(evidence.low1_range?.max);
  const sourceUrl = safeExternalUrl(evidence.low1_source_url);
  return {
    value,
    method,
    label,
    reason:
      value === null
        ? evidence.low1_unavailable_reason ||
          "선택 조건에 적용할 검증된 1% Low 자료가 없습니다."
        : "",
    range:
      value !== null &&
      minimum !== null &&
      maximum !== null &&
      minimum <= maximum
        ? { min: minimum, max: maximum }
        : null,
    confidence: evidence.low1_confidence,
    sourceUrl: value !== null ? sourceUrl : "",
    sourceTitle: evidence.low1_source_title || "1% Low 측정 출처",
    referencePreset: evidence.low1_reference_preset,
    referenceResolution: evidence.low1_reference_resolution,
  };
}
