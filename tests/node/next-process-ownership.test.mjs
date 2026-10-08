import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { existsSync } from "node:fs";
import test from "node:test";
import { recordOwnedChildren } from "./next-process-ownership.mjs";

test(
  "a naturally exited real parent does not mask verification cleanup",
  { skip: process.platform !== "linux" },
  async () => {
    const child = spawn(process.execPath, ["-e", "process.exit(0)"], {
      stdio: "ignore",
    });
    const [code, signal] = await once(child, "exit");
    assert.equal(code, 0);
    assert.equal(signal, null);
    assert.equal(existsSync("/proc/" + child.pid), false);
    const observed = new Map();
    assert.doesNotThrow(() => recordOwnedChildren(child.pid, observed));
    assert.equal(observed.size, 0);
    console.log("Real parent naturally exited", child.pid, code, signal);
  },
);
