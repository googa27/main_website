import { readFileSync } from "node:fs";

export function readLiveProcessFile(path) {
  try {
    return readFileSync(path, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return undefined;
    throw error;
  }
}

export function recordOwnedChildren(parentPID, observedChildren) {
  if (process.platform !== "linux") return;
  const parentStat = readLiveProcessFile(
    "/proc/" + parentPID + "/task/" + parentPID + "/children",
  );
  // A missing proc entry does not prove a reap: the caller still awaits the real exit.
  if (parentStat === undefined) return;
  for (const value of parentStat.trim().split(/\s+/).filter(Boolean)) {
    const path = "/proc/" + value + "/stat";
    const current = readLiveProcessFile(path);
    if (current !== undefined) observedChildren.set(value, current);
  }
}
