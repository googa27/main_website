import { dirname } from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";
import { FlatCompat } from "@eslint/eslintrc";

const require = createRequire(import.meta.url);

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  {
    ignores: ["eslint.config.mjs"],
  },
  ...compat.config(require("@repo/config/eslint")),
  {
    rules: {
      // Add any UI package-specific rules here
      "@next/next/no-html-link-for-pages": "off",
    },
  },
];

export default eslintConfig;
