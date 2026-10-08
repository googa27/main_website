import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import {
  observeOwnedProcess,
  readLiveProcessFile,
  recordOwnedChildren,
} from "./next-process-ownership.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const web = resolve(root, "apps/web");
const webRequire = createRequire(resolve(web, "package.json"));
const manifestPath = webRequire.resolve("next/package.json");
const nextRequire = createRequire(manifestPath);

test("the real Next consumer excludes all seven owned vulnerable releases", () => {
  const [major, minor, patch] = nextRequire("./package.json")
    .version.split(".")
    .map(Number);
  assert.ok(
    major > 16 || (major === 16 && (minor > 3 || (minor === 3 && patch >= 8))),
    "Next must include the maintained 16.3.8 security repair cohort",
  );
});

const linuxGNU =
  process.platform === "linux" &&
  process.arch === "x64" &&
  Boolean(process.report.getReport().header.glibcVersionRuntime);

test(
  "the actual Next compiler executes the independently published GNU asset",
  { skip: !linuxGNU },
  () => {
    const policy = JSON.parse(
      readFileSync(resolve(root, "docs/ARCHITECTURE.yaml"), "utf8"),
    ).architecture.next_security_policy;
    assert.ok(
      policy?.published_assets,
      "Published Next compiler policy absent",
    );
    const binary = realpathSync(nextRequire.resolve("@next/swc-linux-x64-gnu"));
    const files = {
      next_manifest: manifestPath,
      GNU_manifest: resolve(dirname(binary), "package.json"),
      GNU_binary: binary,
    };
    for (const [name, file] of Object.entries(files)) {
      assert.ok(file.startsWith(resolve(root, "node_modules") + "/"));
      assert.equal(
        createHash("sha256").update(readFileSync(file)).digest("hex"),
        policy.published_assets[name],
        name + " differs from independently published bytes",
      );
    }
    // The synchronous adapter loads the installed native binding without a downloader fallback.
    const swc = webRequire("next/dist/build/swc");
    const result = swc.transformSync(
      "const amount: number = 7; export default amount + 5;",
      {
        filename: "literal.ts",
        jsc: { parser: { syntax: "typescript" }, target: "es2022" },
        module: { type: "commonjs" },
      },
    );
    const exports = {};
    vm.runInNewContext(result.code, { exports });
    assert.equal(exports.default, 12);
    assert.ok(
      readFileSync("/proc/self/maps", "utf8")
        .split("\n")
        .some((line) => line.endsWith(" " + binary)),
      "Next did not load its reviewed native compiler",
    );
  },
);

test("the actual developer MCP route admits local clients and refuses foreign origins", async () => {
  const child = spawn(
    process.execPath,
    [
      webRequire.resolve("next/dist/bin/next"),
      "dev",
      "--turbopack",
      "--hostname",
      "127.0.0.1",
      "--port",
      "0",
    ],
    {
      cwd: web,
      env: { ...process.env, NEXT_TELEMETRY_DISABLED: "1" },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  const observation = observeOwnedProcess(child);
  const checkStartupState = () => {
    assert.ifError(observation.error);
    assert.equal(
      observation.outputBoundExceeded,
      false,
      "Developer startup log bound exceeded",
    );
  };
  const pause = () =>
    new Promise((resolvePause) => setTimeout(resolvePause, 50));
  const observedChildren = new Map();
  const trackChildren = () => recordOwnedChildren(child.pid, observedChildren);
  try {
    const deadline = Date.now() + 45000; // Startup guard, never a security-performance oracle.
    while (!/Ready in/.test(observation.output)) {
      checkStartupState();
      assert.equal(
        observation.result,
        undefined,
        "Next stopped during startup: " + observation.output,
      );
      assert.ok(
        Date.now() < deadline,
        "Next startup did not finish: " + observation.output,
      );
      await pause();
    }
    checkStartupState();
    trackChildren();
    const output = observation.output;
    const port = output.match(/Local:\s+http:\/\/[^:\s]+:(\d+)/)?.[1];
    assert.ok(port, "Actual loopback listener was not reported: " + output);
    const origin = "http://127.0.0.1:" + port;
    const request = async (
      requestOrigin,
      path = "/_next/mcp",
      method = "initialize",
    ) => {
      const response = await fetch(origin + path, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
          Origin: requestOrigin,
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method,
          params:
            method === "initialize"
              ? {
                  protocolVersion: "2024-11-05",
                  capabilities: {},
                  clientInfo: {
                    name: "portfolio-security-contract",
                    version: "1.0.0",
                  },
                }
              : {},
        }),
        signal: AbortSignal.timeout(10000),
      });
      return { status: response.status, body: await response.text() };
    };
    for (const lookalike of ["/_next/mcp-extra", "/_next/mcp/extra"]) {
      const wrongRoute = await request(origin, lookalike);
      assert.ok(
        [404, 405].includes(wrongRoute.status),
        "MCP accepted a lookalike route: " + lookalike + ": " + wrongRoute.body,
      );
      assert.doesNotMatch(wrongRoute.body, /"serverInfo"/);
    }
    const local = await request(origin);
    assert.equal(local.status, 200, local.body);
    assert.match(local.body, /"jsonrpc":"2\.0"/);
    assert.match(local.body, /"serverInfo"/);
    const localTools = await request(origin, "/_next/mcp", "tools/list");
    assert.equal(localTools.status, 200, localTools.body);
    assert.match(localTools.body, /"tools"/);
    for (const foreign of ["https://untrusted.invalid", "null"]) {
      for (const method of ["initialize", "tools/list"]) {
        const denied = await request(foreign, "/_next/mcp", method);
        assert.equal(
          denied.status,
          403,
          "MCP accepted " + method + " origin " + foreign + ": " + denied.body,
        );
        assert.doesNotMatch(denied.body, /"serverInfo"/);
      }
    }
  } finally {
    if (observation.result === undefined) {
      trackChildren();
      child.kill("SIGTERM");
    }
    const deadline = Date.now() + 10000;
    while (!observation.closed && Date.now() < deadline) await pause();
    assert.ok(
      observation.closed,
      "Owned CLI termination is unproved; preserve its PID " + child.pid,
    );
    const result = await observation.exited;
    if (process.platform === "linux" && Number.isInteger(child.pid)) {
      assert.equal(
        existsSync("/proc/" + child.pid),
        false,
        "Owned CLI remains live",
      );
      for (const [pid, previous] of observedChildren) {
        const path = "/proc/" + pid + "/stat";
        const current = readLiveProcessFile(path);
        if (current !== undefined) {
          const start = (value) =>
            value.slice(value.lastIndexOf(") ") + 2).split(" ")[19];
          assert.notEqual(
            start(current),
            start(previous),
            "Owned developer child remains live: " + pid,
          );
        }
      }
    }
    console.log(
      "Owned Next CLI exited",
      JSON.stringify(result),
      "PID",
      child.pid,
    );
    checkStartupState();
  }
});
