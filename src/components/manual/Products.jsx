import React, { useMemo } from "react";
import { useApp, useStore } from "../../state/context.jsx";
import { Icon, Button } from "../Controls.jsx";
import {
  money,
  effectivePrice,
  priceProvenance,
  fullProductName,
  partUrl,
  productBadges,
} from "../../domain/products.js";
import { ProductImage } from "../ProductImage.jsx";

const h = React.createElement;
function badges(part, type) {
  if (!part.specs) return productBadges(part, type);
  const s = part.specs;
  const keys =
    {
      cpu: ["socket", "cpu_family", "memory_type"],
      mb: ["chipset", "socket", "memory_type", "form_factor"],
      ram: ["memory_type", "kit", "capacity_gb", "speed", "cl"],
      gpu: ["chipset", "vram_gb"],
      storage: ["form_factor", "interface", "capacity_gb", "nand"],
      psu: ["watt", "rating", "modular", "atx_version"],
      hdd: ["usage", "capacity_gb", "rpm"],
    }[type] || [];
  return keys
    .flatMap((key) => {
      const value = s[key];
      if (!value) return [];
      if (Array.isArray(value)) return value;
      return [
        key === "capacity_gb" || key === "vram_gb"
          ? Number(value) >= 1000
            ? `${Number(value) / 1000}TB`
            : `${value}GB`
          : key === "speed"
            ? `${value}MT/s`
            : key === "cl"
              ? `CL${value}`
              : key === "watt"
                ? `${value}W`
                : key === "rpm"
                  ? `${value} RPM`
                  : value,
      ];
    })
    .slice(0, 6);
}
function ProductRow({ part, type, selected }) {
  const store = useStore();
  const price = effectivePrice(part);
  const provenance = priceProvenance(part);
  return h(
    "article",
    {
      className: "pc-product-row" + (selected ? " is-selected" : ""),
      "data-part-id": part.id,
    },
    h(ProductImage, { part, type }),
    h(
      "div",
      { className: "pc-product-info" },
      h(
        "a",
        {
          className: "pc-product-name",
          href: partUrl(part),
          target: "_blank",
          rel: "noopener noreferrer",
        },
        fullProductName(part),
      ),
      h(
        "div",
        { className: "pc-specs" },
        badges(part, type).map((b, i) => h("span", { key: i }, b)),
      ),
      h("p", { className: "pc-price-source" }, provenance.text),
    ),
    h(
      "div",
      { className: "pc-product-action" },
      h("strong", null, price == null ? "가격 미확인" : money(price)),
      h(
        Button,
        {
          className: selected ? "pc-added" : "pc-add",
          "aria-pressed": selected,
          onClick: () =>
            selected
              ? store.clearProduct(type)
              : store.selectProduct(type, part.id),
        },
        h(Icon, { name: selected ? "check" : "close", size: 14 }),
        selected ? "선택됨" : "담기",
      ),
    ),
  );
}
const MemoProductRow = React.memo(ProductRow);
function Results({ type, parts }) {
  const { state, store } = useApp([
    "browse",
    "builderFilters",
    "productQuery",
    "productSource",
    "productSort",
    "productFacets",
  ]);
  const { browseStateFor, builderSearchKey } = store.domain();
  const browse = browseStateFor(type);
  const current = browse.requestKey === builderSearchKey(type) && browse.loaded;
  const products = useMemo(
    () => store.domain().filteredProducts(type),
    [
      store,
      type,
      state.browse,
      state.builderFilters,
      state.productQuery,
      state.productSource,
      state.productSort,
      state.productFacets,
    ],
  );
  return h(
    React.Fragment,
    null,
    h(
      "div",
      { className: "pc-results-toolbar" },
      h("strong", { id: "productCount" }, `${products.length}개 표시`),
      h(
        "div",
        { className: "pc-results-controls" },
        h(
          "select",
          {
            id: "productSourceSelect",
            value: state.productSource,
            "aria-label": "가격 검색처",
            onChange: (e) => {
              store.update({ productSource: e.target.value });
              void store.loadProducts();
            },
          },
          ["all", "danawa", "compuzone"].map((v, i) =>
            h(
              "option",
              { key: v, value: v },
              ["다나와 + 컴퓨존", "다나와", "컴퓨존"][i],
            ),
          ),
        ),
        h(
          "select",
          {
            id: "productSortSelect",
            value: state.productSort,
            "aria-label": "제품 정렬",
            onChange: (e) => {
              store.update({ productSort: e.target.value });
              void store.loadProducts();
            },
          },
          [
            ["popular", "검색처 기본순"],
            ["price_asc", "낮은 가격순"],
            ["price_desc", "높은 가격순"],
            ["name", "상품명순"],
          ].map(([value, label]) => h("option", { key: value, value }, label)),
        ),
      ),
    ),
    h(
      "p",
      { className: "pc-result-note", role: "status", id: "productBrowseNote" },
      browse.loading
        ? "조건에 맞는 제품과 가격을 검색하고 있어요."
        : browse.error
          ? browse.error
          : browse.partial
            ? "일부 결과를 먼저 표시합니다. 더 보기로 검색을 이어갈 수 있어요."
            : "판매처 사양 기준 · 가격과 이름 정렬은 불러온 제품에 적용됩니다.",
    ),
    h(
      "div",
      {
        id: "productList",
        className: "pc-product-list",
        "aria-busy": browse.loading,
      },
      products.map((part) =>
        h(MemoProductRow, {
          key: part.id,
          part,
          type,
          selected: parts[type]?.id === part.id,
        }),
      ),
      !products.length
        ? h(
            "div",
            { className: "pc-empty" },
            h(Icon, { name: "search", size: 32 }),
            h(
              "h4",
              null,
              browse.loading
                ? "제품을 찾고 있어요"
                : browse.error
                  ? browse.errorKind === "timeout"
                    ? "판매처 응답 시간이 초과됐어요"
                    : browse.errorKind === "cancelled"
                      ? "검색을 취소했어요"
                      : "판매처에 연결하지 못했어요"
                  : "조건에 맞는 제품이 없어요",
            ),
            h(
              "p",
              null,
              browse.error ||
                (browse.loading
                  ? "판매처 조회가 완료되면 제품을 표시합니다."
                  : "검색어를 바꾸거나 선택 조건을 줄여보세요. 사양이 없는 제품은 조건 검색에서 제외됩니다."),
            ),
            !browse.loading
              ? h(
                  Button,
                  {
                    onClick: browse.error
                      ? () => store.retryProducts(type)
                      : store.resetFilters,
                  },
                  browse.error ? "판매처 다시 확인" : "선택 조건 초기화",
                )
              : null,
          )
        : null,
    ),
    current && browse.hasMore
      ? h(
          Button,
          {
            id: "loadMoreProductsBtn",
            className: "pc-load-more",
            disabled: browse.loading,
            onClick: () => void store.loadProducts(type, { append: true }),
          },
          browse.loading ? "불러오는 중…" : "제품 더 보기",
          h(Icon, { name: "down", size: 16 }),
        )
      : null,
  );
}

export default React.memo(Results);
