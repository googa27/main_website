import assert from "node:assert/strict";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const require = createRequire(join(root, "package.json"));
const cli = join(
  dirname(require.resolve("lint-staged/package.json")),
  "bin/lint-staged.js",
);
const pnpm = process.env.npm_execpath;
assert.ok(pnpm, "Run through the pinned pnpm workspace toolchain");
const separators = Array.from(
  { length: 12 },
  (_, i) => `// separator ${i}\n`,
).join("");
const contents = (selected, draft, formatted = true) =>
  `export const selectedValue${formatted ? " = " : "="}${selected};\n${separators}export const draftValue = ${draft};\n`;
const notes = (heading, footer = "base footer") =>
  `${heading}\n${separators}${footer}\n`;

function fixture(run) {
  const cwd = mkdtempSync(join(tmpdir(), "portfolio-staged-"));
  const env = {
    ...process.env,
    CI: "true",
    NODE_DISABLE_COMPILE_CACHE: "1",
    COREPACK_ENABLE_NETWORK: "0",
  };
  for (const key of Object.keys(env))
    if (key.startsWith("GIT_")) delete env[key];
  const invoke = (command, args, expected = 0) => {
    const result = spawnSync(command, args, { cwd, env, encoding: "utf8" });
    assert.equal(
      result.status,
      expected,
      `${command} ${args.join(" ")}\n${result.stdout}\n${result.stderr}`,
    );
    return result.stdout + result.stderr;
  };
  const git = (...args) => invoke("git", args);
  const file = "apps/web/src/staging probe.ts";
  const read = (path) => readFileSync(join(cwd, path), "utf8");
  const write = (path, value) => writeFileSync(join(cwd, path), value);
  try {
    mkdirSync(join(cwd, "apps/web/src"), { recursive: true });
    symlinkSync(
      join(root, "node_modules"),
      join(cwd, "node_modules"),
      "junction",
    );
    symlinkSync(
      join(root, "apps/web/node_modules"),
      join(cwd, "apps/web/node_modules"),
      "junction",
    );
    for (const path of [
      "package.json",
      "apps/web/package.json",
      "apps/web/eslint.config.mjs",
    ])
      write(path, readFileSync(join(root, path)));
    write(".gitignore", "node_modules\n");
    write(file, contents(1, 1));
    write("notes.txt", notes("base heading"));
    write(
      "apps/web/src/unrelated draft.ts",
      "export const unrelatedValue=1;\n",
    );
    git("init", "-q");
    git("config", "user.name", "Synthetic Staged Control");
    git("config", "user.email", "synthetic@example.invalid");
    git("config", "core.hooksPath", join(cwd, "no-hooks"));
    git(
      "add",
      ".gitignore",
      "package.json",
      "apps/web/package.json",
      "apps/web/eslint.config.mjs",
      file,
      "notes.txt",
      "apps/web/src/unrelated draft.ts",
    );
    git("-c", "commit.gpgsign=false", "commit", "-qm", "synthetic baseline");
    write(file, contents(2, 1, false));
    git("add", file);
    write("notes.txt", notes("private tracked draft"));
    write("untracked.txt", "private untracked draft\n");
    write(
      "apps/web/src/unrelated draft.ts",
      "export const unrelatedValue=9;\n",
    );
    write(
      "apps/web/src/untracked draft.ts",
      "export const untrackedValue=9;\n",
    );
    const staged = () => git("show", `:${file}`);
    const check = (args = [], expected = 0) =>
      invoke(
        process.execPath,
        [pnpm, "run", "check:staged", ...args],
        expected,
      );
    run({ cwd, file, read, write, git, staged, check, invoke });
  } finally {
    rmSync(cwd, { recursive: true, force: true });
  }
}

function assertOtherDrafts({ read, git }) {
  assert.equal(
    read("apps/web/src/unrelated draft.ts"),
    "export const unrelatedValue=9;\n",
  );
  assert.equal(
    git("show", ":apps/web/src/unrelated draft.ts"),
    "export const unrelatedValue=1;\n",
  );
  assert.equal(
    read("apps/web/src/untracked draft.ts"),
    "export const untrackedValue=9;\n",
  );
  assert.equal(git("ls-files", "--", "apps/web/src/untracked draft.ts"), "");
}

function assertPrivateFiles({ read, git }) {
  assertOtherDrafts({ read, git });
  assert.equal(read("notes.txt"), notes("private tracked draft"));
  assert.equal(git("show", ":notes.txt"), notes("base heading"));
  assert.equal(read("untracked.txt"), "private untracked draft\n");
  assert.equal(git("stash", "list"), "");
}

test("the root staged command runs web ESLint and formats only the selected file", () =>
  fixture((f) => {
    f.check();
    assert.equal(f.staged(), contents(2, 1));
    assert.equal(f.read(f.file), contents(2, 1));
    assertPrivateFiles(f);
  }));

test("partially staged web edits stay separate from tracked and untracked drafts", () =>
  fixture((f) => {
    f.write(f.file, contents(2, 9, false));
    f.check();
    assert.equal(f.staged(), contents(2, 1));
    assert.equal(f.read(f.file), contents(2, 9));
    assertPrivateFiles(f);
  }));

test("a real ESLint failure restores the exact original index and working bytes", () =>
  fixture((f) => {
    const staged = `${contents(2, 1, false)}const unusedValue = 3;\n`;
    const working = `${contents(2, 9, false)}const unusedValue = 3;\n`;
    f.write(f.file, staged);
    f.git("add", f.file);
    f.write(f.file, working);
    const status = f.git("status", "--porcelain");
    const output = f.check([], 1);
    assert.match(output, /no-unused-vars/);
    assert.equal(f.staged(), staged);
    assert.equal(f.read(f.file), working);
    assert.equal(f.git("status", "--porcelain"), status);
    assertPrivateFiles(f);
  }));

// This synthetic task deliberately edits a tracked file outside the web glob.
// It verifies the public hiding option against independent Git/blob oracles.
function sideEffect(f) {
  f.write(
    "task.cjs",
    'const fs = require("node:fs"); const p = "notes.txt"; fs.writeFileSync(p, fs.readFileSync(p, "utf8").replace("base footer", "task footer"));\n',
  );
  f.write(
    "side-effect.json",
    JSON.stringify({ "apps/web/**/*.ts": "node task.cjs" }),
  );
}

test("the canonical command keeps a side-effect task from staging an existing private draft", () =>
  fixture((f) => {
    sideEffect(f);
    f.check(["--config", "side-effect.json"]);
    assert.equal(
      f.git("show", ":notes.txt"),
      notes("base heading", "task footer"),
    );
    assert.equal(
      f.read("notes.txt"),
      notes("private tracked draft", "task footer"),
    );
    assert.equal(f.read("untracked.txt"), "private untracked draft\n");
    assert.equal(f.git("stash", "list"), "");
    assertOtherDrafts(f);
  }));

test("the unprotected native 17.6 command exposes the documented side-effect staging change", () =>
  fixture((f) => {
    sideEffect(f);
    f.invoke(process.execPath, [cli, "--config", "side-effect.json"]);
    assert.equal(
      f.git("show", ":notes.txt"),
      notes("private tracked draft", "task footer"),
    );
    assert.equal(
      f.read("notes.txt"),
      notes("private tracked draft", "task footer"),
    );
    assert.equal(f.git("stash", "list"), "");
    assertOtherDrafts(f);
  }));
