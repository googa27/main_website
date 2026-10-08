import { readFileSync } from "node:fs";

export function observeOwnedProcess(
  child,
  { maxOutputBytes = 1024 * 1024 } = {},
) {
  const retained = Buffer.alloc(maxOutputBytes);
  let retainedBytes = 0;
  let outputBoundExceeded = false;
  let result;
  let error;
  let closed = false;
  // Event handlers record state; assertions belong inside the caller's try/finally.
  const capture = (chunk) => {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    if (bytes.length >= maxOutputBytes - retainedBytes)
      outputBoundExceeded = true;
    retainedBytes += bytes.copy(
      retained,
      retainedBytes,
      0,
      maxOutputBytes - retainedBytes,
    );
  };
  child.stdout?.on("data", capture);
  child.stderr?.on("data", capture);
  child.on("error", (observed) => {
    error ??= observed;
  });
  child.once("exit", (code, signal) => {
    result = { code, signal };
  });
  const exited = new Promise((resolveExit) => {
    // close follows exit or a failed spawn, after the owned stdio streams close.
    child.once("close", () => {
      closed = true;
      result ??= { error };
      resolveExit(result);
    });
  });
  return {
    get output() {
      return retained.toString("utf8", 0, retainedBytes);
    },
    get outputBoundExceeded() {
      return outputBoundExceeded;
    },
    get result() {
      return result;
    },
    get error() {
      return error;
    },
    get closed() {
      return closed;
    },
    exited,
  };
}

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
