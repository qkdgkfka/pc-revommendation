import React from "react";
import { useStore } from "../../state/context.jsx";
import { Icon, Button } from "../Controls.jsx";
import { BUILDER_PARTS } from "../../domain/products.js";

const h = React.createElement;
function Categories({ type, parts }) {
  const store = useStore();
  return h(
    "nav",
    { className: "pc-categories", "aria-label": "부품 카테고리" },
    BUILDER_PARTS.map((meta) =>
      h(
        Button,
        {
          key: meta.key,
          "aria-pressed": type === meta.key,
          className: type === meta.key ? "is-active" : "",
          onClick: () => store.setPart(meta.key),
        },
        h(Icon, { name: meta.key }),
        h("span", null, meta.label),
        parts[meta.key]
          ? h(
              "span",
              { className: "pc-category-check" },
              h(Icon, { name: "check", size: 14 }),
            )
          : null,
      ),
    ),
  );
}

export default React.memo(Categories);
