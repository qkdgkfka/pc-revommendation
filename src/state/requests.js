export class RequestError extends Error {
  constructor(kind, message) {
    super(message);
    this.name = "RequestError";
    this.kind = kind;
  }
}
export const errorMessage = (error) =>
  error?.kind === "cancelled"
    ? "요청을 취소했습니다."
    : error?.kind === "timeout"
      ? "요청 시간이 초과되었습니다. 다시 확인해주세요."
      : error?.message || "판매처 연결에 실패했습니다. 다시 확인해주세요.";

/** Publish a shared request once, ignoring completions invalidated by cancellation. */
export function runRequest(entry, { onStart, onSuccess, onError }) {
  if (entry.task) return entry.task;
  onStart?.();
  entry.task = entry.promise
    .then((data) => {
      if (entry.current()) return onSuccess?.(data);
    })
    .catch((error) => {
      if (entry.current()) return onError?.(error);
    });
  return entry.task;
}

/** One request per scope; identical work joins, replacement aborts and invalidates. */
export function createRequestManager() {
  const active = new Map(),
    versions = new Map();
  const cancel = (scope) => {
    versions.set(scope, (versions.get(scope) || 0) + 1);
    active
      .get(scope)
      ?.controller.abort(new RequestError("cancelled", "요청을 취소했습니다."));
    active.delete(scope);
  };
  function start(scope, key, executor, timeout = 30000) {
    const existing = active.get(scope);
    if (existing?.key === key) return existing;
    cancel(scope);
    const token = versions.get(scope),
      controller = new AbortController();
    const entry = {
      key,
      token,
      controller,
      current: () => versions.get(scope) === token,
    };
    let timer;
    const aborted = new Promise((_, reject) =>
      controller.signal.addEventListener(
        "abort",
        () =>
          reject(
            controller.signal.reason ||
              new RequestError("cancelled", "요청을 취소했습니다."),
          ),
        { once: true },
      ),
    );
    timer = setTimeout(
      () =>
        controller.abort(
          new RequestError("timeout", "요청 시간이 초과되었습니다."),
        ),
      timeout,
    );
    let work;
    try {
      work = executor(controller.signal);
    } catch (error) {
      work = Promise.reject(error);
    }
    entry.promise = Promise.race([work, aborted]).finally(() => {
      clearTimeout(timer);
      if (active.get(scope) === entry) active.delete(scope);
    });
    active.set(scope, entry);
    return entry;
  }
  return { start, cancel, cancelAll: () => [...active.keys()].forEach(cancel) };
}

export function createJsonClient(fetcher, base = "") {
  return async function json(url, signal, body) {
    const response = await fetcher(base + url, {
      signal,
      ...(body
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        : {}),
    });
    let data;
    try {
      data = await response.json();
      if (!data || typeof data !== "object" || Array.isArray(data))
        throw new Error("JSON object required");
    } catch {
      throw new RequestError(
        "upstream",
        "서버 응답 형식을 확인하지 못했습니다.",
      );
    }
    if (!response.ok || data?.ok === false)
      throw new RequestError(
        data?.error_kind === "timeout" ? "timeout" : "upstream",
        data?.error ||
          `판매처 연결에 실패했습니다 (HTTP ${response.status || "오류"}).`,
      );
    return data;
  };
}
