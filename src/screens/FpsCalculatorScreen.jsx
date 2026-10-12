import React, { useEffect, useMemo } from "react";
import { useApp } from "../state/context.jsx";
import { calculatorRam } from "../state/fpsCalculator.js";
import {
  Icon,
  PageHeading,
  SegmentedControl,
} from "../components/Controls.jsx";
import SearchableSelect from "../components/fps/SearchableSelect.jsx";
import FpsPredictionResults from "../components/fps/FpsPredictionResults.jsx";
import "./fps-calculator.css";
const RESOLUTIONS = [
  { value: "1080", label: "FHD · 1080p" },
  { value: "1440", label: "QHD · 1440p" },
  { value: "2160", label: "4K · 2160p" },
];

export default function FpsCalculatorScreen() {
  const { state, store } = useApp([
    "fpsCalculator",
    "catalogs",
    "games",
    "catalogError",
  ]);
  const { input, loading, error, data } = state.fpsCalculator;
  const cpus = useMemo(
    () =>
      (state.catalogs.cpu || []).filter(
        (cpu) =>
          !cpu.tags?.includes("mobile") &&
          !String(cpu.socket || "").startsWith("BGA"),
      ),
    [state.catalogs.cpu],
  );
  const gpus = state.catalogs.gpu || [];
  const cpu = cpus.find((part) => part.id === input.cpuId),
    gpu = gpus.find((part) => part.id === input.gpuId);
  const ram = calculatorRam(cpu, state.catalogs);
  useEffect(() => () => store.cancelFpsCalculator(), [store]);
  return (
    <main className="app-view fps-calculator" id="fpsCalculatorSection">
      <PageHeading title="내 PC로, 얼마나 부드럽게 플레이할까요?">
        CPU와 GPU를 골라 게임과 해상도에 따른 평균 FPS와 1% Low를 비교해 보세요.
      </PageHeading>
      <div className="fps-calculator-layout">
        <section
          className="fps-calculator-form ui-panel"
          aria-labelledby="fps-settings-heading"
        >
          <header>
            <span className="fps-eyebrow">게임별 FPS 예측</span>
            <h3 id="fps-settings-heading">PC 사양과 게임 설정</h3>
            <p>제품명 일부로도 빠르게 찾을 수 있어요.</p>
          </header>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void store.calculateFps();
            }}
          >
            <SearchableSelect
              label="CPU"
              icon="cpu"
              placeholder="예: 9800X3D, 인텔"
              items={cpus}
              value={input.cpuId}
              onChange={(cpuId) => store.updateFpsCalculator({ cpuId })}
            />
            <SearchableSelect
              label="GPU"
              icon="gpu"
              placeholder="예: RTX 5070, 라데온"
              items={gpus}
              value={input.gpuId}
              onChange={(gpuId) => store.updateFpsCalculator({ gpuId })}
            />
            <SearchableSelect
              label="게임"
              gameImages
              placeholder="게임 이름 검색"
              items={state.games}
              value={input.game}
              onChange={(game) => store.updateFpsCalculator({ game })}
            />
            <fieldset className="fps-resolution">
              <legend>해상도</legend>
              <SegmentedControl
                label="FPS 예측 해상도"
                options={RESOLUTIONS}
                value={input.resolution}
                onChange={(resolution) =>
                  store.updateFpsCalculator({ resolution })
                }
              />
            </fieldset>
            <div className="fps-assumptions">
              <Icon name="ram" size={18} />
              <p>
                <strong>{cpu ? ram.type + " " : ""}32GB RAM 기준</strong>
                <span>
                  CPU에 맞는 메모리 규격을 적용해요. 기본 표는 원본 해상도
                  기준이며, DLSS·FSR·프레임 생성 결과는 별도로 비교할 수 있어요.
                </span>
              </p>
            </div>
            {state.catalogError ? (
              <p className="fps-form-note">
                최신 부품 목록을 불러오지 못해 기본 목록을 표시합니다.{" "}
                <button type="button" onClick={() => store.loadCatalog()}>
                  목록 다시 불러오기
                </button>
              </p>
            ) : null}
            <button
              className="fps-calculate-button"
              type="submit"
              disabled={!cpu || !gpu || loading}
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  FPS 계산 중…
                </>
              ) : (
                "FPS 예측하기"
              )}
            </button>
            {loading ? (
              <button
                type="button"
                className="fps-cancel-button"
                onClick={store.cancelFpsCalculator}
              >
                계산 취소
              </button>
            ) : null}
          </form>
        </section>
        <section
          className={`fps-calculator-output ui-panel${data ? " has-result" : ""}`}
          aria-label="게임 FPS 예측 결과"
          aria-busy={loading}
        >
          {loading ? (
            <div className="fps-calculator-empty" role="status">
              <span className="spinner" />
              <h3>선택한 구성의 FPS를 계산하고 있어요</h3>
              <p>게임별 측정 자료와 하드웨어 성능을 확인합니다.</p>
            </div>
          ) : error ? (
            <div
              className="fps-calculator-empty fps-calculator-error"
              role="alert"
            >
              <Icon name="reset" size={32} />
              <h3>FPS를 불러오지 못했어요</h3>
              <p>{error}</p>
              <button
                type="button"
                className="fps-calculate-button"
                onClick={store.calculateFps}
              >
                다시 계산하기
              </button>
            </div>
          ) : data ? (
            <FpsPredictionResults {...data} />
          ) : (
            <div className="fps-calculator-empty">
              <span className="fps-empty-icon">
                <Icon name="gpu" size={38} />
              </span>
              <h3>내 구성의 게임 성능을 확인하세요</h3>
              <p>
                CPU와 GPU를 선택한 뒤 ‘FPS 예측하기’를 누르면
                <br />
                옵션별 평균 FPS와 1% Low를 볼 수 있어요.
              </p>
              <div className="fps-empty-legend">
                <span>평균 FPS</span>
                <span>1% Low</span>
              </div>
              <p className="fps-low-explanation">
                1% Low는 느린 1% 구간의 프레임 성능으로,
                <br />
                게임 중 순간적인 끊김을 비교하는 데 도움이 됩니다.
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
