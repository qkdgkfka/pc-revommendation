import {
  withPartType,
  priceProvenance,
  effectivePrice,
  applyPriceObservation,
} from "../domain/products.js";
export function createBuildSelection({
  getState,
  publish,
  domain,
  requests,
  json,
  cancelFps,
  timeout,
}) {
  function selectProduct(type, partOrId) {
    const part =
      typeof partOrId === "string"
        ? domain().findPartById(type, partOrId)
        : withPartType([partOrId], type)[0];
    if (!part) return;
    if (["cpu", "gpu", "ram"].includes(type)) cancelFps();
    requests.cancel("prices");
    publish({
      selected: { ...getState().selected, [type]: part },
      pinned: {
        ...getState().pinned,
        [type]: { ...(getState().pinned[type] || {}), [part.id]: part },
      },
    });
    void refreshSelectedPrices();
  }
  function clearProduct(type) {
    if (["cpu", "gpu", "ram"].includes(type)) cancelFps();
    requests.cancel("prices");
    publish({ selected: { ...getState().selected, [type]: null } });
    void refreshSelectedPrices();
  }
  function clearBuild() {
    cancelFps();
    requests.cancel("prices");
    publish({ selected: {} });
  }
  function refreshSelectedPrices() {
    const wanted = Object.entries(getState().selected)
      .filter(
        ([, part]) =>
          part &&
          !["verified", "cached", "stale"].includes(
            priceProvenance(part).status,
          ) &&
          effectivePrice(part) !== 0,
      )
      .map(([type, p]) => ({
        id: p.id,
        type,
        name: p.name,
        base_price: p.base_price ?? p.price ?? null,
      }));
    if (!wanted.length) return Promise.resolve();
    const payload = {
      items: wanted,
      gpu_brands: getState().csGpuMakers,
      source: getState().productSource,
    };
    const entry = requests.start(
      "prices",
      JSON.stringify(payload),
      (signal) => json("/api/price-lookup", signal, payload),
      timeout ?? 20000,
    );
    if (entry.task) return entry.task;
    entry.task = entry.promise
      .then((data) => {
        if (!entry.current()) return;
        const selected = { ...getState().selected },
          pinned = { ...getState().pinned };
        for (const result of data.results || []) {
          const type = Object.keys(selected).find(
            (key) => selected[key]?.id === result.id,
          );
          if (!type) continue;
          const part = applyPriceObservation({ ...selected[type] }, result);
          selected[type] = part;
          pinned[type] = { ...(pinned[type] || {}), [part.id]: part };
        }
        publish({ selected, pinned });
      })
      .catch(() => {});
    return entry.task;
  }
  return { selectProduct, clearProduct, clearBuild, refreshSelectedPrices };
}
