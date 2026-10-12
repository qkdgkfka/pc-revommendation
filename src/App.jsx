import React, { lazy, Suspense, useEffect } from "react";
import { useApp } from "./state/context.jsx";
import { Icon, SegmentedControl } from "./components/Controls.jsx";
import RecommendationScreen from "./screens/RecommendationScreen.jsx";
const ManualScreen = lazy(() => import("./screens/ManualScreen.jsx"));
const FpsCalculatorScreen = lazy(
  () => import("./screens/FpsCalculatorScreen.jsx"),
);
const VIEWS = [
  { value: "ai", label: "AI 자동 추천", id: "viewAiBtn" },
  { value: "custom", label: "직접 사양 선택", id: "viewCustomBtn" },
  { value: "fps", label: "게임별 FPS 예측", id: "viewFpsBtn" },
];
export default function App() {
  const { state, store } = useApp(["activeView"]);
  useEffect(() => {
    void store.loadCatalog();
    return () => store.destroy();
  }, [store]);
  return (
    <div className="app">
      <header className="hero">
        <div className="pc-brand">
          <span className="pc-brand-mark">
            <Icon name="cpu" size={26} />
          </span>
          <div>
            <h1>PC 견적 도우미</h1>
            <p>부품 선택부터 예상 성능까지, 한곳에서</p>
          </div>
        </div>
        <nav aria-label="견적 방식 선택">
          <SegmentedControl
            label="견적 방식"
            className="pc-mode-switch"
            options={VIEWS}
            value={state.activeView}
            onChange={store.setView}
          />
        </nav>
      </header>
      <Suspense
        fallback={
          <div className="screen-loading" role="status">
            <span className="spinner" /> 화면을 불러오는 중…
          </div>
        }
      >
        {state.activeView === "fps" ? (
          <FpsCalculatorScreen />
        ) : state.activeView === "custom" ? (
          <main className="app-view" id="customSection">
            <ManualScreen />
          </main>
        ) : (
          <RecommendationScreen />
        )}
      </Suspense>
    </div>
  );
}
