#!/usr/bin/env node

import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const readText = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");
const readJson = (relativePath) => JSON.parse(readText(relativePath));
const fail = (message) => {
  console.error(`dependency build policy FAILED: ${message}`);
  process.exitCode = 1;
};
const equalSets = (left, right) =>
  left.size === right.size && [...left].every((value) => right.has(value));
const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const sha256 = (path) =>
  createHash("sha256").update(readFileSync(path)).digest("hex");

const packageJson = readJson("package.json");
const architecture = readJson("docs/ARCHITECTURE.yaml");
const policy = architecture.architecture.dependency_lifecycle_policy;
const runtimePolicy = architecture.architecture.node_runtime_policy;
const lock = readText("pnpm-lock.yaml");
const workspace = readText("pnpm-workspace.yaml");

const versionsInLock = (name) => {
  const pattern = new RegExp(
    `^  ['"]?${escapeRegex(name)}@([^'":]+)['"]?:$`,
    "gm",
  );
  return new Set([...lock.matchAll(pattern)].map((match) => match[1]));
};

const packageRoot = (name, version) => {
  const virtualName = name.replace("/", "+");
  const packageParts = name.split("/");
  return resolve(
    root,
    "node_modules/.pnpm",
    `${virtualName}@${version}`,
    "node_modules",
    ...packageParts,
  );
};

const expectHash = (path, expected, label) => {
  let actual;
  try {
    actual = sha256(path);
  } catch (error) {
    fail(`${label} is unreadable at ${path}: ${error.message}`);
    return;
  }
  if (actual !== expected) {
    fail(`${label} SHA-256 ${actual} does not match reviewed ${expected}`);
  }
};

if (packageJson.packageManager !== policy.package_manager) {
  fail(
    `packageManager ${packageJson.packageManager} does not match ${policy.package_manager}`,
  );
}

const expectedPnpmVersion = policy.package_manager.replace("pnpm@", "");
const userAgent = process.env.npm_config_user_agent ?? "";
if (!userAgent.startsWith(`pnpm/${expectedPnpmVersion} `)) {
  fail(
    `policy must run through pnpm ${expectedPnpmVersion}; npm_config_user_agent=${JSON.stringify(userAgent)}`,
  );
}

const pnpmConfig = packageJson.pnpm ?? {};
const forbiddenAllowControls = [
  "allowBuilds",
  "dangerouslyAllowAllBuilds",
  "neverBuiltDependencies",
  "onlyBuiltDependencies",
  "onlyBuiltDependenciesFile",
];
for (const setting of forbiddenAllowControls) {
  if (Object.hasOwn(pnpmConfig, setting)) {
    fail(`package.json pnpm.${setting} is forbidden by deny-only policy`);
  }
  if (new RegExp(`^\\s*${setting}:`, "m").test(workspace)) {
    fail(`pnpm-workspace.yaml ${setting} is forbidden by deny-only policy`);
  }
}

const configuredDenied = new Set(pnpmConfig.ignoredBuiltDependencies ?? []);
const reviewedDenied = new Set(Object.keys(policy.denied_packages));
if (!equalSets(configuredDenied, reviewedDenied)) {
  fail(
    `ignoredBuiltDependencies ${JSON.stringify([...configuredDenied].sort())} does not match reviewed policy ${JSON.stringify([...reviewedDenied].sort())}`,
  );
}

const configuredRuntime = packageJson.devEngines?.runtime;
const expectedRuntime = {
  name: "node",
  version: runtimePolicy.managed_runtime.replace("node@", ""),
  onFail: "download",
};
if (JSON.stringify(configuredRuntime) !== JSON.stringify(expectedRuntime)) {
  fail(
    `devEngines.runtime ${JSON.stringify(configuredRuntime)} does not match ${JSON.stringify(expectedRuntime)}`,
  );
}

