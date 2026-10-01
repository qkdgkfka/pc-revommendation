import React, { lazy, Suspense, useEffect } from "react";
import { useApp } from "./state/context.jsx";
import ManualScreen, { Icon, Button } from "./screens/ManualScreen.jsx";
const RecommendationScreen = lazy(
  () => import("./screens/RecommendationScreen.jsx"),
);
export default function App() {
  const { state, store } = useApp();
  useEffect(() => {
    void store.loadCatalog();
    void store.loadProducts();
    return () => store.destroy();
  }, [store]);
  return (
    <div className="app">
      <section className="hero">
        <div className="pc-brand">
          <Icon name="cpu" size={26} />
          <div>
            <h1>PC 견적 도우미</h1>
            <p>부품 선택부터 예상 성능까지, 한곳에서</p>
          </div>
        </div>
        <nav className="pc-mode-switch" aria-label="견적 방식 선택">
          {[
            ["ai", "AI 자동 추천"],
            ["custom", "직접 사양 선택"],
          ].map(([view, label]) => (
            <Button
              key={view}
              id={view === "custom" ? "viewCustomBtn" : "viewAiBtn"}
              aria-pressed={state.activeView === view}
              className={state.activeView === view ? "is-active" : ""}
              onClick={() => store.setView(view)}
            >
              {label}
            </Button>
          ))}
        </nav>
      </section>
      {state.activeView === "custom" ? (
        <div className="app-view" id="customSection">
          <ManualScreen />
        </div>
      ) : (
        <Suspense
          fallback={
            <div className="screen-loading" role="status">
              <span className="spinner" /> AI 추천 화면을 불러오는 중…
            </div>
          }
        >
          <RecommendationScreen />
        </Suspense>
      )}
    </div>
  );
}
