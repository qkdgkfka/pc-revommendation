import { test } from "node:test";
import assert from "node:assert/strict";
import { createStateSelector } from "../src/state/selectors.js";

test("selected snapshots ignore unrelated edits and track replaced values", () => {
  const select = createStateSelector(["selected", "builderPart"]);
  const state = { selected: {}, builderPart: "cpu", productDraft: "" };
  const first = select(state);
  assert.equal(select({ ...state, productDraft: "Ryzen" }), first);
  const selected = { cpu: { id: "7600" } };
  const next = select({ ...state, selected });
  assert.notEqual(next, first);
  assert.equal(next.selected, selected);
  assert.equal(select({ ...state, selected }), next);
  assert.equal(
    select({ ...state, selected, builderPart: "gpu" }).builderPart,
    "gpu",
  );
});

test("selectors can change fields without retaining a previous selection", () => {
  const state = { csGame: "valorant", game: "cyberpunk2077" };
  assert.deepEqual(createStateSelector(["csGame"])(state), {
    csGame: "valorant",
  });
  assert.deepEqual(createStateSelector(["game"])(state), {
    game: "cyberpunk2077",
  });
  assert.equal(createStateSelector()(state), state);
});
