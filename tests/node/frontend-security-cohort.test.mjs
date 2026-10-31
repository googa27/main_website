import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const webRequire = createRequire(resolve(root, "apps/web/package.json"));
const configRequire = createRequire(webRequire.resolve("eslint-config-next"));
const hooksRequire = createRequire(
  configRequire.resolve("eslint-plugin-react-hooks"),
);
const { z } = hooksRequire("zod");
const policy = JSON.parse(
  readFileSync(resolve(root, "docs/ARCHITECTURE.yaml"), "utf8"),
).architecture.frontend_security_cohort;

test("the real react-hooks consumer resolves the bounded-collection Zod repair", () => {
  assert.equal(hooksRequire("zod/package.json").version, "4.6.6");
  for (const kind of ["array", "set", "map"]) {
    let parsed = 0;
    const element = z.unknown().superRefine(() => {
      parsed++;
    });
    const schema =
      kind === "array"
        ? z.array(element).max(1)
        : kind === "set"
          ? z.set(element).max(1)
          : z.map(z.string(), element).max(1);
    const oversized =
      kind === "array"
        ? ["a", "b"]
        : kind === "set"
          ? new Set(["a", "b"])
          : new Map([
              ["a", "a"],
              ["b", "b"],
            ]);
    const result = schema.safeParse(oversized);
    assert.equal(result.success, false);
    assert.deepEqual(
      result.error.issues.map(({ code }) => code),
      ["too_big"],
    );
    assert.equal(
      parsed,
      0,
      `${kind} validated elements before rejecting its bound`,
    );
    const ordinary =
      kind === "array"
        ? ["a"]
        : kind === "set"
          ? new Set(["a"])
          : new Map([["a", "a"]]);
    assert.equal(schema.safeParse(ordinary).success, true);
    assert.equal(parsed, 1);
  }
});

// This is a reachability disposition, not a package-range suppression. Exact
// installed caller bytes bind the review to the current consumer options.
test("reviewed minimatch callers retain their default preprocessing boundary", () => {
  assert.ok(policy?.minimatch_disposition?.caller_files?.length > 0);
  for (const { file, sha256, minimatch } of policy.minimatch_disposition
    .caller_files) {
    const path = resolve(root, "node_modules/.pnpm", file);
    const callerRequire = createRequire(path);
    assert.equal(callerRequire("minimatch/package.json").version, minimatch);
    const bytes = readFileSync(path);
    assert.equal(
      createHash("sha256").update(bytes).digest("hex"),
      sha256,
      `${file} changed: repeat the per-consumer options review`,
    );
  }
});

for (const version of ["3.1.5", "10.2.5", "10.2.6"]) {
  test(`minimatch ${version} default and actual caller options avoid amplification`, () => {
    const require = createRequire(
      resolve(
        root,
        `node_modules/.pnpm/minimatch@${version}/node_modules/minimatch/package.json`,
      ),
    );
    const minimatch = require(
      `./${version.startsWith("3.") ? "minimatch.js" : "dist/commonjs/index.js"}`,
    );
    const pattern = "**/../a/b/**/../c/d";
    for (const options of [
      {},
      { dot: true },
      { dot: true, flipNegate: true },
    ]) {
      const matcher = new minimatch.Minimatch(pattern, options);
      assert.equal(matcher.globParts.length, 1);
      assert.equal(
        new minimatch.Minimatch("**/*.js", options).match("src/main.js"),
        true,
      );
      assert.equal(
        new minimatch.Minimatch("**/*.js", options).match("src/main.ts"),
        false,
      );
    }
    if (version.startsWith("3.")) {
      assert.equal(typeof minimatch, "function");
      assert.equal(
        minimatch.Minimatch.prototype.firstPhasePreProcess,
        undefined,
      );
    } else {
      // A small positive control proves that the same installed package still
      // contains the advisory mechanism when an unsupported option opts in.
      const optedIn = new minimatch.Minimatch(pattern, {
        optimizationLevel: 2,
      });
      assert.ok(optedIn.globParts.length > 1);
    }
  });
}
