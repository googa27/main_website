import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const policy = JSON.parse(
  readFileSync(resolve(root, "docs/ARCHITECTURE.yaml"), "utf8"),
).architecture.dependency_update_policy.prettier;
assert.deepEqual(policy.importers, [".", "packages/config"]);

// Prettier has no peers. pnpm's generated package/snapshot keys therefore
// expose its version directly; the frozen install validates the full YAML.
const lock = readFileSync(resolve(root, "pnpm-lock.yaml"), "utf8");
test("the frozen lock contains only the reviewed formatter version", () => {
  const versions = new Set(
    [...lock.matchAll(/^  prettier@([^:]+):$/gm)].map((match) => match[1]),
  );
  assert.deepEqual([...versions], [policy.version]);
});

// Independent content oracles: formatting must preserve the mathematical
// expression. CLI success alone misses the 3.9.9 superscript regression.
const fixtures = [
  ["inline superscripts", "Let $r^*$ and $q^*$ be optimal.\n"],
  ["bold subscripts", "**$z_i$ and $w_j$**\n"],
  ["mixed inline math", "Risk $p_i^*$ and $s_j^*$ are finite.\n"],
  ["TeX macro subscripts", "**$\\hat{z}_i$ and $\\hat{w}_j$**\n"],
  ["display math", "$$\nr^* + q_i\n$$\n"],
  ["code dollars", "`$r^*$` remains code.\n"],
  ["ordinary currency", "Budget $100 and cost $200.\n"],
];

for (const importer of policy.importers) {
  const manifestPath = resolve(root, importer, "package.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  const require = createRequire(manifestPath);
  const prettier = require("prettier");
  const installed = require("prettier/package.json");

  test(`${importer} declares and resolves the exact reviewed formatter`, () => {
    assert.equal(manifest.devDependencies.prettier, policy.version);
    assert.equal(installed.name, "prettier");
    assert.equal(installed.version, policy.version);
    assert.equal(prettier.version, policy.version);
  });

  for (const [label, input] of fixtures) {
    test(`${importer} preserves ${label}`, async () => {
      const output = await prettier.format(input, { parser: "markdown" });
      assert.equal(output, input);
      assert.equal(
        await prettier.format(output, { parser: "markdown" }),
        input,
      );
    });
  }
}
