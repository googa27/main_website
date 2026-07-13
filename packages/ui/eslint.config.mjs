import sharedConfig from "@repo/config/eslint";

export default [
  ...sharedConfig,
  {
    ignores: ["eslint.config.mjs"],
  },
];
