import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const policy = JSON.parse(
  readFileSync(resolve(root, "docs/ARCHITECTURE.yaml"), "utf8"),
).architecture.brace_expansion_policy;
const normal = "file{a,b}{1..3}.txt";
const expanded = [
  "filea1.txt",
  "filea2.txt",
  "filea3.txt",
  "fileb1.txt",
  "fileb2.txt",
  "fileb3.txt",
];

for (const version of policy.minimatch_versions) {
  const packageRoot = resolve(
    root,
    `node_modules/.pnpm/minimatch@${version}/node_modules/minimatch`,
  );
  const manifestPath = resolve(packageRoot, "package.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  assert.equal(manifest.version, version);
  const require = createRequire(manifestPath);
  const dependency = require("brace-expansion");
  const expand =
    typeof dependency === "function" ? dependency : dependency.expand;
  const dependencyVersion = require("brace-expansion/package.json").version;
  const bindings = [["CommonJS", require(packageRoot)]];
  if (manifest.exports) {
    bindings.push([
      "ES module",
      await import(
        pathToFileURL(
          resolve(packageRoot, manifest.exports["."].import.default),
        ).href
      ),
    ]);
  }

  test(`minimatch ${version} resolves the selected patched dependency`, () => {
    assert.ok(policy.brace_versions.includes(dependencyVersion));
  });

  // The advisory's argument-list overflow exceeds minimatch's length cap;
  // exercise its actual resolved dependency directly, without bypassing that cap.
  test(`brace-expansion ${dependencyVersion} handles a large comma array`, () => {
    const result = expand("{{x}," + "a,".repeat(300000) + "b}");
    assert.ok(Array.isArray(result) && result.length > 0);
    assert.ok(result.length <= 100000);
  });

  for (const [format, consumer] of bindings) {
    const label = `minimatch ${version} ${format}`;
    test(`${label} preserves ordinary expansion and matching`, () => {
      assert.deepEqual(consumer.braceExpand(normal), expanded);
      const matcher = new consumer.Minimatch(normal);
      for (const filename of expanded)
        assert.equal(matcher.match(filename), true);
      assert.equal(matcher.match("filec1.txt"), false);
      assert.deepEqual(consumer.braceExpand("{a},b}"), ["a}", "b"]);
    });

    // Upstream GHSA-6j4f-fj2g-mc7p: 64,003 characters, below the
    // consumer's 65,536-character maximum; output caps do not fix the parser.
    test(`${label} handles the recursive comma parser payload`, () => {
      const pattern = "{" + "{a},".repeat(16000) + "b}";
      assert.ok(pattern.length < 65536);
      const result = consumer.braceExpand(pattern);
      assert.ok(Array.isArray(result) && result.length > 0);
      assert.ok(result.length <= 100000);
      assert.doesNotThrow(() => new consumer.Minimatch(pattern));
    });

    // Upstream GHSA-qhr7-859c-m2p7 identifies both nesting recursion sites.
    for (const [site, pattern] of [
      ["comma members", "{a,".repeat(6000) + "z" + "}".repeat(6000)],
      ["single set", "{".repeat(6000) + "a,b" + "}".repeat(6000)],
    ]) {
      test(`${label} bounds nested ${site} recursion`, () => {
        assert.ok(pattern.length < 65536);
        const result = consumer.braceExpand(pattern);
        assert.ok(Array.isArray(result) && result.length > 0);
        assert.doesNotThrow(() => new consumer.Minimatch(pattern));
      });
    }

    // GHSA-q2hr-2g5m-vwhr's patch stops rewriting after 1,000 passes and
    // preserves the remaining pattern literally. This is an output oracle,
    // not a timing benchmark or a machine-speed threshold.
    test(`${label} returns excessive rewrites literally`, () => {
      const pattern = "{a}" + "}".repeat(1200) + ",z}";
      assert.deepEqual(consumer.braceExpand(pattern), [pattern]);
      assert.doesNotThrow(() => new consumer.Minimatch(pattern));
    });
  }
}
