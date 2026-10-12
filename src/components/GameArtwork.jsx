import React from "react";
const fallback =
  "data:image/svg+xml," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="32"><rect width="48" height="32" rx="6" fill="#dbeafe"/><path d="M15 10h18l5 14h-7l-3-4h-8l-3 4h-7z" fill="#2563eb"/></svg>',
  );
export default function GameArtwork({ id, lazy = false }) {
  return (
    <img
      src={"/assets/game-icons/" + encodeURIComponent(id) + ".jpg"}
      width="42"
      height="28"
      loading={lazy ? "lazy" : "eager"}
      alt=""
      onError={(event) => {
        if (event.currentTarget.src !== fallback)
          event.currentTarget.src = fallback;
      }}
    />
  );
}
