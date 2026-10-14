import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const require = createRequire(join(root, "package.json"));
const cli = require.resolve("turbo");
const readJson = (path) => JSON.parse(readFileSync(path, "utf8"));
const sha256 = (path) =>
  createHash("sha256").update(readFileSync(path)).digest("hex");
const repositoryConfig = readJson(join(root, "turbo.json"));

// Resolve the real optional native package before any wrapper invocation.
// The upstream wrapper can run npm repair when native resolution fails.
assert.equal(
  process.env.TURBO_BINARY_PATH,
  undefined,
  "binary overrides are outside this acceptance gate",
);
const platform = process.platform === "win32" ? "windows" : process.platform;
const arch = process.arch === "x64" ? "64" : process.arch;
const nativeRequire = createRequire(cli);
const nativePackage = nativeRequire.resolve(
  "@turbo/" + platform + "-" + arch + "/package.json",
);
const nativeBinary = nativeRequire.resolve(
  "@turbo/" +
    platform +
    "-" +
    arch +
    "/bin/turbo" +
    (platform === "windows" ? ".exe" : ""),
);
assert.equal(
  readJson(nativePackage).version,
  "2.11.7",
  "native package must be the reviewed version",
);

function verifyNative() {
  const policy = readJson(join(root, "docs/ARCHITECTURE.yaml")).architecture
    .dependency_update_policy.turbo;
  assert.ok(policy, "canonical Turbo native acceptance policy is required");
  assert.equal(require("turbo/package.json").version, policy.version);
  assert.equal(readJson(nativePackage).version, policy.version);
  assert.equal(sha256(cli), policy.wrapper_sha256);
  if (platform === "linux" && arch === "64")
    assert.equal(sha256(nativeBinary), policy.native_linux_x64_sha256);
  return policy;
}

