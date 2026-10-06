import { seedCatalogItems, withPartType } from "../domain/products.js";
import { gameCategoryFor } from "./initialState.js";

export function catalogPatch(data, state) {
  const mappings = {
    gpu: "gpus",
    cpu: "cpus",
    ram: "rams",
    mb: "mbs",
    storage: "storages",
    hdd: "hdds",
    psu: "psus",
    case: "cases",
    software: "software",
  };
  const catalogs = { ...state.catalogs };
  for (const [type, key] of Object.entries(mappings))
    if (data[key])
      catalogs[type] = seedCatalogItems(withPartType(data[key], type));
  const games = data.games?.length
    ? data.games.map((g) => ({
        id: g.id,
        label: g.label || g.name || g.id,
        group: g.group || "기타",
        category: g.category || gameCategoryFor(g.id, state.games),
      }))
    : state.games;
  const workProfiles = structuredClone(state.workProfiles);
  for (const profile of data.work_profiles || [])
    if (workProfiles[profile.id])
      workProfiles[profile.id] = {
        ...workProfiles[profile.id],
        name: profile.label || workProfiles[profile.id].name,
        group: profile.group || workProfiles[profile.id].group,
      };
  return {
    catalogs,
    games,
    workProfiles,
    productFacets: {
      ...state.productFacets,
      ...(data.filter_facets || {}),
    },
    catalogError: "",
  };
}
