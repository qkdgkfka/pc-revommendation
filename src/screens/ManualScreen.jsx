import React, { useEffect } from "react";
import { useApp } from "../state/context.jsx";
import { money, effectivePrice } from "../domain/products.js";
import { Button } from "../components/Controls.jsx";
import { Compatibility } from "../components/Compatibility.jsx";
import Categories from "../components/manual/Categories.jsx";
import Filters from "../components/manual/Filters.jsx";
import Search from "../components/manual/Search.jsx";
import Results from "../components/manual/Products.jsx";
import Cart from "../components/manual/Cart.jsx";
import Performance from "../components/Performance.jsx";
import "../../manual_builder.css";
const h = React.createElement;
export default function ManualScreen() {
  const { state, store } = useApp(["builderPart", "selected"]);
  useEffect(() => {
    const type = store.getState().builderPart;
    const browse = store.getState().browse[type];
    if (!browse?.loaded && !browse?.loading) void store.loadProducts(type);
  }, [store]);
  const type = state.builderPart;
  const parts = state.selected;
  const selected = Object.values(parts).filter(Boolean);
  const total = selected.reduce((sum, p) => sum + (effectivePrice(p) || 0), 0);
  return h(
    React.Fragment,
    null,
    h(
      "div",
      { className: "pc-workspace" },
      h(Categories, { type, parts }),
      h(
        "main",
        { className: "pc-main" },
        h(
          "div",
          { className: "pc-page-title" },
          h("h2", null, "나만의 PC, 직접 골라보세요"),
          h(
            "p",
            null,
            "원하는 부품을 선택하고, 가격과 예상 성능을 함께 확인하세요.",
          ),
        ),
        h(
          "div",
          { className: "pc-mobile-warning" },
          h(Compatibility, { parts, inline: true }),
        ),
        h(
          "section",
          { className: "pc-browser" },
          h(Search, { key: "search-" + type, type }),
          h(Filters, { key: "filters-" + type, type }),
          h(Results, { type, parts }),
        ),
      ),
      h(
        "aside",
        {
          className: "pc-estimate",
          tabIndex: 0,
          "aria-label": "내 견적과 예상 성능 · 독립 스크롤",
        },
        h(Cart, { parts }),
        h(Performance),
      ),
      h(
        Button,
        {
          className: "pc-mobile-cart-bar",
          onClick: () =>
            document
              .querySelector(".pc-cart")
              .scrollIntoView({ behavior: "smooth", block: "start" }),
        },
        `내 견적 · ${selected.length}개 선택`,
        h("strong", null, money(total)),
      ),
    ),
  );
}
