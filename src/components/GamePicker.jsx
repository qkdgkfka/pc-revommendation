import React, { useEffect, useId, useRef, useState } from "react";
import { useApp } from "../state/context.jsx";
import { GAME_CATEGORIES } from "../domain/options.js";
import { gameCategoryFor } from "../state/initialState.js";
import GameArtwork from "./GameArtwork.jsx";
export default function GamePicker({ manual = false }) {
  const { state, store } = useApp([
      "games",
      "csGameCategory",
      "gameCategory",
      "csGame",
      "game",
    ]),
    [open, setOpen] = useState(false),
    [position, setPosition] = useState({}),
    wrapper = useRef(null),
    trigger = useRef(null),
    list = useRef(null),
    id = useId();
  const category = manual ? state.csGameCategory : state.gameCategory,
    value = manual ? state.csGame : state.game,
    games = open
      ? state.games.filter(
          (game) => gameCategoryFor(game.id, state.games) === category,
        )
      : [],
    selected = state.games.find((game) => game.id === value);
  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (!wrapper.current?.contains(e.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);
  useEffect(() => {
    if (open)
      (
        list.current?.querySelector('[aria-selected="true"]') ||
        list.current?.firstElementChild
      )?.focus();
  }, [open]);
  function show() {
    const rect = trigger.current.getBoundingClientRect(),
      above = rect.top,
      below = window.innerHeight - rect.bottom,
      upward = below < 280 && above > below;
    setPosition({
      top: upward ? "auto" : "calc(100% + 5px)",
      bottom: upward ? "calc(100% + 5px)" : "auto",
      maxHeight: Math.max(100, Math.min(280, (upward ? above : below) - 12)),
    });
    setOpen(true);
  }
  function keys(e) {
    const options = [...list.current.children],
      index = options.indexOf(document.activeElement);
    if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
      trigger.current.focus();
    } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
      e.preventDefault();
      const next =
        e.key === "Home"
          ? 0
          : e.key === "End"
            ? options.length - 1
            : (index + (e.key === "ArrowDown" ? 1 : -1) + options.length) %
              options.length;
      options[next]?.focus();
    } else if (e.key.length === 1 && e.key !== " ") {
      const match =
        options.find(
          (o, i) =>
            i > index &&
            o.textContent.toLowerCase().startsWith(e.key.toLowerCase()),
        ) ||
        options.find((o) =>
          o.textContent.toLowerCase().startsWith(e.key.toLowerCase()),
        );
      match?.focus();
    }
  }
  return (
    <div className="game-select-stack">
      <select
        id={manual ? "csGameCategorySelect" : "gameCategorySelect"}
        className={manual ? "custom-game-select" : "gsel"}
        aria-label="게임 카테고리"
        value={category}
        onChange={(e) => store.chooseGameCategory(e.target.value, manual)}
      >
        {GAME_CATEGORIES.map((c) => (
          <option key={c.id} value={c.id}>
            {c.label}
          </option>
        ))}
      </select>
      <div
        className="game-picker"
        ref={wrapper}
        onBlur={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false);
        }}
      >
        <button
          ref={trigger}
          type="button"
          id={manual ? "csGameSelect" : "gameSelect"}
          className="game-picker-trigger"
          aria-label="세부 게임"
          aria-haspopup="listbox"
          aria-controls={id}
          aria-expanded={open}
          onClick={() => (open ? setOpen(false) : show())}
          onKeyDown={(e) => {
            if (["ArrowDown", "ArrowUp"].includes(e.key)) {
              e.preventDefault();
              show();
            }
          }}
        >
          {selected ? (
            <>
              <GameArtwork id={selected.id} />
              {selected.label}
            </>
          ) : (
            "게임 선택"
          )}
        </button>
        <div
          id={id}
          className="game-picker-options"
          ref={list}
          role="listbox"
          aria-label="게임 목록"
          hidden={!open}
          style={position}
          onKeyDown={keys}
        >
          {games.map((game) => (
            <button
              type="button"
              key={game.id}
              tabIndex={-1}
              role="option"
              aria-selected={game.id === value}
              data-value={game.id}
              onClick={() => {
                store.update(manual ? { csGame: game.id } : { game: game.id });
                setOpen(false);
                trigger.current.focus();
              }}
            >
              <GameArtwork id={game.id} lazy />
              {game.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