test("declared, locked, installed and native Turbo identities bind the reviewed gate", () => {
  const manifest = readJson(join(root, "package.json"));
  const policy = readJson(join(root, "docs/ARCHITECTURE.yaml")).architecture
    .dependency_update_policy.turbo;
  assert.ok(policy, "canonical Turbo native acceptance policy is required");
  assert.equal(manifest.devDependencies.turbo, policy.manifest_range);
  const installed = require("turbo/package.json");
  assert.equal(installed.version, policy.version);
  assert.deepEqual(installed.scripts, { postversion: "node bump-version.js" });
  assert.equal(sha256(cli), policy.wrapper_sha256);
  if (platform === "linux" && arch === "64")
    assert.equal(sha256(nativeBinary), policy.native_linux_x64_sha256);
  const lock = readFileSync(join(root, "pnpm-lock.yaml"), "utf8");
  assert.ok(lock.includes(policy.wrapper_integrity));
  const locked = [
    ...lock.matchAll(/^  ['"]?(turbo|@turbo\/[^'":]+)@([^'":]+)['"]?:$/gm),
  ];
  for (const name of [
    "turbo",
    ...Object.keys(installed.optionalDependencies),
  ]) {
    const versions = new Set(
      locked.filter((m) => m[1] === name).map((m) => m[2]),
    );
    assert.deepEqual([...versions], [policy.version]);
  }
  const platforms = [
    "darwin-64",
    "darwin-arm64",
    "linux-64",
    "linux-arm64",
    "windows-64",
    "windows-arm64",
  ];
  assert.deepEqual(
    Object.keys(installed.optionalDependencies).sort(),
    platforms.map((p) => `@turbo/${p}`).sort(),
  );
  for (const platform of platforms) {
    assert.equal(
      installed.optionalDependencies[`@turbo/${platform}`],
      policy.version,
    );
    assert.ok(lock.includes(`'@turbo/${platform}@${policy.version}':`));
  }
  assert.equal(readJson(nativePackage).version, policy.version);
  assert.equal(readJson(nativePackage).scripts, undefined);
  assert.ok(
    manifest.scripts["check:dependency-build-policy"].includes(policy.gate),
  );
});

function fixture(
  run,
  {
    tracked = false,
    ignored = false,
    filename = ".env.local",
    passthrough = false,
  } = {},
) {
  const cwd = mkdtempSync(join(tmpdir(), "portfolio-turbo-"));
  const env = {
    ...process.env,
    CI: "true",
    TURBO_TELEMETRY_DISABLED: "1",
    DO_NOT_TRACK: "1",
    NODE_DISABLE_COMPILE_CACHE: "1",
  };
  for (const key of Object.keys(env))
    if (
      key.startsWith("GIT_") ||
      key.startsWith("TURBO_") ||
      key.startsWith("VERCEL_")
    )
      delete env[key];
  env.TURBO_TELEMETRY_DISABLED = "1";
  env.XDG_CACHE_HOME = join(cwd, "cache");
  env.XDG_CONFIG_HOME = join(cwd, "config");
  const invoke = (command, args) => {
    if (command === process.execPath && args[0] === cli) {
      verifyNative();
      args = [...args, "--cache=local:rw"];
    }
    const result = spawnSync(command, args, {
      cwd,
      env,
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(result.error, undefined);
    assert.equal(
      result.status,
      0,
      `${command} ${args.join(" ")}\n${result.stdout}\n${result.stderr}`,
    );
    return result.stdout;
  };
  const git = (...args) => invoke("git", args).trim();
  const file = `apps/probe/${filename}`;
  const write = (value) => writeFileSync(join(cwd, file), value);
  const config = {
    $schema: repositoryConfig.$schema,
    globalDependencies: repositoryConfig.globalDependencies,
    ...(passthrough ? { globalPassThroughEnv: ["SDKROOT"] } : {}),
    tasks: { build: { outputs: [] } },
  };
  try {
    mkdirSync(join(cwd, "apps/probe"), { recursive: true });
    writeFileSync(
      join(cwd, "package.json"),
      JSON.stringify({
        name: "synthetic-turbo-contract",
        private: true,
        packageManager: "pnpm@10.34.5",
      }),
    );
    writeFileSync(
      join(cwd, "pnpm-workspace.yaml"),
      'packages:\n  - "apps/*"\n',
    );
    writeFileSync(
      join(cwd, "pnpm-lock.yaml"),
      "lockfileVersion: '9.0'\nimporters:\n  .: {}\n  apps/probe: {}\n",
    );
    writeFileSync(join(cwd, "turbo.json"), JSON.stringify(config));
    writeFileSync(
      join(cwd, ".gitignore"),
      ignored ? ".env.local\n.turbo\n" : ".turbo\n",
    );
    writeFileSync(
      join(cwd, "apps/probe/package.json"),
      JSON.stringify({
        name: "probe",
        version: "0.0.0",
        scripts: { build: "node task.mjs" },
      }),
    );
    writeFileSync(
      join(cwd, "apps/probe/task.mjs"),
      "console.log(JSON.stringify({SDKROOT: process.env.SDKROOT ?? null}));\n",
    );
    write("VERCEL_OIDC_TOKEN=first\nOTHER=keep\n");
    git("init", "-q");
    git("config", "user.name", "Synthetic Turbo Contract");
    git("config", "user.email", "synthetic@example.invalid");
    git("config", "core.hooksPath", join(cwd, "no-hooks"));
    git(
      "add",
      "package.json",
      "pnpm-workspace.yaml",
      "pnpm-lock.yaml",
      "turbo.json",
      ".gitignore",
      "apps/probe/package.json",
      "apps/probe/task.mjs",
    );
    if (tracked) git("add", file);
    git("-c", "commit.gpgsign=false", "commit", "-qm", "synthetic baseline");
    const dry = () => {
      const before = readFileSync(join(cwd, file));
      const output = invoke(process.execPath, [
        cli,
        "run",
        "build",
        "--dry=json",
        "--env-mode=strict",
        "--no-daemon",
      ]);
      assert.deepEqual(
        readFileSync(join(cwd, file)),
        before,
        "cache hashing must not edit dotenv bytes",
      );
      const data = JSON.parse(output);
      assert.equal(data.tasks.length, 1);
      return {
        hash: data.tasks[0].hash,
        inputs: data.tasks[0].inputs,
        globalFiles: data.globalCacheInputs.files,
      };
    };
    run({ cwd, env, file, write, git, dry, invoke });
  } finally {
    rmSync(cwd, { recursive: true, force: true });
  }
}

for (const mode of [
  { name: "clean tracked and then dirty", tracked: true },
  { name: "untracked" },
  { name: "ignored but explicitly global", ignored: true },
])
  test(`literal OIDC rotation only preserves cache identity for ${mode.name} files`, () =>
    fixture((f) => {
      const before = f.dry();
      assert.ok(Object.hasOwn(before.globalFiles, f.file));
      const raw = f.git("hash-object", f.file);
      f.write("VERCEL_OIDC_TOKEN=a-much-longer-rotated-token\nOTHER=keep\n");
      assert.deepEqual(f.dry(), before);
      assert.notEqual(
        f.git("hash-object", f.file),
        raw,
        "raw Git identity must observe the changed bytes",
      );
      if (mode.tracked) {
        f.git("add", f.file);
        f.git(
          "-c",
          "commit.gpgsign=false",
          "commit",
          "-qm",
          "synthetic token rotation",
        );
        assert.deepEqual(
          f.dry(),
          before,
          "clean Git fast path must use the same cache-only normalization",
        );
      }
      f.write("VERCEL_OIDC_TOKEN=a-much-longer-rotated-token\nOTHER=changed\n");
      assert.notEqual(f.dry().hash, before.hash);
    }, mode));

test("comments, token presence and ordinary variables remain cache inputs", () =>
  fixture((f) => {
    const base = f.dry().hash;
    for (const value of [
      "# changed\nVERCEL_OIDC_TOKEN=first\nOTHER=keep\n",
      "OTHER=keep\n",
      "VERCEL_OIDC_TOKEN=first\nOTHER=changed\n",
    ]) {
      f.write(value);
      assert.notEqual(f.dry().hash, base);
    }
  }));

for (const filename of [
  ".env",
  ".env.production",
  ".env.development.local",
  ".env.local.bak",
])
  test(`token rotation invalidates ordinary filename ${filename}`, () =>
    fixture(
      (f) => {
        const base = f.dry().hash;
        f.write("VERCEL_OIDC_TOKEN=a-longer-rotated-token\nOTHER=keep\n");
        assert.notEqual(f.dry().hash, base);
      },
      { filename, tracked: true },
    ));

for (const [name, first, second] of [
  [
    "duplicate keys",
    "VERCEL_OIDC_TOKEN=first\nVERCEL_OIDC_TOKEN=second\n",
    "VERCEL_OIDC_TOKEN=longer-first\nVERCEL_OIDC_TOKEN=second\n",
  ],
  [
    "multiline token",
    'VERCEL_OIDC_TOKEN="first\nline"\n',
    'VERCEL_OIDC_TOKEN="longer-first\nline"\n',
  ],
  [
    "unsupported syntax elsewhere",
    "OTHER=${VALUE}\nVERCEL_OIDC_TOKEN=first\n",
    "OTHER=${VALUE}\nVERCEL_OIDC_TOKEN=longer-first\n",
  ],
  [
    "binary input",
    Buffer.from("VERCEL_OIDC_TOKEN=first\n\0"),
    Buffer.from("VERCEL_OIDC_TOKEN=longer-first\n\0"),
  ],
  [
    "oversized input",
    "VERCEL_OIDC_TOKEN=first\n#" + "x".repeat(1048576),
    "VERCEL_OIDC_TOKEN=longer-first\n#" + "x".repeat(1048576),
  ],
])
  test(`ambiguous ${name} preserves conservative byte invalidation`, () =>
    fixture((f) => {
      f.write(first);
      const base = f.dry().hash;
      f.write(second);
      assert.notEqual(f.dry().hash, base);
    }));

test("SDKROOT forwarding requires explicit repository passthrough configuration", () => {
  assert.equal(
    repositoryConfig.globalPassThroughEnv?.includes("SDKROOT") ?? false,
    false,
  );
  for (const passthrough of [false, true])
    fixture(
      (f) => {
        f.env.SDKROOT = "/synthetic/apple-sdk";
        const output = f.invoke(process.execPath, [
          cli,
          "run",
          "build",
          "--env-mode=strict",
          "--no-daemon",
        ]);
        assert.ok(
          output.includes(
            JSON.stringify({
              SDKROOT: passthrough ? "/synthetic/apple-sdk" : null,
            }),
          ),
        );
      },
      { passthrough },
    );
});
