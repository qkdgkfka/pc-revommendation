import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";
import { createStateSelector } from "./selectors.js";
export const AppContext = createContext(null);
export function useStore() {
  const store = useContext(AppContext);
  if (!store) throw new Error("App store missing");
  return store;
}
export function useApp(fields) {
  const store = useStore();
  const fieldKey = fields?.join("\0");
  const select = useMemo(
    () => createStateSelector(fieldKey?.split("\0")),
    [fieldKey],
  );
  const getSnapshot = useCallback(
    () => select(store.getState()),
    [store, select],
  );
  const state = useSyncExternalStore(store.subscribe, getSnapshot, getSnapshot);
  return { store, state };
}
