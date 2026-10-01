import React from "react";
import {
  money,
  effectivePrice,
  priceProvenance,
  displayName,
  fullProductName,
  partUrl,
} from "../../domain/products.js";
import { Icon, ProductImage } from "../../screens/ManualScreen.jsx";
import PartPreview from "../PartPreview.jsx";

export default function RecommendationPart({ part, type, label }) {
  if (!part?.name && !part?.product_name) return null;
  const provenance = priceProvenance(part);
  return (
    <PartPreview part={part} type={type}>
      <div className="part-row">
        <span className="part-lbl" title={label} aria-label={label}>
          <Icon name={type} size={20} />
        </span>
        <ProductImage part={part} type={type} />
        <span className="part-name">
          <span className="part-title" title={fullProductName(part)}>
            <a
              className="part-link"
              href={partUrl(part)}
              target="_blank"
              rel="noopener noreferrer"
            >
              {displayName(part)}
            </a>
          </span>
          <span className={"price-provenance " + provenance.status}>
            {provenance.text}
          </span>
        </span>
        <span className="part-price">
          {effectivePrice(part) != null
            ? money(effectivePrice(part))
            : "가격 미확인"}
        </span>
      </div>
    </PartPreview>
  );
}
