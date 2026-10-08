import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync, realpathSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const webRequire = createRequire(resolve(root, "apps/web/package.json"));
const nextRequire = createRequire(webRequire.resolve("next/package.json"));
const sharp = nextRequire("sharp");
const redSVG = Buffer.from(
  '<svg xmlns="http://www.w3.org/2000/svg" width="2" height="1">' +
    '<rect width="2" height="1" fill="#ff0000"/></svg>',
);

test("Next's installed Sharp includes the maintained security repair", () => {
  // This is package-version admission; loaded GNU asset identity is checked below.
  // GHSA-wq5f-xc86-pv6w requires patched sharp >=0.35.5 and librsvg >=2.63.2.
  const [major, minor, patch] = sharp.versions.sharp.split(".").map(Number);
  assert.ok(
    major > 0 || minor > 35 || (minor === 35 && patch >= 5),
    `Next loads vulnerable sharp ${sharp.versions.sharp}`,
  );
});

test("Next's SVG dependency metadata includes the maintained security repair", () => {
  const [rMajor, rMinor, rPatch] = sharp.versions.rsvg.split(".").map(Number);
  assert.ok(
    rMajor > 2 ||
      (rMajor === 2 && (rMinor > 63 || (rMinor === 63 && rPatch >= 2))),
    `Next reports vulnerable librsvg metadata ${sharp.versions.rsvg}`,
  );
});

const linuxGNU =
  process.platform === "linux" &&
  process.arch === "x64" &&
  Boolean(process.report.getReport().header.glibcVersionRuntime);

test(
  "the loaded GNU native renderer matches independently published asset bytes",
  { skip: !linuxGNU },
  () => {
    const policy = JSON.parse(
      readFileSync(resolve(root, "docs/ARCHITECTURE.yaml"), "utf8"),
    ).architecture.sharp_policy;
    assert.ok(policy?.native_assets, "Published native asset policy is absent");
    const sharpEntry = nextRequire.resolve("sharp");
    const sharpRequire = createRequire(sharpEntry);
    const bindingRoot = dirname(
      sharpRequire.resolve("@img/sharp-linux-x64/package"),
    );
    const manifests = {
      sharp: resolve(dirname(sharpEntry), "../package.json"),
      "@img/sharp-linux-x64": sharpRequire.resolve(
        "@img/sharp-linux-x64/package",
      ),
      "@img/sharp-libvips-linux-x64": sharpRequire.resolve(
        "@img/sharp-libvips-linux-x64/package",
      ),
    };
    for (const [name, path] of Object.entries(manifests)) {
      const bytes = readFileSync(path);
      assert.equal(
        createHash("sha256").update(bytes).digest("hex"),
        policy.published_manifests[name],
      );
      const manifest = JSON.parse(bytes);
      assert.equal(manifest.name, name);
      for (const hook of ["preinstall", "install", "postinstall", "prepare"]) {
        assert.equal(
          Object.hasOwn(manifest.scripts ?? {}, hook),
          false,
          `${name} has an unreviewed ${hook} hook`,
        );
      }
    }
    const paths = {
      binding: realpathSync(
        resolve(bindingRoot, policy.native_assets.binding.path),
      ),
      libvips: sharpRequire.resolve("@img/sharp-libvips-linux-x64/binary"),
      versions: sharpRequire.resolve("@img/sharp-libvips-linux-x64/versions"),
    };
    const maps = readFileSync("/proc/self/maps", "utf8").split("\n");
    for (const [name, path] of Object.entries(paths)) {
      assert.ok(
        path.startsWith(resolve(root, "node_modules") + "/"),
        "Ambient native dependency is outside the managed installation",
      );
      const actual = createHash("sha256")
        .update(readFileSync(path))
        .digest("hex");
      assert.equal(
        actual,
        policy.native_assets[name].sha256,
        `${name} differs from the published maintained asset`,
      );
      if (name !== "versions") {
        assert.ok(
          maps.some((line) => line.endsWith(" " + path)),
          `${name} was not actually loaded by the real consumer`,
        );
      }
    }
  },
);

test("Next's resolved Sharp preserves literal SVG pixels", async () => {
  const { data, info } = await sharp(redSVG)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  assert.equal(info.width, 2);
  assert.equal(info.height, 1);
  assert.equal(info.channels, 4);
  assert.deepEqual([...data], [255, 0, 0, 255, 255, 0, 0, 255]);
});

test("SVG resizing preserves a hand-derived solid pixel", async () => {
  const { data, info } = await sharp(redSVG)
    .resize(1, 1)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  assert.equal(info.width, 1);
  assert.equal(info.height, 1);
  assert.deepEqual([...data], [255, 0, 0, 255]);
});

test("SVG to PNG roundtrip retains pixels through the actual native renderer", async () => {
  const png = await sharp(redSVG).png().toBuffer();
  assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  const { data, info } = await sharp(png)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  assert.equal(info.width, 2);
  assert.equal(info.height, 1);
  assert.deepEqual([...data], [255, 0, 0, 255, 255, 0, 0, 255]);
});

test("the actual SVG consumer rejects malformed input", async () => {
  await assert.rejects(
    sharp(Buffer.from('<svg><path d="')).toBuffer(),
    /corrupt|parse|invalid|unsupported|error/i,
  );
});

test("the actual SVG consumer enforces its explicit input pixel limit", async () => {
  const svg = Buffer.from(
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"/>',
  );
  await assert.rejects(
    sharp(svg, { limitInputPixels: 64 }).raw().toBuffer(),
    /pixel limit/i,
  );
});
