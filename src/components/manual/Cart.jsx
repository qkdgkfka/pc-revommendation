import React from "react";
import { useApp } from "../../state/context.jsx";
import { Icon, Button } from "../Controls.jsx";
import {
  BUILDER_PARTS,
  money,
  effectivePrice,
  priceProvenance,
  fullProductName,
  partUrl,
} from "../../domain/products.js";
import { pricePerFrame, workScore } from "../../domain/performance.js";
import { ProductImage } from "../ProductImage.jsx";
import { Compatibility } from "../Compatibility.jsx";

const h = React.createElement;
function buildPriceNote(parts) {
  const selected = Object.values(parts).filter(Boolean),
    statuses = selected.map((p) => priceProvenance(p).status);
  return selected.some((p) => effectivePrice(p) == null)
    ? "가격 미확인 부품을 제외한 합계입니다."
    : statuses.includes("estimated")
      ? "참고가가 포함된 예상 합계입니다. 판매처에서 현재 가격을 확인해주세요."
      : statuses.includes("stale")
        ? "이전 확인가가 포함된 합계입니다. 구매 전 가격을 다시 확인해주세요."
        : "판매처 확인가 기준 · 배송비 및 조립비 별도";
}
function buildValueText(state) {
  const parts = Object.values(state.selected).filter(Boolean),
    total = parts.reduce((sum, p) => sum + (effectivePrice(p) || 0), 0),
    p = state.selected;
  if (
    !total ||
    parts.some((p) => effectivePrice(p) == null) ||
    !p.gpu ||
    !p.cpu ||
    !p.ram
  )
    return "전체 부품 가격과 게임 FPS가 확인되면 1프레임당 가격을 계산합니다.";
  if (state.csMode === "game") {
    const value = pricePerFrame(total, state.fps.data?.fps_by_option?.high);
    return value == null
      ? "1프레임당 가격 · 계산 대기"
      : `1프레임당 가격 · ${Math.round(value).toLocaleString("ko-KR")}원 · ${state.csRes}p · 풀옵`;
  }
  const value =
    workScore(p.gpu, p.cpu, p.ram, p.storage, state.csWork) /
    Math.max(1, total / 10000);
  return `작업 성능 1만원당 ${value.toFixed(2)} 지수 · ${value >= 3.5 ? "좋음" : value >= 2 ? "보통" : "낮음"}`;
}
function cartDisplayName(part, type) {
  const full = fullProductName(part);
  const specs = part.specs || {};
  if (type === "cpu") {
    const model = full.match(
      /(?:i[3579][- ]?\d{4,5}[a-z]*|\b\d{4}(?:X3D2?|XT|X|G|F)\b|\b\d{3}[KFT]+(?:\s+Plus)?)/i,
    )?.[0];
    if (model)
      return [
        specs.cpu_family ||
          (/라이젠|Ryzen/i.test(full)
            ? "Ryzen"
            : /울트라|Ultra/i.test(full)
              ? "Core Ultra"
              : "Intel Core"),
        model,
      ]
        .join(" ")
        .replace(/(Core i[3579]) i[3579][- ]/i, "$1-");
  }
  let short = full
    .replace(/^\[([^\]]+)\]\s*/, "$1 ")
    .replace(/\([^)]*\)/g, "")
    .replace(/\[[^\]]*\]/g, "");
  short = short.replace(
    /(?:대원씨티에스|인텍앤컴퍼니|제이씨현|피씨디렉트|코잇|에즈윈|디앤디컴|STCOM|대양케이스|서린|정품|멀티팩|벌크|병행수입|병행|해외구매|트라이프로져\d*|듀러블에디션)/gi,
    "",
  );
  short = short
    .replace(/지포스|GeForce|라데온|Radeon/gi, "")
    .replace(/\bD[567](?:X)?\b/gi, "");
  return short.replace(/\s+/g, " ").trim() || full;
}
function Cart({ parts }) {
  const { state, store } = useApp([
    "builderPart",
    "selected",
    "csMode",
    "csRes",
    "csWork",
    "fps",
  ]);
  const selected = Object.values(parts).filter(Boolean);
  const total = selected.reduce((sum, p) => sum + (effectivePrice(p) || 0), 0);
  const unknown = selected.some((p) => effectivePrice(p) == null);
  return h(
    "section",
    { className: "pc-cart" },
    h(
      "div",
      { className: "pc-cart-head" },
      h("h3", null, "내 견적"),
      h("span", null, selected.length + " / " + BUILDER_PARTS.length),
      h(
        Button,
        {
          className: "pc-text-button",
          onClick: () => {
            store.clearBuild();
          },
        },
        "전체 비우기",
      ),
    ),
    h(Compatibility, { parts }),
    h(
      "div",
      { className: "pc-cart-rows", id: "buildCart" },
      BUILDER_PARTS.map((meta) => {
        const part = parts[meta.key];
        return h(
          "div",
          {
            key: meta.key,
            className:
              "pc-cart-item" +
              (part ? " has-selection" : "") +
              (state.builderPart === meta.key ? " is-current" : ""),
          },
          h(
            Button,
            {
              className: "pc-cart-select",
              onClick: () => store.setPart(meta.key),
            },
            part
              ? h(ProductImage, { part, type: meta.key })
              : h(Icon, { name: meta.key, size: 19 }),
            h(
              "span",
              { className: "pc-cart-name" },
              h("b", null, meta.label),
              part
                ? h(
                    "span",
                    { title: fullProductName(part) },
                    cartDisplayName(part, meta.key),
                  )
                : null,
            ),
            !part
              ? h("span", { className: "pc-cart-prompt" }, "제품 선택")
              : null,
          ),
          part
            ? h(
                "div",
                { className: "pc-cart-item-bottom" },
                h(
                  "a",
                  {
                    href: partUrl(part),
                    target: "_blank",
                    rel: "noopener noreferrer",
                  },
                  effectivePrice(part) == null
                    ? "가격 미확인"
                    : money(effectivePrice(part)),
                ),
                h(
                  Button,
                  {
                    className: "pc-icon-button",
                    "aria-label": meta.label + " 선택 해제",
                    onClick: () => store.clearProduct(meta.key),
                  },
                  h(Icon, { name: "close", size: 14 }),
                ),
              )
            : null,
        );
      }),
    ),
    h(
      "div",
      { className: "pc-cart-total" },
      h("span", null, "부품 합계"),
      h("strong", null, money(total) + (unknown ? " + 미확인" : "")),
    ),
    h("p", { className: "pc-cart-note" }, buildPriceNote(parts)),
    h("p", { className: "pc-cart-note" }, buildValueText(state)),
  );
}

export default React.memo(Cart);
