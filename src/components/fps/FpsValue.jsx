import React from "react";
import { nonNegativeNumber } from "../../domain/numbers.js";
const FORMAT = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1 });

export default function FpsValue({ value, large = false }) {
  const number = nonNegativeNumber(value);
  return number === null ? (
    <span className="fpr-missing">자료 없음</span>
  ) : (
    <span className={large ? "fpr-value fpr-value-large" : "fpr-value"}>
      {FORMAT.format(number)} <small>FPS</small>
    </span>
  );
}
