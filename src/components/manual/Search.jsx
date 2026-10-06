import React from "react";
import { useApp } from "../../state/context.jsx";
import { Icon, Button } from "../Controls.jsx";
import { BUILDER_META } from "../../domain/products.js";

const h = React.createElement;
function Search({ type }) {
  const { state, store } = useApp(["productDraft", "browse"]);
  const draft = state.productDraft;
  const setDraft = (productDraft) => store.update({ productDraft });
  const search = (e) => {
    e?.preventDefault();
    const retry = Boolean(store.domain().browseStateFor(type).error);
    store.update({ productQuery: draft.trim() });
    void store.loadProducts(type, { force: retry });
  };
  return h(
    "div",
    { className: "pc-browser-head" },
    h(
      "div",
      null,
      h("h3", { id: "builderCategoryTitle" }, BUILDER_META[type].label),
      h("p", null, "필요한 사양으로 좁혀보세요"),
    ),
    h(
      "form",
      { className: "pc-search", role: "search", onSubmit: search },
      h(Icon, { name: "search", size: 19 }),
      h("input", {
        id: "productSearchInput",
        type: "search",
        value: draft,
        onChange: (e) => setDraft(e.target.value),
        placeholder: "제품명, 칩셋, 소켓 검색",
        "aria-label": "부품 검색",
      }),
      h(
        "button",
        {
          type: "submit",
          id: "refreshProductsBtn",
          className: "pc-button pc-primary",
        },
        "검색",
      ),
    ),
  );
}

export default React.memo(Search);
