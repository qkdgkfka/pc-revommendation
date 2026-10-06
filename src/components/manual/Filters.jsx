import React, { useState } from "react";
import { useApp } from "../../state/context.jsx";
import { Icon, Button } from "../Controls.jsx";
import { gpuSeriesGroups } from "../../domain/products.js";

const h = React.createElement;
function FilterGroup({ group, type }) {
  const { store } = useApp(["builderFilters"]);
  const { filterValues } = store.domain();
  const [expanded, setExpanded] = useState(false);
  const limit = group.key === "socket" ? 4 : 6;
  const selected = filterValues(type, group.key);
  const visible = expanded
    ? group.options
    : group.options.filter(
        (option, index) => index < limit || selected.includes(option[0]),
      );
  return h(
    "div",
    { className: "pc-filter-row", role: "group", "aria-label": group.label },
    h("div", { className: "pc-filter-label" }, group.label),
    h(
      "div",
      { className: "pc-filter-options" },
      visible.map(([value, label]) =>
        h(
          Button,
          {
            key: value,
            "aria-pressed": selected.includes(String(value)),
            className:
              "pc-chip" +
              (selected.includes(String(value)) ? " is-active" : ""),
            onClick: () => store.toggleFilter(type, group.key, String(value)),
          },
          type === "cpu" && group.key === "platform"
            ? String(label).replace(" CPU용", "")
            : label,
        ),
      ),
      group.options.length > limit
        ? h(
            Button,
            {
              className: "pc-options-more",
              "aria-expanded": expanded,
              onClick: () => setExpanded(!expanded),
            },
            expanded ? "접기" : "옵션 더보기",
            h(Icon, { name: "down", size: 14 }),
          )
        : null,
    ),
  );
}
function GpuHierarchy() {
  const { state, store } = useApp([
    "builderFilters",
    "browse",
    "catalogs",
    "pinned",
  ]);
  const { filterValues, allKnownProductsFor } = store.domain();
  const groups = gpuSeriesGroups(allKnownProductsFor("gpu")).filter(
    (g) =>
      !filterValues("gpu", "vendor").length ||
      filterValues("gpu", "vendor").includes(g.vendor.toLowerCase()),
  );
  const series = filterValues("gpu", "series")[0];
  const modern = groups.filter((g) =>
    /RTX (50|40|30)|RX (9000|7000|6000)/.test(g.label),
  );
  const older = groups.filter((g) => !modern.includes(g));
  const [legacy, setLegacy] = useState(false);
  const active = groups.find((g) => g.label.replace(/ Series$/, "") === series);
  return h(
    "div",
    { className: "pc-gpu-hierarchy" },
    h(
      "div",
      { className: "pc-filter-row" },
      h("div", { className: "pc-filter-label" }, "GPU 시리즈"),
      h(
        "div",
        { className: "pc-filter-options" },
        (legacy ? groups : modern).map((g) =>
          h(
            Button,
            {
              key: g.label,
              className: "pc-chip" + (g === active ? " is-active" : ""),
              "aria-pressed": g === active,
              onClick: () => store.selectGpuSeries(g.label),
            },
            g.label.replace(" Series", ""),
          ),
        ),
        older.length
          ? h(
              Button,
              {
                className: "pc-options-more",
                onClick: () => setLegacy(!legacy),
                "aria-expanded": legacy,
              },
              legacy ? "접기" : "옵션 더보기",
            )
          : null,
      ),
    ),
    active
      ? h(
          "div",
          { className: "pc-filter-row" },
          h("div", { className: "pc-filter-label" }, "세부 칩셋"),
          h(
            "div",
            { className: "pc-filter-options" },
            h(
              Button,
              {
                className:
                  "pc-chip" +
                  (!filterValues("gpu", "model").length ? " is-active" : ""),
                "aria-pressed": !filterValues("gpu", "model").length,
                onClick: () => store.selectGpuSeries(active.label),
              },
              "시리즈 전체",
            ),
            active.models.map((model) =>
              h(
                Button,
                {
                  key: model,
                  className:
                    "pc-chip" +
                    (filterValues("gpu", "model").includes(model)
                      ? " is-active"
                      : ""),
                  "aria-pressed": filterValues("gpu", "model").includes(model),
                  onClick: () => {
                    store.selectGpuModel(model);
                  },
                },
                model,
              ),
            ),
          ),
        )
      : null,
  );
}
function Filters({ type }) {
  const { state, store } = useApp([
    "builderFilters",
    "productFacets",
    "browse",
    "catalogs",
    "productQuery",
    "productSource",
    "productSort",
  ]);
  const { filterValues, builderFilterDefs } = store.domain();
  const [open, setOpen] = useState(true);
  const [extra, setExtra] = useState(false);
  const defs =
    type !== "gpu" && !state.productFacets?.[type]
      ? []
      : builderFilterDefs(type);
  const primary =
    {
      mb: ["manufacturer", "socket", "chipset", "memory_type", "form_factor"],
      ram: ["manufacturer", "memory_type", "capacity_gb", "speed", "cl"],
      hdd: ["manufacturer", "usage", "form_factor", "capacity_gb", "rpm"],
    }[type] || defs.slice(0, 5).map((g) => g.key);
  const shown = extra
    ? defs
    : defs.filter(
        (g) => primary.includes(g.key) || filterValues(type, g.key).length,
      );
  const active = Object.entries(state.builderFilters[type] || {}).flatMap(
    ([key, values]) =>
      values.map((value) => ({
        key,
        value,
        label:
          defs
            .find((d) => d.key === key)
            ?.options.find((o) => o[0] === value)?.[1] || value,
      })),
  );
  return h(
    "div",
    { className: "pc-filters" },
    h(
      "div",
      { className: "pc-filter-heading" },
      h(
        Button,
        {
          className: "pc-filter-toggle",
          "aria-expanded": open,
          onClick: () => setOpen(!open),
        },
        "상세 조건",
        h(Icon, { name: "down", size: 16 }),
      ),
      h("span", null, "항목 간 조건을 함께 적용해요"),
      h(
        Button,
        {
          className: "pc-text-button",
          id: "resetProductFiltersBtn",
          onClick: store.resetFilters,
        },
        h(Icon, { name: "reset", size: 14 }),
        "초기화",
      ),
    ),
    open
      ? h(
          "div",
          { className: "pc-filter-body", id: "builderFilters" },
          shown.map((group) =>
            type === "gpu" && group.key === "model"
              ? h(GpuHierarchy, { key: "gpu" })
              : h(FilterGroup, { key: type + group.key, group, type }),
          ),
          defs.length > primary.length
            ? h(
                Button,
                {
                  className: "pc-extra-filters",
                  "aria-expanded": extra,
                  onClick: () => setExtra(!extra),
                },
                extra
                  ? "주요 조건만 보기"
                  : `상세 항목 ${defs.length - primary.length}개 더보기`,
                h(Icon, { name: "down", size: 14 }),
              )
            : null,
        )
      : null,
    active.length
      ? h(
          "div",
          { className: "pc-active-filters", id: "activeProductFilters" },
          h("span", null, "선택 조건 " + active.length),
          active.map((a) =>
            h(
              Button,
              {
                key: a.key + a.value,
                className: "pc-active-chip",
                "aria-label": a.label + " 조건 해제",
                onClick: () => store.toggleFilter(type, a.key, a.value),
              },
              a.label,
              h(Icon, { name: "close", size: 13 }),
            ),
          ),
        )
      : null,
  );
}

export default React.memo(Filters);
