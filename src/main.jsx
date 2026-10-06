import "../styles.css";
import "./components/shared.css";
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { AppContext } from "./state/context.jsx";
import { createAppStore } from "./state/store.js";
const store = createAppStore();
createRoot(document.getElementById("root")).render(
  <AppContext.Provider value={store}>
    <App />
  </AppContext.Provider>,
);
