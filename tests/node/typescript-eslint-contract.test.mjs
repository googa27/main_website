import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";

const configManifest = new URL(
  "../../packages/config/package.json",
  import.meta.url,
);
const require = createRequire(configManifest);
const manifest = JSON.parse(readFileSync(configManifest, "utf8"));
assert.equal(typeof manifest.devDependencies["typescript-eslint"], "string");
assert.equal(manifest.devDependencies["@typescript-eslint/parser"], undefined);
assert.equal(
  manifest.devDependencies["@typescript-eslint/eslint-plugin"],
  undefined,
);
const shared = require("@repo/config/eslint");
const { Linter } = require("eslint");

test("shared config parses TypeScript and JSX through the atomic upstream provider", () => {
  const linter = new Linter();
  for (const [filename, text] of [
    ["public-synthetic.ts", "const count: number = 1; export { count };"],
    ["public-synthetic.tsx", "export const Example = () => <div />;"],
  ]) {
    assert.deepEqual(linter.verify(text, shared, { filename }), []);
  }
});

test("shared config retains unused-variable refusal and explicit-any warning", () => {
  const messages = new Linter().verify("const unused: any = 1;", shared, {
    filename: "public-synthetic.ts",
  });
  assert.equal(
    messages.some((row) => row.fatal),
    false,
  );
  assert.deepEqual(
    messages.map(({ ruleId, severity }) => [ruleId, severity]).sort(),
    [
      ["@typescript-eslint/no-explicit-any", 1],
      ["@typescript-eslint/no-unused-vars", 2],
    ],
  );
});
