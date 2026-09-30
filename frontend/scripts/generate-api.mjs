/**
 * scripts/generate-api.mjs
 *
 * Regenerates TypeScript types from OpenAPI schema.
 * Supports:
 *   1. Live backend at http://localhost:8000/openapi.json
 *   2. Exported openapi.json file fallback (for offline CI & local dev)
 */

import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");
const rootDir = path.resolve(frontendDir, "..");

const liveUrl = process.env.OPENAPI_URL || "http://localhost:8000/openapi.json";
const localJsonPath = path.join(frontendDir, "src", "lib", "api", "openapi.json");
const outputPath = path.join(frontendDir, "src", "lib", "api", "generated.ts");

async function checkUrl(url) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);
    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);
    return res.ok;
  } catch {
    return false;
  }
}

async function main() {
  console.log("Generating API client...");
  const isLive = await checkUrl(liveUrl);
  let schemaSource = liveUrl;

  if (isLive) {
    console.log(`Using live backend schema from ${liveUrl}`);
  } else {
    console.log(`Backend not reachable at ${liveUrl}. Checking local schema...`);
    // Try exporting schema using python if needed
    try {
      const pythonScript = path.join(rootDir, "scripts", "export_openapi.py");
      if (fs.existsSync(pythonScript)) {
        console.log("Refreshing openapi.json via scripts/export_openapi.py...");
        // Check for venv python or system python
        const venvPython = process.platform === "win32"
          ? path.join(rootDir, "backend", ".venv", "Scripts", "python.exe")
          : path.join(rootDir, "backend", ".venv", "bin", "python");
        const pyCmd = fs.existsSync(venvPython) ? `"${venvPython}"` : "python";
        execSync(`${pyCmd} "${pythonScript}"`, { cwd: rootDir, stdio: "inherit" });
      }
    } catch (err) {
      console.warn("Could not run export_openapi.py, falling back to existing json file:", err.message);
    }

    if (!fs.existsSync(localJsonPath)) {
      console.error(`Error: Cannot find schema at ${localJsonPath}`);
      process.exit(1);
    }
    schemaSource = localJsonPath;
    console.log(`Using local schema: ${localJsonPath}`);
  }

  try {
    const localBin = path.join(
      frontendDir,
      "node_modules",
      ".bin",
      process.platform === "win32" ? "openapi-typescript.cmd" : "openapi-typescript"
    );
    const cmd = fs.existsSync(localBin)
      ? `"${localBin}" "${schemaSource}" -o "${outputPath}"`
      : `npx -y openapi-typescript@7.4.4 "${schemaSource}" -o "${outputPath}"`;
    execSync(cmd, {
      cwd: frontendDir,
      stdio: "inherit",
      shell: true,
    });
    console.log(`Successfully generated types to ${outputPath}`);
  } catch (err) {
    console.error("Failed to generate TypeScript types:", err);
    process.exit(1);
  }
}

main();
