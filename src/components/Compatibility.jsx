import React from "react";
import { socketCompatibility } from "../domain/specs.js";
import { fullProductName } from "../domain/products.js";

const h = React.createElement;
export function Compatibility({ parts, inline = false }) {
  const status = socketCompatibility(parts.cpu, parts.mb);
  if (["incomplete", "compatible"].includes(status.status)) return null;
  const mismatch = status.status === "incompatible";
  return h(
    "div",
    {
      className: "pc-compatibility " + (mismatch ? "is-warning" : "is-unknown"),
      role: "status",
      "aria-live": "polite",
      id: inline ? "manualCompatibilityInline" : "manualCompatibility",
    },
    h(
      "strong",
      null,
      mismatch
        ? "CPU와 메인보드의 소켓이 호환되지 않습니다"
        : "소켓 정보 확인이 필요합니다",
    ),
    h(
      "p",
      null,
      `CPU: ${fullProductName(parts.cpu)} · ${status.cpuSocket === "unknown" ? "소켓 미확인" : status.cpuSocket}`,
    ),
    h(
      "p",
      null,
      `메인보드: ${fullProductName(parts.mb)} · ${status.motherboardSocket === "unknown" ? "소켓 미확인" : status.motherboardSocket}`,
    ),
  );
}
