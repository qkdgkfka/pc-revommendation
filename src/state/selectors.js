/** Keep selected snapshots stable until one of their fields changes. */
export function createStateSelector(fields) {
  let snapshot;
  return (state) => {
    if (!fields) return state;
    if (
      !snapshot ||
      fields.some((key) => !Object.is(snapshot[key], state[key]))
    ) {
      snapshot = Object.fromEntries(fields.map((key) => [key, state[key]]));
    }
    return snapshot;
  };
}
