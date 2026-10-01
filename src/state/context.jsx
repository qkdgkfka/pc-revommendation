import React, { createContext, useContext, useSyncExternalStore } from "react";
export const AppContext = createContext(null);
export function useStore() {
  const store = useContext(AppContext);
  if (!store) throw new Error("App store missing");
  return store;
}
export function useApp() {
  const store = useStore();
  if (!store) throw new Error("App store missing");
  const state = useSyncExternalStore(
    store.subscribe,
    store.getState,
    store.getState,
  );
  return { store, state };
}
