import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { Icon } from "../Controls.jsx";
import { productMatchesQuery } from "../../domain/productSearch.js";
import GameArtwork from "../GameArtwork.jsx";

export default function SearchableSelect({
  label,
  placeholder,
  items,
  value,
  onChange,
  icon,
  gameImages = false,
}) {
  const id = useId(),
    list = useRef(null),
    [open, setOpen] = useState(false),
    [query, setQuery] = useState(""),
    [active, setActive] = useState(0);
  const selected = items.find((item) => item.id === value);
  const matches = useMemo(
    () =>
      query.trim()
        ? items.filter((item) =>
            productMatchesQuery(query, {
              name: [
                item.label || item.name,
                item.english_title,
                ...(item.aliases || []),
              ]
                .filter(Boolean)
                .join(" "),
              brand: item.vendor,
              model: item.id.replaceAll("_", " "),
            }),
          )
        : items,
    [items, query],
  );
  const highlighted = Math.min(active, Math.max(0, matches.length - 1));
  useEffect(() => {
    if (open)
      list.current?.children[highlighted]?.scrollIntoView({ block: "nearest" });
  }, [open, highlighted]);
  function choose(item) {
    onChange(item.id);
    setOpen(false);
    setQuery("");
  }
  function keys(event) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      if (!open) {
        setQuery("");
        setActive(0);
        setOpen(true);
        return;
      }
      setActive(
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? Math.max(0, matches.length - 1)
            : Math.max(
                0,
                Math.min(
                  matches.length - 1,
                  highlighted + (event.key === "ArrowDown" ? 1 : -1),
                ),
              ),
      );
    } else if (event.key === "Enter" && open) {
      event.preventDefault();
      if (matches[highlighted]) choose(matches[highlighted]);
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      setOpen(false);
      setQuery("");
    }
  }
  return (
    <div
      className="fps-select"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false);
          setQuery("");
        }
      }}
    >
      <label htmlFor={id}>
        <Icon name={icon || "search"} size={17} />
        {label}
      </label>
      <div className={`fps-select-control${gameImages ? " with-artwork" : ""}`}>
        {gameImages && selected ? <GameArtwork id={selected.id} /> : null}
        <input
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={id + "-list"}
          aria-autocomplete="list"
          aria-activedescendant={
            open && matches.length ? id + "-option-" + highlighted : undefined
          }
          autoComplete="off"
          placeholder={placeholder}
          value={open ? query : selected?.label || selected?.name || ""}
          onFocus={() => {
            setQuery("");
            setActive(0);
            setOpen(true);
          }}
          onClick={() => {
            if (!open) {
              setQuery("");
              setActive(0);
              setOpen(true);
            }
          }}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
            setOpen(true);
          }}
          onKeyDown={keys}
        />
        <Icon name="down" size={16} />
      </div>
      {open ? (
        <div className="fps-select-popup">
          <div
            ref={list}
            id={id + "-list"}
            role="listbox"
            aria-label={label + " 목록"}
          >
            {matches.map((item, index) => (
              <button
                key={item.id}
                id={id + "-option-" + index}
                type="button"
                role="option"
                tabIndex={-1}
                aria-selected={item.id === value}
                className={index === highlighted ? "is-active" : ""}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(item)}
              >
                {gameImages ? <GameArtwork id={item.id} lazy /> : null}
                <span>{item.label || item.name}</span>
                {item.id === value ? <Icon name="check" size={16} /> : null}
              </button>
            ))}
          </div>
          {!matches.length ? (
            <p role="status">일치하는 항목이 없습니다.</p>
          ) : (
            <span className="fps-select-count">
              {matches.length}개 · 방향키와 Enter로 선택
            </span>
          )}
        </div>
      ) : null}
    </div>
  );
}
