import aliases from "../../product_search_aliases.json" with { type: "json" };

const aliasSeparator = /[\s._-]+/g;
const aliasKey = (value) => value.replace(aliasSeparator, "");
const aliasKeys = new Map(
  Object.entries(aliases).flatMap(([canonical, names]) =>
    names.map((name) => [aliasKey(name), canonical]),
  ),
);
const escapePattern = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const aliasPattern = new RegExp(
  Object.values(aliases)
    .flat()
    .sort((a, b) => b.length - a.length)
    .map((alias) => {
      const pattern = alias
        .split(/[\s._-]+/)
        .map(escapePattern)
        .join("[\\s._-]*");
      return `${/^[a-z]/.test(alias) ? "(?<![a-z])" : ""}${pattern}${/[a-z]$/.test(alias) ? "(?![a-z])" : ""}`;
    })
    .join("|"),
  "g",
);
const searchFields = [
  "product_name",
  "name",
  "brand",
  "manufacturer",
  "vendor",
  "chipset",
  "model",
  "gpu_model",
];

function literalSearchText(value) {
  return value
    .replace(/[-_/]+/g, " ")
    .replace(/[^a-z0-9가-힣\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}
const rawSearchText = (value) =>
  String(value || "")
    .normalize("NFKC")
    .toLowerCase();

export function normalizeSearchText(value) {
  return literalSearchText(
    rawSearchText(value).replace(aliasPattern, (alias) =>
      aliasKeys.get(aliasKey(alias)),
    ),
  );
}

export function productMatchesQuery(query, product) {
  const queries = [
    literalSearchText(rawSearchText(query)),
    normalizeSearchText(query),
  ].map((text) => text.split(" ").filter(Boolean));
  if (!queries[0].length) return true;
  // Grouped specifications can mention other SKUs' capacities and editions.
  const text =
    typeof product === "object" && product
      ? searchFields.map((field) => product[field] || "").join(" ")
      : product;
  // Retain literal fragments inside translated aliases, e.g. 삼성전.
  const compacts = [
    literalSearchText(rawSearchText(text)),
    normalizeSearchText(text),
  ].map((name) => name.replace(/ /g, ""));
  return queries.some((terms) =>
    terms.every((term) => compacts.some((name) => name.includes(term))),
  );
}
