import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const code = "a();\nb();";
const map = (line, column = 0) => ({
  version: 3,
  sections: [
    {
      offset: { line, column },
      map: {
        version: 3,
        sources: ["input.ts"],
        sourcesContent: [code],
        names: [],
        mappings: "AAAA",
      },
    },
  ],
});

// These are both actual locked parents. Resolve their dependency rather than
// installing a separate test copy or importing an unrelated root package.
for (const [parent, directory] of [
  ["postcss", "postcss@8.5.23/node_modules/postcss"],
  [
    "@tailwindcss/node",
    "@tailwindcss+node@4.3.3/node_modules/@tailwindcss/node",
  ],
]) {
  const require = createRequire(
    resolve(root, "node_modules/.pnpm", directory, "package.json"),
  );
  const {
    SourceMapConsumer,
    SourceMapGenerator,
    SourceNode,
  } = require("source-map-js");

  test(`${parent} preserves public source-map round trips`, () => {
    const generator = new SourceMapGenerator({ file: "output.js" });
    generator.addMapping({
      generated: { line: 1, column: 0 },
      original: { line: 7, column: 2 },
      source: "input.ts",
      name: "a",
    });
    generator.setSourceContent("input.ts", code);
    const consumer = new SourceMapConsumer(generator.toJSON());
    assert.deepEqual(consumer.originalPositionFor({ line: 1, column: 0 }), {
      source: "input.ts",
      line: 7,
      column: 2,
      name: "a",
    });
    const node = SourceNode.fromStringWithSourceMap(code, consumer);
    assert.equal(node.toString(), code);
    assert.equal(node.toStringWithSourceMap().code, code);
    assert.equal(consumer.sourceContentFor("input.ts"), code);
  });

  test(`${parent} preserves indexed line offsets and generated code`, () => {
    const consumer = new SourceMapConsumer(map(1));
    const mappings = [];
    consumer.eachMapping((mapping) => mappings.push(mapping));
    assert.equal(mappings[0].generatedLine, 2);
    assert.equal(mappings[0].generatedColumn, 0);
    assert.equal(
      SourceNode.fromStringWithSourceMap(code, consumer).toString(),
      code,
    );
    // Exact section-start lookup has a separately tracked pre-existing upstream
    // bug. This security repair does not claim that boundary is fixed.
  });

  test(`${parent} resolves the reviewed maintained release`, () => {
    assert.equal(require("source-map-js/package.json").version, "1.2.2");
  });

  for (const [label, offset] of [
    ["large admitted finite", 1000000],
    ["maximum admitted line", 10000000],
  ]) {
    test(`${parent} bounds ${label} offsets by generated content`, () => {
      const consumer = new SourceMapConsumer(map(offset));
      const add = SourceNode.prototype.add;
      let fragments = 0;
      // A deterministic test-only circuit breaker keeps the vulnerable version
      // from exhausting memory. Every accepted call delegates to the real public
      // method. It is not a production workaround or a wall-clock benchmark.
      SourceNode.prototype.add = function (chunk) {
        assert.ok(
          ++fragments <= 32,
          "padding exceeded the generated-content budget",
        );
        return add.call(this, chunk);
      };
      try {
        assert.equal(
          SourceNode.fromStringWithSourceMap(code, consumer).toString(),
          code,
        );
      } finally {
        SourceNode.prototype.add = add;
      }
    });
  }
  for (const [label, line, column] of [
    ["excessive finite", 1e12, 0],
    ["maximum safe integer", Number.MAX_SAFE_INTEGER, 0],
    ["JSON exponent overflow", JSON.parse("1e999"), 0],
    ["negative line", -1, 0],
    ["fractional line", 0.5, 0],
    ["string line", "1", 0],
    ["negative column", 0, -1],
    ["fractional column", 0, 0.5],
    ["infinite column", 0, Infinity],
  ]) {
    test(`${parent} refuses ${label} section offsets`, () => {
      assert.throws(
        () => new SourceMapConsumer(map(line, column)),
        /Section offset/,
      );
    });
  }

  test(`${parent} bounds accumulated nested section lines`, () => {
    const nested = map(6000000);
    nested.sections[0].map = map(6000000);
    assert.throws(
      () => new SourceMapConsumer(nested),
      /including offsets of nested sections/,
    );
  });
}
