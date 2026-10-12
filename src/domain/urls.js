/** Browser links only. Server-side fetches require a separate destination allowlist. */
export function safeExternalUrl(value) {
  if (typeof value !== "string" || value.length > 2048) return "";
  const raw = value.replace(/^ +| +$/g, "");
  if (!raw || /[\u0000-\u0020\u007f\\]/.test(raw)) return "";
  try {
    const url = new URL(raw);
    return ["http:", "https:"].includes(url.protocol) &&
      url.hostname &&
      !url.username &&
      !url.password &&
      url.port !== "0"
      ? url.href
      : "";
  } catch {
    return "";
  }
}
