import React from "react";
import { fullProductName } from "../domain/products.js";
import { partImageUrl, imageFallbackUrl } from "../domain/images.js";

const h = React.createElement;
export function ProductImage({ part, type }) {
  return h(
    "span",
    { className: "pc-product-image" },
    h("img", {
      src: partImageUrl(part, type),
      alt: fullProductName(part) + " 제품 이미지",
      loading: "lazy",
      decoding: "async",
      onError: (e) => {
        if (!e.currentTarget.dataset.failed) {
          e.currentTarget.dataset.failed = "1";
          e.currentTarget.src = imageFallbackUrl(part);
        }
      },
    }),
  );
}
