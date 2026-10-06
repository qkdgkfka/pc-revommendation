import React from "react";
import { useApp } from "../state/context.jsx";
export function WorkSelect({ manual = false }) {
  const { state, store } = useApp(["workProfiles", "csWork", "panelWork"]);
  const groups = [
    ...new Set(Object.values(state.workProfiles).map((p) => p.group)),
  ];
  return (
    <select
      className={manual ? "custom-game-select" : "gsel"}
      id={manual ? "csWorkSelect" : "panelWorkSelect"}
      aria-label="세부 작업"
      value={manual ? state.csWork : state.panelWork}
      onChange={(e) =>
        store.update(
          manual ? { csWork: e.target.value } : { panelWork: e.target.value },
        )
      }
    >
      {groups.map((group) => (
        <optgroup key={group} label={group}>
          {Object.entries(state.workProfiles)
            .filter(([, p]) => p.group === group)
            .map(([key, p]) => (
              <option key={key} value={key}>
                {p.name}
              </option>
            ))}
        </optgroup>
      ))}
    </select>
  );
}
