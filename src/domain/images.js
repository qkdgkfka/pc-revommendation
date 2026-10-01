import { queryString, partUrl } from "./products.js";
export function partImageUrl(part, type = "") {
  if (!part?.name && !part?.product_name) return "";
  const name = part.product_name || part.name;
  const params = queryString({
    name: String(name),
    type: String(type || part.part_type || part.type || ""),
    image_url:
      /^https?:\/\//i.test(part.image_url || "") &&
      !String(part.image_url).includes("/api/part-image")
        ? part.image_url
        : "",
    product_url: partUrl(part),
  });
  return `/api/part-image?${params}`;
}
export function imageFallbackUrl() {
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="120" viewBox="0 0 160 120"><rect width="160" height="120" rx="12" fill="#eef4ff"/><rect x="44" y="20" width="72" height="50" rx="8" fill="#d9e6ff"/><path d="M54 58l16-18 13 12 10-9 15 15" fill="none" stroke="#526580" stroke-width="4"/><text x="80" y="96" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#526580">이미지 없음</text></svg>';
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
