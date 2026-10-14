import { test } from "node:test";
import assert from "node:assert/strict";
import * as requests from "../src/state/requests.js";

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

test("joined requests publish loading and completion only once and share their task", async () => {
  const manager = requests.createRequestManager();
  const pending = deferred();
  const events = [];
  const handlers = {
    onStart: () => events.push("loading"),
    onSuccess: (value) => events.push(value),
  };
  const first = manager.start("products", "cpu", () => pending.promise);
  const task = requests.runRequest(first, handlers);
  const joined = manager.start("products", "cpu", () =>
    assert.fail("duplicate fetch"),
  );
  assert.equal(requests.runRequest(joined, handlers), task);
  assert.deepEqual(events, ["loading"]);
  pending.resolve("ready");
  await task;
  assert.deepEqual(events, ["loading", "ready"]);
});

test("cancelled requests ignore both late success and failure", async () => {
  for (const outcome of ["resolve", "reject"]) {
    const manager = requests.createRequestManager();
    const pending = deferred();
    const completions = [];
    const task = requests.runRequest(
      manager.start("fps", "old", () => pending.promise),
      {
        onSuccess: () => completions.push("success"),
        onError: () => completions.push("error"),
      },
    );
    manager.cancel("fps");
    pending[outcome](new Error("late response"));
    await task;
    assert.deepEqual(completions, []);
  }
});

test("a completed response invalidated before publication cannot update state", async () => {
  const manager = requests.createRequestManager();
  const entry = manager.start("catalog", "compact", () => ({ catalogs: [] }));
  await entry.promise;
  manager.cancel("catalog");
  let published = false;
  await requests.runRequest(entry, {
    onSuccess: () => {
      published = true;
    },
  });
  assert.equal(published, false);
});

test("response validation failures reach the current request error handler", async () => {
  const manager = requests.createRequestManager();
  const validationError = new requests.RequestError("empty", "missing FPS");
  let reported;
  await requests.runRequest(
    manager.start("fps", "input", () => ({})),
    {
      onSuccess: () => {
        throw validationError;
      },
      onError: (error) => {
        reported = error;
      },
    },
  );
  assert.equal(reported, validationError);
});

test("timeouts reach the current request error handler and optional errors are silent", async () => {
  const manager = requests.createRequestManager();
  let reported;
  await requests.runRequest(
    manager.start("fps", "input", () => new Promise(() => {}), 5),
    {
      onError: (error) => {
        reported = error;
      },
    },
  );
  assert.equal(reported.kind, "timeout");
  let published = false;
  await requests.runRequest(
    manager.start("prices", "input", () => {
      throw new Error("offline");
    }),
    {
      onSuccess: () => {
        published = true;
      },
    },
  );
  assert.equal(published, false);
});
