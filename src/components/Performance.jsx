import React, { useEffect } from "react";
import { useApp } from "../state/context.jsx";
import GamePicker from "./GamePicker.jsx";
import { FpsChart, WorkChart } from "./Charts.jsx";
import { WorkSelect } from "./WorkSelect.jsx";
export default function Performance() {
  const { state, store } = useApp([
      "selected",
      "csGame",
      "csRes",
      "refresh",
      "csMode",
      "fps",
      "games",
      "workProfiles",
      "csWork",
    ]),
    { gpu, cpu, ram } = state.selected;
  useEffect(() => {
    void store.estimateFps();
    return () => store.cancelFps();
  }, [
    store,
    gpu?.id,
    cpu?.id,
    ram?.id,
    state.csGame,
    state.csRes,
    state.refresh,
    state.csMode,
  ]);
  const ready = gpu && cpu && ram;
  return (
    <section className="pc-performance">
      <h3>예상 성능</h3>
      <section className="use-panel">
        <div className="mode-toggle">
          <button
            type="button"
            className={"mode-btn" + (state.csMode === "game" ? " active" : "")}
            id="csModeGame"
            onClick={() => store.update({ csMode: "game" })}
          >
            게임
          </button>
          <button
            type="button"
            className={"mode-btn" + (state.csMode === "work" ? " active" : "")}
            id="csModeWork"
            onClick={() => store.update({ csMode: "work" })}
          >
            작업
          </button>
        </div>
        {state.csMode === "game" ? (
          <div id="csPanelGame">
            <div className="sec-title">해상도</div>
            <div className="res-row" id="csResRow">
              {[
                ["1080", "FHD 1080p"],
                ["1440", "QHD 1440p"],
                ["2160", "4K"],
              ].map(([res, label]) => (
                <button
                  type="button"
                  className={
                    "res-chip" + (state.csRes === res ? " selected" : "")
                  }
                  key={res}
                  data-res={res}
                  aria-pressed={state.csRes === res}
                  onClick={() => store.update({ csRes: res })}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="sec-title">게임 선택</div>
            <GamePicker manual />
            <div className="sec-title" style={{ marginTop: 15 }}>
              예상 FPS{" "}
              <span style={{ textTransform: "none", letterSpacing: 0 }}>
                (저옵 / 중옵 / 풀옵)
              </span>
            </div>
            <div id="csGameChart" aria-busy={state.fps.loading}>
              {!ready ? (
                <div className="no-spec">
                  <div className="no-spec-text">
                    CPU, GPU, RAM을 선택해주세요
                  </div>
                </div>
              ) : state.fps.loading ? (
                <div className="fps-empty is-loading" role="status">
                  <span className="spinner" /> 선택 구성의 벤치마크를 확인하고
                  있습니다.
                </div>
              ) : state.fps.data ? (
                <FpsChart
                  fps={state.fps.data}
                  game={
                    state.games.find((g) => g.id === state.csGame)?.label ||
                    state.csGame
                  }
                  resolution={state.csRes}
                />
              ) : (
                <div className="fps-empty" role="status">
                  {state.fps.error || "FPS 정보를 불러오지 못했습니다."}
                  <button
                    type="button"
                    className="mini-btn ghost"
                    id="retryFpsBtn"
                    onClick={() => store.estimateFps(true)}
                  >
                    FPS 다시 확인
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div id="csPanelWork">
            <div className="sec-title">세부 작업 선택</div>
            <WorkSelect manual />
            <div className="sec-title" style={{ marginTop: 15 }}>
              작업별 사양 적합도
            </div>
            <div id="csWorkChart">
              {ready ? (
                <WorkChart
                  profiles={state.workProfiles}
                  selected={state.csWork}
                  parts={state.selected}
                />
              ) : (
                <div className="no-spec">
                  <div className="no-spec-text">
                    CPU, GPU, RAM을 선택해주세요
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </section>
    </section>
  );
}
