import { referenceCatalogs } from "../domain/referenceCatalog.js";
import {
  GAME_OPTIONS,
  WORK_PROFILES,
  GAME_CATEGORIES,
} from "../domain/options.js";
import { seedCatalogItems, withPartType } from "../domain/products.js";
export const recommendationDefaults = {
  budgetMode: "soft",
  budget: 2000000,
  budgetMin: 1000000,
  budgetMax: 2000000,
  resolution: "1080",
  refresh: 60,
  gpu_pref: "nopref",
  gpu_brands: [],
  game: "cyberpunk2077",
  gameCategory: "aaa",
  panelMode: "game",
  panelWork: "video_4k",
};
export function initialState(catalogs = referenceCatalogs) {
  return {
    activeView: "ai",
    ...recommendationDefaults,
    csMode: "game",
    csRes: "1080",
    csGame: "cyberpunk2077",
    csGameCategory: "aaa",
    csWork: "video_4k",
    csGpuMakers: [],
    builderPart: "cpu",
    builderFilters: {},
    productQuery: "",
    productDraft: "",
    productQueries: {},
    productDrafts: {},
    productSource: "all",
    productSort: "popular",
    selected: {},
    pinned: {},
    browse: {},
    productFacets: {},
    catalogs: Object.fromEntries(
      Object.entries(catalogs).map(([type, items]) => [
        type,
        seedCatalogItems(withPartType(structuredClone(items), type)),
      ]),
    ),
    games: structuredClone(GAME_OPTIONS),
    workProfiles: structuredClone(WORK_PROFILES),
    lastRecommendation: null,
    recommendation: { loading: false, error: "", kind: "" },
    fps: { key: "", loading: false, data: null, error: "", kind: "" },
    catalogError: "",
  };
}
export function gameCategoryFor(gameId, games = GAME_OPTIONS) {
  const item = games.find((game) => game.id === gameId);
  if (item?.category && GAME_CATEGORIES.some((c) => c.id === item.category))
    return item.category;
  const group = String(item?.group || "").toLowerCase();
  return /fps|경쟁/.test(group)
    ? "fps"
    : /오픈월드|서브컬쳐/.test(group)
      ? "openworld"
      : /aaa|goty/.test(group)
        ? "aaa"
        : "game";
}
