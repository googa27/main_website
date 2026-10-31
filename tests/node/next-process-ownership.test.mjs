import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync, rmdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import {
  observeOwnedProcess,
  ownedNodeIdentityArgs,
  ownedProcessStillLive,
  recordOwnedChildren,
} from "./next-process-ownership.mjs";

test(
  "a naturally exited real parent does not mask verification cleanup",
  { skip: process.platform !== "linux" },
  async () => {
    const child = spawn(
      process.execPath,
      [...ownedNodeIdentityArgs, "-e", "process.exit(0)"],
      { stdio: ["ignore", "pipe", "pipe"] },
    );
    const observation = observeOwnedProcess(child);
    const { code, signal } = await observation.exited;
    assert.equal(code, 0);
    assert.equal(signal, null);
    assert.ok(observation.procIdentity, "Actual child procfs identity absent");
    assert.equal(ownedProcessStillLive(observation.procIdentity), false);
    const observed = new Map();
    assert.doesNotThrow(() =>
      recordOwnedChildren(observation.procIdentity.proc, observed),
    );
    assert.equal(observed.size, 0);
    console.log(
      "Real parent naturally exited",
      observation.procIdentity,
      code,
      signal,
    );
  },
);

const pause = () => new Promise((resolve) => setTimeout(resolve, 25));

test("output flooding fails inside the controlled flow and still closes the real child", async () => {
  const child = spawn(
    process.execPath,
    [
      ...ownedNodeIdentityArgs,
      "-e",
      "process.stdout.write(Buffer.alloc(2 * 1024 * 1024, 'x')); setInterval(() => {}, 1000);",
    ],
    { stdio: ["ignore", "pipe", "pipe"] },
  );
  const observation = observeOwnedProcess(child, { maxOutputBytes: 128 });
  await assert.rejects(async () => {
    try {
      const deadline = Date.now() + 5000;
      while (
        !observation.outputBoundExceeded &&
        observation.result === undefined &&
        Date.now() < deadline
      )
        await pause();
      assert.equal(observation.outputBoundExceeded, true);
      if (process.platform === "linux") {
        assert.ok(
          observation.procIdentity,
          "Actual flood child identity absent",
        );
        const prefix =
          "OWNED_PROC " + JSON.stringify(observation.procIdentity) + "\n";
        assert.equal(
          observation.output,
          prefix + "x".repeat(128 - prefix.length),
        );
      } else assert.equal(observation.output, "x".repeat(128));
      throw new Error("controlled startup bound failure");
    } finally {
      if (observation.result === undefined) child.kill("SIGTERM");
      const deadline = Date.now() + 5000;
      while (!observation.closed && Date.now() < deadline) await pause();
      assert.equal(
        observation.closed,
        true,
        "Owned child close unproved; preserve PID " + child.pid,
      );
      const result = await observation.exited;
      assert.equal(result.signal, "SIGTERM");
      assert.equal(observation.error, undefined);
      if (process.platform === "linux")
        assert.equal(ownedProcessStillLive(observation.procIdentity), false);
      console.log(
        "Real output-bound fixture closed",
        child.pid,
        JSON.stringify(result),
      );
    }
  }, /controlled startup bound failure/);
});

test("a missing executable is observed without an unhandled rejection or invented PID", async () => {
  const directory = mkdtempSync(join(tmpdir(), "next-owned-spawn-fixture-"));
  try {
    const child = spawn(join(directory, "absent-executable"), [], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    const observation = observeOwnedProcess(child);
    const deadline = Date.now() + 5000;
    while (!observation.closed && Date.now() < deadline) await pause();
    assert.equal(observation.closed, true, "Failed spawn close unproved");
    const result = await observation.exited;
    assert.equal(result.error.code, "ENOENT");
    assert.equal(observation.error, result.error);
    assert.equal(child.pid, undefined);
    assert.equal(observation.output, "");
    console.log(
      "Actual failed spawn observed",
      result.error.code,
      "no PID allocated",
    );
  } finally {
    rmdirSync(directory);
  }
});

test(
  "the actual live procfs identity is distinguished from a reused PID",
  { skip: process.platform !== "linux" },
  async () => {
    const child = spawn(
      process.execPath,
      [...ownedNodeIdentityArgs, "-e", "setInterval(() => {}, 1000)"],
      { stdio: ["ignore", "pipe", "pipe"] },
    );
    const observation = observeOwnedProcess(child);
    try {
      const deadline = Date.now() + 5000;
      while (
        !observation.procIdentity &&
        !observation.closed &&
        Date.now() < deadline
      )
        await pause();
      assert.ok(observation.procIdentity, "Actual live child identity absent");
      assert.equal(ownedProcessStillLive(observation.procIdentity), true);
      assert.equal(
        ownedProcessStillLive({
          ...observation.procIdentity,
          start: String(BigInt(observation.procIdentity.start) + 1n),
        }),
        false,
      );
    } finally {
      if (observation.result === undefined) child.kill("SIGTERM");
      const { signal } = await observation.exited;
      assert.equal(signal, "SIGTERM");
      assert.equal(ownedProcessStillLive(observation.procIdentity), false);
    }
  },
);
