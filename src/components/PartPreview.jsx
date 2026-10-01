import React, { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  effectivePrice,
  fullProductName,
  money,
  priceProvenance,
} from "../domain/products.js";
import { partImageUrl, imageFallbackUrl } from "../domain/images.js";
/** Recommendation rows retain the delayed photo/price preview and keyboard access. */
export default function PartPreview({ part, type, children }) {
  const [position, setPosition] = useState(null),
    target = useRef(null),
    timer = useRef(null),
    id = useId();
  const close = () => {
    clearTimeout(timer.current);
    setPosition(null);
  };
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    if (!position) return;
    const key = (e) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", key);
    window.addEventListener("resize", close);
    window.addEventListener("scroll", close, true);
    return () => {
      document.removeEventListener("keydown", key);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [Boolean(position)]);
  const show = () => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const rect = target.current?.getBoundingClientRect();
      if (!rect) return;
      const margin = 12,
        width = 260,
        height = 300;
      let left = rect.right + margin;
      if (left + width > window.innerWidth - margin)
        left = rect.left - width - margin;
      left = Math.max(
        margin,
        Math.min(left, window.innerWidth - width - margin),
      );
      setPosition({
        left,
        top: Math.max(
          margin,
          Math.min(rect.top, window.innerHeight - height - margin),
        ),
      });
    }, 220);
  };
  const price = effectivePrice(part);
  return (
    <div
      ref={target}
      className="part-preview-target"
      aria-describedby={position ? id : undefined}
      onMouseEnter={show}
      onMouseLeave={close}
      onFocus={show}
      onBlur={close}
    >
      {children}
      {position
        ? createPortal(
            <div
              className="part-preview-popover show"
              id={id}
              role="tooltip"
              style={position}
            >
              <div className="preview-image-wrap">
                <img
                  src={partImageUrl(part, type)}
                  alt={fullProductName(part) + " 대표 이미지"}
                  onError={(e) => {
                    if (!e.currentTarget.dataset.failed) {
                      e.currentTarget.dataset.failed = "1";
                      e.currentTarget.src = imageFallbackUrl();
                    }
                  }}
                />
              </div>
              <div className="preview-caption">
                <strong className="preview-name">
                  {fullProductName(part)}
                </strong>
                <span className="preview-price">
                  {price == null ? "가격 미확인" : money(price)}
                </span>
                <span className="preview-source">
                  {priceProvenance(part).text}
                </span>
              </div>
            </div>,
            document.body,
          )
        : null}
    </div>
  );
}
