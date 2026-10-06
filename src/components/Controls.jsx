import React from "react";

const h = React.createElement;
const icons = {
  cpu: "M8 8h8v8H8z M5 9H2m3 6H2m20-6h-3m3 6h-3M9 5V2m6 3V2M9 22v-3m6 3v-3 M5 5h14v14H5z",
  mb: "M5 3h14v18H5z M8 6h5v5H8z M8 15h8m-8 3h8m0-12v5",
  gpu: "M3 6h18v12H3z M7 18v3m4-3v3 M8 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6 M17 9v6",
  ram: "M2 7h20v10H2z M5 10h3v4H5zm6 0h3v4h-3zm6 0h2v4h-2 M5 17v3m4-3v3m4-3v3m4-3v3",
  storage: "M6 4h12l3 16H3z M4 16h16",
  hdd: "M5 3h14v18H5z M12 7a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 11l4 4",
  psu: "M13 2L4 14h7l-1 8 10-13h-7z",
  case: "M6 2h12v20H6z M9 6h6m-6 4h6m-6 7h1",
  software: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  search: "M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6",
  close: "M6 6l12 12M18 6L6 18",
  down: "M5 9l7 7 7-7",
  check: "M5 12l4 4L19 6",
  reset: "M3 10a9 9 0 1 1 1 8 M3 3v7h7",
};
export function Icon({ name, size = 20 }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 1.7,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      "aria-hidden": true,
    },
    h("path", { d: icons[name] || icons.cpu }),
  );
}
export function Button({ children, onClick, className = "", ...props }) {
  return h(
    "button",
    { type: "button", className: "pc-button " + className, onClick, ...props },
    children,
  );
}
