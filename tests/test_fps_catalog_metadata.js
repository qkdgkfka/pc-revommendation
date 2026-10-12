import { test } from "node:test";
import assert from "node:assert/strict";
import { catalogPatch } from "../src/state/catalog.js";
import { initialState } from "../src/state/initialState.js";
import { productMatchesQuery } from "../src/domain/productSearch.js";
test("live game metadata retains English names and aliases for calculator search", () => {
  const result = catalogPatch(
    {
      games: [
        {
          id: "league_of_legends",
          label: "리그 오브 레전드",
          english_title: "League of Legends",
          aliases: ["롤", "LoL"],
          category: "fps",
        },
      ],
    },
    initialState(),
  );
  const game = result.games[0];
  assert.deepEqual(game.aliases, ["롤", "LoL"]);
  assert.equal(game.english_title, "League of Legends");
  const text = [game.label, game.english_title, ...game.aliases].join(" ");
  for (const query of ["롤", "LoL", "League"])
    assert.equal(productMatchesQuery(query, text), true);
});