for (const [name, evidence] of Object.entries(policy.denied_packages)) {
  if (evidence.decision !== "deny") {
    fail(`${name} has non-deny decision ${evidence.decision}`);
    continue;
  }

  const versions = versionsInLock(name);
  if (!equalSets(versions, new Set([evidence.version]))) {
    fail(
      `${name} lock versions ${JSON.stringify([...versions].sort())} do not match reviewed ${evidence.version}`,
    );
    continue;
  }

  const installedRoot = packageRoot(name, evidence.version);
  const manifestPath = resolve(installedRoot, "package.json");
  expectHash(manifestPath, evidence.manifest_sha256, `${name} package.json`);

  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  } catch (error) {
    fail(`${name} package.json cannot be parsed: ${error.message}`);
    continue;
  }
  if (manifest.scripts?.postinstall !== evidence.lifecycle_command) {
    fail(
      `${name} postinstall ${JSON.stringify(manifest.scripts?.postinstall)} does not match reviewed ${JSON.stringify(evidence.lifecycle_command)}`,
    );
  }

  if (evidence.support_package) {
    const support = evidence.support_package;
    const supportVersions = versionsInLock(support.name);
    if (!equalSets(supportVersions, new Set([support.version]))) {
      fail(
        `${support.name} lock versions ${JSON.stringify([...supportVersions].sort())} do not match reviewed ${support.version}`,
      );
      continue;
    }
    const supportRoot = packageRoot(support.name, support.version);
    expectHash(
      resolve(supportRoot, "package.json"),
      support.manifest_sha256,
      `${support.name} package.json`,
    );
    const actualLibFiles = readdirSync(resolve(supportRoot, "lib"), {
      withFileTypes: true,
    })
      .filter((entry) => entry.isFile() && entry.name.endsWith(".js"))
      .map((entry) => `lib/${entry.name}`)
      .sort();
    if (JSON.stringify(actualLibFiles) !== JSON.stringify(support.lib_files)) {
      fail(
        `${support.name} executable files ${JSON.stringify(actualLibFiles)} do not match reviewed ${JSON.stringify(support.lib_files)}`,
      );
    }
    const treeHash = createHash("sha256");
    for (const relativePath of actualLibFiles) {
      treeHash.update(relativePath);
      treeHash.update("\0");
      treeHash.update(readFileSync(resolve(supportRoot, relativePath)));
      treeHash.update("\0");
    }
    const actualTreeHash = treeHash.digest("hex");
    if (actualTreeHash !== support.lib_tree_sha256) {
      fail(
        `${support.name} executable tree SHA-256 ${actualTreeHash} does not match reviewed ${support.lib_tree_sha256}`,
      );
    }
    expectHash(
      resolve(supportRoot, "lib/cli.js"),
      support.cli_sha256,
      `${support.name} lib/cli.js`,
    );
    if (support.cli_sha256 !== evidence.script_sha256) {
      fail(`${name} script_sha256 must identify ${support.name} lib/cli.js`);
    }
  } else {
    expectHash(
      resolve(installedRoot, "scripts/install.js"),
      evidence.script_sha256,
      `${name} scripts/install.js`,
    );
  }
}

const npmExecPath = process.env.npm_execpath;
let moduleState;
try {
  moduleState = readJson("node_modules/.modules.yaml");
} catch (error) {
  fail(`pnpm module state is unreadable: ${error.message}`);
}
if (moduleState) {
  if (moduleState.packageManager !== policy.package_manager) {
    fail(
      `node_modules package manager ${moduleState.packageManager} does not match ${policy.package_manager}`,
    );
  }
  if (!Array.isArray(moduleState.pendingBuilds)) {
    fail("pnpm module state does not expose pendingBuilds");
  } else if (moduleState.pendingBuilds.length > 0) {
    fail(
      `pnpm has unreviewed pending builds: ${JSON.stringify(moduleState.pendingBuilds)}`,
    );
  }
}

if (!npmExecPath) {
  fail("npm_execpath is missing; invoke through pnpm run");
} else {
  const ignoredBuildsEnv = { ...process.env };
  for (const name of Object.keys(ignoredBuildsEnv)) {
    if (name.startsWith("npm_") || name.startsWith("PNPM_")) {
      delete ignoredBuildsEnv[name];
    }
  }
  const ignoredBuilds = spawnSync(npmExecPath, ["ignored-builds"], {
    cwd: root,
    encoding: "utf8",
    env: ignoredBuildsEnv,
  });
  if (ignoredBuilds.status !== 0) {
    fail(
      `pnpm ignored-builds via ${npmExecPath} failed: ${ignoredBuilds.stderr || ignoredBuilds.stdout}`,
    );
  } else {
    const output = ignoredBuilds.stdout;
    const reportsNone =
      /Automatically ignored builds during installation:\s+None/.test(output);
    const cannotIdentify = output.includes(
      "Cannot identify as no node_modules found",
    );
    if (!reportsNone && !cannotIdentify) {
      fail(
        `pnpm reports unreviewed automatically ignored builds via ${npmExecPath}:\n${output}`,
      );
    }
    for (const name of reviewedDenied) {
      if (!output.includes(name)) {
        fail(
          `pnpm ignored-builds output does not confirm explicit denial of ${name}`,
        );
      }
    }
  }
}

if (!process.exitCode) {
  console.log(
    `dependency build policy OK: denied=${[...reviewedDenied].sort().join(",")} runtime=${runtimePolicy.managed_runtime}`,
  );
}
