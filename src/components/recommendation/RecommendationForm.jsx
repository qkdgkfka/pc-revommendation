import React from "react";
import { useApp } from "../../state/context.jsx";
import { Icon } from "../../screens/ManualScreen.jsx";
import GamePicker from "../GamePicker.jsx";
import { WorkSelect } from "../Performance.jsx";

const BUDGETS = [
  { value: 2000000, min: 1000000, label: "100~200만원" },
  { value: 3000000, min: 2000000, label: "200~300만원" },
  { value: 4500000, min: 3000000, label: "300만원 이상" },
  { value: "unlimited", min: 0, label: "금액 설정 안함" },
];
const RESOLUTIONS = [
  { value: "1080", label: "FHD", hint: "1080p" },
  { value: "1440", label: "QHD", hint: "1440p" },
  { value: "2160", label: "4K", hint: "2160p" },
];
const REFRESH_RATES = [60, 120, 144, 240].map((value) => ({
  value,
  label: `${value}Hz`,
}));
const CHIPSETS = [
  { value: "nopref", label: "선호 없음" },
  { value: "nvidia", label: "NVIDIA" },
  { value: "amd", label: "AMD" },
];
const MAKERS = [
  ["msi", "MSI"],
  ["gigabyte", "Gigabyte"],
  ["palit", "Palit"],
  ["colorful", "Colorful"],
  ["asus", "ASUS"],
  ["zotac", "ZOTAC"],
  ["galax", "GALAX"],
  ["emtek", "Emtek"],
].map(([value, label]) => ({ value, label }));

function Field({ title, children, optional = false }) {
  return (
    <fieldset className="ai-field">
      <legend>
        {title}
        {optional ? <span className="ai-optional">선택</span> : null}
      </legend>
      {children}
    </fieldset>
  );
}
function Choices({
  id,
  items,
  value,
  onChange,
  multiple = false,
  budget = false,
}) {
  return (
    <div
      className={`ai-choices${budget ? " ai-budget-choices" : ""}${multiple ? " ai-maker-choices" : ""}`}
      id={id}
    >
      {items.map((item) => {
        const selected = multiple
          ? value.includes(item.value)
          : value === item.value;
        return (
          <button
            type="button"
            key={item.value}
            className={`ai-choice${selected ? " is-selected" : ""}`}
            aria-pressed={selected}
            onClick={() => onChange(item)}
          >
            <span>
              {item.label}
              {item.hint ? <small>{item.hint}</small> : null}
            </span>
            {budget ? (
              <span className="ai-choice-check">
                {selected ? <Icon name="check" size={16} /> : null}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
export default function RecommendationForm() {
  const { state, store } = useApp();
  const loading = state.recommendation.loading;
  return (
    <form
      className="ai-form"
      aria-labelledby="ai-form-heading"
      onSubmit={(event) => {
        event.preventDefault();
        void store.recommend();
      }}
    >
      <header className="ai-form-heading">
        <h3 id="ai-form-heading">추천 조건</h3>
        <p>필요한 조건만 골라주세요</p>
      </header>
      <Field title="예산">
        <Choices
          id="budgetChoices"
          items={BUDGETS}
          value={
            state.budgetMode === "unlimited" ? "unlimited" : state.budgetMax
          }
          budget
          onChange={(item) =>
            store.update(
              item.value === "unlimited"
                ? { budgetMode: "unlimited" }
                : {
                    budgetMode: "soft",
                    budget: item.value,
                    budgetMax: item.value,
                    budgetMin: item.min,
                  },
            )
          }
        />
        <p className="ai-hint">
          {state.budgetMode === "unlimited"
            ? "가격 제한 없이 선택한 사양에 맞춰 추천해요."
            : "선택 금액은 목표 예산이에요. 성능을 위해 최대 20% 초과할 수 있어요."}
        </p>
      </Field>
      <Field title="사용 목적">
        <div className="ai-purpose">
          {[
            ["game", "게임", "panelModeGame"],
            ["work", "작업", "panelModeWork"],
          ].map(([value, label, id]) => (
            <button
              type="button"
              key={value}
              id={id}
              aria-pressed={state.panelMode === value}
              className={state.panelMode === value ? "is-selected" : ""}
              onClick={() => store.update({ panelMode: value })}
            >
              {label}
            </button>
          ))}
        </div>
        {state.panelMode === "game" ? (
          <div id="panelGameSub" className="ai-purpose-detail">
            <GamePicker />
          </div>
        ) : (
          <div id="panelWorkSub" className="ai-purpose-detail">
            <WorkSelect />
            <p className="ai-hint">
              영상 편집은 해상도에 맞춰 작업 강도를 선택해 주세요.
            </p>
          </div>
        )}
      </Field>
      <Field title="해상도">
        <Choices
          id="resChoices"
          items={RESOLUTIONS}
          value={state.resolution}
          onChange={(item) => store.update({ resolution: item.value })}
        />
      </Field>
      <Field title="주사율">
        <Choices
          id="refreshChoices"
          items={REFRESH_RATES}
          value={state.refresh}
          onChange={(item) => store.update({ refresh: item.value })}
        />
      </Field>
      <Field title="GPU 칩셋 선호도">
        <Choices
          id="gpuPrefChoices"
          items={CHIPSETS}
          value={state.gpu_pref}
          onChange={(item) => store.update({ gpu_pref: item.value })}
        />
      </Field>
      <Field title="GPU 제조사" optional>
        <Choices
          id="gpuMakerChoices"
          items={MAKERS}
          value={state.gpu_brands}
          multiple
          onChange={({ value }) =>
            store.update({
              gpu_brands: state.gpu_brands.includes(value)
                ? state.gpu_brands.filter((maker) => maker !== value)
                : [...state.gpu_brands, value],
            })
          }
        />
        <p className="ai-hint">
          선택하지 않으면 목표 성능에 맞는 GPU 중 합리적인 제조사 제품군을
          우선해요.
        </p>
      </Field>
      <div className="ai-actions">
        <button
          type="submit"
          className="ai-submit"
          id="submitBtn"
          disabled={loading}
        >
          {loading ? <span className="spinner" aria-hidden="true" /> : null}
          <span id="submitBtnTxt">
            {loading ? "견적 분석 중…" : "견적 분석하기"}
          </span>
        </button>
        <button
          type="button"
          className="ai-reset"
          id="resetBtn"
          onClick={store.resetRecommendation}
        >
          초기화
        </button>
      </div>
    </form>
  );
}
