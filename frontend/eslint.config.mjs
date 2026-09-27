import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // Never use dangerouslySetInnerHTML on model/source output (Part Q)
      "react/no-danger": "error",
      // Enforce explicit return types on exported functions
      "@typescript-eslint/explicit-module-boundary-types": "warn",
      // No console.log in production code — use structured logging
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
];

export default eslintConfig;
