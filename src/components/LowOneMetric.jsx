import React from "react";
import { lowOneDetails } from "../domain/lowOne.js";
import "./low-one.css";

const format = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1 });

export default function LowOneMetric({ fps, option = "high" }) {
  const info = lowOneDetails(fps, option);
  return (
    <div className="pc-low1-metric">
      <div>
        <span>고옵 · 1% Low</span>
        <strong>
          {info.value === null
            ? "자료 없음"
            : `${format.format(info.value)} FPS`}
        </strong>
      </div>
    </div>
  );
}
