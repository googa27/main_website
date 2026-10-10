import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const policy = JSON.parse(
  readFileSync(resolve(root, "docs/ARCHITECTURE.yaml"), "utf8"),
).architecture.source_map_policy;
const referenceRequire = createRequire(
  resolve(
    root,
    "node_modules/.pnpm/@jridgewell+trace-mapping@0.3.31/node_modules/@jridgewell/trace-mapping/package.json",
  ),
);
const reference = referenceRequire("@jridgewell/trace-mapping");
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
  });

  for (const [line, column] of [
    [0, 0],
    [0, 2],
    [1, 2],
    [3, 5],
  ]) {
    const indexed = map(line, column);
    indexed.sections[0].map.mappings = "AAAA;AACA";
    const label = line + "," + column;
    test(parent + " resolves exact indexed section start " + label, () => {
      const position = { line: line + 1, column };
      const actual = new SourceMapConsumer(indexed).originalPositionFor(
        position,
      );
      assert.deepEqual(actual, {
        source: "input.ts",
        line: 1,
        column: 0,
        name: null,
      });
      assert.deepEqual(
        actual,
        reference.originalPositionFor(new reference.AnyMap(indexed), position),
      );
      if (column > 0)
        assert.deepEqual(
          new SourceMapConsumer(indexed).originalPositionFor({
            line: line + 1,
            column: column - 1,
          }),
          { source: null, line: null, column: null, name: null },
        );
    });
    test(parent + " enumerates first-line-only column offset " + label, () => {
      const actual = [];
      new SourceMapConsumer(indexed).eachMapping((m) =>
        actual.push([m.generatedLine, m.generatedColumn]),
      );
      assert.deepEqual(actual, [
        [line + 1, column],
        [line + 2, 0],
      ]);
    });
    test(parent + " reverses indexed section columns " + label, () => {
      const consumer = new SourceMapConsumer(indexed);
      assert.deepEqual(
        consumer.generatedPositionFor({
          source: "input.ts",
          line: 1,
          column: 0,
        }),
        { line: line + 1, column },
      );
      assert.deepEqual(
        consumer.generatedPositionFor({
          source: "input.ts",
          line: 2,
          column: 0,
        }),
        { line: line + 2, column: 0 },
      );
    });
  }
  for (const [innerLine, expectedLine, expectedColumn] of [
    [0, 3, 7],
    [1, 4, 3],
  ]) {
    test(
      parent + " composes nested first-line column offsets " + innerLine,
      () => {
        const indexed = map(2, 4);
        indexed.sections[0].map = map(innerLine, 3);
        const consumer = new SourceMapConsumer(indexed);
        assert.deepEqual(
          consumer.originalPositionFor({
            line: expectedLine,
            column: expectedColumn,
          }),
          { source: "input.ts", line: 1, column: 0, name: null },
        );
        const actual = [];
        consumer.eachMapping((m) =>
          actual.push([m.generatedLine, m.generatedColumn]),
        );
        assert.deepEqual(actual, [[expectedLine, expectedColumn]]);
      },
    );
  }
  test(
    parent + " selects the next section at its exact column boundary",
    () => {
      const indexed = map(1, 2);
      const next = map(1, 5).sections[0];
      next.map.sources = ["second.ts"];
      indexed.sections.push(next);
      const consumer = new SourceMapConsumer(indexed);
      assert.equal(
        consumer.originalPositionFor({ line: 2, column: 4 }).source,
        "input.ts",
      );
      assert.equal(
        consumer.originalPositionFor({ line: 2, column: 5 }).source,
        "second.ts",
      );
    },
  );
  test(
    parent +
      " retains indexed SourceNode code and generated-column round trips",
    () => {
      const generated = "prefix();\n  a();\nb();";
      const output = SourceNode.fromStringWithSourceMap(
        generated,
        new SourceMapConsumer(map(1, 2)),
      ).toStringWithSourceMap();
      assert.equal(output.code, generated);
      assert.deepEqual(
        new SourceMapConsumer(output.map.toJSON()).originalPositionFor({
          line: 2,
          column: 2,
        }),
        { source: "input.ts", line: 1, column: 0, name: null },
      );
    },
  );

  // Flat oracle coordinates below are literal fixtures, not a reimplementation
  // of section flattening. AnyMap has documented duplicate/nested limitations.
  {
    const section = (line, column, map) => ({ offset: { line, column }, map });
    const indexed = (...sections) => ({ version: 3, sections });
    const basic = (
      line = 3,
      column = 4,
      source = "late.js",
      sourceRoot = undefined,
    ) => {
      const g = new SourceMapGenerator({ file: "generated.js", sourceRoot });
      g.addMapping({
        generated: { line: 1, column: 0 },
        original: { line, column },
        source,
      });
      return g.toJSON();
    };
    const flat = (entries, sourceRoot) => {
      const g = new SourceMapGenerator({ file: "flat.js", sourceRoot });
      for (const [gl, gc, ol, oc] of entries)
        g.addMapping({
          generated: { line: gl, column: gc },
          original: { line: ol, column: oc },
          source: "late.js",
        });
      return g.toJSON();
    };
    const expect = (
      map,
      args,
      expected,
      entries,
      sourceRoot,
      oracleArgs = args,
    ) => {
      const oracle = reference.generatedPositionFor(
        new reference.TraceMap(flat(entries, sourceRoot)),
        oracleArgs,
      );
      assert.deepEqual(
        oracle,
        expected,
        "independent unindexed TraceMap vs literal",
      );
      const actual = new SourceMapConsumer(map).generatedPositionFor(args);
      assert.deepEqual(
        { line: actual.line, column: actual.column },
        expected,
        "real indexed public consumer vs literal",
      );
    };
    const q = { source: "late.js", line: 1, column: 0 };
    test(parent + " present source before first original line stays null", () =>
      expect(indexed(section(2, 7, basic())), q, { line: null, column: null }, [
        [3, 7, 3, 4],
      ]),
    );
    test(
      parent + " present source before first original column stays null",
      () =>
        expect(
          indexed(section(2, 7, basic())),
          { source: "late.js", line: 3, column: 3 },
          { line: null, column: null },
          [[3, 7, 3, 4]],
        ),
    );
    test(parent + " absent source stays null", () =>
      expect(
        indexed(section(2, 7, basic())),
        { source: "absent.js", line: 1, column: 0 },
        { line: null, column: null },
        [[3, 7, 3, 4]],
      ),
    );
    test(parent + " declared source with empty mappings stays null", () =>
      expect(
        indexed(
          section(2, 7, {
            version: 3,
            sources: ["late.js"],
            names: [],
            mappings: "",
          }),
        ),
        q,
        { line: null, column: null },
        [],
      ),
    );
    test(parent + " later section survives an earlier no-match", () =>
      expect(
        indexed(section(2, 7, basic()), section(4, 9, basic(1, 0))),
        q,
        { line: 5, column: 9 },
        [
          [3, 7, 3, 4],
          [5, 9, 1, 0],
        ],
      ),
    );
    test(parent + " all sections without a matching original stay null", () =>
      expect(
        indexed(section(2, 7, basic()), section(4, 9, basic(4, 4))),
        q,
        { line: null, column: null },
        [
          [3, 7, 3, 4],
          [5, 9, 4, 4],
        ],
      ),
    );
    test(parent + " valid mapped result keeps section offsets", () =>
      expect(
        indexed(section(2, 7, basic())),
        { source: "late.js", line: 3, column: 4 },
        { line: 3, column: 7 },
        [[3, 7, 3, 4]],
      ),
    );
    test(parent + " public child preserves relative sourceRoot alias", () => {
      const m = basic(3, 4, "late.js", "/src");
      assert.deepEqual(
        new SourceMapConsumer(m).generatedPositionFor({
          source: "late.js",
          line: 3,
          column: 4,
        }),
        { line: 1, column: 0, lastColumn: null },
      );
      expect(
        indexed(section(2, 7, m)),
        { source: "late.js", line: 3, column: 4 },
        { line: 3, column: 7 },
        [[3, 7, 3, 4]],
        "/src",
        { source: "/src/late.js", line: 3, column: 4 },
      );
    });
    test(
      parent + " canonical sourceRoot path agrees with independent consumer",
      () =>
        expect(
          indexed(section(2, 7, basic(3, 4, "late.js", "/src"))),
          { source: "/src/late.js", line: 3, column: 4 },
          { line: 3, column: 7 },
          [[3, 7, 3, 4]],
          "/src",
        ),
    );
    test(parent + " nested later-line mapped result preserves offsets", () =>
      expect(
        indexed(section(4, 3, indexed(section(2, 7, basic())))),
        { source: "late.js", line: 3, column: 4 },
        { line: 7, column: 7 },
        [[7, 7, 3, 4]],
      ),
    );
    test(parent + " nested first-line columns compose", () =>
      expect(
        indexed(section(0, 3, indexed(section(0, 7, basic())))),
        { source: "late.js", line: 3, column: 4 },
        { line: 1, column: 10 },
        [[1, 10, 3, 4]],
      ),
    );
    test(parent + " nested absent source stays null", () =>
      expect(
        indexed(section(4, 3, indexed(section(2, 7, basic())))),
        { source: "absent.js", line: 1, column: 0 },
        { line: null, column: null },
        [[7, 7, 3, 4]],
      ),
    );
    test(parent + " nested present source without original stays null", () =>
      expect(
        indexed(section(4, 3, indexed(section(2, 7, basic())))),
        q,
        { line: null, column: null },
        [[7, 7, 3, 4]],
      ),
    );
    test(parent + " later mapped section survives nested no-match", () =>
      expect(
        indexed(
          section(2, 7, indexed(section(0, 0, basic()))),
          section(10, 9, basic(1, 0)),
        ),
        q,
        { line: 11, column: 9 },
        [
          [3, 7, 3, 4],
          [11, 9, 1, 0],
        ],
      ),
    );
  }

  test(`${parent} resolves the reviewed maintained release and exact patch`, () => {
    assert.equal(require("source-map-js/package.json").version, "1.2.2");
    assert.equal(
      createHash("sha256")
        .update(
          readFileSync(
            require.resolve("source-map-js/lib/source-map-consumer.js"),
          ),
        )
        .digest("hex"),
      policy.correctness_patch.patched_consumer_sha256,
    );
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

test("PostCSS composes a real previous indexed map at its exact section start", () => {
  const require = createRequire(
    resolve(
      root,
      "node_modules/.pnpm/postcss@8.5.23/node_modules/postcss/package.json",
    ),
  );
  const postcss = require("./lib/postcss.js");
  const indexed = {
    version: 3,
    sections: [
      {
        offset: { line: 1, column: 2 },
        map: {
          version: 3,
          file: "input.css",
          sources: ["input.scss"],
          sourcesContent: ["original"],
          names: [],
          mappings: "AAMG",
        },
      },
    ],
  };
  const output = postcss([
    {
      postcssPlugin: "indexed-map-control",
      Declaration(declaration) {
        if (declaration.value === "red") declaration.value = "blue";
      },
    },
  ]).process("/*a*/\n  a { color: red }", {
    from: "/input.css",
    to: "/output.css",
    map: { prev: indexed, inline: false, annotation: false },
  });
  assert.equal(output.css, "/*a*/\n  a { color: blue }");
  const { SourceMapConsumer } = require("source-map-js");
  assert.deepEqual(
    new SourceMapConsumer(output.map.toJSON()).originalPositionFor({
      line: 2,
      column: 2,
    }),
    { source: "input.scss", line: 7, column: 3, name: null },
  );
});
