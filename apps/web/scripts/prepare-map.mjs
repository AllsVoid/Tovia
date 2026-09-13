import { copyFile, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// Keep the ESM worker and its shared module at stable same-origin URLs.
const require = createRequire(import.meta.url);
const source = dirname(require.resolve("maplibre-gl/package.json"));
const target = fileURLToPath(new URL("../public/maplibre/", import.meta.url));
await mkdir(target, { recursive: true });
for (const name of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  await copyFile(join(source, "dist", name), join(target, name));
}
await copyFile(join(source, "LICENSE.txt"), join(target, "LICENSE.txt"));
